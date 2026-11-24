import pandas as pd, numpy as np, pickle, time
END = pd.Timestamp("2026-11-23")
exec(open("lt.py", encoding="utf8").read())
import sys; sys.path.insert(0, r"E:\vn-stock-advisor")
from advisor import data, features as FT
S = "2018-01-01"
P2 = P[P.date.isin(G)].copy(); n = P2.groupby("code").size(); liqok = P2.groupby("code").nmValue.mean().nlargest(250).index
fr = {}
for c, gg in P2[P2.code.isin(liqok)].groupby("code"):
    d = gg.rename(columns={"adOpen": "open", "adHigh": "high", "adLow": "low", "adClose": "close", "nmVolume": "volume"})
    # px has both raw and adjusted: drop raw before renaming
    d = gg[["date", "adOpen", "adHigh", "adLow", "adClose", "nmVolume"]].copy(); d.columns = ["date", "open", "high", "low", "close", "volume"]
    if len(d) >= 300: fr[c] = d.dropna()
ix = data._fetch_entrade("VNINDEX", "2012-01-01", str(END.date()))
x = FT.build_panel(fr, ix, 5)
# point-in-time universe: top 100 by 60-session median value among HOSE stocks that day
med = VAL.rolling(60, min_periods=40).median().where(FL); rk = med.rank(axis=1, ascending=False)
age = C.notna().cumsum()
rkl = rk.where(age >= 250).stack().rename("lqr"); rkl.index.names = ["date", "sym"]
x = x.merge(rkl.reset_index(), on=["date", "sym"], how="left"); x = x[x.lqr <= 100].reset_index(drop=True)
gb = x.groupby("date")
for f in FT.STOCK: x["r_" + f] = gb[f].rank(pct=True) - .5
for h in (5, 10, 20):
    fw = np.log(C.shift(-h) / C).stack(); fw.index.names = ["date", "sym"]; x = x.merge(fw.rename(f"f{h}").reset_index(), on=["date", "sym"], how="left")
    x[f"t{h}"] = x.groupby("date")[f"f{h}"].rank(pct=True) - .5; x[f"lgb{h}"] = np.nan
x["rev"] = -x.r_ret5; x["abturn"] = x.r_vol_ratio5; x["hi"] = x.r_hi52
D = np.sort(x.date.unique()); print(x.shape, len(D), flush=True)
for s in pd.date_range(S, D[-1], freq="6MS"):
    e = s + pd.DateOffset(months=6); k = int(np.searchsorted(D, s.to_datetime64())); te = (x.date >= s) & (x.date < e)
    for h in (5, 10, 20):
        tr = x[(x.date < D[k - h - 2]) & x[f"t{h}"].notna() & x.vol20.notna()]
        x.loc[te, f"lgb{h}"] = np.mean([lgb.LGBMRegressor(n_estimators=300, learning_rate=.03, num_leaves=31, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.5, reg_lambda=10, random_state=z, n_jobs=8, verbose=-1).fit(tr[FT.FEATURES], tr[f"t{h}"]).predict(x.loc[te, FT.FEATURES]) for z in range(2)], 0)
    print(s.date(), flush=True)
sc = ["lgb5", "lgb10", "lgb20", "rev", "abturn", "hi"]
ic = {k: x[x.date >= S].groupby("date").apply(lambda g: g[k].corr(g.f5, method="spearman")) for k in sc}
print({k: (round(v[v.index < "2023"].mean(), 4), round(v[v.index >= "2023"].mean(), 4)) for k, v in ic.items()})
o = x[x.date >= "2017-12-25"].rename(columns={"sym": "code"})[["date", "code"] + sc]; o.loc[:, :]
for k in sc[:3]: pass
BY = dict(tuple(o.groupby("date"))); ds = [d for d in G if d in BY and d >= pd.Timestamp(S)]
res = {}
for k in sc:
    for hold_ in (5, 10, 20):
        for N in (6, 10):
            for m in (3, 5):
                off = [0, hold_ // 2]
                res[(k, hold_, N, m)] = pd.concat([sim(k, S, N=N, keep=m * N, sg=ds[a::hold_]) for a in off], axis=1).fillna(0).mean(axis=1)
ew = sim("EW", S, sg=ds[::20])
pickle.dump(dict(R=pd.DataFrame(res), ew=ew), open("short.pkl", "wb")); print("done", len(res))
