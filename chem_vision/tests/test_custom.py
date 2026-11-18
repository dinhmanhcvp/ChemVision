import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision import custom
from chem_vision.core import ATOMIC_MASS, ELEMENT_NAMES
from chem_vision.web import handle_analyze

# Hai thẻ Au nối nhau: chất tự thêm "Au2" (không có trong cơ sở dữ liệu)
RAW = json.dumps({"cards": [{"id": 1, "symbol": "Au", "confidence": 0.95}, {"id": 2, "symbol": "Au", "confidence": 0.95}],
                  "connections": [{"a": 1, "b": 2}]})


class FakeRecognizer:
    last_model = "giả"

    def recognize_jpeg(self, jpeg, frame):
        return RAW


def sub(**kw):
    return {"formula": "Au2", "name": "vàng hai nguyên tử", "atoms": ["Au", "Au"], "bonds": [[0, 1]], **kw}


class Custom(unittest.TestCase):
    def test_parse_rejects_bad_input(self):
        for bad in ({"substances": [sub(atoms=["Xx", "Au"])]},
                    {"substances": [sub(bonds=[[0, 5]])]},
                    {"substances": [sub(atoms=["Au", "Au", "Au"], bonds=[[0, 1]])]},     # nguyên tử rời
                    {"substances": [sub(formula="")]},
                    {"elements": [{"symbol": "Au", "name": "vàng", "mass": -1}]},
                    {"substances": [sub()] * 21}, "x"):
            with self.assertRaises(ValueError, msg=bad):
                custom.parse(bad)

    def test_applied_adds_then_restores_element_tables(self):
        names, masses = dict(ELEMENT_NAMES), dict(ATOMIC_MASS)
        with custom.applied({"elements": [{"symbol": "Pt", "name": "bạch kim", "mass": 195}]}) as db:
            self.assertEqual(ELEMENT_NAMES["Pt"], "bạch kim")
            self.assertEqual(ATOMIC_MASS["Pt"], 195)
        self.assertEqual((ELEMENT_NAMES, ATOMIC_MASS), (names, masses))

    def test_custom_substance_matched_only_when_sent(self):
        payload = {"custom": {"substances": [sub()]}}
        with_it = self.analyze(payload)
        self.assertEqual(with_it["clusters"][0]["kind"], "MATCH")
        self.assertEqual(with_it["clusters"][0]["substance"]["formula"], "Au2")
        self.assertNotEqual(self.analyze({})["clusters"][0]["kind"], "MATCH")

    def test_isomer_custom_substances_told_apart(self):
        # hai chất tự thêm cùng thành phần Au3 nhưng khác cấu trúc: chuỗi và vòng
        raw = json.dumps({"cards": [{"id": i, "symbol": "Au", "confidence": 0.95} for i in (1, 2, 3)],
                          "connections": [{"a": 1, "b": 2}, {"a": 2, "b": 3}]})
        chain = {"formula": "Au3-chuoi", "name": "chuỗi", "atoms": ["Au"] * 3, "bonds": [[0, 1], [1, 2]]}
        ring = {"formula": "Au3-vong", "name": "vòng", "atoms": ["Au"] * 3, "bonds": [[0, 1], [1, 2], [0, 2]]}
        with custom.applied({"substances": [ring, chain]}) as db:
            from chem_vision.core import analyze
            a = analyze(raw, db)
        self.assertEqual(a.clusters[0][1].substance.formula, "Au3-chuoi")

    def test_invalid_custom_is_400_before_recognizing(self):
        status, body = handle_analyze({"demo": "nuoc", "custom": {"substances": [sub(atoms=["Xx", "Au"])]}}, {}, {})
        self.assertEqual(status, 400)

    def analyze(self, extra):
        import base64, cv2, numpy as np
        ok, buf = cv2.imencode(".jpg", np.full((64, 64, 3), 128, np.uint8))
        payload = {"image": base64.b64encode(buf.tobytes()).decode(), "code": "x", **extra}
        status, body = handle_analyze(payload, {"ACCESS_CODE": "x", "GEMINI_API_KEY": "k"}, {}, recognizer=FakeRecognizer())
        self.assertEqual(status, 200, body)
        return body


if __name__ == "__main__":
    unittest.main()
