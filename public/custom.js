/* Nguyên tố người dùng tự thêm: nhận một mã vuông, đặt tên là xong (hóa trị, nguyên tử khối tra từ bảng).
   Lưu trong trình duyệt, gửi kèm mỗi lượt kiểm tra (xem chem_vision/custom.py). */
import { $, el, toast } from "/ui.js";

const KEY = "cv_custom";
const FIRST_MARKER = 22, MARKER_COUNT = 50;      // phải khớp len(CARD_ELEMENTS) và DICT_ID_COUNT ở máy chủ
let api = null;

function load() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY));
    return { elements: Array.isArray(v?.elements) ? v.elements : [] };
  } catch (e) { return { elements: [] }; }
}
function save(c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch (e) { /* trình duyệt chặn lưu */ } }

const named = (c) => c.elements.filter((e) => e.name).map(({ marker, name, symbol, valence }) => ({ marker, name, symbol, valence }));

/* gửi kèm yêu cầu kiểm tra; undefined khi chưa có nguyên tố nào được đặt tên */
export function getCustom() {
  const list = named(load());
  return list.length ? { elements: list } : undefined;
}

const ROMAN = ["0", "I", "II", "III", "IV", "V", "VI", "VII", "VIII"];

function render() {
  const c = load();
  const list = $("custom-list");
  list.replaceChildren();
  for (const e of c.elements) {
    const img = el("img", { src: "data:image/png;base64," + (e.png || ""), alt: `Mã vuông số ${e.marker}`, width: 84, height: 84 });
    const head = el("strong", { textContent: e.name ? `Mã ${e.marker} = ${e.symbol} (${e.name})` : `Mã ${e.marker}: chưa gán nhãn` });
    const body = el("div", {}, head);
    if (e.name) {
      body.append(el("div", { className: "note", textContent: "Hóa trị " + e.valence.map((v) => ROMAN[v]).join(", ") }));
    } else {
      const name = el("input", { type: "text", maxLength: 30, placeholder: "Tên nguyên tố (bạch kim)", ariaLabel: `Tên nguyên tố cho mã ${e.marker}` });
      const symbol = el("input", { type: "text", maxLength: 3, placeholder: "Kí hiệu (Pt)", ariaLabel: "Kí hiệu nguyên tố", hidden: true });
      const valence = el("input", { type: "number", min: 0, max: 8, placeholder: "Hóa trị", ariaLabel: "Hóa trị", hidden: true });
      body.append(el("div", { className: "row" }, name, symbol, valence,
        el("button", { type: "button", className: "btn small", textContent: "Lưu tên", onclick: () => saveName(e.marker, name, symbol, valence) })));
    }
    const actions = el("div", { className: "row" },
      el("a", { className: "btn ghost small", href: img.src, download: `ma-${e.marker}.png`, textContent: "Tải mã" }),
      el("button", { type: "button", className: "btn ghost small", textContent: "Xóa", onclick: () => remove(e.marker) }));
    list.append(el("li", {}, img, body, actions));
  }
}

function remove(marker) {
  const c = load();
  c.elements = c.elements.filter((e) => e.marker !== marker);
  save(c);
  render();
}

/* nhận mã chưa dùng kế tiếp và ảnh mã từ máy chủ */
async function addDraft() {
  const c = load();
  const marker = Array.from({ length: MARKER_COUNT - FIRST_MARKER }, (_, i) => FIRST_MARKER + i).find((m) => !c.elements.some((e) => e.marker === m));
  if (marker === undefined) { $("custom-error").textContent = "Đã hết mã. Hãy xóa bớt nguyên tố cũ."; return; }
  const { status, json } = await api("/api/custom", { marker });
  if (status !== 200 || !json.ok) { $("custom-error").textContent = json.error || "Không lấy được mã."; return; }
  $("custom-error").textContent = "";
  c.elements.push({ marker, png: json.image });
  save(c);
  render();
}

/* máy chủ tra tên trong bảng nguyên tố; chưa biết thì hiện thêm ô kí hiệu và hóa trị */
async function saveName(marker, nameBox, symbolBox, valenceBox) {
  const c = load();
  const e = c.elements.find((x) => x.marker === marker);
  const trial = { marker, name: nameBox.value.trim() };
  if (!symbolBox.hidden) { trial.symbol = symbolBox.value.trim(); trial.valence = valenceBox.value === "" ? undefined : Number(valenceBox.value); }
  const { status, json } = await api("/api/custom", { custom: { elements: [...named(c).filter((x) => x.marker !== marker), trial] } });
  if (status !== 200 || !json.ok) {
    $("custom-error").textContent = json.error || "Không lưu được.";
    if (json.need) { symbolBox.hidden = false; valenceBox.hidden = false; }
    return;
  }
  const got = json.elements.find((x) => x.marker === marker);
  Object.assign(e, { name: trial.name, symbol: got.symbol, valence: got.valence });
  $("custom-error").textContent = "";
  save(c);
  render();
  toast(`Mã ${marker} là ${got.symbol}. Dùng được ngay khi kiểm tra.`);
}

export function initCustom(apiFn) {
  api = apiFn;
  $("ce-new").addEventListener("click", addDraft);
  render();
}
