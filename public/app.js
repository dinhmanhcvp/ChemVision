import { $, el, icon, formulaNode, elementChip, setMood, confetti, sfx, toast } from "/ui.js";
import * as progress from "/progress.js";

const LOG_KEY = "cv_logs";
const CODE_KEY = "cv_code";
const PREF_KEY = "cv_prefs";
const HOWTO_KEY = "cv_howto_hidden";
const CLASS_TEACHER_KEY = "cv_class_teacher";
const CLASS_CODE_KEY = "cv_class_code";
const MAX_SIDE = 1280;
const VIEWS = ["ghep", "thuthach", "canbang", "lop", "them"];
const SMALL_SCREEN = () => window.matchMedia("(max-width: 860px)").matches;

let meta = null;
let stream = null;
let fileImage = null;      // ảnh người dùng chọn (khi không dùng camera)
let busy = false;
let challenge = null;      // { name, tasks: [...], index, style, ended }
let suggestions = [];
let sugIndex = 0;
let lastCsv = "";
let qualityTimer = null;
let dashTimer = null;
let gradeFilter = "0";
let currentView = "ghep";

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
/* Hộp xác nhận trong trang (thay cho hộp xác nhận mặc định của trình duyệt): trả về Promise<boolean> */
function askConfirm(text, yesLabel = "Đồng ý") {
  return new Promise((resolve) => {
    const d = $("confirm-dialog");
    $("confirm-text").textContent = text;
    $("confirm-yes").textContent = yesLabel;
    const done = (v) => { $("confirm-yes").onclick = $("confirm-no").onclick = null; d.onclose = null; if (d.open) d.close(); resolve(v); };
    $("confirm-yes").onclick = () => done(true);
    $("confirm-no").onclick = () => done(false);
    d.onclose = () => done(false);
    d.showModal();
  });
}
const groupName = () => ($("group").value.trim() || "Nhóm 1").slice(0, 30);
function savePrefs() {
  setJson("local", PREF_KEY, { group: $("group").value, grade: gradeFilter, speak: $("speak").checked, fx: $("fx").checked, sfx: $("sfx").checked, view: currentView });
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
const celebrate = (strength) => { if ($("fx").checked) confetti(strength); };
const sound = (kind) => { if ($("sfx").checked) sfx(kind); };
async function api(path, body) {
  const headers = { "Content-Type": "application/json" };
  const code = $("code").value.trim();
  if (code) headers["X-Access-Code"] = code;
  let res;
  try {
    res = await fetch(path, { method: body ? "POST" : "GET", headers, body: body ? JSON.stringify(body) : undefined });
  } catch (e) {                                  // mất mạng: mọi nút đều nhận được thông báo thay vì im lặng
    return { status: 0, json: { ok: false, error: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại." } };
  }
  let json = {};
  try { json = await res.json(); } catch (e) { json = { ok: false, error: "Máy chủ trả về dữ liệu không đọc được." }; }
  return { status: res.status, json };
}

/* ------------------------------------------------------------------ điều hướng giữa các thẻ */
function showView(name, opts = {}) {
  if (!VIEWS.includes(name)) name = "ghep";
  currentView = name;
  for (const v of VIEWS) {
    $("view-" + v).hidden = v !== name;
    const tab = $("tab-" + v);
    if (v === name) tab.setAttribute("aria-current", "page"); else tab.removeAttribute("aria-current");
  }
  if (opts.updateHash !== false && location.hash !== "#/" + name) history.replaceState(null, "", "#/" + name);
  if (name === "thuthach") { renderDecks(); renderBadges(); }
  if (!opts.keepScroll) window.scrollTo({ top: 0 });
  savePrefs();
}

/* ------------------------------------------------------------------ khởi tạo */
async function init() {
  const prefs = getJson("local", PREF_KEY, {});
  if (prefs.group) $("group").value = String(prefs.group).slice(0, 30);
  if (prefs.speak === false) $("speak").checked = false;
  if (prefs.fx === false) $("fx").checked = false;
  if (prefs.sfx === true) $("sfx").checked = true;
  if (typeof prefs.grade === "string") gradeFilter = prefs.grade;
  const hashView = location.hash.replace(/^#\//, "");
  showView(VIEWS.includes(hashView) ? hashView : "ghep", { updateHash: false, keepScroll: true });
  $("welcome").hidden = !!getJson("local", HOWTO_KEY, false);
  const saved = store("session") && store("session").getItem(CODE_KEY);
  if (saved) $("code").value = saved;
  saveLogs(loadLogs());
  refreshStars(false);
  updateCheckState();
  try {
    const { status, json } = await api("/api/meta");
    if (status !== 200) throw new Error("meta");
    meta = json;
  } catch (e) {
    say("Chưa kết nối được", "Hãy kiểm tra mạng rồi thử lại.", "bad", "oops");
    $("sub").append(" ", el("button", { type: "button", id: "retry", className: "btn small", textContent: "Thử lại", onclick: () => location.reload() }));
    return;
  }
  for (const s of meta.scenarios) $("scenario").add(new Option(s, s));
  for (const q of meta.equations) $("eq-select").add(new Option((q.id + 1) + ". " + q.reactants.join(" + ") + " → " + q.products.join(" + "), String(q.id)));
  buildEquationForm();
  renderGradeChips();
  renderDecks();
  renderBadges();
  initClassroom();
}

/* ------------------------------------------------------------------ sao, huy hiệu */
function refreshStars(bump) {
  $("stars-count").textContent = String(progress.totals());
  if (bump) { const c = $("stars-chip"); c.classList.remove("bump"); void c.offsetWidth; c.classList.add("bump"); }
}
function announceBadges(fresh) {
  if (!fresh || !fresh.length) return;
  toast("Huy hiệu mới: " + fresh.map((b) => b.name).join(", "), 4800);
  celebrate(0.7);
  sound("badge");
  renderBadges();
}
function renderBadges() {
  const got = new Set(progress.load().badges);
  $("badges").replaceChildren(...progress.BADGES.map((b) => el("div", { className: "badge" + (got.has(b.id) ? " got" : "") },
    el("div", { className: "hexframe" }, icon(b.ico)), el("b", { textContent: b.name }), el("small", { textContent: got.has(b.id) ? "Đã đạt" : b.how }))));
}

/* ------------------------------------------------------------------ hiển thị kết quả thân thiện */
const MOOD_BY_CLASS = { ok: "cheer", close: "think", warn: "think", bad: "oops", "": "wait" };
/* say(): một câu tiêu đề + một câu giải thích; chi tiết dài nằm trong "Vì sao?" */
function say(headline, sub, cls, mood) {
  const r = $("result");
  r.className = "result " + (cls || "idle");
  $("headline").replaceChildren(headline instanceof Node ? headline : document.createTextNode(headline));
  $("sub").replaceChildren(sub instanceof Node ? sub : document.createTextNode(sub || ""));
  setMood(mood || MOOD_BY_CLASS[cls || ""]);
  $("cards-seen").hidden = true;
  $("facts").hidden = true;
}
/* tương thích với chỗ gọi đơn giản: tách câu đầu làm tiêu đề */
function setResult(text, cls, mood) {
  const m = /^(.{8,70}?[.!?])\s+(.*)$/s.exec(text);
  if (m) say(m[1], m[2], cls, mood); else say(text, "", cls, mood);
}
function showCardsSeen(out) {
  const box = $("cards-seen");
  const cards = (out.cards || []).filter((c) => c && c.symbol);
  box.replaceChildren(...cards.map((c) => elementChip(String(c.symbol), meta.colors)));
  box.hidden = !cards.length;
}
function showFacts(items) {
  const box = $("facts");
  box.replaceChildren(...items);
  box.hidden = !items.length;
}
/* mẩu thông tin nhỏ; verdict = "yes" | "no" thêm dấu tích hoặc dấu chéo (có hình, không chỉ có màu) */
const VERDICT_ICON = { yes: "check", no: "x" };
const fact = (text, ion, verdict) => el("span", { className: "chip fact" + (ion ? " ion" : "") + (verdict ? " " + verdict : "") }, ...(verdict ? [icon(VERDICT_ICON[verdict])] : []), document.createTextNode(text));
function nameFormula(sub) {
  const span = el("span");
  span.append(document.createTextNode(sub.name + " ("), formulaNode(sub.formula), document.createTextNode(")"));
  return span;
}
function bondHint(c) {
  const parts = [];
  if (c.missing_bonds && c.missing_bonds.length) parts.push("Thử nối " + c.missing_bonds.map((b) => b.replace("-", "–")).join(", "));
  if (c.extra_bonds && c.extra_bonds.length) parts.push("bỏ nối " + c.extra_bonds.map((b) => b.replace("-", "–")).join(", "));
  return parts.length ? parts.join("; ") + "." : "";
}
function classFor(out) {
  if (out.status !== "OK") return "warn";
  const kinds = out.clusters.map((c) => c.kind);
  if (kinds.every((k) => k === "MATCH")) return "ok";
  if (kinds.includes("UNKNOWN")) return "bad";            // đỏ chỉ dành cho bộ thẻ không tạo thành chất nào
  return "close";                                          // gần đúng (nối chưa đúng, ghép dở): màu hổ phách, giọng khích lệ
}
/* Chọn tiêu đề, câu giải thích, con dấu theo kết quả có cấu trúc (không đọc lại câu chữ của máy chủ) */
function verdictFor(out) {
  const cls = classFor(out);
  if (out.status === "RECAPTURE") return { cls, mood: "think", head: "Chụp lại nhé!", sub: out.message.replace(/^Ảnh chưa đủ rõ:\s*/, "").replace(/\s*Hãy chỉnh lại thẻ và chụp lại\.$/, "") + ". Chỉnh lại rồi chụp lần nữa.", speech: "Chụp lại nhé" };
  if (out.status === "EMPTY") return { cls, mood: "think", head: "Chưa thấy thẻ nào", sub: "Đặt thẻ vào giữa khung rồi chụp lại nhé.", speech: "Chưa thấy thẻ nào" };
  const cl = out.clusters;
  if (cl.length === 1) {
    const c = cl[0];
    if (c.kind === "MATCH") {
      const facts = [];
      if (c.substance.mass) facts.push(fact((c.substance.ionic ? "Khối lượng công thức " : "Phân tử khối ") + c.substance.mass));
      if (c.substance.ionic) facts.push(fact("Hợp chất ion: các ion xếp thành mạng tinh thể", true));
      return { cls, mood: "cheer", head: "Chính xác!", sub: nameFormula(c.substance), facts, speech: "Chính xác! Đó là " + c.substance.name };
    }
    if (c.kind === "WRONG_BONDS") {
      const s = c.substance;
      return { cls, mood: "think", head: "Gần đúng rồi!", sub: el("span", {}, document.createTextNode("Đủ thẻ của "), nameFormula(s), document.createTextNode(" nhưng cách nối chưa đúng. " + bondHint(c))),
        speech: "Gần đúng rồi! Đủ thẻ của " + s.name + " nhưng cách nối chưa đúng" };
    }
    if (c.kind === "SUGGEST") {
      const s = c.suggestions[0];
      const need = Object.entries(s.missing).map(([sym, n]) => n + " thẻ " + sym).join(", ");
      const extra = Object.entries(s.extra).map(([sym, n]) => "bỏ " + n + " thẻ " + sym).join(", ");
      return { cls, mood: "think", head: "Gần xong rồi!", sub: el("span", {}, document.createTextNode("Có phải bạn muốn ghép "), nameFormula(s), document.createTextNode("? " + [need && "Cần thêm " + need, extra].filter(Boolean).join("; ") + ".")),
        speech: "Gần xong rồi! Có phải bạn muốn ghép " + s.name };
    }
    return { cls, mood: "oops", head: "Chưa nhận ra chất này", sub: "Bộ thẻ này chưa tạo thành chất nào trong chương trình. Kiểm tra số thẻ và cách nối nhé.", speech: "Chưa nhận ra chất này" };
  }
  const good = cl.filter((c) => c.kind === "MATCH").length;
  const facts = cl.map((c) => fact(c.kind === "MATCH" ? c.substance.formula : c.kind === "WRONG_BONDS" ? c.substance.formula + "?" : "chưa rõ", false, c.kind === "MATCH" ? "yes" : "no"));
  return { cls, mood: MOOD_BY_CLASS[cls], head: "Có " + cl.length + " cụm thẻ", sub: good + " cụm đúng, " + (cl.length - good) + " cụm cần xem lại.", facts, speech: "Có " + cl.length + " cụm thẻ. " + good + " cụm đúng" };
}
function renderOutput(out, task, withOverlay) {
  let v = verdictFor(out);
  let attempt = null;
  if (task && out.attempt) {
    attempt = out.attempt;
    if (attempt.correct) v = { cls: "ok", mood: "cheer", head: "Đúng rồi!", sub: nameFormula({ name: task.name, formula: task.formula }), facts: v.facts, speech: "Đúng rồi! Bạn đã ghép " + task.name };
    else if (attempt.kind === "MATCH_OTHER") v = { ...v, cls: "close", mood: "think", head: "Đúng chất khác!", sub: "Bạn ghép được chất khác, nhưng nhiệm vụ cần " + task.name + " (" + task.formula + ").", speech: "Đúng chất khác. Nhiệm vụ cần " + task.name };
  }
  say(v.head, v.sub, v.cls, v.mood);
  showCardsSeen(out);
  showFacts(v.facts || []);
  const lines = [];
  for (const c of out.clusters || []) for (const t of c.explain || []) lines.push(t);
  if (attempt && !attempt.correct) lines.unshift(attempt.message);
  if (out.message) lines.push("Tóm tắt của máy: " + out.message);
  $("why-list").replaceChildren(...lines.map((t) => el("li", { textContent: t })));
  $("why").hidden = !lines.length;
  $("why").open = false;
  const warnings = out.quality && out.quality.warnings ? out.quality.warnings : [];
  const qn = $("quality-note");
  qn.hidden = !warnings.length;
  qn.className = "quality warn";
  qn.textContent = warnings.length ? warnings.join(" ") : "";
  $("meta-line").textContent = [out.model, out.links_source === "geometry" ? "liên kết đo bằng hình học" : out.links_source === "markers" ? "đọc từ mã vuông" : ""].filter(Boolean).join(" · ");
  speak(v.speech);
  if (withOverlay && out.cards && out.cards.length) overlay(out);
  setStep(3);
  return v;
}

/* ------------------------------------------------------------------ các bước 1-2-3 */
function setStep(n) {
  [1, 2, 3].forEach((i) => { $("step-" + i).className = i < n ? "done" : i === n ? "on" : ""; });
}
function updateCheckState() {
  const ready = !!(stream || fileImage);
  $("btn-check").disabled = busy || !ready;
  $("check-hint").hidden = ready;
  if (!busy && !$("step-3").classList.contains("on")) setStep(ready ? 2 : 1);
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
  if (m.brightness < 70) add("Hơi tối, bật thêm đèn nhé.", m.brightness < 40);
  else if (m.brightness > 210) add("Ánh sáng gắt, giảm đèn nhé.", m.brightness > 235);
  if (m.sharpness < 150) add("Ảnh hơi mờ, giữ camera yên nhé.", m.sharpness < 20);
  if (m.glare > 0.10) add("Có vùng lóa, đổi hướng đèn nhé.", m.glare > 0.40);
  if (m.contrast < 22) add("Thiếu tương phản, dùng nền trơn nhé.", m.contrast < 10);
  return { bad, warn };
}
function showQuality(q) {
  const box = $("live-quality");
  if (q.bad.length) { box.textContent = q.bad.join(" "); box.className = "quality bad"; }
  else if (q.warn.length) { box.textContent = q.warn.join(" "); box.className = "quality warn"; }
  else { box.textContent = "Ánh sáng và độ nét tốt."; box.className = "quality good"; }
}
function startQualityWatch() {
  stopQualityWatch();
  const tick = () => {
    const v = $("video");
    if (!stream || !v.videoWidth) return;
    showQuality(qualityMessage(measureQuality(v, v.videoWidth, v.videoHeight)));
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
function cameraErrorText(e) {
  const name = e && e.name ? e.name : "";
  if (!window.isSecureContext) return "Camera chỉ hoạt động trên trang HTTPS. Hãy mở trang bằng địa chỉ https:// hoặc dùng nút Chọn ảnh.";
  if (name === "NotAllowedError" || name === "SecurityError") return "Bạn đã chặn camera. Nhấn biểu tượng ổ khóa cạnh địa chỉ trang, cho phép camera rồi thử lại; hoặc dùng nút Chọn ảnh.";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "Không tìm thấy camera trên thiết bị này. Hãy dùng nút Chọn ảnh.";
  if (name === "NotReadableError") return "Camera đang được ứng dụng khác sử dụng. Hãy đóng ứng dụng đó rồi thử lại.";
  return "Không mở được camera (" + (name || "lỗi") + "). Hãy dùng nút Chọn ảnh.";
}
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
    setResult(cameraErrorText(e), "warn");
    return;
  }
  fileImage = null;
  const v = $("video");
  v.srcObject = stream;
  await v.play().catch(() => {});
  $("snap").hidden = true;
  $("stage").classList.remove("shot");
  $("stage").classList.add("live");
  $("btn-camera").lastElementChild.textContent = "Tắt camera";
  updateCheckState();
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
  $("btn-camera").lastElementChild.textContent = "Bật camera";
  updateCheckState();
}
function loadFile(file) {
  if (!file) return;
  if (!/^image\//.test(file.type)) { setResult("Tệp này không phải ảnh. Hãy chọn ảnh JPG hoặc PNG.", "warn"); return; }
  const img = new Image();
  const url = URL.createObjectURL(file);
  img.onload = () => {
    stopCamera();
    fileImage = img;
    drawSource(img, img.naturalWidth, img.naturalHeight);
    $("stage").classList.add("shot");
    updateCheckState();
    showQuality(qualityMessage(measureQuality(img, img.naturalWidth, img.naturalHeight)));
    URL.revokeObjectURL(url);
    toast("Đã chọn ảnh. Nhấn KIỂM TRA nhé!");
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
function setBusy(on) {
  busy = on;
  $("btn-check").classList.toggle("busy", on);
  $("btn-check").textContent = on ? "Đang phân tích" : "KIỂM TRA";
  $("result").setAttribute("aria-busy", String(on));
  $("btn-demo").disabled = on;
  if (on) say("Đang đọc thẻ…", "Chờ một chút nhé.", "", "think");
  updateCheckState();
}
async function analyze(payload, withOverlay) {
  if (busy) return;
  if (payload.demo) showView("ghep");
  setBusy(true);
  hideSuggest();
  const task = challenge && currentTask();
  if (task) payload.target = task.key;
  try {
    const { status, json } = await api("/api/analyze", payload);
    if (status !== 200 || !json.ok) {
      const messages = {
        401: "Thẻ này chưa có mã vuông nên cần mã truy cập. Hãy nhập ở thẻ Thêm, hoặc dùng bộ thẻ in có mã vuông.",
        413: "Ảnh quá lớn. Hãy chụp lại ở độ phân giải thấp hơn.",
        429: "Bạn gửi hơi nhanh. Đợi vài giây rồi nhấn KIỂM TRA lại nhé.",
        502: "Dịch vụ nhận diện đang bận. Hãy thử lại sau ít giây.",
        503: json.error || "Máy chủ chưa sẵn sàng nhận ảnh.",
      };
      const cls = status === 429 || status === 502 || status === 0 ? "warn" : "bad";
      say(status === 0 ? "Mất kết nối" : "Chưa kiểm tra được", messages[status] || json.error || "Có lỗi xảy ra.", cls, cls === "warn" ? "think" : "oops");
      setStep(2);
      return;
    }
    render(json, task, withOverlay);
  } catch (e) {
    say("Mất kết nối", "Kiểm tra mạng rồi thử lại.", "warn", "think");
  } finally {
    setBusy(false);
  }
}
function render(out, task, withOverlay) {
  const v = renderOutput(out, task, withOverlay);
  const cluster = out.status === "OK" ? out.clusters.find((c) => c.kind === "SUGGEST") : null;
  if (task && out.attempt) {
    const row = recordLog(out, task);
    applyAttempt(out, task);
    if (row) sendToClass(row);
    if (out.attempt.correct) onSolved(task);
    else if (v.cls !== "ok") sound("oops");
    refreshChallenge();
    if (challenge && challenge.index >= challenge.tasks.length) finishChallenge();
  } else if (out.status === "OK" && v.cls === "ok") {
    celebrate(0.8); sound("ok");
    announceBadges(progress.recordMatch().fresh);
  } else if (v.cls === "bad") sound("oops");
  if (cluster) { suggestions = cluster.suggestions; sugIndex = 0; askSuggestion(); }
  if (SMALL_SCREEN()) $("result").scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function onSolved(task) {
  const r = progress.recordSolved(task.key, task.score);
  celebrate(1); sound("star");
  refreshStars(true);
  if (r.gained) toast("+" + r.gained + " sao cho " + task.name);
  announceBadges(r.fresh);
}

/* ------------------------------------------------------------------ gợi ý "Có phải bạn muốn ghép …?" */
function hideSuggest() { $("suggest").hidden = true; suggestions = []; }
function askSuggestion() {
  const s = suggestions[sugIndex];
  $("suggest-q").replaceChildren(document.createTextNode("Có phải bạn muốn ghép "), nameFormula(s), document.createTextNode("?"));
  $("suggest").hidden = false;
}
function answerSuggestion(yes) {
  if (!suggestions.length) return;
  const s = suggestions[sugIndex];
  sendActivity("suggest", { accepted: yes });
  if (yes) {
    const part = (o) => Object.entries(o).map(([sym, n]) => n + " thẻ " + sym + (meta.elements[sym] ? " (" + meta.elements[sym] + ")" : "")).join(", ");
    let text = "Cấu trúc chuẩn: " + s.structure + ".";
    if (Object.keys(s.missing).length) text += " Còn thiếu " + part(s.missing) + ".";
    if (Object.keys(s.extra).length) text += " Đang thừa " + part(s.extra) + ".";
    say(nameFormula(s), text, "ok", "happy");
    speak(s.name + ". " + text);
    hideSuggest();
    return;
  }
  sugIndex += 1;
  if (sugIndex >= suggestions.length) { say("Hết gợi ý rồi", "Hãy kiểm tra lại cách ghép thẻ nhé.", "warn", "think"); hideSuggest(); }
  else askSuggestion();
}

/* ------------------------------------------------------------------ thử thách */
const currentTask = () => (challenge && challenge.index < challenge.tasks.length ? challenge.tasks[challenge.index] : null);
const progressText = () => Math.min(challenge.index + 1, challenge.tasks.length) + "/" + challenge.tasks.length;
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
function renderDots() {
  const dots = $("mission-dots");
  if (!challenge) { dots.replaceChildren(); return; }
  dots.replaceChildren(...challenge.tasks.map((t, i) => el("span", { className: t.solved ? "done" : t.skipped ? "skip" : i === challenge.index ? "now" : "", title: "Câu " + (i + 1) })));
  dots.setAttribute("aria-valuenow", String(Math.round(challenge.index / challenge.tasks.length * 100)));
}
function refreshChallenge() {
  const active = !!challenge;
  const t = currentTask();
  $("mission").hidden = !active;
  if (active) $("welcome").hidden = true;
  $("ch-end").disabled = !active;
  $("ch-hint").disabled = !t;
  $("ch-skip").disabled = !t;
  $("ch-hint").hidden = active && !t;
  $("ch-skip").hidden = active && !t;
  $("ch-end").textContent = active && !t ? "Chọn nhiệm vụ khác" : "Dừng";
  if (!active) { $("ch-task").textContent = ""; $("ch-score").textContent = "Điểm: 0"; renderDots(); return; }
  $("mission-eyebrow").textContent = challenge.name + (t ? " · " + (challenge.index + 1) + "/" + challenge.tasks.length : "");
  $("mission-title").replaceChildren(...(t ? (t.prompt ? [document.createTextNode("Lập công thức rồi ghép")] : [document.createTextNode("Ghép " + t.name + " "), formulaNode(t.formula)]) : [document.createTextNode("Hoàn thành bộ đề!")]));
  $("ch-task").textContent = t ? promptText() : "Đã xong bộ đề. " + summaryText();
  $("ch-score").textContent = "Điểm: " + challenge.tasks.reduce((a, x) => a + x.score, 0);
  renderDots();
}
function renderGradeChips() {
  const wrap = $("grade-chips");
  const entries = [["0", "Tất cả"], ...Object.keys(meta.grades).sort().map((g) => [g, "Lớp " + g])];
  wrap.replaceChildren(...entries.map(([g, label]) => {
    const b = el("button", { type: "button", textContent: label });
    b.setAttribute("aria-pressed", String(g === gradeFilter));
    b.addEventListener("click", () => { gradeFilter = g; savePrefs(); renderGradeChips(); renderDecks(); });
    return b;
  }));
}
function renderDecks() {
  if (!meta) return;
  const grid = $("deck-grid");
  const names = Object.keys(meta.decks).filter((n) => gradeFilter === "0" || String(meta.deck_info[n].grade) === gradeFilter);
  grid.replaceChildren(...names.map((name) => {
    const items = meta.decks[name], grade = meta.deck_info[name].grade;
    const st = progress.deckStats(name, items.map((i) => i.key));
    const got = progress.load().solved;
    const b = el("button", { type: "button", className: "deck g" + grade });
    b.dataset.deck = name;
    /* tổ ong: mỗi ô lục giác là một chất; mức tô cho biết đã làm và đạt mấy sao */
    const comb = el("span", { className: "comb", ariaHidden: "true" }, ...items.map((i) => el("i", { className: "l" + (got[i.key] || 0) })));
    b.append(el("span", { className: "grade", textContent: "Lớp " + grade }), el("span", { className: "title", textContent: name.replace(/^Lớp \d+:\s*/, "") }), comb,
      el("span", { className: "meta" }, el("span", { textContent: st.solved + "/" + items.length + " chất" }), el("span", {}, icon("star"), document.createTextNode(st.stars + "/" + items.length * 3))));
    b.setAttribute("aria-label", name + ": " + st.solved + " trên " + items.length + " chất, " + st.stars + " sao");
    b.addEventListener("click", () => startChallenge(name));
    return b;
  }));
  if (!names.length) grid.append(el("p", { className: "note", textContent: "Chưa có bộ đề cho lớp này." }));
}
async function startChallenge(name) {
  if (!meta || !meta.decks[name]) return;
  if (challenge && currentTask() && !(await askConfirm("Bạn đang làm dở một nhiệm vụ. Bỏ nhiệm vụ này để bắt đầu nhiệm vụ mới?", "Bắt đầu mới"))) return;
  if (challenge) finishChallenge();
  challenge = { name, index: 0, style: meta.deck_info[name].style, ended: false,
    tasks: meta.decks[name].map((c) => ({ key: c.key, name: c.name, formula: c.formula, prompt: c.prompt || null, attempts: 0, hints: 0, solved: false, skipped: false, score: 0 })) };
  showView("ghep");
  refreshChallenge();
  savePrefs();
  say("Nhiệm vụ mới!", promptText(), "", "happy");
  speak(promptText());
  sendActivity("start", { deck: name, progress: "1/" + challenge.tasks.length });
}
function finishChallenge() {
  if (!challenge || challenge.ended) return;
  challenge.ended = true;
  const solved = challenge.tasks.filter((t) => t.solved).length;
  const r = progress.recordDeckDone(challenge.name, solved, challenge.tasks.length);
  sendActivity("end", { deck: challenge.name, progress: Math.min(challenge.index, challenge.tasks.length) + "/" + challenge.tasks.length });
  if (challenge.index >= challenge.tasks.length) { celebrate(1.2); sound("badge"); }
  announceBadges(r.fresh);
}
function endChallenge() {
  if (!challenge) return;
  const finished = !currentTask();
  const summary = summaryText();
  finishChallenge();
  challenge = null;
  refreshChallenge();
  say(finished ? "Hoàn thành!" : "Đã dừng nhiệm vụ", summary, finished ? "ok" : "", finished ? "cheer" : "wait");
  renderDecks();
  if (finished) showView("thuthach");
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
  if (t.hints >= meta.scoring.max_hints) { say("Hết gợi ý rồi", "Bạn đã dùng cả 3 gợi ý cho câu này. Cố lên nhé!", "warn", "think"); return; }
  const { status, json } = await api("/api/hint", { target: t.key, level: t.hints + 1 });
  if (status !== 200) { say("Chưa lấy được gợi ý", json.error || "Hãy thử lại.", "bad", "oops"); return; }
  t.hints += 1;
  say("Gợi ý " + t.hints + "/" + meta.scoring.max_hints, json.hint.replace(/^Gợi ý \d:\s*/, ""), "", "think");
  speak(json.hint);
  sendActivity("hint", {});
}
function skip() {
  const t = currentTask();
  if (!t) return;
  t.skipped = true;
  challenge.index += 1;
  refreshChallenge();
  if (currentTask()) { say("Đã bỏ qua", promptText(), "", "wait"); sendActivity("skip", { progress: progressText() }); }
  else { say("Hết bộ đề rồi", summaryText(), "", "wait"); sendActivity("skip", { progress: challenge.tasks.length + "/" + challenge.tasks.length }); finishChallenge(); }
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
    "nhóm": groupName(), "chất mục tiêu": task.key, "kết quả": outcome,
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
  const blob = new Blob(["\ufeff" + lastCsv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "nhat_ky_lop_hoc.csv";
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  toast("Đã tải nhật ký (CSV).");
}
async function clearLogs() {
  if (!loadLogs().length) { toast("Nhật ký đang trống."); return; }
  if (await askConfirm("Xóa toàn bộ nhật ký lớp học trong trình duyệt này?", "Xóa")) { saveLogs([]); toast("Đã xóa nhật ký."); }
}

/* ------------------------------------------------------------------ cân bằng phương trình (lớp 8) */
function parseFormula(formula) {
  const stack = [{}];
  const re = /\(|\)(\d*)|([A-Z][a-z]?)(\d*)/g;
  let m;
  while ((m = re.exec(formula))) {
    if (m[0] === "(") stack.push({});
    else if (m[0].startsWith(")")) { const inner = stack.pop(), k = Number(m[1] || 1); for (const [e, n] of Object.entries(inner)) stack[stack.length - 1][e] = (stack[stack.length - 1][e] || 0) + n * k; }
    else stack[stack.length - 1][m[2]] = (stack[stack.length - 1][m[2]] || 0) + Number(m[3] || 1);
  }
  return stack[0];
}
function buildEquationForm() {
  const q = meta.equations[Number($("eq-select").value)];
  const parts = [];
  let idx = 0;
  const species = (list) => list.forEach((f, i) => {
    if (i) parts.push(el("span", { className: "op", textContent: "+" }));
    const n = idx++;
    const input = el("input", { type: "number", min: "1", max: "20", step: "1", inputMode: "numeric", value: "1", id: "eq-c" + n });
    input.setAttribute("aria-label", "Hệ số của " + f);
    const minus = el("button", { type: "button", className: "step", textContent: "−" });
    const plus = el("button", { type: "button", className: "step", textContent: "+" });
    minus.setAttribute("aria-label", "Giảm hệ số của " + f);
    plus.setAttribute("aria-label", "Tăng hệ số của " + f);
    const bump = (d) => { input.value = String(Math.min(20, Math.max(1, (Number(input.value) || 1) + d))); input.removeAttribute("aria-invalid"); updateCounts(); };
    minus.addEventListener("click", () => bump(-1));
    plus.addEventListener("click", () => bump(1));
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") checkEquation(); });
    input.addEventListener("input", () => { input.removeAttribute("aria-invalid"); updateCounts(); });
    parts.push(el("span", { className: "sp" }, minus, input, plus, formulaNode(f)));
  });
  species(q.reactants);
  parts.push(el("span", { className: "op", textContent: "→" }));
  species(q.products);
  $("eq-form").replaceChildren(...parts);
  $("eq-msg").textContent = "Điền hệ số vào từng ô, mỗi hệ số là số nguyên từ 1 đến 20.";
  $("eq-msg").className = "notice";
  $("eq-next").hidden = true;
  updateCounts();
}
/* bảng đếm nguyên tử: giàn giáo giúp nhìn thấy chỗ lệch mà không phải tính nhẩm */
function updateCounts() {
  const q = meta.equations[Number($("eq-select").value)];
  const left = {}, right = {}, order = [];
  const add = (list, side, offset) => list.forEach((f, i) => {
    const k = Math.min(20, Math.max(0, Number($("eq-c" + (offset + i)).value) || 0));
    for (const [e, n] of Object.entries(parseFormula(f))) { if (!order.includes(e)) order.push(e); side[e] = (side[e] || 0) + n * k; }
  });
  add(q.reactants, left, 0);
  add(q.products, right, q.reactants.length);
  $("eq-counts").tBodies[0].replaceChildren(...order.map((e) => {
    const same = (left[e] || 0) === (right[e] || 0);
    const mark = el("td", { className: "mark" }, icon(same ? "check" : "x"));
    mark.setAttribute("aria-label", same ? "bằng nhau" : "chưa bằng nhau");
    return el("tr", { className: same ? "ok" : "bad" }, el("td", { textContent: e }), el("td", { textContent: String(left[e] || 0) }), el("td", { textContent: String(right[e] || 0) }), mark);
  }));
}
function readEquation() {
  const q = meta.equations[Number($("eq-select").value)];
  const n = q.reactants.length + q.products.length;
  const values = [];
  for (let i = 0; i < n; i++) {
    const input = $("eq-c" + i);
    const raw = input.value.trim();
    let problem = null;
    if (raw === "") problem = "Ô số " + (i + 1) + " đang trống.";
    else if (!/^\d+$/.test(raw)) problem = "Ô số " + (i + 1) + " phải là số nguyên (không có dấu phẩy, dấu chấm hay chữ).";
    else if (Number(raw) < 1 || Number(raw) > 20) problem = "Ô số " + (i + 1) + " phải từ 1 đến 20.";
    if (problem) { input.setAttribute("aria-invalid", "true"); input.focus(); return { error: problem }; }
    input.removeAttribute("aria-invalid");
    values.push(Number(raw));
  }
  return { values };
}
async function checkEquation() {
  const r = readEquation();
  if (r.error) { $("eq-msg").textContent = r.error; $("eq-msg").className = "notice warn"; return; }
  const id = Number($("eq-select").value);
  const { status, json } = await api("/api/equation", { id, coefficients: r.values });
  if (status !== 200) { $("eq-msg").textContent = json.error || "Không kiểm tra được."; $("eq-msg").className = "notice warn"; return; }
  $("eq-msg").textContent = json.message;
  const good = json.balanced && json.simplest;
  $("eq-msg").className = "notice " + (good ? "ok" : json.balanced ? "warn" : "bad");
  $("eq-next").hidden = !good;
  if (good) {
    const p = progress.recordEquation(id);
    celebrate(0.9); sound("ok"); refreshStars(p.isNew);
    announceBadges(p.fresh);
  } else sound("oops");
  speak(json.message);
}
async function revealEquation() {
  const id = Number($("eq-select").value);
  const { status, json } = await api("/api/equation", { id, reveal: true });
  if (status !== 200) { toast(json.error || "Không lấy được đáp án."); return; }
  json.coefficients.forEach((c, i) => { const input = $("eq-c" + i); input.value = String(c); input.removeAttribute("aria-invalid"); });
  updateCounts();
  $("eq-msg").textContent = "Đáp án: " + json.equation;
  $("eq-msg").className = "notice";
}
function nextEquation() {
  const sel = $("eq-select");
  sel.selectedIndex = (sel.selectedIndex + 1) % sel.options.length;
  buildEquationForm();
  $("eq-c0").focus();
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
  $("class-info").replaceChildren(document.createTextNode("Mã lớp của bạn"), el("strong", { textContent: t.code }), document.createTextNode("Học sinh nhập mã này. Dữ liệu tự xóa sau 24 giờ."));
  $("class-open").hidden = false;
  $("class-copy").hidden = false;
}
function showJoined(code) {
  $("class-leave").hidden = false;
  classMsg("Đang ở lớp " + code + ". Kết quả thử thách của nhóm sẽ gửi lên cho giáo viên (không kèm ảnh hay tên).", "good");
}
async function createClass() {
  const { status, json } = await api("/api/classroom", { action: "create", name: "Lớp học" });
  if (status !== 200) { toast(json.error || "Không tạo được lớp."); return; }
  const t = { code: json.code, key: json.teacher_key };
  setJson("session", CLASS_TEACHER_KEY, t);
  showTeacherInfo(t);
  toast("Đã tạo lớp. Hãy đọc mã " + t.code + " cho học sinh.");
  openDashboard();
}
async function copyCode() {
  const t = getJson("session", CLASS_TEACHER_KEY, null);
  if (!t) return;
  try { await navigator.clipboard.writeText(t.code); toast("Đã sao chép mã lớp " + t.code + "."); }
  catch (e) { toast("Không sao chép tự động được. Mã lớp: " + t.code); }
}
async function joinClass() {
  const code = $("class-code").value.trim().toUpperCase();
  if (code.length !== 6) { classMsg("Mã lớp gồm 6 kí tự.", "warn"); $("class-code").focus(); return; }
  const { status, json } = await api("/api/classroom", { action: "join", code });
  if (status !== 200) { classMsg(json.error || "Không vào được lớp.", "bad"); return; }
  setJson("session", CLASS_CODE_KEY, code);
  showJoined(code);
  toast("Đã vào lớp " + code + ".");
}
function leaveClass() {
  setJson("session", CLASS_CODE_KEY, null);
  $("class-leave").hidden = true;
  classMsg("Đã rời lớp.");
}
/* Giáo viên đã kết thúc lớp (hoặc lớp hết hạn): học sinh không cần xử lý gì, chỉ cần biết một lần là mình đã ra khỏi lớp */
function classEnded() {
  if (!getJson("session", CLASS_CODE_KEY, null)) return;
  setJson("session", CLASS_CODE_KEY, null);
  $("class-leave").hidden = true;
  classMsg("Lớp đã kết thúc hoặc hết hạn nên bạn đã ra khỏi lớp.", "warn");
  toast("Lớp đã kết thúc. Kết quả của bạn vẫn lưu trên máy này.");
}
async function sendToClass(row) {
  const code = getJson("session", CLASS_CODE_KEY, null);
  if (!code) return;
  try {
    const { status, json } = await api("/api/classroom", { action: "submit", code, row });
    if (status === 404) classEnded();
    else if (status !== 200) toast("Không gửi được kết quả lên lớp: " + (json.error || status));
  } catch (e) { toast("Mất kết nối: kết quả vẫn lưu trong trình duyệt."); }
}
async function sendActivity(type, extra) {
  const code = getJson("session", CLASS_CODE_KEY, null);
  if (!code) return;
  try {
    const { status } = await api("/api/classroom", { action: "activity", code, type, group: groupName(), ...extra });
    if (status === 404) classEnded();
  } catch (e) { /* không chặn người học */ }
}
async function refreshDashboard() {
  const t = getJson("session", CLASS_TEACHER_KEY, null);
  if (!t) return;
  const { status, json } = await api("/api/classroom", { action: "state", code: t.code, teacher_key: t.key });
  if (status === 404) {
    setJson("session", CLASS_TEACHER_KEY, null);
    $("class-info").hidden = true; $("class-open").hidden = true; $("class-copy").hidden = true;
    closeDashboard();
    toast("Lớp đã hết hạn hoặc đã bị xóa. Hãy tạo lớp mới.");
    return;
  }
  if (status !== 200) { $("class-sub").textContent = json.error || "Không tải được dữ liệu lớp."; return; }
  $("class-title").textContent = "Bảng điều khiển lớp " + json.code;
  const groups = json["nhóm"];
  $("class-sub").textContent = groups.length
    ? groups.length + " nhóm · " + json["nhóm kẹt"].length + " kẹt · " + json["nhóm rảnh"].length + " đang rảnh · " + json["tổng lượt"] + " lượt · tự làm mới mỗi 5 giây"
    : "Chưa có nhóm nào tham gia. Học sinh nhập mã lớp " + json.code + " ở thẻ Lớp học.";
  const head = ["Nhóm", "Bộ đề · tiến độ", "Đã xong", "Lượt", "Câu gần nhất", "Kết quả gần nhất", "Bỏ qua", "Gợi ý", "Cách đây"];
  $("class-table").tHead.replaceChildren(el("tr", {}, ...head.map((h) => el("th", { textContent: h }))));
  $("class-table").tBodies[0].replaceChildren(...groups.map((g) => {
    const state = g["kẹt"] ? " (kẹt)" : g["rảnh"] ? " (rảnh)" : g["đã kết thúc"] ? " (xong bộ đề)" : "";
    const cls = g["kẹt"] ? "stuck" : g["rảnh"] ? "idle" : (g["đã kết thúc"] || g["kết quả gần nhất"] === "ĐÚNG") ? "done" : "";
    const cells = [g["nhóm"] + state, [g["bộ đề"], g["tiến độ"]].filter(Boolean).join(" · ") || "-", String(g["đã xong"]), String(g["lượt"]),
      g["công thức"] || "-", g["kết quả gần nhất"] || "-", String(g["bỏ qua"]), String(g["gợi ý"]), g["giây trước"] + " giây"];
    return el("tr", { className: cls }, ...cells.map((c) => el("td", { textContent: c })));
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
  const fb = json["gợi ý chất"];
  if (fb && fb["đúng"] + fb["không phải"] > 0) {
    extra.append(el("h3", { textContent: "Gợi ý \"Có phải bạn muốn ghép …?\"" }),
      el("p", { className: "note", textContent: "Học sinh xác nhận đúng " + fb["đúng"] + "/" + (fb["đúng"] + fb["không phải"]) + " lần." }));
  }
}
async function openDashboard() {
  await refreshDashboard();
  if (!getJson("session", CLASS_TEACHER_KEY, null)) return;
  if (!$("class-dialog").open) $("class-dialog").showModal();
  clearInterval(dashTimer);
  dashTimer = setInterval(refreshDashboard, 5000);
}
function closeDashboard() { clearInterval(dashTimer); dashTimer = null; if ($("class-dialog").open) $("class-dialog").close(); }
async function endClass() {
  const t = getJson("session", CLASS_TEACHER_KEY, null);
  if (!t) return;
  if (!(await askConfirm("Kết thúc lớp và xóa toàn bộ dữ liệu lớp trên máy chủ? Việc này không hoàn tác được.", "Kết thúc lớp"))) return;
  const { status, json } = await api("/api/classroom", { action: "end", code: t.code, teacher_key: t.key });
  if (status !== 200 && status !== 404) { toast("Chưa kết thúc được lớp: " + (json.error || "lỗi máy chủ") + " Dữ liệu lớp vẫn còn, hãy thử lại."); return; }
  setJson("session", CLASS_TEACHER_KEY, null);
  $("class-info").hidden = true; $("class-open").hidden = true; $("class-copy").hidden = true;
  closeDashboard();
  toast("Đã kết thúc lớp.");
}

/* ------------------------------------------------------------------ nối sự kiện */
for (const v of VIEWS) $("tab-" + v).addEventListener("click", () => showView(v));
window.addEventListener("hashchange", () => { const h = location.hash.replace(/^#\//, ""); if (VIEWS.includes(h) && h !== currentView) showView(h, { updateHash: false }); });
$("btn-camera").addEventListener("click", toggleCamera);
$("camera-select").addEventListener("change", async () => { stopCamera(); await toggleCamera(); });
$("file-input").addEventListener("change", (e) => { loadFile(e.target.files[0]); e.target.value = ""; });
$("btn-check").addEventListener("click", () => { const img = grab(); if (img) analyze({ image: img }, true); });
$("btn-demo").addEventListener("click", () => analyze({ demo: $("scenario").value }, false));
$("sg-yes").addEventListener("click", () => answerSuggestion(true));
$("sg-no").addEventListener("click", () => answerSuggestion(false));
$("speak").addEventListener("change", savePrefs);
$("fx").addEventListener("change", savePrefs);
$("sfx").addEventListener("change", () => { savePrefs(); if ($("sfx").checked) sfx("ok"); });
$("group").addEventListener("change", savePrefs);
$("welcome-close").addEventListener("click", () => { $("welcome").hidden = true; setJson("local", HOWTO_KEY, true); });
$("howto-open").addEventListener("click", () => { setJson("local", HOWTO_KEY, false); $("welcome").hidden = !!challenge; showView("ghep"); });
$("ch-end").addEventListener("click", endChallenge);
$("ch-hint").addEventListener("click", hint);
$("ch-skip").addEventListener("click", skip);
$("eq-select").addEventListener("change", buildEquationForm);
$("eq-check").addEventListener("click", checkEquation);
$("eq-reveal").addEventListener("click", revealEquation);
$("eq-next").addEventListener("click", nextEquation);
$("class-create").addEventListener("click", createClass);
$("class-open").addEventListener("click", openDashboard);
$("class-copy").addEventListener("click", copyCode);
$("class-join").addEventListener("click", joinClass);
$("class-code").addEventListener("keydown", (e) => { if (e.key === "Enter") joinClass(); });
$("class-leave").addEventListener("click", leaveClass);
$("class-end").addEventListener("click", endClass);
$("class-close").addEventListener("click", closeDashboard);
$("class-dialog").addEventListener("close", () => { clearInterval(dashTimer); dashTimer = null; });
$("btn-report").addEventListener("click", showReport);
$("btn-csv").addEventListener("click", downloadCsv);
$("btn-close").addEventListener("click", () => $("report-dialog").close());
$("btn-clear").addEventListener("click", clearLogs);
$("code").addEventListener("change", () => { const s = store("session"); if (s) s.setItem(CODE_KEY, $("code").value.trim()); });
window.addEventListener("pagehide", stopCamera);
window.addEventListener("unhandledrejection", () => toast("Có lỗi không mong muốn. Hãy thử lại hoặc tải lại trang."));
window.__cv = { showView, startChallenge, progress };   // cho kịch bản kiểm thử giao diện (scripts/e2e_browser.js)
init();
