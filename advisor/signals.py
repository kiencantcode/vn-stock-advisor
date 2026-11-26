"""Tín hiệu MUA/GIỮ/BÁN "tất cả đều đẹp" (V6 B-S5, sửa theo V7 M4-E trong STEADY_REPORT.md), theo dõi TRÊN GIẤY.

MUA khi đủ cả 7 điều kiện: hạng ổn định trong top 10; thị trường khỏe (VN-Index trên trung bình 200 phiên, hoặc trên
trung bình 50 phiên và cao hơn 20 phiên trước); giá trên trung bình 50 phiên;
công ty có lãi (P/E > 0); lợi nhuận 4 quý cao hơn một năm trước; khối ngoại mua ròng 20 phiên; tiền vào ngày tăng > 50% (20 phiên).
Mua ở giá đóng cửa phiên kế tiếp, tối đa 6 mã, mỗi mã 1/6 vốn. Giữ ít nhất 20 phiên; sau đó bán ở giá đóng cửa
phiên kế tiếp khi tín hiệu tắt. Không mua ở giá trần, không bán ở giá sàn. Phí 0.4% khứ hồi.
Tiền chưa dùng: để trong quỹ E1VFVN30 khi thị trường khỏe, tiền mặt khi không (0.1% mỗi lần chuyển).
"""
from __future__ import annotations

import hashlib
import os

import numpy as np
import pandas as pd

from . import data, extra, steady
from .report import ROOT

LOG = os.path.join(ROOT, "output", "history", "signals.csv")
TOPK, SLOTS, MIN_HOLD, COST, FCOST = 10, 6, 20, 0.004, 0.001
COND = {"top": "Hạng ổn định trong top 10", "mkt": "Thị trường khỏe", "trend": "Giá trên trung bình 50 phiên",
        "profit": "Công ty có lãi", "growth": "Lợi nhuận cao hơn năm trước", "foreign": "Khối ngoại mua ròng 20 phiên",
        "upvol": "Tiền vào ngày tăng nhiều hơn ngày giảm"}


def sig_id() -> str:
    with open(__file__, encoding="utf-8") as f:
        return "g" + hashlib.sha256((steady.model_id() + f.read()).encode()).hexdigest()[:10]


def conditions(w: dict, now: pd.DataFrame, index: pd.DataFrame, store: dict) -> pd.DataFrame:
    """Giá trị và điều kiện ở phiên mới nhất cho 100 mã trong rổ (giống research/lab_v6.py)."""
    c = w["c"].iloc[-420:]
    G, cols = c.index, list(now["sym"])
    V = w["nmValue"].reindex(index=G, columns=cols).where(c[cols].notna())
    cc = c[cols]
    r = cc.pct_change(fill_method=None)
    s20 = V.rolling(20, min_periods=15).sum()
    upv = (V.where(r > 0, 0).rolling(20, min_periods=15).sum() / s20).iloc[-1]
    ma50 = cc.rolling(50, min_periods=40).mean().iloc[-1]
    f = store["foreign"]
    f = f[f["code"].isin(cols)]
    piv = lambda k: f.pivot(index="date", columns="code", values=k).reindex(index=G, columns=cols)
    first = f.groupby("code")["date"].min().reindex(cols)
    live = pd.DataFrame({s: G >= first[s] if pd.notna(first[s]) else np.zeros(len(G), bool) for s in cols}, index=G) & cc.notna()
    net = piv("netVal").fillna(0).where(live)
    fnet = (net.rolling(20, min_periods=15).sum() / s20).iloc[-1]
    k = store["ratios"]
    k = k[k["code"].isin(cols)]
    K = lambda q: k.pivot(index="date", columns="code", values=q).reindex(columns=cols).reindex(G, method="ffill", limit=5).shift(1)
    pe, pb, mc = K("pe"), K("pb"), K("mcap")
    nz = lambda q: q.where(q.abs() > 1e-9)
    E, B = mc / nz(pe), mc / nz(pb)
    eg = ((E - E.shift(250)) / B.where(B > 0)).iloc[-1]
    idx = index.set_index("date")["close"]
    idx = idx[idx.index <= G[-1]]
    m200 = float(idx.iloc[-1] / idx.rolling(200).mean().iloc[-1] - 1)
    m50 = float(idx.iloc[-1] / idx.rolling(50).mean().iloc[-1] - 1)
    r20 = float(idx.iloc[-1] / idx.iloc[-21] - 1)
    healthy = m200 > 0 or (m50 > 0 and r20 > 0)
    o = pd.DataFrame({"sym": cols, "rank": now["rank"].values, "price": now["price"].values}).set_index("sym")
    o["ma50"] = (cc.iloc[-1] / ma50 - 1).reindex(cols)
    o["pe"], o["eg"], o["fnet"], o["upvol"] = pe.iloc[-1], eg, fnet, upv
    o["top"] = o["rank"] <= TOPK
    o["mkt"] = healthy
    o["trend"] = o["ma50"] > 0
    o["profit"] = o["pe"] > 0
    o["growth"] = o["eg"] > 0
    o["foreign"] = o["fnet"] > 0
    o["upvol"] = o["upvol"] > 0.5
    o["upvol_v"] = upv
    for q in COND:
        o[q] = o[q].fillna(False).astype(bool)
    o["signal"] = o[list(COND)].all(axis=1)
    o.attrs.update(m200=m200, m50=m50, r20=r20, healthy=healthy)
    o.attrs["idx_date"] = idx.index[-1].date().isoformat()
    return o.reset_index()


