"""Ghi CSV/JSON/HTML."""
from __future__ import annotations

import html
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLOR = {"MUA": "#0a7d33", "HANG CAO": "#1a6fb5", "HANG THAP": "#b3261e", "RUI RO CAO": "#b3261e"}
CSS = """body{font:14px system-ui;max-width:1080px;margin:24px auto;padding:0 16px;color:#222;background:#fff}
div{overflow-x:auto}table{border-collapse:collapse;width:100%;margin-bottom:12px}
td,th{border-bottom:1px solid #ddd;padding:6px 8px;text-align:right;white-space:nowrap}
td:nth-child(-n+3),th:nth-child(-n+3){text-align:left}.w{background:#fff4e5;padding:10px 14px;border-radius:6px}"""


def outdir_for(provider: str) -> str:
    return os.path.join(ROOT, "output", "demo") if provider == "synthetic" else os.path.join(ROOT, "output")


def write_outputs(df: pd.DataFrame, info: dict, sector: str | None = None) -> str:
    outdir = outdir_for(info["provider"])
    os.makedirs(outdir, exist_ok=True)
    tag = "_" + "".join(c if c.isalnum() else "_" for c in sector) if sector else ""
    df.to_csv(os.path.join(outdir, f"latest{tag}.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(outdir, f"latest{tag}.json"), "w", encoding="utf-8") as f:
        json.dump({"info": info, "rows": df.to_dict("records")}, f, ensure_ascii=False, indent=1)
    path = os.path.join(outdir, f"report{tag}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_html(df, info))
    return path


def render_html(df: pd.DataFrame, info: dict) -> str:
    val, e = info["validation"], html.escape
    vrows = "".join(
        f"<tr><td>{n}</td><td>{m['periods']}</td><td>{m['rank_ic']:.3f} (t={m['ic_t']:.1f})</td>"
        f"<td>{m['gross_excess_yr']:+.1%}</td><td>{m['net_excess_yr']:+.1%} (t={m['net_t']:.1f})</td>"
        f"<td>{m['coverage80']:.0%}</td></tr>"
        for n, m in (("Phát triển", val.get("dev")), ("Giữ lại để kiểm tra", val.get("holdout"))) if m)
    gate = ("Kiểm định ĐẠT: cho phép tín hiệu MUA." if val["gate"] else
            "Kiểm định CHƯA ĐẠT: lợi nhuận vượt trội sau phí chưa có ý nghĩa thống kê, nên tín hiệu MUA bị khoá. "
            "Hạng chỉ để tham khảo.")
    trs = "".join(
        f"<tr><td>{r.hang}</td><td><b>{e(r.ma)}</b></td><td>{e(r.nganh)}</td><td>{r.gia_hien_tai}</td>"
        f"<td>{r.khoang_80_tu} – {r.khoang_80_den}</td><td>{r.vung_mua_tu} – {r.vung_mua_den}</td>"
        f"<td>{r.vung_ban}</td><td>{r.cat_lo}</td><td>{r.rsi}</td>"
        f"<td style='color:{COLOR.get(r.tin_hieu, '#666')};font-weight:600'>{r.tin_hieu}</td></tr>"
        for r in df.itertuples())
    warn = "".join(f"<li>{e(w)}</li>" for w in info["warnings"])
    warn = f"<h3>Cảnh báo</h3><ul class=w>{warn}</ul>" if warn else ""
    acc = "".join(f"<li>{e(t)}</li>" for t in [*info.get("accuracy", []), info.get("learned", "")])
    ts = "".join(f"<li>{e(t)}</li>" for t in info.get("forecast", []))
    ts = f"<h2>Dự báo chuỗi thời gian</h2><p><a href=forecast.html>Xem biểu đồ 5 phiên từng mã</a></p><ul>{ts}</ul>" if ts else ""
    live = "".join(f"<li>{e(t)}</li>" for t in info.get("live", []))
    live = f"<h2>Điểm trên dữ liệu sống</h2><ul>{live}</ul>" if live else ""
    src = "DỮ LIỆU GIẢ (demo)" if info["provider"] == "synthetic" else info["provider"]
    day = df["ngay_du_lieu"].iloc[0] if len(df) else "?"
    return f"""<!doctype html><html lang=vi><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>VN Stock Advisor</title><style>{CSS}</style>
<h1>VN Stock Advisor</h1><p>Cập nhật {info['updated']} (giờ VN) · Phiên dữ liệu {day} · Dự báo {info['horizon']} phiên
· Nguồn: {e(src)} · Giá: nghìn đồng</p><p class=w><b>{gate}</b> Không phải lời khuyên đầu tư.</p>
<h2>Xếp hạng</h2><div><table><tr><th>Hạng</th><th>Mã</th><th>Ngành</th><th>Giá</th><th>Khoảng 80%</th><th>Vùng mua</th>
<th>Chốt lời</th><th>Cắt lỗ</th><th>RSI</th><th>Tín hiệu</th></tr>{trs}</table></div>
<h2>Kiểm định walk-forward</h2><div><table><tr><th>Giai đoạn</th><th>Số kỳ</th><th>Rank IC</th>
<th>Vượt trội/năm trước phí</th><th>Vượt trội/năm sau phí</th><th>Độ phủ khoảng 80%</th></tr>{vrows}</table></div>
<p>Vượt trội = so với nắm giữ đều toàn bộ danh sách. Chốt lời = mức khoảng 25% trường hợp lịch sử chạm tới; đáy vùng mua
= khoảng 50% chạm tới. RUI RO CAO = từ 3 phiên giảm trên 6% trong 20 phiên gần nhất.</p><h2>Độ chính xác theo kỳ hạn</h2><ul>{acc}</ul>{ts}{live}{warn}</html>"""
