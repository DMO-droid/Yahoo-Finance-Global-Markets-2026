import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import warnings
warnings.filterwarnings('ignore')


# LOAD & CLEAN
df = pd.read_csv('yahoo_finance_global_markets_2026.csv')

EQUITY_CLASSES = ['US_MEGA', 'US_MID', 'INTL']
eq = df[df['asset_class'].isin(EQUITY_CLASSES)].copy()

# Winsorize
for col, (lo, hi) in [('trailingPE',(0,500)),('forwardPE',(-50,300)),
                       ('priceToBook',(-50,100)),('debtToEquity',(0,500)),
                       ('returnOnEquity',(-2,5))]:
    eq[f'{col}_raw'] = eq[col].copy()
    eq[col] = eq[col].clip(lo, hi)

eq['flag_negative_equity']      = (eq['priceToBook_raw'] < 0).astype(int)
eq['flag_extreme_margins']      = ((eq['profitMargins'] < -0.5) | (eq['returnOnEquity'] > 2)).astype(int)
eq['flag_leveraged_or_extreme'] = (eq['return_1y_pct'].abs() > 100).astype(int)

# Chỉ lấy equity có đủ tín hiệu kỹ thuật
eq_tech = eq.dropna(subset=['rsi_14','macd','bb_pct_b','sma_50','sma_200']).copy()
print(f"[INFO] Equity với đủ technical data: {len(eq_tech)} / {len(eq)} rows")

# 1. TẠO TÍN HIỆU KỸ THUẬT TỔNG HỢP
# 1.1 RSI Signal (3 vùng)
def rsi_zone(r):
    if r >= 70: return 'OVERBOUGHT'
    if r <= 30: return 'OVERSOLD'
    return 'NEUTRAL'

eq_tech['rsi_zone'] = eq_tech['rsi_14'].apply(rsi_zone)

# 1.2 Trend Signal: kết hợp Golden Cross + Price vs SMA200
def trend_signal(row):
    gc    = row['golden_cross']
    p200  = row['price_vs_sma200_pct']
    if gc == 1 and p200 > 0:   return 'STRONG_UPTREND'
    if gc == 1 and p200 <= 0:  return 'UPTREND'
    if gc == 0 and p200 < 0:   return 'STRONG_DOWNTREND'
    return 'DOWNTREND'

eq_tech['trend_signal'] = eq_tech.apply(trend_signal, axis=1)

# 1.3 MACD Momentum
# macd_histogram > 0 và tăng so với median = momentum đang mạnh lên
eq_tech['macd_momentum'] = eq_tech['macd_histogram'].apply(
    lambda x: 'BULLISH' if x > 0 else 'BEARISH'
)

# 1.4 BB Position
def bb_zone(b):
    if b > 80: return 'OVERBOUGHT'
    if b < 20: return 'OVERSOLD'
    return 'NEUTRAL'

eq_tech['bb_zone'] = eq_tech['bb_pct_b'].apply(bb_zone)

# 1.5 COMPOSITE TECHNICAL SCORE (0–100)
# Tính từ 4 tín hiệu, mỗi cái đóng góp tối đa 25 điểm
def composite_tech_score(row):
    score = 0
    # RSI: 25 điểm — tốt nhất khi RSI 40–65 (momentum tốt, chưa overbought)
    rsi = row['rsi_14']
    if 40 <= rsi <= 65:   score += 25
    elif 30 <= rsi < 40:  score += 15
    elif 65 < rsi <= 70:  score += 15
    elif rsi > 70:        score += 5   # overbought — rủi ro đảo chiều
    elif rsi < 30:        score += 10  # oversold — có thể là cơ hội

    # MACD: 25 điểm
    if row['macd_crossover'] == 'BULLISH':
        score += 25 if row['macd_histogram'] > 0 else 15
    else:
        score += 5 if row['macd_histogram'] > 0 else 0

    # Trend (Golden Cross + SMA200): 25 điểm
    ts = row['trend_signal']
    score += {'STRONG_UPTREND': 25, 'UPTREND': 15,
              'DOWNTREND': 5, 'STRONG_DOWNTREND': 0}[ts]

    # BB Position: 25 điểm — tốt nhất trong bands và trending up
    bb = row['bb_pct_b']
    if 40 <= bb <= 80:   score += 25   # trong bands, thiên upper
    elif 20 <= bb < 40:  score += 15   # lower half
    elif bb > 80:        score += 10   # near upper band
    elif bb < 20:        score += 10   # oversold theo BB
    return score

