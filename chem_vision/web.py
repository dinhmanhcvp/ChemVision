"""Lớp xử lý cho bản web (Vercel): các hàm thuần nhận dữ liệu JSON và trả về (mã HTTP, JSON).

Bản web không có trạng thái trên máy chủ: điểm thử thách và nhật ký lớp học nằm ở trình duyệt, máy chủ chỉ
nhận diện ảnh, đối sánh, tạo gợi ý và dựng báo cáo.
"""
from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import re
import time
from collections import Counter, defaultdict, deque

from .core import (BY_KEY, DATABASE, ELEMENT_NAMES, Analysis, analyze, describe_structure, extract_json)
from .features import (BASE_SCORE, DECKS, HINT_PENALTY, MAX_HINTS, MIN_SOLVED, WRONG_PENALTY, Challenge,
                       SessionLog, hint_for)
from .recognizer import MODELS, SCENARIOS, GeminiRest
from .retry import GaveUp

MAX_IMAGE_BYTES = 3 * 1024 * 1024          # ảnh JPEG sau khi giải mã base64 (giới hạn thân yêu cầu của Vercel là 4,5 MB)
MAX_BODY_BYTES = 4 * 1024 * 1024
RATE_LIMIT = (20, 60.0)                    # tối đa 20 lượt nhận diện mỗi 60 giây cho mỗi địa chỉ (tính trong một phiên bản máy chủ)
_hits: dict[str, deque] = defaultdict(deque)


# --------------------------------------------------------------------------- tiện ích
def _err(status: int, message: str, **extra):
    return status, {"ok": False, "error": message, **extra}


def client_ip(headers) -> str:
    fwd = headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or ""
    return fwd.split(",")[0].strip() or headers.get("x-real-ip") or "local"


def rate_limited(ip: str, now: float | None = None, limit=RATE_LIMIT) -> bool:
    now = time.monotonic() if now is None else now
    q = _hits[ip]
    while q and now - q[0] > limit[1]:
        q.popleft()
    if len(q) >= limit[0]:
        return True
    q.append(now)
    return False


def access_ok(env, headers, payload) -> tuple[bool, str]:
    """Nhận diện bằng AI tốn hạn mức API nên yêu cầu mã truy cập (biến môi trường ACCESS_CODE)."""
    expected = (env.get("ACCESS_CODE") or "").strip()
    if not expected:
        return False, "Máy chủ chưa đặt ACCESS_CODE nên chưa nhận ảnh. Đặt biến môi trường ACCESS_CODE trên Vercel."
    given = (headers.get("x-access-code") or headers.get("X-Access-Code") or payload.get("code") or "").strip()
    if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        return False, "Mã truy cập không đúng."
    return True, ""


def decode_image(data: str) -> bytes | None:
    if not isinstance(data, str):
        return None
    data = re.sub(r"^data:image/[a-zA-Z+.-]+;base64,", "", data.strip())
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return None
    return raw if raw[:2] == b"\xff\xd8" else None          # chỉ nhận JPEG


def _counter(c: Counter) -> dict:
    return {k: int(v) for k, v in c.items()}


def analysis_to_dict(a: Analysis, data: dict | None = None, model: str | None = None) -> dict:
    clusters = []
    for ids, r in a.clusters:
        item = {"kind": r.kind, "cards": [str(i) for i in ids]}
        if r.substance is not None:
            item["substance"] = {"key": r.substance.key, "name": r.substance.name, "formula": r.substance.formula}
        if r.same_composition:
            item["same_composition"] = [{"key": s.key, "name": s.name, "formula": s.formula} for s in r.same_composition]
        if r.kind == "SUGGEST":
            item["suggestions"] = [{
                "key": s.substance.key, "name": s.substance.name, "formula": s.substance.formula,
                "missing": _counter(s.missing), "extra": _counter(s.extra),
                "structure": describe_structure(s.substance.graph)} for s in r.suggestions]
        if r.kind == "WRONG_BONDS":
            item["extra_bonds"] = [f"{a}-{b}" for (a, b), n in sorted(r.extra_bonds.items()) for _ in range(n)]
            item["missing_bonds"] = [f"{a}-{b}" for (a, b), n in sorted(r.missing_bonds.items()) for _ in range(n)]
        if r.valence_warnings:
            item["warnings"] = r.valence_warnings
        clusters.append(item)
    out = {"ok": True, "status": a.status, "message": a.message, "speech": a.speech, "clusters": clusters}
    if data:
        out["cards"] = [{k: c.get(k) for k in ("id", "symbol", "confidence", "box_2d")}
                        for c in data.get("cards", []) if isinstance(c, dict)]
        out["connections"] = data.get("connections", [])
        out["links_source"] = data.get("links_source", "ai")
    if model:
        out["model"] = model
    return out


# --------------------------------------------------------------------------- các điểm vào
def handle_meta() -> tuple[int, dict]:
    return 200, {
        "ok": True,
        "decks": {name: [{"key": k, "name": BY_KEY[k].name, "formula": BY_KEY[k].formula} for k in keys]
                  for name, keys in DECKS.items()},
        "scenarios": list(SCENARIOS),
        "scoring": {"base": BASE_SCORE, "wrong": WRONG_PENALTY, "hint": HINT_PENALTY, "min": MIN_SOLVED,
                    "max_hints": MAX_HINTS},
        "substances": len(DATABASE),
        "models": list(MODELS),
        "elements": ELEMENT_NAMES,
    }


