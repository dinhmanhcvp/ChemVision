import io
import json
import os
import sys
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision import classroom as C
from chem_vision import web

HDR = {"x-forwarded-for": "1.1.1.1"}


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def row(group, target, result, **kw):
    base = {"thời gian": "t", "nhóm": group, "chất mục tiêu": target, "kết quả": result, "thẻ thiếu": "", "thẻ thừa": "",
            "liên kết sai": ""}
    base.update(kw)
    return base


class Flow(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = C.MemoryStore(self.clock)

    def call(self, **payload):
        return C.handle(payload, {}, HDR, store=self.store, now=self.clock())

    def new_class(self):
        status, out = self.call(action="create", name="Lớp 7A")
        self.assertEqual(status, 200)
        return out["code"], out["teacher_key"]

    def test_create_returns_code_and_key_once(self):
        code, key = self.new_class()
        self.assertRegex(code, "^[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{6}$")
        self.assertEqual(len(key), 24)
        stored = json.dumps(self.store.get(f"cls:{code}"))
        self.assertNotIn(key, stored)                              # chỉ lưu băm của khóa giáo viên

    def test_students_submit_and_teacher_sees_groups(self):
        code, key = self.new_class()
        for r in (row("Nhóm 1", "H2O", "GHÉP DỞ", **{"thẻ thiếu": "Hx1"}), row("Nhóm 1", "H2O", "ĐÚNG"),
                  row("Nhóm 2", "H2O", "SAI LIÊN KẾT", **{"liên kết sai": "H-H | H-O"})):
            self.clock.t += 5
            self.assertEqual(self.call(action="submit", code=code.lower(), row=r)[0], 200)
        status, out = self.call(action="state", code=code, teacher_key=key)
        self.assertEqual(status, 200)
        by = {g["nhóm"]: g for g in out["nhóm"]}
        self.assertEqual(by["Nhóm 1"]["đã xong"], 1)
        self.assertEqual(by["Nhóm 1"]["lượt"], 2)
        self.assertEqual(by["Nhóm 2"]["đã xong"], 0)
        self.assertEqual(out["tổng lượt"], 3)
        self.assertEqual(out["câu khó"][0]["chất"], "H2O")
        self.assertIn("Tổng số lượt kiểm tra: 3", out["report"])
        self.assertTrue(any(m["mã"] == "H-H" for m in out["quan niệm sai"]))

    def test_group_stuck_after_three_misses_in_a_row(self):
        code, key = self.new_class()
        for _ in range(3):
            self.call(action="submit", code=code, row=row("Nhóm 3", "NaCl", "KHÔNG NHẬN RA"))
        out = self.call(action="state", code=code, teacher_key=key)[1]
        self.assertEqual(out["nhóm kẹt"], ["Nhóm 3"])
        self.call(action="submit", code=code, row=row("Nhóm 3", "NaCl", "ĐÚNG"))
        out = self.call(action="state", code=code, teacher_key=key)[1]
        self.assertEqual(out["nhóm kẹt"], [])

    def test_seconds_since_last_activity(self):
        code, key = self.new_class()
        self.call(action="submit", code=code, row=row("Nhóm 1", "H2O", "ĐÚNG"))
        self.clock.t += 42
        out = self.call(action="state", code=code, teacher_key=key)[1]
        self.assertEqual(out["nhóm"][0]["giây trước"], 42)

    def test_wrong_teacher_key_and_unknown_code(self):
        code, key = self.new_class()
        self.assertEqual(self.call(action="state", code=code, teacher_key="sai")[0], 403)
        self.assertEqual(self.call(action="state", code=code, teacher_key="")[0], 403)
        self.assertEqual(self.call(action="state", code="ZZZZZZ", teacher_key=key)[0], 404)
        self.assertEqual(self.call(action="submit", code="abc", row=row("a", "H2O", "ĐÚNG"))[0], 404)
        self.assertEqual(self.call(action="submit", code=None, row=row("a", "H2O", "ĐÚNG"))[0], 404)

    def test_classroom_expires_after_24_hours(self):
        code, key = self.new_class()
        self.clock.t += C.TTL + 1
        self.assertEqual(self.call(action="state", code=code, teacher_key=key)[0], 404)

    def test_end_deletes_everything(self):
        code, key = self.new_class()
        self.call(action="submit", code=code, row=row("Nhóm 1", "H2O", "ĐÚNG"))
        self.assertEqual(self.call(action="end", code=code, teacher_key="sai")[0], 403)
        self.assertEqual(self.call(action="end", code=code, teacher_key=key)[0], 200)
        self.assertEqual(self.call(action="state", code=code, teacher_key=key)[0], 404)
        self.assertEqual(self.store.lrange(f"evt:{code}"), [])

    def test_submit_validation_and_sanitising(self):
        code, key = self.new_class()
        for bad in (None, "x", {}, row("a", "KHÔNG-CÓ", "ĐÚNG"), row("a", "H2O", "TỰ BỊA")):
            self.assertEqual(self.call(action="submit", code=code, row=bad)[0], 400, bad)
        self.call(action="submit", code=code, row=row("<b>Nhóm \"1\"</b>" + "x" * 80, "H2O", "ĐÚNG", **{"thẻ thiếu": "y" * 500}))
        ev = self.store.lrange(f"evt:{code}")[0]
        self.assertNotIn("<", ev["nhóm"])
        self.assertLessEqual(len(ev["nhóm"]), 30)
        self.assertLessEqual(len(ev["thẻ thiếu"]), 200)

    def test_event_list_is_capped(self):
        code, _ = self.new_class()
        for i in range(C.MAX_EVENTS + 20):
            self.store.rpush(f"evt:{code}", {"i": i}, C.TTL, C.MAX_EVENTS)
        self.assertEqual(len(self.store.lrange(f"evt:{code}")), C.MAX_EVENTS)

    def test_join_checks_code_without_recording_anything(self):
        code, key = self.new_class()
        status, out = self.call(action="join", code=code.lower())
        self.assertEqual((status, out["name"]), (200, "Lớp 7A"))
        self.assertEqual(self.call(action="join", code="ZZZZZZ")[0], 404)
        self.assertEqual(self.store.lrange(f"evt:{code}"), [])
        self.assertEqual(self.call(action="state", code=code, teacher_key=key)[1]["tổng lượt"], 0)

    def test_invalid_action(self):
        self.assertEqual(self.call(action="hack")[0], 400)
        self.assertEqual(self.call()[0], 400)

    def test_rate_limit_hook(self):
        status, _ = C.handle({"action": "create"}, {}, HDR, store=self.store, limiter=lambda a, h: True)
        self.assertEqual(status, 429)

    def test_disabled_without_store(self):
        status, out = C.handle({"action": "create"}, {}, HDR)
        self.assertEqual(status, 503)
        self.assertIn("Upstash", out["error"])

    def test_group_names_do_not_collide_on_state(self):
        code, key = self.new_class()
        self.call(action="submit", code=code, row=row("Nhóm 1", "H2O", "ĐÚNG"))
        self.call(action="submit", code=code, row=row("Nhóm 2", "CO2", "ĐÚNG"))
        out = self.call(action="state", code=code, teacher_key=key)[1]
        self.assertEqual(sorted(g["nhóm"] for g in out["nhóm"]), ["Nhóm 1", "Nhóm 2"])


class Activity(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.store = C.MemoryStore(self.clock)
        _, out = C.handle({"action": "create"}, {}, HDR, store=self.store, now=self.clock())
        self.code, self.key = out["code"], out["teacher_key"]

    def act(self, **kw):
        return C.handle({"action": "activity", "code": self.code, **kw}, {}, HDR, store=self.store, now=self.clock())

    def state(self):
        return C.handle({"action": "state", "code": self.code, "teacher_key": self.key}, {}, HDR, store=self.store, now=self.clock())[1]

    def group(self, name):
        return next(g for g in self.state()["nhóm"] if g["nhóm"] == name)

    def test_group_appears_as_soon_as_it_starts_even_without_attempts(self):
        self.assertEqual(self.act(group="Nhóm 1", type="start", deck="Lớp 8: Oxit", progress="1/6")[0], 200)
        g = self.group("Nhóm 1")
        self.assertEqual((g["lượt"], g["bộ đề"], g["tiến độ"], g["công thức"]), (0, "Lớp 8: Oxit", "1/6", ""))

    def test_skip_hint_end_are_counted(self):
        self.act(group="Nhóm 1", type="start", deck="Khởi động", progress="1/6")
        self.act(group="Nhóm 1", type="skip", progress="2/6")
        self.act(group="Nhóm 1", type="skip", progress="3/6")
        self.act(group="Nhóm 1", type="hint")
        g = self.group("Nhóm 1")
        self.assertEqual((g["bỏ qua"], g["gợi ý"], g["tiến độ"], g["đã kết thúc"]), (2, 1, "3/6", False))
        self.act(group="Nhóm 1", type="end", progress="6/6")
        self.assertTrue(self.group("Nhóm 1")["đã kết thúc"])

    def test_restart_resets_counters(self):
        self.act(group="Nhóm 1", type="start", deck="Khởi động", progress="1/6")
        self.act(group="Nhóm 1", type="skip", progress="2/6")
        self.act(group="Nhóm 1", type="end", progress="6/6")
        self.act(group="Nhóm 1", type="start", deck="Lớp 9: Hiđrocacbon", progress="1/6")
        g = self.group("Nhóm 1")
        self.assertEqual((g["bỏ qua"], g["đã kết thúc"], g["bộ đề"]), (0, False, "Lớp 9: Hiđrocacbon"))

    def test_idle_group_is_flagged_but_finished_group_is_not(self):
        self.act(group="Nhóm 1", type="start", deck="Khởi động", progress="1/6")
        self.act(group="Nhóm 2", type="start", deck="Khởi động", progress="1/6")
        self.act(group="Nhóm 2", type="end", progress="6/6")
        self.clock.t += C.IDLE_AFTER + 5
        out = self.state()
        self.assertEqual(out["nhóm rảnh"], ["Nhóm 1"])
        self.act(group="Nhóm 1", type="skip", progress="2/6")
        self.assertEqual(self.state()["nhóm rảnh"], [])

    def test_stuck_groups_sorted_first(self):
        self.act(group="A", type="start", deck="Khởi động", progress="1/6")
        for _ in range(3):
            C.handle({"action": "submit", "code": self.code, "row": row("Z", "NaCl", "KHÔNG NHẬN RA")}, {}, HDR,
                     store=self.store, now=self.clock())
        names = [g["nhóm"] for g in self.state()["nhóm"]]
        self.assertEqual(names[0], "Z")

    def test_suggestion_feedback_counted(self):
        self.act(group="Nhóm 1", type="suggest", accepted=True)
        self.act(group="Nhóm 1", type="suggest", accepted=False)
        self.act(group="Nhóm 2", type="suggest", accepted=False)
        self.assertEqual(self.state()["gợi ý chất"], {"đúng": 1, "không phải": 2})

    def test_validation(self):
        self.assertEqual(self.act(group="a", type="hack")[0], 400)
        self.assertEqual(self.act(group="a")[0], 400)
        status, _ = C.handle({"action": "activity", "code": "ZZZZZZ", "type": "start"}, {}, HDR, store=self.store)
        self.assertEqual(status, 404)

    def test_sanitising_and_limits(self):
        self.act(group="<b>Nhóm</b>" + "x" * 80, type="start", deck="d" * 500, progress="9" * 50)
        ev = self.store.lrange(f"act:{self.code}")[0]
        self.assertNotIn("<", ev["nhóm"])
        self.assertLessEqual(len(ev["nhóm"]), 30)
        self.assertLessEqual(len(ev["bộ đề"]), 60)
        self.assertLessEqual(len(ev["tiến độ"]), 12)

    def test_end_class_deletes_activity_too(self):
        self.act(group="Nhóm 1", type="start", deck="Khởi động", progress="1/6")
        C.handle({"action": "end", "code": self.code, "teacher_key": self.key}, {}, HDR, store=self.store, now=self.clock())
        self.assertEqual(self.store.lrange(f"act:{self.code}"), [])

    def test_memory_store_keeps_every_concurrent_rpush(self):
        import threading
        store = C.MemoryStore()
        threads = [threading.Thread(target=lambda i=i: [store.rpush("k", {"n": i, "j": j}, 60, 10000) for j in range(200)]) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(store.lrange("k")), 8 * 200)

    def test_activity_is_rate_limited_per_action(self):
        self.assertIn("activity", C.RATE)
        status, _ = C.handle({"action": "activity", "code": self.code, "type": "start"}, {}, HDR, store=self.store,
                             limiter=lambda a, h: a == "activity")
        self.assertEqual(status, 429)


class UpstashRest(unittest.TestCase):
    class Resp:
        def __init__(self, body):
            self.body = json.dumps(body).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return self.body

    def store(self, results):
        calls = []

        def opener(req, timeout=None):
            calls.append((req.full_url, json.loads(req.data), dict(req.header_items())))
            r = results.pop(0)
            if isinstance(r, Exception):
                raise r
            return self.Resp(r)
        return C.UpstashStore("https://example.upstash.io/", "tok-gia", opener=opener), calls

    def test_commands_and_auth_header(self):
        st, calls = self.store([{"result": "OK"}, {"result": json.dumps({"a": 1})}, {"result": 1}, {"result": "OK"}, {"result": 1},
                                {"result": [json.dumps({"x": 1}), json.dumps({"x": 2})]}, {"result": 2}])
        st.set("k", {"a": 1}, 60)
        self.assertEqual(st.get("k"), {"a": 1})
        st.rpush("l", {"x": 1}, 60, 100)
        self.assertEqual(st.lrange("l"), [{"x": 1}, {"x": 2}])
        st.delete("k", "l")
        self.assertEqual(calls[0][1][:2], ["SET", "k"])
        self.assertEqual(calls[0][1][-2:], ["EX", 60])
        self.assertEqual([c[1][0] for c in calls[2:5]], ["RPUSH", "LTRIM", "EXPIRE"])
        self.assertEqual(calls[0][2]["Authorization"], "Bearer tok-gia")
        self.assertNotIn("tok-gia", calls[0][0])
        self.assertEqual(calls[-1][1][0], "DEL")

    def test_missing_key_returns_none(self):
        st, _ = self.store([{"result": None}])
        self.assertIsNone(st.get("k"))

    def test_network_and_server_errors_become_store_error(self):
        st, _ = self.store([urllib.error.URLError("mất mạng")])
        with self.assertRaises(C.StoreError):
            st.get("k")
        st, _ = self.store([{"error": "WRONGPASS"}])
        with self.assertRaises(C.StoreError):
            st.get("k")

    def test_handler_reports_store_failure_as_503(self):
        st, _ = self.store([urllib.error.URLError("x")] * 5)
        status, out = C.handle({"action": "create"}, {}, HDR, store=st)
        self.assertEqual(status, 503)
        self.assertNotIn("tok-gia", json.dumps(out))

    def test_store_selection_from_environment(self):
        self.assertIsNone(C.get_store({}))
        self.assertIsInstance(C.get_store({"UPSTASH_REDIS_REST_URL": "https://u", "UPSTASH_REDIS_REST_TOKEN": "t"}), C.UpstashStore)
        self.assertIsInstance(C.get_store({"KV_REST_API_URL": "https://u", "KV_REST_API_TOKEN": "t"}), C.UpstashStore)
        self.assertIsInstance(C.get_store({"CLASSROOM_MEMORY": "1"}), C.MemoryStore)
        self.assertIsNone(C.get_store({"UPSTASH_REDIS_REST_URL": "https://u"}))


class ThroughWeb(unittest.TestCase):
    def setUp(self):
        web._hits.clear()
        C._memory.data.clear()

    def test_meta_reports_whether_classroom_is_available(self):
        self.assertFalse(web.handle_meta({})[1]["classroom"])
        self.assertTrue(web.handle_meta({"CLASSROOM_MEMORY": "1"})[1]["classroom"])

    def test_route_end_to_end_with_rate_limit(self):
        env = {"CLASSROOM_MEMORY": "1"}
        method, fn = web.ROUTES["classroom"]
        self.assertEqual(method, "POST")
        status, out = fn({"action": "create"}, env, {"x-forwarded-for": "9.9.9.1"})
        self.assertEqual(status, 200)
        code, key = out["code"], out["teacher_key"]
        status, out = fn({"action": "submit", "code": code, "row": row("Nhóm 1", "H2O", "ĐÚNG")}, env, {"x-forwarded-for": "9.9.9.2"})
        self.assertEqual(status, 200)
        status, out = fn({"action": "state", "code": code, "teacher_key": key}, env, {"x-forwarded-for": "9.9.9.1"})
        self.assertEqual(out["tổng lượt"], 1)
        for _ in range(C.RATE["create"][0] + 1):
            status, _ = fn({"action": "create"}, env, {"x-forwarded-for": "9.9.9.3"})
        self.assertEqual(status, 429)

    def test_api_file_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "..", "api", "classroom.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
