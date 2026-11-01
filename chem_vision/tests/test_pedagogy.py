import json
import os
import sys
import unittest
from collections import Counter
from math import gcd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision import reactions as R
from chem_vision import web
from chem_vision.core import BY_KEY, analyze
from chem_vision.features import SessionLog
from chem_vision.pedagogy import ADVICE, explain, row_tags


def mol(atoms, edges):
    syms = atoms.split()
    return json.dumps({"cards": [{"id": i + 1, "symbol": s, "confidence": 0.95} for i, s in enumerate(syms)],
                       "connections": [{"a": a, "b": b} for a, b in edges]})


def of(key):
    g = BY_KEY[key].graph
    return json.dumps({"cards": [{"id": i + 1, "symbol": l, "confidence": 0.95} for i, l in enumerate(g.labels)],
                       "connections": [{"a": a + 1, "b": b + 1} for a, b in g.edges]})


class Formulas(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(R.parse_formula("Al2(SO4)3"), Counter({"Al": 2, "S": 3, "O": 12}))
        self.assertEqual(R.parse_formula("Ca(OH)2"), Counter({"Ca": 1, "O": 2, "H": 2}))
        self.assertEqual(R.parse_formula("CO(NH2)2"), Counter({"C": 1, "O": 1, "N": 2, "H": 4}))
        self.assertEqual(R.parse_formula("C2H5OH"), Counter({"C": 2, "H": 6, "O": 1}))

    def test_parse_rejects_garbage(self):
        for bad in ("", "h2o", "H2O)", "(H2O", "H2 O", "2H2O", "Ca(OH2"):
            with self.assertRaises(ValueError, msg=bad):
                R.parse_formula(bad)


class Balancing(unittest.TestCase):
    def test_every_equation_balances_independently_checked(self):
        for i, (reactants, products) in enumerate(R.EQUATIONS):
            sol = R.balance(reactants, products)
            self.assertIsNotNone(sol, i)
            left, right = Counter(), Counter()
            for j, f in enumerate(reactants + products):
                for e, n in R.parse_formula(f).items():
                    (left if j < len(reactants) else right)[e] += n * sol[j]
            self.assertEqual(left, right, (i, sol))
            self.assertTrue(all(c >= 1 for c in sol))
            g = 0
            for c in sol:
                g = gcd(g, c)
            self.assertEqual(g, 1, (i, sol))

    def test_known_answers(self):
        self.assertEqual(R.balance(["H2", "O2"], ["H2O"]), [2, 1, 2])
        self.assertEqual(R.balance(["Al", "O2"], ["Al2O3"]), [4, 3, 2])
        self.assertEqual(R.balance(["C2H5OH", "O2"], ["CO2", "H2O"]), [1, 3, 2, 3])
        self.assertEqual(R.balance(["Al", "H2SO4"], ["Al2(SO4)3", "H2"]), [2, 3, 1, 3])

    def test_impossible(self):
        self.assertIsNone(R.balance(["H2"], ["O2"]))
        self.assertIsNone(R.balance(["H2", "O2"], ["H2O", "H2O2"]))        # nhiều nghiệm độc lập

    def test_check_correct_with_mass_law(self):
        out = R.check(0, [2, 1, 2])
        self.assertTrue(out["ok"] and out["simplest"])
        self.assertIn("36 = khối lượng sản phẩm 36", out["message"].replace("= khối", "= khối"))
        self.assertIn("bảo toàn khối lượng", out["message"])

    def test_check_balanced_but_not_simplest(self):
        out = R.check(0, [4, 2, 4])
        self.assertTrue(out["balanced"])
        self.assertFalse(out["simplest"])
        self.assertIn("rút gọn", out["message"])

    def test_check_wrong_explains_elements(self):
        out = R.check(0, [1, 1, 1])
        self.assertFalse(out["ok"])
        self.assertIn("nguyên tố O: vế trái 2 nguyên tử, vế phải 1 nguyên tử", out["message"])

    def test_check_validation(self):
        for bad in ([1, 1], [1, 1, 0], [1, 1, 21], [1, 1, "2"], [1, 1, True], "2 1 2", None):
            self.assertIn("error", R.check(0, bad), bad)
        self.assertIn("error", R.check(999, [1, 1, 1]))
        self.assertIn("error", R.check(True, [1, 1, 1]))


class WebEquation(unittest.TestCase):
    def test_meta_lists_equations(self):
        _, meta = web.handle_meta()
        self.assertEqual(len(meta["equations"]), len(R.EQUATIONS))
        self.assertEqual(meta["equations"][0], {"id": 0, "reactants": ["H2", "O2"], "products": ["H2O"]})

    def test_check_and_reveal(self):
        status, out = web.handle_equation({"id": 0, "coefficients": [2, 1, 2]})
        self.assertEqual((status, out["ok"]), (200, True))
        status, out = web.handle_equation({"id": 2, "reveal": True})
        self.assertEqual(out["coefficients"], [4, 3, 2])
        self.assertIn("4 Al + 3 O2 → 2 Al2O3", out["equation"])

    def test_bad_requests(self):
        self.assertEqual(web.handle_equation({"id": 99, "coefficients": [1]})[0], 400)
        self.assertEqual(web.handle_equation({"id": "0"})[0], 400)
        self.assertEqual(web.handle_equation({"id": 0, "coefficients": [1]})[0], 400)

    def test_route_registered(self):
        self.assertIn("equation", web.ROUTES)
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "..", "api", "equation.py")))


