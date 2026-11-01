"use strict";

const $ = (id) => document.getElementById(id);
const LOG_KEY = "cv_logs";
const CODE_KEY = "cv_code";
const CLASS_TEACHER_KEY = "cv_class_teacher";
const CLASS_CODE_KEY = "cv_class_code";
const MAX_SIDE = 1280;

let meta = null;
let stream = null;
let fileImage = null;      // ảnh người dùng chọn (khi không dùng camera)
let busy = false;
let challenge = null;      // { name, tasks: [...], index, style }
let suggestions = [];
let sugIndex = 0;
let lastCsv = "";
let qualityTimer = null;
let dashTimer = null;

/* ------------------------------------------------------------------ tiện ích */
function store(kind) {
  try { return kind === "session" ? window.sessionStorage : window.localStorage; } catch (e) { return null; }
}
function getJson(kind, key, fallback) {
  try { return JSON.parse(store(kind).getItem(key)) ?? fallback; } catch (e) { return fallback; }
}
function setJson(kind, key, value) {
  try { const s = store(kind); if (value === null) s.removeItem(key); else s.setItem(key, JSON.stringify(value)); } catch (e) { /* trình duyệt chặn lưu */ }
}
const loadLogs = () => getJson("local", LOG_KEY, []);
function saveLogs(rows) {
  setJson("local", LOG_KEY, rows);
  $("log-count").textContent = rows.length ? rows.length + " lượt đã ghi" : "";
}
function setResult(text, cls) {
  const r = $("result");
  r.textContent = text;
  r.className = "result" + (cls ? " " + cls : "");
}
function el(tag, props, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props || {});
  for (const c of children) node.append(c);
  return node;
}
function toSpeech(text) {
  return text.replace(/\b[A-Z][a-z]?\s*\(([^()0-9A-Z]+)\)/g, "$1").replace(/\s*\((?:[A-Z][A-Za-z0-9()]*)\)/g, "");
}
function speak(text) {
  if (!$("speak").checked || !("speechSynthesis" in window) || !text) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(toSpeech(text));
    u.lang = "vi-VN";
    const vi = window.speechSynthesis.getVoices().find((v) => v.lang && v.lang.toLowerCase().startsWith("vi"));
    if (vi) u.voice = vi;
    window.speechSynthesis.speak(u);
  } catch (e) { /* không có giọng đọc: bỏ qua */ }
}
async function api(path, body) {
  const headers = { "Content-Type": "application/json" };
  const code = $("code").value.trim();
  if (code) headers["X-Access-Code"] = code;
  const res = await fetch(path, { method: body ? "POST" : "GET", headers, body: body ? JSON.stringify(body) : undefined });
  let json = {};
  try { json = await res.json(); } catch (e) { json = { ok: false, error: "Máy chủ trả về dữ liệu không đọc được." }; }
  return { status: res.status, json };
}

/* ------------------------------------------------------------------ khởi tạo */
async function init() {
  const saved = store("session") && store("session").getItem(CODE_KEY);
  if (saved) $("code").value = saved;
  $("code").addEventListener("change", () => { const s = store("session"); if (s) s.setItem(CODE_KEY, $("code").value.trim()); });
  saveLogs(loadLogs());
  try {
    const { status, json } = await api("/api/meta");
    if (status !== 200) throw new Error("meta");
    meta = json;
  } catch (e) {
    setResult("Không tải được thông tin từ máy chủ. Hãy tải lại trang.", "bad");
    return;
  }
  $("grade").add(new Option("Tất cả các lớp", "0"));
  for (const g of Object.keys(meta.grades).sort()) $("grade").add(new Option(meta.grades[g], g));
  fillDecks();
  for (const s of meta.scenarios) $("scenario").add(new Option(s, s));
  for (const q of meta.equations) $("eq-select").add(new Option((q.id + 1) + ". " + q.reactants.join(" + ") + " → " + q.products.join(" + "), String(q.id)));
  buildEquationForm();
  $("meta-line").textContent = meta.substances + " chất trong cơ sở dữ liệu";
  initClassroom();
}
function fillDecks() {
  const grade = $("grade").value;
  $("deck").replaceChildren();
  for (const name of Object.keys(meta.decks)) {
    if (grade === "0" || String(meta.deck_info[name].grade) === grade) $("deck").add(new Option(name, name));
  }
  $("ch-start").disabled = !$("deck").options.length;
}

