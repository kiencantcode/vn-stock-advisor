"""Danh sách ổn định để giữ từ 1 tuần trở lên: 100 mã HOSE thanh khoản nhất, theo dõi TRÊN GIẤY.

Luật cố định (STEADY_REPORT.md): LightGBM nhãn 20 phiên, hạng trung bình 20 phiên, xem lại mỗi 5 phiên, giữ 6 mã,
mã đang giữ chỉ bán khi rớt khỏi hạng 18, phí 0.4% khứ hồi. Mua: đặt ở giá đóng cửa gần nhất, chưa khớp thì mua giá đóng cửa.
"""
from __future__ import annotations

import hashlib
import os

import lightgbm as lgb
import numpy as np
import pandas as pd

from . import data, features
from .report import ROOT
from .track import _nw_t

LOG = os.path.join(ROOT, "output", "history", "steady_rankings.csv")
ETF = "E1VFVN30"
H, SMOOTH, STEP, N, KEEP, TOP, COST, SEEDS = 20, 20, 5, 6, 18, 100, 0.004, 3
SPEC = f"v4|lim|{H}|{SMOOTH}|{STEP}|{N}|{KEEP}|{TOP}|{COST}|{SEEDS}"


def model_id() -> str:
    """Đổi đặc trưng hoặc luật => id mới => theo dõi lại từ đầu."""
    blob = SPEC
    with open(features.__file__, encoding="utf-8") as f:
        blob += f.read()
    return "s" + hashlib.sha256(blob.encode()).hexdigest()[:10]


def wide(p: pd.DataFrame) -> dict[str, pd.DataFrame]:
    c = p.pivot(index="date", columns="code", values="adClose")
    c = c[c.notna().sum(axis=1) > 100]
    w = {k: p.pivot(index="date", columns="code", values=k).reindex(c.index)
         for k in ("close", "nmValue", "floor", "adOpen", "adLow")}
    return {"c": c, **w}


def panel(p: pd.DataFrame, w: dict, index: pd.DataFrame) -> pd.DataFrame:
    c = w["c"]
    # rổ tại từng thời điểm: 100 mã HOSE có trung vị giá trị 60 phiên cao nhất, đã niêm yết >= 250 phiên
    rk = w["nmValue"].rolling(60, min_periods=40).median().where(w["floor"] == "HOSE").rank(axis=1, ascending=False)
    rk = rk.where(c.notna().cumsum() >= 250)
    ever, fr = rk.columns[(rk <= TOP).any()], {}
    for s, g in p[p["date"].isin(c.index) & p["code"].isin(ever)].groupby("code"):
        d = g[["date", "adOpen", "adHigh", "adLow", "adClose"]].copy()
        d.columns = ["date", "open", "high", "low", "close"]
        d["volume"] = g["nmValue"] / g["adClose"]  # giá x khối lượng = giá trị khớp thật (không rò rỉ chia tách)
        fr[s] = d.dropna()
    x = features.build_panel(fr, index, 5)
    lq = rk.stack().rename("lqr")
    lq.index.names = ["date", "sym"]
    x = x.merge(lq.reset_index(), on=["date", "sym"], how="left")
    x = x[x["lqr"] <= TOP].reset_index(drop=True)
    gb = x.groupby("date")
    for f in features.STOCK:
        x["r_" + f] = gb[f].rank(pct=True) - 0.5
    fw = np.log(c.shift(-H) / c).stack()
    fw.index.names = ["date", "sym"]
    x = x.merge(fw.rename("fwd").reset_index(), on=["date", "sym"], how="left")
    x["t"] = x.groupby("date")["fwd"].rank(pct=True) - 0.5
    return x


