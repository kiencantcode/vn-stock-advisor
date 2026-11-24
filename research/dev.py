import pandas as pd
END = pd.Timestamp("2022-12-31")  # 2023+ is cut off before anything is computed
exec(open("lt.py", encoding="utf8").read())
ix = vnindex(); S = "2014-07-01"
print(G[0], G[-1], len(me), X.groupby("date").size().agg(["min", "max"]).to_dict(), X[fe].notna().mean().round(2).to_dict())
ew = sim("EW", S); ir = ix.reindex(G).ffill().pct_change(); ir = ir[ir.index >= S]
T = {"EW": stat(ew), "VNINDEX": {**stat(ir), "t_ew": tex(ir, ew)}}
for k in [*K, "10 LightGBM"]:
    s = sim(k, "2016-07-01" if k[:2] == "10" else S); T[k] = {**stat(s), "t_ew": tex(s, ew), "t_vni": tex(s, ir), "Sharpe16": stat(s[s.index >= "2016-07-01"])["Sharpe"]}
print(pd.DataFrame(T).T.round(3).to_string())
ma = ix > ix.rolling(200).mean(); tr = {d: ma[ma.index <= d].iloc[-1] for d in me}
best = max(K, key=lambda k: T[k]["Sharpe"]); o = sim(best, S, trend=tr); print("best", best, "overlay", {a: round(b, 3) for a, b in stat(o).items()})