eq_tech['tech_score'] = eq_tech.apply(composite_tech_score, axis=1)

# 1.6 Rating dựa trên tech_score
def tech_rating(s):
    if s >= 80: return 'STRONG BUY'
    if s >= 60: return 'BUY'
    if s >= 40: return 'NEUTRAL'
    if s >= 20: return 'SELL'
    return 'STRONG SELL'

eq_tech['tech_rating'] = eq_tech['tech_score'].apply(tech_rating)

print("\n[INFO] Tech Rating Distribution:")
print(eq_tech['tech_rating'].value_counts())
print("\n[INFO] Trend Signal Distribution:")
print(eq_tech['trend_signal'].value_counts())

# 2. SECTOR MOMENTUM ANALYSIS

sector_stats = eq_tech.groupby('sector').agg(
    count           = ('ticker', 'count'),
    avg_momentum    = ('momentum_score', 'mean'),
    avg_tech_score  = ('tech_score', 'mean'),
    avg_rsi         = ('rsi_14', 'mean'),
    pct_golden      = ('golden_cross', 'mean'),
    avg_return_3m   = ('return_3m_pct', 'mean'),
    avg_return_1m   = ('return_1m_pct', 'mean'),
    pct_bullish_macd= ('macd_momentum', lambda x: (x=='BULLISH').mean()),
).round(2).sort_values('avg_momentum', ascending=False)

print("\n[INFO] Sector Momentum Ranking:")
print(sector_stats.to_string())

# 3. WATCHLIST — STRONG BUY FILTER
# Điều kiện: tín hiệu kỹ thuật chất lượng cao, không leveraged
watchlist = eq_tech[
    (eq_tech['golden_cross'] == 1) &          # uptrend dài hạn
    (eq_tech['macd_crossover'] == 'BULLISH') & # momentum đang tăng
    (eq_tech['rsi_14'].between(35, 65)) &      # RSI healthy (không OB/OS)
    (eq_tech['bb_pct_b'] > 30) &              # giá trong vùng tích cực
    (eq_tech['flag_leveraged_or_extreme'] == 0)
].copy().sort_values('tech_score', ascending=False)

print(f"\n[INFO] Watchlist Strong Buy: {len(watchlist)} stocks")

# Lưu tín hiệu đầy đủ
output_cols = ['ticker','shortName','asset_class','sector',
               'rsi_14','rsi_zone','macd_crossover','macd_momentum',
               'bb_pct_b','bb_zone','golden_cross','trend_signal',
               'price_vs_sma50_pct','price_vs_sma200_pct',
               'tech_score','tech_rating',
               'return_1m_pct','return_3m_pct','return_1y_pct',
               'momentum_score','composite_score']

eq_tech[output_cols].sort_values('tech_score', ascending=False).to_csv(
    'tech_signals_summary.csv', index=False)

watchlist[output_cols].head(20).to_csv('watchlist_strong_buy.csv', index=False)
print("[SAVED] tech_signals_summary.csv")
print("[SAVED] watchlist_strong_buy.csv")

# 4. VISUALISATION — DASHBOARD 6 CHARTS

PALETTE = {
    'bg':           '#FAFAF8',
    'card':         '#FFFFFF',
    'border':       '#E8E6DF',
    'text_primary': '#1A1A18',
    'text_muted':   '#6B6B66',
    'bull':         '#1D9E75',   # teal-600
    'bear':         '#E24B4A',   # red-400
    'neutral':      '#888780',   # gray-400
    'amber':        '#BA7517',   # amber-400
    'blue':         '#378ADD',   # blue-400
    'purple':       '#7F77DD',   # purple-400
}

# Rating colors
RATING_COLORS = {
    'STRONG BUY':  PALETTE['bull'],
    'BUY':         '#5DCAA5',
    'NEUTRAL':     PALETTE['neutral'],
    'SELL':        '#F09595',
    'STRONG SELL': PALETTE['bear'],
}

plt.rcParams.update({
    'font.family':       'DejaVu Sans',
    'font.size':         10,
    'axes.facecolor':    PALETTE['card'],
    'figure.facecolor':  PALETTE['bg'],
    'axes.spines.top':   False,
    'axes.spines.right': False,
    'axes.edgecolor':    PALETTE['border'],
    'axes.labelcolor':   PALETTE['text_muted'],
    'xtick.color':       PALETTE['text_muted'],
    'ytick.color':       PALETTE['text_muted'],
    'text.color':        PALETTE['text_primary'],
    'grid.color':        PALETTE['border'],
    'grid.linewidth':    0.5,
})

