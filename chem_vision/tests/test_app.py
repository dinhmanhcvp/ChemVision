import os
import sys
import tempfile
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from chem_vision.app import App, BlankCamera
from chem_vision.core import analyze
from chem_vision.recognizer import DemoRecognizer, SCENARIOS
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
