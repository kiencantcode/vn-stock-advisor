"""V7 (PREREGISTRATION_V7.md): đổi điều kiện thị trường và cách dùng tiền mặt cho tín hiệu B-S5.
Chạy từ thư mục gốc sau research/lab_v5.py: python research/lab_v7.py"""
import sys, json, warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
sys.path[:0] = [".", "research"]
import lab_steady as L, lab_v5 as V

G, cols, n, i0 = L.C.index, list(L.C.columns), L.n, L.i0
CF, NT, R, dead = L.CF.values, L.NT, L.R, L.dead
e = L.etf.reindex(G).ffill()
er = e.pct_change(fill_method=None).fillna(0).values
x = pd.read_pickle(V.OUT); top100 = np.nan_to_num(L.LQ, nan=999) <= 100
P = lambda k, src: src.pivot(index="date", columns="sym", values=k).reindex(index=G, columns=cols)
ix = L.ix.set_index("date")["close"].reindex(G).ffill()
a50, a100, a200 = (ix.rolling(k).mean() for k in (50, 100, 200))
band, on = [], False
for v, m in zip(ix.values, a200.values):
    if not np.isnan(m):
        on = v > m if not on else v > m * 0.97
    band.append(on)
br = ((L.CF > L.CF.rolling(50, min_periods=40).mean()).values & top100).sum(1) / np.maximum(top100.sum(1), 1)
MK = {"M0": (ix > a200).values, "M1": (ix > a100).values, "M2": (ix > a50).values, "M3": (a50 > a200).values,
      "M4": ((ix > a200) | ((ix > a50) & (ix > ix.shift(20)))).values, "M5": np.array(band), "M6": br > .5, "M7": np.ones(n, bool)}
trend = (L.CF > L.CF.rolling(50, min_periods=40).mean()).values
z = V.extra(G, cols)
ep, eg, fn, up = [np.nan_to_num(P(k, z).values, nan=-9) for k in ("k_ep", "k_eg250", "f_net20", "v_up20")]
s = P("B20", x).rank(axis=1, pct=True).rolling(20, min_periods=1).mean().where(top100)
sc = s.values
base = (np.nan_to_num(s.rank(axis=1, ascending=False).values, nan=999) <= 10) & trend & (ep > 0) & (eg > 0) & (fn > 0) & (up > .5)


def sim(mk, park):
    pos, cash, ev, eq, out = {}, 1.0, 0.0, 1.0, []
    sig = base & mk[:, None]
    for i in range(i0, n):
        for j in pos: pos[j][0] *= 1 + R[i, j]
        ev *= 1 + er[i]
        for j in [j for j in pos if dead[i, j]]: cash += pos.pop(j)[0] * .7
        for j in [j for j, (v, t) in pos.items() if i - t >= 20 and not sig[i - 1, j] and not NT[i, j] and R[i, j] >= -.065]:
            cash += pos.pop(j)[0] * (1 - .002)
        tot = cash + ev + sum(v for v, t in pos.values())
        cand = [j for j in np.argsort(-np.nan_to_num(sc[i - 1], nan=-9)) if sig[i - 1, j] and j not in pos and not NT[i, j] and R[i, j] <= .065]
        for j in cand[:6 - len(pos)]:
            a = tot / 6
            if cash < a and ev > 0:  # bán bớt quỹ để có tiền mua cổ phiếu
                q = min(ev, a - cash); ev -= q; cash += q * (1 - .001)
            a = min(a, cash)
            if a <= 0: break
            cash -= a; pos[j] = [a * (1 - .002), i]
        if park and mk[i - 1] and cash > 0: ev += cash * (1 - .001); cash = 0.0
        elif ev > 0 and not (park and mk[i - 1]): cash += ev * (1 - .001); ev = 0.0
        new = cash + ev + sum(v for v, t in pos.values()); out.append(new / eq - 1); eq = new
    return pd.Series(out, G[i0:])


etf = pd.Series(er, G)[i0:]
PER = {"2019-22": ("2019", "2023"), "2023-26": ("2023", "2027"), "2019-26": ("2019", "2027")}
cut = lambda q, a, b: q[(q.index >= a) & (q.index < b)]
ser = {f"{m}-{c}": sim(MK[m], c == "E") for m in MK for c in "CE"}
ser["Quỹ"] = etf
res = {}
for k, q in ser.items():
    r = {}
    for p, (a, b) in PER.items():
        st = V.stats(cut(q, a, b)); r[f"năm {p}"] = round(st["cagr"], 4); r[f"sụt {p}"] = round(st["maxdd"], 3)
    r["t với M0-C"] = round(V.tmon(cut(q, "2019", "2027"), cut(ser["M0-C"], "2019", "2027")), 2) if k != "M0-C" else None
    r["t với quỹ 2023-26"] = round(V.tmon(cut(q, "2023", "2027"), cut(etf, "2023", "2027")), 2) if k != "Quỹ" else None
    res[k] = r
b0 = res["M0-C"]
ok = {k: bool(all(r[f"năm {p}"] > b0[f"năm {p}"] for p in ("2019-22", "2023-26")) and r["sụt 2019-26"] >= b0["sụt 2019-26"] - .05 and (r["t với M0-C"] or 0) >= 1.65)
      for k, r in res.items() if k not in ("M0-C", "Quỹ")}
pd.set_option("display.width", 250)
print(pd.DataFrame(res).T.to_string())
yr = pd.DataFrame({k: (1 + q).groupby(q.index.year).prod() - 1 for k, q in ser.items()}).round(3)
print(yr.to_string())
win = max((k for k in ok if ok[k]), key=lambda k: res[k]["năm 2019-26"], default=None)
print("ĐẠT:", [k for k in ok if ok[k]], "CHỌN:", win)
json.dump({"table": res, "years": {k: {int(y): float(v) for y, v in yr[k].items()} for k in yr}, "pass": ok, "pick": win},
          open("research/v7_results.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
