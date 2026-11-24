# Long-term model: plan written before any test

Written 24 November 2026, before computing any long-term result.

- **Development period:** July 2014 - December 2022. **Exam:** January 2023 - November 2026, opened once, after the choice is recorded below.
- **Universe (point in time):** stocks on HOSE that day, at least 250 sessions of history, top 100 by 60-session median traded value. Includes companies later delisted or moved, where prices exist.
- **Statements:** usable 60 days after quarter end (100 days for Q4).
- **Portfolio:** 20 stocks, equal weight, rebalanced quarterly (end of March, June, September, December), trade at the close one session after the signal. A holding is kept while ranked in the top 40. Cost 0.4% per full round trip. Delisted without further price: 30% loss.
- **Candidates** (average of cross-sectional ranks):
  1. EP (Huang, Liu & Shu 2023, Vietnam)
  2. EP + low 12-month turnover (same, VN-4 factors)
  3. EP + ROE
  4. EP + ROE + low turnover + 52-week high (the paper's significant, large-stock-usable anomalies)
  5. Low volatility, 36 months (Blitz, Pang & van Vliet 2012)
  6. Momentum, months t-12 to t-2 (Jegadeesh & Titman 1993)
  7. Low volatility + momentum + EP (after Blitz & van Vliet 2018)
  8. ROE + gross profit / assets (Novy-Marx 2013)
  9. Candidate 4 + low volatility
  10. LightGBM predicting 12-month rank from all the above (after Gu, Kelly & Xiu 2020), walk-forward
- **Overlay tested only on the chosen candidate:** hold cash (4% a year) when VNINDEX is below its 200-session average at month end (after Faber 2007).
- **Choice rule:** highest Sharpe ratio after costs on the development period (4% cash rate). Candidate 10 starts July 2016 and is compared on that common period. The overlay is added only if it raises the development Sharpe ratio by at least 0.15.
- **Exam pass:** after costs, beats both the equal-weight universe and VNINDEX, with a monthly excess t-statistic of at least 1.65 against the equal-weight universe. Otherwise the report says "not proven".
- **70/30 portfolio:** 70% chosen long-term model, 30% existing 5-session model, reset quarterly. Reported whatever the result, next to 100% long-term and the alternatives.

## Choice recorded before opening 2023-2026

Development results (July 2014 - December 2022, after costs). Sharpe: equal weight 0.38, VNINDEX 0.23, candidates 1-9: 0.25, 0.63, 0.36, **0.73**, 0.68, 0.39, 0.69, 0.34, 0.63; LightGBM 0.42 against 0.48 for candidate 4 from July 2016.

- **Chosen: candidate 4** (EP + ROE + low turnover + 52-week high).
- **Overlay rejected:** Sharpe 0.82 against 0.73, a gain of 0.09, below the 0.15 required.