/* ------------------------------------------------------------------ chất lượng ảnh trực tiếp (cùng ngưỡng với máy chủ) */
function measureQuality(source, w, h) {
  const scale = Math.min(1, 640 / Math.max(w, h));
  const cw = Math.max(Math.round(w * scale), 8), ch = Math.max(Math.round(h * scale), 8);
  const c = document.createElement("canvas");
  c.width = cw; c.height = ch;
  const ctx = c.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(source, 0, 0, cw, ch);
  const d = ctx.getImageData(0, 0, cw, ch).data;
  const gray = new Float32Array(cw * ch);
  let sum = 0, glare = 0;
  for (let i = 0, p = 0; i < d.length; i += 4, p++) {
    const r = d[i], g = d[i + 1], b = d[i + 2];
    const v = 0.299 * r + 0.587 * g + 0.114 * b;
    gray[p] = v; sum += v;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    if (mx >= 250 && (mx === 0 ? 0 : (mx - mn) / mx * 255) < 40) glare++;
  }
  const n = cw * ch, mean = sum / n;
  let varSum = 0;
  for (let i = 0; i < n; i++) varSum += (gray[i] - mean) ** 2;
  let lsum = 0, lsq = 0, cnt = 0;
  for (let y = 1; y < ch - 1; y++) for (let x = 1; x < cw - 1; x++) {
    const i = y * cw + x;
    const lap = gray[i - 1] + gray[i + 1] + gray[i - cw] + gray[i + cw] - 4 * gray[i];
    lsum += lap; lsq += lap * lap; cnt++;
  }
  return { brightness: mean, contrast: Math.sqrt(varSum / n), glare: glare / n, sharpness: lsq / cnt - (lsum / cnt) ** 2 };
}
function qualityMessage(m) {
  const bad = [], warn = [];
  const add = (text, severe) => (severe ? bad : warn).push(text);
  if (m.brightness < 70) add("Ảnh tối: bật thêm đèn.", m.brightness < 40);
  else if (m.brightness > 210) add("Ảnh sáng gắt: giảm đèn.", m.brightness > 235);
  if (m.sharpness < 150) add("Ảnh mờ: giữ camera yên.", m.sharpness < 20);
  if (m.glare > 0.10) add("Có vùng lóa: đổi hướng đèn.", m.glare > 0.40);
  if (m.contrast < 22) add("Thiếu tương phản: dùng nền trơn.", m.contrast < 10);
  return { bad, warn };
}
function startQualityWatch() {
  stopQualityWatch();
  const tick = () => {
    const v = $("video");
    if (!stream || !v.videoWidth) return;
    const q = qualityMessage(measureQuality(v, v.videoWidth, v.videoHeight));
    const box = $("live-quality");
    if (q.bad.length) { box.textContent = q.bad.join(" "); box.className = "quality bad"; }
    else if (q.warn.length) { box.textContent = q.warn.join(" "); box.className = "quality warn"; }
    else { box.textContent = "Ánh sáng và độ nét tốt."; box.className = "quality good"; }
  };
  tick();
  qualityTimer = setInterval(tick, 900);
}
function stopQualityWatch() {
  if (qualityTimer) clearInterval(qualityTimer);
  qualityTimer = null;
  $("live-quality").textContent = "";
  $("live-quality").className = "quality";
}

