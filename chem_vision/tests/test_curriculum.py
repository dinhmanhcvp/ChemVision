import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision.core import BY_KEY, DATABASE, analyze
from chem_vision.curriculum import (ATOMIC_MASS, CARD_ELEMENTS, DECK_GRADE, DECK_SPECS, DECK_STYLE, DECKS, VALENCE,
                                    compound_formula, format_mass, molecular_mass, valence_task)
from chem_vision.features import Challenge, valence_prompt


def mol(key):
    g = BY_KEY[key].graph
    return json.dumps({"cards": [{"id": i + 1, "symbol": l, "confidence": 0.95} for i, l in enumerate(g.labels)],
                       "connections": [{"a": a + 1, "b": b + 1} for a, b in g.edges]})


class Content(unittest.TestCase):
    def test_every_grade_has_content(self):
        for grade in (7, 8, 9):
            self.assertGreaterEqual(sum(1 for s in DATABASE if s.grade == grade), 8, grade)
        for grade in (6, 7, 8, 9):
            self.assertTrue(any(g == grade for g in DECK_GRADE.values()), grade)

    def test_decks_valid(self):
        for name, keys in DECKS.items():
            self.assertTrue(keys and all(k in BY_KEY for k in keys), name)
            self.assertIn(DECK_STYLE[name], ("name", "valence"))
            Challenge.from_deck(name)

    def test_grade_8_and_9_decks_use_matching_grades(self):
        for name, (grade, style, keys) in DECK_SPECS.items():
            if grade == 9:
                self.assertTrue(all(BY_KEY[k].grade in (7, 9) for k in keys), name)

    def test_every_element_has_mass_valence_and_marker(self):
        used = {sym for s in DATABASE for sym in s.graph.labels}
        for sym in used:
            self.assertIn(sym, ATOMIC_MASS, sym)
            self.assertIn(sym, VALENCE, sym)
            self.assertIn(sym, CARD_ELEMENTS, sym)
        self.assertEqual(len(CARD_ELEMENTS), len(set(CARD_ELEMENTS)))

    def test_covalent_degrees_do_not_exceed_valence(self):
        for s in DATABASE:
            if s.ionic:
                continue
            for i, label in enumerate(s.graph.labels):
                self.assertLessEqual(len(s.graph.adj[i]), max(VALENCE[label]), (s.key, label))

    def test_isomers_are_distinct(self):
        self.assertEqual(analyze(mol("C4H10")).matches(), ["C4H10"])
        self.assertEqual(analyze(mol("C4H10-iso")).matches(), ["C4H10-iso"])
        self.assertEqual(analyze(mol("CH3OCH3")).matches(), ["CH3OCH3"])


class Valence(unittest.TestCase):
    def test_compound_formula(self):
        cases = [("Al", 3, "O", 2, "Al2O3"), ("O", 2, "Al", 3, "Al2O3"), ("Ca", 2, "O", 2, "CaO"), ("C", 4, "H", 1, "CH4"),
                 ("H", 1, "S", 2, "H2S"), ("Fe", 3, "Cl", 1, "FeCl3"), ("S", 6, "O", 2, "SO3"), ("N", 3, "H", 1, "NH3"),
                 ("H", 1, "O", 2, "H2O"), ("Na", 1, "O", 2, "Na2O"), ("P", 5, "O", 2, "P2O5"), ("Mg", 2, "Cl", 1, "MgCl2"),
                 ("H", 1, "Cl", 1, "HCl"), ("Fe", 2, "O", 2, "FeO"), ("C", 4, "O", 2, "CO2")]
        for a, va, b, vb, expected in cases:
            self.assertEqual(compound_formula(a, va, b, vb), expected, (a, va, b, vb))

    def test_valence_task_roundtrip_for_binary_compounds(self):
        found = 0
        for s in DATABASE:
            task = valence_task(s.graph.composition(), s.formula)
            if task is None:
                continue
            found += 1
            a, va, b, vb = task
            self.assertEqual(compound_formula(a, va, b, vb), s.formula, s.key)
        self.assertGreaterEqual(found, 25)

    def test_iron_oxides_told_apart_by_valence(self):
        self.assertEqual(valence_task(BY_KEY["FeO"].graph.composition(), "FeO")[1], 2)
        self.assertEqual(valence_task(BY_KEY["Fe2O3"].graph.composition(), "Fe2O3")[1], 3)

    def test_valence_prompt_hides_the_answer(self):
        for key in DECKS["Lớp 7: Lập công thức theo hóa trị"]:
            text = valence_prompt(key)
            self.assertIn("hóa trị", text)
            self.assertNotIn(BY_KEY[key].formula, text)
            self.assertNotIn(BY_KEY[key].name, text)

    def test_valence_deck_prompt_in_challenge(self):
        c = Challenge.from_deck("Lớp 7: Lập công thức theo hóa trị")
        self.assertIn("lập công thức hóa học", c.prompt())
        c.skip()
        c.skip()
        self.assertIn("nitơ N (hóa trị III)", c.prompt())

    def test_valence_deck_is_solved_by_the_right_molecule(self):
        c = Challenge.from_deck("Lớp 7: Lập công thức theo hóa trị")
        self.assertTrue(c.submit(analyze(mol("H2O"))).correct)


class Mass(unittest.TestCase):
    def test_molecular_masses(self):
        cases = {"H2O": 18, "CO2": 44, "NaCl": 58.5, "CaCO3": 100, "Fe2O3": 160, "C2H5OH": 46, "CH3COOH": 60,
                 "CO(NH2)2": 60, "H2SO4": 98, "NH3": 17, "Al2O3": 102, "C6H6": 78, "CuSO4": 160}
        for key, mass in cases.items():
            self.assertEqual(molecular_mass(BY_KEY[key].graph.composition()), mass, key)

    def test_format(self):
        self.assertEqual(format_mass(58.5), "58,5")
        self.assertEqual(format_mass(18), "18")

    def test_messages_show_mass(self):
        a = analyze(mol("H2O"))
        self.assertIn("Phân tử khối: 18.", a.message)
        self.assertIn("Phân tử khối là 18.", a.speech)

    def test_ionic_note(self):
        a = analyze(mol("NaCl"))
        self.assertIn("Khối lượng công thức: 58,5", a.message)
        self.assertIn("hợp chất ion", a.message)
        self.assertIn("mạng tinh thể", a.message)
        self.assertNotIn("mạng tinh thể", analyze(mol("H2O")).message)

    def test_covalent_has_no_ion_note(self):
        for key in ("CO2", "CH4", "C2H4", "H2SO4"):
            self.assertNotIn("hợp chất ion", analyze(mol(key)).message, key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
