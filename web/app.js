"use strict";
const $ = (id) => document.getElementById(id);
const onPages = location.hostname.endsWith(".github.io");
const OWNER = onPages ? location.hostname.split(".")[0] : "";
const REPO = onPages ? location.pathname.split("/")[1] : "";
const WORKFLOW = "daily.yml", KEY = `vnsa-key-${REPO}`;
const SIG = { "MUA": ["Mua", "up"], "HANG CAO": ["Hạng cao", "up"], "TRUNG LAP": ["Trung lập", ""], "HANG THAP": ["Hạng thấp", "down"],
  "RUI RO CAO": ["Rủi ro cao", "down"], "TAM DUNG": ["Tạm dừng", "down"] };
const SECT = { "Ngan hang": "Ngân hàng", "Thep": "Thép", "Bat dong san": "Bất động sản", "Chung khoan": "Chứng khoán", "Cong nghe": "Công nghệ",
  "Tieu dung": "Tiêu dùng", "Dau khi": "Dầu khí", "Dien nuoc": "Điện nước" };
let D = null, tab = "plan";

function el(tag, attrs = {}, ...kids) {  // text only: never inserts HTML
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) k === "class" ? e.className = v : k.startsWith("on") ? e.addEventListener(k.slice(2), v) : e.setAttribute(k, v);
  e.append(...kids); return e;
}
function sv(tag, attrs = {}, text) {
  const e = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text; return e;
}
const f2 = (v) => v == null ? "–" : Number(v).toFixed(v >= 50 ? 1 : 2);
const pc = (v, s) => v == null ? "–" : (s && v > 0 ? "+" : "") + (v * 100).toFixed(1) + "%";
const tv = (v) => v == null ? "chưa đủ dữ liệu" : "t = " + v.toFixed(1);
const store = { get() { try { return sessionStorage.getItem(KEY) || localStorage.getItem(KEY); } catch { return null; } },
  set(v, keep) { this.del(); try { (keep ? localStorage : sessionStorage).setItem(KEY, v); } catch { } },
  del() { try { sessionStorage.removeItem(KEY); localStorage.removeItem(KEY); } catch { } } };
function say(t) { $("status").textContent = t; $("status").hidden = !t; }

function table(head, rows, left = 1) {
  return el("div", { class: "scroll" }, el("table", {}, el("thead", {}, el("tr", {}, ...head.map((h, i) => el("th", { class: i < left ? "l" : "" }, h)))),
    el("tbody", {}, ...rows)));
}
const row = (cells, left = 1) => el("tr", {}, ...cells.map((c, i) => el("td", { class: i < left ? "l" : "" }, c)));

