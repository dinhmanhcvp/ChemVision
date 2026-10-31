"""Tính liên kết giữa các thẻ bằng hình học (OpenCV), thay cho việc để AI đoán thẻ nào chạm thẻ nào.

Gemini chỉ đọc kí hiệu và cho khung bao (box_2d) của từng thẻ. Hai thẻ được coi là chạm nhau khi:
1. tâm hai thẻ không quá xa so với kích thước thẻ, và
2. dọc đoạn nối hai tâm không có khe hở nhìn thấy mặt bàn.
Thẻ chồng lên nhau hoặc sát cạnh nhau thì đoạn nối không có mặt bàn, nên được tính là chạm.
"""
from __future__ import annotations

import numpy as np

MAX_RATIO = 1.7      # khoảng cách hai tâm tối đa, tính theo kích thước thẻ
GAP_FRAC = 0.06      # khe hở liên tục tối đa (theo kích thước thẻ) vẫn coi là chạm
BG_DIST = 30.0       # ngưỡng khoảng cách màu (Lab) để coi một điểm là mặt bàn
CLOSE_PX = 9         # nhân đóng: lấp vệt vân gỗ hẹp
DUP_IOU = 0.5        # hai khung bao cùng kí hiệu trùm nhau từ mức này là một thẻ bị liệt kê hai lần
OPEN_PX = 9          # nhân mở: xóa đốm "mặt bàn" nhỏ trên thẻ


def valid_box(box) -> bool:
    try:
        ymin, xmin, ymax, xmax = (float(v) for v in box)
    except (TypeError, ValueError):
        return False
    return 0 <= ymin < ymax <= 1000 and 0 <= xmin < xmax <= 1000


def box_px(box, width: int, height: int):
    """box_2d = [ymin, xmin, ymax, xmax] trên thang 0-1000 -> (x0, y0, x1, y1) tính bằng điểm ảnh."""
    ymin, xmin, ymax, xmax = (float(v) for v in box)
    return xmin * width / 1000, ymin * height / 1000, xmax * width / 1000, ymax * height / 1000


def background_mask(frame_bgr) -> np.ndarray:
    """Mặt nạ mặt bàn: điểm nào có màu giống màu mặt bàn. Màu bàn lấy ở viền ảnh (nhóm màu phổ biến nhất)."""
    import cv2
    img = cv2.GaussianBlur(frame_bgr, (5, 5), 0)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    b = max(int(min(h, w) * 0.05), 2)
    border = np.concatenate([lab[:b].reshape(-1, 3), lab[-b:].reshape(-1, 3),
                             lab[:, :b].reshape(-1, 3), lab[:, -b:].reshape(-1, 3)])
    q = (border // 16).astype(np.int32)
    keys = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    top = np.bincount(keys).argmax()
    bg = border[keys == top].mean(axis=0)
    mask = (np.linalg.norm(lab - bg, axis=2) < BG_DIST).astype(np.uint8)
    k = lambda n: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k(CLOSE_PX))   # nối các vệt vân gỗ sẫm vào mặt bàn
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k(OPEN_PX))     # bỏ các đốm nhỏ nằm trên thẻ (chữ sẫm màu)
    return mask.astype(bool)


def card_links(frame_bgr, cards: list[dict]):
    """cards: [{'id', 'box_2d'}]. Trả về (danh sách cặp id chạm nhau, thông tin từng cặp để gỡ lỗi)."""
    h, w = frame_bgr.shape[:2]
    mask = background_mask(frame_bgr)
    boxes = {c["id"]: box_px(c["box_2d"], w, h) for c in cards}
    sizes = [((b[2] - b[0]) * (b[3] - b[1])) ** 0.5 for b in boxes.values()]
    size = float(np.median(sizes))
    centres = {i: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2) for i, b in boxes.items()}
    ids = list(boxes)
    links, info = [], []
    for ai in range(len(ids)):
        for bi in range(ai + 1, len(ids)):
            a, b = ids[ai], ids[bi]
            (ax, ay), (bx, by) = centres[a], centres[b]
            dist = float(np.hypot(ax - bx, ay - by))
            ratio = dist / size
            if ratio > MAX_RATIO:
                continue
            n = max(int(dist), 2)
            xs = np.clip(np.linspace(ax, bx, n).round().astype(int), 0, w - 1)
            ys = np.clip(np.linspace(ay, by, n).round().astype(int), 0, h - 1)
            gap = _longest_run(mask[ys, xs])
            touching = gap < GAP_FRAC * size
            info.append({"a": a, "b": b, "ratio": round(ratio, 2), "gap_px": gap, "touching": touching})
            if touching:
                links.append((a, b))
    return links, {"card_size_px": round(size, 1), "pairs": info}


def _longest_run(flags) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def _iou(a, b) -> float:
    ix = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    iy = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def dedupe_cards(cards: list[dict]) -> list[dict]:
    """Bỏ thẻ bị liệt kê hai lần: cùng kí hiệu và khung bao trùm nhau từ DUP_IOU trở lên (giữ thẻ tin cậy hơn)."""
    kept: list[dict] = []
    for c in sorted(cards, key=lambda c: -float(c.get("confidence") or 0)):
        if valid_box(c.get("box_2d")) and any(
                k.get("symbol") == c.get("symbol") and valid_box(k.get("box_2d"))
                and _iou([float(v) for v in k["box_2d"]], [float(v) for v in c["box_2d"]]) >= DUP_IOU for k in kept):
            continue
        kept.append(c)
    order = {id(c): i for i, c in enumerate(cards)}
    return sorted(kept, key=lambda c: order[id(c)])


def apply_geometry(frame_bgr, data: dict) -> dict:
    """Thay danh sách liên kết do AI trả về bằng liên kết tính từ hình học khi mọi thẻ đều có khung bao hợp lệ."""
    cards = [c for c in data.get("cards") or [] if isinstance(c, dict)]
    cards = dedupe_cards(cards) if cards else cards
    data = {**data, "cards": cards}
    usable = [c for c in cards if isinstance(c, dict) and "id" in c and valid_box(c.get("box_2d"))]
    out = dict(data)
    if not cards or len(usable) != len(cards):
        out["links_source"] = "ai"          # thiếu khung bao: giữ liên kết AI trả về
        return out
    links, info = card_links(frame_bgr, usable)
    out["connections"] = [{"a": a, "b": b} for a, b in links]
    out["links_source"] = "geometry"
    out["geometry"] = info
    return out


def annotate(frame_bgr, data: dict):
    """Vẽ khung bao, kí hiệu và liên kết lên ảnh để người dùng kiểm tra bằng mắt."""
    import cv2
    img = frame_bgr.copy()
    h, w = img.shape[:2]
    centres = {}
    for c in data.get("cards") or []:
        if not valid_box(c.get("box_2d")):
            continue
        x0, y0, x1, y1 = (int(v) for v in box_px(c["box_2d"], w, h))
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 140, 255), 2)
        cv2.putText(img, f"{c.get('id')}:{c.get('symbol')}", (x0 + 4, y0 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        centres[c["id"]] = ((x0 + x1) // 2, (y0 + y1) // 2)
    for e in data.get("connections") or []:
        if e.get("a") in centres and e.get("b") in centres:
            cv2.line(img, centres[e["a"]], centres[e["b"]], (0, 200, 0), 3)
    return img
