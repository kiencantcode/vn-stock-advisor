"""Xếp hạng cổ phiếu (LightGBM gộp) + khoảng giá conformal + kiểm định walk-forward."""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import FEATURES

SEEDS = 3
QUANTILES = {"y_close": (0.1, 0.5, 0.9), "y_low": (0.1, 0.5), "y_high": (0.5, 0.75)}


def fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    preds = []
    for seed in range(SEEDS):
        m = lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=500,
            subsample=0.7, subsample_freq=1, colsample_bytree=0.5, reg_lambda=10,
            random_state=seed, n_jobs=-1, verbose=-1)
        preds.append(m.fit(train[FEATURES], train["y_rank"]).predict(test[FEATURES]))
    return np.mean(preds, axis=0)


def trainable(x: pd.DataFrame) -> pd.DataFrame:
    return x[x["y_rank"].notna() & x["y_high"].notna() & x["vol20"].notna()]


def walk_forward(x: pd.DataFrame, core: set[str], horizon: int, start: str) -> pd.DataFrame:
    """Huấn luyện lại mỗi 6 tháng chỉ bằng quá khứ; bỏ horizon+2 phiên sát ranh giới (không rò rỉ nhãn)."""
    dates = np.sort(x["date"].unique())
    last = pd.Timestamp(dates[-1])
    edges = [*pd.date_range(start, last, freq="6MS"), last + pd.Timedelta(days=1)]
    out = []
    for s, e in zip(edges[:-1], edges[1:]):
        k = int(np.searchsorted(dates, s.to_datetime64()))
        if k - horizon - 2 < 250 or k >= len(dates):
            continue
        tr = trainable(x[x["date"] < dates[k - horizon - 2]])
        te = x[(x["date"] >= s) & (x["date"] < e) & x["sym"].isin(core)].copy()
        if len(tr) < 3000 or te.empty:
            continue
        te["score"] = fit_predict(tr, te)
        out.append(te)
    return pd.concat(out) if out else pd.DataFrame()


def conformal(x: pd.DataFrame, asof, horizon: int, window: int = 250) -> dict:
    """Phân vị thực nghiệm của (lợi suất / độ biến động) trong ~1 năm gần nhất, chỉ nhãn đã biết."""
    dates = np.sort(x["date"].unique())
    k = int(np.searchsorted(dates, np.datetime64(asof)))
    p = x[(x["date"] >= dates[max(0, k - window - horizon)]) & (x["date"] <= dates[max(0, k - horizon)])]
    out = {}
    for y, qs in QUANTILES.items():
        z = (p[y] / (p["vol20"] * horizon ** 0.5)).replace([np.inf, -np.inf], np.nan).dropna()
        out[y] = {q: float(np.quantile(z, q)) for q in qs}
    return out


def _t(a) -> float:
    a = np.asarray(a, dtype=float)
    return float(a.mean() / a.std(ddof=1) * len(a) ** 0.5) if len(a) > 2 and a.std() > 0 else 0.0


def _metrics(z: pd.DataFrame, cfg: dict, horizon: int) -> dict:
    pf = cfg["portfolio"]
    ic = z.dropna(subset=["y_close"]).groupby("date")[["score", "y_close"]].apply(
        lambda g: g["score"].rank().corr(g["y_close"].rank()) if len(g) > 5 else np.nan).dropna()
    hold, net, gross, turns = [], [], [], []
    for _, g in z.dropna(subset=["y_trade"]).groupby("date"):
        g = g.set_index("sym")
        rk = g["score"].rank(ascending=False, method="first").sort_values()
        keep = [s for s in hold if s in rk.index and rk[s] <= pf["keep_rank"]]
        new = [s for s in rk.index if s not in keep][: pf["top_n"] - len(keep)]
        turn, hold = len(new) / pf["top_n"], keep + new
        ex = g.loc[hold, "y_trade"].mean() - g["y_trade"].mean()
        gross.append(ex)
        net.append(ex - turn * pf["round_trip_cost"])
        turns.append(turn)
    yr, d = 250 / horizon, z.dropna(subset=["y_close"])
    return {"periods": len(net), "rank_ic": float(ic.mean()), "ic_t": _t(ic),
            "gross_excess_yr": float(np.mean(gross) * yr), "net_excess_yr": float(np.mean(net) * yr),
            "net_t": _t(net), "turnover": float(np.mean(turns)),
            "coverage80": float(((d["y_close"] >= d["lo"]) & (d["y_close"] <= d["hi"])).mean())}


def validate(x: pd.DataFrame, core: set[str], cfg: dict) -> dict:
    H, v = cfg["horizon"], cfg["validation"]
    oos = walk_forward(x, core, H, str(v["start"]))
    if oos.empty:
        return {"gate": False, "note": "không đủ dữ liệu để kiểm định"}
    days = np.sort(oos["date"].unique())[::H]  # các kỳ không chồng nhau
    oos = oos[oos["date"].isin(days)].copy()
    q = {d: conformal(x, d, H)["y_close"] for d in oos["date"].unique()}
    sg = oos["vol20"] * H ** 0.5
    oos["lo"] = oos["date"].map(lambda d: q[d][0.1]) * sg
    oos["hi"] = oos["date"].map(lambda d: q[d][0.9]) * sg
    cut, res = pd.Timestamp(v["holdout"]), {}
    for name, z in (("dev", oos[oos["date"] < cut]), ("holdout", oos[oos["date"] >= cut])):
        if z["date"].nunique() >= 20:
            res[name] = _metrics(z, cfg, H)
    h = res.get("holdout")
    res["gate"] = bool(h and h["net_t"] >= v["min_net_t"] and h["ic_t"] >= v["min_net_t"])
    return res
