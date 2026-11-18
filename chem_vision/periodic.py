"""Bảng tra nguyên tố ngoài bộ thẻ in sẵn: gõ tên (hoặc kí hiệu) là có kí hiệu, nguyên tử khối và hóa trị.

Nguyên tử khối làm tròn theo sách giáo khoa THCS; hóa trị đầu tiên là phổ biến nhất. Khí hiếm có hóa trị 0.
Nguyên tố không có trong bảng thì người dùng tự nhập kí hiệu và hóa trị.
"""
from __future__ import annotations

import unicodedata

from .curriculum import ATOMIC_MASS, ELEMENT_NAMES, VALENCE

# kí hiệu: (tên tiếng Việt, nguyên tử khối, [hóa trị])
EXTRA = {
    "He": ("heli", 4, [0]), "Ne": ("neon", 20, [0]), "Ar": ("agon", 40, [0]), "Kr": ("kripton", 84, [0]),
    "Xe": ("xenon", 131, [0]), "Rn": ("rađon", 222, [0]),
    "Be": ("beri", 9, [2]), "B": ("bo", 11, [3]), "Ti": ("titan", 48, [4]), "V": ("vanađi", 51, [5, 4]),
    "Cr": ("crom", 52, [3, 2, 6]), "Mn": ("mangan", 55, [2, 4, 7, 6]), "Co": ("coban", 59, [2, 3]),
    "Ni": ("niken", 59, [2]), "Ga": ("gali", 70, [3]), "Ge": ("gecmani", 73, [4]), "As": ("asen", 75, [3, 5]),
    "Se": ("selen", 79, [2, 4, 6]), "Rb": ("rubidi", 85.5, [1]), "Sr": ("stronti", 88, [2]),
    "Zr": ("zirconi", 91, [4]), "Mo": ("molipđen", 96, [6]), "Pd": ("paladi", 106, [2]), "Cd": ("cađimi", 112, [2]),
    "Sn": ("thiếc", 119, [2, 4]), "Sb": ("antimon", 122, [3, 5]), "Te": ("telu", 128, [2, 4, 6]),
    "Cs": ("xesi", 133, [1]), "W": ("vonfram", 184, [6]), "Pt": ("bạch kim", 195, [2, 4]),
    "Au": ("vàng", 197, [3, 1]), "Hg": ("thủy ngân", 201, [2, 1]), "Pb": ("chì", 207, [2, 4]),
    "Bi": ("bismut", 209, [3]), "Ra": ("rađi", 226, [2]), "U": ("urani", 238, [6, 4]),
}


def _fold(text: str) -> str:
    """Bỏ dấu, chữ thường: 'Bạch Kim' và 'bach kim' như nhau."""
    s = unicodedata.normalize("NFD", str(text).lower().replace("đ", "d"))
    return "".join(c for c in s if not unicodedata.combining(c)).strip()


def lookup(text: str):
    """Tên hoặc kí hiệu -> (kí hiệu, tên, nguyên tử khối hoặc None, [hóa trị]); không có thì None."""
    key = _fold(text)
    for sym, name in ELEMENT_NAMES.items():                        # nguyên tố đã có thẻ in sẵn
        if key in (_fold(sym), _fold(name)) and sym in VALENCE:
            return sym, name, ATOMIC_MASS.get(sym), list(VALENCE[sym])
    for sym, (name, mass, valence) in EXTRA.items():
        if key in (_fold(sym), _fold(name)):
            return sym, name, mass, list(valence)
    return None
