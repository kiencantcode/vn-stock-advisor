# VN Stock Advisor: mini report

23 November 2026. Forecast horizon: 5 trading sessions. Not investment advice.

## Summary

- The new model ranks stocks better than the old one. On 2023-2026 data its rank correlation with actual 5-day returns is **0.036 (t = 2.3)**; the old model's was 0.007 (t = 0.4).
- Price ranges are reliable: the 80% range contained the actual close **79.8%** of the time.
- **It is not proven profitable.** After an assumed 0.4% round-trip cost, the portfolio trailed an equal-weight holding of the same 31 stocks by 2.1% a year in 2023-2026 (t = -0.3, indistinguishable from zero).
- The pipeline therefore locks the `MUA` (buy) signal until the results pass a significance test.

## How it works

1. **Data.** About 13 years of daily prices from DNSE/Entrade for 75 stocks plus VNINDEX. The 31 listed in `config.yaml` sectors are ranked; the other 44 are training data only.
2. **Features.** 30 price and volume indicators, each converted to a rank among all stocks that day, plus 6 market indicators.
3. **Ranking.** LightGBM (average of 3 seeds) predicts each stock's relative 5-day return.
4. **Price ranges.** Past-year forecast errors, scaled by each stock's volatility, set the ranges and levels (conformal-style calibration). They describe likely movement, not direction.
5. **Validation.** Retrained every 6 months on past data only, with a gap so training labels cannot overlap the test period. Trades are priced at the next day's open.
6. **Signal gate.** `MUA` appears only if 2023+ net return and rank correlation both reach t >= 1.65. Otherwise the top 20% show `HANG CAO`.

## Models compared

Every fifth trading day, 31 stocks. Rank IC is the daily rank correlation between forecast and actual return. "Net" is yearly return above equal weight after costs, holding the top 6 with no hold buffer. 2018-22 was used to choose; 2023-26 only to check.

| Model | IC 2018-22 | IC 2023-26 (t) | Net 2018-22 | Net 2023-26 |
|---|---|---|---|---|
| Original (per sector, 900 days) | 0.016 | 0.007 (0.4) | -3.7% | -7.9% |
| Original with 13 years of data | 0.049 | 0.000 (0.0) | +5.9% | -15.1% |
| Pooled gradient boosting, raw returns | 0.044 | 0.008 (0.5) | +10.8% | -2.5% |
| Pooled gradient boosting, ranks | 0.045 | 0.026 (1.9) | +8.6% | +0.6% |
| Ridge | 0.059 | 0.019 (1.2) | +2.1% | +1.7% |
| LightGBM, ranks | 0.053 | 0.038 (2.6) | -0.5% | -6.6% |
| **LightGBM, ranks + market (chosen)** | **0.068** | **0.036 (2.4)** | **+4.7%** | **+1.0%** |
| CatBoost, ranks | 0.057 | 0.031 (1.9) | +2.3% | -6.4% |
| Ensemble of three | 0.060 | 0.030 (1.9) | +0.5% | -9.5% |
| Chronos-2 foundation model, zero-shot | -0.010 | 0.009 (0.6) | -11.3% | -6.1% |
| 5-day reversal | 0.013 | 0.030 (1.6) | -15.0% | -24.4% |
| 12-month momentum | 0.024 | 0.004 (0.2) | -1.7% | +0.6% |

- The chosen model had the highest 2018-22 IC. Pooled boosting on raw returns had a higher 2018-22 net return, but its IC did not hold up.
- No price-forecasting model tested beat "predict 0%" on absolute price error in either period. Price-point forecasts and the old "Du bao" column were removed.
- A hold buffer (sell only below rank 18) cut turnover from 60% to about 20% per period. It had the best 2018-22 t-statistic for the chosen model (+7.7% a year in the final pipeline), but gave -2.1% in 2023-26.

## What recent research says

