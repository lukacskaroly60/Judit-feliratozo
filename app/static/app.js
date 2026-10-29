"use strict";

// ---------- segédfüggvények ----------

const $ = (sel) => document.querySelector(sel);
const FPS = 25;

function fmt(t) {
  t = Math.max(0, t || 0);
  let ms = Math.round(t * 1000);
  const h = Math.floor(ms / 3600000); ms -= h * 3600000;
  const m = Math.floor(ms / 60000); ms -= m * 60000;
  const s = Math.floor(ms / 1000); ms -= s * 1000;
  const p = (n, w = 2) => String(n).padStart(w, "0");
  return `${p(h)}:${p(m)}:${p(s)},${p(ms, 3)}`;
}

// Elfogad: 00:01:02,500 | 01:02.5 | 62.5 | 00:01:02:12 (képkocka, 25 fps)
function parseTime(str) {
  str = str.trim();
  let m = str.match(/^(\d+):(\d{1,2}):(\d{1,2}):(\d{1,2})$/);
  if (m) return +m[1] * 3600 + +m[2] * 60 + +m[3] + +m[4] / FPS;
  m = str.match(/^(?:(\d+):)?(?:(\d{1,2}):)?(\d{1,2})(?:[,.](\d{1,3}))?$/);
  if (!m) return null;
  const parts = [m[1], m[2]].filter((x) => x !== undefined).map(Number);
  const h = parts.length === 2 ? parts[0] : 0;
  const mi = parts.length === 2 ? parts[1] : parts.length === 1 ? parts[0] : 0;
  return h * 3600 + mi * 60 + +m[3] + (m[4] ? +m[4].padEnd(3, "0") / 1000 : 0);
}

const WEAK = new Set("a az egy és s de hogy ha vagy mert mint is sem nem meg ami aki amely amit akkor pedig".split(" "));
function breakPenalty(word) {
  if (/[.?!…]$/.test(word)) return -12;
  if (/[,;:–-]$/.test(word)) return -8;
  if (WEAK.has(word.toLowerCase().replace(/["'„”]/g, ""))) return 10;
  return 0;
}

// Kiegyensúlyozott sortörés (ugyanaz a logika, mint a szerveren)
function wrap(text, maxChars, maxLines) {
  text = text.split(/\s+/).filter(Boolean).join(" ");
  if (text.length <= maxChars || maxLines < 2) return [text];
  const words = text.split(" ");
  let best = null, bestScore = Infinity;
  for (let i = 1; i < words.length; i++) {
    const first = words.slice(0, i).join(" ");
    const rest = words.slice(i).join(" ");
    if (first.length > maxChars) break;
    const tail = rest.length <= maxChars ? [rest] : wrap(rest, maxChars, maxLines - 1);
    if (tail.some((l) => l.length > maxChars)) continue;
    const score = Math.abs(first.length - tail[0].length) + breakPenalty(words[i - 1]);
    if (score < bestScore) { best = [first, ...tail]; bestScore = score; }
  }
  if (best) return best;
  // Nem fér el: legalább két egyforma sorra törjük, a hibajelzés figyelmeztet a rövidítésre
  let cut = 1;
  for (let i = 1; i < words.length; i++) {
    const d = (k) => Math.abs(words.slice(0, k).join(" ").length - words.slice(k).join(" ").length);
    if (d(i) < d(cut)) cut = i;
  }
  return words.length > 1 ? [words.slice(0, cut).join(" "), words.slice(cut).join(" ")] : [text];
}

function toast(msg, ms = 2500) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.add("hidden"), ms);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}
const jsonBody = (data, method = "POST") => ({
  method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
});

// ---------- állapot ----------

const state = {
  project: null,
  cues: [],
  selected: -1,
  active: -1,
  rows: [],
  undo: [],
  rules: { maxChars: 37, maxLines: 2, maxCps: 15 },
  dirty: false,
  saveTimer: null,
  pollTimer: null,
};
const video = $("#video");

// ---------- kezdőképernyő ----------

async function showStart() {
  stopPolling();
  state.project = null;
  video.removeAttribute("src");
  video.load();
  $("#startView").classList.remove("hidden");
  $("#editorView").classList.add("hidden");
  $("#projectName").textContent = "";
  $("#saveState").textContent = "";
  $("#jobBar").classList.add("hidden");
  const list = $("#projectList");
  list.innerHTML = "";
  const projects = await api("/api/projects");
  if (!projects.length) list.innerHTML = "<li class='meta'>Még nincs korábbi munka.</li>";
  for (const p of projects) {
    const li = document.createElement("li");
    const date = new Date(p.updated * 1000).toLocaleString("hu-HU");
    li.innerHTML = `<a href="#p=${p.id}"></a><span class="meta">${p.cues} felirat · ${date}${p.has_output ? " · ✅ kész videó" : ""}</span><button title="Törlés">🗑</button>`;
    li.querySelector("a").textContent = p.name;
    li.querySelector("button").onclick = async () => {
      if (!confirm(`Biztosan törlöd? (${p.name})`)) return;
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      showStart();
    };
    list.appendChild(li);
  }
}

function upload(file) {
  const bar = $("#uploadProgress");
  bar.classList.remove("hidden");
  const fd = new FormData();
  fd.append("file", file);
  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/projects");
  xhr.upload.onprogress = (e) => { bar.firstElementChild.style.width = `${(e.loaded / e.total) * 100}%`; };
  xhr.onload = () => {
    bar.classList.add("hidden");
    if (xhr.status !== 200) return toast("Hiba a feltöltésnél: " + xhr.responseText);
    location.hash = "p=" + JSON.parse(xhr.responseText).id;
  };
  xhr.onerror = () => { bar.classList.add("hidden"); toast("Hiba a feltöltésnél"); };
  xhr.send(fd);
}

const drop = $("#drop");
$("#fileInput").onchange = (e) => e.target.files[0] && upload(e.target.files[0]);
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
drop.ondragleave = () => drop.classList.remove("over");
drop.ondrop = (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]);
};

