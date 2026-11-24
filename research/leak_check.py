import pandas as pd, numpy as np, sys; sys.path.insert(0, r"E:\vn-stock-advisor")
from advisor import data, features, model, pipeline, track
cfg = pipeline.load_config(); core = [s for v in cfg["sectors"].values() for s in v]
fr, _ = data.load_many(core + cfg["train_extra"], 4900, "auto"); ix = data.load("VNINDEX", 4900, "auto")
p = pd.read_pickle("px.pkl"); p["date"] = pd.to_datetime(p.date); val = p.drop_duplicates(["code", "date"]).set_index(["code", "date"]).nmValue
def fixed(s, d):
    d = d.copy(); v = val.loc[s].reindex(d.date).values if s in val.index.get_level_values(0) else np.nan
    d["volume"] = np.where(np.isfinite(v) & (v > 0), v / d.close / 1000, d.volume); return d
for nm, f in (("as live (leak)", fr), ("true traded value", {s: fixed(s, d) for s, d in fr.items()})):
    x = features.build_panel(f, ix, 5); o = model.walk_forward(x, set(core), 5, "2018-01-01").dropna(subset=["y_close", "y_trade"])
    i = o.groupby("date").apply(lambda g: g.score.rank().corr(g.y_close.rank())).dropna()
    o["r"] = o.groupby("date").score.rank(ascending=False, method="first"); o["ex"] = o.y_trade - o.groupby("date").y_trade.transform("mean"); o["b"] = o.y_trade > o.groupby("date").y_trade.transform("median")
    for a, b in (("2018", "2023"), ("2023", "2027")):
        z = i[(i.index >= a) & (i.index < b)]; q = o[(o.date >= a) & (o.date < b) & (o.r <= 6)]
        print(f"{nm:18s} {a}-: IC {z.mean():.4f} t {track._nw_t(z, 4):.2f} beat {q.b.mean():.3f} gross/trade {q.ex.mean():.4f} t {track._nw_t(q.groupby('date').ex.mean(), 4):.2f}", flush=True)
