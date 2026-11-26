# V6 plan: a "buy only when everything looks good" signal (recorded before running)

Date: 26 Nov 2026. Price data cut at 23 Nov 2026. Data and model scores from V5 (`research/v5_scores.pkl`), walk-forward, no refitting.

## Signal
At each close, a stock in the top 100 liquid HOSE gets **MUA** only when every condition of its level holds:

| Level | Conditions (each adds to the previous) |
|---|---|
| S1 | 20-session average model rank in the top 10 |
| S2 | + VN-Index above its 200-session average |
| S3 | + stock price above its 50-session average |
| S4 | + profitable (E/P > 0) and earnings higher than a year ago |
| S5 ("all good") | + foreigns net buyers over 20 sessions and more traded value on up days than down days (20 sessions) |

Each level is run with two model scores: B (current) and A (all new data). That makes 10 variants.

## Trading
- Buy at the next close; skip a stock near the ceiling or not traded.
- At most 6 stocks, each 1/6 of the money at entry. Money not used stays in cash and earns nothing (conservative).
- Hold at least 20 sessions. After that, sell at the close on the first day the signal is off. Cost 0.4% round trip.

## Reported for 2019–22 and 2023–26
- Signals per month and share of time with nothing to buy.
- For each new signal over its 20 sessions: average return after cost, share that rose, share that beat the fund, and share that beat the average top-100 stock.
- Portfolio yearly return, worst fall, and monthly t against the E1VFVN30 fund.

## Rule
A variant is called useful only if it beats the fund in **both** periods, its signals beat the average stock more than 50% of the time in both periods, and its 2019–26 monthly t against the fund is at least 1.65. Ten variants are tried, so one passing by luck is possible: with no real effect, about 0.5 would be expected by chance. Even a pass stays "paper only" until the live weekly check agrees.
