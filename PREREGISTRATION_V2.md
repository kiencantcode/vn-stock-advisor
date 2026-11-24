# Plan V2: wide search with overfitting tests

Written 24 November 2026 before running. Known beforehand: the V1 results, including 2023-2026 for ten candidates. This is therefore **not a clean exam** for those ten; only future data is.

**Money:** $7 of every $10 long-term, $3 short-term, reset quarterly.

**Long grid (1,152):** 32 scores (11 single signals; 15 combinations of the value, quality, low-risk and momentum themes; ridge and LightGBM at 3 and 12 months; rolling-IC weighting; signal momentum) x 10, 20 or 30 stocks x quarterly or half-yearly x top 100 or 50 liquid stocks x no overlay, 200-session trend, or volatility-managed (never above 100%).

**Short grid (72):** LightGBM at 5, 10, 20 sessions, reversal, abnormal turnover, 52-week high x 5, 10, 20-session holding x 6 or 10 stocks x keep rank 3N or 5N, on the point-in-time 100-stock universe.

Costs 0.4% per round trip; trades at the close one session after the signal; same data rules as V1.

**Evaluation**
1. *Walk-forward selection (primary):* each January from 2018 (short: 2020), take the setting with the highest Sharpe ratio on all earlier data and hold it for the year. Secondary: average of the top 10% of settings; average of all settings.
2. *Probability of backtest overfitting* (Bailey, Borwein, Lopez de Prado & Zhu): CSCV with 16 blocks of monthly returns.
3. *Deflated Sharpe ratio* (Bailey & Lopez de Prado 2014), with effective trials from the mean correlation.
4. *Reality check* (White 2000): stationary bootstrap, 2,000 draws, best setting's excess over the benchmark.
5. t-statistic above 3 as the hurdle for a newly found strategy (Harvey, Liu & Zhu 2016).

**Pass (long):** primary strategy beats the E1VFVN30 fund and the equal-weight universe after costs over 2018-2026, with a bootstrap p-value below 0.10 against the fund, and PBO below 0.5. **Pass (short):** the same against the equal-weight universe, 2020-2026. Otherwise "not proven".
