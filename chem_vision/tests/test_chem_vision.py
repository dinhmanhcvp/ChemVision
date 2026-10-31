import os
import random
import re
import sys
import tempfile
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision import (DATABASE, ApiError, Challenge, GaveUp, SessionLog, analyze,
                         call_with_retry)
from chem_vision.core import (BY_KEY, MAX_DEGREE, Graph, _speech_of, extract_json,
                              is_isomorphic, speech_cache_name)


def mol(atoms, edges, conf=0.95):
    """Dữ liệu giả lập có cùng cấu trúc JSON mà Gemini trả về. atoms: 'H O H', edges: [(1,2),(2,3)]"""
    syms = atoms.split()
    return {"cards": [{"id": i + 1, "symbol": s, "confidence": conf} for i, s in enumerate(syms)],
            "connections": [{"a": a, "b": b} for a, b in edges]}


def of(key, shuffle=None):
    s = BY_KEY[key].graph
    ids = list(range(len(s.labels)))
    if shuffle:
        shuffle.shuffle(ids)
    cards = [{"id": ids[i] + 1, "symbol": s.labels[i], "confidence": 0.95} for i in range(len(ids))]
    return {"cards": cards, "connections": [{"a": ids[a] + 1, "b": ids[b] + 1} for a, b in s.edges]}


def parse_formula(f):
    def expand(s):
        c = Counter()
        for m in re.finditer(r"(\()|(\))(\d*)|([A-Z][a-z]?)(\d*)", s):
            pass
        stack = [Counter()]
        for m in re.finditer(r"\(|\)(\d*)|([A-Z][a-z]?)(\d*)", s):
            t = m.group(0)
            if t == "(":
                stack.append(Counter())
            elif t.startswith(")"):
                inner = stack.pop()
                for k, v in inner.items():
                    stack[-1][k] += v * int(m.group(1) or 1)
            else:
                stack[-1][m.group(2)] += int(m.group(3) or 1)
        return stack[0]
    return expand(f)


class Database(unittest.TestCase):
    def test_size(self):
        self.assertEqual(len(DATABASE), 31)

    def test_composition_matches_formula(self):
        for s in DATABASE:
            if s.key == "CH3OCH3":
                self.assertEqual(s.graph.composition(), Counter({"C": 2, "H": 6, "O": 1}))
                continue
            self.assertEqual(s.graph.composition(), parse_formula(s.formula), s.key)

    def test_connected_and_unique(self):
        for s in DATABASE:
            seen, stack = set(), [0]
            while stack:
                u = stack.pop()
                if u not in seen:
                    seen.add(u)
                    stack.extend(s.graph.adj[u])
            self.assertEqual(len(seen), len(s.graph.labels), s.key)
        for i, a in enumerate(DATABASE):
            for b in DATABASE[i + 1:]:
                self.assertFalse(is_isomorphic(a.graph, b.graph), (a.key, b.key))

    def test_max_atoms(self):
        self.assertEqual(max(len(s.graph.labels) for s in DATABASE), 9)


