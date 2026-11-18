import base64
import json
import os
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision import custom
from chem_vision.core import ATOMIC_MASS, ELEMENT_NAMES, VALENCE, Graph, analyze, cluster_message, match_cluster
from chem_vision.markers import cards_from_markers, marker_image
from chem_vision.web import handle_analyze, handle_custom

PT = {"elements": [{"marker": 22, "name": "bạch kim"}]}


def demo(custom_data=None):
    status, body = handle_analyze({"demo": "Thẻ mới (mã 22) ghép với Cl", "custom": custom_data}, {}, {})
    assert status == 200, body
    return body


class Elements(unittest.TestCase):
    def test_name_only_is_enough_for_known_elements(self):
        registry, rows = custom.parse(PT)
        self.assertEqual(registry, {22: "Pt"})
        self.assertEqual(rows[0][0], "Pt")
        self.assertEqual(rows[0][3], [2, 4])

    def test_unknown_name_asks_for_symbol_and_valence(self):
        with self.assertRaises(custom.NeedMore) as ctx:
            custom.parse({"elements": [{"marker": 22, "name": "chất lạ"}]})
        self.assertEqual(ctx.exception.need, "symbol")
        _, rows = custom.parse({"elements": [{"marker": 22, "name": "chất lạ", "symbol": "Rf", "valence": [4]}]})
        self.assertEqual(rows[0][:1] + rows[0][3:], ("Rf", [4]))

    def test_rejects_bad_input(self):
        for bad in ({"elements": [{"marker": 3, "name": "bạch kim"}]},               # mã của nguyên tố in sẵn
                    {"elements": [{"marker": 99, "name": "bạch kim"}]},
                    {"elements": [{"marker": 22, "name": "oxi"}]},                   # đã có thẻ in sẵn
                    {"elements": [{"marker": 22, "name": ""}]},
                    {"elements": [{"marker": 22, "name": "vàng"}, {"marker": 23, "name": "au"}]},   # trùng nguyên tố
                    {"elements": [{"marker": 22, "name": "vàng"}, {"marker": 22, "name": "chì"}]},  # trùng mã
                    {"elements": [{"marker": 22, "name": "x", "symbol": "Xx", "valence": 1}]},
                    {"elements": "x"}):
            with self.assertRaises(ValueError, msg=bad):
                custom.parse(bad)

    def test_applied_restores_tables(self):
        before = (dict(ELEMENT_NAMES), dict(ATOMIC_MASS), dict(VALENCE))
        _, rows = custom.parse(PT)
        with custom.applied(rows):
            self.assertEqual(VALENCE["Pt"], [2, 4])
        self.assertEqual((ELEMENT_NAMES, ATOMIC_MASS, VALENCE), before)

    def test_marker_image_is_readable_after_png_round_trip(self):
        status, body = handle_custom({"marker": 25})
        self.assertEqual(status, 200)
        png = cv2.imdecode(np.frombuffer(base64.b64decode(body["image"]), np.uint8), cv2.IMREAD_COLOR)
        found = cards_from_markers(png)
        self.assertEqual(found["cards"][0]["marker"], 25)


class PeriodicTable(unittest.TestCase):
    def test_every_element_has_data_and_is_not_preloaded(self):
        from chem_vision.core import ELEMENTS
        from chem_vision.curriculum import CARD_ELEMENTS
        from chem_vision.periodic import EXTRA, lookup
        self.assertEqual(set(EXTRA) | set(CARD_ELEMENTS), ELEMENTS)                 # đủ 118 nguyên tố, không thiếu không thừa
        self.assertFalse(set(EXTRA) & set(CARD_ELEMENTS))
        self.assertEqual(len({v[0] for v in EXTRA.values()}), len(EXTRA))            # tên tiếng Việt không trùng
        for sym, (vi, en, mass, valence) in EXTRA.items():
            self.assertEqual(lookup(vi)[0], sym, sym)
            self.assertEqual(lookup(en)[0], sym, sym)
            self.assertTrue(valence and all(0 <= v <= 8 for v in valence) and mass > 0, sym)
            custom.parse({"elements": [{"marker": 22, "name": vi}]})                 # chỉ cần tên là thêm được
        self.assertNotIn("Ti", VALENCE)                                              # tra cứu không tự thêm nguyên tố vào ứng dụng

    def test_names_ignore_case_and_accents(self):
        from chem_vision.periodic import lookup
        self.assertEqual(lookup("BACH KIM")[0], "Pt")
        self.assertEqual(lookup("Gold")[0], "Au")


class Flow(unittest.TestCase):
    """Câu chuyện ban đầu: thẻ chưa gán nhãn -> chưa biết là gì; đặt tên xong -> tự biết ghép đúng hay sai."""

    def test_unlabeled_then_labeled(self):
        before = demo()
        self.assertEqual(before["status"], "UNLABELED")
        self.assertIn("22", before["message"])
        after = demo(PT)
        self.assertEqual(after["status"], "OK")
        c = after["clusters"][0]
        self.assertEqual((c["kind"], c["substance"]["formula"], c["substance"]["auto"]), ("MATCH", "PtCl2", True))

    def test_valence_decides_right_and_wrong(self):
        _, rows = custom.parse(PT)
        g = lambda labels, edges: Graph.from_edges(labels, edges)
        with custom.applied(rows):
            ok = match_cluster(g(["Pt", "Cl", "Cl"], [(0, 1), (0, 2)]))
            too_many = match_cluster(g(["Pt", "Cl", "Cl", "Cl"], [(0, 1), (0, 2), (0, 3)]))
            too_few = match_cluster(g(["Pt", "Cl"], [(0, 1)]))
            self.assertIn("thiếu", cluster_message(too_few))
        self.assertEqual(ok.kind, "MATCH")
        self.assertEqual((too_many.kind, too_few.kind), ("UNKNOWN", "UNKNOWN"))

    def test_hex_cards_touching_around_new_element_hub(self):
        _, rows = custom.parse({"elements": [{"marker": 22, "name": "titan"}]})      # Ti hóa trị IV nối 4 Cl; các Cl kề nhau chạm suông
        edges = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (2, 3), (3, 4)]
        with custom.applied(rows):
            r = match_cluster(Graph.from_edges(["Ti", "Cl", "Cl", "Cl", "Cl"], edges))
        self.assertEqual((r.kind, r.substance.formula), ("MATCH", "TiCl4"))

    def test_known_substances_unaffected(self):
        r = match_cluster(Graph.from_edges(["H", "O", "H"], [(0, 1), (1, 2)]))
        self.assertEqual((r.kind, r.substance.key), ("MATCH", "H2O"))

    def test_invalid_custom_is_400_before_recognizing(self):
        status, _ = handle_analyze({"demo": "Nước, ghép đúng", "custom": {"elements": [{"marker": 3, "name": "x"}]}}, {}, {})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
