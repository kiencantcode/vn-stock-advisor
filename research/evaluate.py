import pandas as pd, numpy as np, pickle, itertools, sys
from math import comb
from statistics import NormalDist
N01 = NormalDist(); rng = np.random.default_rng(0); CASH = .04
mon = lambda s: (1 + s.fillna(0)).groupby(s.index.to_period("M")).prod() - 1
def st(s):
    nav = (1 + s).cumprod(); n = len(s) / 250; v = s.std() * 250**.5
    return dict(CAGR=nav.iloc[-1]**(1/n) - 1, vol=v, Sharpe=(s.mean() * 250 - CASH) / v, maxDD=(nav / nav.cummax().clip(lower=1) - 1).min())
def t(a, b): d = (mon(a) - mon(b)).dropna(); return d.mean() / d.std() * len(d)**.5
def wf(R, first):
    """each January: best / top10% / all, using only earlier rows"""
    b, e, al, picks = [], [], [], {}
    for y in range(first, 2027):
        past, cur = R[R.index < f"{y}-01-01"], R[R.index.year == y]
        sh = (past.mean() * 250 - CASH) / (past.std() * 250**.5); c = sh.idxmax(); picks[y] = (c, round(sh[c], 2))
        b.append(cur[c]); e.append(cur[sh.nlargest(max(1, len(sh) // 10)).index].mean(axis=1)); al.append(cur.mean(axis=1))
    return pd.concat(b), pd.concat(e), pd.concat(al), picks
def pbo(M, S=16):
    M = M.iloc[len(M) % S:]; bl = np.array_split(np.arange(len(M)), S); X = M.values
    s1 = np.array([X[i].sum(0) for i in bl]); s2 = np.array([(X[i]**2).sum(0) for i in bl]); n = np.array([len(i) for i in bl]); lam, deg = [], []
    for c in itertools.combinations(range(S), S // 2):
        c = list(c); o = [i for i in range(S) if i not in c]
        f = lambda k: (s1[k].sum(0) / n[k].sum()) / np.sqrt(np.maximum(s2[k].sum(0) / n[k].sum() - (s1[k].sum(0) / n[k].sum())**2, 1e-12))
        a, b = f(c), f(o); j = a.argmax(); w = (b < b[j]).sum() + 1; w = w / (len(b) + 1); lam.append(np.log(w / (1 - w))); deg.append(b[j] > np.median(b))
    return float(np.mean(np.array(lam) <= 0))
def dsr(M, col, rf=CASH / 12):
    X = M - rf; sr = X.mean() / X.std(); N = M.shape[1]; cm = np.corrcoef(M.values.T); rho = (cm.sum() - N) / (N * (N - 1)); ne = rho + (1 - rho) * N
    g = .5772156649; sr0 = sr.std() * ((1 - g) * N01.inv_cdf(1 - 1 / ne) + g * N01.inv_cdf(1 - 1 / (ne * np.e))); x = X[col]; T = len(x); s = sr[col]; sk, ku = x.skew(), x.kurt() + 3
    return float(N01.cdf((s - sr0) * (T - 1)**.5 / (1 - sk * s + (ku - 1) / 4 * s * s)**.5)), round(ne, 1), round(rho, 2)
def boot(T, B, p=1 / 6):
    out = np.empty((B, T), int)
    for b in range(B):
        i = rng.integers(T)
        for k in range(T):
            out[b, k] = i; i = rng.integers(T) if rng.random() < p else (i + 1) % T
    return out
def reality(D, B=2000):
    D = D.values if hasattr(D, "values") else D; D = D.reshape(len(D), -1); T = len(D); m = D.mean(0); V = (m * T**.5).max(); ix = boot(T, B)
    W = np.array([((D[i].mean(0) - m) * T**.5).max() for i in ix]); return float((W >= V).mean())
def report(nm, R, first, bench):
    R = R.dropna(axis=1, how="all").fillna(0); ok = R.std() > 0; R = R.loc[:, ok]; print("=====", nm, R.shape, R.index[0].date(), R.index[-1].date())
    b, e, al, picks = wf(R, first); A = {"WF best (primary)": b, "WF top 10%": e, "all average": al, **{k: v[v.index >= b.index[0]] for k, v in bench.items()}}
    T = {k: {**st(s), **{"t_" + x: t(s, bench[x][bench[x].index >= b.index[0]]) if k != x else np.nan for x in bench}} for k, s in A.items()}; print(pd.DataFrame(T).T.round(3).to_string())
    for y, v in picks.items(): print("  pick", y, v)
    M = R.groupby(R.index.to_period("M")).apply(lambda d: (1 + d).prod() - 1); sh = (R.mean() * 250 - CASH) / (R.std() * 250**.5); c = sh.idxmax()
    print("best in hindsight", c, {k: round(v, 3) for k, v in st(R[c]).items()}); print("PBO", round(pbo(M), 3), "DSR", dsr(M, c))
    for k, v in bench.items():
        bm = mon(v).reindex(M.index).fillna(0); D = M.sub(bm, axis=0); print(f"vs {k}: share of settings beating it {np.mean((1+M).prod() > (1+bm).prod()):.2f}; max t {(D.mean()/D.std()*len(D)**.5).max():.2f}; reality-check p {reality(D):.3f}; primary WF p {reality((mon(b)-mon(v).reindex(mon(b).index)).dropna()):.3f}; top10% p {reality((mon(e)-mon(v).reindex(mon(e).index)).dropna()):.3f}")
    y = pd.DataFrame({k: (1 + s).groupby(s.index.year).prod() - 1 for k, s in A.items()}); print(y.T.round(3).to_string()); return b, e, R, M
L = pickle.load(open("long.pkl", "rb")); bl = {"ETF": L["etf"], "EW": L["ew"], "VNI": L["vni"]}
lb, le, LR, LM = report("LONG", L["R"], 2018, bl)
Q = pickle.load(open("short.pkl", "rb")); etf = L["etf"]; vb = {"EW": Q["ew"], "ETF": etf[etf.index >= Q["R"].index[0]]}
sb, se, SR, SM = report("SHORT", Q["R"], 2020, vb)
lev = lambda i: LR.columns.get_level_values(i) if isinstance(LR.columns, pd.MultiIndex) else [c[i] for c in LR.columns]
shp = ((LR.mean() * 250 - CASH) / (LR.std() * 250**.5)); print("median Sharpe by overlay", shp.groupby(list(lev(4))).median().round(2).to_dict(), "N", shp.groupby(list(lev(1))).median().round(2).to_dict(), "freq", shp.groupby(list(lev(2))).median().round(2).to_dict(), "univ", shp.groupby(list(lev(3))).median().round(2).to_dict())
print("median Sharpe by score"); print(shp.groupby(list(lev(0))).median().round(2).sort_values(ascending=False).to_dict())
ss = ((SR.mean() * 250 - CASH) / (SR.std() * 250**.5)); lv = lambda i: list(SR.columns.get_level_values(i)); print("short by score", ss.groupby(lv(0)).median().round(2).to_dict(), "by hold", ss.groupby(lv(1)).median().round(2).to_dict())
def mix(a, b, wa):
    d = pd.concat([a, b], axis=1).dropna(); va, vb_, out, pq = wa, 1 - wa, [], None
    for i, r in d.iterrows():
        p = (i.year, i.quarter)
        if pq and p != pq: k = va + vb_; va, vb_ = k * wa, k * (1 - wa)
        v0 = va + vb_; va *= 1 + r.iloc[0]; vb_ *= 1 + r.iloc[1]; out.append((va + vb_) / v0 - 1); pq = p
    return pd.Series(out, d.index)
c = lambda s: s[s.index >= sb.index[0]]; cash = sb * 0 + 1.04**(1/250) - 1
Mx = {"$7 WF long + $3 WF short": mix(c(lb), sb, .7), "$7 top10% long + $3 top10% short": mix(c(le), se, .7), "$7 ETF + $3 WF short": mix(c(etf), sb, .7), "$7 ETF + $3 top10% short": mix(c(etf), se, .7), "$7 WF long + $3 ETF": mix(c(lb), c(etf), .7), "$7 ETF + $3 cash": mix(c(etf), cash, .7), "$10 ETF": c(etf), "$10 WF long": c(lb), "$10 WF short": sb, "$10 EW100": c(L["ew"])}
print(pd.DataFrame({k: {**st(s), "$10 becomes": 10 * (1 + s).prod(), "t_vs_ETF": t(s, c(etf))} for k, s in Mx.items()}).T.round(3).to_string())
