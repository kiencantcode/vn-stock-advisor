import sys; sys.path[:0] = ["research", "."]
import numpy as np, pandas as pd, pickle, itertools
src = open("research/evaluate.py", encoding="utf8").read(); exec(src[:src.index("def report")])
Z = pickle.load(open("research/all.pkl", "rb")); V = pickle.load(open("research/steady.pkl", "rb")); R, ov = Z["R"].astype(float), Z["ov"]
keys = [tuple(c) for c in R.columns]; X = R.values; D = R.index; ETF, EW = V["etf"], V["ew"][100]; pd.set_option("display.width", 220)
ok = np.array([ov[(k[0], k[1], k[2], k[4])] >= .85 for k in keys]); print("settings", len(keys), "eligible", ok.sum())
V3 = keys.index(("lgb20", 20, 100, 20, 10, "close", "none"))
def cagr(m): return np.exp(np.log1p(X[m]).sum(0) * 250 / m.sum()) - 1
def sharpe(m): return (X[m].mean(0) * 250 - CASH) / (X[m].std(0) * 250**.5)
idx = {k: n for n, k in enumerate(keys)}; dims = [sorted({k[d] for k in keys}, key=str) for d in range(7)]
NB = [[idx[k[:d] + (v,) + k[d + 1:]] for d in range(7) for v in dims[d] if v != k[d]] + [n] for n, k in enumerate(keys)]; NB = np.array(NB)
def plateau(m): return cagr(m)[NB].mean(1)
P = {"A best return": cagr, "B best Sharpe": sharpe, "C plateau": plateau}
def pick(f, m, e): s = np.where(e, f(m), -9); return int(s.argmax())
def line(s, a, b):
    s, e, w = [q[(q.index >= a) & (q.index < b)] for q in (s, ETF, EW)]; return {**st(s), "t_ETF": t(s, e), "t_EW": t(s, w)}
for nm, e in (("ELIGIBLE (steady)", ok),):
    print("=====", nm); WF = {}
    for p, f in P.items():
        o = []; pk = {}
        for y in range(2020, 2027): j = pick(f, D < f"{y}-01-01", e); pk[y] = keys[j]; o.append(R.iloc[:, j][D.year == y])
        WF[p] = pd.concat(o); print(p, *[f"{y}:{tuple(map(str, k))}" for y, k in pk.items()], sep="\n   ")
        j = pick(f, D < "2023", e); print("   chosen on 2018-22:", tuple(map(str, keys[j])), {q: round(v, 3) for q, v in line(R.iloc[:, j], "2023", "2027").items()})
        j = pick(f, D < "2027", e); print("   LIVE pick (all data):", tuple(map(str, keys[j])), "full", {q: round(v, 3) for q, v in st(R.iloc[:, j]).items()})
    WF["V3"] = R.iloc[:, V3]; WF["ETF"] = ETF; WF["EW"] = EW; WF["mean of all eligible"] = R.loc[:, e].mean(axis=1)
    for a in ("2020", "2023"): print(a, pd.DataFrame({k: line(v, a, "2027") if k not in ("ETF", "EW") else st(v[v.index >= a]) for k, v in WF.items()}).T.round(3).to_string())
    print(pd.DataFrame({k: (1 + v).groupby(v.index.year).prod() - 1 for k, v in WF.items()}).loc[2020:].T.round(2).to_string())
    d, c = cagr(D < "2023"), cagr(D >= "2023"); print("rank corr of return 18-22 vs 23-26:", round(pd.Series(d[e]).corr(pd.Series(c[e]), method="spearman"), 3), "share above ETF 23-26:", (c[e] > st(ETF[ETF.index >= "2023"])["CAGR"]).mean().round(3))
    for g, lab in ((5, "entry"), (6, "exit"), (0, "score"), (1, "smooth"), (3, "step"), (4, "N"), (2, "univ")):
        kk = np.array([str(k[g]) for k in keys]); print(lab, pd.DataFrame({"18-22": pd.Series(d[e]).groupby(kk[e]).mean(), "23-26": pd.Series(c[e]).groupby(kk[e]).mean()}).round(3).T.to_string())
M = R.loc[:, ok].groupby(R.index.to_period("M")).apply(lambda q: (1 + q).prod() - 1); print("PBO (12 blocks)", pbo(M, 12))
bm = mon(ETF).reindex(M.index); DD = M.sub(bm, axis=0).values; T_ = len(DD); m = DD.mean(0); VV = (m * T_**.5).max(); print("reality check vs ETF p", np.mean([((DD[i].mean(0) - m) * T_**.5).max() >= VV for i in boot(T_, 500)]))
j = pick(cagr, D < "2027", ok); print("DSR of hindsight best", dsr(M, M.columns[int(np.flatnonzero(ok).tolist().index(j))]))