fig = plt.figure(figsize=(18, 14))
fig.patch.set_facecolor(PALETTE['bg'])

gs = gridspec.GridSpec(3, 3, figure=fig,
                       hspace=0.42, wspace=0.32,
                       left=0.06, right=0.97,
                       top=0.91, bottom=0.06)

# Title
fig.text(0.5, 0.965, 'Technical Analysis Dashboard — Yahoo Finance 2026',
         ha='center', va='top', fontsize=16, fontweight='bold',
         color=PALETTE['text_primary'])
fig.text(0.5, 0.942, f'{len(eq_tech)} equity stocks  |  US Mega + Mid Cap + International',
         ha='center', va='top', fontsize=10, color=PALETTE['text_muted'])


# CHART 1: RSI Distribution (histogram) 
ax1 = fig.add_subplot(gs[0, 0])

rsi_vals = eq_tech['rsi_14'].dropna()
n, bins, patches = ax1.hist(rsi_vals, bins=25, edgecolor='white', linewidth=0.4)

for patch, left in zip(patches, bins[:-1]):
    if left < 30:
        patch.set_facecolor(PALETTE['bull'])
        patch.set_alpha(0.85)
    elif left >= 70:
        patch.set_facecolor(PALETTE['bear'])
        patch.set_alpha(0.85)
    else:
        patch.set_facecolor(PALETTE['blue'])
        patch.set_alpha(0.6)

ax1.axvline(30, color=PALETTE['bull'], lw=1.2, ls='--', alpha=0.8)
ax1.axvline(70, color=PALETTE['bear'], lw=1.2, ls='--', alpha=0.8)
ax1.text(30, ax1.get_ylim()[1]*0.9 if n.max() > 0 else 5,
         'Oversold\n30', ha='center', fontsize=8, color=PALETTE['bull'])
ax1.text(70, ax1.get_ylim()[1]*0.9 if n.max() > 0 else 5,
         'Overbought\n70', ha='center', fontsize=8, color=PALETTE['bear'])

os_c = (rsi_vals < 30).sum()
ob_c = (rsi_vals > 70).sum()
ax1.set_title('RSI-14 Distribution', fontsize=11, fontweight='bold', pad=8)
ax1.set_xlabel('RSI Value')
ax1.set_ylabel('Count')

legend_patches = [
    mpatches.Patch(color=PALETTE['bull'],    alpha=0.85, label=f'Oversold <30 ({os_c})'),
    mpatches.Patch(color=PALETTE['blue'],    alpha=0.6,  label=f'Neutral ({len(rsi_vals)-os_c-ob_c})'),
    mpatches.Patch(color=PALETTE['bear'],    alpha=0.85, label=f'Overbought >70 ({ob_c})'),
]
ax1.legend(handles=legend_patches, fontsize=7.5, framealpha=0)


# CHART 2: Tech Rating Donut
ax2 = fig.add_subplot(gs[0, 1])

rating_counts = eq_tech['tech_rating'].value_counts()
order = ['STRONG BUY','BUY','NEUTRAL','SELL','STRONG SELL']
vals   = [rating_counts.get(r, 0) for r in order]
colors = [RATING_COLORS[r] for r in order]

wedges, texts, autotexts = ax2.pie(
    vals, labels=order, colors=colors,
    autopct=lambda p: f'{p:.0f}%' if p > 3 else '',
    startangle=90,
    wedgeprops={'width': 0.55, 'edgecolor': 'white', 'linewidth': 1.5},
    textprops={'fontsize': 8},
    pctdistance=0.75,
)
for at in autotexts:
    at.set_fontsize(7.5)
    at.set_color('white')
    at.set_fontweight('bold')

ax2.set_title('Technical Rating Distribution', fontsize=11, fontweight='bold', pad=8)
total = sum(vals)
ax2.text(0, 0, f'{total}\nstocks', ha='center', va='center',
         fontsize=9, color=PALETTE['text_muted'])


# CHART 3: Sector Momentum Heatmap
ax3 = fig.add_subplot(gs[0, 2])

sectors_sorted = sector_stats.sort_values('avg_momentum')
s_names  = [s.replace(' ', '\n') if len(s) > 15 else s for s in sectors_sorted.index]
s_values = sectors_sorted['avg_momentum'].values

