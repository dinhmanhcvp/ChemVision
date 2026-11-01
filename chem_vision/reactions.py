"""Phương trình hóa học (Khoa học tự nhiên lớp 8): đọc công thức, cân bằng, kiểm tra hệ số học sinh nhập.

Kết quả cân bằng được tính chính xác bằng phân số (không dùng số thực), nên không có sai số làm tròn.
"""
from __future__ import annotations

import re
from collections import Counter
from fractions import Fraction
from math import gcd

from .curriculum import ATOMIC_MASS, format_mass

# (chất tham gia, sản phẩm). Chỉ liệt kê công thức; hệ số do học sinh tìm.
EQUATIONS = [
    (["H2", "O2"], ["H2O"]),
    (["Mg", "O2"], ["MgO"]),
    (["Al", "O2"], ["Al2O3"]),
    (["P", "O2"], ["P2O5"]),
    (["Fe", "O2"], ["Fe3O4"]),
    (["N2", "H2"], ["NH3"]),
    (["SO2", "O2"], ["SO3"]),
    (["CH4", "O2"], ["CO2", "H2O"]),
    (["C2H2", "O2"], ["CO2", "H2O"]),
    (["C2H5OH", "O2"], ["CO2", "H2O"]),
    (["Zn", "HCl"], ["ZnCl2", "H2"]),
    (["Fe", "HCl"], ["FeCl2", "H2"]),
    (["Al", "HCl"], ["AlCl3", "H2"]),
    (["Al", "H2SO4"], ["Al2(SO4)3", "H2"]),
    (["NaOH", "H2SO4"], ["Na2SO4", "H2O"]),
    (["Ca(OH)2", "HCl"], ["CaCl2", "H2O"]),
    (["Na2CO3", "HCl"], ["NaCl", "H2O", "CO2"]),
    (["BaCl2", "Na2SO4"], ["BaSO4", "NaCl"]),
    (["AgNO3", "NaCl"], ["AgCl", "NaNO3"]),
    (["CuSO4", "NaOH"], ["Cu(OH)2", "Na2SO4"]),
    (["CaCO3"], ["CaO", "CO2"]),
    (["KClO3"], ["KCl", "O2"]),
    (["H2O2"], ["H2O", "O2"]),
    (["Fe(OH)3"], ["Fe2O3", "H2O"]),
]


def parse_formula(formula: str) -> Counter:
    """Đọc công thức có ngoặc và chỉ số, ví dụ Al2(SO4)3 hoặc Ca(OH)2."""
    stack = [Counter()]
    pos = 0
    for m in re.finditer(r"\(|\)(\d*)|([A-Z][a-z]?)(\d*)", formula):
        if m.start() != pos:
            raise ValueError(f"Công thức không hợp lệ: {formula}")
        pos = m.end()
        token = m.group(0)
        if token == "(":
            stack.append(Counter())
        elif token.startswith(")"):
            if len(stack) < 2:
                raise ValueError(f"Công thức không hợp lệ: {formula}")
            inner = stack.pop()
            for sym, n in inner.items():
                stack[-1][sym] += n * int(m.group(1) or 1)
        else:
            stack[-1][m.group(2)] += int(m.group(3) or 1)
    if pos != len(formula) or len(stack) != 1 or not stack[0]:
        raise ValueError(f"Công thức không hợp lệ: {formula}")
    return stack[0]


