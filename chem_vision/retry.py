"""Gọi Gemini ổn định: thử lại có kiểm soát và chuyển sang model dự phòng.

Cải tiến so với bản đầu (3 lần x 2 model, chờ 2/4/6 giây sau mỗi lần lỗi):
- chỉ chờ GIỮA các lần thử, không chờ sau lần thử cuối của mỗi model;
- lỗi không tạm thời (400, 401, 403) dừng ngay, không thử lại vô ích;
- tôn trọng Retry-After của máy chủ khi có;
- có ngân sách thời gian tổng để giao diện không treo quá lâu.
"""
from __future__ import annotations

import time

TRANSIENT = {429, 500, 502, 503, 504}
SWITCH_MODEL = {404}              # model không tồn tại: chuyển model, không chờ
FATAL = {400, 401, 403}


class ApiError(Exception):
    def __init__(self, status: int, message: str = "", retry_after: float | None = None):
        super().__init__(f"{status} {message}".strip())
        self.status = status
        self.retry_after = retry_after


class GaveUp(Exception):
    def __init__(self, last: Exception, attempts: int):
        super().__init__(f"Không gọi được AI sau {attempts} lần thử: {last}")
        self.last = last
        self.attempts = attempts


def call_with_retry(fn, models, *, tries=3, waits=(2.0, 4.0, 6.0), budget=15.0,
                    sleep=time.sleep, clock=time.monotonic):
    """Gọi `fn(model)` lần lượt với từng model. Trả về (kết quả, model đã dùng, số lần thử)."""
    start, attempts, last = clock(), 0, None
    for model in models:
        for k in range(tries):
            attempts += 1
            try:
                return fn(model), model, attempts
            except ApiError as err:
                last = err
                if err.status in FATAL:
                    raise GaveUp(err, attempts) from err
                if err.status in SWITCH_MODEL:
                    break
                if err.status not in TRANSIENT:
                    raise GaveUp(err, attempts) from err
                if k == tries - 1:
                    break                      # hết lượt của model này: không chờ nữa
                wait = err.retry_after if err.retry_after is not None else waits[min(k, len(waits) - 1)]
                if clock() - start + wait > budget:
                    raise GaveUp(err, attempts) from err
                sleep(wait)
    raise GaveUp(last or ApiError(0, "không có model nào"), attempts)
