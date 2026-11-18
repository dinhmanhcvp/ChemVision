"""Nguyên tố người dùng tự thêm trên giao diện: mỗi nguyên tố gắn với một mã ArUco chưa dùng, người dùng chỉ cần đặt tên.

Trình duyệt lưu danh sách và gửi kèm mỗi lượt kiểm tra; máy chủ không lưu gì. Mỗi lượt, `applied` tạm đăng kí tên,
nguyên tử khối, hóa trị của các nguyên tố này (có khóa, xong thì trả lại như cũ). Chất tạo từ thẻ mới được đánh giá
đúng hay sai bằng hóa trị (xem `_by_valence` trong core.py), nên không cần khai báo từng chất.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from .core import ELEMENTS, ELEMENT_NAMES
from .curriculum import ATOMIC_MASS, CARD_ELEMENTS, VALENCE
from .markers import DICT_ID_COUNT
from .periodic import lookup

MAX_ELEMENTS, MAX_NAME = 20, 30
_lock = threading.Lock()


class NeedMore(ValueError):
    """Tên chưa có trong bảng tra: giao diện cần hỏi thêm kí hiệu hoặc hóa trị."""

    def __init__(self, message: str, need: str):
        super().__init__(message)
        self.need = need


def free_markers() -> range:
    return range(len(CARD_ELEMENTS), DICT_ID_COUNT)


def _entry(e) -> tuple[int, str, str, float | None, list[int]]:
    if not isinstance(e, dict) or isinstance(e.get("marker"), bool) or not isinstance(e.get("marker"), int) \
            or e["marker"] not in free_markers():
        raise ValueError("Mã của nguyên tố không hợp lệ.")
    name = " ".join(str(e.get("name") or "").split())
    if not 0 < len(name) <= MAX_NAME:
        raise ValueError(f"Tên nguyên tố phải có từ 1 đến {MAX_NAME} ký tự.")
    found = lookup(name) or (lookup(str(e["symbol"])) if e.get("symbol") else None)
    if found:
        symbol, _, mass, valence = found
    else:                                  # không có trong bảng tra: người dùng phải nhập kí hiệu và hóa trị
        symbol = str(e.get("symbol") or "").strip()
        symbol = symbol[:1].upper() + symbol[1:].lower()
        valence = e.get("valence")
        valence = [valence] if isinstance(valence, int) else valence
        if symbol not in ELEMENTS:
            raise NeedMore(f"Chưa biết '{name}' là nguyên tố nào. Hãy nhập thêm kí hiệu (ví dụ Pt) và hóa trị.", "symbol")
        if not isinstance(valence, list) or not valence or not all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 8 for v in valence):
            raise NeedMore(f"Hãy nhập hóa trị của {symbol} (số từ 0 đến 8).", "valence")
        mass = None
    if symbol in CARD_ELEMENTS:
        raise ValueError(f"{symbol} đã có thẻ in sẵn, không cần thêm.")
    return e["marker"], symbol, name, mass, valence


def parse(custom) -> tuple[dict, list]:
    """Kiểm tra danh sách nguyên tố đã đặt tên. Trả về ({mã: kí hiệu}, [(kí hiệu, tên, nguyên tử khối, hóa trị)]); sai thì ném ValueError."""
    if not custom:
        return {}, []
    entries = custom.get("elements") if isinstance(custom, dict) else None
    if not isinstance(entries, list) or len(entries) > MAX_ELEMENTS:
        raise ValueError(f"Chỉ thêm tối đa {MAX_ELEMENTS} nguyên tố.")
    registry, rows = {}, []
    for e in entries:
        marker, symbol, name, mass, valence = _entry(e)
        if marker in registry or symbol in {r[0] for r in rows}:
            raise ValueError("Mỗi mã và mỗi nguyên tố chỉ được thêm một lần.")
        registry[marker] = symbol
        rows.append((symbol, name, mass, valence))
    return registry, rows


@contextmanager
def applied(rows):
    """Tạm đăng kí tên, nguyên tử khối và hóa trị của nguyên tố thêm vào các bảng dùng chung, xong thì trả lại."""
    if not rows:
        yield
        return
    with _lock:
        saved = [(d, s, d.get(s)) for d in (ELEMENT_NAMES, ATOMIC_MASS, VALENCE) for s, *_ in rows]
        for symbol, name, mass, valence in rows:
            ELEMENT_NAMES[symbol] = name
            VALENCE[symbol] = valence
            if mass is not None:
                ATOMIC_MASS[symbol] = mass
        try:
            yield
        finally:
            for d, s, v in saved:
                if v is None:
                    d.pop(s, None)
                else:
                    d[s] = v
