# Technical Analysis & Momentum Screening Report
## Yahoo Finance Global Markets 2026

> **Universe:** US Mega-Cap, US Mid-Cap, and International Equities (subset of 451-ticker dataset)  
> **Objective:** Surface high-probability trade setups by scoring each equity across four independent technical dimensions, then aggregating into a single Composite Technical Score for ranking and watchlist generation

---

## Table of Contents

1. [Methodology Overview](#1-methodology-overview)
2. [Signal Generation - Four Dimensions](#2-signal-generation--four-dimensions)
   - 2.1 RSI Momentum
   - 2.2 Trend Dynamics (SMA Crossover)
   - 2.3 MACD Momentum
   - 2.4 Bollinger Band Position (%B)
3. [Composite Technical Score](#3-composite-technical-score)
4. [Sector Momentum Aggregation](#4-sector-momentum-aggregation)
5. [Outputs](#5-outputs)
6. [Limitations & Caveats](#6-limitations--caveats)

---

## 1. Methodology Overview

This module is **Phase 2** of the three-phase quantitative pipeline:

```
Phase 1 - Data Engineering (EDA & Cleaning)
    ↓
Phase 2 - Technical Analysis & Momentum  ← this report
    ↓
Phase 3 - Composite Screener & Alpha Scoring
```

The technical scoring pipeline operates exclusively on `df_equity` — the cleaned equity sub-frame produced in Phase 1. Non-equity assets (Crypto, Forex, Commodities, ETFs) are excluded, as price-momentum indicators are not meaningful for these instruments in the same framework

**Design principle:** Each of the four technical dimensions is scored independently on a 0-25 scale. This prevents any single indicator from dominating the final score and ensures that a strong signal in one dimension cannot fully compensate for weakness across the others

---

## 2. Signal Generation - Four Dimensions

### 2.1 RSI Momentum (0–25 pts)

**Indicator:** Relative Strength Index, 14-period (`RSI-14`)

RSI measures the speed and magnitude of recent price changes to identify overbought and oversold conditions

| RSI Range | Classification | Signal Interpretation |
|---|---|---|
| < 30 | Oversold | Potential mean-reversion buy opportunity |
| 30 – 70 | Neutral | No directional bias from RSI alone |
| > 70 | Overbought | Momentum extended; watch for reversal |

**Scoring logic:**

| Condition | Points Awarded |
|---|---|
| RSI 40-60 (healthy momentum, not extended) | 25 |
| RSI 30-40 or 60-70 (mild extremes) | 15 |
| RSI < 30 (oversold) | 10 |
| RSI > 70 (overbought) | 5 |

> RSI alone is not a trade signal. It is one of four inputs to the composite score

---

### 2.2 Trend Dynamics — SMA Crossover (0–25 pts)

**Indicators:** Simple Moving Average 50-day (`SMA-50`) and 200-day (`SMA-200`)

Two conditions are evaluated:

**Golden Cross:** `SMA-50` crosses above `SMA-200` - a widely-followed long-term bullish signal indicating that short-term momentum has shifted above the long-term trend baseline

**Price vs Long-Term Average:** Whether the current price is trading above or below `SMA-200`, confirming the broader trend direction

| Condition | Points Awarded |
|---|---|
| Golden Cross active AND price > SMA-200 (Strong Uptrend) | 25 |
| Price > SMA-200 only | 15 |
| Price < SMA-200 (downtrend) | 5 |
| Death Cross active (SMA-50 < SMA-200) | 0 |

---

### 2.3 MACD Momentum (0-25 pts)

**Indicator:** Moving Average Convergence Divergence - standard parameters (12, 26, 9)

MACD captures the relationship between two exponential moving averages and provides both trend direction and momentum acceleration signals

Two sub-signals are evaluated:

1. **Histogram sign:** Positive histogram → bullish momentum building; negative → bearish
2. **Line crossover:** MACD line crossing above the Signal line → bullish crossover event

| Condition | Points Awarded |
|---|---|
| Bullish crossover AND positive histogram | 25 |
| Positive histogram only | 15 |
| Negative histogram, no crossover | 8 |
| Bearish crossover AND negative histogram | 0 |

---

### 2.4 Bollinger Band Position - %B (0–25 pts)

**Indicator:** Bollinger Bands (20-period, 2 standard deviations); position expressed as `%B`

`%B` locates the current price within the volatility envelope:
- `%B = 1.0` → price at upper band
- `%B = 0.5` → price at midline (20-period SMA)
- `%B = 0.0` → price at lower band

| %B Range | Interpretation | Points Awarded |
|---|---|---|
| 0.4 – 0.8 | Healthy uptrend within bands | 25 |
| 0.8 – 1.0 | Approaching upper band; potential breakout or exhaustion | 15 |
| 0.2 – 0.4 | Below midline; weak momentum | 10 |
| < 0.2 | Near or below lower band; oversold / breakdown | 5 |
| > 1.0 | Outside upper band; extreme extension | 5 |

---

## 3. Composite Technical Score

### Scoring Architecture

The four dimension scores are summed to produce a **Composite Technical Score** on a 0–100 scale:

```
Composite Score = RSI Score + Trend Score + MACD Score + Bollinger Score
                = [0–25]   + [0–25]      + [0–25]     + [0–25]
```

Equal weighting (25% per dimension) reflects the principle that no single indicator has a proven edge over the others in isolation

### Rating Tiers

| Rating | Score Range | Interpretation |
|---|---|---|
| **Strong Buy** | ≥ 80 | Broad-based technical strength across all four dimensions |
| **Buy** | 60 - 79 | Positive momentum with minor weaknesses |
| **Neutral** | 40 - 59 | Mixed signals; no clear directional bias |
| **Sell** | 20 - 39 | Technical deterioration across multiple dimensions |
| **Strong Sell** | < 20 | Broad-based technical weakness; avoid or short |

### Score Interpretation Notes

- A **Strong Buy** rating requires alignment across RSI, trend, MACD, and Bollinger dimensions simultaneously - this is intentionally a high bar
- A score in the **Neutral** band (40–59) does not imply a hold recommendation; it signals insufficient technical evidence for a directional trade
- Technical scores are inputs to the Phase 3 composite Alpha Score (weighted at **10%**), where they are combined with Momentum (40%), Value (30%), and Quality (20%) factors

---

## 4. Sector Momentum Aggregation

Individual ticker scores are aggregated to the sector level to identify which sectors are exhibiting broad-based technical strength vs weakness

**Metrics computed per sector:**

| Metric | Description |
|---|---|
| `avg_composite_score` | Mean Composite Technical Score across all tickers in sector |
| `pct_golden_cross` | Percentage of tickers with an active Golden Cross |
| `avg_3m_return` | Average 3-month price return (%) |
| `avg_1m_return` | Average 1-month price return (%) |
| `avg_rsi` | Mean RSI-14 across sector |

Sector rankings are used in the Phase 3 screener to apply a **sector momentum tilt** - overweighting stocks in technically strong sectors and underweighting those in weak sectors

---

## 5. Outputs

The pipeline produces three deliverables:

### 5.1 `technical_analysis_report.png`
A 6-panel visual dashboard containing:
- RSI distribution histogram (full equity universe)
- Composite Technical Score distribution
- Rating tier breakdown (bar chart)
- Sector heatmap by average composite score
- RSI vs MACD signal quadrant scatter plot
- Golden Cross prevalence by sector

### 5.2 `tech_signals_summary.csv`
Master signal table - one row per equity ticker - containing all computed intermediate signals and the final Composite Technical Score. Columns include:

`ticker` · `rsi_14` · `rsi_signal` · `sma50` · `sma200` · `golden_cross` · `trend_signal` · `macd_line` · `macd_signal_line` · `macd_histogram` · `macd_signal` · `bb_pct_b` · `bb_signal` · `rsi_score` · `trend_score` · `macd_score` · `bb_score` · `composite_score` · `rating`

### 5.3 `watchlist_strong_buy.csv`
Curated shortlist of **Strong Buy** candidates filtered to meet all of the following criteria:
- Composite Technical Score ≥ 80
- Active Golden Cross (`golden_cross == True`)
- RSI between 40 and 70 (healthy momentum, not overbought)
- MACD histogram positive (momentum building, not decelerating)

This multi-condition filter reduces false positives from assets that score highly on one dimension while showing deterioration elsewhere

---

## 6. Limitations & Caveats

| Limitation | Detail |
|---|---|
| **Lagging indicators** | RSI, MACD, and SMA are all backward-looking. They confirm trends; they do not predict reversals |
| **No volume confirmation** | Volume data was not available in the Yahoo Finance dataset. Volume-confirmed breakouts are stronger signals than price-only signals |
| **Equal dimension weighting** | The 25/25/25/25 split is a reasonable default but has not been backtested for this specific universe. Optimal weights may differ by sector or market regime |
| **Static thresholds** | RSI and %B thresholds are fixed. In trending markets, RSI can remain overbought for extended periods without reverting |
| **No fundamental overlay** | Technical scores are purely price-based. A stock can score Strong Buy technically while deteriorating fundamentally. Always cross-reference with Phase 3 composite scores |

---

*Report generated as part of the Yahoo Finance Global Markets 2026 quantitative pipeline*  
*Pipeline stack: Python · Pandas · NumPy · TA-Lib / manual indicator implementation*
