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
let D = null, tab = "rank";

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
function showStock(sym) { $("q").value = sym; go("charts"); }
function drawRank() {
  const rows = filtered().map((s) => {
    const [name, cls] = SIG[s.signal] || [s.signal, ""], last = s.fc[s.fc.length - 1];
    const tr = row([String(s.rank), el("button", { class: "link", "aria-label": `Chart for ${s.sym}` }, s.sym), SECT[s.sector] || s.sector, f2(s.price),
      last ? `${f2(last.lo80)} – ${f2(last.hi80)}` : "–", `${f2(s.buy[0])} – ${f2(s.buy[1])}`, f2(s.target), f2(s.stop), s.rsi.toFixed(0),
      el("span", { class: "sig " + cls }, name)], 3);
    tr.classList.add("click"); tr.addEventListener("click", () => showStock(s.sym)); return tr;
  });
  $("rank").replaceChildren(rows.length ? table(["Rank", "Stock", "Sector", "Price", "80% range, day 5", "Buy zone", "Take profit", "Stop loss", "RSI", "Signal"], rows, 3)
    : el("p", { class: "muted" }, "No stock matches."));
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
  return el("figure", {}, el("figcaption", {}, s.sym + " ", el("span", {}, `rank ${s.rank} · ${f2(s.price)}`)), svg, tip);
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
    table(["80% range", "Price", "Day +1", "Day +2", "Day +3", "Day +4", "Day +5"], rows));
}
function drawAcc() {
  const names = { 5: "Short (1 week)", 20: "Middle (1 month)", 60: "Long (3 months)" };
  const rows = Object.entries(D.accuracy).map(([h, a]) => { const t = a.test; const skill = t.ic_t >= 1.65;
    return row([names[h] || h, pc(t.beat_top), pc(t.beat_all), pc(t.up_top), pc(t.up_all), `${pc(t.net_yr, 1)} (${pc(t.net_lo, 1)} to ${pc(t.net_hi, 1)})`,
      skill && t.net_t >= 1.65 ? "Skill, and profit after fees" : skill ? "Small skill, profit not proven" : "No skill found"]); });
  const v = D.live || {}, kids = [el("h2", {}, "Tested on 2023 onwards"),
    table(["Time frame", "Top picks beat middle stock", "Random picks", "Top picks that rose", "All stocks that rose", "Yearly return vs equal holding, after fees", "Verdict"], rows)];
  if (D.forecast) kids.push(el("p", {}, "5-day forecast: the 80% range held the real price " + Object.entries(D.forecast.cover).map(([h, c]) => `${pc(c)} (day +${h})`).join(", ") + " over the last 500 sessions."));
  kids.push(el("h2", {}, "Live results"), el("p", {}, `Scored sessions: ${v.days || 0}. Waiting: ${v.pending || 0}. Excluded because saved late: ${v.late || 0}.`));
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
function draw() { if (!D) return; drawRank(); drawCharts(); drawAcc(); }
function go(t) {
  tab = t; for (const b of document.querySelectorAll("nav button")) { b.classList.toggle("on", b.dataset.tab === t); b.setAttribute("aria-selected", b.dataset.tab === t); }
  for (const id of ["rank", "charts", "acc", "help"]) $(id).hidden = id !== t;
  $("filters").hidden = t === "acc" || t === "help"; draw();
}
async function load() {
  const r = await fetch("site.json?t=" + Date.now(), { cache: "no-store" });
  if (!r.ok) throw new Error("no data file (" + r.status + ")");
  D = await r.json();
  $("meta").textContent = `Prices to ${D.asof} close · updated ${D.updated} Vietnam time · thousands of VND`;
  $("verdict").textContent = D.gate ? "The backtest passed the profit test, so Buy signals can appear. Not investment advice."
    : "Buy signals are locked: profit after fees is not proven. Use the ranking to learn, not to trade real money. Not investment advice.";
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
$("q").addEventListener("input", draw); $("sector").addEventListener("change", draw);
if (onPages) $("repo").href = `https://github.com/${OWNER}/${REPO}`;
load().catch((e) => { $("meta").textContent = "Could not load results: " + e.message; });
go(["rank", "charts", "acc", "help"].find((t) => location.hash === "#" + t) || "rank");
