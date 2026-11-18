"""Chất và nguyên tố do người dùng tự thêm trên giao diện (lưu ở trình duyệt, gửi kèm mỗi lượt kiểm tra).

Máy chủ không lưu gì: mỗi lượt kiểm tra tạo cơ sở dữ liệu mở rộng = DATABASE + chất thêm, và tạm đăng kí
tên/nguyên tử khối của nguyên tố thêm trong lúc xử lý (có khóa, xong thì trả lại như cũ).
"""
from __future__ import annotations

import re
import threading
from contextlib import contextmanager

from .core import DATABASE, ELEMENTS, ELEMENT_NAMES, Graph, Substance
from .curriculum import ATOMIC_MASS

MAX_SUBSTANCES, MAX_ELEMENTS, MAX_ATOMS, MAX_BONDS, MAX_TEXT = 20, 20, 40, 80, 60
_lock = threading.Lock()


def _text(v, what: str) -> str:
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    if not s or len(s) > MAX_TEXT:
        raise ValueError(f"{what} phải có từ 1 đến {MAX_TEXT} ký tự.")
    return s


def _symbol(v) -> str:
    s = str(v or "").strip()
    s = s[:1].upper() + s[1:].lower()
    if s not in ELEMENTS:
        raise ValueError(f"'{v}' không phải kí hiệu nguyên tố.")
    return s


def parse(custom) -> tuple[tuple[Substance, ...], dict, dict]:
    """Kiểm tra dữ liệu thêm vào. Trả về (chất, tên nguyên tố, nguyên tử khối); sai thì ném ValueError."""
    if not custom:
        return (), {}, {}
    if not isinstance(custom, dict):
        raise ValueError("Dữ liệu tự thêm không hợp lệ.")
    elements = custom.get("elements") or []
    substances = custom.get("substances") or []
    if not isinstance(elements, list) or not isinstance(substances, list) \
            or len(elements) > MAX_ELEMENTS or len(substances) > MAX_SUBSTANCES:
        raise ValueError(f"Chỉ thêm tối đa {MAX_ELEMENTS} nguyên tố và {MAX_SUBSTANCES} chất.")
    names, masses = {}, {}
    for e in elements:
        if not isinstance(e, dict):
            raise ValueError("Nguyên tố không hợp lệ.")
        sym = _symbol(e.get("symbol"))
        names[sym] = _text(e.get("name"), "Tên nguyên tố")
        try:
            mass = float(e.get("mass"))
        except (TypeError, ValueError):
            raise ValueError(f"Nguyên tử khối của {sym} phải là một số.") from None
        if not 0 < mass < 400:
            raise ValueError(f"Nguyên tử khối của {sym} phải từ 0 đến 400.")
        masses[sym] = mass
    subs = []
    for i, s in enumerate(substances):
        if not isinstance(s, dict) or not isinstance(s.get("atoms"), list) or not isinstance(s.get("bonds"), list):
            raise ValueError("Chất không hợp lệ.")
        formula = _text(s.get("formula"), "Công thức")
        atoms = [_symbol(a) for a in s["atoms"]]
        if not 2 <= len(atoms) <= MAX_ATOMS or len(s["bonds"]) > MAX_BONDS:
            raise ValueError(f"{formula}: cần 2 đến {MAX_ATOMS} nguyên tử và tối đa {MAX_BONDS} liên kết.")
        edges = set()
        for b in s["bonds"]:
            try:
                x, y = (int(v) for v in b)
            except (TypeError, ValueError):
                raise ValueError(f"{formula}: liên kết không hợp lệ.") from None
            if x == y or not (0 <= x < len(atoms) and 0 <= y < len(atoms)):
                raise ValueError(f"{formula}: liên kết nối nguyên tử không tồn tại.")
            edges.add((min(x, y), max(x, y)))
        g = Graph.from_edges(atoms, sorted(edges))
        seen, stack = {0}, [0]
        while stack:
            for v in g.adj[stack.pop()] - seen:
                seen.add(v)
                stack.append(v)
        if len(seen) != len(atoms):
            raise ValueError(f"{formula}: các nguyên tử phải nối liền thành một phân tử.")
        subs.append(Substance(f"custom-{i}-{formula}", formula, _text(s.get("name"), "Tên chất"),
                              _text(s.get("group") or "chất thêm", "Nhóm"), g, grade=7))
    return tuple(subs), names, masses


@contextmanager
def applied(custom):
    """Cho cơ sở dữ liệu mở rộng; tạm gắn tên và nguyên tử khối nguyên tố thêm vào bảng dùng chung."""
    subs, names, masses = parse(custom)
    if not (subs or names or masses):
        yield DATABASE
        return
    with _lock:
        old = [(d, k, d.get(k)) for d, new in ((ELEMENT_NAMES, names), (ATOMIC_MASS, masses)) for k in new]
        ELEMENT_NAMES.update(names)
        ATOMIC_MASS.update(masses)
        try:
            yield DATABASE + subs
        finally:
            for d, k, v in old:
                if v is None:
                    d.pop(k, None)
                else:
                    d[k] = v
