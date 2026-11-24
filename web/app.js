"use strict";
const $ = (id) => document.getElementById(id);
const onPages = location.hostname.endsWith(".github.io");
const OWNER = onPages ? location.hostname.split(".")[0] : "";
const REPO = onPages ? location.pathname.split("/")[1] : "";
const WORKFLOW = "daily.yml", KEY = `vnsa-key-${REPO}`;
const SIG = { "MUA": ["Buy", "up"], "HANG CAO": ["High rank", "up"], "TRUNG LAP": ["Neutral", ""], "HANG THAP": ["Low rank", "down"],
  "RUI RO CAO": ["High risk", "down"], "TAM DUNG": ["Paused", "down"] };
const SECT = { "Ngan hang": "Banks", "Thep": "Steel", "Bat dong san": "Real estate", "Chung khoan": "Brokers", "Cong nghe": "Technology",
  "Tieu dung": "Consumer", "Dau khi": "Oil & gas", "Dien nuoc": "Utilities" };
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
const tv = (v) => v == null ? "not enough data" : "t = " + v.toFixed(1);
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
const list = (a) => a.length ? a.join(", ") : "none";
// Backtest, January 2020 - 23 November 2026, after costs (LONGTERM_REPORT_V2.md): name, per year, worst fall, growth
const PAST = [["All in the E1VFVN30 fund", .121, -.42, 2.20], ["70% fund + 30% cash (4% a year)", .104, -.30, 1.97],
  ["70% fund + 30% short model", .180, -.47, 3.12], ["70% best long model + 30% short model", .145, -.49, 2.54]];
