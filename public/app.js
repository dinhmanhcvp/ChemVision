"use strict";

const $ = (id) => document.getElementById(id);
const LOG_KEY = "cv_logs";
const CODE_KEY = "cv_code";
const MAX_SIDE = 1280;

let meta = null;
let stream = null;
let fileImage = null;      // ảnh người dùng chọn (khi không dùng camera)
let busy = false;
let challenge = null;      // { name, tasks: [...], index }
let suggestions = [];
let sugIndex = 0;
let lastCsv = "";

/* ------------------------------------------------------------------ tiện ích */
function store(kind) {
  try { return kind === "session" ? window.sessionStorage : window.localStorage; } catch (e) { return null; }
}
function loadLogs() {
  try { return JSON.parse(store("local").getItem(LOG_KEY)) || []; } catch (e) { return []; }
}
function saveLogs(rows) {
  try { store("local").setItem(LOG_KEY, JSON.stringify(rows)); } catch (e) { /* trình duyệt chặn lưu: bỏ qua */ }
  $("log-count").textContent = rows.length ? rows.length + " lượt đã ghi" : "";
}
function setResult(text, cls) {
  const r = $("result");
  r.textContent = text;
  r.className = "result" + (cls ? " " + cls : "");
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
  for (const name of Object.keys(meta.decks)) $("deck").add(new Option(name, name));
  for (const s of meta.scenarios) $("scenario").add(new Option(s, s));
  $("meta-line").textContent = meta.substances + " chất trong cơ sở dữ liệu";
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
  ctx.lineWidth = Math.max(2, c.width / 400);
  ctx.font = "bold " + Math.max(14, Math.round(c.width / 45)) + "px system-ui, sans-serif";
  for (const card of out.cards || []) {
    if (!card.box_2d) continue;
    const [y0, x0, y1, x1] = card.box_2d;
    const X0 = x0 / 1000 * c.width, Y0 = y0 / 1000 * c.height, X1 = x1 / 1000 * c.width, Y1 = y1 / 1000 * c.height;
    ctx.strokeStyle = "#ff8c00";
    ctx.strokeRect(X0, Y0, X1 - X0, Y1 - Y0);
    ctx.fillStyle = "#e11d48";
    ctx.fillText(String(card.symbol), X0 + 4, Y0 + parseInt(ctx.font.match(/(\d+)px/)[1], 10) + 2);
    pts[card.id] = [(X0 + X1) / 2, (Y0 + Y1) / 2];
  }
  ctx.strokeStyle = "#16a34a";
  ctx.lineWidth *= 2;
  for (const e of out.connections || []) {
    if (pts[e.a] && pts[e.b]) { ctx.beginPath(); ctx.moveTo(...pts[e.a]); ctx.lineTo(...pts[e.b]); ctx.stroke(); }
  }
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
      const msg = status === 401 ? "Mã truy cập sai hoặc chưa nhập. Hãy nhập ở mục Thiết lập." : (json.error || "Có lỗi xảy ra.");
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
    recordLog(out, task);
    applyAttempt(out, task);
    if (out.attempt.correct) text += "\n\n" + (challenge.index >= challenge.tasks.length ? summaryText() : promptText());
    refreshChallenge();
  }
  setResult(text, cls);
  speak(text);
  if (withOverlay && out.cards && out.cards.length) overlay(out);
  $("meta-line").textContent = [out.model, out.links_source === "geometry" ? "liên kết đo bằng hình học" : ""].filter(Boolean).join(" · ");
  const cluster = out.status === "OK" ? out.clusters.find((c) => c.kind === "SUGGEST") : null;
  if (cluster) { suggestions = cluster.suggestions; sugIndex = 0; askSuggestion(); }
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
  return "Câu " + (challenge.index + 1) + "/" + challenge.tasks.length + ": hãy ghép phân tử " + t.name + " (" + t.formula + ").";
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
  $("ch-start").disabled = false;
  if (!active) { $("ch-task").textContent = "Chọn bộ đề rồi nhấn Bắt đầu."; $("ch-score").textContent = ""; return; }
  $("ch-task").textContent = t ? promptText() : "Đã xong bộ đề. " + summaryText();
  $("ch-score").textContent = "Điểm: " + challenge.tasks.reduce((a, x) => a + x.score, 0);
}
function startChallenge() {
  if (!meta || !$("deck").value) return;
  const deck = meta.decks[$("deck").value];
  challenge = { name: $("deck").value, index: 0,
    tasks: deck.map((c) => ({ key: c.key, name: c.name, formula: c.formula, attempts: 0, hints: 0, solved: false, skipped: false, score: 0 })) };
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
  if (out.status !== "OK") return;
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
  const rows = loadLogs();
  rows.push({
    "thời gian": d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" + pad(d.getSeconds()),
    "nhóm": $("group").value.trim() || "Nhóm 1", "chất mục tiêu": task.key, "kết quả": outcome,
    "thẻ thiếu": fmt(missing), "thẻ thừa": fmt(extra), "liên kết sai": bonds,
  });
  saveLogs(rows.slice(-5000));
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

/* ------------------------------------------------------------------ nối sự kiện */
$("btn-camera").addEventListener("click", toggleCamera);
$("camera-select").addEventListener("change", async () => { stopCamera(); await toggleCamera(); });
$("file-input").addEventListener("change", (e) => { loadFile(e.target.files[0]); e.target.value = ""; });
$("btn-check").addEventListener("click", () => { const img = grab(); if (img) analyze({ image: img }, true); });
$("btn-demo").addEventListener("click", () => analyze({ demo: $("scenario").value }, false));
$("sg-yes").addEventListener("click", () => answerSuggestion(true));
$("sg-no").addEventListener("click", () => answerSuggestion(false));
$("ch-start").addEventListener("click", startChallenge);
$("ch-end").addEventListener("click", endChallenge);
$("ch-hint").addEventListener("click", hint);
$("ch-skip").addEventListener("click", skip);
$("btn-report").addEventListener("click", showReport);
$("btn-csv").addEventListener("click", downloadCsv);
$("btn-close").addEventListener("click", () => $("report-dialog").close());
$("btn-clear").addEventListener("click", () => { if (confirm("Xóa toàn bộ nhật ký lớp học trong trình duyệt này?")) saveLogs([]); });
window.addEventListener("pagehide", stopCamera);
init();
