# Report: Investment Screener & Composite Scoring System
> Rebuild a fair Composite Scoring system and filter optimized stock portfolios across five distinct investment strategies

## Core Functional Modules
**Redesigning the Composite Score**
> The original score was heavily biased toward momentum. This script addresses the issue by normalizing all metrics using Percentile Ranking (0–100) before calculating the weighted average:
* **Momentum Index (40%):** Prioritizes stocks with strong price trends and high Sharpe ratios
* **Value Index (30%):** Targets undervalued stocks based on PE, PB, and analyst upside potential
* **Quality Index (20%):** Evaluates financial health through ROE, profit margins, and debt management
* **Technical Signal (10%):** Bonus points derived from indicators like Golden Cross and MACD

**Five Specialized Investment Strategies**
> The system automatically categorizes stocks into strategic buckets:
* **Quality Value:** High-quality businesses trading at a discount (Warren Buffett style)
* **Momentum Breakout:** Stocks with strong upward velocity and technical confirmation
* **GARP (Growth at Reasonable Price):** Revenue growth >10% paired with reasonable PE ratios
* **Dividend Stability:** High yield (>2%) and low volatility, ideal for passive income
* **Contrarian Oversold:** Mean-reversion play for oversold stocks (RSI < 40) with high analyst upside

---

## 📊 Key Outputs
1. *screener_dashboard.png*: A comprehensive visual dashboard featuring rating distributions, sector heatmaps, and a Top 20 ranking table
2. *screener_results.xlsx*: A professional Excel report containing 6 detailed sheets, one for each strategy plus a master ranking list

<p align="center" width="100%">
<img src="./images/screener_report.png" alt="Screener report" style="width: 85%; min-width: 300px; display: block; margin: auto;">
</p>