class Matching(unittest.TestCase):
    def kinds(self, raw):
        a = analyze(raw)
        return a.status, [r.kind for _, r in a.clusters], a

    def test_17_report_scenarios(self):
        # 1-2 nước, thứ tự id khác
        self.assertEqual(self.kinds(mol("H O H", [(1, 2), (2, 3)]))[1], ["MATCH"])
        self.assertEqual(self.kinds(mol("O H H", [(2, 1), (1, 3)]))[1], ["MATCH"])
        # 3 nước sai liên kết
        st, k, a = self.kinds(mol("H H O", [(1, 2), (2, 3)]))
        self.assertEqual(k, ["WRONG_BONDS"])
        self.assertIn("thừa liên kết H–H", a.message)
        self.assertIn("thiếu liên kết H–O", a.message)
        self.assertIn("O nối với H, H", a.message)
        # 4-8
        self.assertEqual(self.kinds(mol("O C O", [(1, 2), (2, 3)]))[1], ["MATCH"])
        self.assertEqual(self.kinds(of("CH4"))[1], ["MATCH"])
        self.assertEqual(self.kinds(of("H2SO4"))[1], ["MATCH"])
        self.assertEqual(self.kinds(of("Ca(OH)2"))[1], ["MATCH"])
        self.assertEqual(self.kinds(of("C2H5OH"))[1], ["MATCH"])
        # 9 cùng thành phần etanol, C–O–C: nay nhận ra là đimetyl ete
        _, k, a = self.kinds(of("CH3OCH3"))
        self.assertEqual(k, ["MATCH"])
        self.assertIn("đimetyl ete", a.message)
        # 10 ghép dở nước
        st, k, a = self.kinds(mol("H O", [(1, 2)]))
        self.assertEqual(k, ["SUGGEST"])
        names = [s.substance.key for s in a.clusters[0][1].suggestions]
        self.assertEqual(names, ["H2O", "NaOH", "KOH"])
        self.assertIn("Còn thiếu 1 thẻ H (hiđro)", a.message)
        # 11 H2SO4 thiếu một H
        g = BY_KEY["H2SO4"].graph
        atoms = [l for l in g.labels]
        raw = {"cards": [{"id": i + 1, "symbol": l, "confidence": 0.9} for i, l in enumerate(atoms[:-1])],
               "connections": [{"a": a + 1, "b": b + 1} for a, b in g.edges if max(a, b) < len(atoms) - 1]}
        _, k, a = self.kinds(raw)
        self.assertEqual(a.clusters[0][1].suggestions[0].substance.key, "H2SO4")
        # 12 thừa thẻ N
        _, k, a = self.kinds(mol("H O H N", [(1, 2), (2, 3), (2, 4)]))
        self.assertEqual(k, ["SUGGEST"])
        self.assertEqual(a.clusters[0][1].suggestions[0].substance.key, "H2O")
        self.assertIn("Đang thừa 1 thẻ N (nitơ)", a.message)
        # 13 không giống chất nào
        self.assertEqual(self.kinds(mol("Cu Zn Au", [(1, 2), (2, 3)]))[1], ["UNKNOWN"])
        # 14 hai cụm
        _, k, a = self.kinds(mol("H O H Cl", [(1, 2), (2, 3)]))
        self.assertEqual(k, ["MATCH", "SUGGEST"])
        self.assertIn("2 cụm thẻ", a.message)
        # 15 độ tin cậy thấp
        raw = mol("C O", [(1, 2)])
        raw["cards"][0]["confidence"] = 0.45
        st, _, a = self.kinds(raw)
        self.assertEqual(st, "RECAPTURE")
        self.assertIn("độ tin cậy 0,45", a.message)
        # 16 "CA"
        self.assertEqual(self.kinds(mol("CA O", [(1, 2)]))[1], ["MATCH"])
        # 17 khung hình trống
        self.assertEqual(self.kinds({"cards": [], "connections": []})[0], "EMPTY")

    def test_all_substances_recognised_random_order(self):
        rng = random.Random(7)
        for s in DATABASE:
            for _ in range(5):
                a = analyze(of(s.key, rng))
                self.assertEqual(a.matches(), [s.key], s.key)

    def test_remove_one_h_suggests_original_in_top3(self):
        rng = random.Random(3)
        with_h = [s for s in DATABASE if "H" in s.graph.labels and len(s.graph.labels) > 2]
        for s in with_h:
            g = s.graph
            drop = max(i for i, l in enumerate(g.labels) if l == "H")
            keep = [i for i in range(len(g.labels)) if i != drop]
            idx = {old: new for new, old in enumerate(keep)}
            raw = {"cards": [{"id": idx[i] + 1, "symbol": g.labels[i], "confidence": 0.9} for i in keep],
                   "connections": [{"a": idx[a] + 1, "b": idx[b] + 1} for a, b in g.edges if drop not in (a, b)]}
            a = analyze(raw)
            top = [x.substance.key for x in a.clusters[0][1].suggestions] if a.clusters[0][1].kind == "SUGGEST" else a.matches()
            self.assertIn(s.key, top, s.key)

    def test_valence_warning(self):
        # H nối với hai thẻ: cảnh báo cụ thể
        _, _, a = Matching.kinds(self, mol("H H O", [(1, 2), (2, 3)]))
        self.assertIn("thẻ H đang chạm 2 thẻ", a.message)
        self.assertEqual(MAX_DEGREE["H"], 1)

    def test_multi_isomer_wrong_bonds(self):
        # C2H6O, ethanol cấu trúc nhưng H gắn sai chỗ (C đầu có 5 láng giềng)
        raw = mol("C C O H H H H H H", [(1, 2), (1, 3), (3, 4), (1, 5), (1, 6), (1, 7), (2, 8), (2, 9)])
        _, k, a = Matching.kinds(self, raw)
        self.assertEqual(k, ["WRONG_BONDS"])
        self.assertIn("etanol", a.message)


