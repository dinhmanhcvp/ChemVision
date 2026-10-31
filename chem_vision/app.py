"""Giao diện CHEM VISION (Tkinter): camera trực tiếp, nút KIỂM TRA, kết quả, gợi ý, chế độ
thử thách, nhật ký lớp học và đọc kết quả bằng giọng nói."""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .core import _speech_of, analyze, count_phrase, describe_structure, sub_label
from .features import DECKS, Challenge, SessionLog
from .recognizer import SCENARIOS, DemoRecognizer
from .retry import GaveUp

BG, PANEL, ACCENT, OK, BAD, WARN = "#f4f6fb", "#ffffff", "#2f5496", "#1b7a3d", "#b3261e", "#9a6700"
FONT = "Segoe UI"
FRAME_MS = 15


class Camera:
    """Camera USB. Trên Windows dùng DirectShow, yêu cầu 1280 x 720."""

    def __init__(self, index: int = 0):
        import cv2
        self.cv2 = cv2
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if os.name == "nt" else cv2.VideoCapture(index)
        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    @property
    def opened(self) -> bool:
        return bool(self.cap.isOpened())

    def read(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def release(self):
        self.cap.release()


class BlankCamera:
    """Khung hình trống cho chế độ thử không có camera."""
    opened = True

    def read(self):
        import numpy as np
        frame = np.full((720, 1280, 3), 235, dtype="uint8")
        return frame

    def release(self):
        pass


class App:
    def __init__(self, root, recognizer, camera=None, speaker=None, log_path="nhat_ky_lop_hoc.csv",
                 mode_text="Chế độ thử (giả lập)", sync=False):
        self.root, self.recognizer = root, recognizer
        self.camera = camera or BlankCamera()
        self.speaker, self.sync, self.mode_text = speaker, sync, mode_text
        self.log = SessionLog(log_path)
        self.challenge: Challenge | None = None
        self.sugs, self.sug_i = [], 0
        self.busy = False
        self.speak_var = tk.BooleanVar(value=speaker is not None)
        self.group_var = tk.StringVar(value="Nhóm 1")
        self.deck_var = tk.StringVar(value=next(iter(DECKS)))
        self.scenario_var = tk.StringVar(value=next(iter(SCENARIOS)))
        self._photo = None
        self._build()
        self._tick()

    # ------------------------------------------------------------------ giao diện
    def _build(self):
        r = self.root
        r.title("CHEM VISION – Ghép thẻ nguyên tố, nhận diện phân tử")
        r.configure(bg=BG)
        r.geometry("1200x820")
        r.minsize(1000, 760)
        left = tk.Frame(r, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(14, 7), pady=14)
        tk.Label(left, text="CAMERA LIVE", font=(FONT, 11, "bold"), bg=BG, fg=ACCENT).pack(anchor="w")
        self.cam_frame = tk.Frame(left, bg="#111", width=320, height=180)
        self.cam_frame.pack(fill="both", expand=True, pady=(4, 6))
        self.cam_frame.pack_propagate(False)             # khung không phình theo ảnh
        self.cam_label = tk.Label(self.cam_frame, bg="#111", bd=0)
        self.cam_label.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(left, text="Ghép các thẻ chạm cạnh nhau trong phân tử; để các phân tử khác cách xa. "
                 "Kiểm tra thẻ rõ trước khi nhấn KIỂM TRA.", font=(FONT, 9), bg=BG, fg="#555",
                 wraplength=620, justify="left").pack(anchor="w")

        right = tk.Frame(r, bg=BG, width=500)
        right.pack(side="right", fill="y", padx=(7, 14), pady=14)
        right.pack_propagate(False)

        head = tk.Frame(right, bg=BG)
        head.pack(fill="x")
        tk.Label(head, text="Nhóm:", bg=BG, font=(FONT, 10)).pack(side="left")
        tk.Entry(head, textvariable=self.group_var, width=12, font=(FONT, 10)).pack(side="left", padx=6)
        tk.Label(head, text=self.mode_text, bg=BG, fg="#666", font=(FONT, 9)).pack(side="right")

        box = tk.LabelFrame(right, text=" Chế độ thử thách ", bg=BG, font=(FONT, 10, "bold"), fg=ACCENT)
        box.pack(fill="x", pady=(10, 6))
        row = tk.Frame(box, bg=BG)
        row.pack(fill="x", padx=8, pady=(6, 2))
        ttk.Combobox(row, textvariable=self.deck_var, values=list(DECKS), state="readonly", width=18).pack(side="left")
        tk.Button(row, text="Bắt đầu", command=self.start_challenge).pack(side="left", padx=6)
        tk.Button(row, text="Kết thúc", command=self.end_challenge).pack(side="left")
        self.task_label = tk.Label(box, text="Chưa bắt đầu. Chọn bộ đề rồi nhấn Bắt đầu.", bg=BG, fg="#333",
                                   font=(FONT, 10), wraplength=470, justify="left")
        self.task_label.pack(fill="x", padx=8)
        row2 = tk.Frame(box, bg=BG)
        row2.pack(fill="x", padx=8, pady=(2, 6))
        self.hint_btn = tk.Button(row2, text="Gợi ý (−2 điểm)", command=self.hint, state="disabled")
        self.hint_btn.pack(side="left")
        self.skip_btn = tk.Button(row2, text="Bỏ qua câu", command=self.skip, state="disabled")
        self.skip_btn.pack(side="left", padx=6)

        self.check_btn = tk.Button(right, text="KIỂM TRA", command=self.check, font=(FONT, 15, "bold"),
                                   bg=ACCENT, fg="white", activebackground="#1f3a73", activeforeground="white",
                                   relief="flat", pady=8)
        self.check_btn.pack(fill="x", pady=(6, 8))

        tk.Label(right, text="KẾT QUẢ", font=(FONT, 11, "bold"), bg=BG, fg=ACCENT).pack(anchor="w")
        self.result = tk.Text(right, height=6, wrap="word", font=(FONT, 11), bg=PANEL, relief="solid", bd=1,
                              padx=8, pady=6, state="disabled")
        self.result.pack(fill="both", expand=True, pady=(2, 6))
        for tag, color in (("ok", OK), ("bad", BAD), ("warn", WARN), ("info", "#222")):
            self.result.tag_configure(tag, foreground=color)

        self.sug_frame = tk.Frame(right, bg=BG)
        self.sug_label = tk.Label(self.sug_frame, text="", bg=BG, font=(FONT, 10, "bold"), wraplength=430, justify="left")
        self.sug_label.pack(anchor="w")
        btns = tk.Frame(self.sug_frame, bg=BG)
        btns.pack(anchor="w", pady=4)
        tk.Button(btns, text="Đúng", width=12, command=lambda: self.answer_suggestion(True)).pack(side="left")
        tk.Button(btns, text="Không phải", width=12, command=lambda: self.answer_suggestion(False)).pack(side="left", padx=6)

        foot = self.foot = tk.Frame(right, bg=BG)
        foot.pack(fill="x", pady=(4, 0))
        tk.Checkbutton(foot, text="Đọc kết quả", variable=self.speak_var, bg=BG,
                       state="normal" if self.speaker else "disabled").pack(side="left")
        tk.Button(foot, text="Báo cáo lớp học", command=self.show_report).pack(side="right")
        if isinstance(self.recognizer, DemoRecognizer):
            demo = self.demo_frame = tk.Frame(right, bg=BG)
            demo.pack(fill="x", pady=(6, 0))
            tk.Label(demo, text="Tình huống giả lập:", bg=BG, font=(FONT, 9)).pack(side="left")
            cb = ttk.Combobox(demo, textvariable=self.scenario_var, values=list(SCENARIOS), state="readonly", width=24)
            cb.pack(side="left", padx=6)
            cb.bind("<<ComboboxSelected>>", lambda _e: setattr(self.recognizer, "scenario", self.scenario_var.get()))
            self.recognizer.scenario = self.scenario_var.get()
        self.status = tk.Label(right, text="", bg=BG, fg="#777", font=(FONT, 8), anchor="w")
        self.status.pack(fill="x")
        # chân trang neo ở đáy; khung kết quả nhận phần còn lại để không che nút
        self.status.pack_forget(); self.status.pack(side="bottom", fill="x")
        if getattr(self, "demo_frame", None):
            self.demo_frame.pack_forget(); self.demo_frame.pack(side="bottom", fill="x", pady=(6, 0))
        self.foot.pack_forget(); self.foot.pack(side="bottom", fill="x", pady=(4, 0))
        self.result.pack_forget(); self.result.pack(fill="both", expand=True, pady=(2, 6))
        r.protocol("WM_DELETE_WINDOW", self.close)

    def _tick(self):
        frame = self.camera.read()
        if frame is not None:
            try:
                from PIL import Image, ImageTk
                h, w = frame.shape[:2]
                fw, fh = max(self.cam_frame.winfo_width(), 320), max(self.cam_frame.winfo_height(), 180)
                scale = min(fw / w, fh / h)
                img = Image.fromarray(frame[:, :, ::-1]).resize((max(int(w * scale), 1), max(int(h * scale), 1)))
                self._photo = ImageTk.PhotoImage(img)
                self.cam_label.configure(image=self._photo)
            except Exception:
                pass
        self._after = self.root.after(FRAME_MS if not isinstance(self.camera, BlankCamera) else 120, self._tick)

    def close(self):
        try:
            self.root.after_cancel(self._after)
        except Exception:
            pass
        self.camera.release()
        self.root.destroy()

    # ------------------------------------------------------------------ hiển thị
    def set_result(self, text: str, tag: str = "info"):
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("end", text, tag)
        self.result.configure(state="disabled")

    def speak(self, text: str):
        if self.speaker and self.speak_var.get():
            self.speaker.say(text)

    # ------------------------------------------------------------------ kiểm tra
    def check(self):
        if self.busy:
            return
        frame = self.camera.read()
        if frame is None:
            self.set_result("Không đọc được hình từ camera. Hãy kiểm tra kết nối camera.", "bad")
            return
        self.busy = True
        self.check_btn.configure(state="disabled", text="Đang phân tích…")
        self.sug_frame.pack_forget()
        frame = frame.copy()                       # chỉ một khung hình này được gửi đi
        if self.sync:
            self._work(frame)
        else:
            threading.Thread(target=self._work, args=(frame,), daemon=True).start()

    def _work(self, frame):
        try:
            raw = self.recognizer.recognize(frame)
            analysis, error = analyze(raw), None
        except GaveUp as err:
            analysis, error = None, f"Không kết nối được dịch vụ AI ({err.last}). Kiểm tra mạng và khóa API rồi thử lại."
        except Exception as err:
            analysis, error = None, f"Lỗi khi nhận diện: {err}"
        if self.sync:
            self._finish(analysis, error)
        else:
            self.root.after(0, self._finish, analysis, error)

    def _finish(self, analysis, error):
        self.busy = False
        self.check_btn.configure(state="normal", text="KIỂM TRA")
        if error:
            self.set_result(error, "bad")
            return
        self.status.configure(text=self.mode_text if getattr(self.recognizer, "last_model", None) is None
                              else f"{self.mode_text} · model: {self.recognizer.last_model}")
        message, tag, spoken = analysis.message, self._tag(analysis), analysis.speech
        if self.challenge and not self.challenge.finished:
            task_key = self.challenge.current.key
            self.log.record(self.group_var.get().strip() or "Nhóm 1", task_key, analysis)
            attempt = self.challenge.submit(analysis)
            message = attempt.message
            tag = "ok" if attempt.correct else ("warn" if attempt.kind in ("RECAPTURE", "EMPTY") else "bad")
            spoken = _speech_of(message)
            if attempt.correct:
                message += "\n\n" + self._next_task_text()
            self._refresh_task()
        self.set_result(message, tag)
        self.speak(spoken)
        self._offer_suggestions(analysis)

    @staticmethod
    def _tag(analysis) -> str:
        if analysis.status != "OK":
            return "warn"
        kinds = [r.kind for _, r in analysis.clusters]
        if all(k == "MATCH" for k in kinds):
            return "ok"
        return "bad" if any(k in ("WRONG_BONDS", "UNKNOWN") for k in kinds) else "warn"

    # ------------------------------------------------------------------ gợi ý "Có phải bạn muốn ghép …?"
    def _offer_suggestions(self, analysis):
        self.sugs, self.sug_i = [], 0
        if analysis.status == "OK":
            for _, r in analysis.clusters:
                if r.kind == "SUGGEST":
                    self.sugs = r.suggestions
                    break
        if not self.sugs:
            self.sug_frame.pack_forget()
            return
        self.sug_frame.pack(side="bottom", fill="x", before=self.result)
        self._ask()

    def _ask(self):
        s = self.sugs[self.sug_i]
        self.sug_label.configure(text=f"Có phải bạn muốn ghép {sub_label(s.substance)}?")

    def answer_suggestion(self, yes: bool):
        if not self.sugs:
            return
        s = self.sugs[self.sug_i]
        if yes:
            text = f"{s.substance.name.capitalize()} ({s.substance.formula}). Cấu trúc chuẩn: {describe_structure(s.substance.graph)}."
            if s.missing:
                text += f" Còn thiếu {count_phrase(s.missing)}."
            if s.extra:
                text += f" Đang thừa {count_phrase(s.extra)}."
            self.set_result(text, "ok")
            self.speak(_speech_of(text))
            self.sug_frame.pack_forget()
            return
        self.sug_i += 1
        if self.sug_i >= len(self.sugs):
            self.set_result("Hết gợi ý. Hãy kiểm tra lại cách ghép thẻ.", "warn")
            self.sug_frame.pack_forget()
        else:
            self._ask()

    # ------------------------------------------------------------------ thử thách
    def start_challenge(self):
        self.challenge = Challenge.from_deck(self.deck_var.get())
        self._refresh_task()
        self.set_result("Bắt đầu thử thách. " + self.challenge.prompt(), "info")
        self.speak(_speech_of(self.challenge.prompt()))

    def end_challenge(self):
        if self.challenge:
            self.set_result(self._summary_text(), "info")
        self.challenge = None
        self._refresh_task()

    def _refresh_task(self):
        c = self.challenge
        if c is None:
            self.task_label.configure(text="Chưa bắt đầu. Chọn bộ đề rồi nhấn Bắt đầu.")
            self.hint_btn.configure(state="disabled")
            self.skip_btn.configure(state="disabled")
        elif c.finished:
            self.task_label.configure(text="Đã xong bộ đề. " + self._summary_text())
            self.hint_btn.configure(state="disabled")
            self.skip_btn.configure(state="disabled")
        else:
            self.task_label.configure(text=c.prompt())
            self.hint_btn.configure(state="normal")
            self.skip_btn.configure(state="normal")

    def _next_task_text(self) -> str:
        return self._summary_text() if self.challenge.finished else self.challenge.prompt()

    def _summary_text(self) -> str:
        s = self.challenge.summary()
        text = f"Tổng kết: {s['điểm']}/{s['tối đa']} điểm, đúng {s['đúng']} câu, bỏ qua {s['bỏ qua']}, dùng {s['gợi ý đã dùng']} gợi ý."
        if s["câu khó nhất"]:
            text += f" Câu khó nhất: {s['câu khó nhất']}."
        return text

    def hint(self):
        if self.challenge and not self.challenge.finished:
            text = self.challenge.hint()
            self.set_result(text, "info")
            self.speak(_speech_of(text))

    def skip(self):
        if self.challenge and not self.challenge.finished:
            self.challenge.skip()
            self._refresh_task()
            self.set_result("Đã bỏ qua. " + self._next_task_text(), "info")

    # ------------------------------------------------------------------ báo cáo lớp
    def show_report(self):
        win = tk.Toplevel(self.root)
        win.title("Báo cáo lớp học")
        win.geometry("560x340")
        txt = tk.Text(win, wrap="word", font=(FONT, 11), padx=10, pady=8)
        txt.pack(fill="both", expand=True)
        txt.insert("end", self.log.teacher_report())
        txt.insert("end", f"\n\nNhật ký (mở được bằng Excel): {os.path.abspath(self.log.path)}")
        txt.configure(state="disabled")
        return win


def main(argv=None):
    import argparse
    from .recognizer import GeminiRecognizer, load_api_key
    from .speech import Speaker

    ap = argparse.ArgumentParser(description="CHEM VISION")
    ap.add_argument("--demo", action="store_true", help="chạy thử không cần camera và khóa API")
    ap.add_argument("--camera", type=int, default=0, help="chỉ số camera (mặc định 0)")
    args = ap.parse_args(argv)
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    camera, recognizer, mode, note = None, None, "", ""
    if not args.demo:
        try:
            cam = Camera(args.camera)
            if cam.opened:
                camera = cam
            else:
                note = "Không mở được camera"
        except Exception as err:
            note = f"Không dùng được OpenCV ({err})"
        key = load_api_key(here)
        if camera and key:
            try:
                recognizer, mode = GeminiRecognizer(key), "Gemini + camera"
            except Exception as err:
                note = f"Không khởi tạo được Gemini ({err})"
        elif camera and not key:
            note = "Chưa có khóa API (đặt GEMINI_API_KEY hoặc tệp api_key.txt)"
    if recognizer is None:
        recognizer, camera = DemoRecognizer(), None
        mode = "Chế độ thử (giả lập)" + (f" – {note}" if note else "")

    speaker = Speaker()
    root = tk.Tk()
    App(root, recognizer, camera, speaker if speaker.available else None,
        log_path=os.path.join(here, "nhat_ky_lop_hoc.csv"), mode_text=mode)
    root.mainloop()


if __name__ == "__main__":
    main()
