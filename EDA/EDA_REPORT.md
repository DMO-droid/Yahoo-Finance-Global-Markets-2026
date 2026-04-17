# Exploratory Data Analysis Report
## Yahoo Finance Global Markets 2026

> **Dataset:** 451 tickers · 131 columns · April 2025 - April 2026  
> **Scope:** 8 asset classes - US Equities, International Equities, ETFs, Crypto, Forex, Commodities, Indices, REITs  
> **Objective:** Transform raw, heterogeneous financial data into a clean, analysis-ready "Gold Standard" dataset for quantitative modelling and dashboard visualisation

---

## Table of Contents

1. [Dataset Overview](#1-dataset-overview)
2. [Data Quality Assessment](#2-data-quality-assessment)
3. [Cleaning Methodology](#3-cleaning-methodology)
   - 3.1 Structural Missing Values
   - 3.2 Outlier Treatment via Economic Winsorisation
   - 3.3 Temporal Standardisation
   - 3.4 Multi-Currency Normalisation
   - 3.5 Leveraged & Extreme-Return Flagging
   - 3.6 Non-Equity Sector Classification
   - 3.7 Extreme Margin & Invalid ROE Flagging
4. [Engineered Features](#4-engineered-features)
5. [Key Findings & Implications](#5-key-findings--implications)

---

## 1. Dataset Overview

| Attribute | Detail |
|---|---|
| Source | Yahoo Finance (scraped April 2025 – April 2026) |
| Universe | 451 tickers across 8 asset classes |
| Columns | 131 raw features (price, fundamentals, returns, metadata) |
| License | CC0 (Public Domain) |
| Base Currency | USD (post-normalisation) |

The dataset intentionally spans multiple asset classes to support a cross-market Alpha Scoring model. This heterogeneity is the primary driver of data quality challenges addressed below

---

## 2. Data Quality Assessment

Seven distinct data quality issues were identified and prioritised by severity:

| # | Issue | Severity | Root Cause |
|---|---|---|---|
| 1 | Structural Missing Values | 🔴 Critical | Mixed asset classes - non-equities lack corporate fundamentals |
| 2 | Statistical Outliers | 🔴 Critical | Extreme ratios from distressed/high-growth firms |
| 3 | Temporal Inconsistency | 🟠 High | Dates stored as strings in `DD/MM/YYYY` format |
| 4 | Multi-Currency Pricing | 🟠 High | Assets priced in KRW, JPY, INR, USX alongside USD |
| 5 | Non-Equity Sector Gaps | 🟠 High | Indices and Commodities lack sector classifications |
| 6 | Extreme Margins / Invalid ROE | 🟠 High | Negative equity from aggressive share buybacks |
| 7 | Leveraged & Extreme Returns | 🟡 Moderate | Leveraged ETFs and Crypto with ±100%+ annual returns |

---

## 3. Cleaning Methodology

### 3.1 Structural Missing Values - 🔴 Critical

**Observation:** Fundamental columns (`trailingPE`, `returnOnEquity`, `debtToEquity`, `priceToBook`) exhibited 45-68% null rates across the full dataset

**Root Cause:** The dataset mixes asset classes. Crypto, Forex, Commodities, and Indices have no corporate balance sheets, so fundamental metrics are structurally absent - not data errors

**Resolution:**

```python
df_equity     = df[df['asset_class'].isin(['US Stock', 'International Stock', 'REIT'])]
df_nonequity  = df[~df.index.isin(df_equity.index)]
```

The dataset was partitioned into two sub-frames:
- **`df_equity`** - stocks and REITs with valid fundamental data; missing values imputed using sector medians
- **`df_nonequity`** - ETFs, Crypto, Forex, Commodities, Indices; fundamental columns intentionally left null

> This partition is the foundational step. All subsequent fundamental analysis operates exclusively on `df_equity`

---

### 3.2 Outlier Treatment via Economic Winsorisation - 🔴 Critical

**Observation:** Extreme ratio values were detected across key valuation metrics:
- `trailingPE` reaching values above 3,000 (loss-making firms with minimal earnings)
- `priceToBook` turning deeply negative (firms with negative book equity)
- `returnOnEquity` exceeding 500% (aggressive buyback distortion)

**Approach:** Values were **clipped** (winsorised), not deleted. Deletion would discard valid price and return data attached to the same row

| Column | Lower Bound | Upper Bound | Rationale |
|---|---|---|---|
| `trailingPE` | 0 | 500 | Negative PE is economically meaningless; >500 is noise |
| `forwardPE` | −50 | 300 | Allows for near-term loss expectations |
| `returnOnEquity` | −2 (−200%) | 5 (500%) | Captures distressed and buyback-heavy firms |

```python
df_equity['trailingPE']     = df_equity['trailingPE'].clip(0, 500)
df_equity['forwardPE']      = df_equity['forwardPE'].clip(-50, 300)
df_equity['returnOnEquity'] = df_equity['returnOnEquity'].clip(-2, 5)
```

---

### 3.3 Temporal Standardisation - 🟠 High

**Observation:** Date columns were stored as plain strings in `DD/MM/YYYY` format, preventing time-series operations, period filtering, and chronological sorting

**Resolution:**

```python
df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
# dtype: datetime64[ns]
```

All date fields were converted to `datetime64[ns]`, enabling `.resample()`, `.dt.year`, and date-range slicing throughout the pipeline

---

### 3.4 Multi-Currency Normalisation — 🟠 High

**Observation:** Price columns contained values denominated in multiple currencies without explicit labelling:

| Currency | Affected Assets | Issue |
|---|---|---|
| KRW (Korean Won) | Korean equities | ~1,300× scale vs USD |
| JPY (Japanese Yen) | Japanese equities | ~150× scale vs USD |
| INR (Indian Rupee) | Indian equities | ~83× scale vs USD |
| USX (US Cents) | Some US-listed instruments | 100× scale vs USD |

**Resolution:**
- **USX → USD:** Divided by 100 where `currency == 'USX'`
- **Non-USD assets:** Flagged with `flag_non_usd = True` to prevent invalid cross-currency price comparisons

> Direct price comparisons across currencies are disabled by design. All cross-market comparisons use percentage returns or USD-denominated market capitalisation

---

### 3.5 Leveraged & Extreme-Return Flagging - 🟡 Moderate

**Observation:** A subset of assets - primarily leveraged ETFs (2×/3× products) and Crypto — exhibited 1-year returns exceeding ±100%, distorting return distribution analysis

**Resolution:** A binary flag was engineered rather than removing these assets:

```python
df['flag_leveraged_or_extreme'] = (
    (df['1Y_return'].abs() > 1.0) |
    (df['asset_class'].isin(['Crypto', 'Leveraged ETF']))
).astype(int)
```

This preserves the full dataset while allowing analysts to exclude these instruments from standard return distribution studies with a single filter

---

### 3.6 Non-Equity Sector Classification - 🟠 High

**Observation:** Indices and Commodities lacked `sector` values, causing null groupings in sector-level dashboard visualisations

**Resolution:** Sector labels were mapped directly from `asset_class` for non-equity instruments:

```python
sector_map = {
    'Index':     'Market Index',
    'Commodity': 'Commodities',
    'Forex':     'Currency',
    'Crypto':    'Digital Assets',
    'ETF':       'Fund / ETF',
}
df.loc[df['sector'].isna(), 'sector'] = df['asset_class'].map(sector_map)
```

This ensures complete sector coverage for all 451 tickers in dashboard groupings

---

### 3.7 Extreme Margin & Invalid ROE Flagging - 🟠 High

**Observation:** Certain equities showed anomalous profitability metrics:
- **Profit margin < -50%:** Deep operating losses (distressed firms, early-stage biotech)
- **ROE > 200%:** Mathematically valid but economically misleading - typically caused by near-zero or negative book equity from aggressive share buybacks (e.g., mature consumer staples)

**Resolution:**

```python
df_equity['flag_extreme_margins'] = (
    (df_equity['profitMargins'] < -0.50) |
    (df_equity['returnOnEquity'] > 2.0)
).astype(int)
```

This flag enables risk-based filtering in downstream investment strategies without discarding the underlying data

---

## 4. Engineered Features

The cleaning process produced three binary risk flags appended to the dataset:

| Feature | Type | Description |
|---|---|---|
| `flag_non_usd` | Binary (0/1) | Asset priced in a non-USD currency |
| `flag_leveraged_or_extreme` | Binary (0/1) | Leveraged product or return exceeding ±100% |
| `flag_extreme_margins` | Binary (0/1) | Profit margin < -50% or ROE > 200% |

These flags serve as first-class filter inputs for all downstream screener and scoring modules

---

## 5. Key Findings & Implications

| Finding | Implication for Analysis |
|---|---|
| 45–68% null rate in fundamentals is **by design**, not data corruption | Do not impute fundamentals for non-equity assets; partition first |
| Extreme PE ratios (>500) are concentrated in loss-making micro-caps | Winsorise before any valuation scoring to avoid rank distortion |
| USX-denominated prices are 100× overstated vs USD | Always normalise currency before any price-level comparison |
| Leveraged ETF and Crypto returns dominate the return distribution tail | Exclude `flag_leveraged_or_extreme == 1` from return percentile ranking |
| High ROE from buybacks ≠ operational quality | Use `flag_extreme_margins` to separate genuine quality from financial engineering |

---

*Report generated as part of the Yahoo Finance Global Markets 2026 quantitative pipeline*  
*Pipeline stack: Python · Pandas · NumPy*