class Cleaning(unittest.TestCase):
    def test_json_in_code_fence(self):
        text = 'Đây là kết quả:\n```json\n{"cards":[{"id":1,"symbol":"H","confidence":0.9},{"id":2,"symbol":"Cl","confidence":0.9}],"connections":[[1,2]]}\n```'
        self.assertEqual(analyze(text).matches(), ["HCl"])

    def test_percent_confidence_and_string_ids(self):
        raw = {"cards": [{"id": "1", "symbol": " h ", "confidence": 95}, {"id": "2", "symbol": "cl", "confidence": 90}],
               "connections": [{"a": "1", "b": 2}]}
        self.assertEqual(analyze(raw).matches(), ["HCl"])

    def test_bad_json_requests_recapture(self):
        self.assertEqual(analyze("xin lỗi, tôi không thấy ảnh").status, "RECAPTURE")

    def test_all_problem_cards_listed_together(self):
        raw = {"cards": [{"id": 1, "symbol": "X1", "confidence": 0.9}, {"id": 2, "symbol": "O", "confidence": 0.3},
                         {"id": 3, "symbol": "H", "confidence": 0.2}], "connections": []}
        a = analyze(raw)
        self.assertEqual(a.status, "RECAPTURE")
        self.assertEqual(len(a.cleaned.problems), 3)

    def test_bad_edges_ignored(self):
        raw = mol("H O H", [(1, 2), (2, 3), (2, 3), (3, 2), (1, 1), (1, 99)])
        a = analyze(raw)
        self.assertEqual(a.matches(), ["H2O"])

    def test_duplicate_ids(self):
        raw = {"cards": [{"id": 1, "symbol": "H", "confidence": 0.9}, {"id": 1, "symbol": "O", "confidence": 0.9}], "connections": []}
        self.assertEqual(len(analyze(raw).cleaned.cards), 1)

    def test_zero_read_as_O(self):
        self.assertEqual(analyze(mol("Ca 0", [(1, 2)])).matches(), ["CaO"])

    def test_extract_json_none(self):
        self.assertIsNone(extract_json("không có json"))


class Speech(unittest.TestCase):
    def test_no_formula_in_speech(self):
        a = analyze(mol("H O", [(1, 2)]))
        self.assertNotRegex(a.speech, r"H2O|NaOH|\(")
        self.assertIn("nước", a.speech)
        self.assertIn("hiđro", a.speech)

    def test_speech_of_helper(self):
        self.assertEqual(_speech_of("Còn thiếu 1 thẻ H (hiđro)"), "Còn thiếu 1 thẻ hiđro")

    def test_cache_name_stable(self):
        self.assertEqual(speech_cache_name("a"), speech_cache_name("a"))
        self.assertNotEqual(speech_cache_name("a"), speech_cache_name("b"))


class Retry(unittest.TestCase):
    class Clock:
        def __init__(self):
            self.t = 0.0
            self.sleeps = []

        def now(self):
            return self.t

        def sleep(self, s):
            self.sleeps.append(s)
            self.t += s

    def run_call(self, outcomes, models=("m1", "m2"), **kw):
        c, calls = self.Clock(), []

        def fn(model):
            calls.append(model)
            o = outcomes.pop(0)
            if isinstance(o, Exception):
                raise o
            return o

        try:
            res = call_with_retry(fn, models, sleep=c.sleep, clock=c.now, **kw)
        except GaveUp as e:
            return e, calls, c
        return res, calls, c

    def test_success_first_try(self):
        res, calls, c = self.run_call(["ok"])
        self.assertEqual(res, ("ok", "m1", 1))
        self.assertEqual(c.sleeps, [])

    def test_transient_then_success(self):
        res, calls, c = self.run_call([ApiError(503), ApiError(429), "ok"])
        self.assertEqual(res[0], "ok")
        self.assertEqual(c.sleeps, [2.0, 4.0])

    def test_switch_model_without_waiting_after_last_try(self):
        res, calls, c = self.run_call([ApiError(503)] * 3 + ["ok"])
        self.assertEqual(res, ("ok", "m2", 4))
        self.assertEqual(c.sleeps, [2.0, 4.0])      # bản cũ chờ thêm 6 s trước khi đổi model

    def test_both_models_down_waits_12s_not_24s(self):
        res, calls, c = self.run_call([ApiError(503)] * 6)
        self.assertIsInstance(res, GaveUp)
        self.assertEqual(sum(c.sleeps), 12.0)
        self.assertEqual(len(calls), 6)

    def test_fatal_stops_immediately(self):
        res, calls, c = self.run_call([ApiError(401)])
        self.assertIsInstance(res, GaveUp)
        self.assertEqual(len(calls), 1)

    def test_retry_after_respected(self):
        res, calls, c = self.run_call([ApiError(429, retry_after=5), "ok"])
        self.assertEqual(c.sleeps, [5])

    def test_budget(self):
        res, calls, c = self.run_call([ApiError(503, retry_after=20)], budget=15)
        self.assertIsInstance(res, GaveUp)
        self.assertEqual(c.sleeps, [])

    def test_missing_model_switches(self):
        res, calls, c = self.run_call([ApiError(404), "ok"])
        self.assertEqual(res[1], "m2")
        self.assertEqual(c.sleeps, [])