/* ------------------------------------------------------------------ camera và ảnh */
async function toggleCamera() {
  if (stream) { stopCamera(); return; }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setResult("Trình duyệt không hỗ trợ camera. Hãy dùng nút Chọn ảnh.", "warn");
    return;
  }
  try {
    const id = $("camera-select").value;
    const video = id ? { deviceId: { exact: id } } : { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } };
    stream = await navigator.mediaDevices.getUserMedia({ video, audio: false });
  } catch (e) {
    setResult("Không mở được camera (" + (e && e.name ? e.name : "lỗi") + "). Hãy cho phép dùng camera hoặc dùng nút Chọn ảnh.", "warn");
    return;
  }
  fileImage = null;
  const v = $("video");
  v.srcObject = stream;
  await v.play().catch(() => {});
  $("snap").hidden = true;
  $("stage").classList.remove("shot");
  $("stage").classList.add("live");
  $("btn-camera").textContent = "Tắt camera";
  $("btn-check").disabled = false;
  startQualityWatch();
  try {
    const devices = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
    const sel = $("camera-select");
    if (devices.length > 1) {
      const current = stream.getVideoTracks()[0].getSettings().deviceId;
      sel.replaceChildren(...devices.map((d, i) => new Option(d.label || "Camera " + (i + 1), d.deviceId, false, d.deviceId === current)));
      sel.hidden = false;
    }
  } catch (e) { /* không liệt kê được: bỏ qua */ }
}
function stopCamera() {
  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null;
  stopQualityWatch();
  $("video").srcObject = null;
  $("stage").classList.remove("live");
  $("btn-camera").textContent = "Bật camera";
  $("btn-check").disabled = !fileImage;
}
function loadFile(file) {
  if (!file) return;
  const img = new Image();
  const url = URL.createObjectURL(file);
  img.onload = () => {
    stopCamera();
    fileImage = img;
    drawSource(img, img.naturalWidth, img.naturalHeight);
    $("stage").classList.add("shot");
    $("btn-check").disabled = false;
    const q = qualityMessage(measureQuality(img, img.naturalWidth, img.naturalHeight));
    const box = $("live-quality");
    box.textContent = q.bad.concat(q.warn).join(" ") || "Ánh sáng và độ nét tốt.";
    box.className = "quality " + (q.bad.length ? "bad" : q.warn.length ? "warn" : "good");
    URL.revokeObjectURL(url);
  };
  img.onerror = () => { setResult("Không đọc được ảnh này. Hãy chọn ảnh JPG hoặc PNG.", "warn"); URL.revokeObjectURL(url); };
  img.src = url;
}
function drawSource(source, w, h) {
  const scale = Math.min(1, MAX_SIDE / Math.max(w, h));
  const c = $("snap");
  c.width = Math.round(w * scale);
  c.height = Math.round(h * scale);
  c.getContext("2d").drawImage(source, 0, 0, c.width, c.height);
  c.hidden = false;
}
function grab() {
  if (stream && $("video").videoWidth) {
    drawSource($("video"), $("video").videoWidth, $("video").videoHeight);
  } else if (fileImage) {
    drawSource(fileImage, fileImage.naturalWidth, fileImage.naturalHeight);
  } else {
    return null;
  }
  return $("snap").toDataURL("image/jpeg", 0.85);
}
function overlay(out) {
  const c = $("snap");
  const ctx = c.getContext("2d");
  const pts = {};
  const fontPx = Math.max(14, Math.round(c.width / 45));
  ctx.lineWidth = Math.max(2, c.width / 400);
  ctx.font = "bold " + fontPx + "px system-ui, sans-serif";
  for (const card of out.cards || []) {
    if (!card.box_2d) continue;
    const [y0, x0, y1, x1] = card.box_2d;
    const X0 = x0 / 1000 * c.width, Y0 = y0 / 1000 * c.height, X1 = x1 / 1000 * c.width, Y1 = y1 / 1000 * c.height;
    ctx.strokeStyle = "#ff8c00";
    ctx.strokeRect(X0, Y0, X1 - X0, Y1 - Y0);
    ctx.fillStyle = "#e11d48";
    ctx.fillText(String(card.symbol), X0 + 4, Y0 + fontPx + 2);
    pts[card.id] = [(X0 + X1) / 2, (Y0 + Y1) / 2];
  }
  ctx.strokeStyle = "#16a34a";
  ctx.lineWidth *= 2;
  const ionic = new Set();
  for (const cl of out.clusters || []) if (cl.kind === "MATCH" && cl.substance && cl.substance.ionic) (cl.cards || []).forEach((id) => ionic.add(String(id)));
  for (const e of out.connections || []) {
    if (pts[e.a] && pts[e.b]) {
      ctx.setLineDash(ionic.has(String(e.a)) && ionic.has(String(e.b)) ? [10, 8] : []);   // nét đứt: liên kết ion theo quy ước ghép cặp
      ctx.beginPath(); ctx.moveTo(...pts[e.a]); ctx.lineTo(...pts[e.b]); ctx.stroke();
    }
  }
  ctx.setLineDash([]);
  $("stage").classList.add("shot");
}

