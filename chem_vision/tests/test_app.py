import os
import sys
import tempfile
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision.app import App, BlankCamera
from chem_vision.core import analyze
from chem_vision.recognizer import DemoRecognizer, GeminiRecognizer, MODELS, SCENARIOS, create_prompt, frame_to_jpeg
from chem_vision.retry import ApiError, GaveUp


class FakeSpeaker:
    def __init__(self):
        self.said = []

    def say(self, text, block=False):
        self.said.append(text)


def make_app(scenario="Nước, ghép đúng", speaker=None):
    try:
        root = tk.Tk()
    except tk.TclError as err:
        raise unittest.SkipTest(f"không có màn hình: {err}")
    root.withdraw()
    path = os.path.join(tempfile.mkdtemp(), "log.csv")
    rec = DemoRecognizer(scenario)
    return root, App(root, rec, BlankCamera(), speaker, log_path=path, sync=True), rec


def text_of(app):
    return app.result.get("1.0", "end").strip()


class Gui(unittest.TestCase):
    def tearDown(self):
        getattr(self, "root", None) and self.root.destroy()

    def run_check(self, scenario, speaker=None):
        self.root, app, rec = make_app(scenario, speaker)
        app.scenario_var.set(scenario)
        rec.scenario = scenario
        app.check()
        return app

    def test_match(self):
        app = self.run_check("Nước, ghép đúng")
        self.assertIn("Cấu trúc khớp với nước", text_of(app))
        self.assertEqual(app.check_btn["state"], "normal")

    def test_wrong_bonds_message(self):
        app = self.run_check("Nước, sai liên kết")
        self.assertIn("thừa liên kết H–H", text_of(app))

    def test_suggestion_flow(self):
        app = self.run_check("Ghép dở (H–O)")
        self.assertIn("Có phải bạn muốn ghép nước (H2O)?", app.sug_label["text"])
        app.answer_suggestion(False)
        self.assertIn("natri hiđroxit", app.sug_label["text"])
        app.answer_suggestion(False)
        self.assertIn("kali hiđroxit", app.sug_label["text"])
        app.answer_suggestion(False)
        self.assertIn("Hết gợi ý", text_of(app))
        app.check()
        app.answer_suggestion(True)
        self.assertIn("Cấu trúc chuẩn: O nối với H, H", text_of(app))
        self.assertIn("Còn thiếu 1 thẻ H", text_of(app))

    def test_recapture_and_empty(self):
        self.assertIn("độ tin cậy 0,45", text_of(self.run_check("Ảnh chưa rõ")))
        self.root.destroy()
        self.assertIn("Không thấy thẻ", text_of(self.run_check("Không có thẻ")))

    def test_speech_uses_plain_text(self):
        sp = FakeSpeaker()
        self.run_check("Ghép dở (H–O)", sp)
        self.assertEqual(len(sp.said), 1)
        self.assertNotIn("H2O", sp.said[0])

    def test_challenge_flow_and_log(self):
        self.root, app, rec = make_app()
        app.deck_var.set("Khởi động")
        app.start_challenge()                       # câu 1: H2
        self.assertIn("hiđro (H2)", app.task_label["text"])
        rec.scenario = "Nước, sai liên kết"
        app.check()
        self.assertIn("Chưa đúng", text_of(app))
        app.hint()
        self.assertIn("Gợi ý 1", text_of(app))
        app.skip()                                   # sang câu 2: O2
        app.skip()                                   # câu 3: H2O
        self.assertIn("nước (H2O)", app.task_label["text"])
        rec.scenario = "Nước, ghép đúng"
        app.check()
        self.assertIn("Chính xác", text_of(app))
        self.assertEqual(len(app.log.rows), 2)
        report = app.show_report()
        report.destroy()
        app.end_challenge()
        self.assertIn("Tổng kết", text_of(app))

    def test_ai_failure_shown(self):
        self.root, app, rec = make_app()

        def boom(_):
            raise GaveUp(ApiError(503, "quá tải"), 6)
        rec.recognize = boom
        app.check()
        self.assertIn("Không kết nối được dịch vụ AI", text_of(app))
        self.assertEqual(app.check_btn["state"], "normal")


class FakeGenai:
    """Máy khách Gemini giả: trả lỗi theo kịch bản rồi trả JSON."""
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls.append((model, config))
        o = self.outcomes.pop(0)
        if isinstance(o, Exception):
            raise o
        return type("R", (), {"text": o})()


class CodeError(Exception):
    def __init__(self, code):
        self.code = code


class Gemini(unittest.TestCase):
    def frame(self):
        import numpy as np
        return np.full((60, 80, 3), 200, dtype="uint8")

    def test_prompt_has_no_formula(self):
        p = create_prompt()
        for formula in ("H2O", "CO2", "NaCl", "CH4", "H2SO4"):
            self.assertNotIn(formula, p)
        self.assertIn("mỗi thẻ là một nguyên tử", p)

    def test_jpeg_in_memory(self):
        self.assertTrue(frame_to_jpeg(self.frame()).startswith(b"\xff\xd8"))

    def test_success_uses_json_config(self):
        fake = FakeGenai([SCENARIOS["Nước, ghép đúng"]])
        rec = GeminiRecognizer("k", client=fake)
        self.assertEqual(analyze(rec.recognize(self.frame())).matches(), ["H2O"])
        cfg = fake.calls[0][1]
        self.assertEqual(cfg.temperature, 0.1)
        self.assertEqual(cfg.response_mime_type, "application/json")

    def test_retry_then_fallback_model(self):
        fake = FakeGenai([CodeError(503)] * 3 + [SCENARIOS["CO2, ghép đúng"]])
        slept = []
        rec = GeminiRecognizer("k", client=fake, sleep=slept.append)
        self.assertEqual(analyze(rec.recognize(self.frame())).matches(), ["CO2"])
        self.assertEqual([c[0] for c in fake.calls], [MODELS[0]] * 3 + [MODELS[1]])
        self.assertEqual(rec.last_model, MODELS[1])
        self.assertEqual(slept, [2.0, 4.0])

    def test_auth_error_stops(self):
        fake = FakeGenai([CodeError(401)])
        with self.assertRaises(GaveUp):
            GeminiRecognizer("k", client=fake).recognize(self.frame())
        self.assertEqual(len(fake.calls), 1)

    def test_network_error_is_transient(self):
        fake = FakeGenai([ConnectionError("mất mạng"), SCENARIOS["Nước, ghép đúng"]])
        rec = GeminiRecognizer("k", client=fake, sleep=lambda s: None)
        self.assertTrue(rec.recognize(self.frame()))
        self.assertEqual(len(fake.calls), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
