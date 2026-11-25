# Plan V3: steady suggestions held one week or more

Written 25 November 2026 before running. The owner's problem: the list changes too much each day. 2023-26 has been seen in earlier work for related models, so only future data is fully clean.

**Data:** VNDirect prices incl. delisted HOSE stocks, true traded value (no turnover leak), universe chosen at each date (top 100 or top 50 by 60-session median value, listed 250+ sessions). No whole-sample stock filter.

**Grid (240):** 5 scores (LightGBM on 5-, 10-, 20-session rank labels; ridge on 20-session; average rank of these four) x trailing mean of the daily rank over 1, 5, 10, 20 sessions x universe 100 or 50 x trade every 5, 10, 20 sessions x 6 or 10 stocks. Sell only below rank 3N. Models retrained every 6 months on the past with a gap of label + 2 sessions; 3 seeds.

**Trading:** next session's close, 0.4% per round trip, no buying near the ceiling, no selling near the floor; average of start days 5 sessions apart.

**Choice (2018-2022 only):** among settings whose top-N list overlaps yesterday's by at least 85% on average, the highest information ratio against the equal-weight universe, after costs. The current live 31-stock, 5-session model is measured for comparison.

**Check (2023 - Nov 2026), once:** return after costs, worst fall and t-statistic against the equal-weight universe and the E1VFVN30 fund; the same at 0.8% cost; year by year; share of 5-, 10- and 20-session holds that beat the median stock; PBO and deflated Sharpe over the grid.

**Verdict:** "proven" only if it beats both benchmarks in 2023-26 with t >= 1.65 against each and PBO < 0.5. Otherwise "best candidate, not proven": paper only.