/* ------------------------------------------------------------------ kiểm tra */
function classFor(out) {
  if (out.status !== "OK") return "warn";
  const kinds = out.clusters.map((c) => c.kind);
  if (kinds.every((k) => k === "MATCH")) return "ok";
  return kinds.some((k) => k === "WRONG_BONDS" || k === "UNKNOWN") ? "bad" : "warn";
}
async function analyze(payload, withOverlay) {
  if (busy) return;
  busy = true;
  $("btn-check").textContent = "Đang phân tích…";
  $("btn-check").disabled = true;
  $("btn-demo").disabled = true;
  hideSuggest();
  const task = challenge && currentTask();
  if (task) payload.target = task.key;
  try {
    const { status, json } = await api("/api/analyze", payload);
    if (status !== 200 || !json.ok) {
      const msg = status === 401 ? "Thẻ này chưa có mã vuông nên cần mã truy cập. Hãy nhập ở mục Thiết lập, hoặc dùng bộ thẻ in có mã." : (json.error || "Có lỗi xảy ra.");
      setResult(msg, "bad");
      return;
    }
    render(json, task, withOverlay);
  } catch (e) {
    setResult("Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.", "bad");
  } finally {
    busy = false;
    $("btn-check").textContent = "KIỂM TRA";
    $("btn-check").disabled = !(stream || fileImage);
    $("btn-demo").disabled = false;
  }
}
function render(out, task, withOverlay) {
  let text = out.message;
  let cls = classFor(out);
  if (task && out.attempt) {
    text = out.attempt.message;
    cls = out.attempt.correct ? "ok" : (out.status === "OK" ? "bad" : "warn");
    const row = recordLog(out, task);
    applyAttempt(out, task);
    if (row) sendToClass(row);
    if (out.attempt.correct) text += "\n\n" + (challenge.index >= challenge.tasks.length ? summaryText() : promptText());
    refreshChallenge();
  }
  setResult(text, cls);
  showWhy(out);
  const qn = $("quality-note");
  const warnings = out.quality && out.quality.warnings ? out.quality.warnings : [];
  qn.hidden = !warnings.length;
  qn.className = "quality warn";
  qn.textContent = warnings.length ? "Lưu ý về ảnh: " + warnings.join(" ") : "";
  speak(text);
  if (withOverlay && out.cards && out.cards.length) overlay(out);
  $("meta-line").textContent = [out.model, out.links_source === "geometry" ? "liên kết đo bằng hình học" : out.links_source === "markers" ? "đọc từ mã vuông" : ""].filter(Boolean).join(" · ");
  const cluster = out.status === "OK" ? out.clusters.find((c) => c.kind === "SUGGEST") : null;
  if (cluster) { suggestions = cluster.suggestions; sugIndex = 0; askSuggestion(); }
}
function showWhy(out) {
  const lines = [];
  for (const c of out.clusters || []) for (const t of c.explain || []) lines.push(t);
  $("why-list").replaceChildren(...lines.map((t) => el("li", { textContent: t })));
  $("why").hidden = !lines.length;
  $("why").open = false;
}

