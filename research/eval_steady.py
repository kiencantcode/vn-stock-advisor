import sys; sys.path.insert(0, "research"); sys.path.insert(0, ".")
import numpy as np, pandas as pd, pickle
src = open("research/evaluate.py", encoding="utf8").read(); exec(src[:src.index("def report")])
import lab_steady as L
Z = pickle.load(open("research/steady.pkl", "rb")); R, meta, E = Z["R"], Z["meta"], Z["etf"]; CUT = "2023-01-01"
def line(s, u, a, b):
    s, w, e = [q[(q.index >= a) & (q.index < b)] for q in (s, Z["ew"][u], E)]; d = mon(s) - mon(w)
    return {**st(s), "t_EW": t(s, w), "t_ETF": t(s, e), "IR_EW": d.mean() / d.std() * 12**.5}
dev = pd.DataFrame({c: {**line(R[c], c[2], "2018", CUT), "ov1": meta[c][0], "ov5": meta[c][1], "turn": meta[c][2]} for c in R}).T
chk = pd.DataFrame({c: line(R[c], c[2], CUT, "2027") for c in R}).T
ok = dev[dev.ov1 >= .85].sort_values("IR_EW", ascending=False); ch = ok.index[0]; pd.set_option("display.width", 220)
print("eligible", len(ok), "of", len(dev)); print(ok.head(8).round(2).to_string()); print("CHOSEN", ch); print(chk.loc[ok.head(8).index].round(2).to_string())
print("dev-check rank corr of IR", round(dev.IR_EW.corr(chk.IR_EW, method="spearman"), 2), "share of eligible beating EW", (chk.loc[ok.index].t_EW > 0).mean().round(2), "ETF", (chk.loc[ok.index].t_ETF > 0).mean().round(2))
for nm, g in (("smoothing", 1), ("score", 0), ("universe", 2), ("step", 3), ("N", 4)):
    k = [c[g] for c in dev.index]; print(nm, pd.DataFrame({"dev IR": dev.IR_EW.groupby(k).mean(), "check IR": chk.IR_EW.groupby(k).mean(), "check CAGR": chk.CAGR.groupby(k).mean(), "overlap 1d": dev.ov1.groupby(k).mean(), "5d": dev.ov5.groupby(k).mean()}).round(2).T.to_string())
for u in (100, 50): print("EW", u, {a: {k: round(v, 3) for k, v in st(Z["ew"][u][lambda q: (q.index >= a) & (q.index < b)]).items()} for a, b in (("2018", CUT), (CUT, "2027"))})
print("ETF", {a: {k: round(v, 3) for k, v in st(E[(E.index >= a) & (E.index < b)]).items()} for a, b in (("2018", CUT), (CUT, "2027"))})
M = R.groupby(R.index.to_period("M")).apply(lambda d: (1 + d).prod() - 1); print("PBO", round(pbo(M), 3), "DSR chosen", dsr(M, ch))
k, sm, u, sp, N = ch; S = L.mat(k, sm)
for c in (.006, .008): print("cost", c, {a: {q: round(v, 2) for q, v in line(L.sim(S, u, sp, N, cost=c), u, a, b).items()} for a, b in (("2018", CUT), (CUT, "2027"))})
for o in range(0, sp, 5): print("start", o, {a: {q: round(v, 2) for q, v in line(L.sim(S, u, sp, N, offs=[o]), u, a, b).items() if q in ("CAGR", "maxDD")} for a, b in (("2018", CUT), (CUT, "2027"))})
y = pd.DataFrame({"model": R[ch], "EW": Z["ew"][u], "ETF": E}); print(((1 + y).groupby(y.index.year).prod() - 1).round(3).T.to_string())
F = {h: np.log(L.CF.shift(-h) / L.CF).values for h in (5, 10, 20)}
for a, b in (("2018", CUT), (CUT, "2027")):
    o = {}
    for h in (5, 10, 20):
        bt, up, al, ic = [], [], [], []
        for i in range(L.i0, L.n - h):
            if not (pd.Timestamp(a) <= L.G[i] < pd.Timestamp(b)): continue
            od = L.order(S, i, u)
            if len(od) < 20: continue
            f = F[h][i][od]; m = np.nanmedian(f); bt.append(np.mean(f[:N] > m)); up.append(np.mean(f[:N] > 0)); al.append(np.mean(f > 0)); ic.append(pd.Series(-np.arange(len(f))).corr(pd.Series(f).rank(), method="spearman"))
        from advisor import track
        o[h] = dict(beat=np.mean(bt), up=np.mean(up), all_up=np.mean(al), ic=np.mean(ic), ic_t=track._nw_t(ic, h - 1))
    print(a, pd.DataFrame(o).round(3).to_string())
hold = []
print("typical", {"overlap1": meta[ch][0], "overlap5": meta[ch][1], "turnover/yr": meta[ch][2]})
