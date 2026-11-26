# V5 plan: new data for the steady list (recorded before running)

Date: 26 Nov 2026. Price data cut at 23 Nov 2026, as in V3/V4.

## Question
Does adding foreign flows, financial results, or richer volume features make the live V4 steady list better?

## Data (VNDirect, all codes ever in the top 100 liquid HOSE)
- Foreign buy/sell value and room per day, from 30 Aug 2018. Data before then is missing, not zero.
- Daily P/E, P/B, P/S and market cap, from Dec 2017. These values change only after a report is filed (checked: KDH Q1 2024 filed 26 Apr, P/E changed 2 May). As an extra guard, every value is used one session late.

## Feature sets (all ranked across stocks each day, like the current features)
- **B** (base): the current 33 features.
- **V** = B + volume: share of value on up days (20), value shock vs 60-day median, value trend 5/20, price-volume correlation (20), close location weighted by value (20), value-weighted return minus plain return (20).
- **F** = B + foreign: net foreign value / traded value over 5, 20, 60 sessions; foreign share of trading (20); room left; change in foreign holding over 20 sessions.
- **K** = B + financial results: E/P, B/P, S/P, size, ROE, earnings change over 250 and 63 sessions (scaled by book), sales growth over 250 sessions.
- **A** = all of the above.

## Model and test
The live model and setting stay fixed: LightGBM, 20-session label, 3 seeds, refit every 6 months on data ending 22 sessions before the window. Then 20-session average rank, top 100, review every 5 sessions, 6 stocks, keep to rank 18, 0.4% cost (close fills, same for every set).

Reported for 2019–22 and 2023–26: monthly IC and its t, yearly return, worst fall, t against the E1VFVN30 fund, and a weekly check (top 6 bought fresh each week, held 5 sessions).

## Rule
A set replaces B only if all three hold:
1. Higher yearly return than B in **both** 2019–22 and 2023–26.
2. Higher IC than B in both periods.
3. Paired monthly t against B over 2019–26 of at least 1.65.

If more than one passes, the highest 2019–26 return wins. Otherwise B stays. Even then, the list stays "paper only" unless it beats the fund with t ≥ 1.65 in 2023–26. Five sets are tried, so one passing by luck is possible; this is reported.

Honest limit: 2023–26 was already looked at many times in V3/V4, so it is not a clean holdout. The real test is the saved weekly predictions.
