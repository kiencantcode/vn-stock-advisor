import sys; sys.path[:0] = ["research", "."]
import numpy as np, pandas as pd, pickle, time, os
from multiprocessing import Pool
import lab_steady as L
cf = L.CF.values; OP = L.W("adOpen").reindex(L.G).values; LO = L.W("adLow").reindex(L.G).values
ENT = ["close", "open", "lim", "dip2", "dip5"]
EXI = {"none": (0, 0, 0), **{f"s{int(x*100)}": (x, 0, 0) for x in (.07, .1, .15, .2)}, **{f"t{int(x*100)}": (0, x, 0) for x in (.1, .15, .2, .3)}, **{f"r{int(x*100)}": (0, 0, x) for x in (.1, .15, .2)}, "s10t20": (.1, .2, 0), "s15t30": (.15, .3, 0)}
R, NT, DEAD = L.R, L.NT, L.dead
def sim(O, N, STEP, ent, ex_, cost=.004):
    sl, tp, tr = ex_; hc = cost / 2; res = np.zeros(L.n - L.i0); no = 0; dp = {"dip2": .02, "dip5": .05}.get(ent)
    for off in range(0, STEP, STEP // 5):
        no += 1; w = {}; en = {}; pk = {}; born = {}; cash = 1.; todo = None; ex = set(); lim = {}; out = np.zeros(L.n - L.i0)
        for i in range(L.i0 + off, L.n):
            Ri = R[i]; v0 = cash
            for j in w: v0 += w[j]; w[j] *= 1 + Ri[j]
            for j in [j for j in w if DEAD[i, j]]: cash += w.pop(j) * .7
            for j in list(ex):
                if j not in w: ex.discard(j)
                elif i - born[j] >= 3 and Ri[j] >= -.065 and not NT[i, j]: cash += w.pop(j) * (1 - hc); ex.discard(j)
            for j in list(lim):
                px, a, d = lim[j]
                if j in w: del lim[j]
                elif i > d: del lim[j]
                elif not NT[i, j] and LO[i, j] <= px and cash > 1e-9:
                    f = min(px, OP[i, j]); a = min(a, cash); cash -= a; w[j] = a * (1 - hc) * cf[i, j] / f; en[j] = pk[j] = f; born[j] = i; del lim[j]
            if todo is not None:
                v = sum(w.values()) + cash; rk = {j: q + 1 for q, j in enumerate(todo[:3 * N])}
                kp = [j for j in w if j in rk or Ri[j] < -.065 or NT[i, j]]; m = max(0, N - len(kp)); new = []
                if m:
                    for j in todo:
                        if j not in w and Ri[j] <= .065 and not NT[i, j]:
                            new.append(j)
                            if len(new) == m: break
                each = v / max(N, len(kp) + len(new)); nw = {}; fee = 0.
                ks = set(kp)
                for j in w:
                    a = each if j in ks else 0.
                    if NT[i, j] or (Ri[j] < -.065 and a < w[j]) or (Ri[j] > .065 and a > w[j]): a = w[j]
                    fee += abs(a - w[j]) * hc
                    if a > 0: nw[j] = a
                left = v - fee - sum(nw.values())
                if dp is None:
                    f = min(1., max(0., left) / (each * len(new) * (1 + hc))) if new else 1
                    for j in new:
                        a = each * f; p = cf[i, j]
                        if ent == "open": p = OP[i, j]
                        elif ent == "lim" and LO[i, j] <= cf[i - 1, j]: p = min(OP[i, j], cf[i - 1, j])
                        left -= a * (1 + hc); nw[j] = a * cf[i, j] / p; en[j] = pk[j] = p; born[j] = i
                    lim = {}
                else:
                    lim = {j: (cf[i - 1, j] * (1 - dp), each, i + STEP - 1) for j in new}
                    for j in list(lim):  # may fill the same day
                        px, a, d = lim[j]
                        if LO[i, j] <= px and left > 1e-9: f = min(px, OP[i, j]); a = min(a, left); left -= a; nw[j] = a * (1 - hc) * cf[i, j] / f; en[j] = pk[j] = f; born[j] = i; del lim[j]
                w = nw; cash = left; todo = None; ex = set()
            if sl or tp or tr:
                for j in w:
                    c = cf[i, j]
                    if c > pk[j]: pk[j] = c
                    g = c / en[j] - 1
                    if (sl and g <= -sl) or (tp and g >= tp) or (tr and c / pk[j] - 1 <= -tr): ex.add(j)
            out[i - L.i0] = (sum(w.values()) + cash) / v0 - 1
            if (i - L.i0 - off) % STEP == 0: todo = O[i]
        res += out
    return (res / no).astype("float32")
def job(a):
    k, sm, u = a; S = L.mat(k, sm); O = {i: list(map(int, L.order(S, i, u))) for i in range(L.i0, L.n)}; r = {}; ov = {}
    for N in (6, 10):
        ov[(k, sm, u, N)] = L.overlap(S, u, N, 1)
        for st in (5, 10, 20):
            for e in ENT:
                for x in EXI: r[(k, sm, u, st, N, e, x)] = sim(O, N, st, e, EXI[x])
    return r, ov
if __name__ == "__main__":
    t0 = time.time(); jobs = [(k, sm, u) for k in L.SC for sm in (1, 5, 10, 20) for u in (100, 50)]; Rr, ov = {}, {}
    with Pool(max(1, os.cpu_count() - 1)) as p:
        for n, (r, o) in enumerate(p.imap_unordered(job, jobs)): Rr.update(r); ov.update(o); print(n + 1, len(jobs), int(time.time() - t0), "s", flush=True)
    pickle.dump(dict(R=pd.DataFrame(Rr, index=L.G[L.i0:]), ov=ov), open("research/all.pkl", "wb")); print("done", len(Rr))
