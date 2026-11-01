/* Phần trình bày dùng chung: không chứa logic nghiệp vụ. Quy tắc: docs/ngon-ngu-thiet-ke.md */
export const $ = (id) => document.getElementById(id);

export function el(tag, props, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props || {});
  for (const c of children) node.append(c);
  return node;
}

/* biểu tượng SVG (mặt nạ CSS, xem .ic trong style.css): cùng màu chữ, giống nhau trên mọi hệ điều hành, không dùng emoji */
export const icon = (name) => el("i", { className: "ic ic-" + name, ariaHidden: "true" });

/* H2O -> H₂O bằng thẻ <sub>; chữ số đứng sau chữ cái hoặc dấu ngoặc đóng mới là chỉ số dưới (hệ số đứng đầu giữ nguyên) */
export function formulaNode(formula) {
  const span = el("span", { className: "formula" });
  let prev = "";
  for (const ch of String(formula)) {
    if (/\d/.test(ch) && /[A-Za-z)]/.test(prev)) span.append(el("sub", { textContent: ch }));
    else span.append(document.createTextNode(ch));
    prev = ch;
  }
  return span;
}

/* thẻ nguyên tố: lục giác tô màu CPK (cùng màu và cùng hình với thẻ in) */
export function elementChip(symbol, colors) {
  const chip = el("span", { className: "chip el", textContent: symbol });
  const c = colors && colors[symbol];
  if (c) chip.style.setProperty("--c", c);
  return chip;
}

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* con dấu kết quả: mỗi trạng thái một hình riêng (dấu chờ, mũi tên, tích, xoay lại, chéo), không chỉ khác màu */
const MOODS = ["wait", "happy", "cheer", "think", "oops"];
const SEALS = { wait: "wait", happy: "start", cheer: "ok", think: "close", oops: "bad" };
export function setMood(name) {
  const img = $("seal");
  if (!img || !MOODS.includes(name)) return;
  img.src = "/img/seal-" + SEALS[name] + ".svg";
  img.classList.remove("stamp");
  if (name !== "wait") { void img.offsetWidth; img.classList.add("stamp"); }     // đóng dấu mỗi lần có kết quả mới
}

/* ---------- hiệu ứng khi đúng: mảnh lục giác theo màu nguyên tố, ngắn (1,4 giây), tắt được, tự tắt khi bật "giảm chuyển động" ---------- */
let confettiRun = 0;
export function confetti(strength = 1) {
  if (reducedMotion()) return;
  const canvas = $("confetti");
  if (!canvas || !canvas.getContext) return;
  const dpr = window.devicePixelRatio || 1;
  canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  const colors = ["#c8341e", "#2f5fd0", "#f2cf3d", "#1d9a5a", "#e8e2d2", "#1d1c19"];
  const n = Math.round(60 * strength);
  const parts = Array.from({ length: n }, () => ({
    x: innerWidth / 2 + (Math.random() - 0.5) * 120, y: innerHeight * 0.55,
    vx: (Math.random() - 0.5) * 11, vy: -Math.random() * 13 - 4, g: 0.38 + Math.random() * 0.12,
    s: 7 + Math.random() * 7, r: Math.random() * 6, vr: (Math.random() - 0.5) * 0.3, c: colors[(Math.random() * colors.length) | 0],
  }));
  const run = ++confettiRun;
  const t0 = performance.now();
  (function frame(now) {
    if (run !== confettiRun) return;
    const t = now - t0;
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    for (const p of parts) {
      p.vy += p.g; p.x += p.vx; p.y += p.vy; p.r += p.vr;
      ctx.save(); ctx.globalAlpha = Math.max(0, 1 - t / 1400); ctx.translate(p.x, p.y); ctx.rotate(p.r);
      ctx.fillStyle = p.c; ctx.strokeStyle = "rgba(29, 28, 25, .55)"; ctx.lineWidth = 1;
      ctx.beginPath();
      for (let k = 0; k < 6; k++) { const a = Math.PI / 3 * k - Math.PI / 2; ctx.lineTo(Math.cos(a) * p.s, Math.sin(a) * p.s); }
      ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.restore();
    }
    if (t < 1400) requestAnimationFrame(frame); else ctx.clearRect(0, 0, innerWidth, innerHeight);
  })(t0);
}

/* ---------- âm thanh "ting" bằng Web Audio, không cần tệp âm thanh ---------- */
let audio = null;
export function sfx(kind) {
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    const notes = { ok: [660, 880], star: [784, 1046], oops: [300, 240], badge: [523, 659, 784] }[kind] || [660];
    notes.forEach((f, i) => {
      const o = audio.createOscillator(), g = audio.createGain();
      o.type = kind === "oops" ? "triangle" : "sine"; o.frequency.value = f;
      const t = audio.currentTime + i * 0.11;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.18, t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.28);
      o.connect(g); g.connect(audio.destination); o.start(t); o.stop(t + 0.3);
    });
  } catch (e) { /* trình duyệt không cho phát âm thanh: bỏ qua */ }
}

/* ---------- thông báo ngắn ---------- */
let toastTimer = null;
export function toast(text, ms = 3600) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, ms);
}
