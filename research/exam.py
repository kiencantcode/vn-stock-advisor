import pandas as pd
END = pd.Timestamp("2026-11-23")
exec(open("lt.py", encoding="utf8").read())
ix = vnindex(); S = "2023-01-01"
from advisor import data, features, model, pipeline
ir = ix.reindex(G).ffill().pct_change(); ir = ir[ir.index >= S]
et = data._fetch_entrade("E1VFVN30", "2014-01-01", "2026-11-23").set_index("date").close.reindex(G).ffill().pct_change(); et = et[et.index >= S]
ew = sim("EW", S); A = {"EW universe": ew, "VNINDEX": ir, "E1VFVN30 ETF": et}
for k in [*K, "10 LightGBM"]: A[k] = sim(k, S)
LG = A["4 VN anomalies"]
ma = ix > ix.rolling(200).mean(); tr = {d: ma[ma.index <= d].iloc[-1] for d in me}; A["4 + overlay (rejected on dev)"] = sim("4 VN anomalies", S, trend=tr)
# short sleeve: existing 5-session model, its own 31 stocks
cfg = pipeline.load_config(); core = [s for v in cfg["sectors"].values() for s in v]
fr, _ = data.load_many(core + cfg["train_extra"], 4900, "auto"); x = features.build_panel(fr, data.load("VNINDEX", 4900, "auto"), 5); x = x[x.date <= END]
o = model.walk_forward(x, set(core), 5, "2018-01-01"); o = o[o.date.isin(G)][["date", "sym", "score"]].rename(columns={"sym": "code", "score": "short"})
BYL = BY; BY = dict(tuple(o.groupby("date"))); ds = [d for d in G if d in BY and d >= pd.Timestamp("2022-12-25")]; res = []
for k in range(5): res.append(sim("short", S, N=6, keep=18, sg=ds[k::5]))
SH = pd.concat(res, axis=1).fillna(0).mean(axis=1); SH.attrs["to"] = sum(r.attrs["to"] for r in res) / 5; A["Short model (5 start days)"] = SH
o["dummy"] = 0; es = pd.concat([sim("EW", S, sg=ds[::60])], axis=1).iloc[:, 0]; A["EW of the 31 stocks"] = es; BY = BYL
def mix(a, b, wa):
    d = pd.concat([a, b], axis=1).fillna(0); q = d.index.to_period("Q"); va, vb, out, pq = wa, 1 - wa, [], None
    for (i, r), p in zip(d.iterrows(), q):
        if pq is not None and p != pq: t = va + vb; va, vb = t * wa, t * (1 - wa)
        v0 = va + vb; va *= 1 + r.iloc[0]; vb *= 1 + r.iloc[1]; out.append((va + vb) / v0 - 1); pq = p
    return pd.Series(out, d.index)
A["70% long + 30% short"] = mix(LG, SH, .7); A["70% long + 30% ETF"] = mix(LG, et, .7); A["70% long + 30% cash"] = mix(LG, LG * 0 + 1.04**(1/250) - 1, .7)
A["70% ETF + 30% short"] = mix(et, SH, .7); A["50% long + 50% short"] = mix(LG, SH, .5)
T = {k: {**stat(s), "t_ew": tex(s, ew) if k != "EW universe" else np.nan, "t_vni": tex(s, ir) if k != "VNINDEX" else np.nan, "total": (1 + s).prod() - 1} for k, s in A.items()}
print(pd.DataFrame(T).T.round(3).to_string())
Y = pd.DataFrame({k: (1 + A[k]).groupby(A[k].index.year).prod() - 1 for k in ("4 VN anomalies", "Short model (5 start days)", "70% long + 30% short", "EW universe", "VNINDEX", "E1VFVN30 ETF")}); print(Y.round(3).T.to_string())
d = (mon(LG) - mon(ew)).dropna(); print("monthly excess vs EW", round(d.mean() * 12, 4), "/yr; corr long-short", round(LG.corr(SH), 2))
import pickle; pickle.dump(A, open("exam.pkl", "wb"))
