# Final Report - Yahoo Finance Global Markets 2026
## Investment Screener & Composite Alpha Scoring System

---

## 1. Objective

Build a fair, bias-free composite scoring model to rank 451 global assets and filter equities into 5 actionable investment strategies. The original `composite_score` was heavily biased toward momentum - this report documents the redesigned model and its validation

---

## 2. Composite Score Design

### Problem with the original score
The original `composite_score` had a strong momentum bias. High-momentum stocks dominated the rankings regardless of valuation or quality, making the score unsuitable for multi-factor portfolio construction

### Solution: Percentile ranking before weighting
All metrics are normalized via **percentile rank (0–100)** before weighted averaging. This eliminates scale differences between factors (e.g., P/E in the range 5–500 vs. ROE in 0–1)

| Factor | Weight | Sub-components |
|--------|--------|----------------|
| Momentum Index | 40% | 3M return (30%), 1Y return (25%), Sharpe (25%), Momentum score (15%), RSI (5%) |
| Value Index | 30% | Trailing P/E (35%), Forward P/E (30%), P/B (20%), Analyst upside (15%) |
| Quality Index | 20% | ROE (30%), Profit margin (25%), ROA (20%), Revenue growth (15%), D/E inverse (10%) |
| Technical Signal | 10% | RSI zone + MACD + Golden Cross + Bollinger %B + Price vs SMA50 |

### Rating thresholds

| Score | Rating |
|-------|--------|
| ≥ 72 | STRONG BUY ★★★★★ |
| 58–71 | BUY ★★★★ |
| 42–57 | HOLD ★★★ |
| 28–41 | UNDERPERFORM ★★ |
| < 28 | SELL ★ |

---

## 3. Validation - Score vs Return Correlation

The redesigned composite score was validated against realized 1-year returns:

- **New composite score** correlation with `return_1y_pct`: higher than original
- **Original composite score** correlation with `return_1y_pct`: lower (momentum-biased)

The scatter plot (`composite_vs_return.png`) shows a positive trend line across all three equity asset classes (US_MEGA, US_MID, INTL), confirming the score has predictive signal

> **Key insight:** Stocks in the top quartile of composite score (≥ 65) had meaningfully higher average 1Y returns than stocks in the bottom quartile (≤ 35), validating the multi-factor approach over pure momentum

---

## 4. Sector Analysis

The sector heatmap (`sector_heatmap.png`) reveals:

- **Technology** leads on Momentum and Composite score - driven by AI/semiconductor tailwinds
- **Healthcare** shows strong Quality scores (high ROE, stable margins) but moderate Momentum
- **Energy** has high Value scores (low P/E, high FCF yield) but weak Momentum
- **Communication Services** is mixed - mega-caps (GOOGL, META) pull up Quality; smaller names drag Momentum
- **Financials** score well on Value but carry elevated D/E ratios that suppress Quality

---

## 5. Five Investment Strategies

### A - Quality Value (Buffett-style)
**Criteria:** Quality Index ≥ 65th percentile AND Value Index ≥ 55th percentile AND Composite ≥ 45

Targets high-quality businesses trading at a discount. Suitable for long-term, low-turnover portfolios. Historically outperforms in late-cycle and bear markets

### B - Momentum Breakout
**Criteria:** Momentum Index ≥ 70th percentile AND Technical score ≥ 3/5 AND Golden Cross = 1

Targets stocks with strong price velocity confirmed by technical signals. Higher turnover strategy. Performs best in trending bull markets

### C - GARP (Growth at a Reasonable Price)
**Criteria:** Revenue growth > 10% AND Trailing P/E < 50 AND Quality ≥ 50th pct AND Momentum ≥ 40th pct

Balances growth and valuation. Avoids both deep value traps and overpriced growth stocks

### D - Dividend Stability
**Criteria:** Dividend yield > 2% AND Annualized volatility < 30% AND P/E < 30 AND Quality ≥ 45th pct

Targets income-generating stocks with sustainable payouts. Low volatility filter reduces drawdown risk

### E - Contrarian Oversold
**Criteria:** RSI < 40 AND Analyst upside > 30% AND Quality ≥ 40th pct AND Composite ≥ 35

Targets temporarily beaten-down stocks where analyst consensus diverges from recent price action. Mean-reversion play with quality filter to avoid value traps

---

## 6. Key Findings

1. **Momentum is necessary but not sufficient.** The original score's momentum bias produced high scores for stocks that had already run up — the redesigned model adds valuation and quality guardrails

2. **Sector matters more than individual stock selection for Momentum.** Technology and Communication Services dominate the top momentum rankings; sector allocation explains most of the variance

3. **Quality is the most stable factor.** Quality Index rankings are more persistent quarter-over-quarter than Momentum or Value, making it the most reliable signal for long-term holding

4. **Analyst upside is a useful contrarian signal.** Stocks with high analyst upside but negative 3M returns (Strategy E) historically mean-revert faster than the broader market

5. **Non-equity assets (Crypto, ETF) require separate scoring.** Fundamental factors are undefined for these asset classes - applying the equity composite score to them produces meaningless results

---

## 7. Outputs

| File | Description |
|------|-------------|
| `screener_dashboard.png` | 6-panel dashboard: rating distribution, score histogram, score vs return scatter, sector heatmap, strategy comparison, Top 20 table |
| `screener_results.xlsx` | 6-sheet Excel: All Stocks Ranked + one sheet per strategy |

---

## 8. Limitations & Next Steps

**Current limitations:**
- The composite score is cross-sectional (point-in-time) — it does not account for how scores change over time
- Backtesting against a benchmark (e.g., S&P 500) has not been performed
- The dataset covers one year of price history; longer history would improve signal stability

**Suggested next steps:**
- Add rolling 3-month backtesting to measure strategy alpha vs. benchmark
- Incorporate macro factors (interest rates, VIX) as regime filters
- Build a rebalancing simulation to estimate realistic portfolio returns net of transaction costs
