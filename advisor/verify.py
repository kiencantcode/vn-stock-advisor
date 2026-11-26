"""Lưu dự đoán mỗi phiên (chỉ ghi thêm) và tự kiểm chứng: mua phiên kế tiếp, giữ 5 phiên, so với quỹ E1VFVN30."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import data, steady
from .report import ROOT

LOG = os.path.join(ROOT, "output", "history", "predictions.csv")
SCORES = os.path.join(ROOT, "output", "history", "prediction_scores.csv")
HOLD = 5
K = HOLD + 1  # từ phiên dự đoán: 1 phiên để mua + 5 phiên giữ


def ranges(x: pd.DataFrame, c: pd.DataFrame, now: pd.DataFrame) -> dict[str, tuple]:
    """Khoảng 80% của lợi suất sau K phiên, hiệu chỉnh trên ~1 năm gần nhất (chỉ kết quả đã biết)."""
    fw = (c.shift(-K) / c - 1).stack().rename("fk")
    fw.index.names = ["date", "sym"]
    D = np.sort(x["date"].unique())
    z = x.loc[(x["date"] >= D[max(0, len(D) - 1 - K - 250)]) & (x["date"] <= D[-1 - K]), ["date", "sym", "vol20"]]
    z = z.merge(fw.reset_index(), on=["date", "sym"])
    q = (z["fk"] / (z["vol20"] * K ** 0.5)).replace([np.inf, -np.inf], np.nan).dropna()
    a, b = q.quantile(0.1), q.quantile(0.9)
    return {s: (a * v * K ** 0.5, b * v * K ** 0.5) for s, v in zip(now["sym"], now["vol20"])}


def append(x, c, now, path: str = LOG) -> None:
    old = pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()
    asof, mid = str(now["date"].iloc[0].date()), steady.model_id()
    if len(old) and ((old["asof"] == asof) & (old["model_id"] == mid)).any():
        return
    r, top = ranges(x, c, now), now.head(steady.N)
    new = pd.DataFrame({"logged_at": data.vn_now().isoformat(timespec="seconds"), "asof": asof, "model_id": mid,
                        "sym": top["sym"], "rank": top["rank"], "buy": top["price"],
                        "lo": [round(r[s][0], 5) for s in top["sym"]], "hi": [round(r[s][1], 5) for s in top["sym"]]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new
    out.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)


def check(c, op, lo, fund: pd.Series, path: str = LOG) -> list[dict]:
    """Mọi dự đoán, mới nhất trước. Dự đoán lưu sau 9:00 phiên kế tiếp không được tính."""
    if not os.path.exists(path):
        return []
    log = pd.read_csv(path)
    log = log[log["model_id"] == steady.model_id()]
    grid, f, out = c.index, fund.reindex(c.index).ffill(), []
    for asof, g in log.groupby("asof"):
        i = int(grid.searchsorted(pd.Timestamp(asof)))
        if i >= len(grid) or grid[i] != pd.Timestamp(asof):
            continue
        late = i + 1 < len(grid) and pd.to_datetime(g["logged_at"]).max() >= (grid[i + 1] + pd.Timedelta(hours=9)).tz_localize(data.VN)
        j = min(i + K, len(grid) - 1)  # phiên dùng để tính, tối đa 5 phiên sau khi mua
        done, picks = i + K < len(grid), []
        for r in g.sort_values("rank").to_dict("records"):
            s = r["sym"]
            p = {"sym": s, "buy": r["buy"], "lo": r["buy"] * (1 + r["lo"]), "hi": r["buy"] * (1 + r["hi"]),
                 "fill": None, "now": None, "ret": None, "inside": None}
            if j > i and s in c:
                base, px = c[s].iloc[i], c[s].ffill()
                if pd.isna(c[s].iloc[i + 1]) or px.iloc[i + 1] / base - 1 > 0.065:
                    p["fill"] = "bỏ qua"  # gần giá trần hoặc không giao dịch
                else:
                    e = min(op[s].iloc[i + 1], base) if lo[s].iloc[i + 1] <= base else c[s].iloc[i + 1]
                    p["fill"], p["ret"] = float(r["buy"] * e / base), float(px.iloc[j] / e - 1 - steady.COST)
                p["now"] = float(r["buy"] * px.iloc[j] / base)  # quy về giá lúc dự đoán (không bị nhiễu bởi chia tách)
                if done:
                    p["inside"] = bool(p["lo"] <= p["now"] <= p["hi"])
            picks.append(p)
        rets = [p["ret"] for p in picks if p["ret"] is not None]
        out.append({"asof": asof, "late": bool(late), "done": bool(done), "age": int(max(0, j - i - 1)),
                    "until": grid[j].date().isoformat() if j > i else None, "picks": picks,
                    "ret": float(np.mean(rets)) if rets else None,
                    # quỹ tính từ giá đóng cửa phiên dự đoán, giống lệnh mua đặt ở giá đó
                 "fund": float(f.iloc[j] / f.iloc[i] - 1) if j > i else None})
    return sorted(out, key=lambda d: d["asof"], reverse=True)


def summary(items: list[dict]) -> dict:
    """Chấm theo tuần không chồng nhau (cách nhau ít nhất 5 phiên), bắt đầu từ dự đoán hợp lệ đầu tiên."""
    ok = sorted((d for d in items if d["done"] and not d["late"] and d["ret"] is not None), key=lambda d: d["asof"])
    weeks, last = [], None
    for d in ok:
        if last is None or d["asof"] >= last:  # dự đoán mới chỉ bắt đầu khi tuần trước đã kết thúc
            weeks.append(d)
            last = d["until"]
    ex = np.array([d["ret"] - d["fund"] for d in weeks])
    ins = [p["inside"] for d in weeks for p in d["picks"] if p["inside"] is not None]
    n = len(ex)
    t = float(ex.mean() / ex.std(ddof=1) * n ** 0.5) if n >= 8 and ex.std() > 0 else None
    return {"weeks": n, "ret": float(np.prod([1 + d["ret"] for d in weeks]) - 1) if n else None,
            "fund": float(np.prod([1 + d["fund"] for d in weeks]) - 1) if n else None,
            "beat": int((ex > 0).sum()), "up": int(sum(d["ret"] > 0 for d in weeks)),
            "inside": float(np.mean(ins)) if ins else None, "t": t,
            "worst": float(min(d["ret"] for d in weeks)) if n else None,
            "pass": bool(n >= 26 and t is not None and t >= 1.65 and np.mean(ex) > 0)}


def build(x, w, now, fund: pd.Series, log: bool) -> dict:
    if log:
        append(x, w["c"], now)
    items = check(w["c"], w["adOpen"], w["adLow"], fund)
    if items:
        pd.DataFrame([{k: d[k] for k in ("asof", "until", "done", "late", "ret", "fund")} for d in items]).to_csv(SCORES, index=False)
    return {"summary": summary(items), "items": items[:30]}