// ---------- szerkesztő megnyitása ----------

async function openProject(id) {
  const p = await api(`/api/projects/${id}`);
  state.project = p;
  state.cues = p.cues;
  state.undo = [];
  state.selected = -1;
  state.active = -1;
  const s = p.settings || {};
  state.rules = { maxChars: s.max_chars || 37, maxLines: s.max_lines || 2, maxCps: s.max_cps || 15 };
  $("#startView").classList.add("hidden");
  $("#editorView").classList.remove("hidden");
  $("#projectName").textContent = p.name;
  $("#saveState").textContent = "";
  document.title = `${p.name} – Judit feliratozó`;
  video.src = `/api/projects/${id}/video`;
  $("#btnExport").href = `/api/projects/${id}/export.srt`;
  $("#btnDownload").href = `/api/projects/${id}/output`;
  $("#btnDownload").classList.toggle("hidden", !p.has_output);
  renderList();
  showJob(p.job);
  if (p.job && p.job.state === "running") startPolling();
}

function route() {
  const m = location.hash.match(/p=([0-9a-f]{12})/);
  if (m) openProject(m[1]).catch((e) => { toast(e.message); location.hash = ""; });
  else showStart();
}
window.addEventListener("hashchange", async () => { await flushSave(); route(); });
$("#home").onclick = (e) => { e.preventDefault(); location.hash = ""; };

// ---------- feliratlista ----------

