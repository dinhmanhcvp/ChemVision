"""Nhận diện thẻ bằng mã đánh dấu ArUco in trên thẻ: chạy ngay trên máy, ngoại tuyến, miễn phí, không gửi ảnh đi đâu.

Mỗi thẻ nguyên tố in kèm một mã ArUco có số hiệu bằng vị trí của nguyên tố trong `CARD_ELEMENTS`. OpenCV đọc số hiệu
và vị trí mã, từ đó suy ra kí hiệu nguyên tố và thẻ nào chạm thẻ nào. Kết quả có cùng dạng JSON với kết quả từ Gemini,
nên phần còn lại của hệ thống không cần biết thẻ được đọc bằng cách nào.
"""
from __future__ import annotations

import numpy as np

from .curriculum import CARD_ELEMENTS

DICT_NAME = "DICT_4X4_50"
DICT_ID_COUNT = 50           # số mã của từ điển; mã sau các nguyên tố in sẵn dành cho nguyên tố người dùng thêm     # 50 mã, đủ cho 22 nguyên tố; mã 4x4 lớn nên đọc tốt ở khoảng cách xa
CARD_TO_MARKER = 2.2          # đối cạnh của thẻ lục giác / cạnh mã in trên thẻ (xem scripts/make_cards.py)
LINK_RATIO = 1.3              # hai thẻ chạm nhau nếu hai tâm cách nhau không quá LINK_RATIO x kích thước thẻ


def _detector():
    import cv2
    aruco = cv2.aruco
    return aruco.ArucoDetector(aruco.getPredefinedDictionary(getattr(aruco, DICT_NAME)), aruco.DetectorParameters())


def marker_image(element: str | int, size: int = 200):
    """Ảnh mã ArUco (xám) của một nguyên tố (kí hiệu) hoặc của một số hiệu mã, dùng khi in thẻ."""
    import cv2
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(getattr(aruco, DICT_NAME))
    marker_id = element if isinstance(element, int) else CARD_ELEMENTS.index(element)
    return aruco.generateImageMarker(dictionary, marker_id, size)


def cards_from_markers(frame_bgr, min_cards: int = 1, registry: dict | None = None, off: set | None = None) -> dict | None:
    """Đọc các mã ArUco trong ảnh. Trả về dữ liệu cùng dạng với kết quả của Gemini, hoặc None nếu không thấy mã nào hợp lệ.

    registry: {số hiệu mã: kí hiệu} của các nguyên tố người dùng tự thêm (số hiệu từ len(CARD_ELEMENTS) trở lên).
    off: số hiệu mã của nguyên tố in sẵn đã bị xóa (coi như chưa gán nhãn).
    Mã chưa được gán nhãn cho ra thẻ có symbol "?" và marker = số hiệu, để báo "chưa biết đây là chất gì"."""
    registry, off = registry or {}, off or set()
    corners, ids, _ = _detector().detectMarkers(frame_bgr)
    if ids is None:
        return None
    h, w = frame_bgr.shape[:2]
    found = []
    for quad, mid in zip(corners, ids.flatten()):
        mid = int(mid)
        symbol = "?" if mid in off else CARD_ELEMENTS[mid] if 0 <= mid < len(CARD_ELEMENTS) else registry.get(mid, "?")
        pts = quad.reshape(4, 2)
        side = float(np.mean([np.linalg.norm(pts[i] - pts[(i + 1) % 4]) for i in range(4)]))
        centre = pts.mean(axis=0).astype(float)
        found.append((symbol, mid, centre, side * CARD_TO_MARKER))
    if len(found) < min_cards:
        return None
    # sắp xếp từ trái sang phải, trên xuống dưới để số thứ tự thẻ ổn định giữa các lần chụp
    found.sort(key=lambda f: (round(f[2][1] / max(f[3], 1)), f[2][0]))
    cards, centres = [], []
    for i, (symbol, mid, c, card) in enumerate(found, 1):
        half = card * 0.58
        box = [max(0.0, (c[1] - half) / h * 1000), max(0.0, (c[0] - half) / w * 1000),
               min(1000.0, (c[1] + half) / h * 1000), min(1000.0, (c[0] + half) / w * 1000)]
        item = {"id": i, "symbol": symbol, "confidence": 1.0, "box_2d": [round(float(v), 1) for v in box]}
        if symbol == "?":
            item["marker"] = mid
        cards.append(item)
        centres.append((c, card))
    links = []
    for i in range(len(centres)):
        for j in range(i + 1, len(centres)):
            (ci, si), (cj, sj) = centres[i], centres[j]
            if float(np.linalg.norm(ci - cj)) <= LINK_RATIO * (si + sj) / 2:
                links.append({"a": i + 1, "b": j + 1})
    return {"cards": cards, "connections": links, "links_source": "markers"}


def resolve_markers(data: dict, registry: dict, off: set | None = None) -> dict:
    """Áp dụng nguyên tố đã thêm và đã xóa cho kết quả dựng sẵn: mã đã gán nhãn có kí hiệu, nguyên tố đã xóa thành "?" kèm số hiệu mã."""
    gone = {CARD_ELEMENTS[m]: m for m in (off or ())}
    cards = []
    for c in data.get("cards", []):
        if c.get("symbol") == "?" and c.get("marker") in registry:
            c = {**c, "symbol": registry[c["marker"]]}
        elif c.get("symbol") in gone:
            c = {**c, "symbol": "?", "marker": gone[c["symbol"]]}
        cards.append(c)
    return {**data, "cards": cards}
