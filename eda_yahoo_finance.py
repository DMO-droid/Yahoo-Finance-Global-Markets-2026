"""
EDA & Data Cleaning — Yahoo Finance Global Markets 2026
=======================================================
Phát hiện và xử lý 7 vấn đề chính trong bộ dữ liệu.
Chạy: python eda_yahoo_finance.py
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# LOAD DATA
# ============================================================
df = pd.read_csv('yahoo_finance_global_markets_2026.csv')
print(f"[INFO] Raw data: {df.shape[0]} rows × {df.shape[1]} cols\n")


# ============================================================
# VẤN ĐỀ 1 — MISSING VALUES CÓ CẤU TRÚC (KHÔNG PHẢI LỖI)
# ============================================================
# LÝ DO: ~45–68% null ở cột cơ bản (PE, ROE, debtToEquity...)
# KHÔNG phải lỗi — CRYPTO, FOREX, COMMODITIES, INDICES không có
# chỉ số tài chính doanh nghiệp. Điền 0 hay mean sẽ SAI hoàn toàn.
# GIẢI PHÁP: Tách thành 2 tập phân tích riêng biệt.

EQUITY_CLASSES   = ['US_MEGA', 'US_MID', 'INTL']
NONEQUITY_CLASSES = ['CRYPTO', 'ETF', 'FOREX', 'COMMODITIES', 'INDICES']

df_equity    = df[df['asset_class'].isin(EQUITY_CLASSES)].copy()
df_nonequity = df[df['asset_class'].isin(NONEQUITY_CLASSES)].copy()

print("=" * 60)
print("VẤN ĐỀ 1 — MISSING VALUES CÓ CẤU TRÚC")
print("=" * 60)
print(f"  Equity (có fundamentals):     {len(df_equity):3d} rows")
print(f"  Non-equity (không có):        {len(df_nonequity):3d} rows")

# Kiểm tra null còn lại trong equity
equity_null = df_equity[['trailingPE','returnOnEquity','debtToEquity',
                          'revenueGrowth','beta']].isnull().mean() * 100
print("\n  Null % trong equity sau khi tách:")
print(equity_null.round(1).to_string())

# Chỉ với equity: điền median theo sector cho các cột kỹ thuật nhỏ
# (không điền cột fundamental quan trọng — giữ NaN để biết thiếu)
FILL_MEDIAN_COLS = ['beta']
for col in FILL_MEDIAN_COLS:
    df_equity[col] = df_equity.groupby('sector')[col].transform(
        lambda x: x.fillna(x.median())
    )
    # fallback nếu cả sector đều null
    df_equity[col] = df_equity[col].fillna(df_equity[col].median())

print(f"\n  [FIX] 'beta' điền median theo sector. Còn lại giữ NaN.")


# ============================================================
# VẤN ĐỀ 2 — OUTLIERS CỰC ĐOAN TRONG CHỈ SỐ ĐỊNH GIÁ
# ============================================================
# LÝ DO:
#   - trailingPE = 3739 (SHY — ETF trái phiếu ngắn hạn, PE vô nghĩa)
#   - forwardPE = -4329 (TLT — ETF bond, EPS âm làm PE âm)
#   - priceToBook = -283 (DOCN — accumulated deficit > equity, kỹ thuật hợp lệ
#     nhưng gây nhiễu nếu dùng P/B để filter)
# GIẢI PHÁP: Winsorize (clip) theo ngưỡng kinh tế học hợp lý.
# KHÔNG xóa dòng — mất dữ liệu giá, kỹ thuật vẫn dùng được.

print("\n" + "=" * 60)
print("VẤN ĐỀ 2 — OUTLIERS TRONG CHỈ SỐ ĐỊNH GIÁ")
print("=" * 60)

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


# ============================================================
# VẤN ĐỀ 3 — KIỂU DỮ LIỆU SAI: CỘT NGÀY LÀ STRING
# ============================================================
# LÝ DO: exDividendDate, lastFiscalYearEnd, price_date là object (string).
# Format: 'DD/MM/YYYY' (không phải ISO). Không thể tính khoảng cách thời gian,
# sort theo thời gian, hay lọc "cổ tức sau ngày X" nếu giữ nguyên string.

print("\n" + "=" * 60)
print("VẤN ĐỀ 3 — KIỂU DỮ LIỆU SAI: CỘT NGÀY")
print("=" * 60)

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
print(f"  Ví dụ price_date: {df['price_date'].dropna().head(3).tolist()}")


# ============================================================
# VẤN ĐỀ 4 — ĐA TIỀN TỆ: KHÔNG THỂ SO SÁNH GIÁ TRỰC TIẾP
# ============================================================
# LÝ DO: KRW (Korea), INR (India), JPY (Japan) có đơn vị giá khác nhau
# hoàn toàn. Samsung giá 186,200 KRW nhưng không có nghĩa đắt hơn Apple
# giá $255. Nếu dùng currentPrice để vẽ histogram hay so sánh → vô nghĩa.
# GIẢI PHÁP: Thêm cột market_cap_usd (đã có sẵn) làm chuẩn so sánh.
# Với các phân tích cần giá, dùng return (%) thay vì price tuyệt đối.

print("\n" + "=" * 60)
print("VẤN ĐỀ 4 — ĐA TIỀN TỆ")
print("=" * 60)
print("  Phân phối tiền tệ:")
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


# ============================================================
# VẤN ĐỀ 5 — RETURN 1Y CÓ GIÁ TRỊ ÂM DƯỚI -100% (BẤT KHẢ THI)
# ============================================================
# LÝ DO: return_1y_pct = -133%, -177%, -236% là bất khả thi với cổ phiếu
# thông thường (max loss = -100%). Nguyên nhân: leveraged ETF (SOXS/SOXL)
# dùng đòn bẩy 3x tính NAV, hoặc crypto tính theo giá gốc rất thấp.
# SOXS = -236%, SOXL = +236% (đối nghịch nhau, đúng về bản chất đòn bẩy).
# GIẢI PHÁP: Không xóa — đây là dữ liệu hợp lệ cho leveraged products.
# Thêm flag và tách ra khi phân tích normal distribution của returns.

print("\n" + "=" * 60)
print("VẤN ĐỀ 5 — RETURN BẤT THƯỜNG (LEVERAGED/CRYPTO)")
print("=" * 60)

extreme_return = df[df['return_1y_pct'].abs() > 100].copy()
print(f"  Số tài sản có |return_1y| > 100%: {len(extreme_return)}")
print(extreme_return[['ticker','asset_class','return_1y_pct']].to_string())

df['flag_leveraged_or_extreme'] = (df['return_1y_pct'].abs() > 100).astype(int)
print(f"\n  [FLAG] Đã tạo 'flag_leveraged_or_extreme' — loại khỏi phân tích return thông thường")
print(f"  [TIP] Khi vẽ phân phối return, dùng: df[df['flag_leveraged_or_extreme']==0]")


# ============================================================
# VẤN ĐỀ 6 — NON-EQUITY KHÔNG CÓ SECTOR (NULL 100%)
# ============================================================
# LÝ DO: ETF, FOREX, COMMODITIES, INDICES không có sector vì đây
# không phải cổ phiếu đơn lẻ. Nếu group-by sector sẽ bỏ sót 161 rows.
# GIẢI PHÁP: Điền sector = asset_class cho non-equity để giữ trong
# phân tích tổng quan, nhưng KHÔNG dùng cho phân tích sector rotation.

print("\n" + "=" * 60)
print("VẤN ĐỀ 6 — SECTOR NULL VỚI NON-EQUITY")
print("=" * 60)

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


# ============================================================
# VẤN ĐỀ 7 — PROFIT MARGINS ÂM CỰC ĐOAN & ROE KHÔNG HỢP LỆ
# ============================================================
# LÝ DO: profitMargins = -1.99 (thua lỗ nặng, có thể hợp lệ nhưng
# cần kiểm tra). ROE = 6225% (ABBV) do shareholders' equity rất nhỏ
# sau buyback khổng lồ — kỹ thuật hợp lệ nhưng gây bias nếu dùng
# ROE để so sánh toàn thị trường.
# GIẢI PHÁP: Flag các cases đặc biệt, không xóa.

print("\n" + "=" * 60)
print("VẤN ĐỀ 7 — MARGIN VÀ ROE BẤT THƯỜNG")
print("=" * 60)

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


# ============================================================
# SUMMARY REPORT
# ============================================================
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

# Lưu output
df_equity.to_csv('df_equity_cleaned.csv', index=False)
df_nonequity.to_csv('df_nonequity_cleaned.csv', index=False)
print("\n  [SAVED] df_equity_cleaned.csv")
print("  [SAVED] df_nonequity_cleaned.csv")
print("\n[DONE] EDA cleaning hoàn tất.")