function problems(i) {
  const c = state.cues[i], next = state.cues[i + 1], r = state.rules;
  const out = [];
  const lines = c.text.split("\n");
  const dur = c.end - c.start;
  if (!c.text.trim()) out.push("üres");
  const longest = Math.max(...lines.map((l) => l.length));
  if (longest > r.maxChars) out.push(`túl hosszú sor (${longest} kar.)`);
  if (lines.length > r.maxLines) out.push(`túl sok sor (${lines.length})`);
  if (dur <= 0) out.push("a vége a kezdete előtt van");
  else if (dur < 0.7) out.push("túl rövid ideig látszik");
  if (next && c.end > next.start) out.push("átfedés a következővel");
  return out;
}

function cps(c) {
  const dur = c.end - c.start;
  return dur > 0 ? c.text.replace(/\n/g, "").length / dur : 0;
}

function renderList() {
  const list = $("#cueList");
  list.innerHTML = "";
  state.rows = state.cues.map((c, i) => {
    const row = document.createElement("div");
    row.className = "cue";
    row.innerHTML = `
      <div class="cue-meta">
        <span class="num" title="Ugrás ide"></span>
        <input class="tc in" title="Kezdet (Alt+I)">
        <span>→</span>
        <input class="tc out" title="Vége (Alt+O)">
        <span class="dur"></span>
        <span class="cps"></span>
      </div>
      <textarea rows="2" spellcheck="true" lang="hu"></textarea>
      <div class="problems"></div>`;
    const ta = row.querySelector("textarea");
    ta.value = c.text;
    ta.addEventListener("focus", () => { select(row._i, false); ta._undoPushed = false; });
    ta.addEventListener("input", () => {
      if (!ta._undoPushed) { pushUndo(); ta._undoPushed = true; }
      state.cues[row._i].text = ta.value;
      updateRow(row._i);
      updateCounts();
      if (row._i === state.active) setOverlay(ta.value);
      scheduleSave();
    });
    for (const cls of ["in", "out"]) {
      const inp = row.querySelector(`.${cls}`);
      inp.addEventListener("focus", () => select(row._i, false));
      inp.addEventListener("change", () => {
        const t = parseTime(inp.value);
        const cue = state.cues[row._i];
        if (t === null) { inp.value = fmt(cls === "in" ? cue.start : cue.end); return toast("Hibás időformátum"); }
        pushUndo();
        cue[cls === "in" ? "start" : "end"] = t;
        afterTimeChange(row._i);
      });
      inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
    }
    row.querySelector(".num").onclick = () => { select(row._i); video.currentTime = state.cues[row._i].start; };
    row.addEventListener("mousedown", () => select(row._i, false));
    list.appendChild(row);
    return row;
  });
  state.rows.forEach((_, i) => updateRow(i));
  $("#emptyHint").classList.toggle("hidden", state.cues.length > 0);
  updateCounts();
  if (state.selected >= state.cues.length) state.selected = state.cues.length - 1;
  highlight();
}

function updateRow(i) {
  const row = state.rows[i];
  if (!row) return;
  const c = state.cues[i];
  row._i = i;
  row.querySelector(".num").textContent = i + 1;
  const inEl = row.querySelector(".in"), outEl = row.querySelector(".out");
  if (document.activeElement !== inEl) inEl.value = fmt(c.start);
  if (document.activeElement !== outEl) outEl.value = fmt(c.end);
  row.querySelector(".dur").textContent = (c.end - c.start).toFixed(1) + " mp";
  const speed = cps(c);
  const cpsEl = row.querySelector(".cps");
  cpsEl.textContent = `${Math.round(speed)} kar/mp`;
  cpsEl.classList.toggle("err", speed > state.rules.maxCps + 0.5);
  cpsEl.title = speed > state.rules.maxCps ? "Túl gyors – nehéz elolvasni" : "Olvasási sebesség";
  const probs = problems(i);
  row.querySelector(".problems").textContent = probs.join(" · ");
  row.querySelector("textarea").classList.toggle("err", probs.length > 0);
  row.classList.toggle("bad", probs.length > 0);
}