colors_bar = [PALETTE['bull'] if v >= 0 else PALETTE['bear'] for v in s_values]

bars = ax3.barh(range(len(s_names)), s_values, color=colors_bar,
                alpha=0.8, height=0.65, edgecolor='white', linewidth=0.5)

for i, (val, bar) in enumerate(zip(s_values, bars)):
    xpos = val + 0.5 if val >= 0 else val - 0.5
    ha   = 'left' if val >= 0 else 'right'
    ax3.text(xpos, i, f'{val:+.1f}', va='center', ha=ha,
             fontsize=7.5, color=PALETTE['text_primary'])

ax3.set_yticks(range(len(s_names)))
ax3.set_yticklabels(s_names, fontsize=7.5)
ax3.axvline(0, color=PALETTE['border'], lw=1)
ax3.set_title('Sector Avg Momentum Score', fontsize=11, fontweight='bold', pad=8)
ax3.set_xlabel('Momentum Score')
ax3.grid(axis='x', alpha=0.4)


# CHART 4: MACD Histogram Scatter (RSI vs MACD momentum)
ax4 = fig.add_subplot(gs[1, 0:2])

scatter_df = eq_tech[eq_tech['flag_leveraged_or_extreme'] == 0].copy()
scatter_df['macd_hist_clipped'] = scatter_df['macd_histogram'].clip(-5, 5)

bull_mask = scatter_df['macd_crossover'] == 'BULLISH'
bear_mask = ~bull_mask

ax4.scatter(scatter_df.loc[bull_mask, 'rsi_14'],
            scatter_df.loc[bull_mask, 'macd_hist_clipped'],
            c=PALETTE['bull'], alpha=0.55, s=30,
            label=f'BULLISH crossover ({bull_mask.sum()})', zorder=3)
ax4.scatter(scatter_df.loc[bear_mask, 'rsi_14'],
            scatter_df.loc[bear_mask, 'macd_hist_clipped'],
            c=PALETTE['bear'], alpha=0.45, s=30,
            label=f'BEARISH crossover ({bear_mask.sum()})', zorder=3)

# Quadrant lines
ax4.axvline(30, color=PALETTE['bull'],    lw=0.8, ls=':', alpha=0.6)
ax4.axvline(70, color=PALETTE['bear'],    lw=0.8, ls=':', alpha=0.6)
ax4.axhline(0,  color=PALETTE['neutral'], lw=1.0, ls='--', alpha=0.7)

# Quadrant labels
ax4.text(50, ax4.get_ylim()[1]*0.85 if ax4.get_ylim()[1] != 0 else 4,
         'Sweet spot\n(RSI 30–70, MACD > 0)', ha='center',
         fontsize=7.5, color=PALETTE['bull'], alpha=0.8)

# Label top momentum stocks
top5 = scatter_df.nlargest(5, 'momentum_score')
for _, row in top5.iterrows():
    ax4.annotate(row['ticker'],
                 xy=(row['rsi_14'], row['macd_hist_clipped']),
                 xytext=(5, 5), textcoords='offset points',
                 fontsize=7, color=PALETTE['text_primary'],
                 arrowprops=dict(arrowstyle='-', color=PALETTE['border'], lw=0.5))

ax4.set_title('RSI vs MACD Histogram — Signal Quadrants', fontsize=11, fontweight='bold', pad=8)
ax4.set_xlabel('RSI-14')
ax4.set_ylabel('MACD Histogram (clipped ±5)')
ax4.legend(fontsize=8, framealpha=0, loc='upper left')
ax4.grid(alpha=0.3)

# Shade sweet spot
ax4.axvspan(30, 70, alpha=0.04, color=PALETTE['bull'])


# CHART 5: Golden Cross & Trend Signal
ax5 = fig.add_subplot(gs[1, 2])

trend_counts  = eq_tech['trend_signal'].value_counts()
trend_order   = ['STRONG_UPTREND', 'UPTREND', 'DOWNTREND', 'STRONG_DOWNTREND']
trend_colors  = [PALETTE['bull'], '#5DCAA5', '#F09595', PALETTE['bear']]
trend_labels  = ['Strong\nUptrend', 'Uptrend', 'Downtrend', 'Strong\nDowntrend']
trend_vals    = [trend_counts.get(t, 0) for t in trend_order]

