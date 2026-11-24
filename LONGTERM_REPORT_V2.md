# V2: wide search for a $7 long-term / $3 short-term plan

24 November 2026. Not investment advice. Plan: [PREREGISTRATION_V2.md](PREREGISTRATION_V2.md). Code: `research/`. Costs 0.4% per round trip.

## Long-term ($7): 1,152 settings, fails

Walk-forward selection, 2018 - November 2026:

| | Per year | Sharpe | Worst fall |
|---|---|---|---|
| Best past setting each year (primary) | 6.0% | 0.19 | -46% |
| Top 10% of settings | 9.7% | 0.40 | -38% |
| E1VFVN30 fund | 8.2% | 0.29 | -48% |
| Equal weight, 100 stocks | 8.9% | 0.32 | -58% |

PBO 0.30; reality-check p 0.36 against the fund; 37% of settings beat the fund. The best in hindsight (52-week high, 10 stocks, trend overlay, 20.9% a year, Sharpe 0.97) has deflated Sharpe 0.91, below 0.95, and was not selectable in advance.

## Short-term ($3): 72 settings, passes the plan, fails stress tests

Selected by walk-forward: LightGBM, 20-session target, mostly 10-session holding, 6 stocks, 100-stock universe. 2020 - November 2026:

| | Per year | Sharpe | Worst fall |
|---|---|---|---|
| Best past setting each year (primary) | 29.0% | 0.88 | -63% |
| Equal weight, 100 stocks | 13.4% | 0.47 | -58% |
| E1VFVN30 fund | 12.1% | 0.45 | -42% |

(In the short table of the log, equal weight is reset every 20 sessions: 12.3%.) PBO 0.39; primary p 0.001 against equal weight, 0.026 against the fund; t = 2.6 (hurdle 3). Deflated Sharpe 0.39, which fails.

Stress tests, added after seeing the result (20-session model and holding, 6 stocks, no buying at the ceiling or selling at the floor):

| Change | Per year 2020-26 | t vs fund | Per year 2023-26 | t vs fund |
|---|---|---|---|---|
| None | 23% | 1.36 | 19% | 0.17 |
| Cost 1.0% | 18% | 0.90 | 14% | -0.31 |
| Only the 50 most liquid | 18% | 1.02 | 16% | -0.09 |
| Trade 2 days later | 22% | 1.27 | 16% | -0.02 |
| 50 liquid, 10 stocks, 0.6%, 2 days later | 16% | 0.80 | 12% | -0.59 |

The fund returned 17.6% a year in 2023-26. Much of the model's advantage comes from 2020-21 and from less liquid stocks.

## $10 split, January 2020 - 23 November 2026

| Plan | Per year | Sharpe | Worst fall | $10 becomes |
|---|---|---|---|---|
| $10 fund | 12.1% | 0.45 | -42% | $22.0 |
| $7 fund + $3 cash (4%) | 10.4% | 0.46 | -30% | $19.7 |
| **$7 fund + $3 short model** | **18.0%** | **0.68** | **-47%** | **$31.2** |
| $7 chosen long + $3 short model | 14.5% | 0.56 | -49% | $25.4 |
| $7 chosen long + $3 fund | 8.9% | 0.34 | -44% | $18.0 |

## Leak found and fixed

Two features used adjusted price x raw volume. Adjusted prices depend on later splits and dividends, so old values were 6-40% of true traded value. The short search above uses true traded value. Effect on the live model (31 stocks, 2023-26): rank IC 0.0300 to 0.0289. The live code still has it.

## Limits

2023-26 was seen before; the winner of the short search was examined further only to weaken it; statements may include later corrections; the index fund's own past is one path. Only future data is clean.

## Papers opened in full text

Read: abstract plus the passages used. Bailey & Lopez de Prado (deflated Sharpe); Bailey, Borwein, Lopez de Prado & Zhu (PBO); Harvey, Liu & Zhu; Novy-Marx & Velikov (buy/hold spread); Novy-Marx (profitability); Moreira & Muir (volatility-managed); Ehsani & Linnainmaa (factor momentum); Jensen, Kelly & Pedersen (replication); Gu, Kelly & Xiu; Huang, Liu & Shu (Vietnam); Cakici et al. 2023 on global machine learning (J. Economic Dynamics & Control 155); Cai et al. (IC weighting, arXiv 2508.18592); Rahimikia et al. Used without opening: White 2000 (reality check); Politis & Romano (stationary bootstrap).
