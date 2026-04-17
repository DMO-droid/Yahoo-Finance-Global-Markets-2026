"""
EDA & Data Cleaning — Yahoo Finance Global Markets 2026
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')


# LOAD DATA
df = pd.read_csv('yahoo_finance_global_markets_2026.csv')
df.head()
print(f"[INFO] Raw data: {df.shape[0]} rows × {df.shape[1]} cols\n")


---
# Issues 1 - Structural Missing Values Management

EQUITY_CLASSES   = ['US_MEGA', 'US_MID', 'INTL']
NONEQUITY_CLASSES = ['CRYPTO', 'ETF', 'FOREX', 'COMMODITIES', 'INDICES']

df_equity    = df[df['asset_class'].isin(EQUITY_CLASSES)].copy()
df_nonequity = df[df['asset_class'].isin(NONEQUITY_CLASSES)].copy()

print(f"  Equity (có fundamentals):     {len(df_equity):3d} rows")
print(f"  Non-equity (không có):        {len(df_nonequity):3d} rows")

# Kiểm tra null còn lại trong equity
equity_null = df_equity[['trailingPE','returnOnEquity','debtToEquity',
                          'revenueGrowth','beta']].isnull().mean() * 100
print("\n  Null % trong equity sau khi tách:")
print(equity_null.round(1).to_string())

# Chỉ với equity: điền median theo sector cho các cột kỹ thuật nhỏ
# (Không điền cột fundamental quan trọng — giữ NaN để biết thiếu)
FILL_MEDIAN_COLS = ['beta']
for col in FILL_MEDIAN_COLS:
    df_equity[col] = df_equity.groupby('sector')[col].transform(
        lambda x: x.fillna(x.median())
    )
    # fallback nếu cả sector đều null
    df_equity[col] = df_equity[col].fillna(df_equity[col].median())

print(f"\n  [FIX] 'beta' điền median theo sector. Còn lại giữ NaN.")

'''
  Equity (có fundamentals):     247 rows
  Non-equity (không có):        204 rows

  Null % trong equity sau khi tách:
trailingPE        21.1
returnOnEquity     3.6
debtToEquity      15.4
revenueGrowth      1.6
beta               0.8

  [FIX] 'beta' điền median theo sector. Còn lại giữ NaN.
'''

# Issues 2 - Economic Winsorization of Outliers

outlier_rules = {
    'trailingPE':  (0, 500),    # PE > 500: vô nghĩa kinh tế với equity
    'forwardPE':   (-50, 300),  # PE âm sâu: EPS dự báo âm, không thể so sánh
    'priceToBook': (-50, 100),  # P/B cực âm = accumulated deficit, cần flag riêng
    'debtToEquity':(0, 500),    # D/E > 500: ngân hàng có thể cao nhưng >1000 bất thường
    'returnOnEquity': (-2, 5),  # ROE > 500%: thường do equity rất nhỏ hoặc âm
}

for col, (lo, hi) in outlier_rules.items():
    if col in df_equity.columns:
        n_before = df_equity[col].between(lo, hi).sum()
        original = df_equity[col].copy()
        df_equity[f'{col}_raw'] = original          # giữ bản gốc
        df_equity[col] = df_equity[col].clip(lo, hi)
        n_clipped = (original != df_equity[col]).sum()
        print(f"  {col}: clip [{lo}, {hi}] — {n_clipped} giá trị bị winsorize")

# Flag riêng priceToBook âm (negative equity) để phân tích sau
df_equity['flag_negative_equity'] = (df_equity['priceToBook_raw'] < 0).astype(int)
neg_eq_count = df_equity['flag_negative_equity'].sum()
print(f"\n  [FLAG] {neg_eq_count} công ty có negative book equity (flag_negative_equity=1)")
print(f"  Tickers: {df_equity[df_equity['flag_negative_equity']==1]['ticker'].tolist()}")
---
'''
trailingPE: clip [0, 500] — 53 giá trị bị winsorize
forwardPE: clip [-50, 300] — 2 giá trị bị winsorize
priceToBook: clip [-50, 100] — 11 giá trị bị winsorize
debtToEquity: clip [0, 500] — 45 giá trị bị winsorize
returnOnEquity: clip [-2, 5] — 13 giá trị bị winsorize

[FLAG] 10 công ty có negative book equity (flag_negative_equity=1)
Tickers: ['ABBV', 'BKNG', 'BOX', 'DOCN', 'DOMO', 'EVGO', 'MCD', 'MCK', 'MO', 'ORLY']
'''

# Issues 3 - Temporal Data Standardization

date_cols = ['exDividendDate', 'lastFiscalYearEnd', 'mostRecentQuarter',
             'nextFiscalYearEnd', 'price_date']

for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
        null_after = df[col].isnull().sum()
        print(f"  {col}: → datetime64, {null_after} NaT (gốc là NaN hoặc format lỗi)")

# Áp dụng cho cả 2 tập con
for col in date_cols:
    if col in df_equity.columns:
        df_equity[col] = pd.to_datetime(df_equity[col], format='%d/%m/%Y', errors='coerce')
    if col in df_nonequity.columns:
        df_nonequity[col] = pd.to_datetime(df_nonequity[col], format='%d/%m/%Y', errors='coerce')

print("\n  [FIX] Tất cả cột ngày đã convert sang datetime64[ns]")

'''
exDividendDate: → datetime64, 299 NaT (gốc là NaN hoặc format lỗi)
lastFiscalYearEnd: → datetime64, 205 NaT (gốc là NaN hoặc format lỗi)
mostRecentQuarter: → datetime64, 205 NaT (gốc là NaN hoặc format lỗi)
nextFiscalYearEnd: → datetime64, 205 NaT (gốc là NaN hoặc format lỗi)
price_date: → datetime64, 2 NaT (gốc là NaN hoặc format lỗi)

[FIX] Tất cả cột ngày đã convert sang datetime64[ns]
'''


# Issues 4 - Mix Currencies

print(df['currency'].value_counts().to_string())

# Tạo flag để cảnh báo khi dùng giá tuyệt đối
df['is_usd'] = (df['currency'] == 'USD').astype(int)
non_usd = df[df['is_usd'] == 0][['ticker','currency','shortName']].head(10)
print(f"\n  [WARN] {(df['is_usd']==0).sum()} tài sản NON-USD — không so sánh giá trực tiếp")
print(f"  Dùng 'return_*_pct' hoặc 'market_cap_usd' cho cross-currency analysis")

# USX = cents (commodities như Cotton, Coffee) — đổi về USD
usx_tickers = df[df['currency'] == 'USX']['ticker'].tolist()
print(f"\n  [FIX] USX (cents) tickers: {usx_tickers}")
print(f"  → currentPrice của các tickers này cần ÷ 100 nếu so với USD")
df.loc[df['currency'] == 'USX', 'currentPrice'] = df.loc[
    df['currency'] == 'USX', 'currentPrice'] / 100
df.loc[df['currency'] == 'USX', 'currency'] = 'USD'

'''
currency
USD    420
AUD      6
EUR      5
KRW      4
CHF      3
INR      2
NGN      1
BRL      1
GBP      1
HKD      1
IDR      1
MXN      1
JPY      1
SGD      1
ILS      1
TWD      1

  [WARN] 31 tài sản NON-USD — không so sánh giá trực tiếp
  Dùng 'return_*_pct' hoặc 'market_cap_usd' cho cross-currency analysis

  [FIX] USX (cents) tickers: []
  → currentPrice của các tickers này cần ÷ 100 nếu so với USD
'''



# Issues 5 - Identification of Leveraged & Extreme Returns

extreme_return = df[df['return_1y_pct'].abs() > 100].copy()
print(f"  Số tài sản có |return_1y| > 100%: {len(extreme_return)}")
print(extreme_return[['ticker','asset_class','return_1y_pct']].to_string())

df['flag_leveraged_or_extreme'] = (df['return_1y_pct'].abs() > 100).astype(int)
print(f"\n  [FLAG] Đã tạo 'flag_leveraged_or_extreme' — loại khỏi phân tích return thông thường")
print(f"  [TIP] Khi vẽ phân phối return, dùng: df[df['flag_leveraged_or_extreme']==0]")

'''
Số tài sản có |return_1y| > 100%: 24
        ticker  asset_class  return_1y_pct
0    000660.KS         INTL         187.40
1    005930.KS         INTL         138.61
21        AMAT      US_MEGA         108.88
22         AMD      US_MEGA         115.19
47     BAL-USD       CRYPTO        -133.91
76         CAT      US_MEGA         100.87
122       DOCN       US_MID         140.39
130       EDIT       US_MID         144.08
138    EOS-USD       CRYPTO        -177.16
156   FLOW-USD       CRYPTO        -154.14
160       FSLY       US_MID         234.44
216       KLAC      US_MEGA         104.17
219       LABD          ETF        -168.83
220       LABU          ETF         173.01
227       LRCX      US_MEGA         139.64
266       NTLA       US_MID         123.45
273     OP-USD       CRYPTO        -114.82
294       PRME       US_MID         152.30
330       SI=F  COMMODITIES         109.96
333        SLV          ETF         105.71
343       SOXL          ETF         236.52
344       SOXS          ETF        -236.17
362  THETA-USD       CRYPTO        -103.48
364    TIA-USD       CRYPTO        -148.75

  [FLAG] Đã tạo 'flag_leveraged_or_extreme' — loại khỏi phân tích return thông thường
  [TIP] Khi vẽ phân phối return, dùng: df[df['flag_leveraged_or_extreme']==0]
'''


# Issues 6 - NON-EQUITY no sector

print(f"  Sector null trong non-equity: {df_nonequity['sector'].isnull().sum()}/{len(df_nonequity)}")

# Điền sector placeholder
df_nonequity['sector'] = df_nonequity['sector'].fillna(
    df_nonequity['asset_class'].map({
        'ETF':         'ETF',
        'CRYPTO':      'Crypto',
        'FOREX':       'Forex',
        'COMMODITIES': 'Commodities',
        'INDICES':     'Indices',
    })
)
print("  [FIX] sector điền từ asset_class cho non-equity")
print(f"  [WARN] Không dùng sector này cho sector rotation analysis")
print(f"  Distribution sau fix:\n{df_nonequity['sector'].value_counts().to_string()}")

'''
Sector null trong non-equity: 204/204
  [FIX] sector điền từ asset_class cho non-equity
  [WARN] Không dùng sector này cho sector rotation analysis
  Distribution sau fix:
sector
ETF            87
Crypto         43
Forex          30
Indices        26
Commodities    18
'''


# Issues 7 - Extremely Negative Profit Margins & Invalid ROE

# profitMargins < -50% = lỗ nặng, ảnh hưởng quality_score
extreme_loss = df_equity[df_equity['profitMargins'] < -0.5]
print(f"  Công ty lỗ nặng (margin < -50%): {len(extreme_loss)}")
if len(extreme_loss) > 0:
    print(extreme_loss[['ticker','sector','profitMargins','returnOnEquity']].to_string())

# ROE cực cao do negative equity hoặc buyback
extreme_roe = df_equity[df_equity['returnOnEquity'] > 2]  # >200%
print(f"\n  ROE > 200% (extreme buyback / tiny equity): {len(extreme_roe)}")
if len(extreme_roe) > 0:
    print(extreme_roe[['ticker','returnOnEquity','flag_negative_equity']].to_string())

df_equity['flag_extreme_margins'] = (
    (df_equity['profitMargins'] < -0.5) |
    (df_equity['returnOnEquity'] > 2)
).astype(int)
print(f"\n  [FLAG] 'flag_extreme_margins' — cẩn thận khi dùng trong scoring")



# SUMMARY REPORT
print("\n" + "=" * 60)
print("TỔNG KẾT SAU CLEANING")
print("=" * 60)
print(f"  df_equity:    {len(df_equity)} rows | Equity thuần tuý (US + INTL)")
print(f"  df_nonequity: {len(df_nonequity)} rows | ETF, Crypto, Forex, Commodities, Indices")

print("\n  Flags đã tạo:")
flags = [c for c in df_equity.columns if c.startswith('flag_')]
for f in flags:
    print(f"  - {f}: {df_equity[f].sum()} rows flagged")

print("\n  Cột raw (giữ bản gốc trước winsorize):")
raw_cols = [c for c in df_equity.columns if c.endswith('_raw')]
print(f"  {raw_cols}")

'''
Công ty lỗ nặng (margin < -50%): 7
    ticker             sector  profitMargins  returnOnEquity
53    BEAM         Healthcare       -0.57242        -0.08113
59    BLNK        Industrials       -0.80550        -0.91036
84    CHPT  Consumer Cyclical       -0.53547        -2.00000
202   INVZ  Consumer Cyclical       -1.23064        -0.86558
221   LCID  Consumer Cyclical       -1.99296        -0.66020
307   RIVN  Consumer Cyclical       -0.67681        -0.65005
402   WOLF         Technology       -0.91641        -1.37040

  ROE > 200% (extreme buyback / tiny equity): 4
    ticker  returnOnEquity  flag_negative_equity
5     ABBV         5.00000                     1
29     APP         2.12945                     0
88      CL         4.97470                     0
230     MA         2.09915                     0

  [FLAG] 'flag_extreme_margins' — cẩn thận khi dùng trong scoring
'''


# Lưu output
df_equity.to_csv('df_equity_cleaned.csv', index=False)
df_nonequity.to_csv('df_nonequity_cleaned.csv', index=False)
print("\n  [SAVED] df_equity_cleaned.csv")
print("  [SAVED] df_nonequity_cleaned.csv")
print("\n[DONE] EDA cleaning hoàn tất.")
