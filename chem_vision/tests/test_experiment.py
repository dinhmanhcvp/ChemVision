import json
import math
import os
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import analyze_experiment as AE  # noqa: E402
from chem_vision.curriculum import compound_formula, molecular_mass  # noqa: E402
from chem_vision.reactions import parse_formula  # noqa: E402


def t_pdf(x, df):
    return math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi) * (1 + x * x / df) ** (-(df + 1) / 2)


def p_by_integration(t, df, steps=20000):
    """Cách tính độc lập với betainc: tích phân số đuôi hai phía bằng quy tắc Simpson trên [|t|, 200]."""
    a, b = abs(t), 200.0
    h = (b - a) / steps
    s = t_pdf(a, df) + t_pdf(b, df)
    for i in range(1, steps):
        s += (4 if i % 2 else 2) * t_pdf(a + i * h, df)
    return 2 * s * h / 3


class Distribution(unittest.TestCase):
    def test_table_values(self):
        self.assertAlmostEqual(AE.t_critical(10), 2.2281, places=3)
        self.assertAlmostEqual(AE.t_critical(5), 2.5706, places=3)
        self.assertAlmostEqual(AE.t_critical(30), 2.0423, places=3)
        self.assertAlmostEqual(AE.t_critical(1000), 1.9623, places=3)
        self.assertAlmostEqual(AE.t_two_sided_p(2.0, 10), 0.0734, places=3)

    def test_matches_independent_integration(self):
        for t, df in ((0.5, 3), (1.7, 8), (2.6, 14.5), (3.4, 40), (0.0, 12)):
            self.assertAlmostEqual(AE.t_two_sided_p(t, df), p_by_integration(t, df), places=5, msg=(t, df))

    def test_symmetry_and_range(self):
        self.assertAlmostEqual(AE.t_two_sided_p(-1.3, 9), AE.t_two_sided_p(1.3, 9))
        self.assertEqual(AE.t_two_sided_p(0.0, 7), 1.0)
        self.assertLess(AE.t_two_sided_p(50, 20), 1e-10)


class Statistics(unittest.TestCase):
    def test_welch_known_case(self):
        a, b = [20.1, 19.8, 22.3, 21.0, 20.5, 19.9], [18.2, 19.0, 17.5, 18.8, 19.3, 18.0]
        w = AE.welch(a, b)
        self.assertAlmostEqual(w["diff"], np.mean(a) - np.mean(b))
        self.assertAlmostEqual(w["p"], p_by_integration(w["t"], w["df"]), places=5)
        self.assertLess(w["p"], 0.01)

    def test_welch_equal_groups_not_significant(self):
        w = AE.welch([5, 6, 7, 8, 9], [5, 6, 7, 8, 9])
        self.assertEqual(w["diff"], 0)
        self.assertGreater(w["p"], 0.99)

    def test_hedges_g(self):
        rng = np.random.default_rng(3)
        a, b = rng.normal(1, 1, 3000), rng.normal(0, 1, 3000)
        g = AE.hedges_g(a, b)
        self.assertAlmostEqual(g["g"], 1.0, delta=0.07)
        self.assertTrue(g["ci_low"] < g["g"] < g["ci_high"])

    def test_ancova_recovers_effect(self):
        rng = np.random.default_rng(11)
        n = 600
        pre = rng.normal(5, 1.5, n)
        group = rng.integers(0, 2, n)
        post = 1.0 + 0.8 * pre + 1.0 * group + rng.normal(0, 0.5, n)
        out = AE.ancova(post, pre, group)
        self.assertAlmostEqual(out["effect"], 1.0, delta=0.1)
        self.assertAlmostEqual(out["pre_slope"], 0.8, delta=0.05)
        self.assertLess(out["p"], 1e-6)

    def test_ancova_null_effect(self):
        rng = np.random.default_rng(5)
        n = 400
        pre = rng.normal(5, 1.5, n)
        group = rng.integers(0, 2, n)
        post = 1.0 + 0.8 * pre + rng.normal(0, 0.8, n)
        out = AE.ancova(post, pre, group)
        self.assertLess(abs(out["effect"]), 0.25)
        self.assertGreater(out["p"], 0.01)

    def test_cluster_robust_is_wider_when_classes_differ(self):
        rng = np.random.default_rng(2)
        classes = np.repeat(np.arange(8), 30)
        class_effect = rng.normal(0, 1.0, 8)[classes]
        group = np.repeat([0, 1] * 4, 30)                       # cả lớp cùng một nhóm
        pre = rng.normal(5, 1, len(classes))
        post = pre + class_effect + rng.normal(0, 0.5, len(classes))
        plain = AE.ancova(post, pre, group)
        robust = AE.ancova(post, pre, group, classes)
        self.assertGreater(robust["se"], 2 * plain["se"])       # bỏ qua cụm thì quá tự tin
        self.assertEqual(robust["df"], 7)
        self.assertEqual(robust["clusters"], 8)

    def test_sample_size(self):
        self.assertEqual(AE.sample_size_per_group(0.5), 63)
        self.assertEqual(AE.sample_size_per_group(0.8), 25)
        self.assertGreater(AE.sample_size_per_group(0.5, cluster_size=25, icc=0.1), 3 * 62)
        self.assertGreater(AE.sample_size_per_group(0.3), AE.sample_size_per_group(0.5))