function updateCounts() {
  $("#cueCount").textContent = `${state.cues.length} felirat`;
  const bad = state.cues.filter((_, i) => problems(i).length).length;
  $("#issueCount").textContent = bad ? `⚠ ${bad} hibás` : "";
}

function afterTimeChange(i) {
  const c = state.cues[i];
  // Ha az időrend megváltozott, újrarendezünk
  const sorted = state.cues.every((x, k) => k === 0 || state.cues[k - 1].start <= x.start);
  if (!sorted) {
    state.cues.sort((a, b) => a.start - b.start);
    state.selected = state.cues.indexOf(c);
    renderList();
  } else {
    for (const k of [i - 1, i, i + 1]) updateRow(k);
    updateCounts();
  }
  scheduleSave();
}

function select(i, scroll = true) {
  if (i < 0 || i >= state.cues.length) return;
  state.selected = i;
  highlight();
  if (scroll) state.rows[i].scrollIntoView({ block: "center", behavior: "smooth" });
}

function highlight() {
  state.rows.forEach((row, i) => {
    row.classList.toggle("selected", i === state.selected);
    row.classList.toggle("active", i === state.active);
  });
}

function currentIndex() {
  const row = document.activeElement?.closest?.(".cue");
  if (row && row._i !== undefined) return row._i;
  if (state.selected >= 0) return state.selected;
  return state.active;
}

// ---------- videó és felirat-előnézet ----------