- [Rahimikia et al. (2025)](https://arxiv.org/abs/2511.18578) report that off-the-shelf time-series foundation models do worse than boosted-tree ensembles on daily excess returns, across 94 countries. Models pre-trained on financial data did better, but need far more data than this project has.
- [Chronos-2 (2025)](https://arxiv.org/abs/2510.15821) leads general forecasting benchmarks. It did not carry over to these stocks (table above).
- [Adaptive conformal inference](https://arxiv.org/abs/2106.00170) motivates recalibrating ranges as markets change. This pipeline uses a simpler rolling one-year version.

These were reviewed through search summaries, not read in full. Only Chronos-2 was tested here; TimesFM, TiRex and Kronos were not.

## Fixed

- `requirements.txt` crashed pip on Windows (non-ASCII comments).
- Cached prices became wrong when the source re-adjusted history for dividends or splits; this is now detected and reloaded.
- An unfinished session's price could be used as a close before 15:00 Vietnam time.
- Demo runs overwrote real reports, demo data changed every run, and its artificial cycle made models look predictive.
- Watch mode stopped on any network error.

## Limits

- **Survivorship bias:** the stocks are today's large names, so past results are flattering.
- **Holdout reuse:** several models and buffers were viewed on 2023-26, so it is no longer fully untouched. Trust live results most.
- **Costs are assumed** (0.4%). Set `round_trip_cost` to your broker's actual fees.
- The backtest assumes fills at the open, even for stocks locked at their price limit.
- Buy, take-profit and stop levels were not backtested as a trading strategy.
- Prices and volume only: no fundamentals, news or foreign flows.

## Checks run

| Check | Result |
|---|---|
| Features identical when future data is removed (12 stocks) | Pass, difference 0 |
| Corrupted/re-adjusted cache repaired; incremental update | Pass |
| Random demo data gives no signal | Pass, IC 0.001 and -0.003 |
| Clean install on Windows, Python 3.12 | Pass |
| Real run, single sector, wrong sector name | Pass |

Not tested: `vnstock`, `--watch`, and the GitHub Actions workflow.

## Next steps worth trying

1. Let the daily ranking log (added in `advisor/track.py`) run for 3-6 months, then review the live score.
2. Add foreign net buying and quarterly fundamentals.
3. Use point-in-time VN100 membership to remove survivorship bias.

## Update, 24 November 2026: horizons and live learning

Results on 2023-26, 31 stocks, top 6 picks, 6-month retraining. Net is averaged over 5 cycle start days.

| Horizon | Rank IC (t) | Picks beat median (random) | Picks that rose (all stocks) | Net per year (range) |
|---|---|---|---|---|
| 5 sessions | 0.030 (2.6) | 49.6% (48.3%) | 50.1% (49.6%) | -0.8% (-4.3% to +3.7%) |
| 20 sessions | 0.007 (0.3) | 49.1% (48.4%) | 51.5% (51.4%) | +0.4% (-3.0% to +3.1%) |
| 60 sessions | -0.006 (-0.2) | 47.7% (48.4%) | 52.2% (52.7%) | -1.8% (-7.9% to +4.6%) |

- Only the 5-session horizon shows skill. The 20- and 60-session models looked good on 2018-22 and failed on 2023-26.
- The 5-session IC here uses every day; the 0.036 above uses every fifth day. The -2.1% net above is one start day within this range.
- Learning methods (5 sessions, IC 2018-22 / 2023-26, single seed): 6-month retraining 0.056 / 0.031; monthly 0.062 / 0.032; 6-month favouring recent data (2-year half-life) 0.052 / 0.019; monthly favouring recent data 0.052 / 0.022. Frequent retraining on all history was kept; recency weighting was rejected.
- Each logged ranking now includes a frozen model that ignores outcomes after the log began, to measure whether learning helps. High-rank signals pause if live IC is significantly negative after 60 sessions.

## Update, 24 November 2026: time-series forecasting

`advisor/forecast.py` forecasts sessions +1 to +5 for each stock and relearns at every run. Tested on 2018-22 and 2023-26.

**Price line.** Error change against "price stays the same" at +5 sessions, half-weight forecasts (positive is better; t in brackets):

| Method | 2018-22 | 2023-26 |
|---|---|---|
| 250-day drift | +0.03% (-0.3) | -0.55% (-2.4) |
| Holt damped trend | -0.08% (-0.3) | -0.62% (-3.2) |
| AR(5) | -0.29% (-1.6) | -0.41% (-3.0) |
| Ridge on lags | +0.13% (0.7) | -0.35% (-2.1) |
| LightGBM on lags | +0.21% (0.8) | -0.17% (-0.8) |

None reliably beat no change, so the line stays flat unless a method wins with t >= 2.4 over the last 500 sessions. Holt, ridge and LightGBM compete at every run.

**Price range.** HAR volatility had the lowest quantile error of six methods at +1, +3 and +5 in both periods (about 3% lower than 20-day volatility at +5). Its 80% range covered 78-79% over the last 500 sessions.

**Replay.** Six past dates with later data removed: the 80% range contained 76-87% by session (186 forecasts each, strongly correlated).
