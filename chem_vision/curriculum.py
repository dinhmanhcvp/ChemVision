"""Nội dung chương trình Khoa học tự nhiên THCS (lớp 6 đến lớp 9) dùng cho CHEM VISION.

Chứa dữ liệu nguyên tố (tên, nguyên tử khối làm tròn như sách giáo khoa, hóa trị, màu thẻ), cách lập công thức hóa học
theo hóa trị, phân tử khối và các bộ đề theo lớp. Không phụ thuộc vào core.py để core.py nhập được.
"""
from __future__ import annotations

from collections import Counter
from math import gcd

# Thứ tự này quyết định số hiệu mã đánh dấu (ArUco) in trên thẻ: không đổi thứ tự khi đã in thẻ.
CARD_ELEMENTS = ["H", "C", "N", "O", "Na", "Mg", "Al", "P", "S", "Cl", "K", "Ca", "Fe", "Cu", "Zn", "Ag", "Ba",
                 "F", "Br", "I", "Si", "Li"]

ELEMENT_NAMES = {
    "H": "hiđro", "C": "cacbon", "N": "nitơ", "O": "oxi", "Na": "natri", "Mg": "magie", "Al": "nhôm",
    "P": "photpho", "S": "lưu huỳnh", "Cl": "clo", "K": "kali", "Ca": "canxi", "Fe": "sắt", "Cu": "đồng",
    "Zn": "kẽm", "Ag": "bạc", "Ba": "bari", "F": "flo", "Br": "brom", "I": "iot", "Si": "silic", "Li": "liti",
    "Au": "vàng", "He": "heli",
}

# Nguyên tử khối làm tròn theo sách giáo khoa THCS.
ATOMIC_MASS = {"H": 1, "Li": 7, "C": 12, "N": 14, "O": 16, "F": 19, "Na": 23, "Mg": 24, "Al": 27, "Si": 28,
               "P": 31, "S": 32, "Cl": 35.5, "K": 39, "Ca": 40, "Fe": 56, "Cu": 64, "Zn": 65, "Br": 80,
               "Ag": 108, "I": 127, "Ba": 137}

# Hóa trị thường gặp (số đầu tiên là hóa trị phổ biến nhất).
VALENCE = {"H": [1], "Li": [1], "Na": [1], "K": [1], "Ag": [1], "F": [1], "Cl": [1], "Br": [1], "I": [1],
           "O": [2], "Mg": [2], "Ca": [2], "Ba": [2], "Zn": [2], "Cu": [2, 1], "Fe": [3, 2], "Al": [3],
           "C": [4, 2], "Si": [4], "N": [3, 2, 4, 5], "P": [5, 3], "S": [2, 4, 6]}

# Màu thẻ theo quy ước CPK (RGB) để học sinh nhận ra nguyên tố bằng màu.
COLORS = {"H": (240, 240, 240), "C": (110, 110, 110), "N": (90, 120, 230), "O": (235, 80, 70), "Na": (170, 120, 230),
          "Mg": (140, 210, 90), "Al": (200, 170, 170), "P": (255, 150, 40), "S": (240, 220, 70), "Cl": (90, 210, 90),
          "K": (150, 90, 200), "Ca": (110, 180, 110), "Fe": (210, 130, 60), "Cu": (200, 125, 85), "Zn": (150, 160, 190),
          "Ag": (200, 200, 205), "Ba": (80, 190, 100), "F": (150, 220, 120), "Br": (170, 60, 50), "I": (140, 60, 170),
          "Si": (190, 170, 130), "Li": (200, 120, 230)}

_METALS = ["Li", "Na", "K", "Mg", "Ca", "Ba", "Zn", "Fe", "Cu", "Al", "Ag"]
_NONMETAL_ORDER = ["H", "Si", "C", "N", "P", "S", "I", "Br", "Cl", "O", "F"]
_HYDRIDE_LAST = {"C", "Si", "N", "P"}        # CH4, SiH4, NH3, PH3: H viết sau


def molecular_mass(composition: Counter) -> float:
    """Phân tử khối (hoặc khối lượng công thức) theo nguyên tử khối làm tròn."""
    return sum(ATOMIC_MASS[s] * n for s, n in composition.items())


def format_mass(value: float) -> str:
    text = f"{value:g}".replace(".", ",")
    return text


