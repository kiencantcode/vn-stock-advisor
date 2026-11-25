# V3: steady suggestions held one week or more

25 November 2026. Plan: [PREREGISTRATION_V3.md](PREREGISTRATION_V3.md). Code: `research/lab_steady.py`, `research/eval_steady.py`, `research/churn_live.py`. Not investment advice.

**Verdict: best candidate, not proven. Paper only.**

## The problem

The live 31-stock, 5-session model keeps 58% of its top 6 from one day to the next and 40% after five sessions (2023-26 walk-forward).

## The choice

240 settings; 153 met the steadiness rule (85% one-day overlap). Chosen on 2018-22: **LightGBM with a 20-session label, 20-session average rank, top 100 liquid stocks, review every 20 sessions, 10 stocks, sell below rank 30.** Top-10 overlap: 93% after one day, 74% after five sessions (2018-26). Turnover 4.6 times a year.

## Results after 0.4% costs

| | 2018-22 per year | Worst fall | 2023-26 per year | Worst fall |
|---|---|---|---|---|
| Chosen model | 25% | -59% | 14% | -28% |
| Equal weight, 100 stocks | 4% | -58% | 12% | -25% |
| E1VFVN30 fund | 1% | -48% | 18% | -16% |

- 2023-26: t = 0.17 against equal weight and -0.25 against the fund. At 0.8% cost: 11% a year.
- Start day alone moves 2023-26 between 10% and 17% a year.
- By year, model / fund: 2018 -6/-12, 2019 18/3, 2020 54/22, 2021 165/44, 2022 -34/-33, 2023 30/12, 2024 44/21, 2025 -6/54, 2026 -7/-10 (%).
- Picks beating the median stock after 5, 10, 20 sessions: 54, 55, 57% (2018-22); 53, 53, 52% (2023-26). Rank IC at 20 sessions 0.110 (t 5.4), then 0.035 (t 1.5).
- PBO 0.22. Deflated Sharpe 0.75 (below 0.95).
- The order of settings in 2018-22 says nothing about their order in 2023-26 (rank correlation 0.03). 86% of eligible settings beat equal weight in 2023-26 and 36% beat the fund, none of which was used to change the choice.
- Steadier lists were weaker in 2023-26: average yearly return fell from 18% with no averaging to 14% with 20 sessions. Steadiness is a trade-off.

## Limits

2023-26 was seen in earlier work. Further searching on it would only find luck. The live log is the clean test; judge it after about 120 sessions.

## Addendum, 25 November 2026: prices (after seeing the results above)

- **Exits and cheaper entries** (`research/exits.py`, 16 variants of stop, take-profit, trailing stop and waiting for a dip): none had a higher return than rank-based exits in either period. A 10% trailing stop cut the 2018-22 worst fall to -37% from -59%, but barely helped in 2023-26 (-25% from -28%).
- **20-session price range** shown on the page: 10th and 90th percentile of past-year outcomes scaled by volatility; held 79% of outcomes in 2023-26 (target 80%).
- **One buy price** (`research/entry_price.py`), chosen on 2018-22: last close. Steady list: limit at the last close, else buy at the session's close. Fills 91%; gain over buying at the close 0.13 points per trade in 2018-22 (t 2.9) and 0.02 in 2023-26 (t 0.5). Daily ranking: limit at the last close for 3 sessions, fills 92-93%; mean net result per order +0.19% in 2018-22 and -0.11% in 2023-26. A 2% lower limit filled 41-49%.

# V4: all 16,800 combinations (replaces V3 live)

Plan: [PREREGISTRATION_V4.md](PREREGISTRATION_V4.md). Code: `research/lab_all.py`, `research/eval_all.py`, `research/stress_v4.py`. The first run used one start day for weekly review and overstated it; the corrected rerun is reported.

10,710 of 16,800 settings were steady enough. Walk-forward results, each year's setting chosen on earlier data only:

| | 2020-26 per year | 2023-26 per year | Worst fall 2020-26 | t vs fund 2023-26 |
|---|---|---|---|---|
| A best return | 15.0% | 13.7% | -61% | -0.35 |
| B best Sharpe | 18.8% | 8.8% | -38% | -1.02 |
| **C plateau (primary)** | **14.5%** | **14.6%** | **-62%** | **-0.25** |
| V3 (its choice used 2018-22) | 22.3% | 14.0% | -60% | -0.22 |
| E1VFVN30 fund | 12.1% | 17.6% | -42% | |
| Equal weight, 100 stocks | 11.3% | 12.5% | -58% | |

C beat the V3 figure in 2023-26 (14.6% against 14.0%), a margin well within luck, so by the rule its pick goes live: **LightGBM 20-session label, 20-session average rank, top 100, review every 5 sessions, 6 stocks, keep to rank 18, limit buy at the last close (else the next close), no price exits.**

That setting with hindsight: 28% (2018-22), 19% (2023-26), worst fall -60%; 2023-26 t = 0.20 against the fund. Five start days, 2023-26: 16.5-21%. At 0.6 / 0.8 / 1.0% cost: 17 / 15 / 13%. Buying at the close: 18%. Trailing stop 10%: 17%, worst fall -54%. Ten stocks: 16%. Top 50 liquid only: 12%. Overlap 91% after a day, 70% after five sessions.

PBO 0.15; reality check against the fund p = 0.10; deflated Sharpe of the best 0.47; 10% of eligible settings beat the fund in 2023-26. **Verdict: not proven, paper only.**
