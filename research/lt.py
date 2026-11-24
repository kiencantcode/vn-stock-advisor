import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings("ignore")
import lightgbm as lgb
P = pd.read_pickle("px.pkl"); P["date"] = pd.to_datetime(P.date)
P = P.sort_values(["code", "date"]).drop_duplicates(["code", "date"], keep="last"); P = P[P.date <= END]
w = lambda c: P.pivot(index="date", columns="code", values=c)
C, RAW, VAL = w("adClose"), w("close"), w("nmValue"); FL = w("floor") == "HOSE"
ok = C.notna().sum(axis=1) > 100; C, RAW, VAL, FL = C[ok], RAW[ok], VAL[ok], FL[ok]
R = C.pct_change(fill_method=None); R = R.where(R.abs() < .5)
CF, RF, G = C.ffill(), RAW.ffill(), C.index
F = pd.read_pickle("fs.pkl"); F = F[F.itemCode.isin([23000, 14000, 14110, 12700, 23100])]; F["fd"] = pd.to_datetime(F.fiscalDate)
F = F.sort_values("modifiedDate").drop_duplicates(["code", "itemCode", "fd"], keep="last")
Q = F.pivot(index=["code", "fd"], columns="itemCode", values="numericValue").reset_index().sort_values(["code", "fd"])
g = Q.groupby("code"); Q["ni"] = g[23000].transform(lambda s: s.rolling(4).sum()); Q["gp"] = g[23100].transform(lambda s: s.rolling(4).sum())
span = (Q.fd - g.fd.shift(3)).dt.days; Q.loc[~span.between(260, 290), ["ni", "gp"]] = np.nan
Q["av"] = Q.fd + pd.to_timedelta(np.where(Q.fd.dt.month == 12, 100, 60), unit="D"); Q = Q[Q.av <= END]
def asof_px(code, fd, M):
    if code not in M: return np.nan
    i = M.index.searchsorted(fd, side="right") - 1
    return M[code].iloc[i] if i >= 0 else np.nan
Q["rp"] = [asof_px(c, d, RF) for c, d in zip(Q.code, Q.fd)]; Q["ap"] = [asof_px(c, d, CF) for c, d in zip(Q.code, Q.fd)]
Q["mc0"] = Q[14110] / 1e4 * Q.rp * 1000
me = pd.DatetimeIndex(pd.Series(G, G).groupby(G.to_period("M")).last().values); me = me[me >= "2014-01-01"]
MR = C.ffill(limit=5).groupby(G.to_period("M")).last().pct_change(fill_method=None)
rows = []
for d in me:
    i = G.get_loc(d); liq = VAL.iloc[i-59:i+1].fillna(0).median()
    u = FL.iloc[i] & (C.iloc[:i+1].notna().sum() >= 250) & C.iloc[i].notna() & (C.iloc[max(0, i-259):i+1].notna().sum() >= 200)
    top = liq[u].nlargest(100).index; now = C.iloc[i][top]
    q = Q[(Q.av <= d) & (Q.fd >= d - pd.Timedelta(days=300))].groupby("code").last().reindex(top); mc = q.mc0 * now / q.ap
    x = pd.DataFrame(index=top)
    x["ep"] = q.ni / mc; x["roe"] = q.ni / q[14000].where(q[14000] > 0); x["gpa"] = q.gp / q[12700]
    x["lturn"] = -(VAL.iloc[i-249:i+1].mean()[top] / mc); x["hi52"] = now / CF.iloc[i-249:i+1].max()[top]
    rr = MR[MR.index <= d.to_period("M")].iloc[-36:][top]; x["lvol"] = -rr.std().where(rr.notna().sum() >= 12)
    x["mom"] = CF.iloc[i-20][top] / CF.iloc[i-250][top] - 1; x["date"] = d
    rows.append(x.rename_axis("code").reset_index())
X = pd.concat(rows, ignore_index=True); fe = ["ep", "roe", "gpa", "lturn", "hi52", "lvol", "mom"]
for c in fe:
    r = X.groupby("date")[c].rank(pct=True) - .5
    X["r_" + c] = r.fillna(0. if c == "gpa" else -.25)  # thiếu dữ liệu: hơi bất lợi; gpa không có ở ngân hàng: trung lập
K = {"1 EP": ["ep"], "2 EP+lowturn": ["ep", "lturn"], "3 EP+ROE": ["ep", "roe"], "4 VN anomalies": ["ep", "roe", "lturn", "hi52"],
     "5 LowVol": ["lvol"], "6 Momentum": ["mom"], "7 LowVol+Mom+EP": ["lvol", "mom", "ep"], "8 Quality": ["roe", "gpa"],
     "9 VN+LowVol": ["ep", "roe", "lturn", "hi52", "lvol"]}
