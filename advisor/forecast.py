"""Dự báo chuỗi thời gian từng mã, phiên +1..+5. Mỗi lần chạy học lại từ giá thật mới nhất.

- Đường giữa: các mô hình (Holt, ridge, LightGBM trên chuỗi trễ) thi đấu với "giá không đổi" trên 500 phiên gần nhất;
  chỉ thay thế khi thắng có ý nghĩa thống kê.
- Dải giá: dự báo biến động HAR + hiệu chỉnh conformal 250 phiên gần nhất.
"""
from __future__ import annotations

import os

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from . import data
from .report import ROOT
from .track import MIN_DAYS, _nw_t

VERSION, H = "ts1", 5
LOG = os.path.join(ROOT, "output", "history", "forecasts.csv")
QS = {"lo80": 0.1, "lo50": 0.25, "hi50": 0.75, "hi80": 0.9}
NAMES = {"rw": "giá không đổi", "holt": "Holt", "ridge": "Ridge", "lgb": "LightGBM"}
EVAL, CALIB, BLOCK, MIN_T = 500, 250, 125, 2.4
MIN_SESSIONS = 1300
EPS = 1e-12


def _wide(frames, col):
    return np.log(pd.concat({s: d.set_index("date")[col] for s, d in frames.items()}, axis=1, sort=True))


def _holt(c: np.ndarray, a=0.8, b=0.05, phi=0.9):
    lev, tr = np.full(c.shape, np.nan), np.full(c.shape, np.nan)
    lv, t = np.full(c.shape[1], np.nan), np.zeros(c.shape[1])
    for i, x in enumerate(c):
        p = lv + phi * t
        nl = a * x + (1 - a) * p
        nt = b * (nl - lv) + (1 - b) * phi * t
        ok, new = ~np.isnan(x), np.isnan(lv)
        t = np.where(ok, np.where(new, 0, nt), t)
        lv = np.where(ok, np.where(new, x, nl), lv)
        lev[i], tr[i] = lv, t
    return lev, tr


def _fit_rows(X, y, lo, hi):
    x, t = X[lo:hi].reshape(-1, X.shape[-1]), y[lo:hi].ravel()
    ok = np.isfinite(x).all(1) & np.isfinite(t)
    return x[ok], t[ok]


def _predict(m, X, lo, hi):
    x = X[lo:hi].reshape(-1, X.shape[-1])
    ok, out = np.isfinite(x).all(1), np.full(len(x), np.nan)
    if ok.any():
        out[ok] = m.predict(x[ok])
    return out.reshape(hi - lo, X.shape[1])


def build(frames: dict, index, core: set[str]) -> dict:
    C, Hi, Lo, O = (_wide(frames, k) for k in ("close", "high", "low", "open"))
    n, S = len(C), list(C.columns)
    if n < MIN_SESSIONS:
        raise ValueError(f"cần ít nhất {MIN_SESSIONS} phiên, có {n}")
    ci = [j for j, s in enumerate(S) if s in core]
    R = C.diff()
    if index is not None:
        M = np.log(index.set_index("date")["close"]).reindex(C.index).ffill().diff()
    else:
        M = R.mean(axis=1)
    v20 = R.rolling(20).std().replace(0, np.nan)
    ms = M.rolling(20).std()

    def spread(s):
        return np.repeat(s.values[:, None], len(S), 1)

    lags = [(R.shift(k) / v20).values for k in range(20)] + [spread(M.shift(k) / ms) for k in range(10)]
    lags += [((C - C.shift(k)) / (v20 * k ** 0.5)).values for k in (5, 20, 60, 120)]
    X = np.clip(np.stack(lags, -1), -6, 6)
    rs = (Hi - Lo) ** 2 / (4 * np.log(2)) + (O - C.shift()) ** 2
    lr = np.log(rs + 1e-6)
    V = np.stack([lr.rolling(w).mean().values for w in (1, 5, 22, 66)]
                 + [spread(lr.mean(axis=1).rolling(w).mean()) for w in (1, 5, 22)]
                 + [np.log(v20.values)], -1)
    lev, tr = _holt(C.values)
    Y = {h: (C.shift(-h) - C).values for h in range(1, H + 1)}
    first = n - EVAL - CALIB - H
    starts = list(range(first, n, BLOCK))
    P = {m: {} for m in NAMES}
    HV = {}
    for h in Y:
        sc = v20.values * h ** 0.5
        P["rw"][h] = np.zeros(C.shape)
        P["holt"][h] = 0.5 * (lev + tr * sum(0.9 ** k for k in range(1, h + 1)) - C.values)
        for m in ("ridge", "lgb"):
            P[m][h] = np.full(C.shape, np.nan)
        HV[h] = np.full(C.shape, np.nan)
        yz, ya = np.clip(Y[h] / sc, -4, 4), np.log(np.abs(Y[h]) + 1e-3)
        # thêm n-1: lần học cuối dùng mọi kết quả đã biết để dự báo phiên mới nhất
        edges = [*[(s, min(s + BLOCK, n - 1)) for s in starts if s < n - 1], (n - 1, n)]
        for a, b in edges:
            end = a - h  # nhãn của dòng end-1 kết thúc ở phiên a-1: không dùng tương lai
            x, t = _fit_rows(X, yz, 250, end)
            P["ridge"][h][a:b] = 0.5 * _predict(Ridge(5000).fit(x, t), X, a, b) * sc[a:b]
            g = lgb.LGBMRegressor(n_estimators=150, learning_rate=0.03, num_leaves=15, min_child_samples=1000,
                                  colsample_bytree=0.5, reg_lambda=10, random_state=0, n_jobs=-1, verbose=-1)
            P["lgb"][h][a:b] = 0.5 * _predict(g.fit(x, t), X, a, b) * sc[a:b]
            x, t = _fit_rows(V, ya, 250, end)
            HV[h][a:b] = np.exp(_predict(Ridge(1).fit(x, t), V, a, b))
    # --- thi đấu: sai số so với "giá không đổi" trên EVAL phiên đã biết kết quả
    w = slice(n - EVAL - H, n - H)
    table, best = {}, "rw"
    for m in NAMES:
        gains = np.zeros(EVAL)
        base = 0.0
        for h in Y:
            y, f = Y[h][w][:, ci], P[m][h][w][:, ci]
            f = np.where(np.isfinite(f), f, 0)
            gains += np.nanmean(np.abs(y) - np.abs(y - f), axis=1)
            base += np.nanmean(np.abs(y))
        table[m] = {"gain": float(gains.mean() / base), "t": 0.0 if m == "rw" else _nw_t(gains, H - 1)}
        if m != "rw" and table[m]["t"] >= MIN_T and table[m]["gain"] > table[best]["gain"]:
            best = m
    # --- dải giá + độ phủ ngoài mẫu
    cover, rows = {}, []
    for h in Y:
        z = (Y[h] - P[best][h]) / (HV[h] + EPS)

        def quant(i):
            q = z[max(first, i - h - CALIB + 1):i - h + 1]
            return np.nanquantile(q, list(QS.values()))

        hit = []
        for i in range(n - EVAL - H, n - H):
            q = quant(i)
            lo, hi = P[best][h][i] + q[0] * HV[h][i], P[best][h][i] + q[-1] * HV[h][i]
            y = Y[h][i]
            ok = np.isfinite(y[ci]) & np.isfinite(lo[ci])
            hit.append(((y >= lo) & (y <= hi))[ci][ok])
        cover[h] = float(np.concatenate(hit).mean())
        q = quant(n - 1)
        for j in ci:
            c, sg = P[best][h][n - 1, j], HV[h][n - 1, j]
            if np.isfinite(c) and np.isfinite(sg) and np.isfinite(C.values[n - 1, j]):
                rows.append({"sym": S[j], "h": h, "model": best, "center": c,
                             **{k: c + v * sg for k, v in zip(QS, q)}})
    f = pd.DataFrame(rows)
    f.insert(0, "asof", C.index[-1])
    f["close"] = f["sym"].map(np.exp(C.iloc[-1]))
    return {"f": f, "table": table, "best": best, "cover": cover}


