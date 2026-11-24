# Long-term model and 70/30 test

24 November 2026. Not investment advice. Plan: [PREREGISTRATION.md](PREREGISTRATION.md). Code: `research/`.

## Result: not proven

Chosen before opening the exam: candidate 4 (EP + ROE + low turnover + 52-week high). Exam: January 2023 - 23 November 2026, after costs.

| Portfolio | Return per year | Worst fall | Sharpe |
|---|---|---|---|
| **Chosen long-term model** | **11.2%** | -19.0% | 0.47 |
| Short model (5 sessions, mean of 5 start days) | 9.5% | -32.2% | 0.34 |
| **70% long + 30% short** | **10.9%** | -20.9% | 0.44 |
| Equal weight, 100 liquid stocks | 11.3% | -23.6% | 0.42 |
| VNINDEX (dividends not included) | 14.4% | -18.1% | 0.62 |
| E1VFVN30 index fund | 17.6% | -16.0% | 0.79 |
| 70% index fund + 30% short model | 15.6% | -17.1% | 0.70 |

The exam required beating both equal weight and VNINDEX with t >= 1.65 against equal weight. The model was below both (t = -0.1 against equal weight).

## All candidates (Sharpe)

| Candidate | 2014-22 | 2023-26 |
|---|---|---|
| 1 EP | 0.25 | 0.84 |
| 2 EP + low turnover | 0.63 | 0.78 |
| 3 EP + ROE | 0.36 | 0.62 |
| **4 EP + ROE + low turnover + 52-week high (chosen)** | **0.73** | **0.47** |
| 5 Low volatility | 0.68 | 0.42 |
| 6 Momentum | 0.39 | 0.40 |
| 7 Low volatility + momentum + EP | 0.69 | 0.66 |
| 8 ROE + gross profit | 0.34 | 0.15 |
| 9 Candidate 4 + low volatility | 0.63 | 0.39 |
| 10 LightGBM (12 months) | 0.42 (from 2016) | 0.71 |

- The rank correlation between the two columns for candidates 1-9 is 0.05: the past ordering did not predict the later one.
- EP was the best in the exam and the worst in development. Choosing it now would be choosing on the exam.
- The rejected trend overlay would have lowered exam Sharpe to 0.26.
- 70/30 barely diversifies: the daily correlation between the sleeves is 0.83.

## Data

- 438 of 447 companies in VNDirect's HOSE list, 26 of 35 marked delisted included; companies that moved to other exchanges are included where listed. Universe chosen by liquidity on each date.
- Quarterly statements lagged 60 or 100 days.

## Limits

- Under four years of exam: differences of several percent a year can be luck.
- Statements may include later corrections; many old ones are stamped 2019. Nine companies have no prices.
- The short model's 31 stocks were chosen with hindsight, and it was developed while looking at 2023-26, so its result is flattering.
- The index fund was a comparison, not a selected model. A few large companies drove much of the index in some years, and it may not repeat.

## Papers

| Paper | Used for | How I read it |
|---|---|---|
| [Huang, Liu & Shu (2023)](https://doi.org/10.1016/j.pacfin.2023.102176), Vietnam, 2008-June 2022 | EP, turnover, ROE, 52-week high | Introduction, main anomaly table and definitions of the full text |
| Blitz, Pang & van Vliet (2012), [summary](https://www.cxoadvisory.com/volatility-effects/reward-for-risk-in-emerging-equity-markets/) | Low volatility | Summary only |
| [Rahimikia et al. (2025)](https://arxiv.org/abs/2511.18578) | Short model choice | Search summaries |
| Jegadeesh & Titman (1993); Novy-Marx (2013); Blitz & van Vliet (2018); Gu, Kelly & Xiu (2020); Faber (2007) | Momentum, quality, combination, machine learning, overlay | Not opened; standard rules from general knowledge |

Huang, Liu & Shu report weak size-neutral results for momentum (t = 1.2) and significant ones for EP (2.2), 12-month turnover (-2.4) and 52-week high (2.5). Those are long-short results before costs, which an ordinary Vietnamese investor cannot replicate.
