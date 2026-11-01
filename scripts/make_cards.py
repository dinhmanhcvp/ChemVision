"""Tạo bộ thẻ nguyên tố in được (PDF khổ A4) cho từng lớp THCS.

Mỗi thẻ là hình lục giác (đối cạnh 40 mm) tô màu theo nguyên tố, có kí hiệu lớn, tên nguyên tố và một mã ArUco ở
chính giữa (cạnh mã = đối cạnh / 2,2, khớp với `chem_vision.markers.CARD_TO_MARKER`). Mã giúp phần mềm đọc thẻ ngoại
tuyến, nhanh và chính xác; kí hiệu và màu giúp học sinh nhìn là biết.

Chạy: python scripts/make_cards.py        (ghi vào public/the-in/)
"""
from __future__ import annotations

import math
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from chem_vision.core import DATABASE  # noqa: E402
from chem_vision.curriculum import COLORS, ELEMENT_NAMES, GRADE_TITLES  # noqa: E402
from chem_vision.markers import CARD_TO_MARKER, marker_image  # noqa: E402

DPI = 300
MM = DPI / 25.4
PAGE_W, PAGE_H = round(210 * MM), round(297 * MM)
FLAT_MM = 40.0                               # đối cạnh của thẻ lục giác
CELL_W_MM, CELL_H_MM = 48.0, 44.0            # ô lưới trên trang (4 cột x 6 hàng = 24 thẻ mỗi trang)
COLS, ROWS = 4, 6
MARGIN_X_MM, MARGIN_Y_MM = 9.0, 16.0
SETS = 2                                     # số bộ: đủ để một nhóm ghép hai phân tử cùng lúc

FONT_DIRS = [r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "/usr/share/fonts/truetype/liberation"]


