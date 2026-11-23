"""Vùng giá từ khoảng conformal, tín hiệu từ hạng; MUA chỉ mở khi kiểm định đạt."""
from __future__ import annotations


def tick(p: float) -> float:
    """Bước giá HOSE (nghìn đồng)."""
    s = 0.01 if p < 10 else 0.05 if p < 50 else 0.1
    return round(round(p / s) * s, 2)


def make_levels(row, conf: dict, rank: int, n: int, horizon: int, gate: bool) -> dict:
    px, sg = float(row["close"]), float(row["vol20"]) * horizon ** 0.5

    def at(y, q):
        return px * (1 + conf[y][q] * sg)

    buy_lo, buy_hi = at("y_low", 0.5), px
    stop = min(at("y_low", 0.1), buy_lo * (1 - 0.5 * float(row["atr_pct"])))
    sell = at("y_high", 0.75)
    floor, k = int(row["floor20"]), max(1, round(n * 0.2))
    if floor >= 3:
        sig = "RUI RO CAO"
    elif rank <= k:
        sig = "MUA" if gate else "HANG CAO"
    elif rank > n - k:
        sig = "HANG THAP"
    else:
        sig = "TRUNG LAP"
    return {
        "hang": rank, "gia_hien_tai": round(px, 2),
        "khoang_80_tu": tick(at("y_close", 0.1)), "khoang_80_den": tick(at("y_close", 0.9)),
        "vung_mua_tu": tick(buy_lo), "vung_mua_den": tick(buy_hi), "vung_ban": tick(sell),
        "cat_lo": tick(stop),
        "rsi": round(float(row["rsi14"]), 1), "phien_giam_manh_20": floor, "tin_hieu": sig}
