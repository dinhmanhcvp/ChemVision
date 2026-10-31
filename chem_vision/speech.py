"""Đọc kết quả bằng giọng nói tiếng Việt: gTTS tạo MP3, pygame phát.

Tệp âm thanh đặt tên theo nội dung câu (xem core.speech_cache_name): câu lặp lại dùng lại
tệp cũ, không gọi mạng lần nữa và không ghi đè tệp đang phát (tránh lỗi Permission denied).
"""
from __future__ import annotations

import os
import tempfile
import threading

from .core import speech_cache_name


class Speaker:
    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "chem_vision_tts")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.error: str | None = None
        self._mixer = None

    @property
    def available(self) -> bool:
        try:
            import gtts, pygame  # noqa: F401
            return True
        except ImportError as err:
            self.error = f"thiếu thư viện: {err.name}"
            return False

    def _file(self, text: str) -> str:
        path = os.path.join(self.cache_dir, speech_cache_name(text))
        if not os.path.exists(path):
            from gtts import gTTS
            tmp = path + ".part"
            gTTS(text=text, lang="vi").save(tmp)
            os.replace(tmp, path)
        return path

    def say(self, text: str, block: bool = False) -> None:
        """Phát trong luồng riêng để không làm đứng giao diện."""
        if not text:
            return
        t = threading.Thread(target=self._play, args=(text,), daemon=True)
        t.start()
        if block:
            t.join()

    def _play(self, text: str) -> None:
        with self.lock:
            try:
                path = self._file(text)
                import pygame
                if self._mixer is None:
                    pygame.mixer.init()
                    self._mixer = pygame.mixer
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.wait(80)
                self.error = None
            except Exception as err:             # mất mạng, thiếu thư viện, không có loa
                self.error = str(err)[:120]