function findActive(t) {
  let lo = 0, hi = state.cues.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (state.cues[mid].start <= t) { found = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return found >= 0 && t < state.cues[found].end ? found : -1;
}

function setOverlay(text) { $("#overlay").textContent = text; }

function tick() {
  if (state.project) {
    const t = video.currentTime;
    $("#timeDisplay").textContent = fmt(t);
    const a = findActive(t);
    if (a !== state.active) {
      state.active = a;
      setOverlay(a >= 0 ? state.cues[a].text : "");
      highlight();
      const editing = $("#cueList").contains(document.activeElement);
      if (a >= 0 && !video.paused && $("#follow").checked && !editing) {
        state.rows[a].scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }
    if (state.playUntil && t >= state.playUntil) { video.pause(); state.playUntil = null; }
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

function togglePlay() { state.playUntil = null; video.paused ? video.play() : video.pause(); }
video.onplay = () => ($("#playBtn").textContent = "⏸ Szünet");
video.onpause = () => ($("#playBtn").textContent = "▶ Lejátszás");
video.onclick = togglePlay;
$("#speed").onchange = (e) => (video.playbackRate = +e.target.value);
const seek = (d) => (video.currentTime = Math.max(0, video.currentTime + d));
document.querySelectorAll("[data-act]").forEach((b) => {
  b.onclick = () => ({ back1: () => seek(-1), fwd1: () => seek(1), play: togglePlay })[b.dataset.act]();
});

// ---------- szerkesztési műveletek ----------

function pushUndo() {
  state.undo.push(JSON.stringify(state.cues));
  if (state.undo.length > 200) state.undo.shift();
}

function undo() {
  if (!state.undo.length) return toast("Nincs mit visszavonni");
  state.cues = JSON.parse(state.undo.pop());
  renderList();
  scheduleSave();
  toast("Visszavonva");
}

function focusText(i, pos) {
  const ta = state.rows[i]?.querySelector("textarea");
  if (!ta) return;
  ta.focus();
  if (pos !== undefined) ta.setSelectionRange(pos, pos);
}

function setIn() {
  const i = currentIndex(); if (i < 0) return;
  pushUndo();
  state.cues[i].start = +video.currentTime.toFixed(3);
  afterTimeChange(i);
}

function setOut() {
  const i = currentIndex(); if (i < 0) return;
  pushUndo();
  state.cues[i].end = +video.currentTime.toFixed(3);
  afterTimeChange(i);
}

function newCue() {
  const t = video.currentTime;
  let idx = state.cues.findIndex((c) => c.start > t);
  if (idx < 0) idx = state.cues.length;
  const nextStart = state.cues[idx]?.start ?? Infinity;
  const end = Math.min(t + 2, nextStart - 0.08);
  if (end - t < 0.3) return toast("Itt nincs hely új feliratnak");
  pushUndo();
  state.cues.splice(idx, 0, { start: +t.toFixed(3), end: +end.toFixed(3), text: "" });
  state.selected = idx;
  renderList();
  focusText(idx);
  scheduleSave();
}

function splitCue() {
  const i = currentIndex(); if (i < 0) return;
  const c = state.cues[i];
  const ta = state.rows[i].querySelector("textarea");
  const flat = c.text;
  let pos = document.activeElement === ta ? ta.selectionStart : -1;
  if (pos <= 0 || pos >= flat.length) {
    // nincs kurzor: a középhez legközelebbi szóköznél vágunk
    const mid = flat.length / 2;
    pos = -1;
    for (let k = 0; k < flat.length; k++) if (/\s/.test(flat[k]) && (pos < 0 || Math.abs(k - mid) < Math.abs(pos - mid))) pos = k;
    if (pos < 0) return toast("Ezt nem lehet kettévágni");
  }
  const a = flat.slice(0, pos).replace(/\s+/g, " ").trim();
  const b = flat.slice(pos).replace(/\s+/g, " ").trim();
  const t = video.currentTime;
  const cut = t > c.start + 0.3 && t < c.end - 0.3
    ? t
    : c.start + (c.end - c.start) * (a.length / Math.max(1, a.length + b.length));
  pushUndo();
  const r = state.rules;
  state.cues.splice(i, 1,
    { start: c.start, end: +(cut - 0.04).toFixed(3), text: wrap(a, r.maxChars, r.maxLines).join("\n") },
    { start: +(cut + 0.04).toFixed(3), end: c.end, text: wrap(b, r.maxChars, r.maxLines).join("\n") });
  state.selected = i + 1;
  renderList();
  focusText(i + 1, 0);
  scheduleSave();
}

function mergeNext() {
  const i = currentIndex();
  if (i < 0 || i >= state.cues.length - 1) return;
  pushUndo();
  const a = state.cues[i], b = state.cues[i + 1];
  const text = `${a.text} ${b.text}`.replace(/\s+/g, " ").trim();
  state.cues.splice(i, 2, { start: a.start, end: b.end, text: wrap(text, state.rules.maxChars, state.rules.maxLines).join("\n") });
  state.selected = i;
  renderList();
  focusText(i);
  scheduleSave();
}

function deleteCue() {
  const i = currentIndex(); if (i < 0) return;
  pushUndo();
  state.cues.splice(i, 1);
  state.selected = Math.min(i, state.cues.length - 1);
  renderList();
  scheduleSave();
}

function rewrap() {
  const i = currentIndex(); if (i < 0) return;
  pushUndo();
  const c = state.cues[i];
  c.text = wrap(c.text, state.rules.maxChars, state.rules.maxLines).join("\n");
  state.rows[i].querySelector("textarea").value = c.text;
  updateRow(i);
  if (i === state.active) setOverlay(c.text);
  updateCounts();
  scheduleSave();
}

function step(dir) {
  if (!state.cues.length) return;
  let i = currentIndex();
  if (i < 0) {
    const t = video.currentTime;
    i = dir > 0 ? state.cues.findIndex((c) => c.start > t) : state.cues.findLastIndex((c) => c.start < t);
    if (i < 0) return;
  } else {
    i = Math.max(0, Math.min(state.cues.length - 1, i + dir));
  }
  select(i);
  video.currentTime = state.cues[i].start;
  if (document.activeElement?.tagName === "TEXTAREA") focusText(i);
}

function playSelected() {
  const i = currentIndex(); if (i < 0) return;
  video.currentTime = state.cues[i].start;
  state.playUntil = state.cues[i].end;
  video.play();
}

document.addEventListener("keydown", (e) => {
  if (!state.project || document.querySelector("dialog[open]")) return;
  const typing = /^(TEXTAREA|INPUT|SELECT)$/.test(document.activeElement?.tagName);
  if (e.ctrlKey && e.code === "Space") { e.preventDefault(); return togglePlay(); }
  if (!typing && e.code === "Space") { e.preventDefault(); return togglePlay(); }
  if (!typing && e.ctrlKey && e.code === "KeyZ") { e.preventDefault(); return undo(); }
  if (!e.altKey || e.ctrlKey) return;
  const actions = {
    ArrowLeft: () => seek(e.shiftKey ? -0.1 : -1),
    ArrowRight: () => seek(e.shiftKey ? 0.1 : 1),
    ArrowUp: () => step(-1),
    ArrowDown: () => step(1),
    KeyI: setIn,
    KeyO: setOut,
    KeyP: playSelected,
    KeyN: newCue,
    KeyS: splitCue,
    KeyM: mergeNext,
    KeyW: rewrap,
    KeyZ: undo,
    Delete: deleteCue,
    Backspace: deleteCue,
  };
  const fn = actions[e.code];
  if (fn) { e.preventDefault(); fn(); }
});

// ---------- mentés ----------

function scheduleSave() {
  state.dirty = true;
  $("#saveState").textContent = "Mentés…";
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(flushSave, 800);
}

async function flushSave() {
  clearTimeout(state.saveTimer);
  if (!state.dirty || !state.project) return;
  state.dirty = false;
  try {
    await api(`/api/projects/${state.project.id}/cues`, jsonBody({ cues: state.cues }, "PUT"));
    $("#saveState").textContent = "✓ Mentve";
  } catch (e) {
    state.dirty = true;
    $("#saveState").textContent = "⚠ Nem sikerült menteni";
    toast("Mentési hiba: " + e.message);
  }
}
window.addEventListener("beforeunload", (e) => { if (state.dirty) { flushSave(); e.preventDefault(); } });

// ---------- háttérfeladatok ----------

function showJob(job) {
  const bar = $("#jobBar");
  if (!job || job.state === "idle" || job.state === "done") { bar.classList.add("hidden"); return; }
  bar.classList.remove("hidden");
  bar.classList.toggle("error", job.state === "error");
  $("#jobMsg").textContent = job.state === "error" ? "Hiba: " + job.message : job.message;
  $("#jobProgress").style.width = `${Math.round(job.progress * 100)}%`;
  $("#jobProgress").parentElement.classList.toggle("hidden", job.state === "error");
}

function setBusy(busy) {
  for (const id of ["#btnTranscribe", "#btnRender", "#btnImport", "#btnRetime"]) $(id).disabled = busy;
}

function startPolling() {
  stopPolling();
  setBusy(true);
  const id = state.project.id;
  state.pollTimer = setInterval(async () => {
    let job;
    try { job = await api(`/api/projects/${id}/job`); } catch { return; }
    if (!state.project || state.project.id !== id) return stopPolling();
    showJob(job);
    if (job.state === "running") return;
    stopPolling();
    if (job.state === "done" && job.kind === "transcribe") {
      const p = await api(`/api/projects/${id}`);
      state.cues = p.cues;
      state.project.settings = p.settings;
      state.undo = [];
      renderList();
      toast(`Kész! ${p.cues.length} felirat készült. Nézd át és javítsd, ahol kell.`, 5000);
    } else if (job.state === "done" && job.kind === "render") {
      $("#btnDownload").classList.remove("hidden");
      toast("A feliratos videó elkészült!", 5000);
    }
  }, 1000);
}

function stopPolling() {
  clearInterval(state.pollTimer);
  state.pollTimer = null;
  setBusy(false);
}

// ---------- gombok, párbeszédablakok ----------

function ask(dialog) {
  return new Promise((resolve) => {
    dialog.returnValue = "";
    dialog.showModal();
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok" ? new FormData(dialog.querySelector("form")) : null), { once: true });
  });
}

$("#btnTranscribe").onclick = async () => {
  const dlg = $("#dlgTranscribe");
  const form = dlg.querySelector("form");
  form.max_chars.value = state.rules.maxChars;
  form.max_lines.value = state.rules.maxLines;
  form.max_cps.value = state.rules.maxCps;
  if (state.project.settings?.prompt) form.prompt.value = state.project.settings.prompt;
  $("#overwriteWarn").classList.toggle("hidden", !state.cues.length);
  const fd = await ask(dlg);
  if (!fd) return;
  const body = {
    model: fd.get("model"), language: "hu", prompt: fd.get("prompt"),
    max_chars: +fd.get("max_chars"), max_lines: +fd.get("max_lines"), max_cps: +fd.get("max_cps"),
  };
  state.rules = { maxChars: body.max_chars, maxLines: body.max_lines, maxCps: body.max_cps };
  await flushSave();
  try {
    await api(`/api/projects/${state.project.id}/transcribe`, jsonBody(body));
    showJob({ state: "running", progress: 0, message: "Indítás…" });
    startPolling();
  } catch (e) { toast(e.message); }
};

$("#btnRender").onclick = async () => {
  if (!state.cues.length) return toast("Még nincs felirat");
  const bad = state.cues.filter((_, i) => problems(i).length).length;
  if (bad && !confirm(`${bad} feliratnál hibát találtam (pirossal jelölve). Így is elkészítsem a videót?`)) return;
  const fd = await ask($("#dlgRender"));
  if (!fd) return;
  await flushSave();
  try {
    await api(`/api/projects/${state.project.id}/render`,
      jsonBody({ mode: fd.get("mode"), font_size: fd.get("font_size"), box: fd.get("box") === "1" }));
    $("#btnDownload").classList.add("hidden");
    showJob({ state: "running", progress: 0, message: "Videó készítése…" });
    startPolling();
  } catch (e) { toast(e.message); }
};

$("#btnExport").onclick = async (e) => {
  if (state.dirty) {
    e.preventDefault();
    await flushSave();
    location.href = $("#btnExport").href;
  }
};

$("#btnImport").onclick = () => {
  if (state.cues.length && !confirm("A jelenlegi feliratok felülíródnak. Folytatod?")) return;
  $("#srtInput").click();
};
$("#srtInput").onchange = async (e) => {
  const file = e.target.files[0];
  e.target.value = "";
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const p = await api(`/api/projects/${state.project.id}/import-srt`, { method: "POST", body: fd });
    pushUndo();
    state.cues = p.cues;
    renderList();
    toast(`${p.cues.length} felirat betöltve`);
  } catch (err) { toast("Hiba: " + err.message); }
};

$("#btnRetime").onclick = async () => {
  await flushSave();
  pushUndo();
  const p = await api(`/api/projects/${state.project.id}/retime`, { method: "POST" });
  state.cues = p.cues;
  renderList();
  toast("Időzítés javítva (Alt+Z: visszavonás)");
};

$("#btnReplace").onclick = async () => {
  const fd = await ask($("#dlgReplace"));
  if (!fd) return;
  const find = fd.get("find");
  if (!find) return;
  const esc = find.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = fd.get("whole") ? `(?<![\\p{L}\\p{N}])${esc}(?![\\p{L}\\p{N}])` : esc;
  const re = new RegExp(pattern, "gu" + (fd.get("case") ? "" : "i"));
  let count = 0;
  pushUndo();
  for (const c of state.cues) {
    c.text = c.text.replace(re, () => { count++; return fd.get("repl"); });
  }
  if (!count) { state.undo.pop(); return toast("Nincs találat"); }
  renderList();
  scheduleSave();
  toast(`${count} csere történt`);
};

route();
