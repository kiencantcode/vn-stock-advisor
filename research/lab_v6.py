"""V6 (PREREGISTRATION_V6.md): chỉ báo MUA khi mọi điều kiện cùng đẹp, còn lại cầm tiền.
Chạy từ thư mục gốc sau research/lab_v5.py: python research/lab_v6.py"""
import sys, json, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path[:0] = [".", "research"]
import lab_steady as L, lab_v5 as V

G, cols, n, i0 = L.C.index, list(L.C.columns), L.n, L.i0
CF, NT, R, dead = L.CF.values, L.NT, L.R, L.dead
e = L.etf.reindex(G).ffill().values
x = pd.read_pickle(V.OUT); LQ = L.LQ
top100 = np.nan_to_num(LQ, nan=999) <= 100
P = lambda k, src: src.pivot(index="date", columns="sym", values=k).reindex(index=G, columns=cols)
ix = L.ix.set_index("date")["close"].reindex(G).ffill()
mkt = (ix > ix.rolling(200).mean()).values[:, None]
trend = (L.CF > L.CF.rolling(50, min_periods=40).mean()).values
z = V.extra(G, cols)
ep, eg, fn, up = [np.nan_to_num(P(k, z).values, nan=-9) for k in ("k_ep", "k_eg250", "f_net20", "v_up20")]
fund = (ep > 0) & (eg > 0)
flow = (fn > 0) & (up > 0.5)
score = {}
for m in ("B", "A"):
    s = P(f"{m}20", x).rank(axis=1, pct=True).rolling(20, min_periods=1).mean().where(top100)
    score[m] = s.values
    rank = s.rank(axis=1, ascending=False).values
    lv = np.nan_to_num(rank, nan=999) <= 10
    score[m + "lv"] = [lv, lv & mkt, lv & mkt & trend, lv & mkt & trend & fund, lv & mkt & trend & fund & flow]

fwd = np.full(CF.shape, np.nan); fwd[1:-20] = CF[21:] / CF[1:-20] - 1  # mua phiên i+1, giữ 20 phiên
avg = np.array([np.nanmean(fwd[i][top100[i]]) if top100[i].any() else np.nan for i in range(n)])
efwd = np.full(n, np.nan); efwd[1:-20] = e[21:] / e[1:-20] - 1


def signals(sig):
    rows = []
    for j in range(len(cols)):
        last = -99
        for i in np.flatnonzero(sig[i0:n - 22, j]) + i0:
            if i - last < 20 or NT[i + 1, j] or R[i + 1, j] > .065 or np.isnan(fwd[i, j]):
                continue
            last = i; rows.append((G[i], fwd[i, j] - .004, efwd[i], avg[i]))
    return pd.DataFrame(rows, columns=["d", "r", "f", "a"]).set_index("d").sort_index()


def sim(sig, sc):
    pos, cash, eq, out, inv = {}, 1.0, 1.0, [], []
    for i in range(i0, n):
        for j in pos: pos[j][0] *= 1 + R[i, j]
        for j in [j for j in pos if dead[i, j]]: cash += pos.pop(j)[0] * .7
        for j in [j for j, (v, t) in pos.items() if i - t >= 20 and not sig[i - 1, j] and not NT[i, j] and R[i, j] >= -.065]:
            cash += pos.pop(j)[0] * (1 - .002)
        tot = cash + sum(v for v, t in pos.values())
        cand = [j for j in np.argsort(-np.nan_to_num(sc[i - 1], nan=-9)) if sig[i - 1, j] and j not in pos and not NT[i, j] and R[i, j] <= .065]
        for j in cand[:6 - len(pos)]:
            a = min(tot / 6, cash)
            if a <= 0: break
            cash -= a; pos[j] = [a * (1 - .002), i]
        new = cash + sum(v for v, t in pos.values()); out.append(new / eq - 1); eq = new; inv.append(len(pos))
    return pd.Series(out, G[i0:]), np.array(inv)


etf = pd.Series(e, G).pct_change(fill_method=None).fillna(0)[i0:]
PER = {"2019-22": ("2019", "2023"), "2023-26": ("2023", "2027"), "2019-26": ("2019", "2027")}
cut = lambda s, a, b: s[(s.index >= a) & (s.index < b)]
res, dec = {}, {}
for m in ("B", "A"):
    for k, sig in enumerate(score[m + "lv"]):
        name = f"{m}-S{k + 1}"; r = {}; s, inv = sim(sig, score[m]); sg = signals(sig)
        for p, (a, b) in PER.items():
            q, w = cut(sg, a, b), cut(s, a, b); st = V.stats(w); yrs = len(w) / 250
            r[f"tín hiệu/tháng {p}"] = round(len(q) / (yrs * 12), 1)
            r[f"lãi TB 20 phiên {p}"] = round(float(q.r.mean()), 4) if len(q) else None
            r[f"tăng {p}"] = round(float((q.r > 0).mean()), 3) if len(q) else None
            r[f"thắng quỹ {p}"] = round(float((q.r > q.f).mean()), 3) if len(q) else None
            r[f"thắng TB mã {p}"] = round(float((q.r > q.a - .004).mean()), 3) if len(q) else None
            r[f"năm {p}"] = round(st["cagr"], 4); r[f"sụt {p}"] = round(st["maxdd"], 3)
            r[f"t quỹ {p}"] = round(V.tmon(w, cut(etf, a, b)), 2)
            r[f"không có mã {p}"] = round(float((inv[(s.index >= a) & (s.index < b)] == 0).mean()), 3)
        res[name] = r
        dec[name] = bool(all(r[f"năm {p}"] > V.stats(cut(etf, *PER[p]))["cagr"] and (r[f"thắng TB mã {p}"] or 0) > .5 for p in ("2019-22", "2023-26")) and r["t quỹ 2019-26"] >= 1.65)
        res[name]["năm theo từng năm"] = {int(y): round(float(v), 3) for y, v in ((1 + s).groupby(s.index.year).prod() - 1).items()}
res["ETF"] = {f"năm {p}": round(V.stats(cut(etf, a, b))["cagr"], 4) for p, (a, b) in PER.items()} | {f"sụt {p}": round(V.stats(cut(etf, a, b))["maxdd"], 3) for p, (a, b) in PER.items()}
res["ETF"]["năm theo từng năm"] = {int(y): round(float(v), 3) for y, v in ((1 + etf).groupby(etf.index.year).prod() - 1).items()}
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
T = pd.DataFrame({k: {q: v for q, v in r.items() if q != "năm theo từng năm"} for k, r in res.items()}).T
for p in PER: print(p); print(T[[c for c in T.columns if c.endswith(p)]].to_string())
print(pd.DataFrame({k: r["năm theo từng năm"] for k, r in res.items()}).to_string())
print("ĐẠT:", dec)
json.dump({"table": res, "pass": dec}, open("research/v6_results.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