class ChallengeMode(unittest.TestCase):
    def test_full_run(self):
        ch = Challenge(["H2O", "CO2", "NaCl"])
        self.assertIn("nước", ch.prompt())
        # sai một lần: ghép nhầm liên kết
        att = ch.submit(analyze(mol("H H O", [(1, 2), (2, 3)])))
        self.assertFalse(att.correct)
        self.assertEqual(att.kind, "WRONG_BONDS")
        h1 = ch.hint()
        self.assertIn("hiđro", h1)
        self.assertIn("2 thẻ H", ch.hint())
        self.assertIn("O nối với H, H", ch.hint())
        self.assertIn("hết 3 gợi ý", ch.hint())
        att = ch.submit(analyze(of("H2O")))
        self.assertTrue(att.correct)
        self.assertEqual(ch.tasks[0].score, max(1, 10 - 1 - 2 * 3))
        # câu 2: ghép nhầm chất khác
        att = ch.submit(analyze(of("SO2")))
        self.assertEqual(att.kind, "MATCH_OTHER")
        att = ch.submit(analyze(of("CO2")))
        self.assertEqual(ch.tasks[1].score, 9)
        ch.skip()
        self.assertTrue(ch.finished)
        s = ch.summary()
        self.assertEqual((s["đúng"], s["bỏ qua"], s["điểm"]), (2, 1, 3 + 9))
        self.assertEqual(s["câu khó nhất"], "H2O")

    def test_bad_photo_not_counted_as_wrong(self):
        ch = Challenge(["H2O"])
        att = ch.submit(analyze({"cards": [], "connections": []}))
        self.assertEqual(att.kind, "EMPTY")
        self.assertEqual(ch.tasks[0].attempts, 0)

    def test_target_found_among_extra_clusters(self):
        ch = Challenge(["H2O"])
        att = ch.submit(analyze(mol("H O H Cl", [(1, 2), (2, 3)])))
        self.assertTrue(att.correct)

    def test_decks_valid(self):
        for name in Challenge.__init__.__globals__["DECKS"]:
            Challenge.from_deck(name)

    def test_invalid_target(self):
        with self.assertRaises(ValueError):
            Challenge(["XYZ"])


class ClassLog(unittest.TestCase):
    def make(self):
        d = tempfile.mkdtemp()
        return SessionLog(os.path.join(d, "log.csv"))

    def test_record_and_report(self):
        log = self.make()
        log.record("Nhóm 1", "H2O", analyze(mol("H O", [(1, 2)])), when=0)
        log.record("Nhóm 1", "H2O", analyze(of("H2O")), when=1)
        log.record("Nhóm 2", "H2O", analyze(mol("H H O", [(1, 2), (2, 3)])), when=2)
        log.record("Nhóm 2", "H2O", analyze(of("H2O")), when=3)
        log.record("Nhóm 3", "CO2", analyze(of("CO2")), when=4)
        self.assertIsNone(log.record("Nhóm 3", "CO2", analyze({"cards": [], "connections": []})))
        st = log.stats()
        self.assertEqual((st["đúng ngay lần đầu"], st["số cặp nhóm-chất"]), (1, 3))
        text = log.teacher_report()
        self.assertIn("Tổng số lượt kiểm tra: 5", text)
        self.assertIn("nước (H2O): sai 2/4", text)
        self.assertIn("hay thiếu thẻ H", text)

    def test_csv_persists_and_reloads(self):
        log = self.make()
        log.record("Nhóm 1", "NaCl", analyze(of("NaCl")), when=0)
        again = SessionLog(log.path)
        self.assertEqual(len(again.rows), 1)
        with open(log.path, encoding="utf-8-sig") as f:
            header = f.readline().strip()
        self.assertEqual(header, "thời gian,nhóm,chất mục tiêu,kết quả,thẻ thiếu,thẻ thừa,liên kết sai")

    def test_no_image_or_name_fields(self):
        log = self.make()
        row = log.record("Nhóm 1", "H2O", analyze(of("H2O")), when=0)
        self.assertEqual(set(row), {"thời gian", "nhóm", "chất mục tiêu", "kết quả", "thẻ thiếu", "thẻ thừa", "liên kết sai"})

    def test_empty_report(self):
        self.assertIn("Chưa có", self.make().teacher_report())


if __name__ == "__main__":
    unittest.main(verbosity=2)