def summary(r: dict) -> list[str]:
    out = [f"Đường giữa đang dùng: {NAMES[r['best']]}. Sai số so với 'giá không đổi' trên {EVAL} phiên gần nhất: "
           + ", ".join(f"{NAMES[m]} {v['gain']:+.2%} (t={v['t']:.1f})" for m, v in r["table"].items() if m != "rw")
           + " (dương = tốt hơn)"]
    out.append("Độ phủ dải 80% ngoài mẫu: " + ", ".join(f"+{h}: {c:.0%}" for h, c in r["cover"].items()))
    return out


def append(r: dict, path: str = LOG) -> bool:
    new = r["f"].copy()
    new.insert(0, "logged_at", data.vn_now().isoformat(timespec="seconds"))
    new.insert(1, "version", VERSION)
    if os.path.exists(path):
        old = pd.read_csv(path, parse_dates=["asof"])
        if ((old["asof"] == new["asof"].iloc[0]) & (old["version"] == VERSION)).any():
            return False
        new = pd.concat([old, new], ignore_index=True)
    new["asof"] = new["asof"].dt.strftime("%Y-%m-%d")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)
    return True


def score(frames: dict, path: str = LOG) -> list[str]:
    """Chấm dự báo đã ghi bằng giá thật (chỉ bản ghi trước 9:00 phiên kế tiếp)."""
    if not os.path.exists(path):
        return []
    log = pd.read_csv(path, parse_dates=["asof"])
    log = log[log["version"] == VERSION]
    C = _wide(frames, "close")
    out, late, done = [], set(), []
    for asof, g in log.groupby("asof"):
        i = int(C.index.searchsorted(asof))
        if i + 1 >= len(C) or C.index[i] != asof:
            continue
        if pd.to_datetime(g["logged_at"]).max() >= (C.index[i + 1] + pd.Timedelta(hours=9)).tz_localize(data.VN):
            late.add(asof)
            continue
        g = g[g["sym"].isin(C.columns) & (i + g["h"] < len(C))].copy()
        g["y"] = [C[s].iloc[i + h] - C[s].iloc[i] for s, h in zip(g["sym"], g["h"])]
        done.append(g.dropna(subset=["y"]))
    d = pd.concat(done) if done else pd.DataFrame()
    if d.empty:
        return [f"Chuỗi thời gian: chưa có kết quả để chấm (chờ phiên kế tiếp; loại vì ghi muộn {len(late)})"]
    for h, g in d.groupby("h"):
        c80 = ((g["y"] >= g["lo80"]) & (g["y"] <= g["hi80"])).mean()
        c50 = ((g["y"] >= g["lo50"]) & (g["y"] <= g["hi50"])).mean()
        e, b = (g["y"] - g["center"]).abs().mean(), g["y"].abs().mean()
        out.append(f"Chuỗi thời gian +{h}: {g['asof'].nunique()} phiên, dải 80% chứa {c80:.0%}, dải 50% chứa {c50:.0%}, "
                   f"sai số {e:.2%} (giá không đổi {b:.2%})")
    if d["asof"].nunique() < MIN_DAYS:
        out.append(f"Chuỗi thời gian: quá sớm để kết luận (cần {MIN_DAYS} phiên); loại vì ghi muộn {len(late)}")
    return out
