"""V5 (PREREGISTRATION_V5.md): thêm khối lượng, khối ngoại, kết quả kinh doanh vào mô hình danh sách ổn định.
Chạy từ thư mục gốc: python research/lab_v5.py   (giai đoạn 1 lưu research/v5_scores.pkl, giai đoạn 2 in kết quả)."""
import sys, os, json, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, lightgbm as lgb
sys.path[:0] = [".", "research"]
from advisor import features as FT
import lab_steady as L

OUT = "research/v5_scores.pkl"
VOL = "v_up20 v_shock v_trend v_pvcorr v_clv v_wret".split()
FOR = "f_net5 f_net20 f_net60 f_share20 f_room f_own20".split()
FUN = "k_ep k_bp k_sp k_size k_roe k_eg250 k_eg63 k_sg250".split()
BASE = FT.FEATURES
SETS = {"B": BASE, "V": BASE + ["r_" + f for f in VOL], "F": BASE + ["r_" + f for f in FOR],
        "K": BASE + ["r_" + f for f in FUN], "A": BASE + ["r_" + f for f in VOL + FOR + FUN]}


def extra(G, cols) -> pd.DataFrame:
    p = L.p; W = lambda k: p.pivot(index="date", columns="code", values=k).reindex(index=G, columns=cols)
    C, O, H, Lo, V = W("adClose"), W("adOpen"), W("adHigh"), W("adLow"), W("nmValue")
    r = C.pct_change(fill_method=None); V = V.where(C.notna())
    s20 = V.rolling(20, min_periods=15).sum()
    out = {"v_up20": V.where(r > 0, 0).rolling(20, min_periods=15).sum() / s20,
           "v_shock": np.log(V / V.rolling(60, min_periods=40).median()),
           "v_trend": np.log(V.rolling(5, min_periods=4).mean() / V.rolling(20, min_periods=15).mean()),
           "v_pvcorr": r.rolling(20, min_periods=15).corr(np.log(V.where(V > 0)).diff()),
           "v_clv": (((2 * C - H - Lo) / (H - Lo).where(H > Lo)).fillna(0) * V).rolling(20, min_periods=15).sum() / s20,
           "v_wret": (r * V).rolling(20, min_periods=15).sum() / s20 - r.rolling(20, min_periods=15).mean()}
    E = pd.read_pickle("data/cache/vnd_extra.pkl.gz"); f, k = E["foreign"], E["ratios"]
    Fw = lambda c: f.pivot(index="date", columns="code", values=c).reindex(index=G, columns=cols)
    start = f.groupby("code")["date"].min().reindex(cols)
    live = pd.DataFrame({c: G >= start[c] if pd.notna(start[c]) else np.zeros(len(G), bool) for c in cols}, index=G) & C.notna()
    net, gross = Fw("netVal").fillna(0).where(live), (Fw("buyVal").fillna(0) + Fw("sellVal").fillna(0)).where(live)
    tot, cur = Fw("totalRoom").ffill(limit=10), Fw("currentRoom").ffill(limit=10)
    for n in (5, 20, 60):
        out[f"f_net{n}"] = net.rolling(n, min_periods=int(n * .75)).sum() / V.rolling(n, min_periods=int(n * .75)).sum()
    out["f_share20"] = gross.rolling(20, min_periods=15).sum() / (2 * s20)
    out["f_room"] = (cur / tot.where(tot > 0)).where(live)
    out["f_own20"] = ((cur.shift(20) - cur) / tot.where(tot > 0)).where(live)
    K = lambda c: k.pivot(index="date", columns="code", values=c).reindex(columns=cols).reindex(G, method="ffill", limit=5).shift(1)  # dùng trễ 1 phiên
    pe, pb, ps, mc = K("pe"), K("pb"), K("ps"), K("mcap")
    nz = lambda q: q.where(q.abs() > 1e-9)
    Eg, B, S = mc / nz(pe), mc / nz(pb), mc / nz(ps)
    out.update({"k_ep": 1 / nz(pe), "k_bp": 1 / nz(pb), "k_sp": 1 / nz(ps), "k_size": np.log(mc.where(mc > 0)),
                "k_roe": Eg / B.where(B > 0), "k_eg250": (Eg - Eg.shift(250)) / B.where(B > 0),
                "k_eg63": (Eg - Eg.shift(63)) / B.where(B > 0), "k_sg250": np.log((S / S.shift(250)).where(S.shift(250) > 0))})
    z = pd.concat({n: q.replace([np.inf, -np.inf], np.nan).stack() for n, q in out.items()}, axis=1)
    z.index.names = ["date", "sym"]; return z.reset_index()


