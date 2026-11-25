"""Độ chính xác dễ hiểu theo từng kỳ hạn: ngắn (5), trung (20), dài (60 phiên)."""
from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd

from . import features, model, track

HORIZONS = {5: "Ngắn hạn (~1 tuần)", 20: "Trung hạn (~1 tháng)", 60: "Dài hạn (~3 tháng)"}


def _stats(z: pd.DataFrame, H: int, cfg: dict) -> dict:
    z = z.dropna(subset=["y_close", "y_trade"]).copy()
    by = z.groupby("date")
    z["r"] = by["score"].rank(ascending=False, method="first")
    z["ex"] = z["y_trade"] - by["y_trade"].transform("mean")
    z["beat"] = z["y_trade"] > by["y_trade"].transform("median")
    z["up"] = z["y_trade"] > 0
    top = z[z["r"] <= cfg["portfolio"]["top_n"]]
    ic = z.groupby("date")[["score", "y_close"]].apply(lambda g: g["score"].rank().corr(g["y_close"].rank())).dropna()
    ex = top.groupby("date")["ex"].mean()
    # kết quả sau phí phụ thuộc ngày bắt đầu chu kỳ: lấy trung bình 5 ngày bắt đầu khác nhau
    days = sorted(z["date"].unique())
    nets = [model._metrics(z[z["date"].isin(days[k::H])].assign(lo=-1e9, hi=1e9), cfg, H)
            for k in range(0, H, max(1, H // 5)) if len(days) > k]
    yr = [m["net_excess_yr"] for m in nets]
    return {"days": int(ic.size), "ic": float(ic.mean()), "ic_t": track._nw_t(ic, H - 1),
            "beat_top": float(top["beat"].mean()), "beat_all": float(z["beat"].mean()),
            "up_top": float(top["up"].mean()), "up_all": float(z["up"].mean()),
            "gross_per_trade": float(ex.mean()), "gross_t": track._nw_t(ex, H - 1),
            "net_yr": sum(yr) / len(yr), "net_lo": min(yr), "net_hi": max(yr),
            "net_t": sum(m["net_t"] for m in nets) / len(nets)}


def verdict(s: dict) -> str:
    if s["ic_t"] >= 1.65 and s["net_t"] >= 1.65:
        return "Có kỹ năng và có lời sau phí"
    if s["ic_t"] >= 1.65:
        return "Có kỹ năng nhỏ, CHƯA chứng minh có lời sau phí"
    return "KHÔNG có bằng chứng kỹ năng, không nên dùng"


def build(frames, index, core, cfg, outdir, force=False, keep=lambda old: True, asof=None) -> dict:
    path, mid = os.path.join(outdir, "accuracy.json"), track.model_id(cfg)
    if not force and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        if old["model_id"] == mid and keep(old):
            return old
    cut, res = pd.Timestamp(cfg["validation"]["holdout"]), {}
    for H, name in HORIZONS.items():
        print(f"Đang đo độ chính xác: {name}...", flush=True)
        oos = model.walk_forward(features.build_panel(frames, index, H), core, H, str(cfg["validation"]["start"]))
        if oos.empty:
            continue
        test = oos[oos["date"] >= cut]
        res[str(H)] = {"name": name, "dev": _stats(oos[oos["date"] < cut], H, cfg), "test": _stats(test, H, cfg)}
        res[str(H)]["years"] = {str(y): _stats(g, H, cfg) for y, g in test.groupby(test["date"].dt.year)}
        res[str(H)]["verdict"] = verdict(res[str(H)]["test"])
    out = {"model_id": mid, "asof": str(asof), "run_at": datetime.now().isoformat(timespec="seconds"),
           "holdout": str(cut.date()), "horizons": res}
    os.makedirs(outdir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def lines(a: dict) -> list[str]:
    out = [f"Đo trên dữ liệu từ {a['holdout']}; mô hình tại mỗi thời điểm chỉ học từ quá khứ"]
    for h in a["horizons"].values():
        s = h["test"]
        out.append(f"{h['name']}: mã top thắng trung vị {s['beat_top']:.1%} (chọn ngẫu nhiên {s['beat_all']:.1%}); "
                   f"mã top tăng giá {s['up_top']:.1%} (mọi mã {s['up_all']:.1%}); IC {s['ic']:+.3f} (t={s['ic_t']:.1f}); "
                   f"sau phí {s['net_yr']:+.1%}/năm, từ {s['net_lo']:+.1%} đến {s['net_hi']:+.1%} tuỳ ngày bắt đầu (t={s['net_t']:.1f}) => {h['verdict']}")
        out.append("   IC từng năm: " + ", ".join(f"{y} {v['ic']:+.3f}" for y, v in h["years"].items()))
    return out
