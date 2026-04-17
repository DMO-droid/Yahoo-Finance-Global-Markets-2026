# EDA report
>EDA and data cleaning pipeline for the 2026 Yahoo Finance global markets dataset. The primary goal was to transform noisy, inconsistently formatted raw data into a "Gold Standard" dataset ready for Quantitative Analysis and high-fidelity dashboard visualization

## Data Cleaning Strategy - 7 Key Issues Addressed

1. **Structural Missing Values Management**
   * **Observation:** Approximately 45–68% null values were found in fundamental columns such as PE, ROE, and Debt-to-Equity
   * **Root Cause:** The dataset aggregates diverse asset classes (Crypto, Forex, Commodities) that do not possess corporate financial metrics
   * **Solution:** Segregated the data into two specialized subsets: df_equity (US & International stocks) and df_nonequity (ETFs, Crypto, Forex, etc.) to prevent statistical bias

2. **Economic Winsorization of Outliers**
   * **Observation:** Extreme outliers were detected, such as trailing PE ratios exceeding 3,000 or highly negative P/B ratios
   * **Solution:** Implemented Winsorization (clipping) based on logical economic thresholds rather than raw deletion to preserve technical price data
     * *trailingPE: Clipped to [0, 500]*
     * *forwardPE: Clipped to [-50, 300]*
     * *returnOnEquity: Clipped to [-2, 5]*

3. **Temporal Data Standardization**
   * **Observation:** Date columns (e.g., exDividendDate, price_date) were stored as strings in 'DD/MM/YYYY' format
   * **Solution:** Converted all temporal features to datetime64[ns] to enable time-series sorting and period-based filtering

4. **Mix Currencies**
   * **Observation:** The dataset contains assets priced in various currencies (KRW, JPY, INR, USX), making direct price comparisons invalid
   * **Solution:**
     * *Converted USX (Cents) prices to USD (dividing by 100)*
     * *Flagged non-USD assets to warn users against direct price comparisons in cross-currency analysis*

5. **Identification of Leveraged & Extreme Returns**
   * **Observation:** Certain assets (Leveraged ETFs and Crypto) showed 1-year returns exceeding +/- 100%
   * **Solution:** Created a flag_leveraged_or_extreme feature to exclude these anomalies when analyzing the normal distribution of market returns

6. **NON-EQUITY no sector**
   * **Observation:** Non-equity assets (Indices, Commodities) lacked sector classifications
   * **Solution:** Mapped sector values directly from the asset_class for non-equities to ensure data integrity during dashboard grouping operations

7. **Extremely Negative Profit Margins & Invalid ROE**
   * **Observation:** Anomalies like negative equity (from heavy buybacks) or extreme losses were identified
   * **Solution:** Engineered a flag_extreme_margins feature to identify companies with profit margins < -50% or ROE > 200%, allowing for easy risk-filtering in investment strategies

---

## 📊 Dashboard Insights & Results
The finalized EDA resulted in a high-performance Investment Screener Dashboard:

1. Rating Distribution: The market sentiment appears bearish/cautious, with Sell (90) and Hold (75) ratings dominating the landscape
2. Composite Score vs. Return: A strong positive correlation ($r = 0.67$) was established between the engineered Composite Score and 1-year returns
3. Sector Strength: Heatmap analysis indicates that Energy and Basic Materials currently hold the highest Momentum and Composite scores
4. Top 20 Picks: The "Top 20 Cổ phiếu" table

<p align="center" width="100%">
<img src="./images/EDA_report.png" alt="EDA report" style="width: 70%; min-width: 300px; display: block; margin: auto;">
</p>

