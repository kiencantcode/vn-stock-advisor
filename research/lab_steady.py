"""V3: run from the repo root. Stage 1 builds scores, stage 2 simulates (see PREREGISTRATION_V3.md)."""
import sys, os, pickle, time, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import Ridge
sys.path.insert(0, ".")
from advisor import data, features as FT, model, pipeline
p = pd.read_pickle("data/cache/vnd_px.pkl.gz"); p = p[p.date <= "2026-11-23"]
W = lambda k: p.pivot(index="date", columns="code", values=k)
C = W("adClose"); C = C[C.notna().sum(axis=1) > 100]; VAL, FL = W("nmValue").reindex(C.index), W("floor").reindex(C.index) == "HOSE"
ix = data.load("VNINDEX", 4900, "auto"); etf = data.load("E1VFVN30", 4900, "auto").set_index("date").close
OUT = "research/steady_scores.pkl"
if not os.path.exists(OUT):
    rk = VAL.rolling(60, min_periods=40).median().where(FL).rank(axis=1, ascending=False).where(C.notna().cumsum() >= 250)
    ever = rk.columns[(rk <= 100).any()]; fr = {}
    for s, g in p[p.date.isin(C.index) & p.code.isin(ever)].groupby("code"):
        d = g[["date", "adOpen", "adHigh", "adLow", "adClose"]].copy(); d.columns = ["date", "open", "high", "low", "close"]; d["volume"] = g.nmValue / g.adClose; fr[s] = d.dropna()
    x = FT.build_panel(fr, ix, 5); l = rk.stack().rename("lqr"); l.index.names = ["date", "sym"]
    x = x.merge(l.reset_index(), on=["date", "sym"], how="left"); x = x[x.lqr <= 100].reset_index(drop=True); gb = x.groupby("date")
    for f in FT.STOCK: x["r_" + f] = gb[f].rank(pct=True) - .5
    for h in (5, 10, 20):
        f = np.log(C.shift(-h) / C).stack(); f.index.names = ["date", "sym"]; x = x.merge(f.rename(f"f{h}").reset_index(), on=["date", "sym"], how="left")
        x[f"t{h}"] = x.groupby("date")[f"f{h}"].rank(pct=True) - .5
    for k in ("lgb5", "lgb10", "lgb20", "ridge20"): x[k] = np.nan
    D = np.sort(x.date.unique()); R_ = ["r_" + f for f in FT.STOCK]
    for s in pd.date_range("2017-07-01", D[-1], freq="6MS"):
        k = int(np.searchsorted(D, s.to_datetime64())); te = (x.date >= s) & (x.date < s + pd.DateOffset(months=6))
        for h in (5, 10, 20):
            tr = x[(x.date < D[k - h - 2]) & x[f"t{h}"].notna() & x.vol20.notna()]
            x.loc[te, f"lgb{h}"] = np.mean([lgb.LGBMRegressor(n_estimators=300, learning_rate=.03, num_leaves=31, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.5, reg_lambda=10, random_state=z, n_jobs=-1, verbose=-1).fit(tr[FT.FEATURES], tr[f"t{h}"]).predict(x.loc[te, FT.FEATURES]) for z in range(3)], 0)
            if h == 20: x.loc[te, "ridge20"] = Ridge(1000).fit(tr[R_].fillna(0), tr.t20).predict(x.loc[te, R_].fillna(0))
        print(s.date(), flush=True)
    S4 = ["lgb5", "lgb10", "lgb20", "ridge20"]; x = x[x.lgb5.notna()]
    x["ens"] = x.groupby("date")[S4].rank(pct=True).mean(axis=1)
    x[["date", "sym", "lqr", "f5", "f10", "f20", *S4, "ens"]].to_pickle(OUT)
