"""output/forecast.html: biểu đồ quạt 40 phiên gần nhất + 5 phiên dự báo cho từng mã, kèm bảng số."""
from __future__ import annotations

import html
import json
import os

import numpy as np

from .levels import tick
from .report import outdir_for

W, HT, L, R, T, B, HIST = 330, 190, 46, 10, 10, 24, 40
CSS = """body{font:14px system-ui;max-width:1080px;margin:24px auto;padding:0 16px;color:#0b0b0b;background:#fff}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
figure{margin:0;border:1px solid #e1e0d9;border-radius:8px;padding:10px;position:relative}
figcaption{font-weight:600;margin-bottom:4px}figcaption span{font-weight:400;color:#52514e}
svg{width:100%;height:auto;display:block}svg text{font:11px system-ui;fill:#52514e}
.k{display:flex;gap:18px;flex-wrap:wrap;margin:8px 0 14px;color:#52514e}.k i{display:inline-block;width:18px;height:10px;margin-right:6px}
.tip{position:absolute;display:none;background:#0b0b0b;color:#fff;font-size:12px;padding:4px 7px;border-radius:4px;pointer-events:none;white-space:nowrap;z-index:2}
.t{overflow-x:auto}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #e1e0d9;padding:5px 8px;text-align:right;white-space:nowrap}
td:first-child,th:first-child{text-align:left}.w{background:#fff4e5;padding:10px 14px;border-radius:6px}"""
JS = """document.querySelectorAll('figure').forEach(f=>{const s=f.querySelector('svg'),t=f.querySelector('.tip'),
p=JSON.parse(f.dataset.p),c=s.querySelector('.x');
s.addEventListener('pointermove',e=>{const r=s.getBoundingClientRect(),x=(e.clientX-r.left)*%d/r.width;
let b=p[0];p.forEach(q=>{if(Math.abs(q[0]-x)<Math.abs(b[0]-x))b=q});c.setAttribute('x1',b[0]);c.setAttribute('x2',b[0]);
c.style.display='block';t.textContent=b[1];t.style.display='block';
t.style.left=Math.max(0,Math.min(b[0]*r.width/%d-40,f.clientWidth-t.offsetWidth-4))+'px';t.style.top='34px'});
s.addEventListener('pointerleave',()=>{t.style.display='none';c.style.display='none'})})""" % (W, W)


def _chart(sym: str, hist, g) -> str:
    hist = hist.tail(HIST)
    px, base = hist["close"].values, float(hist["close"].iloc[-1])
    g = g.sort_values("h")
    band = {k: np.r_[base, base * np.exp(g[k].values)] for k in ("center", "lo80", "lo50", "hi50", "hi80")}
    lo, hi = min(px.min(), band["lo80"].min()), max(px.max(), band["hi80"].max())
    pad = (hi - lo) * 0.06 or 1
    lo, hi, n = lo - pad, hi + pad, len(px) + len(g)

    def X(i):
        return round(L + i * (W - L - R) / (n - 1), 1)

    def Y(v):
        return round(T + (hi - v) * (HT - T - B) / (hi - lo), 1)

    k0 = len(px) - 1

    def area(a, b):
        up = [f"{X(k0 + i)},{Y(v)}" for i, v in enumerate(band[b])]
        dn = [f"{X(k0 + i)},{Y(v)}" for i, v in enumerate(band[a])]
        return " ".join(up + dn[::-1])

    grid = "".join(f"<line x1={L} x2={W - R} y1={Y(v)} y2={Y(v)} stroke='#e1e0d9'/><text x={L - 5} y={Y(v) + 4} "
                   f"text-anchor=end>{v:.{1 if v >= 50 else 2}f}</text>" for v in np.linspace(lo + pad, hi - pad, 4))
    line = " ".join(f"{X(i)},{Y(v)}" for i, v in enumerate(px))
    mid = " ".join(f"{X(k0 + i)},{Y(v)}" for i, v in enumerate(band["center"]))
    pts = [[X(i), f"{d:%d/%m}: {v:.2f}"] for i, (d, v) in enumerate(zip(hist["date"], px))]
    pts += [[X(k0 + i), f"Phiên +{i}: {tick(band['lo80'][i])} – {tick(band['hi80'][i])} (80%)"] for i in range(1, len(g) + 1)]
    return (f"<figure data-p='{html.escape(json.dumps(pts, ensure_ascii=False))}'><figcaption>{html.escape(sym)} "
            f"<span>{base:.2f} → phiên +5: {tick(band['lo80'][-1])} – {tick(band['hi80'][-1])}</span></figcaption>"
            f"<svg viewBox='0 0 {W} {HT}' role=img aria-label='{html.escape(sym)}'>{grid}"
            f"<polygon points='{area('lo80', 'hi80')}' fill='#2a78d6' opacity='.2'/>"
            f"<polygon points='{area('lo50', 'hi50')}' fill='#2a78d6' opacity='.35'/>"
            f"<polyline points='{line}' fill=none stroke='#0b0b0b' stroke-width=2 stroke-linejoin=round />"
            f"<polyline points='{mid}' fill=none stroke='#1c5cab' stroke-width=2 stroke-dasharray='4 3'/>"
            f"<text x={L} y={HT - 6}>{hist['date'].iloc[0]:%d/%m}</text>"
            f"<text x={X(k0)} y={HT - 6} text-anchor=end>{hist['date'].iloc[-1]:%d/%m}</text>"
            f"<text x={W - R} y={HT - 6} text-anchor=end>+5</text>"
            f"<line class=x y1={T} y2={HT - B} stroke='#898781' style='display:none'/></svg><div class=tip></div></figure>")