def font(size_pt: float, bold: bool = False):
    names = ["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else \
            ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
    for d in FONT_DIRS:
        for n in names:
            path = os.path.join(d, n)
            if os.path.exists(path):
                return ImageFont.truetype(path, round(size_pt * DPI / 72))
    return ImageFont.load_default()


def deck_counts(grade: int) -> Counter:
    """Số thẻ mỗi nguyên tố: đủ để ghép bất kỳ chất nào đến lớp này, nhân với SETS (hai phân tử cùng lúc)."""
    need: Counter = Counter()
    for s in DATABASE:
        if s.grade <= grade:
            for sym, n in s.graph.composition().items():
                need[sym] = max(need[sym], n)
    return Counter({sym: n * SETS for sym, n in need.items()})


def hexagon(cx, cy, flat_px):
    r = flat_px / math.sqrt(3)
    return [(cx + r * math.cos(math.pi / 3 * k), cy + r * math.sin(math.pi / 3 * k)) for k in range(6)]


def draw_card(img: Image.Image, symbol: str, cx: float, cy: float) -> None:
    d = ImageDraw.Draw(img)
    flat = FLAT_MM * MM
    colour = COLORS.get(symbol, (220, 220, 220))
    soft = tuple(int(c * 0.55 + 255 * 0.45) for c in colour)          # màu nhạt để mã đen trắng nổi rõ
    hexa = hexagon(cx, cy, flat)
    d.polygon(hexa, fill=soft)
    d.line(hexa + [hexa[0]], fill=(70, 70, 70), width=3)
    m_px = round(FLAT_MM / CARD_TO_MARKER * MM)
    pad = round(m_px * 0.16)                                            # viền trắng quanh mã (bắt buộc để đọc được)
    d.rectangle([cx - m_px / 2 - pad, cy - m_px / 2 - pad, cx + m_px / 2 + pad, cy + m_px / 2 + pad], fill="white")
    mk = Image.fromarray(marker_image(symbol, m_px)).convert("RGB")
    img.paste(mk, (round(cx - m_px / 2), round(cy - m_px / 2)))
    top_mid = ((cy - flat / 2) + (cy - m_px / 2 - pad)) / 2             # giữa dải trống phía trên mã
    bottom_mid = ((cy + flat / 2) + (cy + m_px / 2 + pad)) / 2
    d.text((cx, top_mid), symbol, font=font(21, bold=True), fill=(20, 20, 20), anchor="mm")
    d.text((cx, bottom_mid), ELEMENT_NAMES.get(symbol, ""), font=font(9), fill=(20, 20, 20), anchor="mm")


def sheet(symbols: list[str]) -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    for i, sym in enumerate(symbols):
        col, row = i % COLS, i // COLS
        cx = (MARGIN_X_MM + CELL_W_MM * (col + 0.5)) * MM
        cy = (MARGIN_Y_MM + CELL_H_MM * (row + 0.5)) * MM
        draw_card(img, sym, cx, cy)
    return img


def instructions(grade: int, counts: Counter) -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    x, y = round(20 * MM), round(22 * MM)

    def line(text, f, gap=1.6, fill=(20, 20, 20)):
        nonlocal y
        d.text((x, y), text, font=f, fill=fill)
        y += round(f.size * gap)

    line("CHEM VISION: bộ thẻ nguyên tố", font(26, True), 1.5, (47, 84, 150))
    line(GRADE_TITLES[grade], font(14), 2.0)
    for t in ["1. In trên giấy A4, tỉ lệ 100% (không chọn \"Vừa trang\"). Nên in giấy dày hoặc ép nhựa.",
              "2. Cắt theo viền xám của từng thẻ lục giác.",
              "3. Ghép các thẻ của MỘT phân tử sao cho các cạnh chạm sát nhau; để các phân tử khác nhau cách xa ít nhất một thẻ.",
              "4. Đặt thẻ lên nền trơn, khác màu thẻ, đủ sáng, rồi chụp từ trên xuống hoặc đưa vào camera.",
              "5. Không che mã vuông đen trắng ở giữa mỗi thẻ: đó là thứ giúp phần mềm đọc thẻ không cần Internet.",
              "6. Mỗi thẻ có kí hiệu, tên và màu nguyên tố để học sinh nhận ra bằng mắt."]:
        for part in wrap(t, 88):
            line(part, font(12), 1.5)
        y += round(2 * MM)
    y += round(6 * MM)
    line("Số thẻ trong bộ (đủ để ghép bất kỳ chất nào đến lớp này, hai phân tử cùng lúc):", font(12, True), 1.8)
    for sym, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        row_y, f = y, font(12)
        d.text((x, row_y), sym, font=font(12, True), fill=(20, 20, 20))
        d.text((x + round(14 * MM), row_y), ELEMENT_NAMES.get(sym, ""), font=f, fill=(20, 20, 20))
        d.text((x + round(55 * MM), row_y), f"{n} thẻ", font=f, fill=(20, 20, 20))
        y += round(f.size * 1.45)
    return img


def wrap(text: str, width: int):
    words, cur, out = text.split(), "", []
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    out.append(cur)
    return out


def build(grade: int) -> tuple[list[Image.Image], Counter]:
    counts = deck_counts(grade)
    symbols = [sym for sym, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) for _ in range(n)]
    pages = [instructions(grade, counts)]
    per_page = COLS * ROWS
    for i in range(0, len(symbols), per_page):
        pages.append(sheet(symbols[i:i + per_page]))
    return pages, counts


def main(out_dir: str | None = None) -> list[str]:
    out_dir = out_dir or os.path.join(ROOT, "public", "the-in")
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for grade in (7, 8, 9):
        pages, counts = build(grade)
        path = os.path.join(out_dir, f"bo-the-lop-{grade}.pdf")
        pages[0].save(path, "PDF", resolution=DPI, save_all=True, append_images=pages[1:], quality=82)
        written.append(path)
        print(f"lớp {grade}: {sum(counts.values())} thẻ, {len(pages)} trang -> {os.path.relpath(path, ROOT)} "
              f"({os.path.getsize(path) / 1e6:.1f} MB)")
    return written


if __name__ == "__main__":
    main()
