"""Tạo thẻ trống in được (PDF khổ A4): mỗi thẻ có sẵn một mã ArUco chưa gán nguyên tố (từ số 22 trở đi).

Dùng để thử nguyên tố mới: viết kí hiệu và tên nguyên tố lên thẻ, nhập số mã in trên thẻ ở thẻ Thêm trong ứng dụng,
đặt tên là ứng dụng nhận ra thẻ. Trước khi đặt tên, thẻ cho kết quả "chưa gán nhãn".

Chạy: python scripts/make_the_trong.py        (ghi public/the-in/the-trong.pdf)
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw  # noqa: E402

import make_cards as mc  # noqa: E402
from chem_vision.curriculum import CARD_ELEMENTS  # noqa: E402
from chem_vision.markers import CARD_TO_MARKER, DICT_ID_COUNT, marker_image  # noqa: E402

COUNT = 12                                   # số thẻ trống trên một tờ (3 hàng x 4 cột)


def blank_card(img: Image.Image, marker: int, cx: float, cy: float) -> None:
    d = ImageDraw.Draw(img)
    flat = mc.FLAT_MM * mc.MM
    hexa = mc.hexagon(cx, cy, flat)
    d.polygon(hexa, fill=(250, 250, 245))
    d.line(hexa + [hexa[0]], fill=(70, 70, 70), width=3)
    m_px = round(mc.FLAT_MM / CARD_TO_MARKER * mc.MM)
    pad = round(m_px * 0.16)
    d.rectangle([cx - m_px / 2 - pad, cy - m_px / 2 - pad, cx + m_px / 2 + pad, cy + m_px / 2 + pad], fill="white")
    img.paste(Image.fromarray(marker_image(marker, m_px)).convert("RGB"), (round(cx - m_px / 2), round(cy - m_px / 2)))
    top = ((cy - flat / 2) + (cy - m_px / 2 - pad)) / 2
    bottom = ((cy + flat / 2) + (cy + m_px / 2 + pad)) / 2
    d.text((cx, top), "Kí hiệu: ____", font=mc.font(10), fill=(90, 90, 90), anchor="mm")           # chỗ viết kí hiệu
    d.text((cx, bottom - mc.MM * 2.4), "Tên: ________", font=mc.font(9), fill=(90, 90, 90), anchor="mm")
    d.text((cx, bottom + mc.MM * 2.6), f"mã {marker}", font=mc.font(8, bold=True), fill=(20, 20, 20), anchor="mm")


def sheet(markers: list[int]) -> Image.Image:
    img = Image.new("RGB", (mc.PAGE_W, mc.PAGE_H), "white")
    for i, m in enumerate(markers):
        col, row = i % mc.COLS, i // mc.COLS
        blank_card(img, m, (mc.MARGIN_X_MM + mc.CELL_W_MM * (col + 0.5)) * mc.MM, (mc.MARGIN_Y_MM + mc.CELL_H_MM * (row + 0.5)) * mc.MM)
    return img


def instructions(first: int, last: int) -> Image.Image:
    img = Image.new("RGB", (mc.PAGE_W, mc.PAGE_H), "white")
    d = ImageDraw.Draw(img)
    x, y = round(20 * mc.MM), round(22 * mc.MM)
    d.text((x, y), "CHEM VISION: thẻ trống để thử nguyên tố mới", font=mc.font(22, True), fill=(47, 84, 150))
    y += round(18 * mc.MM)
    steps = [
        "1. In trang sau trên giấy A4, tỉ lệ 100% (không chọn \"Vừa trang\"), rồi cắt theo viền từng thẻ lục giác.",
        f"2. Mỗi thẻ có một mã vuông riêng (mã {first} đến {last}). Viết kí hiệu và tên nguyên tố lên thẻ, ví dụ Ti, titan. Không che mã vuông.",
        "3. Mở ứng dụng, vào thẻ Thêm, mục Thêm nguyên tố mới. Nhập số mã in trên thẻ rồi nhấn Thêm nguyên tố mới.",
        "4. Trước khi đặt tên: ghép thẻ vào camera, ứng dụng báo thẻ chưa có nhãn nên chưa biết đây là chất gì.",
        "5. Gõ tên nguyên tố (ví dụ titan) rồi nhấn Lưu tên. Ứng dụng tự tra nguyên tử khối và hóa trị.",
        "6. Ghép thẻ vừa đặt tên với các thẻ khác: ứng dụng tự báo cách ghép đúng hay sai theo hóa trị, không cần khai báo chất.",
        "7. Muốn thử nhận diện chất có sẵn: vào mục Các chất hiện có, nhấn Xóa một chất, ghép chất đó thì không nhận ra; nhấn Thêm lại thì nhận ra như cũ.",
    ]
    for s in steps:
        for part in mc.wrap(s, 88):
            d.text((x, y), part, font=mc.font(12), fill=(20, 20, 20))
            y += round(12 * mc.DPI / 72 * 1.5)
        y += round(2 * mc.MM)
    return img


def main(out_dir: str | None = None) -> str:
    out_dir = out_dir or os.path.join(ROOT, "public", "the-in")
    os.makedirs(out_dir, exist_ok=True)
    first = len(CARD_ELEMENTS)
    markers = list(range(first, min(first + COUNT, DICT_ID_COUNT)))
    pages = [instructions(markers[0], markers[-1]), sheet(markers)]
    path = os.path.join(out_dir, "the-trong.pdf")
    pages[0].save(path, "PDF", resolution=mc.DPI, save_all=True, append_images=pages[1:], quality=82)
    print(f"{len(markers)} thẻ trống (mã {markers[0]} đến {markers[-1]}) -> {os.path.relpath(path, ROOT)} ({os.path.getsize(path) / 1e6:.1f} MB)")
    return path


if __name__ == "__main__":
    main()