class Report(unittest.TestCase):
    def write_csv(self, rows):
        path = os.path.join(tempfile.mkdtemp(), "d.csv")
        with open(path, "w", encoding="utf-8") as f:
            f.write("lop,nhom,diem_truoc,diem_sau\n" + "\n".join(rows) + "\n")
        return path

    def simulated(self, classes=8, per=20, effect=1.0):
        rng = np.random.default_rng(0)
        rows = []
        for c in range(classes):
            grp = "CV" if c % 2 == 0 else "BQ"
            for _ in range(per):
                pre = float(np.clip(round(rng.normal(4, 1.5)), 0, 8))
                post = float(np.clip(round(pre + 1 + (effect if grp == "CV" else 0) + rng.normal(0, 1)), 0, 8))
                rows.append(f"L{c},{grp},{pre},{post}")
        return rows

    def test_report_contents(self):
        text = AE.report(AE.read_rows(self.write_csv(self.simulated())))
        for part in ("Số học sinh", "Welch", "Hedges g", "ANCOVA", "sai số chuẩn theo cụm lớp", "chưa đủ bằng chứng"):
            self.assertIn(part, text)

    def test_few_classes_warns(self):
        text = AE.report(AE.read_rows(self.write_csv(self.simulated(classes=2))))
        self.assertIn("dưới 4 lớp", text)

    def test_bad_input(self):
        with self.assertRaises(SystemExit):
            AE.read_rows(self.write_csv(["L1,XX,3,4"]))
        path = os.path.join(tempfile.mkdtemp(), "e.csv")
        open(path, "w").write("a,b\n1,2\n")
        with self.assertRaises(SystemExit):
            AE.read_rows(path)
        self.assertIn("ít nhất 3", AE.report(AE.read_rows(self.write_csv(["L1,CV,3,4", "L1,BQ,3,4"]))))


class QuestionBank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = json.load(open(os.path.join(ROOT, "docs", "bo-cau-hoi-kiem-tra.json"), encoding="utf-8"))

    def test_forms_are_parallel(self):
        a, b = self.bank["dang"]["A"], self.bank["dang"]["B"]
        self.assertEqual(len(a), 8)
        self.assertEqual([q["ky_nang"] for q in a], [q["ky_nang"] for q in b])
        for q in a + b:
            self.assertIn(q["ky_nang"], self.bank["ky_nang"])
            self.assertEqual(len(q["lua_chon"]), 4)
            self.assertEqual(len(set(q["lua_chon"])), 4)
            self.assertIn(q["dap_an"], range(4))

    def test_ids_unique(self):
        ids = [q["id"] for form in self.bank["dang"].values() for q in form]
        self.assertEqual(len(ids), len(set(ids)))

    def test_answer_positions_are_not_all_the_same(self):
        positions = [q["dap_an"] for form in self.bank["dang"].values() for q in form]
        self.assertGreater(len(set(positions)), 1)

    def test_numeric_and_formula_keys_verified_by_code(self):
        checked = 0
        for form in self.bank["dang"].values():
            for q in form:
                chk = q.get("kiem_tra")
                if not chk:
                    continue
                correct = q["lua_chon"][q["dap_an"]]
                if "va" in chk:
                    self.assertEqual(compound_formula(chk["a"], chk["va"], chk["b"], chk["vb"]), chk["cong_thuc"], q["id"])
                    self.assertEqual(correct, chk["cong_thuc"], q["id"])
                if "khoi_luong" in chk:
                    self.assertEqual(molecular_mass(parse_formula(chk["cong_thuc"])), chk["khoi_luong"], q["id"])
                    self.assertEqual(correct, str(chk["khoi_luong"]), q["id"])
                checked += 1
        self.assertEqual(checked, 6)

    def test_distractors_for_formula_questions_are_wrong(self):
        for form in self.bank["dang"].values():
            for q in form:
                chk = q.get("kiem_tra")
                if chk and "va" in chk:
                    for i, opt in enumerate(q["lua_chon"]):
                        if i != q["dap_an"]:
                            self.assertNotEqual(opt, chk["cong_thuc"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
