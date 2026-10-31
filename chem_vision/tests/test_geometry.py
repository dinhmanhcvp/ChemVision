import json
import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision.core import analyze
from chem_vision.geometry import apply_geometry, card_links, valid_box
from chem_vision.recognizer import GeminiRecognizer

W, H, R = 640, 480, 50          # ảnh 640 x 480, thẻ lục giác bán kính R (cạnh nhọn nằm ngang)
TABLE = (60, 90, 130)           # màu mặt bàn (BGR)


def table():
    img = np.full((H, W, 3), TABLE, dtype=np.uint8)
    rng = np.random.default_rng(1)
    for _ in range(300):        # vân gỗ: các vệt sẫm ngắn, giống ảnh thật
        x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
        cv2.line(img, (x, y), (x + int(rng.integers(10, 40)), y), (40, 60, 95), 1)
    return img


def hexagon(cx, cy, r=R):
    return np.array([(cx + r * np.cos(np.pi / 3 * k), cy + r * np.sin(np.pi / 3 * k)) for k in range(6)], np.int32)


def draw(img, cx, cy, colour):
    cv2.fillPoly(img, [hexagon(cx, cy)], colour)


def card(i, sym, cx, cy):
    r = R
    return {"id": i, "symbol": sym, "confidence": 0.95,
            "box_2d": [(cy - r) * 1000 / H, (cx - r) * 1000 / W, (cy + r) * 1000 / H, (cx + r) * 1000 / W]}


FLAT = R * 3 ** 0.5             # khoảng cách hai tâm khi hai thẻ chạm cạnh


def water_scene(gap_between_h2=0, far=False):
    """H–O–H: O ở giữa, hai H chạm hai bên; kèm một thẻ Cl đứng riêng (xa hoặc không)."""
    img = table()
    ox, oy = 250, 240
    pts = [(ox - FLAT - 0, oy), (ox, oy), (ox + FLAT + gap_between_h2, oy)]
    for (x, y), colour in zip(pts, [(200, 200, 240), (120, 120, 230), (200, 200, 240)]):
        draw(img, int(x), int(y), colour)
    cards = [card(1, "H", *pts[0]), card(2, "O", *pts[1]), card(3, "H", *pts[2])]
    cx = 560 if far else 250 + FLAT * 2 + 20
    if far:
        draw(img, cx, 400, (150, 220, 150))
        cards.append(card(4, "Cl", cx, 400))
    return img, {"cards": cards, "connections": []}


class Links(unittest.TestCase):
    def links(self, img, data):
        pairs, info = card_links(img, data["cards"])
        return {tuple(sorted(p)) for p in pairs}, info

    def test_touching_cards_linked_far_card_not(self):
        img, data = water_scene(far=True)
        links, _ = self.links(img, data)
        self.assertEqual(links, {(1, 2), (2, 3)})           # H–O và O–H; H và H không chạm nhau

    def test_gap_means_no_link(self):
        img, data = water_scene(gap_between_h2=45)          # khe hở lớn giữa O và H phải
        links, _ = self.links(img, data)
        self.assertEqual(links, {(1, 2)})

    def test_tiny_gap_still_counts_as_touching(self):
        img, data = water_scene(gap_between_h2=3)           # khe hở mấy điểm ảnh: sai số khi đặt thẻ
        links, _ = self.links(img, data)
        self.assertEqual(links, {(1, 2), (2, 3)})

    def test_wood_grain_does_not_break_gap(self):
        img, data = water_scene(gap_between_h2=60)          # khe lớn, vân gỗ không được làm "nối" hai thẻ
        links, info = self.links(img, data)
        self.assertNotIn((2, 3), links)

    def test_end_to_end_water(self):
        img, data = water_scene(far=True)
        out = apply_geometry(img, data)
        self.assertEqual(out["links_source"], "geometry")
        a = analyze(json.dumps(out))
        self.assertEqual(a.matches(), ["H2O"])
        self.assertEqual([r.kind for _, r in a.clusters], ["MATCH", "SUGGEST"])    # H2O và Cl đứng riêng

    def test_wrong_assembly_detected_by_geometry(self):
        """H–H–O (O ở cuối): hình học phải ra sai liên kết, không nhầm thành nước."""
        img = table()
        xs = [150, 150 + FLAT, 150 + 2 * FLAT]
        for x, colour in zip(xs, [(200, 200, 240), (200, 200, 240), (120, 120, 230)]):
            draw(img, int(x), 240, colour)
        data = {"cards": [card(1, "H", xs[0], 240), card(2, "H", xs[1], 240), card(3, "O", xs[2], 240)], "connections": []}
        a = analyze(json.dumps(apply_geometry(img, data)))
        self.assertEqual([r.kind for _, r in a.clusters], ["WRONG_BONDS"])

    def test_missing_box_keeps_ai_links(self):
        img, data = water_scene()
        del data["cards"][1]["box_2d"]
        data["connections"] = [{"a": 1, "b": 2}, {"a": 2, "b": 3}]
        out = apply_geometry(img, data)
        self.assertEqual(out["links_source"], "ai")
        self.assertEqual(len(out["connections"]), 2)

    def test_duplicate_card_removed(self):
        img, data = water_scene()
        data["cards"].append({**data["cards"][1], "id": 9, "confidence": 0.5})      # thẻ O bị liệt kê hai lần
        out = apply_geometry(img, data)
        self.assertEqual([c["id"] for c in out["cards"]], [1, 2, 3])
        self.assertEqual(analyze(json.dumps(out)).matches(), ["H2O"])

    def test_same_symbol_different_place_kept(self):
        img, data = water_scene()
        self.assertEqual(len(apply_geometry(img, data)["cards"]), 3)               # hai thẻ H ở hai nơi khác nhau

    def test_valid_box(self):
        self.assertTrue(valid_box([10, 20, 300, 400]))
        for bad in (None, [1, 2, 3], [300, 10, 10, 20], [0, 0, 1001, 10], ["a", 1, 2, 3]):
            self.assertFalse(valid_box(bad))


class FakeGenai:
    def __init__(self, text):
        self.text, self.models = text, self

    def generate_content(self, model, contents, config):
        return type("R", (), {"text": self.text})()


class RecognizerUsesGeometry(unittest.TestCase):
    def test_ai_links_overridden(self):
        img, data = water_scene(far=True)
        data["connections"] = [{"a": 1, "b": 3}, {"a": 1, "b": 2}, {"a": 2, "b": 3}, {"a": 3, "b": 4}]   # AI đoán dư
        rec = GeminiRecognizer("k", client=FakeGenai(json.dumps(data)))
        out = json.loads(rec.recognize(img))
        self.assertEqual({tuple(sorted((c["a"], c["b"]))) for c in out["connections"]}, {(1, 2), (2, 3)})
        self.assertEqual(out["links_source"], "geometry")

    def test_ai_mode_keeps_ai_links(self):
        img, data = water_scene()
        data["connections"] = [{"a": 1, "b": 3}]
        rec = GeminiRecognizer("k", client=FakeGenai(json.dumps(data)), link_mode="ai")
        self.assertEqual(json.loads(rec.recognize(img))["connections"], [{"a": 1, "b": 3}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
