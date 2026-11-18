/* Chất và nguyên tố người dùng tự thêm: lưu trong trình duyệt, gửi kèm mỗi lượt kiểm tra (xem chem_vision/custom.py). */
import { $, el, toast } from "/ui.js";

const KEY = "cv_custom";
const empty = () => ({ elements: [], substances: [] });

function load() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY));
    return { elements: Array.isArray(v?.elements) ? v.elements : [], substances: Array.isArray(v?.substances) ? v.substances : [] };
  } catch (e) { return empty(); }
}
function save(c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) { /* trình duyệt chặn lưu */ } }

/* gửi kèm yêu cầu kiểm tra; undefined khi chưa thêm gì */
export function getCustom() {
  const c = load();
  return c.elements.length || c.substances.length ? c : undefined;
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();

/* "1-3, 2-3" -> [[0,2],[1,2]]; trả về { atoms, bonds } hoặc { error } */
function readStructure() {
  const atoms = $("cs-atoms").value.trim().split(/[\s,]+/).filter(Boolean).map(cap);
  if (atoms.length < 2) return { error: "Cần ít nhất 2 nguyên tử." };
  const bonds = [];
  for (const part of $("cs-bonds").value.split(/[,;]+/).map((s) => s.trim()).filter(Boolean)) {
    const m = part.match(/^(\d+)\s*[-–]\s*(\d+)$/);
    if (!m) return { error: `Liên kết "${part}" phải viết dạng 1-2.` };
    const a = +m[1] - 1, b = +m[2] - 1;
    if (a === b || a < 0 || b < 0 || a >= atoms.length || b >= atoms.length) return { error: `Liên kết "${part}" nối nguyên tử không tồn tại.` };
    bonds.push([Math.min(a, b), Math.max(a, b)]);
  }
  return { atoms, bonds };
}

function preview() {
  const s = readStructure();
  const text = s.error ? (($("cs-atoms").value || $("cs-bonds").value) ? s.error : "")
    : `${s.atoms.length} nguyên tử, ${new Set(s.bonds.map(String)).size} liên kết: ` +
      (s.bonds.map(([a, b]) => `${s.atoms[a]}${a + 1}–${s.atoms[b]}${b + 1}`).join(", ") || "chưa có liên kết");
  $("cs-preview").textContent = text;
}

let api = null;

function render() {
  const c = load();
  const list = $("custom-list");
  list.replaceChildren();
  const row = (text, remove) => list.append(el("li", {}, el("span", { textContent: text }),
    el("button", { type: "button", className: "btn ghost small", textContent: "Xóa", onclick: remove })));
  c.elements.forEach((e, i) => row(`Nguyên tố ${e.symbol}: ${e.name}, nguyên tử khối ${e.mass}`, () => { c.elements.splice(i, 1); save(c); render(); }));
  c.substances.forEach((s, i) => row(`${s.formula}: ${s.name} (${s.atoms.length} nguyên tử)`, () => { c.substances.splice(i, 1); save(c); render(); }));
}

async function commit(kind, item) {
  const c = load();
  c[kind].push(item);
  const { status, json } = await api("/api/custom", { custom: c });     // máy chủ kiểm tra trước khi lưu: dữ liệu sai không làm hỏng các lượt kiểm tra sau
  if (status !== 200 || !json.ok) { $("custom-error").textContent = json.error || "Không thêm được."; return false; }
  $("custom-error").textContent = "";
  save(c);
  render();
  toast("Đã thêm. Dùng được ngay khi kiểm tra thẻ.");
  return true;
}

async function addElement() {
  const item = { symbol: cap($("ce-symbol").value.trim()), name: $("ce-name").value.trim(), mass: Number($("ce-mass").value) };
  if (await commit("elements", item)) for (const id of ["ce-symbol", "ce-name", "ce-mass"]) $(id).value = "";
}

async function addSubstance() {
  const s = readStructure();
  if (s.error) { $("custom-error").textContent = s.error; return; }
  const item = { formula: $("cs-formula").value.trim(), name: $("cs-name").value.trim(), atoms: s.atoms, bonds: s.bonds };
  if (!(await commit("substances", item))) return;
  for (const id of ["cs-formula", "cs-name", "cs-atoms", "cs-bonds"]) $(id).value = "";
  preview();
}

export function initCustom(apiFn) {
  api = apiFn;
  $("ce-add").addEventListener("click", addElement);
  $("cs-add").addEventListener("click", addSubstance);
  $("cs-atoms").addEventListener("input", preview);
  $("cs-bonds").addEventListener("input", preview);
  render();
}