bars5 = ax5.bar(range(4), trend_vals, color=trend_colors,
                alpha=0.85, width=0.6, edgecolor='white', linewidth=0.5)
for i, (bar, val) in enumerate(zip(bars5, trend_vals)):
    ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
             str(val), ha='center', fontsize=9, fontweight='bold',
             color=PALETTE['text_primary'])

ax5.set_xticks(range(4))
ax5.set_xticklabels(trend_labels, fontsize=8)
ax5.set_title('Trend Signal (SMA50/200)', fontsize=11, fontweight='bold', pad=8)
ax5.set_ylabel('Number of Stocks')
ax5.grid(axis='y', alpha=0.4)

pct_up = (trend_vals[0] + trend_vals[1]) / sum(trend_vals) * 100
ax5.text(1.5, max(trend_vals)*0.92,
         f'{pct_up:.0f}% in uptrend',
         ha='center', fontsize=8.5, color=PALETTE['bull'],
         fontweight='bold')


# CHART 6: Top 15 Tech Score - Ranked Bar
ax6 = fig.add_subplot(gs[2, :])

top15 = eq_tech.nlargest(15, 'tech_score')[
    ['ticker','sector','tech_score','tech_rating',
     'rsi_14','macd_crossover','golden_cross','return_3m_pct']
].copy()

bar_colors = [RATING_COLORS.get(r, PALETTE['neutral']) for r in top15['tech_rating']]

bars6 = ax6.barh(range(len(top15)), top15['tech_score'],
                 color=bar_colors, alpha=0.82,
                 height=0.65, edgecolor='white', linewidth=0.5)

ax6.set_yticks(range(len(top15)))
ax6.set_yticklabels(
    [f"{row['ticker']}  ({row['sector'][:18]})" for _, row in top15.iterrows()],
    fontsize=8.5
)
ax6.invert_yaxis()

# Annotations per bar
for i, (_, row) in enumerate(top15.iterrows()):
    macd_sym = '▲' if row['macd_crossover'] == 'BULLISH' else '▼'
    gc_sym   = 'GC' if row['golden_cross'] == 1 else '—'
    label    = f"  {row['tech_rating']}  |  RSI {row['rsi_14']:.0f}  |  MACD {macd_sym}  |  {gc_sym}  |  3M: {row['return_3m_pct']:+.1f}%"
    ax6.text(row['tech_score'] + 0.5, i, label,
             va='center', fontsize=7.5, color=PALETTE['text_primary'])

ax6.set_xlim(0, 105)
ax6.set_title('Top 15 Stocks by Technical Score', fontsize=11, fontweight='bold', pad=8)
ax6.set_xlabel('Technical Score (0–100)')
ax6.grid(axis='x', alpha=0.3)
ax6.axvline(80, color=PALETTE['bull'], lw=0.8, ls='--', alpha=0.5)
ax6.axvline(60, color=PALETTE['blue'], lw=0.8, ls='--', alpha=0.5)
ax6.text(80, -0.7, 'Strong Buy', ha='center', fontsize=7, color=PALETTE['bull'])
ax6.text(60, -0.7, 'Buy',        ha='center', fontsize=7, color=PALETTE['blue'])

# Legend cho rating colors
legend_patches = [mpatches.Patch(color=c, label=r, alpha=0.85)
                  for r, c in RATING_COLORS.items()]
ax6.legend(handles=legend_patches, loc='lower right',
           fontsize=7.5, framealpha=0.8, ncol=5)


# Save
plt.savefig('technical_analysis_report.png',
            dpi=150, bbox_inches='tight',
            facecolor=PALETTE['bg'])
plt.close()
print("\n[SAVED] technical_analysis_report.png")


# 5. PRINT WATCHLIST SUMMARY

print("\n" + "=" * 65)
print("WATCHLIST — TOP 20 KỸ THUẬT (Golden Cross + MACD Bullish + RSI OK)")
print("=" * 65)
watch_display = watchlist.head(20)[
    ['ticker','sector','tech_score','tech_rating',
     'rsi_14','macd_crossover','golden_cross',
     'return_1m_pct','return_3m_pct','composite_score']
]
print(watch_display.to_string(index=False))

print("\n" + "=" * 65)
print("SECTOR MOMENTUM RANKING (tốt nhất → yếu nhất)")
print("=" * 65)
print(sector_stats[['count','avg_momentum','avg_tech_score',
                     'pct_golden','avg_return_3m']].to_string())

print("\n[DONE] Bước 2 hoàn tất.")
