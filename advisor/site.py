"""Dữ liệu cho trang web: output/site.json (JSON hợp lệ, không NaN)."""
from __future__ import annotations

import json
import math
import os

from .report import outdir_for

HIST = 40


def _clean(v):
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def write(provider, updated, df, frames, fc, val, acc, live, warnings) -> None:
    stocks = []
    for r in df.to_dict("records"):
        h = frames[r["ma"]].tail(HIST)
        s = {"sym": r["ma"], "sector": r["nganh"], "rank": r["hang"], "price": r["gia_hien_tai"],
             "buy": [r["vung_mua_tu"], r["vung_mua_den"]], "target": r["vung_ban"], "stop": r["cat_lo"],
             "rsi": r["rsi"], "signal": r["tin_hieu"],
             "dates": [d.strftime("%Y-%m-%d") for d in h["date"]], "close": [round(c, 3) for c in h["close"]], "fc": []}
        if fc is not None:
            g = fc["f"][fc["f"]["sym"] == r["ma"]].sort_values("h")
            for x in g.to_dict("records"):
                s["fc"].append({k: round(x["close"] * math.exp(x[k]), 3) for k in ("center", "lo80", "lo50", "hi50", "hi80")})
        stocks.append(s)
    out = {"updated": updated, "asof": df["ngay_du_lieu"].iloc[0] if len(df) else None, "gate": val["gate"],
           "holdout": val.get("holdout"), "accuracy": acc["horizons"], "live": live, "warnings": warnings,
           "forecast": None if fc is None else {"best": fc["best"], "cover": fc["cover"]}, "stocks": stocks}
    path = os.path.join(outdir_for(provider), "site.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_clean(out), f, ensure_ascii=False, allow_nan=False)
