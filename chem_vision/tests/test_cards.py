import os
import re
import sys
import unittest
from collections import Counter

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import make_cards as mc  # noqa: E402
from chem_vision.core import DATABASE  # noqa: E402
from chem_vision.markers import cards_from_markers  # noqa: E402


def to_bgr(pil_image, width=None):
    arr = np.array(pil_image.convert("RGB"))[:, :, ::-1].copy()
    if width:
        h = round(arr.shape[0] * width / arr.shape[1])
        arr = cv2.resize(arr, (width, h), interpolation=cv2.INTER_AREA)
    return arr


class PrintedCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decks = {g: mc.build(g) for g in (7, 8, 9)}

    def test_deck_can_build_every_substance_of_its_grade_twice(self):
        for grade, (pages, counts) in self.decks.items():
            for s in DATABASE:
                if s.grade <= grade:
                    for sym, n in s.graph.composition().items():
                        self.assertGreaterEqual(counts[sym], 2 * n, (grade, s.key, sym))

    def test_page_count_matches_cards(self):
        for grade, (pages, counts) in self.decks.items():
            self.assertEqual(len(pages) - 1, -(-sum(counts.values()) // (mc.COLS * mc.ROWS)), grade)

    def test_printing_then_detecting_reads_every_card(self):
        """Vòng khép kín: in thẻ rồi chụp lại phải đọc ra đúng kí hiệu và đúng số lượng từng thẻ."""
        for grade, (pages, counts) in self.decks.items():
            read = Counter()
            for page in pages[1:]:
                data = cards_from_markers(to_bgr(page))
                read.update(c["symbol"] for c in data["cards"])
            self.assertEqual(read, counts, grade)

    def test_cards_still_readable_when_photographed_smaller_and_tilted(self):
        pages, counts = self.decks[7]
        page = pages[1]
        expected = Counter()
        symbols = [sym for sym, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) for _ in range(n)]
        expected.update(symbols[:mc.COLS * mc.ROWS])
        img = to_bgr(page, width=1100)
        mat = cv2.getRotationMatrix2D((img.shape[1] / 2, img.shape[0] / 2), 9, 1.0)
        img = cv2.warpAffine(img, mat, (img.shape[1], img.shape[0]), borderValue=(255, 255, 255))
        img = cv2.GaussianBlur(img, (0, 0), 1.0)
        data = cards_from_markers(img)
        self.assertEqual(Counter(c["symbol"] for c in data["cards"]), expected)

    def test_printed_cards_on_a_sheet_are_apart_so_no_links_are_invented_far_away(self):
        pages, _ = self.decks[7]
        data = cards_from_markers(to_bgr(pages[1]))
        # các thẻ trên tờ in cách nhau theo lưới; mỗi thẻ chỉ có thể "chạm" tối đa các thẻ sát bên
        degree = Counter()
        for e in data["connections"]:
            degree[e["a"]] += 1
            degree[e["b"]] += 1
        self.assertLessEqual(max(degree.values(), default=0), 4)

    def test_pdfs_are_written(self):
        out = os.path.join(ROOT, "public", "the-in")
        for grade, (pages, _) in self.decks.items():
            path = os.path.join(out, f"bo-the-lop-{grade}.pdf")
            self.assertTrue(os.path.isfile(path), path)
            raw = open(path, "rb").read()
            self.assertTrue(raw.startswith(b"%PDF"))
            self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", raw)), len(pages), grade)
            self.assertLess(len(raw), 5 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main(verbosity=2)
