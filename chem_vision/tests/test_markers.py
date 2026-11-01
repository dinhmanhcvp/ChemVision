import json
import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision.core import analyze
from chem_vision.curriculum import CARD_ELEMENTS
from chem_vision.markers import CARD_TO_MARKER, cards_from_markers, marker_image
from chem_vision.quality import assess

W, H = 800, 600
MARKER = 44                          # cạnh mã (điểm ảnh)
FLAT = MARKER * CARD_TO_MARKER       # đối cạnh thẻ
R = FLAT / 3 ** 0.5                  # bán kính thẻ lục giác
TABLE = (200, 205, 210)


def scene(cards, rotate=0.0, blur=0, noise=0):
    """cards: [(kí hiệu, tâm x, tâm y)]. Vẽ thẻ lục giác tô màu và dán mã ArUco ở giữa."""
    img = np.full((H, W, 3), TABLE, np.uint8)
    for sym, cx, cy in cards:
        hexa = np.array([(cx + R * np.cos(np.pi / 3 * k), cy + R * np.sin(np.pi / 3 * k)) for k in range(6)], np.int32)
        cv2.fillPoly(img, [hexa], (120, 160, 220))
        cv2.polylines(img, [hexa], True, (60, 60, 60), 2)
        m = cv2.cvtColor(marker_image(sym, MARKER), cv2.COLOR_GRAY2BGR)
        x0, y0 = int(cx - MARKER / 2), int(cy - MARKER / 2)
        img[y0:y0 + MARKER, x0:x0 + MARKER] = m
    if rotate:
        mat = cv2.getRotationMatrix2D((W / 2, H / 2), rotate, 1.0)
        img = cv2.warpAffine(img, mat, (W, H), borderValue=TABLE)
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    if noise:
        img = np.clip(img.astype(int) + np.random.default_rng(0).normal(0, noise, img.shape), 0, 255).astype(np.uint8)
    return img


def water(far_cl=True):
    cards = [("H", 300 - FLAT, 250), ("O", 300, 250), ("H", 300 + FLAT, 250)]
    if far_cl:
        cards.append(("Cl", 300 + 4 * FLAT, 450))
    return cards


class Markers(unittest.TestCase):
    def links(self, data):
        sym = {c["id"]: c["symbol"] for c in data["cards"]}
        return sorted(tuple(sorted((sym[e["a"]], sym[e["b"]]))) for e in data["connections"])

    def test_water_and_separate_card(self):
        data = cards_from_markers(scene(water()))
        self.assertEqual(sorted(c["symbol"] for c in data["cards"]), ["Cl", "H", "H", "O"])
        self.assertEqual(self.links(data), [("H", "O"), ("H", "O")])
        self.assertEqual(data["links_source"], "markers")

    def test_end_to_end_matches_water_and_suggests_for_lone_cl(self):
        a = analyze(json.dumps(cards_from_markers(scene(water()))))
        self.assertEqual(a.matches(), ["H2O"])
        self.assertEqual([r.kind for _, r in a.clusters].count("SUGGEST"), 1)

    def test_rotated_blurred_noisy_still_read(self):
        data = cards_from_markers(scene(water(), rotate=27, blur=1.2, noise=6))
        self.assertEqual(sorted(c["symbol"] for c in data["cards"]), ["Cl", "H", "H", "O"])
        self.assertEqual(self.links(data), [("H", "O"), ("H", "O")])

    def test_wrong_assembly_h_h_o(self):
        cards = [("H", 200, 250), ("H", 200 + FLAT, 250), ("O", 200 + 2 * FLAT, 250)]
        a = analyze(json.dumps(cards_from_markers(scene(cards))))
        self.assertEqual([r.kind for _, r in a.clusters], ["WRONG_BONDS"])

    def test_gap_between_cards_breaks_the_link(self):
        cards = [("H", 300 - FLAT, 250), ("O", 300, 250), ("H", 300 + FLAT + FLAT * 0.6, 250)]
        data = cards_from_markers(scene(cards))
        self.assertEqual(self.links(data), [("H", "O")])

    def test_hexagonal_cluster_methane(self):
        # C ở giữa, bốn H quanh: bốn H phải nối với C, không nối với nhau nếu ở cách xa nhau
        d = FLAT
        cards = [("C", 400, 300), ("H", 400 + d, 300), ("H", 400 - d, 300), ("H", 400, 300 + d), ("H", 400, 300 - d)]
        a = analyze(json.dumps(cards_from_markers(scene(cards))))
        self.assertEqual(a.matches(), ["CH4"])

    def test_no_marker_returns_none(self):
        self.assertIsNone(cards_from_markers(np.full((H, W, 3), TABLE, np.uint8)))

    def test_ids_out_of_range_ignored(self):
        import cv2.aruco as ar
        d = ar.getPredefinedDictionary(ar.DICT_4X4_50)
        img = np.full((H, W, 3), TABLE, np.uint8)
        img[100:200, 100:200] = cv2.cvtColor(ar.generateImageMarker(d, 45, 100), cv2.COLOR_GRAY2BGR)   # id 45 > số nguyên tố
        self.assertIsNone(cards_from_markers(img))

    def test_every_element_has_its_own_readable_marker(self):
        for k, sym in enumerate(CARD_ELEMENTS):
            img = np.full((300, 300, 3), TABLE, np.uint8)
            img[50:250, 50:250] = cv2.cvtColor(marker_image(sym, 200), cv2.COLOR_GRAY2BGR)
            data = cards_from_markers(img)
            self.assertEqual([c["symbol"] for c in data["cards"]], [sym], sym)


class Quality(unittest.TestCase):
    def good(self):
        return scene(water())

    def test_good_image_ok(self):
        q = assess(self.good())
        self.assertTrue(q["ok"])
        self.assertEqual(q["blocking"], [])

    def test_dark(self):
        q = assess((self.good() * 0.15).astype(np.uint8))
        self.assertFalse(q["ok"])
        self.assertTrue(any("tối" in w for w in q["blocking"]))

    def test_slightly_dark_only_warns(self):
        tile = np.indices((H, W)).sum(axis=0) // 8 % 2            # bàn cờ: ảnh nét, tương phản cao
        img = np.repeat(np.where(tile == 0, 20, 180).astype(np.uint8)[..., None], 3, axis=2)
        q = assess((img * 0.6).astype(np.uint8))                  # độ sáng trung bình khoảng 60
        self.assertTrue(q["ok"], q)
        self.assertTrue(any("tối" in w for w in q["warnings"]))

    def test_blur(self):
        q = assess(cv2.GaussianBlur(self.good(), (0, 0), 12))
        self.assertFalse(q["ok"])
        self.assertTrue(any("mờ" in w for w in q["blocking"]))

    def test_glare(self):
        img = self.good()
        img[:, :] = 255
        q = assess(img)
        self.assertFalse(q["ok"])

    def test_flat_image_lacks_contrast(self):
        q = assess(np.full((H, W, 3), 128, np.uint8))
        self.assertFalse(q["ok"])
        self.assertTrue(any("tương phản" in w for w in q["blocking"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