def rank_today(x: pd.DataFrame, w: dict) -> pd.DataFrame:
    """Trung bình hạng 20 phiên gần nhất. Học lại 1/1 và 1/7, đúng như kiểm định, để danh sách không nhảy mỗi ngày."""
    D = np.sort(x["date"].unique())
    asof = pd.Timestamp(D[-1])
    if asof != w["c"].index[-1]:
        raise ValueError("phiên mới nhất của đặc trưng và giá không khớp")
    z = x[x["date"] >= D[-SMOOTH - 20]].copy()  # thêm 20 phiên để biết hạng trước đây
    z["score"] = np.nan
    half = lambda d: pd.Timestamp(d.year, 1 if d.month < 7 else 7, 1)
    for s in sorted({half(d) for d in z["date"]}):
        k = int(np.searchsorted(D, s.to_datetime64()))
        tr = x[(x["date"] < D[k - H - 2]) & x["t"].notna() & x["vol20"].notna()]
        te = z["date"].map(half) == s
        z.loc[te, "score"] = np.mean([lgb.LGBMRegressor(
            n_estimators=300, learning_rate=0.03, num_leaves=31, min_child_samples=500, subsample=0.7,
            subsample_freq=1, colsample_bytree=0.5, reg_lambda=10, random_state=q, n_jobs=-1, verbose=-1,
        ).fit(tr[features.FEATURES], tr["t"]).predict(z.loc[te, features.FEATURES]) for q in range(SEEDS)], axis=0)
    daily = z.pivot(index="date", columns="sym", values="score").rank(axis=1, pct=True)
    member = daily.notna()
    sm = daily.rolling(SMOOTH, min_periods=1).mean().where(member)
    rks = sm.rank(axis=1, ascending=False, method="first")
    now = x[x["date"] == asof].copy()
    if len(now) < TOP * 0.8 or now["m_ret5"].isna().all():
        raise ValueError(f"dữ liệu phiên {asof.date()} chưa đủ ({len(now)} mã)")
    now["score"] = now["sym"].map(sm.iloc[-1])
    for n in (5, 20):
        now[f"ago{n}"] = now["sym"].map(rks.iloc[-1 - n])
    now = now.sort_values("score", ascending=False, kind="stable").reset_index(drop=True)
    now["rank"] = now.index + 1
    now["price"] = w["close"].loc[asof].reindex(now["sym"]).values
    for k, v in price_range(x, D, len(D) - 1).items():
        now[k] = v * now["vol20"].values * H ** 0.5
    return now


def price_range(x: pd.DataFrame, D, i: int) -> dict:
    """Phân vị 10% và 90% của (lợi suất 20 phiên / độ biến động) trong ~1 năm gần nhất, chỉ kết quả đã biết ở phiên i."""
    z = x[(x["date"] >= D[max(0, i - H - 250)]) & (x["date"] <= D[i - H])]
    q = (np.expm1(z["fwd"]) / (z["vol20"] * H ** 0.5)).replace([np.inf, -np.inf], np.nan).dropna()
    return {"lo20": float(q.quantile(0.1)), "hi20": float(q.quantile(0.9))}


def _read(path: str = LOG) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["asof"]) if os.path.exists(path) else pd.DataFrame()


