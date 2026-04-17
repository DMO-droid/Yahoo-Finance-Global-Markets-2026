"""
Bước 5 — Investment Screener & Composite Scoring
=================================================
Input:  yahoo_finance_global_markets_2026.csv
Output: screener_results.xlsx   (6 sheets)
        screener_dashboard.png  (visual dashboard)

Tại sao build lại composite score?
- composite_score gốc: R²=0.96 với momentum → momentum dominated
- value_score gốc: thang 0.35–10,075 (raw, không chuẩn hoá)
- quality_score gốc: thang −167–1,884 (raw)
→ Cần percentile-rank tất cả về 0–100 trước khi weighted average

Chạy: python screener.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════
# 0. LOAD & CLEAN (kế thừa Bước 1 + 2)
# ══════════════════════════════════════════════════════════════
df = pd.read_csv('yahoo_finance_global_markets_2026.csv')
EQUITY = ['US_MEGA', 'US_MID', 'INTL']
eq = df[df['asset_class'].isin(EQUITY)].copy().reset_index(drop=True)

# Fix bb_pct_b unit (0-100 → 0-1)
eq['bb_pct_b_norm'] = eq['bb_pct_b'] / 100.0

# Fix outliers cho valuation cols
clip_rules = {
    'trailingPE':    (0, 500),
    'forwardPE':     (-50, 300),
    'priceToBook':   (-50, 100),
    'debtToEquity':  (0, 500),
    'returnOnEquity':(-2, 5),
}
for col, (lo, hi) in clip_rules.items():
    if col in eq.columns:
        eq[col] = eq[col].clip(lo, hi)

print(f"[INFO] Equity rows: {len(eq)}")


# ══════════════════════════════════════════════════════════════
# 1. XÂY DỰNG LẠI COMPOSITE SCORE CHUẨN HOÁ
# ══════════════════════════════════════════════════════════════
# LÝ DO: Score gốc bị momentum dominated (weight ~21x so với value).
# Percentile rank đưa tất cả về thang 0–100, công bằng cross-metric.
# Higher = better cho tất cả 3 trụ.

def pct_rank(series, ascending=True):
    """Percentile rank 0–100. ascending=True: giá trị cao → điểm cao."""
    if ascending:
        return series.rank(pct=True, na_option='keep') * 100
    else:
        return (1 - series.rank(pct=True, na_option='keep')) * 100

# ── Trụ 1: MOMENTUM (40% weight) ──────────────────────────────
# Cổ phiếu đang tăng mạnh → ưu tiên trong ngắn-trung hạn
eq['pr_return_3m']    = pct_rank(eq['return_3m_pct'])
eq['pr_return_1y']    = pct_rank(eq['return_1y_pct'])
eq['pr_sharpe']       = pct_rank(eq['sharpe_1y'])
eq['pr_momentum_raw'] = pct_rank(eq['momentum_score'])
eq['pr_rsi']          = pct_rank(eq['rsi_14'])          # RSI cao = đang tăng

eq['momentum_idx'] = (
    eq['pr_return_3m']    * 0.30 +
    eq['pr_return_1y']    * 0.25 +
    eq['pr_sharpe']       * 0.25 +
    eq['pr_momentum_raw'] * 0.15 +
    eq['pr_rsi']          * 0.05
)

# ── Trụ 2: VALUE (30% weight) ─────────────────────────────────
# Cổ phiếu rẻ tương đối → điểm cao = PE thấp, P/B thấp...
eq['pr_pe']       = pct_rank(eq['trailingPE'],    ascending=False)  # PE thấp = tốt
eq['pr_fpe']      = pct_rank(eq['forwardPE'],     ascending=False)
eq['pr_pb']       = pct_rank(eq['priceToBook'],   ascending=False)
eq['pr_upside']   = pct_rank(eq['analyst_upside_pct'])              # upside cao = tốt

eq['value_idx'] = (
    eq['pr_pe']     * 0.35 +
    eq['pr_fpe']    * 0.30 +
    eq['pr_pb']     * 0.20 +
    eq['pr_upside'] * 0.15
)

# ── Trụ 3: QUALITY (30% weight) ───────────────────────────────
# Sức khoẻ tài chính → ROE cao, margin cao, nợ thấp, tăng trưởng dương
eq['pr_roe']      = pct_rank(eq['returnOnEquity'])
eq['pr_margin']   = pct_rank(eq['profitMargins'])
eq['pr_rev_gw']   = pct_rank(eq['revenueGrowth'])
eq['pr_debt']     = pct_rank(eq['debtToEquity'],  ascending=False)  # nợ thấp = tốt
eq['pr_roa']      = pct_rank(eq['returnOnAssets'])

eq['quality_idx'] = (
    eq['pr_roe']    * 0.30 +
    eq['pr_margin'] * 0.25 +
    eq['pr_roa']    * 0.20 +
    eq['pr_rev_gw'] * 0.15 +
    eq['pr_debt']   * 0.10
)

# ── Trụ 4: TECHNICAL SIGNAL (bonus, 0-5) ─────────────────────
eq['tech_score'] = (
    (eq['golden_cross'] == 1).astype(float) +
    (eq['macd_crossover'] == 'BULLISH').astype(float) +
    (eq['rsi_14'].between(40, 65)).astype(float) +
    (eq['bb_pct_b_norm'].between(0.3, 0.8)).astype(float) +
    (eq['price_vs_sma50_pct'] > 0).astype(float)
).fillna(0)
eq['pr_tech'] = eq['tech_score'] / 5.0 * 100

# ── COMPOSITE: 40% Momentum + 30% Value + 20% Quality + 10% Tech ──
eq['composite_new'] = (
    eq['momentum_idx'] * 0.40 +
    eq['value_idx']    * 0.30 +
    eq['quality_idx']  * 0.20 +
    eq['pr_tech']      * 0.10
).round(2)

print("\n[INFO] Composite score (new) distribution:")
print(eq['composite_new'].describe().round(2))
print(f"\nCorr with return_1y: {eq['composite_new'].corr(eq['return_1y_pct']):.3f}")
print(f"Corr old composite:  {eq['composite_score'].corr(eq['return_1y_pct']):.3f}")


# ══════════════════════════════════════════════════════════════
# 2. PHÂN LOẠI & GẮN NHÃN
# ══════════════════════════════════════════════════════════════
def classify(score):
    if score >= 72:   return 'STRONG BUY'
    elif score >= 58: return 'BUY'
    elif score >= 42: return 'HOLD'
    elif score >= 28: return 'UNDERPERFORM'
    else:             return 'SELL'

eq['rating']   = eq['composite_new'].apply(classify)
eq['stars']    = eq['composite_new'].apply(
    lambda s: '★★★★★' if s>=72 else '★★★★' if s>=58 else '★★★' if s>=42
              else '★★' if s>=28 else '★'
)

rating_dist = eq['rating'].value_counts()
print("\n[INFO] Rating distribution:")
print(rating_dist.to_string())


# ══════════════════════════════════════════════════════════════
# 3. STRATEGY SCREENERS (5 chiến lược)
# ══════════════════════════════════════════════════════════════
OUTPUT_COLS = ['ticker','asset_class','sector','rating','stars',
               'composite_new','momentum_idx','value_idx','quality_idx',
               'tech_score','rsi_14','macd_crossover','golden_cross',
               'trailingPE','priceToBook','returnOnEquity','profitMargins',
               'debtToEquity','revenueGrowth','analyst_consensus',
               'analyst_upside_pct','return_1m_pct','return_3m_pct',
               'return_1y_pct','sharpe_1y','volatility_30d_ann',
               'week52_zone','fear_greed_label','market_cap_tier']

# ── Strategy A: Quality Value ─────────────────────────────────
# Doanh nghiệp tốt + đang rẻ tương đối → Warren Buffett style
strat_a = eq[
    (eq['quality_idx'] >= eq['quality_idx'].quantile(0.65)) &
    (eq['value_idx']   >= eq['value_idx'].quantile(0.55)) &
    (eq['composite_new'] >= 45)
].sort_values('composite_new', ascending=False)[OUTPUT_COLS].reset_index(drop=True)

# ── Strategy B: Momentum Breakout ────────────────────────────
# Đang tăng mạnh + tín hiệu kỹ thuật đồng thuận → Trend following
strat_b = eq[
    (eq['momentum_idx'] >= eq['momentum_idx'].quantile(0.7)) &
    (eq['tech_score']   >= 3) &
    (eq['golden_cross'] == 1)
].sort_values('momentum_idx', ascending=False)[OUTPUT_COLS].reset_index(drop=True)

# ── Strategy C: GARP (Growth at Reasonable Price) ─────────────
# Tăng trưởng doanh thu > 10% + PE không quá đắt + quality tốt
strat_c = eq[
    (eq['revenueGrowth'].fillna(0) > 0.10) &
    (eq['trailingPE'].fillna(999) < 50) &
    (eq['quality_idx'] >= eq['quality_idx'].quantile(0.50)) &
    (eq['momentum_idx'] >= eq['momentum_idx'].quantile(0.40))
].sort_values('composite_new', ascending=False)[OUTPUT_COLS].reset_index(drop=True)

# ── Strategy D: Dividend + Stability ─────────────────────────
# Cổ tức ổn định + biến động thấp + PE hợp lý → Thu nhập thụ động
strat_d = eq[
    (eq['dividendYield'].fillna(0) > 0.02) &
    (eq['volatility_30d_ann'].fillna(999) < 30) &
    (eq['trailingPE'].fillna(999) < 30) &
    (eq['quality_idx'] >= eq['quality_idx'].quantile(0.45))
].sort_values('composite_new', ascending=False)[OUTPUT_COLS].reset_index(drop=True)

# ── Strategy E: Contrarian Oversold ──────────────────────────
# RSI oversold + analyst upside cao + quality không tệ → Mean reversion
strat_e = eq[
    (eq['rsi_14'] < 40) &
    (eq['analyst_upside_pct'].fillna(0) > 30) &
    (eq['quality_idx'] >= eq['quality_idx'].quantile(0.40)) &
    (eq['composite_new'] >= 35)
].sort_values('analyst_upside_pct', ascending=False)[OUTPUT_COLS].reset_index(drop=True)

print(f"\n[INFO] Screener results:")
print(f"  A — Quality Value:       {len(strat_a):3d} stocks")
print(f"  B — Momentum Breakout:   {len(strat_b):3d} stocks")
print(f"  C — GARP:                {len(strat_c):3d} stocks")
print(f"  D — Dividend Stability:  {len(strat_d):3d} stocks")
print(f"  E — Contrarian Oversold: {len(strat_e):3d} stocks")


# ══════════════════════════════════════════════════════════════
# 4. DASHBOARD CHART
# ══════════════════════════════════════════════════════════════
COLOR_BG    = '#FAFAF8'
C_BULL      = '#1D9E75'
C_BEAR      = '#D85A30'
C_NEUT      = '#888780'
C_BLUE      = '#185FA5'
C_AMBER     = '#BA7517'
C_PURPLE    = '#534AB7'
C_BORDER    = '#D3D1C7'

fig = plt.figure(figsize=(20, 16), facecolor=COLOR_BG)
fig.suptitle('Yahoo Finance 2026 — Investment Screener Dashboard',
             fontsize=17, fontweight='500', y=0.985, color='#2C2C2A')
gs = gridspec.GridSpec(3, 3, figure=fig,
                       hspace=0.45, wspace=0.35,
                       left=0.05, right=0.97, top=0.94, bottom=0.05)

# ── Panel 1: Rating Distribution ──────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor(COLOR_BG)
labels   = ['STRONG\nBUY', 'BUY', 'HOLD', 'UNDER-\nPERFORM', 'SELL']
counts   = [rating_dist.get(l.replace('\n',''), 0) for l in
            ['STRONG BUY','BUY','HOLD','UNDERPERFORM','SELL']]
colors   = [C_BULL,'#5DCAA5',C_NEUT,C_AMBER,C_BEAR]
bars = ax1.bar(labels, counts, color=colors, edgecolor='white',
               linewidth=0.5, width=0.6)
for bar, cnt in zip(bars, counts):
    if cnt > 0:
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
                 str(cnt), ha='center', fontsize=10, fontweight='500',
                 color='#2C2C2A')
ax1.set_title('Rating Distribution', fontsize=11, fontweight='500',
              color='#2C2C2A', pad=8)
ax1.set_ylabel('Số cổ phiếu', fontsize=9, color=C_NEUT)
ax1.spines[['top','right']].set_visible(False)
ax1.spines[['bottom','left']].set_color(C_BORDER)
ax1.tick_params(colors=C_NEUT, labelsize=8)
ax1.set_ylim(0, max(counts)*1.2)

# ── Panel 2: Composite Score Distribution ─────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor(COLOR_BG)
scores = eq['composite_new'].dropna()
n, bins, patches = ax2.hist(scores, bins=25, edgecolor='white', linewidth=0.4)
for patch, b in zip(patches, bins[:-1]):
    if b >= 72:   patch.set_facecolor(C_BULL)
    elif b >= 58: patch.set_facecolor('#5DCAA5')
    elif b >= 42: patch.set_facecolor(C_NEUT)
    elif b >= 28: patch.set_facecolor(C_AMBER)
    else:         patch.set_facecolor(C_BEAR)
for thresh, label, color in [(72,'Strong Buy',C_BULL),(58,'Buy','#5DCAA5'),
                               (42,'Hold',C_NEUT),(28,'Sell',C_BEAR)]:
    ax2.axvline(thresh, color=color, linewidth=1, linestyle='--', alpha=0.6)
ax2.set_title('Composite Score Distribution', fontsize=11, fontweight='500',
              color='#2C2C2A', pad=8)
ax2.set_xlabel('Composite Score (0–100)', fontsize=9, color=C_NEUT)
ax2.set_ylabel('Số cổ phiếu', fontsize=9, color=C_NEUT)
ax2.spines[['top','right']].set_visible(False)
ax2.spines[['bottom','left']].set_color(C_BORDER)
ax2.tick_params(colors=C_NEUT, labelsize=8)

# ── Panel 3: Composite Score vs Return 1Y ─────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax3.set_facecolor(COLOR_BG)
plot_df = eq[['composite_new','return_1y_pct','asset_class']].dropna()
ac_colors = {'US_MEGA': C_BLUE, 'US_MID': C_AMBER, 'INTL': C_PURPLE}
for ac, grp in plot_df.groupby('asset_class'):
    ax3.scatter(grp['composite_new'], grp['return_1y_pct'],
                c=ac_colors.get(ac, C_NEUT), s=22, alpha=0.65,
                edgecolors='white', linewidth=0.3, label=ac)
# Trend line
z = np.polyfit(plot_df['composite_new'], plot_df['return_1y_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(plot_df['composite_new'].min(), plot_df['composite_new'].max(), 100)
ax3.plot(x_line, p(x_line), color='#2C2C2A', linewidth=1.2,
         linestyle='--', alpha=0.5, label=f'Trend (r={plot_df["composite_new"].corr(plot_df["return_1y_pct"]):.2f})')
ax3.axhline(0, color=C_NEUT, linewidth=0.6, alpha=0.4)
ax3.set_title('Composite Score vs Return 1Y', fontsize=11, fontweight='500',
              color='#2C2C2A', pad=8)
ax3.set_xlabel('Composite Score', fontsize=9, color=C_NEUT)
ax3.set_ylabel('Return 1Y (%)', fontsize=9, color=C_NEUT)
ax3.legend(fontsize=7.5, frameon=False, labelcolor='#444441')
ax3.spines[['top','right']].set_visible(False)
ax3.spines[['bottom','left']].set_color(C_BORDER)
ax3.tick_params(colors=C_NEUT, labelsize=8)

# ── Panel 4: Sector Composite Heatmap ─────────────────────────
ax4 = fig.add_subplot(gs[1, :2])
ax4.set_facecolor(COLOR_BG)
sector_summary = eq.groupby('sector').agg(
    n=('ticker','count'),
    composite=('composite_new','mean'),
    momentum=('momentum_idx','mean'),
    value=('value_idx','mean'),
    quality=('quality_idx','mean'),
    ret_1y=('return_1y_pct','mean')
).round(1).sort_values('composite', ascending=False)

heat = sector_summary[['composite','momentum','value','quality','ret_1y']]
heat.columns = ['Composite','Momentum','Value','Quality','Return 1Y %']
heat_norm = (heat - heat.min()) / (heat.max() - heat.min() + 1e-9)

from matplotlib.colors import LinearSegmentedColormap
cmap_rg = LinearSegmentedColormap.from_list('rg',
    ['#FAECE7','#F0997B','#FAF0DA','#EAF3DE','#5DCAA5','#1D9E75'])
ax4.imshow(heat_norm.values, cmap=cmap_rg, aspect='auto', vmin=0, vmax=1)
ax4.set_xticks(range(len(heat.columns)))
ax4.set_xticklabels(heat.columns, fontsize=9, color='#2C2C2A', rotation=15, ha='right')
ax4.set_yticks(range(len(heat.index)))
ax4.set_yticklabels([f"{s}  (n={int(sector_summary.loc[s,'n'])})"
                      for s in heat.index], fontsize=8.5, color='#2C2C2A')
for i in range(len(heat.index)):
    for j in range(len(heat.columns)):
        v = heat.iloc[i, j]
        txt = f"{v:.0f}" if abs(v) >= 1 else f"{v:.2f}"
        brightness = heat_norm.iloc[i, j]
        tc = '#FFFFFF' if brightness > 0.6 else '#2C2C2A'
        ax4.text(j, i, txt, ha='center', va='center', fontsize=8, color=tc)
ax4.set_title('Sector Score Heatmap', fontsize=11, fontweight='500',
              color='#2C2C2A', pad=8)
ax4.spines[:].set_visible(False)
ax4.tick_params(length=0)

# ── Panel 5: Strategy Stock Count + Avg Return ────────────────
ax5 = fig.add_subplot(gs[1, 2])
ax5.set_facecolor(COLOR_BG)
strats      = ['Quality\nValue', 'Momentum\nBreakout', 'GARP', 'Dividend\nStability', 'Contrarian']
strat_dfs   = [strat_a, strat_b, strat_c, strat_d, strat_e]
strat_colors= [C_BLUE, C_BULL, C_PURPLE, C_AMBER, C_BEAR]
n_stocks = [len(s) for s in strat_dfs]
avg_ret  = [s['return_1y_pct'].mean() for s in strat_dfs]

x = np.arange(len(strats))
ax5b = ax5.twinx()
ax5.bar(x, n_stocks, color=strat_colors, alpha=0.25, width=0.55, edgecolor='white')
ax5b.plot(x, avg_ret, 'o-', color='#2C2C2A', linewidth=1.5, markersize=6,
          markerfacecolor='white', markeredgewidth=1.5)
for xi, ret in zip(x, avg_ret):
    ax5b.text(xi, ret + 1.5, f'{ret:.0f}%', ha='center', fontsize=8,
              color='#2C2C2A', fontweight='500')
ax5.set_xticks(x)
ax5.set_xticklabels(strats, fontsize=8, color=C_NEUT)
ax5.set_ylabel('Số cổ phiếu', fontsize=8.5, color=C_NEUT)
ax5b.set_ylabel('Avg Return 1Y (%)', fontsize=8.5, color=C_NEUT)
ax5.set_title('5 Chiến lược — Size & Return', fontsize=11, fontweight='500',
              color='#2C2C2A', pad=8)
ax5.spines[['top']].set_visible(False)
ax5b.spines[['top']].set_visible(False)
ax5.spines[['bottom','left']].set_color(C_BORDER)
ax5b.spines[['bottom','right']].set_color(C_BORDER)
ax5.tick_params(colors=C_NEUT, labelsize=8)
ax5b.tick_params(colors=C_NEUT, labelsize=8)

# ── Panel 6: Top 20 Stocks Ranking ───────────────────────────
ax6 = fig.add_subplot(gs[2, :])
ax6.set_facecolor(COLOR_BG)
ax6.axis('off')
top20 = eq.nlargest(20, 'composite_new')[
    ['ticker','sector','rating','composite_new',
     'momentum_idx','value_idx','quality_idx',
     'return_1y_pct','sharpe_1y','analyst_consensus']
].reset_index(drop=True)

ax6.set_title('Top 20 Cổ phiếu — Composite Score mới (40% Momentum · 30% Value · 20% Quality · 10% Technical)',
              fontsize=11, fontweight='500', color='#2C2C2A', pad=8, loc='left', x=0.01)

col_headers = ['#','Ticker','Sector','Rating',
               'Composite','Momentum','Value','Quality',
               'Return 1Y%','Sharpe','Analyst']
col_x   = [0.01, 0.05, 0.14, 0.30, 0.40, 0.49, 0.58, 0.67, 0.76, 0.85, 0.92]
row_h   = 0.86 / 21
header_y = 0.95

for ci, (ch, cx) in enumerate(zip(col_headers, col_x)):
    ax6.text(cx, header_y, ch, transform=ax6.transAxes,
             fontsize=8.5, fontweight='500', color='#2C2C2A',
             va='top', ha='left')

ax6.plot([0.01, 0.99], [header_y - 0.025, header_y - 0.025],
         color=C_BORDER, linewidth=0.8, transform=ax6.transAxes)

rating_colors = {'STRONG BUY': C_BULL, 'BUY': '#1D9E75',
                 'HOLD': C_NEUT, 'UNDERPERFORM': C_AMBER, 'SELL': C_BEAR}

for ri, row in top20.iterrows():
    y = header_y - (ri + 1) * row_h - 0.015
    bg = '#F1EFE8' if ri % 2 == 0 else COLOR_BG
    rect = mpatches.FancyBboxPatch((0.005, y - row_h*0.35), 0.99, row_h*0.82,
                                    boxstyle='round,pad=0.002',
                                    facecolor=bg, edgecolor='none',
                                    transform=ax6.transAxes, zorder=0)
    ax6.add_patch(rect)

    vals = [
        str(ri+1),
        row['ticker'],
        row['sector'][:18],
        row['rating'],
        f"{row['composite_new']:.1f}",
        f"{row['momentum_idx']:.0f}",
        f"{row['value_idx']:.0f}",
        f"{row['quality_idx']:.0f}",
        f"{row['return_1y_pct']:+.1f}%",
        f"{row['sharpe_1y']:.2f}" if pd.notna(row['sharpe_1y']) else '—',
        str(row['analyst_consensus']) if pd.notna(row['analyst_consensus']) else '—',
    ]
    for ci, (val, cx) in enumerate(zip(vals, col_x)):
        color = '#2C2C2A'
        fw = '400'
        if ci == 3:
            color = rating_colors.get(val, C_NEUT)
            fw = '500'
        elif ci == 8:
            color = C_BULL if row['return_1y_pct'] > 0 else C_BEAR
            fw = '500'
        elif ci == 1:
            fw = '500'
        ax6.text(cx, y, val, transform=ax6.transAxes,
                 fontsize=8, color=color, fontweight=fw, va='center', ha='left')

plt.savefig('screener_dashboard.png', dpi=150, bbox_inches='tight',
            facecolor=COLOR_BG, edgecolor='none')
print("\n[SAVED] screener_dashboard.png")


# ══════════════════════════════════════════════════════════════
# 5. EXPORT EXCEL — 6 SHEETS
# ══════════════════════════════════════════════════════════════
with pd.ExcelWriter('screener_results.xlsx', engine='openpyxl') as writer:
    eq.sort_values('composite_new', ascending=False)[OUTPUT_COLS + ['composite_new','momentum_idx','value_idx','quality_idx','stars']]\
      .to_excel(writer, sheet_name='All Stocks Ranked', index=False)

    strat_a.to_excel(writer, sheet_name='A — Quality Value',       index=False)
    strat_b.to_excel(writer, sheet_name='B — Momentum Breakout',   index=False)
    strat_c.to_excel(writer, sheet_name='C — GARP',                index=False)
    strat_d.to_excel(writer, sheet_name='D — Dividend Stability',  index=False)
    strat_e.to_excel(writer, sheet_name='E — Contrarian Oversold', index=False)

print("[SAVED] screener_results.xlsx (6 sheets)")

# ══════════════════════════════════════════════════════════════
# 6. SUMMARY PRINT
# ══════════════════════════════════════════════════════════════
print("\n" + "═"*65)
print("COMPOSITE SCORE MỚI — SO SÁNH VỚI GỐC")
print("═"*65)
print(f"Correlation với return_1y | Mới: {eq['composite_new'].corr(eq['return_1y_pct']):.3f}"
      f" | Gốc: {eq['composite_score'].corr(eq['return_1y_pct']):.3f}")

print("\n" + "═"*65)
print("TOP 15 — COMPOSITE SCORE MỚI")
print("═"*65)
print(eq.nlargest(15,'composite_new')[
    ['ticker','sector','rating','composite_new','momentum_idx',
     'value_idx','quality_idx','return_1y_pct','sharpe_1y']
].to_string(index=False))

print("\n" + "═"*65)
print("5 CHIẾN LƯỢC — TOP 5 MỖI CHIẾN LƯỢC")
print("═"*65)
for name, sdf in [('A Quality Value',strat_a),('B Momentum',strat_b),
                   ('C GARP',strat_c),('D Dividend',strat_d),('E Contrarian',strat_e)]:
    print(f"\n  [{name}]  ({len(sdf)} stocks, avg return 1Y = {sdf['return_1y_pct'].mean():.1f}%)")
    if len(sdf) > 0:
        print(sdf.head(5)[['ticker','sector','composite_new','return_1y_pct','analyst_consensus']].to_string(index=False))

print("\n[DONE] Bước 5 hoàn tất.")