function filtered() {
  const q = $("q").value.trim().toUpperCase(), s = $("sector").value;
  return D.stocks.filter((x) => (!q || x.sym.includes(q)) && (!s || x.sector === s));
}
const money = () => Number($("money").value.replace(/\D/g, "")) || 0;
const vnd = (v) => Math.round(v).toLocaleString("vi-VN") + " VND";
const list = (a) => a.length ? a.join(", ") : "không có";
const rng = (r) => r && r.lo20 != null ? `${f2(r.price * (1 + r.lo20))} – ${f2(r.price * (1 + r.hi20))}` : "–";
const gain = (v) => el("span", { class: "sig " + (v > 0 ? "up" : v < 0 ? "down" : "") }, pc(v, 1));
function drawPlan() {
  const m = money(), s = D.steady, out = [];
  if (!s) return $("planout").replaceChildren(el("p", { class: "notice" }, "Danh sách sẽ hiện sau lần cập nhật tới."));
  const px = Object.fromEntries(s.rows.map((r) => [r.sym, r])), held = s.held || {}, val = m * (s.live ? s.live.model : 1);
  const line = (sym, w, what) => { const r = px[sym], h = held[sym], p = r ? r.price : h ? h.price : null, a = val * w, n = p ? Math.floor(a / (p * 1000)) : null;
    return row([sym, what, r ? String(r.rank) : "ngoài 100", f2(p), what.startsWith("Mua") ? el("b", {}, f2(p)) : "–", h ? `${f2(h.buy)} (${h.date})` : "chưa mua", h ? gain(h.pnl) : "–", rng(r), vnd(a),
      n == null ? "–" : n.toLocaleString("vi-VN") + (n > 0 && n < 100 ? " (lô lẻ)" : "")], 2); };
  const head = ["Mã", "Việc cần làm (trên giấy)", "Hạng ổn định", "Giá hiện tại", "Giá đặt mua", "Giá đã mua", "Lãi/lỗ", "Khoảng 20 phiên tới (8/10 lần)", "Số tiền", "Số cổ phiếu"];
  if (s.pending) {
    const q = s.pending, all = [...q.keep, ...q.buy];
    out.push(el("p", { class: "notice" }, `Ngày xem lại. Phiên kế tiếp, mua giả: ${list(q.buy)}. Bán: ${list(q.sell)}. Giữ: ${list(q.keep)}. Đặt lệnh đúng giá ở cột Giá đặt mua; nếu đến cuối phiên chưa khớp thì mua ở giá đóng cửa. Mã cần bán thì bán ở giá đóng cửa. Sau đó không cần làm gì trong 5 phiên.`),
      table(head, [...all.map((x) => line(x, 1 / Math.max(6, all.length), q.buy.includes(x) ? "Mua phiên kế tiếp" : "Giữ")), ...q.sell.map((x) => line(x, s.hold[x] || 0, "Bán phiên kế tiếp"))], 2));
  } else if (Object.keys(s.hold).length) {
    out.push(el("p", { class: "notice" }, `Không cần làm gì. Còn ${s.next_in} phiên tới ngày xem lại. Chỉ khi đó mới bán mã rớt khỏi hạng 18.`),
      table(head, Object.entries(s.hold).sort((a, b) => b[1] - a[1]).map(([x, w]) => line(x, w, "Giữ")), 2));
  }
  out.push(el("p", { class: "muted" }, `Theo giá đóng cửa ${s.asof}, nghìn đồng. Khoảng 20 phiên không phải giá mục tiêu. Chỉ theo dõi trên giấy, không phải lời khuyên đầu tư.`));
  if (s.trades.length) out.push(el("h3", {}, "Giao dịch giả gần đây"), table(["Ngày", "Mua", "Bán"], s.trades.slice().reverse().map((t) => row([t.date, list(t.buy), list(t.sell)], 3)), 3));
  out.push(el("h2", {}, "Kết quả thật từ khi bắt đầu"));
  if (s.live) out.push(el("p", {}, `Từ ${s.live.start}: ${s.live.sessions} phiên.` + (s.live.sessions < 120 ? " Còn quá sớm để kết luận, cần khoảng 120 phiên (6 tháng)." : "")),
    table(["", "Thay đổi", "Tiền giả định thành"], [["Danh sách ổn định, sau phí", s.live.model], ["Quỹ chỉ số E1VFVN30", s.live.fund]].map(([n, v]) => row([n, gain(v - 1), vnd(m * v)]))));
  else out.push(el("p", {}, "Bắt đầu từ lần mua giả đầu tiên."));
  out.push(el("h2", {}, "Kiểm định quá khứ, mỗi năm"), table(["Cách đầu tư", "2018–2022", "2023–2026", "Giảm nặng nhất 2018–2026"],
    [["Danh sách ổn định, sau phí", "28%", "19%", "−60%"], ["Mua đều 100 mã, chưa trừ phí", "4%", "12%", "−58%"], ["Quỹ E1VFVN30", "1%", "18%", "−48%"], ["Nếu mỗi năm chỉ chọn cách tốt nhất từ quá khứ", "–", "15%", "−62% (2020–2026)"]].map((r) => row(r))),
    el("p", { class: "notice" }, "Chưa được chứng minh. Cách này được chọn trong 16.800 trường hợp trên toàn bộ dữ liệu, nên 28% và 19% là con số đẹp hơn thực tế. Dòng cuối mới là ước lượng công bằng: 15% mỗi năm trong 2023–2026, thấp hơn quỹ (18%). Năm 2025 và 2026 cách này đều lỗ. Nếu chỉ mua 50 mã giao dịch nhiều nhất thì còn 12%. Số liệu này tính đến 23/11/2026 và không tự đổi; phần kết quả thật ở trên mới tự cập nhật."));
  const ag = (v) => v == null ? "–" : String(v);
  out.push(el("h2", {}, "Hạng ổn định, 30 mã đầu"), table(["Hạng", "Mã", "Hạng 1 tuần trước", "Hạng 1 tháng trước", "Giá", "20 phiên qua", "Khoảng 20 phiên tới", "Biến động năm", "Cảnh báo"],
    s.rows.slice(0, 30).map((r) => row([String(r.rank), r.sym, ag(r.ago5), ag(r.ago20), f2(r.price), pc(r.ret20, 1), rng(r), pc(r.vol), r.floor20 >= 3 ? el("span", { class: "sig down" }, "Rủi ro cao") : ""], 2)), 2));
  $("planout").replaceChildren(...out);
}
function drawCheck() {
  const v = D.steady && D.steady.verify;
  if (!v) return $("check").replaceChildren(el("p", {}, "Phần này hiện sau lần cập nhật tới."));
  const s = v.summary, out = [], tries = (n, d) => d ? `${n}/${d} tuần` : "–";
  out.push(el("p", { class: "notice" }, s.pass ? "Đạt mức tối thiểu: từ 26 tuần trở lên và thắng quỹ rõ ràng (t ≥ 1.65). Vẫn có thể lỗ." :
    `Chưa đạt. Cần ít nhất 26 tuần và thắng quỹ với t ≥ 1.65 (hiện có ${s.weeks} tuần). Một tuần chưa nói lên điều gì: trong 2023–2026, sau một tuần thắng quỹ, tuần kế tiếp vẫn kém quỹ trung bình 0,1%.`));
  out.push(el("h2", {}, "Điểm chung, các tuần không chồng nhau"), table(["Chỉ số", "Kết quả thật", "Khi thử 2023–2026"], [
    row(["Số tuần đã kiểm chứng", String(s.weeks), "–"]), row(["Tuần có lời, sau phí", tries(s.up, s.weeks), "49%"]), row(["Tuần thắng quỹ E1VFVN30", tries(s.beat, s.weeks), "42%"]),
    row(["Giá thật nằm trong khoảng dự đoán", pc(s.inside), "79%"]), row(["Tổng lãi/lỗ của dự đoán, sau phí", s.ret == null ? "–" : gain(s.ret), "–"]), row(["Tổng lãi/lỗ của quỹ", s.fund == null ? "–" : gain(s.fund), "–"]),
    row(["Tuần tệ nhất", pc(s.worst, 1), "−16,8%"]), row(["Độ chắc chắn (t)", s.t == null ? "cần ít nhất 8 tuần" : s.t.toFixed(1), "–"])]));
  out.push(el("p", { class: "muted" }, "Mỗi dự đoán được tính như mua mới 6 mã rồi bán hết sau 5 phiên, nên phí cao hơn Danh sách ổn định (chỉ bán mã rớt hạng)."));
  for (const d of v.items) {
    const st = d.late ? "Lưu trễ, không tính." : d.done ? `Đã kiểm chứng đến ${d.until}.` : d.until ? `Đang chờ: đã giữ ${d.age}/5 phiên, giá đến ${d.until}.` : "Đang chờ phiên kế tiếp để mua.";
    out.push(el("h3", {}, `Dự đoán ngày ${d.asof}`), el("p", {}, st + (d.ret == null ? "" : ` Trung bình ${pc(d.ret, 1)} sau phí, quỹ ${pc(d.fund, 1)}.`)),
      table(["Mã", "Giá đặt mua", "Khoảng dự đoán (8/10 lần)", "Giá khớp", d.done ? "Giá sau 5 phiên" : "Giá mới nhất", "Lãi/lỗ sau phí", "Đúng khoảng?"],
        d.picks.map((p) => row([p.sym, f2(p.buy), `${f2(p.lo)} – ${f2(p.hi)}`, p.fill == null ? "chưa mua" : typeof p.fill === "string" ? p.fill : f2(p.fill), f2(p.now), p.ret == null ? "–" : gain(p.ret), p.inside == null ? "–" : p.inside ? "Đúng" : "Sai"]))));
  }
  $("check").replaceChildren(...out);
}
function showStock(sym) { $("q").value = sym; go("charts"); }
function drawRank() {
  const rows = filtered().map((s) => {
    const [name, cls] = SIG[s.signal] || [s.signal, ""], last = s.fc[s.fc.length - 1];
    const tr = row([String(s.rank), el("button", { class: "link", "aria-label": `Biểu đồ ${s.sym}` }, s.sym), SECT[s.sector] || s.sector, f2(s.price),
      last ? `${f2(last.lo80)} – ${f2(last.hi80)}` : "–", el("b", {}, f2(s.price)), f2(s.target), f2(s.stop), s.rsi.toFixed(0),
      el("span", { class: "sig " + cls }, name)], 3);
    tr.classList.add("click"); tr.addEventListener("click", () => showStock(s.sym)); return tr;
  });
  $("rank").replaceChildren(el("p", { class: "notice" }, "Chỉ nhìn 5 phiên tới. Khi kiểm tra, khoảng 42% nhóm 6 mã đầu thay đổi mỗi ngày, nên không hợp để giữ cả tuần. Muốn giữ lâu hơn, hãy theo Danh sách ổn định, trên giấy. Giá đặt mua chỉ nên thử trên giấy, có hiệu lực 3 phiên: trong 2023–2026 cách này vẫn lỗ trung bình 0,11% mỗi lệnh sau phí."), rows.length ? table(["Hạng", "Mã", "Ngành", "Giá", "Khoảng 80%, phiên 5", "Giá đặt mua", "Chốt lời", "Cắt lỗ", "RSI", "Tín hiệu"], rows, 3)
    : el("p", { class: "muted" }, "Không có mã phù hợp."));
}
function chart(s) {
  const W = 330, H = 190, L = 46, R = 10, T = 10, B = 24, px = s.close, k0 = px.length - 1, n = px.length + s.fc.length;
  const base = px[k0], b = (k) => [base, ...s.fc.map((x) => x[k])], all = [...px, ...b("lo80"), ...b("hi80")];
  let lo = Math.min(...all), hi = Math.max(...all); const pad = (hi - lo) * .06 || 1; lo -= pad; hi += pad;
  const X = (i) => L + i * (W - L - R) / (n - 1), Y = (v) => T + (hi - v) * (H - T - B) / (hi - lo);
  const pts = (a, o = 0) => a.map((v, i) => `${X(i + o).toFixed(1)},${Y(v).toFixed(1)}`);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${s.sym}: 40 phiên gần nhất và dự báo 5 phiên` });
  for (let i = 0; i < 4; i++) { const v = lo + pad + i * (hi - lo - 2 * pad) / 3; svg.append(sv("line", { class: "gl", x1: L, x2: W - R, y1: Y(v), y2: Y(v) }), sv("text", { x: L - 5, y: Y(v) + 4, "text-anchor": "end" }, f2(v))); }
  for (const c of ["80", "50"]) svg.append(sv("polygon", { class: "b" + c, points: [...pts(b("hi" + c), k0), ...pts(b("lo" + c), k0).reverse()].join(" ") }));
  svg.append(sv("polyline", { class: "pl", points: pts(px).join(" ") }), sv("polyline", { class: "ml", points: pts(b("center"), k0).join(" ") }));
  const dm = (d) => d.slice(8) + "/" + d.slice(5, 7);
  svg.append(sv("text", { x: L, y: H - 6 }, dm(s.dates[0])), sv("text", { x: X(k0), y: H - 6, "text-anchor": "end" }, dm(s.dates[k0])), sv("text", { x: W - R, y: H - 6, "text-anchor": "end" }, "+" + s.fc.length));
  const x = sv("line", { class: "x", y1: T, y2: H - B, visibility: "hidden" }); svg.append(x);
  const tip = el("div", { class: "tip", hidden: "" });
  svg.addEventListener("pointermove", (e) => {
    const r = svg.getBoundingClientRect(), i = Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left) * W / r.width - L) / (W - L - R) * (n - 1))));
    x.setAttribute("x1", X(i)); x.setAttribute("x2", X(i)); x.setAttribute("visibility", "visible"); tip.hidden = false;
    const p = s.fc[i - k0 - 1]; tip.textContent = p ? `Phiên +${i - k0}: ${f2(p.lo80)} – ${f2(p.hi80)} (80%)` : `${dm(s.dates[i])}: ${f2(px[i])}`;
  });
  svg.addEventListener("pointerleave", () => { tip.hidden = true; x.setAttribute("visibility", "hidden"); });
  return el("figure", {}, el("figcaption", {}, s.sym + " ", el("span", {}, `hạng ${s.rank} · ${f2(s.price)}`)), svg, tip);
}
function swatch(cls, text, line) {
  const g = sv("svg", { viewBox: "0 0 22 10", "aria-hidden": "true" });
  g.append(line ? sv("line", { class: cls, x1: 0, x2: 22, y1: 5, y2: 5 }) : sv("rect", { class: cls, width: 22, height: 10 }));
  return el("span", {}, g, text);
}
function drawCharts() {
  const list = filtered().filter((s) => s.fc.length);
  const key = el("div", { class: "key" }, swatch("pl", "Giá thật", 1), swatch("ml", "Đường tham khảo", 1), swatch("b50", "Khoảng 50%"), swatch("b80", "Khoảng 80%"));
  const note = D.forecast && D.forecast.best === "rw" ? "Đường nét đứt nằm ngang vì chưa cách nào thắng chắc chắn “giá không đổi”. Hãy dùng khoảng màu xanh." : "Đường nét đứt chỉ để tham khảo.";
  const rows = list.map((s) => row([s.sym, f2(s.price), ...s.fc.map((p) => `${f2(p.lo80)} – ${f2(p.hi80)}`)]));
  $("charts").replaceChildren(el("p", { class: "muted" }, note), key, list.length ? el("div", { class: "grid" }, ...list.map(chart)) : el("p", {}, "Chưa có dự báo."),
    table(["Khoảng 80%", "Giá", "Phiên +1", "Phiên +2", "Phiên +3", "Phiên +4", "Phiên +5"], rows));
}
function drawAcc() {
  const names = { 5: "Ngắn (1 tuần)", 20: "Vừa (1 tháng)", 60: "Dài (3 tháng)" };
  const rows = Object.entries(D.accuracy).map(([h, a]) => { const t = a.test; const skill = t.ic_t >= 1.65;
    return row([names[h] || h, pc(t.beat_top), pc(t.beat_all), pc(t.up_top), pc(t.up_all), `${pc(t.net_yr, 1)} (${pc(t.net_lo, 1)} đến ${pc(t.net_hi, 1)})`,
      skill && t.net_t >= 1.65 ? "Có kỹ năng và có lời sau phí" : skill ? "Kỹ năng nhỏ, chưa chứng minh có lời" : "Không thấy kỹ năng"]); });
  const v = D.live || {}, kids = [el("h2", {}, "Danh sách ổn định, kết quả thật"), el("p", {}, D.steady ? `Số phiên đã lưu: ${D.steady.logged}. Đã chấm sau 20 phiên: ${D.steady.skill.days}. Lưu trễ: ${D.steady.late}. Kỹ năng xếp hạng (IC): ${D.steady.skill.ic == null ? "chưa chấm được phiên nào" : D.steady.skill.ic.toFixed(3) + " (" + tv(D.steady.skill.t) + ")"}.` : "Chưa có."),
    el("p", { class: "muted" }, "Kiểm định quá khứ ở 20 phiên (đến 23/11/2026): IC 0.110 trong 2018–2022 (t = 5.4) và 0.035 trong 2023–2026 (t = 1.5, có thể do may rủi). IC bằng 0 là đoán mò."),
    el("h2", {}, "Xếp hạng hằng ngày (31 mã), kiểm định từ 2023 đến nay"), el("p", { class: "muted" }, `${D.tested ? `Kiểm định lại với giá đến ${D.tested}. ` : ""}Tự kiểm định lại mỗi khi có phiên mới. Số liệu hơi đẹp hơn thực tế: hai đầu vào bị lẫn chút thông tin chia tách, cổ tức về sau.`),
    table(["Kỳ hạn", "Mã đầu bảng thắng mã ở giữa", "Chọn ngẫu nhiên", "Mã đầu bảng tăng giá", "Mọi mã tăng giá", "Mỗi năm so với mua đều, sau phí", "Kết luận"], rows)];
  if (D.forecast) kids.push(el("p", {}, "Dự báo 5 phiên: khoảng 80% chứa giá thật " + Object.entries(D.forecast.cover).map(([h, c]) => `${pc(c)} (phiên +${h})`).join(", ") + " trong 500 phiên gần nhất."));
  kids.push(el("h2", {}, "Xếp hạng hằng ngày, kết quả thật"), el("p", {}, `Đã chấm: ${v.days || 0} phiên. Đang chờ: ${v.pending || 0}. Bỏ vì lưu trễ: ${v.late || 0}.`));
  if (v.days) {
    kids.push(table(["Chỉ số", "Kết quả", "Mức tốt"], [
      row(["Kỹ năng xếp hạng (IC)", `${v.rank_ic.toFixed(3)} (${tv(v.ic_t)})`, "trên 0, t ≥ 1.65"]),
      row(["Mã đầu bảng sau phí so với mua đều, cộng dồn", `${pc(v.net_total, 1)} qua ${v.periods} kỳ (${tv(v.net_t)})`, "trên 0%, t ≥ 1.65"]),
      row(["Khoảng 80% chứa giá thật", pc(v.coverage80), "khoảng 80%"]),
      row(["Chạm chốt lời / chạm cắt lỗ", `${pc(v.hit_target)} / ${pc(v.hit_stop)}`, "khoảng 25% / nhiều nhất 10%"]),
      ...(v.learn_days ? [row(["Học hằng ngày so với bản đóng băng (IC)", `${v.ic_learn.toFixed(3)} so với ${v.ic_frozen.toFixed(3)} (${tv(v.learn_t)})`, "học cao hơn"])] : [])]));
  }
  kids.push(el("p", { class: "muted" }, (v.days || 0) < 60 ? "Còn quá sớm để kết luận, cần ít nhất 60 phiên đã chấm." : "Đã chấm ít nhất 60 phiên."));
  $("acc").replaceChildren(...kids);
}
function draw() { if (!D) return; drawPlan(); drawCheck(); drawRank(); drawCharts(); drawAcc(); }
function go(t) {
  tab = t; for (const b of document.querySelectorAll("nav button")) { b.classList.toggle("on", b.dataset.tab === t); b.setAttribute("aria-selected", b.dataset.tab === t); }
  for (const id of ["plan", "check", "rank", "charts", "acc", "help"]) $(id).hidden = id !== t;
  $("filters").hidden = !["rank", "charts"].includes(t); draw();
}
async function load() {
  const r = await fetch("site.json?t=" + Date.now(), { cache: "no-store" });
  if (!r.ok) throw new Error("không có tệp dữ liệu (" + r.status + ")");
  D = await r.json();
  $("meta").textContent = `Giá đóng cửa đến ${D.asof} · cập nhật ${D.updated} giờ Việt Nam · nghìn đồng` + (D.warnings && D.warnings.length ? ` · ${D.warnings.length} cảnh báo: ${D.warnings.join("; ")}` : "");
  $("verdict").textContent = D.gate ? "Xếp hạng hằng ngày đạt kiểm định lợi nhuận nên tín hiệu Mua có thể hiện. Danh sách ổn định vẫn chỉ trên giấy. Không phải lời khuyên đầu tư."
    : "Tín hiệu Mua đang khoá vì chưa chứng minh có lời sau phí. Hãy dùng để học, đừng giao dịch tiền thật. Không phải lời khuyên đầu tư.";
  const sel = $("sector"), cur = sel.value; sel.replaceChildren(el("option", { value: "" }, "Mọi ngành"), ...[...new Set(D.stocks.map((s) => s.sector))].map((s) => el("option", { value: s }, SECT[s] || s))); sel.value = cur;
  draw();
}
async function api(path, opt = {}) {
  return fetch(`https://api.github.com/repos/${OWNER}/${REPO}/${path}`, { ...opt, cache: "no-store", headers: { Accept: "application/vnd.github+json", Authorization: "Bearer " + store.get() } });
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function update() {
  if (!onPages) return say("Nút này chỉ hoạt động trên trang github.io.");
  if (!store.get()) {
    window.open(`https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}`, "_blank", "noopener");
    return say("GitHub đã mở ở thẻ mới: bấm Run workflow, chờ 5 đến 15 phút rồi tải lại trang này. Muốn chỉ bấm một lần, xem Cài đặt nút.");
  }
  const btn = $("update"); btn.disabled = true;
  try {
    const t0 = Date.now() - 60000, before = D && D.updated;
    const r = await api(`actions/workflows/${WORKFLOW}/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main" }) });
    if (r.status === 401) { store.del(); throw new Error("khoá sai hoặc hết hạn nên đã bị xoá. Hãy thêm khoá mới trong Cài đặt nút."); }
    if (r.status === 403 || r.status === 404) throw new Error("khoá thiếu quyền. Cần Actions: Read and write trên kho này.");
    if (!r.ok) throw new Error("GitHub trả lời " + r.status);
    say("Đã bắt đầu cập nhật, mất khoảng 5 đến 15 phút. Bạn cứ xem tiếp.");
    for (let i = 0; i < 90; i++) {
      await wait(15000);
      const q = await api(`actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=5`); if (!q.ok) continue;
      const run = (await q.json()).workflow_runs.find((x) => Date.parse(x.created_at) >= t0); if (!run) continue;
      if (run.status !== "completed") { say(`Đang cập nhật… (${Math.round((Date.now() - Date.parse(run.created_at)) / 60000)} phút)`); continue; }
      if (run.conclusion !== "success") throw new Error("lần chạy kết thúc với: " + run.conclusion + ". Trang vẫn hiện kết quả cũ.");
      for (let k = 0; k < 12; k++) { await load(); if (D.updated !== before) return say("Xong. Đang hiện kết quả mới."); await wait(10000); }
      return say("Đã chạy xong. Nếu ngày ở trên chưa đổi, hãy tải lại sau vài phút.");
    }
    say("Vẫn đang chạy. Hãy tải lại trang sau.");
  } catch (e) { say("Cập nhật lỗi: " + e.message); } finally { btn.disabled = false; }
}
$("update").addEventListener("click", update);
$("setup").addEventListener("click", () => { $("panel").hidden = !$("panel").hidden; });
$("save").addEventListener("click", () => { const v = $("token").value.trim(); if (!v) return; store.set(v, $("remember").checked); $("token").value = ""; $("panel").hidden = true; say("Đã lưu khoá. Giờ chỉ cần bấm Cập nhật ngay."); });
$("forget").addEventListener("click", () => { store.del(); say("Đã xoá khoá khỏi trình duyệt này."); });
for (const b of document.querySelectorAll("nav button")) b.addEventListener("click", () => { if (b.dataset.tab !== tab) $("q").value = ""; go(b.dataset.tab); });
const fmt = () => { const m = money(); $("money").value = m ? m.toLocaleString("vi-VN") : ""; };
try { $("money").value = localStorage.getItem("vnsa-money") || "10000000"; } catch { $("money").value = "10000000"; }
fmt();
$("money").addEventListener("input", () => { fmt(); try { localStorage.setItem("vnsa-money", String(money())); } catch { } if (D) drawPlan(); });
$("q").addEventListener("input", draw); $("sector").addEventListener("change", draw);
if (onPages) $("repo").href = `https://github.com/${OWNER}/${REPO}`;
load().catch((e) => { $("meta").textContent = "Không tải được kết quả: " + e.message; });
go(["plan", "check", "rank", "charts", "acc", "help"].find((t) => location.hash === "#" + t) || "plan");
