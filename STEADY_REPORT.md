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