class Explanations(unittest.TestCase):
    def results(self, raw):
        return [r for _, r in analyze(raw).clusters]

    def test_h_bonded_to_h_explained_by_valence(self):
        r = self.results(mol("H H O", [(1, 2), (2, 3)]))[0]
        text = " ".join(explain(r))
        self.assertIn("hóa trị I", text)
        self.assertIn("chỉ nối được với MỘT thẻ khác", text)
        self.assertIn("Cần thêm liên kết H–O", text)

    def test_missing_card_explained(self):
        r = self.results(mol("H O", [(1, 2)]))[0]
        self.assertIn("cần thêm 1 thẻ H (hiđro)", " ".join(explain(r)))

    def test_extra_card_explained(self):
        r = self.results(mol("H O H N", [(1, 2), (2, 3), (2, 4)]))[0]
        self.assertIn("không thuộc nước", " ".join(explain(r)))

    def test_ionic_match_mentions_ionic_bond(self):
        text = " ".join(explain(self.results(of("NaCl"))[0]))
        self.assertIn("liên kết ion", text)
        self.assertIn("nhiều ion xếp đều đặn", text)

    def test_covalent_match_mentions_valence(self):
        self.assertIn("hóa trị", " ".join(explain(self.results(of("H2O"))[0])))

    def test_isomer_note(self):
        raw = mol("C C O H H H H H H", [(1, 2), (1, 3), (3, 4), (1, 5), (1, 6), (1, 7), (2, 8), (2, 9)])
        text = " ".join(explain(self.results(raw)[0]))
        self.assertIn("đồng phân", text)

    def test_unknown_gives_valence_hint(self):
        r = self.results(mol("Cu Zn Au", [(1, 2), (2, 3)]))[0]
        self.assertIn("hóa trị", " ".join(explain(r)))

    def test_api_includes_explanations(self):
        status, out = web.handle_analyze({"demo": "Nước, sai liên kết"}, {}, {})
        self.assertTrue(out["clusters"][0]["explain"])


class Misconceptions(unittest.TestCase):
    def row(self, **kw):
        base = {"thời gian": "t", "nhóm": "Nhóm 1", "chất mục tiêu": "H2O", "kết quả": "ĐÚNG", "thẻ thiếu": "",
                "thẻ thừa": "", "liên kết sai": ""}
        base.update(kw)
        return base

    def test_h_h(self):
        self.assertIn("H-H", row_tags(self.row(**{"kết quả": "SAI LIÊN KẾT", "liên kết sai": "H-H | H-O"})))

    def test_monovalent(self):
        self.assertIn("MONOVALENT", row_tags(self.row(**{"chất mục tiêu": "NaOH", "kết quả": "SAI LIÊN KẾT", "liên kết sai": "H-Na | H-O"})))

    def test_missing_h_and_extra(self):
        self.assertIn("MISSING_H", row_tags(self.row(**{"kết quả": "GHÉP DỞ", "thẻ thiếu": "Hx1"})))
        self.assertIn("EXTRA_CARD", row_tags(self.row(**{"kết quả": "GHÉP DỞ", "thẻ thừa": "Nx1"})))

    def test_isomer(self):
        self.assertIn("ISOMER", row_tags(self.row(**{"chất mục tiêu": "C2H5OH", "kết quả": "ĐÚNG CHẤT KHÁC"})))
        self.assertNotIn("ISOMER", row_tags(self.row(**{"chất mục tiêu": "H2O", "kết quả": "ĐÚNG CHẤT KHÁC"})))

    def test_ionic_correct(self):
        self.assertEqual(row_tags(self.row(**{"chất mục tiêu": "NaCl"})), ["ION_AS_MOLECULE"])
        self.assertEqual(row_tags(self.row()), [])

    def test_all_tags_have_advice(self):
        for code in ("H-H", "MONOVALENT", "MISSING_H", "EXTRA_CARD", "ISOMER", "WRONG_ORDER", "ION_AS_MOLECULE"):
            self.assertIn(code, ADVICE)

    def test_teacher_report_lists_misconceptions(self):
        log = SessionLog(rows=[
            self.row(**{"kết quả": "SAI LIÊN KẾT", "liên kết sai": "H-H | H-O"}),
            self.row(**{"nhóm": "Nhóm 2", "kết quả": "SAI LIÊN KẾT", "liên kết sai": "H-H | H-O"}),
            self.row(**{"nhóm": "Nhóm 3", "kết quả": "GHÉP DỞ", "thẻ thiếu": "Hx1"}),
            self.row(**{"nhóm": "Nhóm 4", "chất mục tiêu": "NaCl"}),
        ])
        text = log.teacher_report()
        self.assertIn("Quan niệm sai thường gặp", text)
        self.assertIn("Nối hai thẻ hiđro với nhau (H–H) trong hợp chất: 2 lượt", text)
        self.assertIn("Quên thẻ hiđro: 1 lượt", text)
        self.assertIn("mạng tinh thể ion", text)

    def test_report_without_errors_has_no_section(self):
        log = SessionLog(rows=[self.row()])
        self.assertNotIn("Quan niệm sai", log.teacher_report())


if __name__ == "__main__":
    unittest.main(verbosity=2)