def write(res: dict, frames: dict, order: list[str], notes: list[str], provider: str) -> str:
    f = res["f"]
    syms = [s for s in order if s in set(f["sym"])]
    figs = "".join(_chart(s, frames[s], f[f["sym"] == s]) for s in syms)
    rows = ""
    for s in syms:
        g = f[f["sym"] == s].sort_values("h")
        cells = "".join(f"<td>{tick(r.close * np.exp(r.lo80))} – {tick(r.close * np.exp(r.hi80))}</td>" for r in g.itertuples())
        rows += f"<tr><td><b>{html.escape(s)}</b></td><td>{g['close'].iloc[0]:.2f}</td>{cells}</tr>"
    head = "".join(f"<th>Phiên +{h}</th>" for h in sorted(f["h"].unique()))
    demo = "<p class=w><b>DỮ LIỆU GIẢ (demo)</b></p>" if provider == "synthetic" else ""
    page = f"""<!doctype html><html lang=vi><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Dự báo chuỗi thời gian</title><style>{CSS}</style><h1>Dự báo chuỗi thời gian 5 phiên</h1>{demo}
<p>Từ giá đóng cửa {f['asof'].iloc[0]:%d/%m/%Y} · Giá: nghìn đồng · <a href=report.html>Về báo cáo xếp hạng</a></p>
<p class=w>Dải giá là phần đáng tin. Đường giữa chỉ là mốc, <b>không phải</b> giá chắc chắn xảy ra. Không phải lời khuyên đầu tư.</p>
<ul>{''.join(f'<li>{html.escape(t)}</li>' for t in notes)}</ul>
<div class=k><span><i style="background:#0b0b0b;height:2px;vertical-align:middle"></i>Giá thật</span>
<span><i style="border-top:2px dashed #1c5cab;height:0;vertical-align:middle"></i>Đường giữa</span>
<span><i style="background:#2a78d6;opacity:.55"></i>Dải 50%</span><span><i style="background:#2a78d6;opacity:.2"></i>Dải 80%</span></div>
<div class=g>{figs}</div><h2>Bảng dải 80%</h2><div class=t><table><tr><th>Mã</th><th>Giá</th>{head}</tr>{rows}</table></div>
<script>{JS}</script></html>"""
    path = os.path.join(outdir_for(provider), "forecast.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    f.drop(columns="asof").to_csv(os.path.join(outdir_for(provider), "forecast.csv"), index=False)
    return path