def balance(reactants: list[str], products: list[str]) -> list[int] | None:
    """Hệ số nguyên dương nhỏ nhất cân bằng phương trình, theo thứ tự chất tham gia rồi sản phẩm; None nếu không có."""
    species = reactants + products
    comps = [parse_formula(f) for f in species]
    elements = sorted({e for c in comps for e in c})
    rows = [[Fraction(c[e] * (1 if i < len(reactants) else -1)) for i, c in enumerate(comps)] for e in elements]
    n = len(species)
    pivots, r = [], 0
    for col in range(n):
        pr = next((i for i in range(r, len(rows)) if rows[i][col] != 0), None)
        if pr is None:
            continue
        rows[r], rows[pr] = rows[pr], rows[r]
        rows[r] = [v / rows[r][col] for v in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][col] != 0:
                f = rows[i][col]
                rows[i] = [a - f * b for a, b in zip(rows[i], rows[r])]
        pivots.append(col)
        r += 1
    free = [c for c in range(n) if c not in pivots]
    if len(free) != 1:
        return None                                   # không có nghiệm hoặc nhiều nghiệm độc lập
    x = [Fraction(0)] * n
    x[free[0]] = Fraction(1)
    for i, col in enumerate(pivots):
        x[col] = -rows[i][free[0]]
    if any(v <= 0 for v in x):
        return None
    den = 1
    for v in x:
        den = den * v.denominator // gcd(den, v.denominator)
    ints = [int(v * den) for v in x]
    g = 0
    for v in ints:
        g = gcd(g, v)
    return [v // g for v in ints]


def equation_text(reactants: list[str], products: list[str], coefficients: list | None = None) -> str:
    def side(formulas, coefs):
        parts = []
        for f, c in zip(formulas, coefs):
            parts.append((f"{c} " if c not in (1, None, "") else "") + f if coefs is not None else f)
        return " + ".join(parts)
    n = len(reactants)
    co = coefficients if coefficients is not None else [None] * (n + len(products))
    return side(reactants, co[:n]) + " → " + side(products, co[n:])


def mass_of(formula: str) -> float | None:
    comp = parse_formula(formula)
    if any(e not in ATOMIC_MASS for e in comp):
        return None
    return sum(ATOMIC_MASS[e] * n for e, n in comp.items())


def check(index: int, coefficients: list) -> dict:
    """Kiểm tra hệ số học sinh nhập cho phương trình số `index`; giải thích nguyên tố nào chưa cân bằng."""
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(EQUATIONS):
        return {"ok": False, "error": "Phương trình không tồn tại."}
    reactants, products = EQUATIONS[index]
    n = len(reactants) + len(products)
    if (not isinstance(coefficients, list) or len(coefficients) != n
            or not all(isinstance(c, int) and not isinstance(c, bool) and 1 <= c <= 20 for c in coefficients)):
        return {"ok": False, "error": f"Cần nhập {n} hệ số, mỗi hệ số là số nguyên từ 1 đến 20."}
    comps = [parse_formula(f) for f in reactants + products]
    left, right = Counter(), Counter()
    for i, comp in enumerate(comps):
        for e, k in comp.items():
            (left if i < len(reactants) else right)[e] += k * coefficients[i]
    wrong = [e for e in sorted(set(left) | set(right)) if left[e] != right[e]]
    best = balance(reactants, products)
    out = {"ok": not wrong, "balanced": not wrong, "equation": equation_text(reactants, products, coefficients)}
    if wrong:
        out["message"] = "Chưa cân bằng. " + "; ".join(
            f"nguyên tố {e}: vế trái {left[e]} nguyên tử, vế phải {right[e]} nguyên tử" for e in wrong) + "."
        return out
    simplest = best is not None and coefficients == best
    masses = [mass_of(f) for f in reactants + products]
    note = ""
    if all(m is not None for m in masses):
        lm = sum(masses[i] * coefficients[i] for i in range(len(reactants)))
        rm = sum(masses[i] * coefficients[i] for i in range(len(reactants), n))
        note = (f" Khối lượng chất tham gia {format_mass(lm)} = khối lượng sản phẩm {format_mass(rm)} "
                "(định luật bảo toàn khối lượng).")
    out["simplest"] = simplest
    out["message"] = ("Chính xác! Phương trình đã cân bằng." if simplest else
                      "Đã cân bằng, nhưng chưa phải hệ số nhỏ nhất: hãy rút gọn các hệ số.") + note
    return out


def solution(index: int) -> list[int] | None:
    reactants, products = EQUATIONS[index]
    return balance(reactants, products)
