"""Kho khối ngoại (từ 2018-08) và P/E, P/B, P/S, vốn hoá theo ngày (từ 2017-12), VNDirect.
Lần đầu tải đủ lịch sử từng mã cần dùng; các ngày sau chỉ tải vài phiên gần nhất cho cả sàn HOSE."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pandas as pd

from . import data, vnd

PATH = os.path.join(data.CACHE_DIR, "vnd_extra.pkl.gz")
ITEMS = {"51006": "pe", "51012": "pb", "51011": "ps", "51003": "mcap"}
FCOLS = ["code", "date", "buyVal", "sellVal", "netVal", "totalRoom", "currentRoom"]


def _foreign(d: pd.DataFrame) -> pd.DataFrame:
    if d.empty:
        return pd.DataFrame(columns=FCOLS)
    d = d.rename(columns={"tradingDate": "date"})
    d["date"] = pd.to_datetime(d["date"])
    return d[FCOLS]


def _ratios(parts: list[pd.DataFrame]) -> pd.DataFrame:
    parts = [q for q in parts if len(q)]
    if not parts:
        return pd.DataFrame(columns=["date", "code", *ITEMS.values()])
    r = pd.concat(parts, ignore_index=True).rename(columns={"reportDate": "date"})
    r["date"] = pd.to_datetime(r["date"])
    return r.pivot_table(index=["date", "code"], columns="item", values="value", aggfunc="last").reset_index()


def _full(code: str):
    f = _foreign(vnd._get("foreigns", q=f"code:{code}", size=5000))
    r = _ratios([vnd._get("ratios", q=f"code:{code}~itemCode:{k}", size=5000).assign(item=v) for k, v in ITEMS.items()])
    return f, r


def _recent(a, b):
    """Cả sàn HOSE trong [a, b] (tối đa vài ngày để không vượt 10.000 dòng mỗi truy vấn)."""
    f = _foreign(vnd._get("foreigns", q=f"floor:HOSE~tradingDate:gte:{a}~tradingDate:lte:{b}", size=5000))
    r = _ratios([vnd._get("ratios", q=f"itemCode:{k}~reportDate:gte:{a}~reportDate:lte:{b}", size=5000).assign(item=v)
                 for k, v in ITEMS.items()])
    return f, r


def _merge(old: pd.DataFrame, new: list[pd.DataFrame], key: list[str]) -> pd.DataFrame:
    parts = [q for q in [old, *new] if len(q)]
    if not parts:
        return old
    out = pd.concat(parts, ignore_index=True).drop_duplicates(key, keep="last")
    return out.sort_values(key).reset_index(drop=True)


def load() -> dict:
    if os.path.exists(PATH):
        s = pd.read_pickle(PATH)
        s.setdefault("full", set(s["foreign"]["code"].unique()))
        return s
    return {"foreign": pd.DataFrame(columns=FCOLS), "ratios": _ratios([]), "full": set()}


def update(codes) -> dict:
    s = load()
    today = data.vn_now().date()
    fn, rn = [], []
    if len(s["foreign"]):
        a = min(s["foreign"]["date"].max(), s["ratios"]["date"].max()).date() - timedelta(days=7)
        while a <= today:
            b = min(a + timedelta(days=2), today)
            f, r = _recent(a, b)
            fn.append(f); rn.append(r)
            a = b + timedelta(days=1)
    todo = sorted(set(codes) - s["full"])
    if todo:
        with ThreadPoolExecutor(4) as ex:
            for f, r in ex.map(_full, todo):
                fn.append(f); rn.append(r)
    s["foreign"] = _merge(s["foreign"], fn, ["code", "date"])
    s["ratios"] = _merge(s["ratios"], rn, ["date", "code"])
    s["full"] |= set(todo)
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    pd.to_pickle(s, PATH + ".tmp", compression="gzip")
    os.replace(PATH + ".tmp", PATH)
    return s