def append(o: pd.DataFrame, asof, path: str = LOG) -> None:
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    a, sid = str(pd.Timestamp(asof).date()), sig_id()
    if len(old) and ((old["asof"] == a) & (old["sig_id"] == sid)).any():
        return
    new = o[["sym", "rank", "price", *COND, "signal"]].copy()
    new.insert(0, "sig_id", sid); new.insert(0, "asof", a); new.insert(0, "logged_at", data.vn_now().isoformat(timespec="seconds"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new
    out.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)


def valid(grid: pd.DatetimeIndex, path: str = LOG) -> tuple[dict, int]:
    """{chỉ số phiên: bảng tín hiệu} chỉ gồm bản ghi lưu trước 9:00 phiên kế tiếp."""
    if not os.path.exists(path):
        return {}, 0
    log = pd.read_csv(path)
    log = log[log["sig_id"] == sig_id()]
    out, late = {}, 0
    for a, g in log.groupby("asof"):
        i = int(grid.searchsorted(pd.Timestamp(a)))
        if i >= len(grid) or grid[i] != pd.Timestamp(a):
            continue
        if i + 1 < len(grid) and pd.to_datetime(g["logged_at"]).max() >= (grid[i + 1] + pd.Timedelta(hours=9)).tz_localize(data.VN):
            late += 1
            continue
        out[i] = g.sort_values("rank").set_index("sym")
    return out, late


def replay(w: dict, days: dict, fund: pd.Series) -> dict:
    """Danh mục giấy dựng lại từ sổ tín hiệu (giống research/lab_v6.py)."""
    c, raw = w["c"], w["close"]
    grid = c.index
    res = {"nav": [], "pos": {}, "trades": [], "cash": 1.0, "fund": 0.0}
    if not days:
        return res
    cf = c.ffill()
    R = cf.pct_change(fill_method=None)
    R = R.where(R.abs() < 0.5).fillna(0)
    NT = c.isna()
    f = fund.reindex(grid).ffill()
    fr = f.pct_change(fill_method=None).fillna(0)
    pos, cash, ev, start = {}, 1.0, 0.0, min(days)
    for i in range(start + 1, len(grid)):
        for s in pos:
            pos[s]["v"] *= 1 + R[s].iloc[i]
        ev *= 1 + fr.iloc[i]
        prev = days.get(i - 1)
        if prev is not None:  # sổ của phiên trước hợp lệ: mới được bán / mua
            on = set(prev.index[prev["signal"]])
            for s in [s for s, p in pos.items() if i - p["i"] >= MIN_HOLD and s not in on and not NT[s].iloc[i] and R[s].iloc[i] >= -0.065]:
                p = pos.pop(s)
                cash += p["v"] * (1 - COST / 2)
                res["trades"].append({"sym": s, "buy_date": grid[p["i"]].date().isoformat(), "buy": p["raw"],
                                      "sell_date": grid[i].date().isoformat(), "sell": float(raw[s].iloc[i]),
                                      "ret": float(cf[s].iloc[i] / p["adj"] * (1 - COST / 2) / (1 + COST / 2) - 1),
                                      "fund": float(f.iloc[i] / f.iloc[p["i"]] - 1), "sessions": i - p["i"],
                                      "why": [COND[q] for q in COND if not bool(prev.loc[s, q])] if s in prev.index else ["Rớt khỏi rổ 100 mã"]})
            tot = cash + ev + sum(p["v"] for p in pos.values())
            for s in [s for s in prev.index[prev["signal"]] if s in c and s not in pos]:
                if len(pos) >= SLOTS:
                    break
                if NT[s].iloc[i] or R[s].iloc[i] > 0.065:
                    continue
                a = tot / SLOTS
                if cash < a and ev > 0:  # bán bớt quỹ để có tiền mua cổ phiếu
                    q = min(ev, a - cash)
                    ev -= q
                    cash += q * (1 - FCOST)
                a = min(a, cash)
                if a <= 1e-9:
                    break
                cash -= a
                pos[s] = {"v": a / (1 + COST / 2), "i": i, "adj": float(c[s].iloc[i]), "raw": float(raw[s].iloc[i])}
            healthy = bool(prev["mkt"].iloc[0]) if len(prev) else False
            if healthy and cash > 0:
                ev += cash * (1 - FCOST)
                cash = 0.0
            elif not healthy and ev > 0:
                cash += ev * (1 - FCOST)
                ev = 0.0
        res["nav"].append((grid[i], cash + ev + sum(p["v"] for p in pos.values())))
    res["pos"], res["cash"], res["fund"] = pos, cash, ev
    return res


def build(w: dict, now: pd.DataFrame, index: pd.DataFrame, fund: pd.Series, log: bool) -> dict:
    store = extra.update(set(now["sym"]) | set(_held_codes()))
    o = conditions(w, now, index, store)
    asof = now["date"].iloc[0]
    if log:
        append(o, asof)
    grid = w["c"].index
    days, late = valid(grid)
    pf = replay(w, days, fund)
    cf, raw = w["c"].ffill().iloc[-1], w["close"].ffill().iloc[-1]
    n, last = len(grid), days.get(len(grid) - 1)
    on = set(last.index[last["signal"]]) if last is not None else set(o.loc[o["signal"], "sym"])
    held, sells = [], []
    for s, p in pf["pos"].items():
        age = n - 1 - p["i"]
        sell = last is not None and (age + 1) >= MIN_HOLD and s not in on
        why = ([COND[q] for q in COND if not bool(last.loc[s, q])] if s in last.index else ["Rớt khỏi rổ 100 mã"]) if sell else []
        held.append({"sym": s, "buy_date": grid[p["i"]].date().isoformat(), "buy": p["adj"] * float(raw[s] / cf[s]),  # giá mua quy về mặt bằng giá hôm nay
                     "price": float(raw[s]), "pnl": float(cf[s] / p["adj"] * (1 - COST / 2) / (1 + COST / 2) - 1), "age": age,
                     "action": "BÁN" if sell else "GIỮ", "why": why, "left": max(0, MIN_HOLD - age - 1)})
        if sell:
            sells.append(s)
    free = SLOTS - len(pf["pos"]) + len(sells)
    buys = [s for s in o.loc[o["signal"]].sort_values("rank")["sym"] if s not in pf["pos"]][:max(0, free)]
    nav = pf["nav"]
    summ = None
    if nav:
        f = fund.reindex(grid).ffill()
        i0 = int(grid.searchsorted(nav[0][0])) - 1
        tr = pf["trades"]
        summ = {"start": grid[i0 + 1].date().isoformat(), "sessions": len(nav), "model": float(nav[-1][1] - 1),
                "fund": float(f.iloc[-1] / f.iloc[i0 + 1] - 1) if len(nav) > 1 else 0.0, "trades": len(tr),
                "win": sum(t["ret"] > 0 for t in tr), "beat": sum(t["ret"] > t["fund"] for t in tr),
                "cash": float(pf["cash"] / nav[-1][1]), "infund": float(pf["fund"] / nav[-1][1]), "late": late, "logged": len(days)}
    rows = []
    for r in o.sort_values("rank").head(30).to_dict("records"):
        rows.append({"sym": r["sym"], "rank": int(r["rank"]), "price": float(r["price"]), "signal": bool(r["signal"]),
                     "ok": {q: bool(r[q]) for q in COND}, "ma50": _f(r["ma50"]), "pe": _f(r["pe"]), "eg": _f(r["eg"]),
                     "fnet": _f(r["fnet"]), "upvol": _f(r["upvol_v"])})
    return {"id": sig_id(), "asof": pd.Timestamp(asof).date().isoformat(), "cond": COND, "market": {"m200": o.attrs["m200"], "m50": o.attrs["m50"], "r20": o.attrs["r20"], "ok": bool(o.attrs["healthy"]), "date": o.attrs["idx_date"]},
            "signals": [r["sym"] for r in rows if r["signal"]], "buy": [{"sym": s, "price": float(o.set_index("sym").loc[s, "price"])} for s in buys],
            "held": held, "trades": pf["trades"][::-1][:50], "summary": summ, "rows": rows}


def _f(v):
    return None if v is None or pd.isna(v) else float(v)


def _held_codes() -> list:
    """Mã còn trong sổ gần đây (để tải đủ dữ liệu cho cả mã đang giữ đã rớt khỏi rổ)."""
    if not os.path.exists(LOG):
        return []
    log = pd.read_csv(LOG)
    return list(log.loc[log["signal"].astype(bool), "sym"].unique())
