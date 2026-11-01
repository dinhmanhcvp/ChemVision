"""Bảng điều khiển cả lớp: giáo viên tạo lớp lấy mã, các nhóm vào bằng mã, giáo viên thấy nhóm nào xong, nhóm nào kẹt.

Vercel không giữ trạng thái giữa các lần gọi nên dữ liệu lớp lưu ở Upstash Redis (qua giao diện REST, cài từ Vercel
Marketplace). Chưa cấu hình kho lưu trữ thì tính năng tắt và báo rõ; các tính năng khác không bị ảnh hưởng.
Dữ liệu lớp tự xóa sau 24 giờ; chỉ lưu nhãn nhóm và kết quả từng lượt, không lưu ảnh, không lưu tên học sinh.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
from collections import Counter

from .core import BY_KEY
from .features import FIELDS, SessionLog
from .pedagogy import ADVICE, row_tags

TTL = 24 * 3600
MAX_EVENTS = 2000
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"        # bỏ các kí tự dễ nhầm: I, O, 0, 1
OUTCOMES = {"ĐÚNG", "ĐÚNG CHẤT KHÁC", "SAI LIÊN KẾT", "GHÉP DỞ", "KHÔNG NHẬN RA"}
STUCK_AFTER = 3                                           # sai từ ngần này lần liền trên cùng một câu thì coi là kẹt
RATE = {"create": (5, 60.0), "join": (30, 60.0), "submit": (90, 60.0), "activity": (150, 60.0), "state": (60, 60.0)}
ACTIVITY = {"start": "bắt đầu bộ đề", "skip": "bỏ qua câu", "hint": "xin gợi ý", "end": "kết thúc bộ đề",
            "suggest": "trả lời gợi ý"}
IDLE_AFTER = 120                                          # giây không có hoạt động thì coi là nhóm đang rảnh


# --------------------------------------------------------------------------- kho lưu trữ
class MemoryStore:
    """Kho trong bộ nhớ: dùng cho máy chủ thử và kiểm thử (trên Vercel mỗi lần gọi có thể chạy ở một phiên bản khác)."""

    def __init__(self, clock=time.time):
        self.clock, self.data = clock, {}
        self._lock = threading.Lock()                          # máy chủ thử chạy nhiều luồng; RPUSH của Upstash vốn nguyên tử

    def _live(self, key):
        item = self.data.get(key)
        if item and item[1] > self.clock():
            return item
        self.data.pop(key, None)
        return None

    def set(self, key, value, ttl):
        self.data[key] = (value, self.clock() + ttl)

    def get(self, key):
        item = self._live(key)
        return item[0] if item else None

    def rpush(self, key, value, ttl, cap):
        with self._lock:
            item = self._live(key)
            items = list(item[0]) if item else []
            items.append(value)
            self.data[key] = (items[-cap:], self.clock() + ttl)

    def lrange(self, key):
        item = self._live(key)
        return list(item[0]) if item else []

    def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)


class UpstashStore:
    """Upstash Redis qua REST: mỗi lệnh là một yêu cầu POST chứa mảng lệnh."""

    def __init__(self, url: str, token: str, opener=None, timeout: float = 8.0):
        self.url, self.token, self.timeout = url.rstrip("/"), token, timeout
        self.opener = opener or urllib.request.urlopen

    def _cmd(self, *args):
        req = urllib.request.Request(self.url, data=json.dumps(list(args)).encode("utf-8"), method="POST",
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with self.opener(req, timeout=self.timeout) as resp:
                body = json.load(resp)
        except (urllib.error.URLError, OSError, ValueError) as err:
            raise StoreError("Không kết nối được kho lưu trữ lớp học.") from err
        if "error" in body:
            raise StoreError("Kho lưu trữ lớp học báo lỗi.")
        return body.get("result")

    def set(self, key, value, ttl):
        self._cmd("SET", key, json.dumps(value, ensure_ascii=False), "EX", ttl)

    def get(self, key):
        raw = self._cmd("GET", key)
        return json.loads(raw) if raw else None

    def rpush(self, key, value, ttl, cap):
        self._cmd("RPUSH", key, json.dumps(value, ensure_ascii=False))
        self._cmd("LTRIM", key, -cap, -1)
        self._cmd("EXPIRE", key, ttl)

    def lrange(self, key):
        return [json.loads(x) for x in (self._cmd("LRANGE", key, 0, -1) or [])]

    def delete(self, *keys):
        self._cmd("DEL", *keys)


class StoreError(Exception):
    pass


_memory = MemoryStore()


def get_store(env):
    """Chọn kho theo biến môi trường; None nếu chưa cấu hình (tính năng tắt)."""
    for url_key, token_key in (("UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"), ("KV_REST_API_URL", "KV_REST_API_TOKEN")):
        if env.get(url_key) and env.get(token_key):
            return UpstashStore(env[url_key], env[token_key])
    if env.get("CLASSROOM_MEMORY") == "1":
        return _memory
    return None


# --------------------------------------------------------------------------- tiện ích
def _hash(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _clean_group(name) -> str:
    text = re.sub(r"[\x00-\x1f\x7f<>&\"']", "", str(name or "")).strip()
    return text[:30] or "Nhóm"


def _norm_code(code) -> str | None:
    text = str(code or "").strip().upper()
    return text if re.fullmatch(f"[{CODE_ALPHABET}]{{6}}", text) else None


def _new_code(store) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if store.get(f"cls:{code}") is None:
            return code
    raise StoreError("Không tạo được mã lớp, hãy thử lại.")


def summarize(events: list[dict], now: float, acts: list[dict] | None = None) -> dict:
    acts = acts or []
    groups: dict[str, dict] = {}

    def group(name):
        return groups.setdefault(name, {"attempts": 0, "solved": set(), "fails": Counter(), "last": None, "streak": Counter(),
                                        "t": 0.0, "deck": "", "progress": "", "skips": 0, "hints": 0, "ended": False,
                                        "yes": 0, "no": 0})
    per_target: dict[str, Counter] = {}
    for e in events:
        g = group(e["nhóm"])
        t = e["chất mục tiêu"]
        g["attempts"] += 1
        g["t"] = max(g["t"], float(e.get("t", 0)))
        pt = per_target.setdefault(t, Counter())
        pt["attempts"] += 1
        if e["kết quả"] == "ĐÚNG":
            g["solved"].add(t)
            g["streak"][t] = 0
        else:
            g["fails"][t] += 1
            g["streak"][t] += 1
            pt["wrong"] += 1
        g["last"] = e
    for a in acts:
        g = group(a["nhóm"])
        g["t"] = max(g["t"], float(a.get("t", 0)))
        kind = a.get("loại")
        if kind == "start":
            g.update(deck=a.get("bộ đề", ""), progress=a.get("tiến độ", ""), ended=False, skips=0, hints=0)
        elif kind == "skip":
            g["skips"] += 1
            g["progress"] = a.get("tiến độ", g["progress"])
        elif kind == "hint":
            g["hints"] += 1
        elif kind == "end":
            g["ended"] = True
            g["progress"] = a.get("tiến độ", g["progress"])
        elif kind == "suggest":
            g["yes" if a.get("đúng") else "no"] += 1
    rows = []
    for name, g in groups.items():
        last = g["last"]
        t = last["chất mục tiêu"] if last else ""
        stuck = bool(last) and t not in g["solved"] and g["streak"][t] >= STUCK_AFTER
        idle = int(now - g["t"]) if g["t"] else 0
        rows.append({
            "nhóm": name, "lượt": g["attempts"], "đã xong": len(g["solved"]),
            "câu gần nhất": t, "công thức": BY_KEY[t].formula if last else "",
            "kết quả gần nhất": last["kết quả"] if last else "",
            "kẹt": stuck, "giây trước": max(0, idle), "bộ đề": g["deck"], "tiến độ": g["progress"],
            "bỏ qua": g["skips"], "gợi ý": g["hints"], "đã kết thúc": g["ended"],
            "rảnh": (not g["ended"]) and idle >= IDLE_AFTER,
        })
    rows.sort(key=lambda r: (not r["kẹt"], not r["rảnh"], r["nhóm"]))
    targets = [{"chất": t, "công thức": BY_KEY[t].formula, "tên": BY_KEY[t].name, "lượt": c["attempts"], "sai": c["wrong"],
                "tỉ lệ sai": round(c["wrong"] / c["attempts"], 2)} for t, c in per_target.items()]
    targets.sort(key=lambda x: (-x["tỉ lệ sai"], -x["lượt"]))
    tags = Counter(tag for e in events for tag in row_tags(e))
    yes = sum(g["yes"] for g in groups.values())
    no = sum(g["no"] for g in groups.values())
    return {
        "nhóm": rows, "câu khó": targets[:5], "tổng lượt": len(events),
        "quan niệm sai": [{"mã": code, "nhãn": ADVICE[code][0], "lượt": n, "cách xử lý": ADVICE[code][1]}
                          for code, n in tags.most_common(4)],
        "nhóm kẹt": [r["nhóm"] for r in rows if r["kẹt"]],
        "nhóm rảnh": [r["nhóm"] for r in rows if r["rảnh"]],
        "gợi ý chất": {"đúng": yes, "không phải": no},
    }


# --------------------------------------------------------------------------- điểm vào
def _err(status, message):
    return status, {"ok": False, "error": message}


def handle(payload: dict, env, headers, store=None, now: float | None = None, limiter=None) -> tuple[int, dict]:
    store = store or get_store(env)
    if store is None:
        return _err(503, "Tính năng lớp học trực tuyến chưa được bật: máy chủ chưa kết nối kho lưu trữ (Upstash Redis).")
    action = payload.get("action")
    if action not in RATE:
        if action != "end":
            return _err(400, "Thao tác không hợp lệ.")
    now = time.time() if now is None else now
    if limiter is not None and action in RATE and limiter(action, headers):
        return _err(429, "Thao tác quá nhanh, hãy đợi một lát.")
    try:
        if action == "create":
            code = _new_code(store)
            key = secrets.token_hex(12)
            name = _clean_group(payload.get("name") or "Lớp học")
            store.set(f"cls:{code}", {"name": name, "key": _hash(key), "created": now}, TTL)
            return 200, {"ok": True, "code": code, "teacher_key": key, "name": name, "ttl_hours": TTL // 3600}
        code = _norm_code(payload.get("code"))
        info = store.get(f"cls:{code}") if code else None
        if info is None:
            return _err(404, "Không tìm thấy lớp với mã này (mã sai hoặc lớp đã hết hạn).")
        if action == "join":                                   # chỉ xác nhận mã lớp, không ghi dữ liệu
            return 200, {"ok": True, "name": info["name"]}
        if action == "activity":                               # nút Bắt đầu, Bỏ qua, Gợi ý, Kết thúc, Đúng/Không phải
            typ = payload.get("type")
            if typ not in ACTIVITY:
                return _err(400, "Loại hoạt động không hợp lệ.")
            event = {"nhóm": _clean_group(payload.get("group")), "loại": typ, "t": now,
                     "bộ đề": str(payload.get("deck") or "")[:60], "tiến độ": str(payload.get("progress") or "")[:12]}
            if typ == "suggest":
                event["đúng"] = bool(payload.get("accepted"))
            store.rpush(f"act:{code}", event, TTL, MAX_EVENTS)
            return 200, {"ok": True}
        if action == "submit":
            row = payload.get("row")
            if not isinstance(row, dict) or row.get("chất mục tiêu") not in BY_KEY or row.get("kết quả") not in OUTCOMES:
                return _err(400, "Dữ liệu lượt kiểm tra không hợp lệ.")
            event = {k: str(row.get(k, ""))[:200] for k in FIELDS}
            event["nhóm"] = _clean_group(row.get("nhóm"))
            event["t"] = now
            store.rpush(f"evt:{code}", event, TTL, MAX_EVENTS)
            return 200, {"ok": True}
        # state và end cần khóa của giáo viên
        key = str(payload.get("teacher_key") or "")
        if not hmac.compare_digest(_hash(key), info["key"]):
            return _err(403, "Khóa giáo viên không đúng.")
        if action == "end":
            store.delete(f"cls:{code}", f"evt:{code}", f"act:{code}")
            return 200, {"ok": True}
        events = store.lrange(f"evt:{code}")
        out = {"ok": True, "name": info["name"], "code": code, **summarize(events, now, store.lrange(f"act:{code}"))}
        out["report"] = SessionLog(rows=events).teacher_report()
        return 200, out
    except StoreError as err:
        return _err(503, str(err))