x = pd.read_pickle(OUT); SC = ["lgb5", "lgb10", "lgb20", "ridge20", "ens"]
G = C.index; cols = list(C.columns); ci = {c: j for j, c in enumerate(cols)}; CF = C.ffill()
R = CF.pct_change(fill_method=None); R = R.where(R.abs() < .5).fillna(0).values; NT = C.isna().values
dead = C.isna().rolling(60).sum().values >= 60
LQ = x.pivot(index="date", columns="sym", values="lqr").reindex(index=G, columns=cols).values
def mat(k, sm):
    r = x.pivot(index="date", columns="sym", values=k).rank(axis=1, pct=True).reindex(index=G, columns=cols)
    return r.rolling(sm, min_periods=1).mean().values if sm > 1 else r.values
i0 = int(G.searchsorted(pd.Timestamp("2018-01-01"))); n = len(G)
def order(S, i, u):
    s = np.where(LQ[i] <= u, S[i], np.nan); j = np.argsort(-np.where(np.isnan(s), -9, s), kind="stable"); return j[:int((~np.isnan(s)).sum())]
def sim(S, u, step, N, cost=.004, offs=None, trace=None):
    res = []
    for off in (offs if offs is not None else range(0, step, 5)):
        w = {}; cash = 1.; todo = None; out = []; turn = 0
        for i in range(i0 + off, n):
            v0 = sum(w.values()) + cash; r = R[i]
            for j in w: w[j] *= 1 + r[j]
            for j in [j for j in w if dead[i, j]]: cash += w.pop(j) * .7
            if todo is not None:
                v = sum(w.values()) + cash; rk = {j: q + 1 for q, j in enumerate(todo)}
                kp = [j for j in w if rk.get(j, 999) <= 3 * N or r[j] < -.065 or NT[i, j]]
                new = [j for j in todo if j not in w and r[j] <= .065 and not NT[i, j]][:max(0, N - len(kp))]
                t = {j: v / max(N, len(kp) + len(new)) for j in kp + new}
                for j in w:
                    a = t.get(j, 0.)
                    if NT[i, j] or (r[j] < -.065 and a < w[j]) or (r[j] > .065 and a > w[j]): t[j] = w[j]
                ov = sum(t.values()) - v
                if ov > 0 and new:
                    f = max(0., 1 - ov / sum(t[j] for j in new))
                    for j in new: t[j] *= f
                tr = sum(abs(t.get(j, 0) - w.get(j, 0)) for j in {*t, *w}); fee = tr / 2 * cost; turn += tr / 2 / v
                w = {j: a * (1 - fee / v) for j, a in t.items() if a > 0}; cash = v - fee - sum(w.values()); todo = None
            out.append((sum(w.values()) + cash) / v0 - 1)
            if (i - i0 - off) % step == 0: todo = order(S, i, u)
        res.append(pd.Series(out, G[i0 + off:]).reindex(G[i0:]).fillna(0));
    s = pd.concat(res, axis=1).mean(axis=1); s.attrs["turn"] = turn / ((n - i0) / 250); return s
def ew(u):
    m = (LQ <= u); m = np.vstack([np.zeros((1, m.shape[1]), bool), m[:-1]]); return pd.Series(np.where(m, R, 0).sum(1) / np.maximum(m.sum(1), 1), G)[i0:]
def overlap(S, u, N, lag):
    tops = [set(order(S, i, u)[:N]) for i in range(i0, n)]; return np.mean([len(a & b) / N for a, b in zip(tops, tops[lag:])])
if __name__ == "__main__":
    res, meta, t0 = {}, {}, time.time()
    for k in SC:
        for sm in (1, 5, 10, 20):
            S = mat(k, sm)
            for u in (100, 50):
                for N in (6, 10):
                    ov = overlap(S, u, N, 1), overlap(S, u, N, 5)
                    for st in (5, 10, 20):
                        q = sim(S, u, st, N); res[(k, sm, u, st, N)] = q; meta[(k, sm, u, st, N)] = (*ov, q.attrs["turn"])
            print(k, sm, int(time.time() - t0), flush=True)
    e = etf.reindex(G).ffill().pct_change(fill_method=None)[i0:].fillna(0)
    pickle.dump(dict(R=pd.DataFrame(res), meta=meta, ew={u: ew(u) for u in (100, 50)}, etf=e), open("research/steady.pkl", "wb"))
