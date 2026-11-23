"""Nhật ký xếp hạng hằng ngày (chỉ ghi thêm) và chấm điểm bằng giá thật sau đó."""
from __future__ import annotations

import hashlib
import os

import numpy as np
import pandas as pd

from . import data, features, model
from .report import ROOT

LOG = os.path.join(ROOT, "output", "history", "rankings.csv")
MIN_DAYS = 60  # dưới số phiên đã chấm này thì chưa kết luận
LEVELS = {"lo": ("y_close", 0.1), "hi": ("y_close", 0.9), "buy": ("y_low", 0.5)}


def model_id(cfg: dict) -> str:
    """Đổi mô hình, horizon hoặc danh sách mã => id mới => chấm điểm lại từ đầu."""
    blob = f"{cfg['horizon']}|{sorted(s for v in cfg['sectors'].values() for s in v)}"
    for m in (features, model):
        with open(m.__file__, encoding="utf-8") as f:
            blob += f.read()
    return "m" + hashlib.sha256(blob.encode()).hexdigest()[:10]


def _read(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["asof"])


def freeze_date(cfg: dict, path: str = LOG):
    """Phiên đầu tiên được ghi với mô hình này: mốc của bản 'đóng băng'."""
    log = _read(path)
    mine = log[log["model_id"] == model_id(cfg)] if len(log) else log
    return mine["asof"].min() if len(mine) else None


def frozen_rank(x: pd.DataFrame, now: pd.DataFrame, cfg: dict, path: str = LOG) -> np.ndarray:
    """Hạng theo bản KHÔNG học dữ liệu sau mốc đóng băng, để đo xem việc học mỗi ngày có ích không."""
    f = freeze_date(cfg, path)
    tr = model.trainable(x)
    if f is not None:
        known = np.sort(x.loc[x["date"] <= f, "date"].unique())
        tr = tr[tr["date"] <= known[-1 - cfg["horizon"]]]
    s = pd.Series(model.fit_predict(tr, now))
    return s.rank(ascending=False, method="first").astype(int).values


def append(now: pd.DataFrame, conf: dict, df: pd.DataFrame, cfg: dict, path: str = LOG,
           frozen=None) -> bool:
    """Ghi một phiên. Phiên đã có (cùng mô hình) thì KHÔNG ghi đè. Mức giá lưu dạng % so với giá đóng cửa."""
    mid, asof, old = model_id(cfg), now["date"].iloc[0], _read(path)
    if len(old) and ((old["asof"] == asof) & (old["model_id"] == mid)).any():
        return False
    px = now["close"].values
    sg = now["vol20"].values * cfg["horizon"] ** 0.5
    new = pd.DataFrame({
        "logged_at": data.vn_now().isoformat(timespec="seconds"), "asof": asof, "model_id": mid,
        "rank_frozen": np.nan if frozen is None else frozen,
        "horizon": cfg["horizon"], "sym": now["sym"].values, "rank": df["hang"].values,
        "score": now["score"].values, "close": px, "signal": df["tin_hieu"].values,
        **{k: conf[y][q] * sg for k, (y, q) in LEVELS.items()},
        "target": df["vung_ban"].values / px - 1, "stop": df["cat_lo"].values / px - 1})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new
    out["asof"] = pd.to_datetime(out["asof"]).dt.strftime("%Y-%m-%d")
    out.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)
    return True