for k, v in K.items(): X[k] = X[["r_" + c for c in v]].mean(axis=1)
f12 = CF.shift(-250) / CF - 1; f12 = f12.where(CF.shift(-250).notna())
X["y"] = [f12.at[d, c] for c, d in zip(X.code, X.date)]; X["y"] = X.groupby("date").y.rank(pct=True) - .5
X["10 LightGBM"] = np.nan; rc = ["r_" + c for c in fe]
for yr in range(2016, END.year + 1):
    s = pd.Timestamp(f"{yr}-01-01") - pd.Timedelta(days=7); i = G.searchsorted(s) - 252
    tr = X[(X.date <= G[i]) & X.y.notna()] if i > 0 else X.iloc[:0]; te = (X.date >= s) & (X.date < f"{yr+1}-01-01")
    if len(tr) < 800: continue
    X.loc[te, "10 LightGBM"] = np.mean([lgb.LGBMRegressor(n_estimators=150, learning_rate=.03, num_leaves=8, min_child_samples=200,
        subsample=.7, subsample_freq=1, colsample_bytree=.7, reg_lambda=10, random_state=z, verbose=-1).fit(tr[rc], tr.y).predict(X.loc[te, rc]) for z in range(5)], 0)
CASH = .04; BY = dict(tuple(X.groupby("date"))); cols = {c: j for j, c in enumerate(C.columns)}
LV = np.array([G.get_loc(C[c].last_valid_index()) for c in C.columns]); RV = R.fillna(0).values
def sim(score, start, N=20, keep=40, cost=.004, trend=None, sg=None):
    if sg is None:
        sg = [d for d in me if d.month in (3, 6, 9, 12)]
        sg = [max(d for d in me if d < pd.Timestamp(start))] + [d for d in sg if d >= pd.Timestamp(start)]
    trade = {G.get_loc(d) + 1: d for d in sg if G.get_loc(d) + 1 < len(G)}; mset = {G.get_loc(d) + 1: d for d in me}
    wt = np.zeros(len(cols)); cash, hold, out, tos, on = 1., [], [], 0., True
    for i in range(min(trade), len(G)):
        v0 = wt.sum() + cash; wt = wt * (1 + RV[i]); cash *= (1 + CASH) ** (1 / 250)
        for j in np.nonzero(wt)[0]:
            if LV[j] < len(G) - 60 and i == LV[j] + 1: cash += wt[j] * .7; wt[j] = 0
        v = wt.sum() + cash; ch = False
        if i in trade:
            b = BY[trade[i]]
            if score == "EW": hold = list(b.code)
            else:
                s = b.set_index("code")[score].dropna().sort_values(ascending=False, kind="stable"); rk = {c: n + 1 for n, c in enumerate(s.index)}
                kp = [c for c in hold if rk.get(c, 999) <= keep]; hold = kp + [c for c in s.index if c not in kp][:N - len(kp)]
        if trend is not None and i in mset: n = bool(trend[mset[i]]); ch = n != on; on = n
        if i in trade or ch:
            t = np.zeros_like(wt)
            if on:
                for c in hold: t[cols[c]] = v / len(hold)
            traded = np.abs(t - wt).sum(); tc = traded / 2 * cost; tos += traded / 2 / v; wt = t * (1 - tc / v); cash = v - tc - wt.sum()
        out.append((G[i], (wt.sum() + cash) / v0 - 1))
    s = pd.Series(dict(out)).iloc[1:]; s.attrs["to"] = tos / (len(s) / 250); return s[s.index >= start]
def stat(s):
    n = len(s) / 250; nav = (1 + s).cumprod(); vol = s.std() * 250**.5
    return dict(CAGR=nav.iloc[-1]**(1/n) - 1, vol=vol, Sharpe=(s.mean() * 250 - CASH) / vol, maxDD=(nav / nav.cummax().clip(lower=1) - 1).min(), turn=s.attrs.get("to", np.nan))
mon = lambda s: (1 + s).groupby(s.index.to_period("M")).prod() - 1
def tex(a, b):
    d = (mon(a) - mon(b)).dropna(); return d.mean() / d.std() * len(d)**.5
def vnindex():
    sys.path.insert(0, r"E:\vn-stock-advisor"); from advisor import data
    ix = data._fetch_entrade("VNINDEX", "2012-01-01", str(END.date())).set_index("date").close
    return ix[ix.index <= END]