/* ------------------------------------------------------------------ gợi ý "Có phải bạn muốn ghép …?" */
function hideSuggest() { $("suggest").hidden = true; suggestions = []; }
function askSuggestion() {
  const s = suggestions[sugIndex];
  $("suggest-q").textContent = "Có phải bạn muốn ghép " + s.name + " (" + s.formula + ")?";
  $("suggest").hidden = false;
}
function answerSuggestion(yes) {
  if (!suggestions.length) return;
  const s = suggestions[sugIndex];
  if (yes) {
    const part = (o) => Object.entries(o).map(([sym, n]) => n + " thẻ " + sym + (meta.elements[sym] ? " (" + meta.elements[sym] + ")" : "")).join(", ");
    let text = s.name + " (" + s.formula + "). Cấu trúc chuẩn: " + s.structure + ".";
    if (Object.keys(s.missing).length) text += " Còn thiếu " + part(s.missing) + ".";
    if (Object.keys(s.extra).length) text += " Đang thừa " + part(s.extra) + ".";
    setResult(text, "ok");
    speak(text);
    hideSuggest();
    return;
  }
  sugIndex += 1;
  if (sugIndex >= suggestions.length) { setResult("Hết gợi ý. Hãy kiểm tra lại cách ghép thẻ.", "warn"); hideSuggest(); }
  else askSuggestion();
}

/* ------------------------------------------------------------------ thử thách */
const currentTask = () => (challenge && challenge.index < challenge.tasks.length ? challenge.tasks[challenge.index] : null);
const promptText = () => {
  const t = currentTask();
  const head = "Câu " + (challenge.index + 1) + "/" + challenge.tasks.length + ": ";
  return head + (t.prompt ? t.prompt : "hãy ghép phân tử " + t.name + " (" + t.formula + ").");
};
function summaryText() {
  const T = challenge.tasks;
  const score = T.reduce((a, t) => a + t.score, 0);
  const max = meta.scoring.base * T.length;
  const hints = T.reduce((a, t) => a + t.hints, 0);
  const worst = T.filter((t) => t.attempts || t.hints).sort((a, b) => (b.attempts + 2 * b.hints) - (a.attempts + 2 * a.hints))[0];
  return "Tổng kết: " + score + "/" + max + " điểm, đúng " + T.filter((t) => t.solved).length + " câu, bỏ qua " +
    T.filter((t) => t.skipped).length + ", dùng " + hints + " gợi ý." + (worst ? " Câu khó nhất: " + worst.formula + "." : "");
}
function refreshChallenge() {
  const active = !!challenge;
  const t = currentTask();
  $("ch-end").disabled = !active;
  $("ch-hint").disabled = !t;
  $("ch-skip").disabled = !t;
  if (!active) { $("ch-task").textContent = "Chọn bộ đề rồi nhấn Bắt đầu."; $("ch-score").textContent = ""; return; }
  $("ch-task").textContent = t ? promptText() : "Đã xong bộ đề. " + summaryText();
  $("ch-score").textContent = "Điểm: " + challenge.tasks.reduce((a, x) => a + x.score, 0);
}
function startChallenge() {
  if (!meta || !$("deck").value) return;
  const name = $("deck").value;
  challenge = { name, index: 0, style: meta.deck_info[name].style,
    tasks: meta.decks[name].map((c) => ({ key: c.key, name: c.name, formula: c.formula, prompt: c.prompt || null, attempts: 0, hints: 0, solved: false, skipped: false, score: 0 })) };
  refreshChallenge();
  setResult("Bắt đầu thử thách. " + promptText());
  speak(promptText());
}
function endChallenge() {
  if (challenge) setResult(summaryText());
  challenge = null;
  refreshChallenge();
}
function applyAttempt(out, t) {
  if (out.status !== "OK") return;            // ảnh hỏng không tính là lần sai
  t.attempts += 1;
  if (out.attempt.correct) {
    const s = meta.scoring;
    t.solved = true;
    t.score = Math.max(s.min, s.base - s.wrong * (t.attempts - 1) - s.hint * t.hints);
    challenge.index += 1;
  }
}
async function hint() {
  const t = currentTask();
  if (!t) return;
  if (t.hints >= meta.scoring.max_hints) { setResult("Đã dùng hết 3 gợi ý cho câu này.", "warn"); return; }
  const { status, json } = await api("/api/hint", { target: t.key, level: t.hints + 1 });
  if (status !== 200) { setResult(json.error || "Không lấy được gợi ý.", "bad"); return; }
  t.hints += 1;
  setResult(json.hint);
  speak(json.hint);
}
function skip() {
  const t = currentTask();
  if (!t) return;
  t.skipped = true;
  challenge.index += 1;
  refreshChallenge();
  setResult("Đã bỏ qua. " + (currentTask() ? promptText() : summaryText()));
}

