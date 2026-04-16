# Yahoo-Finance-Global-Markets-2026

## 📌 Project Overview
Analyze the Yahoo Finance 2026 dataset to build an Alpha Scoring model based on the factors of Value, Quality and Momentum

## 🔥 Dataset Overview
**Name:** yahoo_finance_global_markets_2026
**Link:** https://www.kaggle.com/datasets/kanchana1990/yahoo-finance-global-markets-intelligence-2026/data

| Attribute | Value |
| :--- | :--- |
| **Tickers** | 451 |
| **Columns** | 131 |
| **Asset Classes** | 8 |
| **Price History** | 1 Year (April 2025 – April 2026) |
| **Source** | [Yahoo Finance (yfinance)](https://finance.yahoo.com/) |
| **FX Normalised** | Market caps converted to USD |
| **License** | [CC0: Public Domain](https://creativecommons.org/publicdomain/zero/1.0/) |

---

### Technical Specs
![Tickers](https://img.shields.io/badge/Tickers-451-blue)
![Columns](https://img.shields.io/badge/Columns-131-green)
![License](https://img.shields.io/badge/License-CC0-orange)

## 🛠 Tech Stack
* **Programming Language:** Python
* **Data Manipulation:** Pandas, Numpy
* **Support Library:** Warnings

## 📈 Methodology & Pipeline
1. **Data Segmentation:**
   Devine the dataset into two separate parts: Equity (Stocks - With underlying data) and Non-equity (Crypto, Forex, ETFs, etc. - Without corporate financial indices)
2. **Handling Missing Values:**
   * Fill in the median value for each sectors to avoid industry-specific biases
   * Retain NaN values in important columns to ensure data integrity
3. **Outlier Management:**
   Use the Clip method for indicators such as P/E, P/B and D/E. RETAIN the data flow but remove noise from extreme values
4. **Standardization:**
   * Datetime: Converts the date format from string to datetime64
   * Currency: Converts small currency unit to USD for consistent value
   * Feature engineering: Creates flag_* cloumns to mark special cases


## 💡 Key Discovories & Business Insights
1. **Asymmetrical nature of financial ratios:** The absence of blank Fundamental columns is not a system error but rather due to the nature of the assets. The principles of stock valuation cannot be applied to Crypto or Commodities
2. **Leveraged Effect:** Detects stocks with returns > 100% or < -100%. This is a crucial insight to warn investors about the risks of derivative/3x leveraged products
3. **Capital Structure Risk Warning:** Detects companies with negative equity or extremely high ROE due to excessive buybacks. This helps filter out "artificially healthy" companies when running the Scoring model
4. **Currency Bias:** Recognizing that absolute price comparisons between markets are meaningless, it suggests using Return (%) or Market Cap (USD) as a common benchmark

---

# EDA & Data Cleaning
Identify and address 7 key issues in the dataset

| Key issue | Severity level |
| :--- | :--- |
| **Missing Values** | 🔴 Serious |
| **OUTLIERS** | 🔴 Serious |
| **Incorrect Data Type** | 🟠 Important |
| **Mix Currencies** | 🟠 Important |
| **Return 1Y has a negative value below -100% (Impossible)** | 🟡 Moderate |
| **NON-EQUITY no sector (NULL 100%)** | 🟠 Important |
| **Extremely Negative Profit Margins & Invalid ROE** | 🟠 Important |