def append(now: pd.DataFrame, path: str = LOG) -> bool:
    """Chỉ ghi thêm; phiên đã ghi (cùng mô hình) không bao giờ bị sửa."""
    old, asof, mid = _read(path), now["date"].iloc[0], model_id()
    if len(old) and ((old["asof"] == asof) & (old["model_id"] == mid)).any():
        return False
    new = pd.DataFrame({"logged_at": data.vn_now().isoformat(timespec="seconds"), "asof": asof, "model_id": mid,
                        "sym": now["sym"], "rank": now["rank"], "score": now["score"].round(6), "price": now["price"]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = pd.concat([old, new], ignore_index=True) if len(old) else new
    out["asof"] = pd.to_datetime(out["asof"]).dt.strftime("%Y-%m-%d")
    out.to_csv(path + ".tmp", index=False)
    os.replace(path + ".tmp", path)
    return True


def valid_days(c: pd.DataFrame, log: pd.DataFrame) -> tuple[dict, int]:
    """Chỉ nhận bản ghi được lưu trước 9:00 phiên kế tiếp."""
    grid, out, late = c.index, {}, 0
    if log.empty:
        return out, late
    for asof, g in log[log["model_id"] == model_id()].groupby("asof"):
        i = int(grid.searchsorted(asof))
        if i >= len(grid) or grid[i] != asof:
            continue
        if i + 1 < len(grid):
            opening = (grid[i + 1] + pd.Timedelta(hours=9)).tz_localize(data.VN)
            if pd.to_datetime(g["logged_at"]).max() >= opening:
                late += 1
                continue
        out[i] = g.sort_values("rank")["sym"].tolist()
    return out, late


def replay(c: pd.DataFrame, op: pd.DataFrame, lo: pd.DataFrame, days: dict) -> dict:
    """Dựng lại danh mục giấy từ nhật ký. Không mua ở giá trần, không bán ở giá sàn."""
    res = {"nav": pd.Series(dtype=float), "hold": {}, "pending": None, "next_in": None, "trades": [], "entry": {}}
    if not days:
        return res
    grid, r = c.index, c.ffill().pct_change(fill_method=None)
    r = r.where(r.abs() < 0.5).fillna(0)
    off = c.isna()
    w, cash, last_sig, todo, out, entry = {}, 1.0, None, None, [], {}
    for i in range(min(days), len(grid)):
        for s in w:
            w[s] *= 1 + r[s].iloc[i]
        for s in list(w):  # ngừng giao dịch 60 phiên: bán với mức phạt 30% như kiểm định
            if i >= 60 and off[s].iloc[i - 59:i + 1].all():
                cash += w.pop(s) * 0.7
        if todo is not None:
            v, mv, nt = sum(w.values()) + cash, r.iloc[i], off.iloc[i]
            rk = {s: n + 1 for n, s in enumerate(todo)}
            keep = [s for s in w if rk.get(s, 999) <= KEEP or mv[s] < -0.065 or nt[s]]
            new = [s for s in todo if s in c and s not in w and mv[s] <= 0.065 and not nt[s]][:max(0, N - len(keep))]
            each, tgt, fee = v / max(N, len(keep) + len(new)), {}, 0.0
            for s in w:
                a = each if s in keep else 0.0
                if nt[s] or (mv[s] < -0.065 and a < w[s]) or (mv[s] > 0.065 and a > w[s]):
                    a = w[s]
                fee += abs(a - w[s]) * COST / 2
                if a > 0:
                    tgt[s] = a
            cash = v - fee - sum(tgt.values())
            part = each * min(1.0, max(0.0, cash) / (each * len(new) * (1 + COST / 2))) if new else 0.0
            fill = {}
            for s in new:  # lệnh đặt ở giá đóng cửa phiên tín hiệu; chưa khớp thì mua giá đóng cửa phiên này
                last, px = c[s].ffill().iloc[i - 1], c[s].iloc[i]
                fill[s] = min(op[s].iloc[i], last) if lo[s].iloc[i] <= last else px
                cash -= part * (1 + COST / 2)
                tgt[s] = part * px / fill[s]
            res["trades"].append({"date": grid[i].date().isoformat(), "buy": new,
                                  "sell": [s for s in w if not tgt.get(s)]})
            old, w = w, tgt
            for s, a in w.items():  # giá vốn trung bình (theo giá điều chỉnh)
                px, was = c[s].iloc[i] if not nt[s] else np.nan, old.get(s, 0.0)
                if s not in entry or s not in old:
                    entry[s] = {"date": grid[i].date().isoformat(), "px": float(fill[s])}
                elif a > was and px == px:
                    entry[s]["px"] = float(a / (was / entry[s]["px"] + (a - was) / px))
            entry = {s: e for s, e in entry.items() if s in w}
            todo = None
        if res["trades"]:
            out.append((grid[i], sum(w.values()) + cash))
        if i in days and (last_sig is None or i - last_sig >= STEP):
            last_sig, todo = i, days[i]
    nav = sum(w.values()) + cash
    res["nav"] = pd.Series(dict(out), dtype=float)
    res["hold"] = {s: a / nav for s, a in w.items()}
    res["entry"] = {s: entry[s] for s in w}
    if todo is not None:  # tín hiệu phiên mới nhất, khớp ở phiên sau
        rk = {s: n + 1 for n, s in enumerate(todo)}
        keep = [s for s in w if rk.get(s, 999) <= KEEP]
        new = [s for s in todo if s not in keep][:max(0, N - len(keep))]
        res["pending"] = {"keep": keep, "buy": new, "sell": [s for s in w if s not in keep]}
    res["next_in"] = max(0, STEP - (len(grid) - 1 - last_sig))
    return res


def skill(c: pd.DataFrame, days: dict) -> dict:
    """Rank IC sống: hạng so với lợi suất 20 phiên sau."""
    ics = []
    for i, order in sorted(days.items()):
        if i + H < len(c):
            f = c.iloc[i + H].reindex(order) / c.iloc[i].reindex(order) - 1
            if f.notna().sum() >= 30:
                ics.append(pd.Series(-np.arange(len(order)), order).where(f.notna()).rank().corr(f.rank()))
    n = len(ics)
    return {"days": n, "waiting": len(days) - n, "ic": float(np.mean(ics)) if n else None,
            "t": _nw_t(ics, H - 1) if n >= 60 else float("nan")}


def build(p: pd.DataFrame, index: pd.DataFrame, etf: pd.DataFrame, log: bool = True) -> dict:
    w = wide(p)
    c = w["c"]
    x = panel(p, w, index)
    now = rank_today(x, w)
    if log:
        append(now)
    days, late = valid_days(c, _read())
    pf = replay(c, w["adOpen"], w["adLow"], days)
    raw, adj = w["close"].ffill().iloc[-1], c.ffill().iloc[-1]
    held = {s: {"date": q["date"], "pnl": float(adj[s] / q["px"] - 1), "price": float(raw[s]),
                "buy": float(q["px"] * raw[s] / adj[s])} for s, q in pf["entry"].items()}  # giá mua quy về mặt bằng giá hôm nay
    nav, e, live = pf["nav"], etf.set_index("date")["close"], None
    if len(nav):
        fr = e.reindex(nav.index).ffill().pct_change(fill_method=None).fillna(0)
        live = {"start": nav.index[0].date().isoformat(), "sessions": len(nav) - 1,
                "fund": float((1 + fr).prod()), "model": float(nav.iloc[-1])}
    rows = [{"sym": r["sym"], "rank": int(r["rank"]), "ago5": r["ago5"], "ago20": r["ago20"], "lo20": r["lo20"], "hi20": r["hi20"], "price": r["price"], "ret20": r["ret20"],
             "vol": r["vol20"] * 250 ** 0.5, "floor20": int(r["floor20"]), "lq": int(r["lqr"])}
            for r in now.to_dict("records")]
    from . import signals, verify  # tránh import vòng
    try:
        sg = signals.build(w, now, index, e, log)
    except Exception as ex:  # lỗi tải khối ngoại/P/E không được làm hỏng danh sách ổn định
        sg = {"error": f"{type(ex).__name__}: {ex}"}
    return {"verify": verify.build(x, w, now, e, log), "signals": sg, "asof": now["date"].iloc[0].date().isoformat(), "model_id": model_id(), "rows": rows,
            "hold": pf["hold"], "held": held, "pending": pf["pending"], "next_in": pf["next_in"], "trades": pf["trades"][-10:],
            "live": live, "skill": skill(c, days), "late": late, "logged": len(days),
            "fund": {"sym": ETF, "price": float(e.iloc[-1]), "date": etf["date"].iloc[-1].date().isoformat()}}