/* ------------------------------------------------------------------ nhật ký và báo cáo */
function recordLog(out, task) {
  if (out.status !== "OK") return null;
  const ok = out.clusters.find((c) => c.kind === "MATCH" && c.substance.key === task.key);
  const r = ok || out.clusters[0];
  let missing = {}, extra = {}, bonds = "";
  if (r.kind === "SUGGEST") {
    const s = r.suggestions.find((x) => x.key === task.key) || r.suggestions[0];
    missing = s.missing; extra = s.extra;
  } else if (r.kind === "WRONG_BONDS") {
    bonds = (r.extra_bonds || []).join(", ") + " | " + (r.missing_bonds || []).join(", ");
  }
  const outcome = ok ? "ĐÚNG" : { MATCH: "ĐÚNG CHẤT KHÁC", WRONG_BONDS: "SAI LIÊN KẾT", SUGGEST: "GHÉP DỞ", UNKNOWN: "KHÔNG NHẬN RA" }[r.kind];
  const pad = (n) => String(n).padStart(2, "0");
  const d = new Date();
  const fmt = (o) => Object.entries(o).sort().map(([k, n]) => k + "x" + n).join(" ");
  const row = {
    "thời gian": d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()),
    "nhóm": $("group").value.trim() || "Nhóm 1", "chất mục tiêu": task.key, "kết quả": outcome,
    "thẻ thiếu": fmt(missing), "thẻ thừa": fmt(extra), "liên kết sai": bonds,
  };
  const rows = loadLogs();
  rows.push(row);
  saveLogs(rows.slice(-5000));
  return row;
}
async function showReport() {
  const { status, json } = await api("/api/report", { rows: loadLogs() });
  $("report-text").textContent = status === 200 ? json.report : (json.error || "Không tạo được báo cáo.");
  lastCsv = status === 200 ? json.csv : "";
  $("btn-csv").disabled = !lastCsv || !loadLogs().length;
  $("report-dialog").showModal();
}
function downloadCsv() {
  const blob = new Blob(["﻿" + lastCsv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "nhat_ky_lop_hoc.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ------------------------------------------------------------------ cân bằng phương trình (lớp 8) */
function buildEquationForm() {
  const q = meta.equations[Number($("eq-select").value)];
  const parts = [];
  const species = (list, offset) => list.forEach((f, i) => {
    if (i) parts.push(el("span", { className: "op", textContent: "+" }));
    parts.push(el("input", { type: "number", min: "1", max: "20", value: "1", id: "eq-c" + (offset + i), ariaLabel: "Hệ số của " + f }));
    parts.push(el("span", { textContent: f }));
  });
  species(q.reactants, 0);
  parts.push(el("span", { className: "op", textContent: "→" }));
  species(q.products, q.reactants.length);
  $("eq-form").replaceChildren(...parts);
  $("eq-msg").textContent = "Điền hệ số vào từng ô, mỗi hệ số từ 1 đến 20.";
  $("eq-msg").className = "result small";
}
const eqCoefficients = () => {
  const q = meta.equations[Number($("eq-select").value)];
  return Array.from({ length: q.reactants.length + q.products.length }, (_, i) => Number($("eq-c" + i).value));
};
async function checkEquation() {
  const id = Number($("eq-select").value);
  const { status, json } = await api("/api/equation", { id, coefficients: eqCoefficients() });
  if (status !== 200) { $("eq-msg").textContent = json.error || "Không kiểm tra được."; $("eq-msg").className = "result small warn"; return; }
  $("eq-msg").textContent = json.message;
  $("eq-msg").className = "result small " + (json.balanced && json.simplest ? "ok" : json.balanced ? "warn" : "bad");
  speak(json.message);
}
async function revealEquation() {
  const id = Number($("eq-select").value);
  const { status, json } = await api("/api/equation", { id, reveal: true });
  if (status !== 200) return;
  json.coefficients.forEach((c, i) => { $("eq-c" + i).value = String(c); });
  $("eq-msg").textContent = "Đáp án: " + json.equation;
  $("eq-msg").className = "result small";
}

/* ------------------------------------------------------------------ lớp học trực tuyến */
function initClassroom() {
  if (!meta.classroom) { $("class-off").hidden = false; $("class-box").hidden = true; return; }
  const teacher = getJson("session", CLASS_TEACHER_KEY, null);
  if (teacher) showTeacherInfo(teacher);
  const code = getJson("session", CLASS_CODE_KEY, null);
  if (code) { $("class-code").value = code; showJoined(code); }
}
function classMsg(text, cls) { const m = $("class-msg"); m.textContent = text; m.className = "note" + (cls ? " " + cls : ""); }
function showTeacherInfo(t) {
  $("class-info").hidden = false;
  $("class-info").textContent = "Mã lớp: " + t.code + " (giáo viên giữ, học sinh nhập mã này). Dữ liệu tự xóa sau 24 giờ.";
  $("class-open").hidden = false;
}
function showJoined(code) {
  $("class-leave").hidden = false;
  classMsg("Đang ở lớp " + code + ". Kết quả thử thách của nhóm sẽ gửi lên cho giáo viên (không kèm ảnh hay tên).", "good");
}
async function createClass() {
  const { status, json } = await api("/api/classroom", { action: "create", name: "Lớp học" });
  if (status !== 200) { classMsg(json.error || "Không tạo được lớp.", "bad"); return; }
  const t = { code: json.code, key: json.teacher_key };
  setJson("session", CLASS_TEACHER_KEY, t);
  showTeacherInfo(t);
  classMsg("Đã tạo lớp. Hãy đọc mã " + t.code + " cho học sinh.", "good");
  openDashboard();
}
async function joinClass() {
  const code = $("class-code").value.trim().toUpperCase();
  if (code.length !== 6) { classMsg("Mã lớp gồm 6 kí tự.", "warn"); return; }
  const { status, json } = await api("/api/classroom", { action: "join", code });
  if (status !== 200) { classMsg(json.error || "Không vào được lớp.", "bad"); return; }
  setJson("session", CLASS_CODE_KEY, code);
  showJoined(code);
}
function leaveClass() {
  setJson("session", CLASS_CODE_KEY, null);
  $("class-leave").hidden = true;
  classMsg("Đã rời lớp.");
}
async function sendToClass(row) {
  const code = getJson("session", CLASS_CODE_KEY, null);
  if (!code) return;
  try {
    const { status, json } = await api("/api/classroom", { action: "submit", code, row });
    if (status !== 200) classMsg("Không gửi được kết quả lên lớp: " + (json.error || status), "warn");
  } catch (e) { classMsg("Mất kết nối, kết quả vẫn lưu trong trình duyệt.", "warn"); }
}
async function refreshDashboard() {
  const t = getJson("session", CLASS_TEACHER_KEY, null);
  if (!t) return;
  const { status, json } = await api("/api/classroom", { action: "state", code: t.code, teacher_key: t.key });
  if (status !== 200) { $("class-sub").textContent = json.error || "Không tải được dữ liệu lớp."; return; }
  $("class-title").textContent = "Bảng điều khiển lớp " + json.code;
  $("class-sub").textContent = json["tổng lượt"] === 0 ? "Chưa có nhóm nào gửi kết quả. Mã lớp: " + json.code : "Tổng " + json["tổng lượt"] + " lượt · tự làm mới mỗi 5 giây";
  const head = ["Nhóm", "Đã xong", "Lượt", "Câu gần nhất", "Kết quả gần nhất", "Cách đây"];
  $("class-table").tHead.replaceChildren(el("tr", {}, ...head.map((h) => el("th", { textContent: h }))));
  $("class-table").tBodies[0].replaceChildren(...json["nhóm"].map((g) => {
    const tr = el("tr", { className: g["kẹt"] ? "stuck" : (g["kết quả gần nhất"] === "ĐÚNG" ? "done" : "") },
      el("td", { textContent: g["nhóm"] + (g["kẹt"] ? " (kẹt)" : "") }), el("td", { textContent: String(g["đã xong"]) }),
      el("td", { textContent: String(g["lượt"]) }), el("td", { textContent: g["công thức"] }),
      el("td", { textContent: g["kết quả gần nhất"] }), el("td", { textContent: g["giây trước"] + " giây" }));
    return tr;
  }));
  const extra = $("class-extra");
  extra.replaceChildren();
  if (json["câu khó"].length) {
    extra.append(el("h3", { textContent: "Câu sai nhiều nhất" }),
      el("ul", {}, ...json["câu khó"].map((x) => el("li", { textContent: x["tên"] + " (" + x["công thức"] + "): sai " + x["sai"] + "/" + x["lượt"] + " lượt" }))));
  }
  if (json["quan niệm sai"].length) {
    extra.append(el("h3", { textContent: "Quan niệm sai thường gặp" }),
      el("ul", {}, ...json["quan niệm sai"].map((x) => el("li", { textContent: x["nhãn"] + " (" + x["lượt"] + " lượt). " + x["cách xử lý"] }))));
  }
}
async function openDashboard() {
  await refreshDashboard();
  if (!$("class-dialog").open) $("class-dialog").showModal();
  clearInterval(dashTimer);
  dashTimer = setInterval(refreshDashboard, 5000);
}
function closeDashboard() { clearInterval(dashTimer); dashTimer = null; $("class-dialog").close(); }
async function endClass() {
  const t = getJson("session", CLASS_TEACHER_KEY, null);
  if (!t || !confirm("Kết thúc lớp và xóa toàn bộ dữ liệu lớp trên máy chủ?")) return;
  await api("/api/classroom", { action: "end", code: t.code, teacher_key: t.key });
  setJson("session", CLASS_TEACHER_KEY, null);
  $("class-info").hidden = true;
  $("class-open").hidden = true;
  closeDashboard();
  classMsg("Đã kết thúc lớp và xóa dữ liệu.");
}

/* ------------------------------------------------------------------ nối sự kiện */
$("btn-camera").addEventListener("click", toggleCamera);
$("camera-select").addEventListener("change", async () => { stopCamera(); await toggleCamera(); });
$("file-input").addEventListener("change", (e) => { loadFile(e.target.files[0]); e.target.value = ""; });
$("btn-check").addEventListener("click", () => { const img = grab(); if (img) analyze({ image: img }, true); });
$("btn-demo").addEventListener("click", () => analyze({ demo: $("scenario").value }, false));
$("sg-yes").addEventListener("click", () => answerSuggestion(true));
$("sg-no").addEventListener("click", () => answerSuggestion(false));
$("grade").addEventListener("change", fillDecks);
$("ch-start").addEventListener("click", startChallenge);
$("ch-end").addEventListener("click", endChallenge);
$("ch-hint").addEventListener("click", hint);
$("ch-skip").addEventListener("click", skip);
$("eq-select").addEventListener("change", buildEquationForm);
$("eq-check").addEventListener("click", checkEquation);
$("eq-reveal").addEventListener("click", revealEquation);
$("class-create").addEventListener("click", createClass);
$("class-open").addEventListener("click", openDashboard);
$("class-join").addEventListener("click", joinClass);
$("class-leave").addEventListener("click", leaveClass);
$("class-end").addEventListener("click", endClass);
$("class-close").addEventListener("click", closeDashboard);
$("class-dialog").addEventListener("close", () => { clearInterval(dashTimer); dashTimer = null; });
$("btn-report").addEventListener("click", showReport);
$("btn-csv").addEventListener("click", downloadCsv);
$("btn-close").addEventListener("click", () => $("report-dialog").close());
$("btn-clear").addEventListener("click", () => { if (confirm("Xóa toàn bộ nhật ký lớp học trong trình duyệt này?")) saveLogs([]); });
window.addEventListener("pagehide", stopCamera);
init();
