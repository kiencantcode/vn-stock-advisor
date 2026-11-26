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

# V5: foreign flows, financial results, richer volume (result: keep V4)

Plan: [PREREGISTRATION_V5.md](PREREGISTRATION_V5.md), recorded before running. Code: `research/extra_data.py`, `research/lab_v5.py`; results in `research/v5_results.json`.

| Set | IC 2019-22 | IC 2023-26 | Per year 2019-22 | Per year 2023-26 | Worst fall 2019-26 | Weeks beating fund 2023-26 |
|---|---|---|---|---|---|---|
| B current | 0.079 | 0.055 | 46% | 18.2% | -64% | 41% |
| V + volume | 0.106 | 0.065 | 39% | 19.0% | -63% | 38% |
| F + foreign | 0.081 | 0.065 | 33% | 21.6% | -53% | 44% |
| K + financial results | 0.092 | 0.053 | 34% | 21.3% | -56% | 43% |
| A all | 0.110 | 0.075 | 44% | 18.6% | -48% | 45% |
| E1VFVN30 fund | | | 4.9% | 17.6% | -42% | |

Rule check: no set has a higher return than B in both periods; paired t against B is negative for all four (-0.28 to -0.85). **B stays live.** The new data makes the whole ranking more accurate (IC of A is 0.093 vs 0.067 over 2019-26, t 5.6), but the top 6 do not earn more, and none beats the fund clearly in 2023-26 (t 0.13-0.57). Most useful new inputs by model gain: earnings change over 63 and 250 sessions, E/P, foreign room left, sales growth.

# V6: "buy only when everything looks good" (result: not useful)

Plan: [PREREGISTRATION_V6.md](PREREGISTRATION_V6.md). Code: `research/lab_v6.py`; results in `research/v6_results.json`. None of the 10 variants passed.

| Variant | Signals per month | Per year 2019-22 | Per year 2023-26 | Worst fall 2019-22 | Worst fall 2023-26 | Signals beating avg stock 2023-26 |
|---|---|---|---|---|---|---|
| A-S1 model top 10 only | 15 | 52% | 19.5% | -50% | -26% | 49% |
| A-S2 + VN-Index above MA200 | 10 | 48% | 7.5% | -18% | -29% | 50% |
| A-S3 + price above MA50 | 8 | 45% | 11.2% | -19% | -23% | 50% |
| A-S4 + profitable, earnings up | 6 | 38% | 9.9% | -19% | -25% | 49% |
| A-S5 all good (+ foreigns buying, up-day volume) | 3 | 31% | 7.0% | -23% | -19% | 46% |
| B-S5 all good, current model | 4 | 26% | 9.5% | -21% | -20% | 49% |
| E1VFVN30 fund | | 4.9% | 17.6% | -42% | -16% | |

The filters halved the worst fall in 2019-22 (they kept out of most of 2022), but in 2023-26 every filtered variant earned far less than the fund, mostly because the market filter missed the 2025 rally (fund +54%; filtered variants 2-20%). Signals that met every condition beat the average stock less than half the time in 2023-26.

## V6 on the site (paper only)

The site now shows the B-S5 signal ("all good", current model) as the tab "Tín hiệu MUA/BÁN": `advisor/signals.py`, data in `advisor/extra.py`. B-S5 was picked over A-S5 because it earned more in 2023-26 (9.5% vs 7.0% a year) and reuses the live model. Each session's signals for the top 100 are saved to `output/history/signals.csv` before 9:00 the next session; the paper portfolio is rebuilt only from that log. On 26 Nov 2026 VN-Index was 8.5% below its 200-session average, so there were no buy signals.