def stage1():
    G, cols = L.C.index, list(L.C.columns)
    rk = L.VAL.rolling(60, min_periods=40).median().where(L.FL).rank(axis=1, ascending=False).where(L.C.notna().cumsum() >= 250)
    ever = rk.columns[(rk <= 100).any()]; fr = {}
    for s, g in L.p[L.p.date.isin(G) & L.p.code.isin(ever)].groupby("code"):
        d = g[["date", "adOpen", "adHigh", "adLow", "adClose"]].copy(); d.columns = ["date", "open", "high", "low", "close"]; d["volume"] = g.nmValue / g.adClose; fr[s] = d.dropna()
    x = FT.build_panel(fr, L.ix, 5); l = rk.stack().rename("lqr"); l.index.names = ["date", "sym"]
    x = x.merge(l.reset_index(), on=["date", "sym"], how="left"); x = x[x.lqr <= 100].reset_index(drop=True)
    x = x.merge(extra(G, cols), on=["date", "sym"], how="left"); gb = x.groupby("date")
    for f in FT.STOCK + VOL + FOR + FUN: x["r_" + f] = gb[f].rank(pct=True) - .5
    print("phủ dữ liệu 2019+:", {f: round(x.loc[x.date >= "2019", f].notna().mean(), 2) for f in VOL + FOR + FUN}, flush=True)
    for h in (5, 20):
        q = np.log(L.C.shift(-h) / L.C).stack(); q.index.names = ["date", "sym"]; x = x.merge(q.rename(f"f{h}").reset_index(), on=["date", "sym"], how="left")
        x[f"t{h}"] = x.groupby("date")[f"f{h}"].rank(pct=True) - .5
    jobs = [(n, 20) for n in SETS] + [("B", 5), ("A", 5)]
    for n, h in jobs: x[f"{n}{h}"] = np.nan
    D = np.sort(x.date.unique())
    for s in pd.date_range("2017-07-01", D[-1], freq="6MS"):
        k = int(np.searchsorted(D, s.to_datetime64())); te = (x.date >= s) & (x.date < s + pd.DateOffset(months=6))
        for n, h in jobs:
            tr = x[(x.date < D[k - h - 2]) & x[f"t{h}"].notna() & x.vol20.notna()]
            x.loc[te, f"{n}{h}"] = np.mean([lgb.LGBMRegressor(n_estimators=300, learning_rate=.03, num_leaves=31, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.5, reg_lambda=10, random_state=z, n_jobs=-1, verbose=-1).fit(tr[SETS[n]], tr[f"t{h}"]).predict(x.loc[te, SETS[n]]) for z in range(3)], 0)
        print(s.date(), flush=True)
    keep = ["date", "sym", "lqr", "f5", "f20"] + [f"{n}{h}" for n, h in jobs]
    x.loc[x["B20"].notna(), keep].to_pickle(OUT)
    # tầm quan trọng của đặc trưng mới trong lần học cuối
    tr = x[(x.date < D[-22]) & x.t20.notna() & x.vol20.notna()]
    m = lgb.LGBMRegressor(n_estimators=300, learning_rate=.03, num_leaves=31, min_child_samples=500, subsample=.7, subsample_freq=1, colsample_bytree=.5, reg_lambda=10, random_state=0, n_jobs=-1, verbose=-1, importance_type="gain").fit(tr[SETS["A"]], tr.t20)
    imp = pd.Series(m.feature_importances_, SETS["A"]); (imp / imp.sum()).sort_values(ascending=False).to_csv("research/v5_importance.csv")


def stats(s):
    s = s[s.index.notna()]; y = len(s) / 250; eq = (1 + s).cumprod()
    return {"cagr": float(eq.iloc[-1] ** (1 / y) - 1), "maxdd": float((eq / eq.cummax() - 1).min())}