def compound_formula(a: str, va: int, b: str, vb: int) -> str:
    """Lập công thức hợp chất hai nguyên tố theo hóa trị (quy tắc chéo, rút gọn)."""
    g = gcd(va, vb)
    na, nb = vb // g, va // g
    first, second = _order(a, b)
    counts = {a: na, b: nb}
    def part(sym):
        n = counts[sym]
        return sym + (str(n) if n > 1 else "")
    return part(first) + part(second)


def _order(a: str, b: str) -> tuple[str, str]:
    for x, y in ((a, b), (b, a)):
        if x in _METALS and y not in _METALS:
            return x, y
    if a in _METALS and b in _METALS:
        return (a, b) if _METALS.index(a) <= _METALS.index(b) else (b, a)
    if "H" in (a, b):
        other = b if a == "H" else a
        return (other, "H") if other in _HYDRIDE_LAST else ("H", other)
    ia, ib = _NONMETAL_ORDER.index(a), _NONMETAL_ORDER.index(b)
    return (a, b) if ia <= ib else (b, a)


def valence_task(formula_composition: Counter, formula: str):
    """Tìm (A, hóa trị A, B, hóa trị B) sao cho quy tắc hóa trị cho đúng công thức này; None nếu không có."""
    if len(formula_composition) != 2:
        return None
    a, b = sorted(formula_composition)
    for va in VALENCE.get(a, []):
        for vb in VALENCE.get(b, []):
            if compound_formula(a, va, b, vb) == formula:
                first, second = _order(a, b)
                vals = {a: va, b: vb}
                return first, vals[first], second, vals[second]
    return None


ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI"}

# --------------------------------------------------------------------------- bộ đề theo lớp
# Mỗi bộ đề: tên -> (lớp, kiểu, danh sách chất). Kiểu "valence": đề nêu hóa trị thay vì tên chất.
DECK_SPECS = {
    "Khởi động": (7, "name", ["H2", "O2", "H2O", "CO2", "NH3", "CH4"]),
    "Oxit và axit": (7, "name", ["CO", "SO2", "SO3", "NO2", "HCl", "HNO3", "H2SO4"]),
    "Bazơ và muối": (7, "name", ["NaOH", "KOH", "Ca(OH)2", "NaCl", "Na2CO3", "CaCO3"]),
    "Phân biệt đồng phân": (7, "name", ["C2H5OH", "CH3OCH3", "H2O2", "H2O"]),
    "Lớp 6: Chất quanh ta": (6, "name", ["O2", "N2", "H2O", "CO2", "NaCl"]),
    "Lớp 7: Lập công thức theo hóa trị": (7, "valence", ["H2O", "CO2", "NH3", "CaO", "Na2O", "Al2O3"]),
    "Lớp 8: Oxit": (8, "name", ["Na2O", "Fe2O3", "Al2O3", "P2O5", "CuO", "SO3"]),
    "Lớp 8: Axit và bazơ": (8, "name", ["HCl", "H2SO4", "H3PO4", "H2CO3", "NaOH", "Mg(OH)2", "Al(OH)3", "Fe(OH)3"]),
    "Lớp 8: Muối và phân bón": (8, "name", ["NaCl", "CuSO4", "BaSO4", "KNO3", "AgCl", "FeCl3", "CO(NH2)2"]),
    "Lớp 9: Hiđrocacbon": (9, "name", ["CH4", "C2H6", "C2H4", "C2H2", "C3H8", "C6H6"]),
    "Lớp 9: Đồng phân và dẫn xuất": (9, "name", ["C4H10", "C4H10-iso", "CH3OH", "C2H5OH", "CH3OCH3", "CH3COOH"]),
}
DECKS = {name: keys for name, (grade, style, keys) in DECK_SPECS.items()}
DECK_GRADE = {name: grade for name, (grade, style, keys) in DECK_SPECS.items()}
DECK_STYLE = {name: style for name, (grade, style, keys) in DECK_SPECS.items()}

GRADE_TITLES = {6: "Lớp 6: chất và sự biến đổi", 7: "Lớp 7: nguyên tử, phân tử, hóa trị",
                8: "Lớp 8: phản ứng hóa học, oxit, axit, bazơ, muối", 9: "Lớp 9: hợp chất hữu cơ"}
