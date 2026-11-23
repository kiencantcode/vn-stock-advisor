"""Tải OHLCV: cache, cập nhật tăng dần, phát hiện giá bị điều chỉnh lại (cổ tức/chia tách)."""
from __future__ import annotations

import os
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache")
COLS = ["date", "open", "high", "low", "close", "volume"]
VN = ZoneInfo("Asia/Ho_Chi_Minh")
INDEX = "VNINDEX"


def vn_now() -> datetime:
    return datetime.now(VN)


def _normalize(df: pd.DataFrame, is_index: bool = False) -> pd.DataFrame:
    df = df[COLS].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.dropna().drop_duplicates("date", keep="last").sort_values("date")
    px = ["open", "high", "low", "close"]
    df = df[(df[px] > 0).all(axis=1)].copy()
    if not is_index and len(df) and df["close"].median() > 1000:  # về nghìn đồng
        df[px] = df[px] / 1000.0
    df["high"], df["low"] = df[px].max(axis=1), df[px].min(axis=1)
    return df.reset_index(drop=True)


def _fetch_entrade(sym: str, start: str, end: str) -> pd.DataFrame:
    """API công khai của DNSE/Entrade (không cần key)."""
    is_index = sym == INDEX
    t0 = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
    t1 = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp()) + 86400
    url = "https://services.entrade.com.vn/chart-api/v2/ohlcs/" + ("index" if is_index else "stock")
    for attempt in range(4):
        try:
            r = requests.get(url, params={"from": t0, "to": t1, "symbol": sym, "resolution": "1D"}, timeout=30)
            r.raise_for_status()
            j = r.json()
            break
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    if not j.get("t"):
        raise ValueError(f"Không có dữ liệu cho {sym}")
    return _normalize(pd.DataFrame({
        "date": pd.to_datetime(j["t"], unit="s"), "open": j["o"], "high": j["h"],
        "low": j["l"], "close": j["c"], "volume": j["v"]}), is_index)


def _fetch_vnstock(sym: str, start: str, end: str) -> pd.DataFrame:
    from vnstock import Quote  # type: ignore

    raw = Quote(symbol=sym, source="VCI").history(start=start, end=end, interval="1D")
    return _normalize(raw.rename(columns={"time": "date"}), sym == INDEX)


def _synthetic(sym: str, start: str, end: str) -> pd.DataFrame:
    """Bước ngẫu nhiên (KHÔNG phải giá thật, không có tín hiệu nào để học)."""
    rng = np.random.default_rng(zlib.crc32(sym.encode()))  # hash() đổi theo mỗi lần chạy
    days = pd.bdate_range(start, end)
    n = len(days)
    close = 30 * np.exp(np.cumsum(rng.normal(0, 0.016, n)))
    opn = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.003, n))
    hi = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, 0.006, n)))
    lo = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, 0.006, n)))
    return _normalize(pd.DataFrame({"date": days, "open": opn, "high": hi, "low": lo, "close": close,
                                    "volume": rng.integers(200_000, 5_000_000, n).astype(float)}),
                      is_index=True)


FETCH = {"vnstock": _fetch_vnstock, "entrade": _fetch_entrade}


def _load_from(source: str, sym: str, start_full: str, end: str) -> pd.DataFrame:
    path = os.path.join(CACHE_DIR, f"{source}_{sym}.csv")  # mỗi nguồn một cache, không trộn
    meta = path + ".start"  # ngày bắt đầu đã yêu cầu (mã niêm yết muộn vẫn hợp lệ)
    cached, asked, df = None, None, None
    if os.path.exists(path) and os.path.exists(meta):
        try:
            cached = pd.read_csv(path, parse_dates=["date"])
            with open(meta, encoding="ascii") as f:
                asked = f.read().strip()
        except (ValueError, pd.errors.ParserError):
            cached = None
    if cached is not None and len(cached) > 20 and asked and asked <= start_full:
        start = (cached["date"].max() - timedelta(days=20)).date().isoformat()
        fresh = FETCH[source](sym, start, end)
        both = cached.merge(fresh, on="date", suffixes=("_c", "_f"))
        both = both[both["date"] < cached["date"].max()]  # nến cuối có thể chưa chốt
        # Giá quá khứ đổi => nguồn vừa điều chỉnh => phải tải lại toàn bộ
        if len(both) and ((both["close_c"] / both["close_f"] - 1).abs() < 1e-4).all():
            df = pd.concat([cached, fresh]).drop_duplicates("date", keep="last").sort_values("date")
            start_full = asked
    if df is None:
        df = FETCH[source](sym, start_full, end)
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)
    with open(meta, "w", encoding="ascii") as f:
        f.write(start_full)
    return df.reset_index(drop=True)


def load(sym: str, history_days: int, provider: str) -> pd.DataFrame:
    os.makedirs(CACHE_DIR, exist_ok=True)
    now = vn_now()
    start, end = (now.date() - timedelta(days=history_days)).isoformat(), now.date().isoformat()
    if provider == "synthetic":
        return _synthetic(sym, start, end)
    err: Exception | None = None
    for source in (["entrade", "vnstock"] if provider == "auto" else [provider]):
        try:
            df = _load_from(source, sym, start, end)
            break
        except Exception as e:  # thử nguồn tiếp theo
            err = err or e
    else:
        raise RuntimeError(f"mọi nguồn dữ liệu đều lỗi ({err})")
    df = df[df["date"] >= pd.Timestamp(start)]
    if now.hour < 15:  # phiên hôm nay chưa chốt
        df = df[df["date"] < pd.Timestamp(now.date())]
    return df.reset_index(drop=True)


def load_many(syms: list[str], history_days: int, provider: str) -> tuple[dict[str, pd.DataFrame], list[str]]:
    def job(s):
        try:
            return s, load(s, history_days, provider), None
        except Exception as e:
            return s, None, f"{s}: {e}"

    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(job, syms))
    return {s: d for s, d, _ in res if d is not None}, [e for _, _, e in res if e]