def tmon(a, b):
    d = ((1 + a).groupby(a.index.to_period("M")).prod() - (1 + b).groupby(b.index.to_period("M")).prod()).dropna()
    return float(d.mean() / d.std(ddof=1) * len(d) ** .5)


def stage2():
    x = pd.read_pickle(OUT); G, cols = L.C.index, list(L.C.columns)
    etf = L.etf.reindex(G).ffill().pct_change(fill_method=None).fillna(0)
    P = {"2019-22": ("2019", "2023"), "2023-26": ("2023", "2027"), "2019-26": ("2019", "2027")}
    cut = lambda s, a, b: s[(s.index >= a) & (s.index < b)]
    res, ser = {}, {}
    m = x.groupby(x.date.dt.to_period("M")).date.transform("min") == x.date  # một ngày mỗi tháng, IC không chồng nhiều
    for n, h in [(n, 20) for n in SETS] + [("B", 5), ("A", 5)]:
        k = f"{n}{h}"; ic = x[m].groupby("date").apply(lambda g: g[k].corr(g[f"f{h}"], method="spearman"))
        r = {}
        for p, (a, b) in P.items():
            q = cut(ic, a, b); r[f"IC {p}"] = round(float(q.mean()), 4); r[f"IC t {p}"] = round(float(q.mean() / q.std() * len(q) ** .5), 2)
        if h == 20:
            S = x.pivot(index="date", columns="sym", values=k).rank(axis=1, pct=True).reindex(index=G, columns=cols).rolling(20, min_periods=1).mean().values
            s = L.sim(S, 100, 5, 6); ser[n] = s
            for p, (a, b) in P.items():
                st = stats(cut(s, a, b)); r[f"năm {p}"] = round(st["cagr"], 4); r[f"sụt {p}"] = round(st["maxdd"], 3)
                r[f"t quỹ {p}"] = round(tmon(cut(s, a, b), cut(etf, a, b)), 2)
            CF = L.CF.values; e = L.etf.reindex(G).ffill().values; wk = []
            for i in range(L.i0, L.n - 7, 5):
                o = L.order(S, i, 100)[:6]; g = [CF[i + 6, j] / CF[i + 1, j] - 1 - .004 for j in o if not L.NT[i + 1, j]]
                wk.append((G[i], np.mean(g), e[i + 6] / e[i + 1] - 1))
            w = pd.DataFrame(wk, columns=["d", "r", "f"]).set_index("d")
            for p, (a, b) in list(P.items())[:2]:
                q = cut(w, a, b); r[f"tuần lãi TB {p}"] = round(float(q.r.mean()), 4); r[f"tuần thắng quỹ {p}"] = round(float((q.r > q.f).mean()), 3)
        res[k] = r
    for p, (a, b) in P.items():
        res["ETF"] = {**res.get("ETF", {}), f"năm {p}": round(stats(cut(etf, a, b))["cagr"], 4), f"sụt {p}": round(stats(cut(etf, a, b))["maxdd"], 3)}
    T = pd.DataFrame(res).T; pd.set_option("display.width", 250); print(T.to_string())
    dec = {}
    for n in "VFKA":
        c1 = all(res[f"{n}20"][f"năm {p}"] > res["B20"][f"năm {p}"] for p in ("2019-22", "2023-26"))
        c2 = all(res[f"{n}20"][f"IC {p}"] > res["B20"][f"IC {p}"] for p in ("2019-22", "2023-26"))
        t = tmon(cut(ser[n], "2019", "2027"), cut(ser["B"], "2019", "2027")); dec[n] = {"năm cao hơn cả hai giai đoạn": c1, "IC cao hơn cả hai": c2, "t so với B": round(t, 2), "đạt": bool(c1 and c2 and t >= 1.65)}
    print(json.dumps(dec, ensure_ascii=False, indent=1))
    yr = pd.DataFrame({n: (1 + s).groupby(s.index.year).prod() - 1 for n, s in ser.items()} | {"ETF": (1 + etf[L.i0:]).groupby(etf[L.i0:].index.year).prod() - 1}).round(3)
    print(yr.to_string())
    json.dump({"table": res, "decision": dec, "years": yr.to_dict()}, open("research/v5_results.json", "w", encoding="utf8"), ensure_ascii=False, indent=1, default=str)


if __name__ == "__main__":
    if not os.path.exists(OUT):
        stage1()
    stage2()
