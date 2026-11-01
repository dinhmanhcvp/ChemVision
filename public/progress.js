/* Sao và huy hiệu: chỉ ghi nhận tiến bộ của chính học sinh, lưu trong trình duyệt. Không có bảng xếp hạng. */
const KEY = "cv_progress";

export const BADGES = [
  { id: "first", ico: "hexplus", name: "Mảnh ghép đầu tiên", how: "Ghép đúng một phân tử" },
  { id: "builder", ico: "molecule", name: "Thợ ghép", how: "Giải đúng 5 chất khác nhau" },
  { id: "deck", ico: "flag", name: "Về đích", how: "Hoàn thành một bộ đề" },
  { id: "balancer", ico: "scale", name: "Nhà cân bằng", how: "Cân bằng đúng một phương trình" },
  { id: "master", ico: "cap", name: "Bậc thầy phương trình", how: "Cân bằng đúng 10 phương trình" },
];

const empty = () => ({ stars: 0, solved: {}, equations: {}, decks: {}, badges: [], matches: 0 });

export function load() {
  try { return { ...empty(), ...(JSON.parse(localStorage.getItem(KEY)) || {}) }; } catch (e) { return empty(); }
}
function save(p) { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch (e) { /* trình duyệt chặn lưu */ } }

/* 3 sao nếu từ 9 điểm, 2 sao từ 6 điểm, còn lại 1 sao */
export const starsFor = (score) => (score >= 9 ? 3 : score >= 6 ? 2 : 1);

function award(p, id, fresh) {
  if (!p.badges.includes(id)) { p.badges.push(id); fresh.push(BADGES.find((b) => b.id === id)); }
}
function totalStars(p) {
  return Object.values(p.solved).reduce((a, b) => a + b, 0) + Object.keys(p.equations).length * 2;
}

/* Ghi nhận một câu giải đúng. Chỉ tính phần sao tăng thêm so với lần tốt nhất trước đó, nên làm lại để cải thiện chứ không "cày". */
export function recordSolved(key, score) {
  const p = load(), fresh = [];
  const stars = starsFor(score), before = p.solved[key] || 0;
  if (stars > before) p.solved[key] = stars;
  p.stars = totalStars(p);
  award(p, "first", fresh);
  if (Object.keys(p.solved).length >= 5) award(p, "builder", fresh);
  save(p);
  return { gained: Math.max(0, stars - before), stars: p.stars, fresh };
}
export function recordMatch() {
  const p = load(), fresh = [];
  p.matches = (p.matches || 0) + 1;
  award(p, "first", fresh);
  save(p);
  return { fresh };
}
export function recordDeckDone(deckName, solved, total) {
  const p = load(), fresh = [];
  p.decks[deckName] = Math.max(p.decks[deckName] || 0, solved);
  if (total && solved / total >= 0.5) award(p, "deck", fresh);
  save(p);
  return { fresh };
}
export function recordEquation(id) {
  const p = load(), fresh = [];
  const isNew = !p.equations[id];
  p.equations[id] = true;
  p.stars = totalStars(p);
  award(p, "balancer", fresh);
  if (Object.keys(p.equations).length >= 10) award(p, "master", fresh);
  save(p);
  return { isNew, stars: p.stars, fresh };
}
export function deckStats(deckName, keys) {
  const p = load();
  return { solved: keys.filter((k) => p.solved[k]).length, stars: keys.reduce((a, k) => a + (p.solved[k] || 0), 0), best: p.decks[deckName] || 0 };
}
export const totals = () => load().stars;