def _attempt(analysis: Analysis, target: str) -> dict:
    att = Challenge([target]).submit(analysis)
    return {"target": target, "correct": att.correct, "kind": att.kind, "message": att.message}


def handle_analyze(payload: dict, env, headers, recognizer=None, now: float | None = None) -> tuple[int, dict]:
    """Nhận ảnh JPEG (base64) hoặc tên tình huống giả lập; trả về kết quả nhận diện và đối sánh."""
    target = payload.get("target")
    if target is not None and target not in BY_KEY:
        return _err(400, "Chất mục tiêu không có trong cơ sở dữ liệu.")
    demo = payload.get("demo")
    if demo is not None:                                  # chạy thử: không gọi AI, không tốn hạn mức
        if demo not in SCENARIOS:
            return _err(400, "Tình huống giả lập không tồn tại.")
        raw = SCENARIOS[demo]
        a = analyze(raw)
        out = analysis_to_dict(a, extract_json(raw), "giả lập")
        if target:
            out["attempt"] = _attempt(a, target)
        return 200, out

    ok, why = access_ok(env, headers, payload)
    if not ok:
        return _err(401 if "ACCESS_CODE nên" not in why else 503, why)
    if rate_limited(client_ip(headers), now):
        return _err(429, "Bạn gửi quá nhanh. Hãy đợi một lát rồi thử lại.")
    jpeg = decode_image(payload.get("image"))
    if jpeg is None:
        return _err(400, "Ảnh không hợp lệ: cần ảnh JPEG mã hóa base64.")
    if len(jpeg) > MAX_IMAGE_BYTES:
        return _err(413, "Ảnh quá lớn (tối đa 3 MB). Hãy giảm kích thước ảnh.")
    if recognizer is None:
        key = (env.get("GEMINI_API_KEY") or "").strip()
        if not key:
            return _err(503, "Máy chủ chưa có GEMINI_API_KEY.")
        recognizer = GeminiRest(key)
    import cv2
    import numpy as np
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return _err(400, "Không giải mã được ảnh.")
    try:
        raw = recognizer.recognize_jpeg(jpeg, frame)
    except GaveUp as err:
        status = getattr(err.last, "status", 0)
        return _err(502, "Không kết nối được dịch vụ AI. Kiểm tra khóa API và thử lại.",
                    upstream=status)
    a = analyze(raw)
    out = analysis_to_dict(a, extract_json(raw), getattr(recognizer, "last_model", None))
    if target:
        out["attempt"] = _attempt(a, target)
    return 200, out


def handle_hint(payload: dict) -> tuple[int, dict]:
    key, level = payload.get("target"), payload.get("level", 1)
    if key not in BY_KEY:
        return _err(400, "Chất mục tiêu không có trong cơ sở dữ liệu.")
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= MAX_HINTS:
        return _err(400, f"Mức gợi ý phải từ 1 đến {MAX_HINTS}.")
    return 200, {"ok": True, "level": level, "hint": hint_for(key, level)}


def handle_report(payload: dict) -> tuple[int, dict]:
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) > 5000 or not all(isinstance(r, dict) for r in rows):
        return _err(400, "Nhật ký không hợp lệ (cần danh sách tối đa 5000 dòng).")
    clean = [{k: str(r.get(k, ""))[:200] for k in ("thời gian", "nhóm", "chất mục tiêu", "kết quả", "thẻ thiếu", "thẻ thừa", "liên kết sai")}
             for r in rows if r.get("chất mục tiêu") in BY_KEY]
    log = SessionLog(rows=clean)
    return 200, {"ok": True, "report": log.teacher_report(), "csv": log.to_csv(), "rows": len(clean)}


ROUTES = {"meta": ("GET", lambda p, env, h: handle_meta()),
          "analyze": ("POST", lambda p, env, h: handle_analyze(p, env, h)),
          "hint": ("POST", lambda p, env, h: handle_hint(p)),
          "report": ("POST", lambda p, env, h: handle_report(p))}


def serve(handler, route: str) -> None:
    """Dùng cho BaseHTTPRequestHandler (hàm serverless của Vercel và máy chủ thử cục bộ)."""
    method, fn = ROUTES[route]

    def send(status: int, body: dict):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(raw)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(raw)

    if handler.command != method:
        return send(405, {"ok": False, "error": f"Chỉ hỗ trợ {method}."})
    payload = {}
    if method == "POST":
        try:
            length = int(handler.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY_BYTES:
            return send(413 if length > MAX_BODY_BYTES else 400, {"ok": False, "error": "Thân yêu cầu trống hoặc quá lớn."})
        try:
            payload = json.loads(handler.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return send(400, {"ok": False, "error": "Thân yêu cầu không phải JSON."})
        if not isinstance(payload, dict):
            return send(400, {"ok": False, "error": "Thân yêu cầu phải là một đối tượng JSON."})
    try:
        status, body = fn(payload, os.environ, handler.headers)
    except Exception:                                   # không để lộ chi tiết nội bộ ra ngoài
        status, body = 500, {"ok": False, "error": "Lỗi máy chủ."}
    send(status, body)
