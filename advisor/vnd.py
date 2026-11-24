"""Kho giá VNDirect: mọi mã HOSE (kể cả đã huỷ niêm yết), giá điều chỉnh và giá trị khớp lệnh THẬT."""
from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pandas as pd
import requests

from . import data

PATH = os.path.join(data.CACHE_DIR, "vnd_px.pkl.gz")
URL = "https://api-finfo.vndirect.com.vn/v4/"
COLS = ["code", "date", "close", "adOpen", "adHigh", "adLow", "adClose", "nmValue", "floor"]
MIN_CODES = 250  # phiên có ít mã hơn là dữ liệu chưa về đủ


def _get(path: str, **params) -> pd.DataFrame:
    out, page, pages = [], 1, 1
    while page <= pages:
        for attempt in range(5):
            try:
                r = requests.get(URL + path, params={**params, "page": page}, timeout=60,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.raise_for_status()
                j = r.json()
                break
            except (requests.RequestException, ValueError):
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        out += j["data"]
        pages, page = j.get("totalPages", 1), page + 1
    return pd.DataFrame(out)


def _tidy(d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return pd.DataFrame(columns=COLS)
    d = d[d["type"] == "STOCK"][COLS].copy() if "type" in d else d[COLS].copy()
    d["date"] = pd.to_datetime(d["date"])
    px = ["close", "adOpen", "adHigh", "adLow", "adClose"]
    d = d.dropna(subset=px)
    return d[(d[px] > 0).all(axis=1)]


def _full(code: str) -> pd.DataFrame:
    return _tidy(_get("stock_prices", q=f"code:{code}~date:gte:2013-01-01", size=5000, sort="date"))


def _many(codes) -> list[pd.DataFrame]:
    with ThreadPoolExecutor(4) as ex:
        return [d for d in ex.map(_full, codes) if len(d)]


def update() -> pd.DataFrame:
    """Chỉ tải phần mới; mã nào giá điều chỉnh quá khứ đổi thì tải lại toàn bộ mã đó."""
    now = data.vn_now()
    old = pd.read_pickle(PATH) if os.path.exists(PATH) else None
    if old is None:
        codes = sorted(_get("stocks", q="type:STOCK~floor:HOSE", size=3000)["code"].unique())
        print(f"Tải lần đầu {len(codes)} mã từ VNDirect (vài phút)...", flush=True)
        parts = _many(codes)
    else:
        since = (old["date"].max() - timedelta(days=20)).date().isoformat()
        new = _tidy(_get("stock_prices", q=f"floor:HOSE~date:gte:{since}", size=3000, sort="date"))
        m = old.merge(new, on=["code", "date"], suffixes=("", "_n"))
        m = m[m["date"] < old["date"].max()]
        bad = set(m.loc[(m["adClose_n"] / m["adClose"] - 1).abs() > 1e-4, "code"]) | (set(new["code"]) - set(old["code"]))
        parts = [old[~old["code"].isin(bad)], new[~new["code"].isin(bad)], *_many(sorted(bad))]
    p = pd.concat(parts).drop_duplicates(["code", "date"], keep="last").sort_values(["code", "date"])
    if (now.hour, now.minute) < (15, 20):  # phiên hôm nay chưa chốt
        p = p[p["date"] < pd.Timestamp(now.date())]
    while len(p) and p.loc[p["date"] == p["date"].max(), "code"].nunique() < MIN_CODES:
        p = p[p["date"] < p["date"].max()]
    if p.empty:
        raise ValueError("không có dữ liệu")
    p = p.reset_index(drop=True)
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    p.to_pickle(PATH + ".tmp", compression="gzip")
    os.replace(PATH + ".tmp", PATH)
    return p


def true_value(frames: dict[str, pd.DataFrame], p: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Đặt khối lượng sao cho giá điều chỉnh x khối lượng = giá trị khớp thật.
    Nếu không, 'turn' và 'illiq' trong quá khứ chứa thông tin chia tách/cổ tức của tương lai."""
    val = p.set_index(["code", "date"])["nmValue"]
    have, out = set(p["code"]), {}
    for s, d in frames.items():
        d = d.copy()
        if s in have:
            v = val.loc[s].reindex(d["date"]).values
            ok = pd.notna(v) & (v > 0)
            d["volume"] = d["volume"].astype(float)
            d.loc[ok, "volume"] = v[ok] / d["close"].values[ok] / 1000
        out[s] = d
    return out
