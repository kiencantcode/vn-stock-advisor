"""Tải dữ liệu -> đặc trưng -> kiểm định -> xếp hạng -> vùng giá."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

import pandas as pd
import yaml

from . import accuracy, data, fanchart, features, forecast, levels, model, short, site, track, vnd
from .report import ROOT, outdir_for, write_outputs  # noqa: F401


def load_config(path: str | None = None) -> dict:
    with open(path or os.path.join(ROOT, "config.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _signature(cfg: dict, syms: list[str]) -> str:
    key = {"cfg": {k: cfg[k] for k in ("horizon", "history_days", "portfolio", "validation")},
           "core": sorted(s for v in cfg["sectors"].values() for s in v), "syms": sorted(syms)}
    blob = json.dumps(key, sort_keys=True, default=str)
    for m in (features, model):
        with open(m.__file__, encoding="utf-8") as f:
            blob += f.read()
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def get_validation(x, core, cfg, outdir, force=False) -> dict:
    path, sig = os.path.join(outdir, "validation.json"), _signature(cfg, list(x["sym"].unique()))
    if not force and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        age = (datetime.now() - datetime.fromisoformat(old["run_at"])).days
        if old["sig"] == sig and age <= cfg["validation"]["max_age_days"]:
            return old
    print("Đang kiểm định walk-forward (vài phút)...", flush=True)
    res = {**model.validate(x, core, cfg), "sig": sig, "run_at": datetime.now().isoformat(timespec="seconds")}
    os.makedirs(outdir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


def run(cfg: dict, provider: str | None = None, only_sector: str | None = None,
        force_validate: bool = False, log: bool = True,
        force_accuracy: bool = False) -> tuple[pd.DataFrame, dict]:
    provider = provider or cfg.get("provider", "auto")
    H = cfg["horizon"] = int(cfg.get("horizon", 5))
    sector_of = {s: sec for sec, syms in cfg["sectors"].items() for s in syms}
    if only_sector and not any(only_sector.lower() in s.lower() for s in cfg["sectors"]):
        raise SystemExit(f"Không có ngành '{only_sector}'. Các ngành: {', '.join(cfg['sectors'])}")
    syms = list(dict.fromkeys([*sector_of, *cfg.get("train_extra", [])]))
    frames, warnings = data.load_many(syms, cfg["history_days"], provider)
    for s in [s for s, d in frames.items() if len(d) < cfg["min_history"]]:
        warnings.append(f"{s}: chỉ có {len(frames.pop(s))} phiên, bỏ qua")
    if len(frames) < 10 or not set(frames) & set(sector_of):
        raise SystemExit("Quá ít mã tải được, dừng lại.\n" + "\n".join(warnings))
    index = None
    if provider != "synthetic":
        try:
            index = data.load(data.INDEX, cfg["history_days"], provider)
        except Exception as e:
            warnings.append(f"VNINDEX: {e} (dùng trung bình các mã thay thế)")
    store = None
    if provider != "synthetic":
        try:
            store = vnd.update()
            frames = vnd.true_value(frames, store)
        except Exception as e:
            warnings.append(f"VNDirect: {e}. Không cập nhật mô hình 1 tháng, không ghi nhật ký phiên này.")
            log = False  # đặc trưng dùng khối lượng chưa sửa: không được chấm điểm
    x = features.build_panel(frames, index, H)
    core = set(sector_of) & set(frames)
    val = get_validation(x, core, cfg, outdir_for(provider), force_validate)

    asof = x["date"].max()
    now = x[(x["date"] == asof) & x["sym"].isin(core) & x["vol20"].notna() & x["atr_pct"].notna()].copy()
    for s in sorted(core - set(now["sym"])):
        warnings.append(f"{s}: không có dữ liệu ngày {asof.date()}, bỏ qua")
    if (data.vn_now().date() - asof.date()).days > 5:
        warnings.append(f"Dữ liệu cũ: phiên mới nhất là {asof.date()}")
    now["score"] = model.fit_predict(model.trainable(x), now)
    now = now.sort_values("score", ascending=False).reset_index(drop=True)
    conf = model.conformal(x, asof, H)
    rows = [{"nganh": sector_of[r["sym"]], "ma": r["sym"], "ngay_du_lieu": asof.date().isoformat(),
             **levels.make_levels(r, conf, i + 1, len(now), H, val["gate"])} for i, r in now.iterrows()]
    df = pd.DataFrame(rows)
    live = None
    acc = accuracy.build(frames, index, core, cfg, outdir_for(provider), force_accuracy)
    tr = model.trainable(x)
    learned = f"Mô hình lần này học từ {len(tr):,} mẫu, kết quả mới nhất đã biết: phiên {tr['date'].max().date()}"
    if provider != "synthetic":
        try:
            frozen = track.frozen_rank(x, now, cfg) if log else None
            if log and not track.append(now, conf, df, cfg, frozen=frozen):
                print(f"Phiên {asof.date()} đã có trong nhật ký, giữ nguyên bản ghi đầu tiên.")
            live = track.score(frames, cfg)
            if track.failing(live):
                df.loc[df["tin_hieu"].isin(["MUA", "HANG CAO"]), "tin_hieu"] = "TAM DUNG"
                warnings.append("Điểm sống âm có ý nghĩa thống kê: tạm dừng tín hiệu hạng cao.")
        except OSError as e:  # ví dụ rankings.csv đang mở trong Excel
            warnings.append(f"KHÔNG ghi/chấm được nhật ký: {e}. Đóng file rồi chạy lại trước 9:00 phiên kế tiếp.")
    notes: list[str] = []
    fc = None
    try:
        fc = forecast.build(frames, index, core)
        notes = forecast.summary(fc)
        if provider != "synthetic":
            try:
                if log:
                    forecast.append(fc)
                notes += forecast.score(frames)
            except OSError as e:
                warnings.append(f"KHÔNG ghi/chấm được nhật ký chuỗi thời gian: {e}. Đóng file rồi chạy lại trước 9:00.")
        fanchart.write(fc, frames, [r["ma"] for r in rows], notes, provider)
    except ValueError as e:
        warnings.append(f"Chuỗi thời gian: {e}")
    sh = None
    if store is not None and index is not None:
        try:
            sh = short.build(store, index, data.load(short.ETF, cfg["history_days"], provider), log)
        except Exception as e:
            warnings.append(f"Mô hình 1 tháng: {e}")
    updated = data.vn_now().strftime("%Y-%m-%d %H:%M")
    site.write(provider, updated, df, frames, fc, val, acc, live, warnings, sh)
    if only_sector:
        df = df[df["nganh"].str.lower().str.contains(only_sector.lower(), regex=False)]
    return df, {"updated": updated, "horizon": H, "provider": provider,
                "n_ranked": len(now), "validation": val, "accuracy": accuracy.lines(acc), "learned": learned,
                "live": track.summary(live) if live else [],
                "forecast": notes, "warnings": warnings}


def score_only(cfg: dict, provider: str | None = None) -> list[str]:
    """Tải giá mới và chấm điểm nhật ký, không huấn luyện."""
    cfg["horizon"] = int(cfg.get("horizon", 5))
    syms = [s for v in cfg["sectors"].values() for s in v]
    frames, warnings = data.load_many(syms, cfg["history_days"], provider or cfg.get("provider", "auto"))
    return track.summary(track.score(frames, cfg)) + forecast.score(frames) + [f"CẢNH BÁO: {w}" for w in warnings]
