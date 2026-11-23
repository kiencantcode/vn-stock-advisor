"""Đặc trưng (chỉ dùng quá khứ) và nhãn (tương lai)."""
from __future__ import annotations

import numpy as np
import pandas as pd

STOCK = (
    "ret1 ret5 ret10 ret20 rsi14 macd_h bb_pos bb_width atr_pct vol_ratio dist_ma20 dist_ma50 "
    "range_pos20 vol20 ret60 ret120 mom12_1 vol_ratio5 dist_ma200 vol60 hi52 max20 min20 illiq turn "
    "overnight20 intraday20 lim20 clv skew60"
).split()
MARKET = "m_ret5 m_ret20 m_ret60 m_vol20 m_ma200 breadth50".split()
FEATURES = ["r_" + f for f in STOCK] + MARKET


def stock_features(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    g = df.sort_values("date").copy()
    c, h, l, v, o = g["close"], g["high"], g["low"], g["volume"], g["open"]
    r = c.pct_change()
    g["ret1"] = r
    for n in (5, 10, 20, 60, 120):
        g[f"ret{n}"] = c.pct_change(n)
    g["mom12_1"] = c.shift(20) / c.shift(250) - 1
    diff = c.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-diff.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    g["rsi14"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    g["macd_h"] = (macd - macd.ewm(span=9, adjust=False).mean()) / c
    ma20, sd = c.rolling(20).mean(), c.rolling(20).std()
    g["bb_pos"], g["bb_width"] = (c - ma20 + 2 * sd) / (4 * sd), 4 * sd / ma20
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    g["atr_pct"] = tr.rolling(14).mean() / c
    g["vol_ratio"], g["vol_ratio5"] = v / v.rolling(20).mean(), v.rolling(5).mean() / v.rolling(60).mean()
    g["dist_ma20"] = c / ma20 - 1
    for n in (50, 200):
        g[f"dist_ma{n}"] = c / c.rolling(n).mean() - 1
    lo, hi = l.rolling(20).min(), h.rolling(20).max()
    g["range_pos20"] = (c - lo) / (hi - lo)
    g["vol20"], g["vol60"] = r.rolling(20).std(), r.rolling(60).std()
    g["hi52"] = c / h.rolling(250).max() - 1
    g["max20"], g["min20"] = r.rolling(20).max(), r.rolling(20).min()
    g["illiq"] = np.log((r.abs() / (c * v).replace(0, np.nan)).rolling(20).mean() + 1e-15)
    g["turn"] = np.log((c * v).rolling(20).mean() + 1)
    g["overnight20"], g["intraday20"] = (o / c.shift() - 1).rolling(20).mean(), (c / o - 1).rolling(20).mean()
    g["lim20"] = (r.abs() > 0.065).rolling(20).sum()      # số phiên gần trần/sàn
    g["floor20"] = (r < -0.06).rolling(20).sum()          # chỉ để cảnh báo
    g["clv"] = ((2 * c - h - l) / (h - l).replace(0, np.nan)).fillna(0).rolling(5).mean()
    g["skew60"] = r.rolling(60).skew()
    # --- nhãn ---
    H = horizon
    g["y_close"] = c.shift(-H) / c - 1
    g["y_trade"] = o.shift(-H - 1) / o.shift(-1) - 1      # mua giá mở cửa hôm sau
    g["y_high"] = h[::-1].rolling(H).max()[::-1].shift(-1) / c - 1
    g["y_low"] = l[::-1].rolling(H).min()[::-1].shift(-1) / c - 1
    return g.replace([np.inf, -np.inf], np.nan)


def build_panel(frames: dict[str, pd.DataFrame], index: pd.DataFrame | None, horizon: int) -> pd.DataFrame:
    x = pd.concat([stock_features(d, horizon).assign(sym=s) for s, d in frames.items()], ignore_index=True)
    if index is not None:
        i = index.set_index("date")["close"].sort_index()
    else:  # không có VNINDEX: dùng trung bình lợi suất các mã
        i = (1 + x.groupby("date")["ret1"].mean().fillna(0)).cumprod()
    m = pd.DataFrame({
        "m_ret5": i.pct_change(5), "m_ret20": i.pct_change(20), "m_ret60": i.pct_change(60),
        "m_vol20": i.pct_change().rolling(20).std(), "m_ma200": i / i.rolling(200).mean() - 1})
    x = x.merge(m.rename_axis("date").reset_index(), on="date", how="left")
    x["breadth50"] = (x["dist_ma50"] > 0).groupby(x["date"]).transform("mean")
    gb = x.groupby("date")
    ranks = {"r_" + f: gb[f].rank(pct=True) - 0.5 for f in STOCK}  # hạng trong ngày, khử biến động chung
    ranks["y_rank"] = gb["y_close"].rank(pct=True) - 0.5
    x = pd.concat([x, pd.DataFrame(ranks)], axis=1)
    # ~250 phiên đầu chưa đủ dữ liệu cho chỉ báo dài hạn
    first = x["date"].min() + pd.Timedelta(days=400)
    return x[x["date"] >= first].sort_values(["date", "sym"]).reset_index(drop=True)
