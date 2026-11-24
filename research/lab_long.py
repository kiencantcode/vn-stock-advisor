import pandas as pd, numpy as np, pickle, time
END = pd.Timestamp("2026-11-23")
exec(open("lt.py", encoding="utf8").read())
from sklearn.linear_model import Ridge
S = "2015-01-01"
# ---- extra signals
q4 = Q.groupby("code"); Q["sueq"] = Q[23000] - q4[23000].shift(4); Q["agr"] = Q[12700] / q4[12700].shift(4) - 1
Q.loc[~(Q.fd - q4.fd.shift(4)).dt.days.between(350, 380), ["sueq", "agr"]] = np.nan
ex = []
for d in me:
    i = G.get_loc(d); t = BY[d].code; q = Q[(Q.av <= d) & (Q.fd >= d - pd.Timedelta(days=300))].groupby("code").last().reindex(t)
    mc = (q.mc0 * C.iloc[i].reindex(t) / q.ap).values; lq = VAL.iloc[i-59:i+1].fillna(0).median().reindex(t)
    ex.append(pd.DataFrame({"date": d, "code": t.values, "bm": q[14000].values / mc, "ag": -q.agr.values, "sue": q.sueq.values / mc, "small": -mc, "lq": lq.rank(ascending=False).values}))
X = X.merge(pd.concat(ex), on=["date", "code"], how="left")
new = ["bm", "ag", "sue", "small"]
for c in new: X["r_" + c] = (X.groupby("date")[c].rank(pct=True) - .5).fillna(-.25)
sig = fe + new; rc = ["r_" + c for c in sig]; SC = {}
for c in sig: SC["s:" + c] = X["r_" + c]
th = {"V": ["ep", "bm"], "Q": ["roe", "gpa"], "L": ["lvol", "lturn"], "M": ["mom", "hi52"]}; TH = {k: X[["r_" + c for c in v]].mean(axis=1) for k, v in th.items()}
import itertools
for n in (1, 2, 3, 4):
    for cb in itertools.combinations("VQLM", n): SC["t:" + "".join(cb)] = sum(TH[c] for c in cb)
# ---- labels and walk-forward models (label end must be before the prediction month)
for H in (60, 250):
    f = (CF.shift(-H) / CF - 1).where(CF.shift(-H).notna()); X[f"y{H}"] = [f.at[d, c] for c, d in zip(X.code, X.date)]
    X[f"y{H}"] = X.groupby("date")[f"y{H}"].rank(pct=True) - .5
Z = X.reset_index(drop=True)
for H in (60, 250):
    for nm in ("ridge", "lgb"): SC[f"m:{nm}{H}"] = pd.Series(np.nan, Z.index)
for d in me[me >= pd.Timestamp("2014-11-01")]:
    if d.month not in (3, 6, 9, 12, 11): continue
    for H in (60, 250):
        i = G.get_loc(d) - H - 2
        tr = Z[(Z.date <= G[i]) & Z[f"y{H}"].notna()] if i > 0 else Z.iloc[:0]
        if len(tr) < 500: continue
        te = (Z.date == d)
        SC[f"m:ridge{H}"][te] = Ridge(50).fit(tr[rc], tr[f"y{H}"]).predict(Z.loc[te, rc])
        SC[f"m:lgb{H}"][te] = np.mean([lgb.LGBMRegressor(n_estimators=120, learning_rate=.03, num_leaves=8, min_child_samples=150, subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=10, random_state=z, n_jobs=8, verbose=-1).fit(tr[rc], tr[f"y{H}"]).predict(Z.loc[te, rc]) for z in range(3)], 0)
# IC-weighted: mean rank IC over known 36 months; signal momentum: sign of last 12 known months' IC
ic = pd.DataFrame({c: Z.groupby("date").apply(lambda g: g[c].corr(g.y60)) for c in rc})
w1, w2 = pd.Series(0., Z.index), pd.Series(0., Z.index)
for d in me:
    known = ic[ic.index <= G[max(G.get_loc(d) - 62, 0)]].dropna(how="all"); te = Z.date == d
    if len(known) >= 6:
        w1[te] = Z.loc[te, rc] @ known.tail(36).mean().clip(lower=0); w2[te] = Z.loc[te, rc] @ (known.tail(12).mean() > 0).astype(float)
SC["c:icw"], SC["c:sigmom"] = w1, w2
print(len(SC), "scores", flush=True)
for k, v in SC.items(): Z[k] = np.asarray(v)
Zb = Z
def sgs(months): s = [d for d in me if d.month in months and d >= pd.Timestamp(S)]; return [max(d for d in me if d < pd.Timestamp(S))] + s
freq = {"Q": sgs((3, 6, 9, 12)), "H": sgs((6, 12))}
# November 2014 signal starts the books; ML scores exist there (month 11/12)
ix = vnindex().reindex(G).ffill(); vr = ix.pct_change()
ma = ix > ix.rolling(200).mean(); rv = vr.rolling(20).var(); med = rv.expanding(250).median(); vm = (med / rv).clip(upper=1)
EXP = {"none": None}
for nm, ser in (("trend", ma.astype(float)), ("volm", vm)):
    e = pd.Series(np.nan, G)
    for d in me:
        j = G.get_loc(d) + 2
        if j < len(G): e.iloc[j] = ser[d]
    EXP[nm] = e.ffill().fillna(1.)
def over(s, nm):
    if nm == "none": return s
    e = EXP[nm].reindex(s.index); return e * s + (1 - e) * (1.04**(1/250) - 1) - e.diff().abs().fillna(0) * .002
res, t0 = {}, time.time()
for u in (100, 50):
    Y = Zb.copy()
    if u == 50:
        for k in SC: Y.loc[Y.lq > 50, k] = np.nan
    BY = dict(tuple(Y.groupby("date")))
    for k in SC:
        for N in (10, 20, 30):
            for fq in freq:
                try: s = sim(k, S, N=N, keep=2 * N if u == 100 else min(2 * N, 45), sg=freq[fq])
                except Exception as e: print("fail", k, N, fq, u, repr(e)[:80]); continue
                for o in EXP: res[(k, N, fq, u, o)] = over(s, o)
    print(u, len(res), int(time.time() - t0), "s", flush=True)
BY = dict(tuple(Zb.groupby("date"))); ew = sim("EW", S, sg=freq["Q"])
import sys; from advisor import data
et = data._fetch_entrade("E1VFVN30", "2014-01-01", str(END.date())).set_index("date").close.reindex(G).ffill().pct_change(); et = et[et.index >= S]
pickle.dump(dict(R=pd.DataFrame({k: v for k, v in res.items()}), ew=ew, vni=vr[vr.index >= S], etf=et), open("long.pkl", "wb"))