function drawPlan() {
  const m = money(), L = m * .7, S = m - L, s = D.short, out = [];
  if (!s) return $("planout").replaceChildren(el("p", { class: "notice" }, "The 70/30 data is not ready yet. It appears after the next update."));
  const price = s.fund.price * 1000, units = Math.floor(L / price);
  out.push(el("div", { class: "grid" },
    el("div", { class: "card" }, el("h2", {}, "70% long-term"), el("p", { class: "big" }, vnd(L)),
      el("p", {}, `Index fund E1VFVN30, about ${vnd(price)} each (close ${s.fund.date}).`),
      el("p", {}, m ? `That is ${units.toLocaleString("vi-VN")} units for ${vnd(units * price)}, ${vnd(L - units * price)} left over.` : "Type your money above."),
      el("p", { class: "muted" }, "We tested 1,152 long-term settings. Picking the best past one each year did not beat this fund. It can still fall by more than 40%, so many people buy a part each month.")),
    el("div", { class: "card" }, el("h2", {}, "30% short-term"), el("p", { class: "big" }, vnd(S)),
      el("p", {}, el("b", {}, "Keep this in cash for now. "), "The model below is paper only for at least 6 months."),
      el("p", { class: "muted" }, "At the start of each quarter, move money so the split is 70/30 again."))));
  out.push(el("h2", {}, "Paper portfolio of the short-term model"), el("p", { class: "muted" }, `Based on the ${s.asof} close. One trade day every 10 sessions.`));
  const px = Object.fromEntries(s.rows.map((r) => [r.sym, r.price]));
  const line = (sym, w, what) => { const p = px[sym], a = S * w, n = p ? Math.floor(a / (p * 1000)) : null;
    return row([sym, what, p ? f2(p) : "–", pc(w), vnd(a), n == null ? "–" : n.toLocaleString("vi-VN") + (n > 0 && n < 100 ? " (odd lot)" : "")], 2); };
  const head = ["Stock", "Paper action", "Price (thousand VND)", "Part of the 30%", "Amount", "Shares"];
  if (s.pending) {
    const q = s.pending, all = [...q.keep, ...q.buy];
    out.push(el("p", { class: "notice" }, `New paper trade at the next session's close. Buy: ${list(q.buy)}. Sell: ${list(q.sell)}. Keep: ${list(q.keep)}.`),
      table(head, all.map((x) => line(x, 1 / Math.max(6, all.length), q.buy.includes(x) ? "Buy next session" : "Keep")), 2));
  } else if (Object.keys(s.hold).length) {
    out.push(el("p", {}, `${s.next_in} session(s) until the next change.`), table(head, Object.entries(s.hold).sort((a, b) => b[1] - a[1]).map(([x, w]) => line(x, w, "Hold")), 2));
  } else out.push(el("p", {}, "Nothing held yet."));
  if (s.trades.length) out.push(el("h3", {}, "Last paper trades"), table(["Date", "Bought", "Sold"], s.trades.slice().reverse().map((t) => row([t.date, list(t.buy), list(t.sell)], 3)), 3));
  out.push(el("h2", {}, "Live comparison (the only clean test)"));
  if (s.live) {
    const l = s.live, r = (n, v) => row([n, pc(v - 1, 1), vnd(m * v)]);
    out.push(el("p", {}, `Since ${l.start}: ${l.sessions} session(s).` + (l.sessions < 120 ? " Too early to judge: wait for about 120 sessions (6 months)." : "")),
      table(["Plan", "Change", "Your money would be"], [r("All in the fund", l.fund), r("70% fund + 30% cash", l.cash_plan), r("70% fund + 30% short model", l.plan), r("Short model alone", l.model)]));
  } else out.push(el("p", {}, "Starts with the first paper trade."));
  out.push(el("h2", {}, "Past test, January 2020 to November 2026, after costs"),
    table(["Plan", "Per year", "Worst fall", "Your money would have become"], PAST.map(([n, y, d, g]) => row([n, pc(y), pc(d), vnd(m * g)]))),
    el("p", { class: "notice" }, "Don't expect this. Most of the short model's gain came in 2020–2021 and from less-traded stocks. With strict trading limits it made 19% a year in 2023–2026, against 17.6% for the fund, and 13% to 31% depending only on the day it started. It once fell 63%. It failed two of the overfitting checks."));
  $("planout").replaceChildren(...out);
}
function drawRank() {
  const s = D.short; if (!s) return $("rank").replaceChildren(el("p", {}, "The 1-month ranking appears after the next update."));
  const q = $("q").value.trim().toUpperCase(), held = new Set([...Object.keys(s.hold), ...(s.pending ? s.pending.buy : [])]);
  const rows = s.rows.filter((r) => !q || r.sym.includes(q)).map((r) => row([String(r.rank), r.sym, f2(r.price), pc(r.ret20, 1), pc(r.vol), String(r.lq),
    r.floor20 >= 3 ? el("span", { class: "sig down" }, "High risk") : "", held.has(r.sym) ? el("span", { class: "sig up" }, "In paper portfolio") : r.rank <= 18 ? "Top 18" : ""], 2));
  $("rank").replaceChildren(el("p", { class: "notice" }, `Paper only. The model's view of about the next month, from the ${s.asof} close. Neighbouring ranks mean little.`),
    rows.length ? table(["Rank", "Stock", "Price (thousand VND)", "Last 20 sessions", "Yearly volatility", "Most traded no.", "Warning", "Status"], rows, 2) : el("p", { class: "muted" }, "No stock matches."));
}
function drawLevels() {
  const rows = filtered().map((s) => { const [name, cls] = SIG[s.signal] || [s.signal, ""];
    return row([s.sym, SECT[s.sector] || s.sector, f2(s.price), `${f2(s.buy[0])} – ${f2(s.buy[1])}`, f2(s.target), f2(s.stop), s.rsi.toFixed(0), el("span", { class: "sig " + cls }, name)], 2); });
  return [el("h2", {}, "5-day price levels (older model)"), table(["Stock", "Sector", "Price", "Buy zone", "Take profit", "Stop loss", "RSI", "5-day signal"], rows, 2)];
}
function chart(s) {
  const W = 330, H = 190, L = 46, R = 10, T = 10, B = 24, px = s.close, k0 = px.length - 1, n = px.length + s.fc.length;
  const base = px[k0], b = (k) => [base, ...s.fc.map((x) => x[k])], all = [...px, ...b("lo80"), ...b("hi80")];
  let lo = Math.min(...all), hi = Math.max(...all); const pad = (hi - lo) * .06 || 1; lo -= pad; hi += pad;
  const X = (i) => L + i * (W - L - R) / (n - 1), Y = (v) => T + (hi - v) * (H - T - B) / (hi - lo);
  const pts = (a, o = 0) => a.map((v, i) => `${X(i + o).toFixed(1)},${Y(v).toFixed(1)}`);
  const svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${s.sym} last 40 sessions and 5-session forecast` });
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
    const p = s.fc[i - k0 - 1]; tip.textContent = p ? `Day +${i - k0}: ${f2(p.lo80)} – ${f2(p.hi80)} (80%)` : `${dm(s.dates[i])}: ${f2(px[i])}`;
  });
  svg.addEventListener("pointerleave", () => { tip.hidden = true; x.setAttribute("visibility", "hidden"); });
  return el("figure", {}, el("figcaption", {}, s.sym + " ", el("span", {}, f2(s.price))), svg, tip);
}
function swatch(cls, text, line) {
  const g = sv("svg", { viewBox: "0 0 22 10", "aria-hidden": "true" });
  g.append(line ? sv("line", { class: cls, x1: 0, x2: 22, y1: 5, y2: 5 }) : sv("rect", { class: cls, width: 22, height: 10 }));
  return el("span", {}, g, text);
}
function drawCharts() {
  const list = filtered().filter((s) => s.fc.length);
  const key = el("div", { class: "key" }, swatch("pl", "Real price", 1), swatch("ml", "Reference line", 1), swatch("b50", "50% range"), swatch("b80", "80% range"));
  const note = D.forecast && D.forecast.best === "rw" ? "The dashed line is flat because no method reliably beat “price stays the same”. Use the blue ranges." : "The dashed line is a reference, not a promise.";
  const rows = list.map((s) => row([s.sym, f2(s.price), ...s.fc.map((p) => `${f2(p.lo80)} – ${f2(p.hi80)}`)]));
  $("charts").replaceChildren(el("p", { class: "muted" }, note), key, list.length ? el("div", { class: "grid" }, ...list.map(chart)) : el("p", {}, "No forecast available."),
    table(["80% range", "Price", "Day +1", "Day +2", "Day +3", "Day +4", "Day +5"], rows), ...drawLevels());
}
function drawAcc() {
  const names = { 5: "Short (1 week)", 20: "Middle (1 month)", 60: "Long (3 months)" };
  const rows = Object.entries(D.accuracy).map(([h, a]) => { const t = a.test; const skill = t.ic_t >= 1.65;
    return row([names[h] || h, pc(t.beat_top), pc(t.beat_all), pc(t.up_top), pc(t.up_all), `${pc(t.net_yr, 1)} (${pc(t.net_lo, 1)} to ${pc(t.net_hi, 1)})`,
      skill && t.net_t >= 1.65 ? "Skill, and profit after fees" : skill ? "Small skill, profit not proven" : "No skill found"]); });
  const v = D.live || {}, kids = [el("h2", {}, "1-month model, live"), el("p", {}, D.short ? `Saved sessions: ${D.short.logged}. Scored after 20 sessions: ${D.short.skill.days}. Excluded because saved late: ${D.short.late}. Ranking skill (IC): ${D.short.skill.ic == null ? "none scored yet" : D.short.skill.ic.toFixed(3) + " (" + tv(D.short.skill.t) + ")"}.` : "Not ready yet."),
    el("p", { class: "muted" }, "Backtest, retrained every 6 months on the past only: IC 0.076 in 2020–2026 (t = 4.5) and 0.046 in 2023–2026 (t = 2.3). IC 0 is guessing. Judge it after 60 scored sessions."),
    el("h2", {}, "Older 5-day ranking of 31 stocks, tested on 2023 onwards"),
    table(["Time frame", "Top picks beat middle stock", "Random picks", "Top picks that rose", "All stocks that rose", "Yearly return vs equal holding, after fees", "Verdict"], rows)];
  if (D.forecast) kids.push(el("p", {}, "5-day forecast: the 80% range held the real price " + Object.entries(D.forecast.cover).map(([h, c]) => `${pc(c)} (day +${h})`).join(", ") + " over the last 500 sessions."));
  kids.push(el("h2", {}, "Older ranking, live results"), el("p", {}, `Scored sessions: ${v.days || 0}. Waiting: ${v.pending || 0}. Excluded because saved late: ${v.late || 0}.`));
  if (v.days) {
    kids.push(table(["Measure", "Result", "Good result"], [
      row(["Ranking skill (IC)", `${v.rank_ic.toFixed(3)} (${tv(v.ic_t)})`, "above 0, t ≥ 1.65"]),
      row(["Top picks after fees, total", `${pc(v.net_total, 1)} over ${v.periods} periods (${tv(v.net_t)})`, "above 0%, t ≥ 1.65"]),
      row(["80% range held the price", pc(v.coverage80), "about 80%"]),
      row(["Take profit reached / stop reached", `${pc(v.hit_target)} / ${pc(v.hit_stop)}`, "about 25% / at most 10%"]),
      ...(v.learn_days ? [row(["Daily learning vs frozen copy (IC)", `${v.ic_learn.toFixed(3)} vs ${v.ic_frozen.toFixed(3)} (${tv(v.learn_t)})`, "learning higher"])] : [])]));
  }
  kids.push(el("p", { class: "muted" }, (v.days || 0) < 60 ? "Too early to judge: wait for at least 60 scored sessions." : "At least 60 sessions scored."));
  $("acc").replaceChildren(...kids);
}
function draw() { if (!D) return; drawPlan(); drawRank(); drawCharts(); drawAcc(); }
function go(t) {
  tab = t; for (const b of document.querySelectorAll("nav button")) { b.classList.toggle("on", b.dataset.tab === t); b.setAttribute("aria-selected", b.dataset.tab === t); }
  for (const id of ["plan", "rank", "charts", "acc", "help"]) $(id).hidden = id !== t;
  $("filters").hidden = !["rank", "charts"].includes(t); $("sector").hidden = t !== "charts"; draw();
}
async function load() {
  const r = await fetch("site.json?t=" + Date.now(), { cache: "no-store" });
  if (!r.ok) throw new Error("no data file (" + r.status + ")");
  D = await r.json();
  $("meta").textContent = `Prices to ${D.asof} close · updated ${D.updated} Vietnam time · thousands of VND`;
  $("verdict").textContent = D.gate ? "The older 5-day ranking passed the profit test, so its Buy signals can appear. The 1-month model is paper only. Not investment advice."
    : "Paper only: profit after fees is not proven for either ranking. Use them to learn, not to trade real money. Not investment advice.";
  const sel = $("sector"), cur = sel.value; sel.replaceChildren(el("option", { value: "" }, "All sectors"), ...[...new Set(D.stocks.map((s) => s.sector))].map((s) => el("option", { value: s }, SECT[s] || s))); sel.value = cur;
  draw();
}
async function api(path, opt = {}) {
  return fetch(`https://api.github.com/repos/${OWNER}/${REPO}/${path}`, { ...opt, cache: "no-store", headers: { Accept: "application/vnd.github+json", Authorization: "Bearer " + store.get() } });
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function update() {
  if (!onPages) return say("This button works on the github.io page.");
  if (!store.get()) {
    window.open(`https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW}`, "_blank", "noopener");
    return say("GitHub opened in a new tab: press Run workflow there, wait 3 to 10 minutes, then reload this page. For one click, see Button settings.");
  }
  const btn = $("update"); btn.disabled = true;
  try {
    const t0 = Date.now() - 60000, before = D && D.updated;
    const r = await api(`actions/workflows/${WORKFLOW}/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main" }) });
    if (r.status === 401) { store.del(); throw new Error("the key is wrong or expired and was removed. Add a new one in Button settings."); }
    if (r.status === 403 || r.status === 404) throw new Error("the key lacks permission. It needs Actions: Read and write on this repository.");
    if (!r.ok) throw new Error("GitHub answered " + r.status);
    say("Update started. This takes about 3 to 10 minutes; you can keep reading.");
    for (let i = 0; i < 90; i++) {
      await wait(15000);
      const q = await api(`actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=5`); if (!q.ok) continue;
      const run = (await q.json()).workflow_runs.find((x) => Date.parse(x.created_at) >= t0); if (!run) continue;
      if (run.status !== "completed") { say(`Updating… (${Math.round((Date.now() - Date.parse(run.created_at)) / 60000)} min)`); continue; }
      if (run.conclusion !== "success") throw new Error("the run ended with: " + run.conclusion + ". Old results are still shown.");
      for (let k = 0; k < 12; k++) { await load(); if (D.updated !== before) return say("Done. Showing new results."); await wait(10000); }
      return say("The run finished. Reload in a few minutes if the date above has not changed.");
    }
    say("Still running. Reload this page later.");
  } catch (e) { say("Update failed: " + e.message); } finally { btn.disabled = false; }
}
$("update").addEventListener("click", update);
$("setup").addEventListener("click", () => { $("panel").hidden = !$("panel").hidden; });
$("save").addEventListener("click", () => { const v = $("token").value.trim(); if (!v) return; store.set(v, $("remember").checked); $("token").value = ""; $("panel").hidden = true; say("Key saved. Update now works with one click."); });
$("forget").addEventListener("click", () => { store.del(); say("Key removed from this browser."); });
for (const b of document.querySelectorAll("nav button")) b.addEventListener("click", () => { if (b.dataset.tab !== tab) $("q").value = ""; go(b.dataset.tab); });
const fmt = () => { const m = money(); $("money").value = m ? m.toLocaleString("vi-VN") : ""; };
try { $("money").value = localStorage.getItem("vnsa-money") || "10000000"; } catch { $("money").value = "10000000"; }
fmt();
$("money").addEventListener("input", () => { fmt(); try { localStorage.setItem("vnsa-money", String(money())); } catch { } if (D) drawPlan(); });
$("q").addEventListener("input", draw); $("sector").addEventListener("change", draw);
if (onPages) $("repo").href = `https://github.com/${OWNER}/${REPO}`;
load().catch((e) => { $("meta").textContent = "Could not load results: " + e.message; });
go(["plan", "rank", "charts", "acc", "help"].find((t) => location.hash === "#" + t) || "plan");