def _nw_t(a, lag: int) -> float:
    """t-stat Newey-West: các phiên liền nhau chồng lấn nên t thường bị thổi phồng."""
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 10:
        return float("nan")
    e = a - a.mean()
    var = (e @ e) / n + 2 * sum((1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n for k in range(1, min(lag, n - 1) + 1))
    return float(a.mean() / (var / n) ** 0.5) if var > 0 else float("nan")


def score(frames: dict[str, pd.DataFrame], cfg: dict, path: str = LOG) -> dict:
    H, pf, log = cfg["horizon"], cfg["portfolio"], _read(path)
    res = {"days": 0, "pending": 0, "late": 0, "other_model": 0}
    if log.empty:
        return res
    mine = log[log["model_id"] == model_id(cfg)]
    res["other_model"] = int(log.loc[log["model_id"] != model_id(cfg), "asof"].nunique())
    if mine.empty or not frames:
        return res
    w = {c: pd.concat({s: d.set_index("date")[c] for s, d in frames.items()}, axis=1, sort=True)
         for c in ("open", "high", "low", "close")}
    grid, rows, live = w["close"].index, [], {}
    for asof, g in mine.groupby("asof"):
        i = int(grid.searchsorted(asof))
        if i >= len(grid) or grid[i] != asof or i + 1 >= len(grid):
            res["pending"] += 1
            continue
        # chỉ hợp lệ nếu ghi trước giờ mở cửa phiên kế tiếp
        opening = (grid[i + 1] + pd.Timedelta(hours=9)).tz_localize(data.VN)
        if pd.to_datetime(g["logged_at"]).max() >= opening:
            res["late"] += 1
            continue
        if i + H + 1 >= len(grid):
            res["pending"] += 1
            continue
        g = g[g["sym"].isin(w["close"].columns)].set_index("sym").sort_values("rank")
        s, fut = g.index, slice(i + 1, i + H + 1)
        base = w["close"].iloc[i][s]
        g = g.assign(y=w["close"].iloc[i + H][s] / base - 1,
                     yt=w["open"].iloc[i + H + 1][s] / w["open"].iloc[i + 1][s] - 1,
                     hi_real=w["high"].iloc[fut][s].max() / base - 1,
                     lo_real=w["low"].iloc[fut][s].min() / base - 1).dropna(subset=["y", "yt"])
        if len(g) <= 5:
            continue
        live[i] = g
        fr = g["rank_frozen"] if "rank_frozen" in g else pd.Series(np.nan, g.index)
        rows.append({"asof": asof.date().isoformat(), "n": len(g),
                     "rank_ic": (-g["rank"]).rank().corr(g["y"].rank()),
                     "ic_frozen": (-fr).rank().corr(g["y"].rank()) if fr.notna().all() else np.nan,
                     "top_excess": g["yt"].head(pf["top_n"]).mean() - g["yt"].mean(),
                     "coverage80": ((g["y"] >= g["lo"]) & (g["y"] <= g["hi"])).mean(),
                     "hit_buy": (g["lo_real"] <= g["buy"]).mean(),
                     "hit_target": (g["hi_real"] >= g["target"]).mean(),
                     "hit_stop": (g["lo_real"] <= g["stop"]).mean()})
    if not rows:
        return res
    t = pd.DataFrame(rows)
    t.to_csv(os.path.join(os.path.dirname(path), "scores.csv"), index=False)
    # danh mục: cân bằng lại mỗi H phiên (không chồng lấn), có phí, cùng luật với kiểm định
    hold, net, last = [], [], -10 ** 9
    for i, g in live.items():
        if i - last < H:
            continue
        last = i
        rk = g["rank"].rank(method="first")
        keep = [s for s in hold if s in rk.index and rk[s] <= pf["keep_rank"]]
        new = [s for s in rk.index if s not in keep][: pf["top_n"] - len(keep)]
        hold = keep + new
        net.append(g.loc[hold, "yt"].mean() - g["yt"].mean() - len(new) / pf["top_n"] * pf["round_trip_cost"])
    both = t.dropna(subset=["ic_frozen"])
    if len(both):
        gap = both["rank_ic"] - both["ic_frozen"]
        res.update(learn_days=len(both), ic_learn=float(both["rank_ic"].mean()),
                   ic_frozen=float(both["ic_frozen"].mean()), learn_t=_nw_t(gap, H - 1))
    res.update(days=len(t), first=t["asof"].iloc[0], last=t["asof"].iloc[-1],
               rank_ic=float(t["rank_ic"].mean()), ic_t=_nw_t(t["rank_ic"], H - 1),
               periods=len(net), net_per_period=float(np.mean(net)), net_total=float(np.sum(net)),
               net_t=_nw_t(net, 0), **{k: float(t[k].mean()) for k in
                                       ("coverage80", "hit_buy", "hit_target", "hit_stop")})
    return res


def failing(r: dict | None) -> bool:
    """Dữ liệu sống cho thấy xếp hạng sai hệ thống => tạm dừng tín hiệu."""
    return bool(r and r["days"] >= MIN_DAYS and r["ic_t"] <= -1.65)


def summary(r: dict) -> list[str]:
    out = [f"Đã chấm {r['days']} phiên; chờ kết quả {r['pending']}; loại vì ghi muộn {r['late']}; "
           f"thuộc mô hình cũ {r['other_model']}"]
    if not r["days"]:
        return out + ["Chưa có kết quả: mỗi xếp hạng cần đủ số phiên dự báo + 1 mới chấm được."]

    def tt(v):
        return "chưa đủ dữ liệu" if np.isnan(v) else f"t={v:.1f}"

    out += [f"Giai đoạn {r['first']} đến {r['last']}",
            f"Rank IC: {r['rank_ic']:+.3f} ({tt(r['ic_t'])})",
            f"Danh mục top, sau phí, so với giữ đều: {r['net_per_period']:+.2%}/kỳ, cộng dồn {r['net_total']:+.2%} "
            f"qua {r['periods']} kỳ ({tt(r['net_t'])})",
            f"Khoảng 80% chứa giá thật: {r['coverage80']:.0%} (mục tiêu 80%)",
            f"Chạm đáy vùng mua {r['hit_buy']:.0%} (kỳ vọng ~50%), chốt lời {r['hit_target']:.0%} (~25%), "
            f"cắt lỗ {r['hit_stop']:.0%} (tối đa ~10%)"]
    if r.get("learn_days"):
        out.append(f"Học mỗi ngày: IC {r['ic_learn']:+.3f}, bản đóng băng {r['ic_frozen']:+.3f} "
                   f"({r['learn_days']} phiên, chênh lệch {tt(r['learn_t'])})")
    if r["days"] < MIN_DAYS:
        out.append(f"KẾT LUẬN: quá sớm (cần ít nhất {MIN_DAYS} phiên).")
    elif r["ic_t"] >= 1.65 and r["net_t"] >= 1.65:
        out.append("KẾT LUẬN: có bằng chứng tốt trên dữ liệu sống, cả xếp hạng lẫn lợi nhuận sau phí.")
    elif r["ic_t"] >= 1.65:
        out.append("KẾT LUẬN: xếp hạng có kỹ năng, nhưng chưa chứng minh có lời sau phí.")
    else:
        out.append("KẾT LUẬN: chưa có bằng chứng mô hình hiệu quả. Không nên dựa vào.")
    return out
