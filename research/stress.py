"""Re-run the short search without the adjusted-price leak, then with harsher trading rules (added after seeing results; can only weaken them)."""
import pandas as pd, numpy as np, pickle
src = open("lab_short.py", encoding="utf8").read()
# true traded value instead of adjusted price x raw volume
src = src.replace('d = gg[["date", "adOpen", "adHigh", "adLow", "adClose", "nmVolume"]].copy(); d.columns = ["date", "open", "high", "low", "close", "volume"]',
                  'd = gg[["date", "adOpen", "adHigh", "adLow", "adClose"]].copy(); d.columns = ["date", "open", "high", "low", "close"]; d["volume"] = gg.nmValue / gg.adClose')
src = src.replace('open("short.pkl", "wb")', 'open("short_fixed.pkl", "wb")')
exec(src)
# ---- fills: no buying at the ceiling, no selling at the floor (close within 0.5% of a 7% move, or no trade)
HI = (R > .065).values; LOW = (R < -.065).values; NT = C.isna().values; ci = {c: j for j, c in enumerate(C.columns)}
def simx(score, sg, N, keep, cost, lag=1, maxrank=100):
    trade = {G.get_loc(d) + lag: d for d in sg if G.get_loc(d) + lag < len(G)}; wt = np.zeros(len(ci)); cash, out, hold = 1., [], []
    for i in range(min(trade), len(G)):
        v0 = wt.sum() + cash; wt = wt * (1 + RV[i])
        for j in np.nonzero(wt)[0]:
            if LV[j] < len(G) - 60 and i == LV[j] + 1: cash += wt[j] * .7; wt[j] = 0
        if i in trade:
            v = wt.sum() + cash; b = BY[trade[i]]; b = b[b.lqr <= maxrank]; s = b.set_index("code")[score].dropna().sort_values(ascending=False, kind="stable"); rk = {c: n + 1 for n, c in enumerate(s.index)}
            cur = [c for c in ci if wt[ci[c]] > 0]; kp = [c for c in cur if rk.get(c, 999) <= keep or LOW[i, ci[c]] or NT[i, ci[c]]]
            new = [c for c in s.index if c not in kp and not HI[i, ci[c]] and not NT[i, ci[c]]][:max(0, N - len(kp))]; tgt = kp + new; t_ = np.zeros_like(wt)
            for c in tgt: t_[ci[c]] = v / max(N, len(tgt))
            for c in cur:
                j = ci[c]
                if NT[i, j] or (LOW[i, j] and t_[j] < wt[j]) or (HI[i, j] and t_[j] > wt[j]): t_[j] = wt[j]
            over = t_.sum() - v
            if over > 0:
                fr_ = [ci[c] for c in new] or [];
                if fr_: t_[fr_] *= max(0, 1 - over / t_[fr_].sum())
            tr_ = np.abs(t_ - wt).sum(); tc = tr_ / 2 * cost; wt = t_ * (1 - tc / v); cash = v - tc - wt.sum()
        out.append((G[i], (wt.sum() + cash) / v0 - 1))
    s = pd.Series(dict(out)).iloc[1:]; return s[s.index >= S]
o = x[x.date >= "2017-12-25"].rename(columns={"sym": "code"})[["date", "code", "lqr", "ret1"] + sc]
BY = dict(tuple(o.groupby("date"))); ds = [d for d in G if d in BY and d >= pd.Timestamp(S)]
L = pickle.load(open("long.pkl", "rb")); etf = L["etf"]
mon = lambda s: (1 + s.fillna(0)).groupby(s.index.to_period("M")).prod() - 1
def st(s): nav = (1 + s).cumprod(); v = s.std() * 250**.5; return dict(CAGR=nav.iloc[-1]**(250 / len(s)) - 1, Sharpe=(s.mean() * 250 - .04) / v, maxDD=(nav / nav.cummax().clip(lower=1) - 1).min())
def tt(a, b): d = (mon(a) - mon(b)).dropna(); return d.mean() / d.std() * len(d)**.5
ew = sim("EW", S, sg=ds[::20]); rows = {}; keepser = {}
tests = {"base 0.4%": {}, "cost 0.6%": dict(cost=.006), "cost 1.0%": dict(cost=.01), "trade 2 days later": dict(lag=2), "trade 3 days later": dict(lag=3), "top 50 liquid": dict(maxrank=50), "top 30 liquid": dict(maxrank=30), "10 stocks": dict(N=10, keep=30), "20 stocks": dict(N=20, keep=60), "top50, 0.6%, 2d late, 10 stocks": dict(maxrank=50, cost=.006, lag=2, N=10, keep=30)}
for k in ("lgb10", "lgb20"):
    for nm, a in tests.items():
        p = dict(N=6, keep=18, cost=.004); p.update(a); r = pd.concat([simx(k, ds[f::20], **p) for f in (0, 5, 10, 15)], axis=1).fillna(0).mean(axis=1); keepser[(k, nm)] = r
        z = r[r.index >= "2020"]; w = r[r.index >= "2023"]; e, f_ = ew[ew.index >= "2020"], etf[etf.index >= "2020"]
        rows[(k, nm)] = {**st(z), "t_EW": tt(z, e), "t_ETF": tt(z, f_), **{a_ + "23": b_ for a_, b_ in st(w).items()}, "t_EW23": tt(w, ew[ew.index >= "2023"]), "t_ETF23": tt(w, etf[etf.index >= "2023"])}
print(pd.DataFrame(rows).T.round(2).to_string()); pickle.dump(keepser, open("stress.pkl", "wb"))
