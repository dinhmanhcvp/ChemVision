import base64
import http.client
import json
import os
import sys
import threading
import unittest
import urllib.error
from http.server import ThreadingHTTPServer

import cv2
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from chem_vision import web
from chem_vision.recognizer import MODELS, GeminiRest, create_prompt, frame_to_jpeg
from chem_vision.retry import ApiError, GaveUp

ENV = {"ACCESS_CODE": "ma-bi-mat", "GEMINI_API_KEY": "khoa-gia"}
HDR = {"x-access-code": "ma-bi-mat", "x-forwarded-for": "1.2.3.4"}


def jpeg_b64(color=(60, 90, 130)):
    img = np.full((120, 160, 3), color, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    return base64.b64encode(buf.tobytes()).decode()


class FakeRecognizer:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.last_model = text, error, "model-gia"

    def recognize_jpeg(self, jpeg, frame):
        if self.error:
            raise self.error
        return self.text


WATER = json.dumps({"cards": [{"id": 1, "symbol": "H", "confidence": 0.9}, {"id": 2, "symbol": "O", "confidence": 0.9},
                              {"id": 3, "symbol": "H", "confidence": 0.9}],
                    "connections": [{"a": 1, "b": 2}, {"a": 2, "b": 3}]})


class Analyze(unittest.TestCase):
    def setUp(self):
        web._hits.clear()

    def run_(self, payload, env=ENV, headers=HDR, rec=None):
        return web.handle_analyze(payload, env, headers, recognizer=rec)

    def test_demo_needs_no_key_or_code(self):
        status, out = web.handle_analyze({"demo": "Nước, ghép đúng"}, {}, {})
        self.assertEqual(status, 200)
        self.assertIn("Cấu trúc khớp với nước", out["message"])
        self.assertEqual(out["clusters"][0]["substance"]["key"], "H2O")

    def test_demo_suggestions_structure(self):
        _, out = web.handle_analyze({"demo": "Ghép dở (H–O)"}, {}, {})
        sug = out["clusters"][0]["suggestions"]
        self.assertEqual([s["key"] for s in sug], ["H2O", "NaOH", "KOH"])
        self.assertEqual(sug[0]["missing"], {"H": 1})
        self.assertIn("O nối với H, H", sug[0]["structure"])

    def test_unknown_demo(self):
        self.assertEqual(web.handle_analyze({"demo": "không có"}, {}, {})[0], 400)

    def test_image_with_fake_recognizer(self):
        status, out = self.run_({"image": jpeg_b64()}, rec=FakeRecognizer(WATER))
        self.assertEqual(status, 200)
        self.assertEqual(out["status"], "OK")
        self.assertEqual(out["clusters"][0]["kind"], "MATCH")
        self.assertEqual(out["model"], "model-gia")
        self.assertEqual(len(out["cards"]), 3)

    def test_data_url_accepted(self):
        status, _ = self.run_({"image": "data:image/jpeg;base64," + jpeg_b64()}, rec=FakeRecognizer(WATER))
        self.assertEqual(status, 200)

    def test_attempt_for_challenge_target(self):
        _, out = self.run_({"image": jpeg_b64(), "target": "H2O"}, rec=FakeRecognizer(WATER))
        self.assertTrue(out["attempt"]["correct"])
        _, out = self.run_({"image": jpeg_b64(), "target": "CO2"}, rec=FakeRecognizer(WATER))
        self.assertFalse(out["attempt"]["correct"])
        self.assertEqual(out["attempt"]["kind"], "MATCH_OTHER")

    def test_invalid_target(self):
        self.assertEqual(self.run_({"image": jpeg_b64(), "target": "XYZ"}, rec=FakeRecognizer(WATER))[0], 400)

    def test_access_code_required(self):
        self.assertEqual(self.run_({"image": jpeg_b64()}, headers={"x-forwarded-for": "9.9.9.9"}, rec=FakeRecognizer(WATER))[0], 401)
        self.assertEqual(self.run_({"image": jpeg_b64()}, headers={"x-access-code": "sai"}, rec=FakeRecognizer(WATER))[0], 401)

    def test_access_code_in_body_ok(self):
        status, _ = self.run_({"image": jpeg_b64(), "code": "ma-bi-mat"}, headers={}, rec=FakeRecognizer(WATER))
        self.assertEqual(status, 200)

    def test_server_without_access_code_refuses(self):
        status, out = self.run_({"image": jpeg_b64()}, env={"GEMINI_API_KEY": "k"}, rec=FakeRecognizer(WATER))
        self.assertEqual(status, 503)
        self.assertIn("ACCESS_CODE", out["error"])

    def test_missing_api_key(self):
        status, out = self.run_({"image": jpeg_b64()}, env={"ACCESS_CODE": "ma-bi-mat"})
        self.assertEqual(status, 503)
        self.assertIn("GEMINI_API_KEY", out["error"])

    def test_bad_images(self):
        for bad in (None, "", "không phải base64!!", base64.b64encode(b"PNG....").decode(), 123):
            self.assertEqual(self.run_({"image": bad}, rec=FakeRecognizer(WATER))[0], 400, repr(bad)[:30])

    def test_too_large(self):
        big = base64.b64encode(b"\xff\xd8" + b"0" * (web.MAX_IMAGE_BYTES + 10)).decode()
        self.assertEqual(self.run_({"image": big}, rec=FakeRecognizer(WATER))[0], 413)

    def test_corrupt_jpeg(self):
        bad = base64.b64encode(b"\xff\xd8" + b"nothing").decode()
        self.assertEqual(self.run_({"image": bad}, rec=FakeRecognizer(WATER))[0], 400)

    def test_rate_limit(self):
        codes = [self.run_({"image": jpeg_b64()}, rec=FakeRecognizer(WATER))[0] for _ in range(web.RATE_LIMIT[0] + 2)]
        self.assertEqual(codes[:web.RATE_LIMIT[0]], [200] * web.RATE_LIMIT[0])
        self.assertEqual(codes[-1], 429)
        self.assertEqual(web.handle_analyze({"image": jpeg_b64()}, ENV, {**HDR, "x-forwarded-for": "5.6.7.8"},
                                            recognizer=FakeRecognizer(WATER))[0], 200)   # địa chỉ khác không bị ảnh hưởng

    def test_upstream_failure_hides_details(self):
        err = GaveUp(ApiError(503, "chi tiết nội bộ khóa=abc"), 6)
        status, out = self.run_({"image": jpeg_b64()}, rec=FakeRecognizer(error=err))
        self.assertEqual(status, 502)
        self.assertNotIn("abc", json.dumps(out))

    def test_recapture_status(self):
        low = json.dumps({"cards": [{"id": 1, "symbol": "C", "confidence": 0.4}], "connections": []})
        _, out = self.run_({"image": jpeg_b64()}, rec=FakeRecognizer(low))
        self.assertEqual(out["status"], "RECAPTURE")


class Others(unittest.TestCase):
    def test_meta(self):
        status, out = web.handle_meta()
        self.assertEqual(status, 200)
        self.assertEqual(out["substances"], 31)
        self.assertIn("Khởi động", out["decks"])
        self.assertEqual(out["decks"]["Khởi động"][0]["formula"], "H2")
        self.assertEqual(out["scoring"]["base"], 10)

    def test_hint(self):
        self.assertIn("hiđro", web.handle_hint({"target": "H2O", "level": 1})[1]["hint"])
        self.assertIn("O nối với H, H", web.handle_hint({"target": "H2O", "level": 3})[1]["hint"])
        for bad in ({"target": "X", "level": 1}, {"target": "H2O", "level": 0}, {"target": "H2O", "level": 4},
                    {"target": "H2O", "level": True}, {"target": "H2O", "level": "1"}):
            self.assertEqual(web.handle_hint(bad)[0], 400, bad)

    def test_report(self):
        rows = [{"thời gian": "t", "nhóm": "Nhóm 1", "chất mục tiêu": "H2O", "kết quả": "GHÉP DỞ", "thẻ thiếu": "Hx1",
                 "thẻ thừa": "", "liên kết sai": ""},
                {"thời gian": "t", "nhóm": "Nhóm 1", "chất mục tiêu": "H2O", "kết quả": "ĐÚNG", "thẻ thiếu": "", "thẻ thừa": "",
                 "liên kết sai": ""},
                {"nhóm": "x", "chất mục tiêu": "KHÔNG-CÓ"}]
        status, out = web.handle_report({"rows": rows})
        self.assertEqual(status, 200)
        self.assertEqual(out["rows"], 2)                               # dòng chất lạ bị bỏ
        self.assertIn("Tổng số lượt kiểm tra: 2", out["report"])
        self.assertTrue(out["csv"].startswith("thời gian,nhóm,chất mục tiêu"))

    def test_report_validation(self):
        for bad in ({}, {"rows": "x"}, {"rows": [1]}, {"rows": [{}] * 5001}):
            self.assertEqual(web.handle_report(bad)[0], 400)
        self.assertIn("Chưa có", web.handle_report({"rows": []})[1]["report"])


class RestClient(unittest.TestCase):
    class Resp:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(self.body).encode()

    def client(self, outcomes):
        calls = []

        def opener(req, timeout=None):
            calls.append((req.full_url, json.loads(req.data), dict(req.header_items())))
            o = outcomes.pop(0)
            if isinstance(o, Exception):
                raise o
            return self.Resp(o)
        return GeminiRest("khoa-gia", opener=opener, sleep=lambda s: None), calls

    @staticmethod
    def ok(text):
        return {"candidates": [{"content": {"parts": [{"text": text}]}}]}

    @staticmethod
    def http_error(code, body="lỗi", headers=None):
        import io
        from email.message import Message
        h = Message()
        for k, v in (headers or {}).items():
            h[k] = v
        return urllib.error.HTTPError("http://x", code, "err", h, io.BytesIO(body.encode()))

    def test_request_shape_and_key_header(self):
        c, calls = self.client([self.ok(WATER)])
        text = c.recognize_jpeg(b"\xff\xd8abc")
        self.assertEqual(text, WATER)
        url, body, headers = calls[0]
        self.assertIn("gemini-2.5-flash:generateContent", url)
        self.assertNotIn("khoa-gia", url)                                  # khóa chỉ nằm trong header, không nằm trong URL
        self.assertEqual(headers["X-goog-api-key"], "khoa-gia")
        cfg = body["generationConfig"]
        self.assertEqual((cfg["temperature"], cfg["responseMimeType"]), (0.1, "application/json"))
        self.assertEqual(cfg["thinkingConfig"], {"thinkingBudget": 0})
        self.assertEqual(body["contents"][0]["parts"][0]["inline_data"]["mime_type"], "image/jpeg")

    def test_thinking_rejected_then_retried_without_and_remembered_per_model(self):
        c, calls = self.client([self.http_error(400, "Request contains an invalid argument"), self.ok(WATER), self.ok(WATER)])
        self.assertEqual(c.recognize_jpeg(b"\xff\xd8"), WATER)
        self.assertNotIn("thinkingConfig", calls[1][1]["generationConfig"])
        self.assertEqual(c.no_thinking, {MODELS[0]})
        c.recognize_jpeg(b"\xff\xd8")                                     # lần sau không gửi lại tùy chọn bị từ chối
        self.assertNotIn("thinkingConfig", calls[2][1]["generationConfig"])

    def test_retry_then_fallback_model(self):
        c, calls = self.client([self.http_error(503)] * 3 + [self.ok(WATER)])
        c.recognize_jpeg(b"\xff\xd8")
        self.assertIn(MODELS[1] + ":generate", calls[3][0])
        self.assertEqual(c.last_model, MODELS[1])

    def test_prompt_has_no_formula(self):
        p = create_prompt()
        for formula in ("H2O", "CO2", "NaCl", "CH4", "H2SO4"):
            self.assertNotIn(formula, p)
        self.assertIn("mỗi thẻ là một nguyên tử", p)
        self.assertIn("box_2d", p)

    def test_jpeg_in_memory(self):
        self.assertTrue(frame_to_jpeg(np.full((60, 80, 3), 200, dtype="uint8")).startswith(b"\xff\xd8"))

    def test_recognize_frame_for_desktop(self):
        c, calls = self.client([self.ok(WATER)])
        out = json.loads(c.recognize(np.full((60, 80, 3), 200, dtype="uint8")))
        self.assertIn("cards", out)

    def test_auth_error_stops(self):
        c, calls = self.client([self.http_error(403, "API key not valid")])
        with self.assertRaises(GaveUp):
            c.recognize_jpeg(b"\xff\xd8")
        self.assertEqual(len(calls), 1)

    def test_network_error_transient(self):
        c, calls = self.client([urllib.error.URLError("mất mạng"), self.ok(WATER)])
        self.assertEqual(c.recognize_jpeg(b"\xff\xd8"), WATER)

    def test_empty_answer_is_transient(self):
        c, calls = self.client([{"candidates": []}, self.ok(WATER)])
        self.assertEqual(c.recognize_jpeg(b"\xff\xd8"), WATER)


class HttpEndToEnd(unittest.TestCase):
    """Chạy máy chủ thử cục bộ thật và gọi qua HTTP, đi đúng đường của các hàm trong api/."""

    @classmethod
    def setUpClass(cls):
        import dev_server
        cls.old = {k: os.environ.get(k) for k in ("ACCESS_CODE", "GEMINI_API_KEY")}
        os.environ["ACCESS_CODE"], os.environ["GEMINI_API_KEY"] = "ma-bi-mat", "khoa-gia"
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), dev_server.Dev)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        for k, v in cls.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=20)
        data = json.dumps(body).encode() if body is not None else None
        c.request(method, path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
        r = c.getresponse()
        raw = r.read()
        return r.status, r.getheader("Content-Type"), raw

    def test_meta_get(self):
        s, ct, raw = self.req("GET", "/api/meta")
        self.assertEqual(s, 200)
        self.assertIn("application/json", ct)
        self.assertEqual(json.loads(raw)["substances"], 31)

    def test_wrong_method_is_405_json(self):
        s, ct, raw = self.req("GET", "/api/analyze")
        self.assertEqual(s, 405)
        self.assertFalse(json.loads(raw)["ok"])

    def test_demo_over_http(self):
        s, _, raw = self.req("POST", "/api/analyze", {"demo": "Nước, sai liên kết"})
        out = json.loads(raw)
        self.assertEqual((s, out["clusters"][0]["kind"]), (200, "WRONG_BONDS"))
        self.assertIn("thừa liên kết H–H", out["message"])

    def test_image_without_code_is_401(self):
        s, _, _ = self.req("POST", "/api/analyze", {"image": jpeg_b64()})
        self.assertEqual(s, 401)

    def test_hint_and_report_over_http(self):
        s, _, raw = self.req("POST", "/api/hint", {"target": "CO2", "level": 2})
        self.assertEqual(s, 200)
        self.assertIn("1 thẻ C", json.loads(raw)["hint"])
        s, _, raw = self.req("POST", "/api/report", {"rows": []})
        self.assertEqual(s, 200)

    def test_bad_body(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", "/api/hint", body=b"khong phai json", headers={"Content-Length": "15"})
        self.assertEqual(c.getresponse().status, 400)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", "/api/hint", body=b"[1,2]", headers={"Content-Length": "5"})
        self.assertEqual(c.getresponse().status, 400)

    def test_unknown_route_and_traversal(self):
        self.assertEqual(self.req("GET", "/api/khong-co")[0], 404)
        self.assertEqual(self.req("GET", "/../vercel.json")[0], 404)
        self.assertEqual(self.req("GET", "/..%2fvercel.json")[0], 404)


class VercelConfig(unittest.TestCase):
    def test_vercel_json(self):
        cfg = json.load(open(os.path.join(ROOT, "vercel.json"), encoding="utf-8"))
        self.assertEqual(cfg["outputDirectory"], "public")
        fn = cfg["functions"]["api/*.py"]
        self.assertLessEqual(fn["maxDuration"], 60)
        self.assertIn("chem_vision", fn["includeFiles"])
        headers = {h["key"]: h["value"] for h in cfg["headers"][0]["headers"]}
        self.assertIn("camera=(self)", headers["Permissions-Policy"])
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])

    def test_files_present(self):
        for rel in ("api/analyze.py", "api/meta.py", "api/hint.py", "api/report.py", "public/index.html",
                    "public/app.js", "public/style.css", "requirements.txt", ".python-version"):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, rel)), rel)
        reqs = open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8").read().split()
        self.assertEqual(sorted(reqs), ["numpy", "opencv-python-headless"])        # không kéo pygame/gTTS/Tkinter lên Vercel

    def test_function_modules_import_only_web_dependencies(self):
        import ast
        banned = {"tkinter", "pygame", "gtts", "google", "PIL"}
        for name in ("web", "recognizer", "core", "features", "geometry", "retry"):
            tree = ast.parse(open(os.path.join(ROOT, "chem_vision", name + ".py"), encoding="utf-8").read())
            top = {n.names[0].name.split(".")[0] for n in tree.body if isinstance(n, ast.Import)}
            top |= {n.module.split(".")[0] for n in tree.body if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
            self.assertFalse(top & banned, (name, top & banned))


if __name__ == "__main__":
    unittest.main(verbosity=2)
