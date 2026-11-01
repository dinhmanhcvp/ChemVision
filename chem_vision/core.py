"""Lõi CHEM VISION: làm sạch dữ liệu AI, đối sánh cấu trúc phân tử, gợi ý chất.

Nguyên tắc giữ nguyên từ báo cáo: AI chỉ "nhìn" (trả danh sách thẻ và cặp thẻ chạm
cạnh), còn phần mềm "kết luận" bằng đối sánh đồ thị liên kết.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass, field, replace

from .curriculum import ATOMIC_MASS, ELEMENT_NAMES, format_mass, molecular_mass

MIN_CONFIDENCE = 0.6
MAX_D = 3            # tổng thẻ thiếu + thừa tối đa của một gợi ý
MAX_EXTRA = 1        # số thẻ thừa tối đa
MIN_OVERLAP = 0.5    # tỉ lệ thẻ của cụm trùng với chất gợi ý
MAX_SUGGESTIONS = 3

ELEMENTS = set(
    "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn "
    "Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce "
    "Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn "
    "Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl "
    "Mc Lv Ts Og".split()
)


# --------------------------------------------------------------------------- đồ thị
@dataclass
class Graph:
    labels: list[str]
    adj: list[set[int]]

    @classmethod
    def from_edges(cls, labels, edges):
        adj = [set() for _ in labels]
        for a, b in edges:
            adj[a].add(b)
            adj[b].add(a)
        return cls(list(labels), adj)

    @property
    def edges(self):
        return [(i, j) for i in range(len(self.labels)) for j in self.adj[i] if i < j]

    def composition(self) -> Counter:
        return Counter(self.labels)

    def signature(self):
        return tuple(sorted(self.composition().items()))

    def bond_types(self) -> Counter:
        return Counter(tuple(sorted((self.labels[i], self.labels[j]))) for i, j in self.edges)


def _colors(g: Graph, rounds: int = 3) -> list[str]:
    col = list(g.labels)
    for _ in range(rounds):
        col = [
            hashlib.md5((col[i] + "|" + ",".join(sorted(col[j] for j in g.adj[i]))).encode()).hexdigest()[:12]
            for i in range(len(col))
        ]
    return col


def is_isomorphic(a: Graph, b: Graph) -> bool:
    """Đẳng cấu có nhãn. Lọc nhanh bằng thành phần và màu (Weisfeiler-Lehman) rồi quay lui."""
    if len(a.labels) != len(b.labels) or a.signature() != b.signature():
        return False
    ca, cb = _colors(a), _colors(b)
    if sorted(ca) != sorted(cb):
        return False
    n = len(a.labels)
    order = sorted(range(n), key=lambda i: (-len(a.adj[i]), a.labels[i]))
    mapping: dict[int, int] = {}
    used: set[int] = set()

    def place(k: int) -> bool:
        if k == n:
            return True
        u = order[k]
        for v in range(n):
            if v in used or ca[u] != cb[v]:
                continue
            if any(w in mapping and mapping[w] not in b.adj[v] for w in a.adj[u]):
                continue
            if sum(1 for w in mapping if mapping[w] in b.adj[v]) != sum(1 for w in a.adj[u] if w in mapping):
                continue
            mapping[u] = v
            used.add(v)
            if place(k + 1):
                return True
            del mapping[u]
            used.discard(v)
        return False

    return place(0)


def is_subgraph(small: Graph, big: Graph) -> bool:
    """`small` có nằm trong `big` không (mỗi liên kết của small có trong big, cùng nhãn)."""
    n, m = len(small.labels), len(big.labels)
    if n > m:
        return False
    order, seen = [], set()
    for s in sorted(range(n), key=lambda i: -len(small.adj[i])):
        stack = [s]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            order.append(u)
            stack.extend(sorted(small.adj[u] - seen, key=lambda i: -len(small.adj[i])))
    mapping: dict[int, int] = {}
    used: set[int] = set()

    def place(k: int) -> bool:
        if k == n:
            return True
        u = order[k]
        for v in range(m):
            if v in used or small.labels[u] != big.labels[v] or len(small.adj[u]) > len(big.adj[v]):
                continue
            if any(w in mapping and mapping[w] not in big.adj[v] for w in small.adj[u]):
                continue
            mapping[u] = v
            used.add(v)
            if place(k + 1):
                return True
            del mapping[u]
            used.discard(v)
        return False

    return place(0)


# --------------------------------------------------------------------------- cơ sở dữ liệu
@dataclass(frozen=True)
class Substance:
    key: str
    formula: str
    name: str
    group: str
    graph: Graph
    grade: int = 7          # lớp học chất này (6 đến 9)
    ionic: bool = False     # hợp chất ion: quy ước ghép cặp, thực tế là mạng tinh thể


def _s(key, formula, name, group, atoms, bonds):
    return Substance(key, formula, name, group, Graph.from_edges(atoms.split(), bonds))


def _star(centre, n):  # tâm nối với n nguyên tử còn lại
    return [(centre, i) for i in range(1, n + 1)]


DATABASE: tuple[Substance, ...] = (
    _s("H2", "H2", "hiđro", "đơn chất", "H H", [(0, 1)]),
    _s("O2", "O2", "oxi", "đơn chất", "O O", [(0, 1)]),
    _s("N2", "N2", "nitơ", "đơn chất", "N N", [(0, 1)]),
    _s("H2O", "H2O", "nước", "oxit", "O H H", _star(0, 2)),
    _s("CO2", "CO2", "cacbon đioxit", "oxit", "C O O", _star(0, 2)),
    _s("CO", "CO", "cacbon monooxit", "oxit", "C O", [(0, 1)]),
    _s("SO2", "SO2", "lưu huỳnh đioxit", "oxit", "S O O", _star(0, 2)),
    _s("SO3", "SO3", "lưu huỳnh trioxit", "oxit", "S O O O", _star(0, 3)),
    _s("NO", "NO", "nitơ monooxit", "oxit", "N O", [(0, 1)]),
    _s("NO2", "NO2", "nitơ đioxit", "oxit", "N O O", _star(0, 2)),
    _s("CaO", "CaO", "canxi oxit", "oxit", "Ca O", [(0, 1)]),
    _s("MgO", "MgO", "magie oxit", "oxit", "Mg O", [(0, 1)]),
    _s("CuO", "CuO", "đồng(II) oxit", "oxit", "Cu O", [(0, 1)]),
    _s("ZnO", "ZnO", "kẽm oxit", "oxit", "Zn O", [(0, 1)]),
    _s("FeO", "FeO", "sắt(II) oxit", "oxit", "Fe O", [(0, 1)]),
    _s("HCl", "HCl", "axit clohiđric", "axit", "H Cl", [(0, 1)]),
    _s("HNO3", "HNO3", "axit nitric", "axit", "N O O O H", _star(0, 3) + [(3, 4)]),
    _s("H2SO4", "H2SO4", "axit sunfuric", "axit", "S O O O O H H", _star(0, 4) + [(3, 5), (4, 6)]),
    _s("H3PO4", "H3PO4", "axit photphoric", "axit", "P O O O O H H H", _star(0, 4) + [(2, 5), (3, 6), (4, 7)]),
    _s("NaOH", "NaOH", "natri hiđroxit", "bazơ", "Na O H", [(0, 1), (1, 2)]),
    _s("KOH", "KOH", "kali hiđroxit", "bazơ", "K O H", [(0, 1), (1, 2)]),
    _s("Ca(OH)2", "Ca(OH)2", "canxi hiđroxit", "bazơ", "Ca O O H H", [(0, 1), (0, 2), (1, 3), (2, 4)]),
    _s("NaCl", "NaCl", "natri clorua", "muối", "Na Cl", [(0, 1)]),
    _s("Na2CO3", "Na2CO3", "natri cacbonat", "muối", "C O O O Na Na", _star(0, 3) + [(1, 4), (2, 5)]),
    _s("NaHCO3", "NaHCO3", "natri hiđrocacbonat", "muối", "C O O O Na H", _star(0, 3) + [(1, 4), (2, 5)]),
    _s("CaCO3", "CaCO3", "canxi cacbonat", "muối", "C O O O Ca", _star(0, 3) + [(1, 4), (2, 4)]),
    _s("NH3", "NH3", "amoniac", "hợp chất", "N H H H", _star(0, 3)),
    _s("CH4", "CH4", "metan", "hợp chất", "C H H H H", _star(0, 4)),
    _s("C2H5OH", "C2H5OH", "etanol", "hợp chất", "C C H H H H H O H",
       [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5), (1, 6), (1, 7), (7, 8)]),
    # bổ sung so với phiên bản đầu: đồng phân của etanol và một chất có liên kết O–O
    _s("CH3OCH3", "CH3OCH3", "đimetyl ete", "hợp chất", "C C O H H H H H H",
       [(0, 2), (1, 2), (0, 3), (0, 4), (0, 5), (1, 6), (1, 7), (1, 8)]),
    _s("H2O2", "H2O2", "hiđro peoxit", "hợp chất", "O O H H", [(0, 1), (0, 2), (1, 3)]),
)

_BASE_COUNT = len(DATABASE)

def _more():
    S = _s
    st = _star
    ph = [(0, 1), (0, 2), (1, 3), (2, 4)]                       # M(OH)2
    m3 = [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (3, 6)]        # M(OH)3
    sulfate = st(0, 4)
    rows = [
        # ---- lớp 8: oxit
        S("Na2O", "Na2O", "natri oxit", "oxit", "Na Na O", [(0, 2), (1, 2)]),
        S("K2O", "K2O", "kali oxit", "oxit", "K K O", [(0, 2), (1, 2)]),
        S("Fe2O3", "Fe2O3", "sắt(III) oxit", "oxit", "Fe Fe O O O", [(0, 2), (1, 2), (0, 3), (1, 4)]),
        S("Al2O3", "Al2O3", "nhôm oxit", "oxit", "Al Al O O O", [(0, 2), (1, 2), (0, 3), (1, 4)]),
        S("P2O5", "P2O5", "điphotpho pentaoxit", "oxit", "P P O O O O O", [(0, 2), (1, 2), (0, 3), (0, 4), (1, 5), (1, 6)]),
        # ---- lớp 8: axit, bazơ
        S("H2S", "H2S", "hiđro sunfua", "axit", "S H H", st(0, 2)),
        S("H2CO3", "H2CO3", "axit cacbonic", "axit", "C O O O H H", st(0, 3) + [(1, 4), (2, 5)]),
        S("Mg(OH)2", "Mg(OH)2", "magie hiđroxit", "bazơ", "Mg O O H H", ph),
        S("Cu(OH)2", "Cu(OH)2", "đồng(II) hiđroxit", "bazơ", "Cu O O H H", ph),
        S("Ba(OH)2", "Ba(OH)2", "bari hiđroxit", "bazơ", "Ba O O H H", ph),
        S("Fe(OH)3", "Fe(OH)3", "sắt(III) hiđroxit", "bazơ", "Fe O O O H H H", m3),
        S("Al(OH)3", "Al(OH)3", "nhôm hiđroxit", "bazơ", "Al O O O H H H", m3),
        # ---- lớp 8: muối, phân bón
        S("KCl", "KCl", "kali clorua", "muối", "K Cl", [(0, 1)]),
        S("CaCl2", "CaCl2", "canxi clorua", "muối", "Ca Cl Cl", st(0, 2)),
        S("MgCl2", "MgCl2", "magie clorua", "muối", "Mg Cl Cl", st(0, 2)),
        S("ZnCl2", "ZnCl2", "kẽm clorua", "muối", "Zn Cl Cl", st(0, 2)),
        S("AlCl3", "AlCl3", "nhôm clorua", "muối", "Al Cl Cl Cl", st(0, 3)),
        S("FeCl2", "FeCl2", "sắt(II) clorua", "muối", "Fe Cl Cl", st(0, 2)),
        S("FeCl3", "FeCl3", "sắt(III) clorua", "muối", "Fe Cl Cl Cl", st(0, 3)),
        S("AgCl", "AgCl", "bạc clorua", "muối", "Ag Cl", [(0, 1)]),
        S("Na2SO4", "Na2SO4", "natri sunfat", "muối", "S O O O O Na Na", sulfate + [(1, 5), (2, 6)]),
        S("CuSO4", "CuSO4", "đồng(II) sunfat", "muối", "S O O O O Cu", sulfate + [(1, 5), (2, 5)]),
        S("BaSO4", "BaSO4", "bari sunfat", "muối", "S O O O O Ba", sulfate + [(1, 5), (2, 5)]),
        S("CaSO4", "CaSO4", "canxi sunfat", "muối", "S O O O O Ca", sulfate + [(1, 5), (2, 5)]),
        S("KNO3", "KNO3", "kali nitrat", "muối", "N O O O K", st(0, 3) + [(1, 4)]),
        S("NaNO3", "NaNO3", "natri nitrat", "muối", "N O O O Na", st(0, 3) + [(1, 4)]),
        S("AgNO3", "AgNO3", "bạc nitrat", "muối", "N O O O Ag", st(0, 3) + [(1, 4)]),
        S("CO(NH2)2", "CO(NH2)2", "urê", "hợp chất", "C O N N H H H H",
          [(0, 1), (0, 2), (0, 3), (2, 4), (2, 5), (3, 6), (3, 7)]),
        S("Cl2", "Cl2", "clo", "đơn chất", "Cl Cl", [(0, 1)]),
        S("O3", "O3", "ozon", "đơn chất", "O O O", [(0, 1), (1, 2)]),
        # ---- lớp 9: hợp chất hữu cơ
        S("C2H6", "C2H6", "etan", "hiđrocacbon", "C C H H H H H H", [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5), (1, 6), (1, 7)]),
        S("C2H4", "C2H4", "etilen", "hiđrocacbon", "C C H H H H", [(0, 1), (0, 2), (0, 3), (1, 4), (1, 5)]),
        S("C2H2", "C2H2", "axetilen", "hiđrocacbon", "C C H H", [(0, 1), (0, 2), (1, 3)]),
        S("C3H8", "C3H8", "propan", "hiđrocacbon", "C C C H H H H H H H H",
          [(0, 1), (1, 2), (0, 3), (0, 4), (0, 5), (1, 6), (1, 7), (2, 8), (2, 9), (2, 10)]),
        S("C4H10", "C4H10", "butan", "hiđrocacbon", "C C C C H H H H H H H H H H",
          [(0, 1), (1, 2), (2, 3), (0, 4), (0, 5), (0, 6), (1, 7), (1, 8), (2, 9), (2, 10), (3, 11), (3, 12), (3, 13)]),
        S("C4H10-iso", "C4H10", "isobutan", "hiđrocacbon", "C C C C H H H H H H H H H H",
          [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5), (1, 6), (1, 7), (2, 8), (2, 9), (2, 10), (3, 11), (3, 12), (3, 13)]),
        S("C6H6", "C6H6", "benzen", "hiđrocacbon", "C C C C C C H H H H H H",
          [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)] + [(i, 6 + i) for i in range(6)]),
        S("CH3OH", "CH3OH", "metanol", "dẫn xuất", "C O H H H H", [(0, 1), (0, 2), (0, 3), (0, 4), (1, 5)]),
        S("CH3COOH", "CH3COOH", "axit axetic", "dẫn xuất", "C C O O H H H H",
          [(0, 1), (1, 2), (1, 3), (3, 4), (0, 5), (0, 6), (0, 7)]),
    ]
    return tuple(rows)


_IONIC = {"CaO", "MgO", "CuO", "ZnO", "FeO", "NaOH", "KOH", "Ca(OH)2", "NaCl", "Na2CO3", "NaHCO3", "CaCO3",
          "Na2O", "K2O", "Fe2O3", "Al2O3", "Mg(OH)2", "Cu(OH)2", "Ba(OH)2", "Fe(OH)3", "Al(OH)3", "KCl", "CaCl2",
          "MgCl2", "ZnCl2", "AlCl3", "FeCl2", "FeCl3", "AgCl", "Na2SO4", "CuSO4", "BaSO4", "CaSO4", "KNO3", "NaNO3",
          "AgNO3"}
_GRADE = {"C2H5OH": 9, "CH3OCH3": 9, "H2O2": 8}
_GRADE_BY_GROUP = {"hiđrocacbon": 9, "dẫn xuất": 9}
DATABASE = tuple(
    replace(s, ionic=s.key in _IONIC,
            grade=_GRADE.get(s.key, _GRADE_BY_GROUP.get(s.group, 8 if i >= _BASE_COUNT else 7)))
    for i, s in enumerate(DATABASE + _more())
)

BY_KEY = {s.key: s for s in DATABASE}
BY_SIGNATURE: dict[tuple, list[Substance]] = {}
for _sub in DATABASE:
    BY_SIGNATURE.setdefault(_sub.graph.signature(), []).append(_sub)

# số thẻ tối đa một thẻ nguyên tố có thể chạm, suy ra từ cơ sở dữ liệu
MAX_DEGREE: dict[str, int] = {}
for _sub in DATABASE:
    for _i, _l in enumerate(_sub.graph.labels):
        MAX_DEGREE[_l] = max(MAX_DEGREE.get(_l, 0), len(_sub.graph.adj[_i]))


# --------------------------------------------------------------------------- làm sạch dữ liệu AI
@dataclass
class Card:
    id: object
    symbol: str
    confidence: float


@dataclass
class Cleaned:
    cards: dict
    edges: set
    problems: list = field(default_factory=list)   # buộc chụp lại
    warnings: list = field(default_factory=list)   # chỉ lưu ý

    @property
    def recapture(self) -> bool:
        return bool(self.problems)


def extract_json(raw) -> dict | None:
    """Lấy JSON từ câu trả lời của AI, kể cả khi bọc trong ```json ... ``` hoặc kèm lời dẫn."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    text = re.sub(r"```(?:json)?", "", raw)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def normalize_symbol(raw) -> str | None:
    s = re.sub(r"[^0-9A-Za-z]", "", str(raw or ""))
    if s == "0":
        s = "O"          # số không bị đọc nhầm cho chữ O
    if not s.isalpha():
        return None
    s = s[0].upper() + s[1:].lower()
    return s if s in ELEMENTS else None


def _norm_id(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return str(x)


def _norm_conf(x) -> float | None:
    try:
        c = float(x)
    except (TypeError, ValueError):
        return None
    if 1 < c <= 100:
        c /= 100
    return min(max(c, 0.0), 1.0)


def _fmt(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def clean_molecule(raw) -> Cleaned:
    data = extract_json(raw)
    if data is None:
        return Cleaned({}, set(), problems=["không đọc được kết quả nhận diện từ AI"])
    out = Cleaned({}, set())
    for msg in data.get("quality_problems") or []:        # ảnh quá tối, mờ, lóa: do phần kiểm tra chất lượng ảnh báo
        out.problems.append(str(msg).rstrip("."))
    for item in data.get("cards") or []:
        if not isinstance(item, dict):
            continue
        cid = _norm_id(item.get("id"))
        if cid in out.cards:
            out.warnings.append(f"bỏ thẻ trùng id {cid}")
            continue
        sym = normalize_symbol(item.get("symbol"))
        conf = _norm_conf(item.get("confidence"))
        if conf is None:
            conf = 1.0
            out.warnings.append(f"thẻ {cid} thiếu độ tin cậy")
        if sym is None:
            out.problems.append(f"thẻ {cid} có kí hiệu không hợp lệ ({item.get('symbol')!r})")
            continue
        out.cards[cid] = Card(cid, sym, conf)
        if conf < MIN_CONFIDENCE:
            out.problems.append(
                f"thẻ {cid} ({sym}) nhận diện chưa chắc chắn (độ tin cậy {_fmt(conf)})")
    for item in data.get("connections") or []:
        if isinstance(item, dict):
            pair = (item.get("a"), item.get("b"))
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            pair = tuple(item)
        else:
            continue
        a, b = _norm_id(pair[0]), _norm_id(pair[1])
        if a == b or a not in out.cards or b not in out.cards:
            continue
        out.edges.add(frozenset((a, b)))
    return out


def components(cleaned: Cleaned) -> list[tuple[list, Graph]]:
    """Tách các thẻ thành cụm liền nhau; mỗi cụm là một phân tử."""
    adj = {cid: set() for cid in cleaned.cards}
    for e in cleaned.edges:
        a, b = tuple(e)
        adj[a].add(b)
        adj[b].add(a)
    seen, result = set(), []
    for start in cleaned.cards:
        if start in seen:
            continue
        stack, ids = [start], []
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            ids.append(u)
            stack.extend(adj[u] - seen)
        index = {cid: i for i, cid in enumerate(ids)}
        labels = [cleaned.cards[c].symbol for c in ids]
        edges = [(index[a], index[b]) for a, b in (tuple(e) for e in cleaned.edges) if a in index]
        result.append((ids, Graph.from_edges(labels, edges)))
    return result


# --------------------------------------------------------------------------- đối sánh
@dataclass
class Suggestion:
    substance: Substance
    missing: Counter
    extra: Counter
    is_subgraph: bool

    @property
    def d(self) -> int:
        return sum(self.missing.values()) + sum(self.extra.values())


@dataclass
class ClusterResult:
    kind: str                       # MATCH | WRONG_BONDS | SUGGEST | UNKNOWN
    graph: Graph
    substance: Substance | None = None
    same_composition: list = field(default_factory=list)
    extra_bonds: Counter = field(default_factory=Counter)
    missing_bonds: Counter = field(default_factory=Counter)
    suggestions: list = field(default_factory=list)
    valence_warnings: list = field(default_factory=list)


def _bond_diff(g: Graph, ref: Graph):
    a, b = g.bond_types(), ref.bond_types()
    return a - b, b - a


def valence_warnings(g: Graph) -> list[str]:
    out = []
    for i, label in enumerate(g.labels):
        limit = MAX_DEGREE.get(label)
        if limit is not None and len(g.adj[i]) > limit:
            out.append(f"thẻ {label} đang chạm {len(g.adj[i])} thẻ, nhưng thẻ {label} thường chỉ nối tối đa {limit} thẻ")
    return out


def suggest(g: Graph, db=DATABASE) -> list[Suggestion]:
    comp, found = g.composition(), []
    for s in db:
        sc = s.graph.composition()
        missing, extra = sc - comp, comp - sc
        sug = Suggestion(s, missing, extra, False)
        overlap = sum((comp & sc).values())
        if sug.d > MAX_D or sum(extra.values()) > MAX_EXTRA or overlap < MIN_OVERLAP * len(g.labels):
            continue
        sug.is_subgraph = is_subgraph(g, s.graph)
        found.append((sug, overlap))
    if not found:
        return []
    best = min(s.d for s, _ in found)
    shared_bonds = lambda s: sum((g.bond_types() & s.substance.graph.bond_types()).values())
    found = [(s, o) for s, o in found if s.d <= best + 1]
    found.sort(key=lambda so: (so[0].d, not so[0].is_subgraph, -shared_bonds(so[0]), -so[1]))
    return [s for s, _ in found[:MAX_SUGGESTIONS]]


def match_cluster(g: Graph, db=DATABASE) -> ClusterResult:
    candidates = [s for s in BY_SIGNATURE.get(g.signature(), []) if s in db]
    for s in candidates:
        if is_isomorphic(g, s.graph):
            return ClusterResult("MATCH", g, s)
    warn = valence_warnings(g)
    if candidates:
        best = min(candidates, key=lambda s: sum(_sum_diff(g, s.graph)))
        extra, missing = _bond_diff(g, best.graph)
        return ClusterResult("WRONG_BONDS", g, best, candidates, extra, missing, valence_warnings=warn)
    sugs = suggest(g, db)
    return ClusterResult("SUGGEST" if sugs else "UNKNOWN", g, suggestions=sugs, valence_warnings=warn)


def _sum_diff(g, ref):
    a, b = _bond_diff(g, ref)
    return sum(a.values()), sum(b.values())


# --------------------------------------------------------------------------- lời thông báo
def card_label(sym: str, speech: bool = False) -> str:
    name = ELEMENT_NAMES.get(sym)
    if speech:
        return name or sym
    return f"{sym} ({name})" if name else sym


def sub_label(s: Substance, speech: bool = False) -> str:
    return s.name if speech else f"{s.name} ({s.formula})"


def count_phrase(counter: Counter, speech: bool = False) -> str:
    return ", ".join(f"{n} thẻ {card_label(sym, speech)}" for sym, n in sorted(counter.items()))


def describe_structure(g: Graph) -> str:
    centres = [i for i in range(len(g.labels)) if len(g.adj[i]) > 1]
    if not centres:
        centres = [0]
    parts = sorted(f"{g.labels[i]} nối với {', '.join(sorted(g.labels[j] for j in g.adj[i]))}" for i in centres)
    return "; ".join(parts)


def _bond_phrase(c: Counter) -> str:
    return ", ".join(f"{a}–{b}" + (f" (×{n})" if n > 1 else "") for (a, b), n in sorted(c.items()))


def _match_extra(sub: Substance, speech: bool) -> str:
    comp = sub.graph.composition()
    if any(sym not in ATOMIC_MASS for sym in comp):
        return ""
    mass = format_mass(molecular_mass(comp))
    if sub.ionic:
        if speech:
            return f" Khối lượng công thức là {mass}. Đây là hợp chất ion."
        return (f" Khối lượng công thức: {mass}. Lưu ý: {sub.name} là hợp chất ion, gồm các ion xếp thành mạng tinh thể, "
                "không có phân tử riêng lẻ; ghép cặp chỉ là quy ước để kiểm tra.")
    return f" Phân tử khối là {mass}." if speech else f" Phân tử khối: {mass}."


def cluster_message(r: ClusterResult, speech: bool = False) -> str:
    if r.kind == "MATCH":
        return f"Cấu trúc khớp với {sub_label(r.substance, speech)}." + _match_extra(r.substance, speech)
    if r.kind == "WRONG_BONDS":
        names = " hoặc ".join(sub_label(s, speech) for s in r.same_composition)
        msg = f"Thành phần giống {names} nhưng cách ghép thẻ chưa đúng cấu trúc phân tử."
        if not speech:
            if r.extra_bonds or r.missing_bonds:
                parts = []
                if r.extra_bonds:
                    parts.append(f"thừa liên kết {_bond_phrase(r.extra_bonds)}")
                if r.missing_bonds:
                    parts.append(f"thiếu liên kết {_bond_phrase(r.missing_bonds)}")
                msg += " Cụ thể: " + "; ".join(parts) + "."
            msg += f" Cấu trúc đúng của {r.substance.name}: {describe_structure(r.substance.graph)}."
        if r.valence_warnings and not speech:
            msg += " Lưu ý: " + "; ".join(r.valence_warnings) + "."
        return msg
    if r.kind == "SUGGEST":
        first = r.suggestions[0]
        msg = f"Chưa khớp chất nào. Có phải bạn muốn ghép {sub_label(first.substance, speech)}?"
        if first.missing:
            msg += f" Còn thiếu {count_phrase(first.missing, speech)}."
        if first.extra:
            msg += f" Đang thừa {count_phrase(first.extra, speech)}."
        rest = r.suggestions[1:]
        if rest:
            msg += " Hoặc: " + ", ".join(sub_label(s.substance, speech) for s in rest) + "?"
        if r.valence_warnings and not speech:
            msg += " Lưu ý: " + "; ".join(r.valence_warnings) + "."
        return msg
    return "Chưa nhận ra chất nào phù hợp với cụm thẻ này. Hãy kiểm tra lại cách ghép."


# --------------------------------------------------------------------------- toàn bộ một lượt kiểm tra
@dataclass
class Analysis:
    status: str                      # EMPTY | RECAPTURE | OK
    cleaned: Cleaned
    clusters: list = field(default_factory=list)   # [(ids, ClusterResult)]
    message: str = ""
    speech: str = ""

    def matches(self) -> list[str]:
        return [r.substance.key for _, r in self.clusters if r.kind == "MATCH"]


def analyze(raw, db=DATABASE) -> Analysis:
    cleaned = clean_molecule(raw)
    if cleaned.recapture:
        text = "Ảnh chưa đủ rõ: " + "; ".join(cleaned.problems) + ". Hãy chỉnh lại thẻ và chụp lại."
        return Analysis("RECAPTURE", cleaned, message=text, speech=_speech_of(text))
    if not cleaned.cards:
        text = "Không thấy thẻ nguyên tố nào trong ảnh."
        return Analysis("EMPTY", cleaned, message=text, speech=text)
    clusters = [(ids, match_cluster(g, db)) for ids, g in components(cleaned)]
    if len(clusters) == 1:
        r = clusters[0][1]
        return Analysis("OK", cleaned, clusters, cluster_message(r), cluster_message(r, True))
    head = f"Có {len(clusters)} cụm thẻ chưa liền nhau."
    text = head + "".join(f" Cụm {i}: {cluster_message(r)}" for i, (_, r) in enumerate(clusters, 1))
    spoken = head + "".join(f" Cụm {i}: {cluster_message(r, True)}" for i, (_, r) in enumerate(clusters, 1))
    return Analysis("OK", cleaned, clusters, text, spoken)


def _speech_of(text: str) -> str:
    """Bỏ phần kí hiệu trong ngoặc để giọng đọc không đọc 'H2O' từng chữ."""
    text = re.sub(r"\b[A-Z][a-z]?\s*\(([^()0-9A-Z]+)\)", r"\1", text)      # "H (hiđro)" -> "hiđro"
    return re.sub(r"\s*\((?:[A-Z][A-Za-z0-9()]*)\)", "", text)             # bỏ "(H2O)"


def speech_cache_name(text: str) -> str:
    """Tên tệp âm thanh theo nội dung: lặp lại một câu thì dùng lại, không gọi gTTS nữa."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16] + ".mp3"
