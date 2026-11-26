# V7 plan: avoid 2022, catch 2025 (recorded before running)

Date: 27 Nov 2026. Same data, scores and trading rules as V6 B-S5 (current model, 7 conditions, 6 slots, hold at least 20 sessions, 0.4% cost). Only two things change.

## 1. Market condition (condition 2), 8 versions
| Id | "Market is healthy" when |
|---|---|
| M0 | VN-Index above its 200-session average (live now) |
| M1 | above its 100-session average |
| M2 | above its 50-session average |
| M3 | 50-session average above 200-session average |
| M4 | above 200-session average, or (above 50-session average and up over 20 sessions) |
| M5 | M0 with a band: turns on above the 200-session average, turns off only 3% below it |
| M6 | more than half of the top 100 stocks above their own 50-session average |
| M7 | no market condition |

## 2. Money not in stocks, 2 versions
- **C** (live now): cash, earning nothing.
- **E**: in the E1VFVN30 fund while the market condition holds; cash otherwise. Moving money in or out of the fund costs 0.1% each way.

16 variants in all (M0-C is the live one).

## Rule
A variant replaces M0-C only if all hold:
1. Higher yearly return than M0-C in **both** 2019–22 and 2023–26.
2. Worst fall over 2019–26 no more than 5 points worse than M0-C.
3. Paired monthly t against M0-C over 2019–26 of at least 1.65.

If several pass, the highest 2019–26 yearly return wins. Otherwise nothing changes.

Honest limits: I already know 2025 hurt the live rule, so this search is partly shaped by hindsight. With 15 challengers, about 0.75 would pass by luck at t ≥ 1.65 if none were truly better. A change also restarts the signal log.
