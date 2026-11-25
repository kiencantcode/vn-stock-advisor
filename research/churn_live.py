"""How much does the live 31-stock list change per day? (walk-forward, 3 seeds, as live)"""
import sys; sys.path.insert(0, ".")
import pandas as pd, numpy as np
from advisor import data, features, model, pipeline
cfg = pipeline.load_config(); core = {s for v in cfg["sectors"].values() for s in v}
fr, _ = data.load_many([*core, *cfg["train_extra"]], 4900, "auto"); x = features.build_panel(fr, data.load("VNINDEX", 4900, "auto"), 5)
o = model.walk_forward(x, core, 5, "2018-01-01"); S = o.pivot(index="date", columns="sym", values="score")
for n, a in (("2018-22", S[S.index < "2023"]), ("2023-26", S[S.index >= "2023"])):
    top = [set(r.dropna().nlargest(6).index) for _, r in a.iterrows()]; rc = a.rank(axis=1)
    f = lambda k: np.mean([len(p & q) / 6 for p, q in zip(top, top[k:])])
    print(n, "top-6 overlap 1d %.2f 5d %.2f 10d %.2f" % (f(1), f(5), f(10)), "rank corr 1d %.2f 5d %.2f" % (rc.corrwith(rc.shift(1), axis=1).mean(), rc.corrwith(rc.shift(5), axis=1).mean()))
