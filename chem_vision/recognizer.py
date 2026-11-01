"""Nhận diện thẻ từ một khung hình: Gemini thật hoặc bộ giả lập để chạy thử không cần camera/mạng.

AI chỉ "nhìn": trả JSON gồm danh sách thẻ và các cặp thẻ chạm cạnh. Prompt không chứa
công thức hóa học nào, để AI không bị gợi ý đáp án.
"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request

from .geometry import apply_geometry
from .markers import cards_from_markers
from .quality import assess
from .retry import ApiError, call_with_retry

# Khi thử: gemini-2.5-flash với thinkingBudget=0 mất khoảng 2,5 s/ảnh (mặc định 9-40 s); gemini-flash-lite-latest
# nhanh (3-4 s) nhưng từ chối thinkingBudget. Đã loại gemini-2.5-flash-lite (404, không còn dùng được)
# và gemini-flash-latest (55-180 s/ảnh).
MODELS = ("gemini-2.5-flash", "gemini-flash-lite-latest")
TEMPERATURE = 0.1
THINKING_BUDGET = 0      # 0: tắt suy luận mở rộng của model 2.5 để nhanh hơn; None: để mặc định


def create_prompt() -> str:
    return (
        "Ảnh chụp từ phía trên một bàn có các thẻ nguyên tố hóa học, mỗi thẻ ghi một kí hiệu nguyên tố lớn.\n"
        "Quy ước: mỗi thẻ là một nguyên tử; hai thẻ chạm cạnh nhau là có liên kết.\n"
        "Nhiệm vụ của bạn chỉ là QUAN SÁT, không suy luận hóa học:\n"
        "1. Liệt kê mọi thẻ có kí hiệu đọc được, mỗi thẻ gồm: id (số nguyên bắt đầu từ 1), symbol (kí hiệu nguyên tố, "
        "đúng chữ hoa và chữ thường), confidence (từ 0 đến 1) và box_2d là khung bao của cả tấm thẻ dạng "
        "[ymin, xmin, ymax, xmax] trên thang 0 đến 1000. Bỏ qua mặt sau trống và thẻ bị che đến mức không đọc được kí hiệu.\n"
        "2. Liệt kê các cặp thẻ chạm cạnh nhau (connections). Chỉ ghi cặp mà hai cạnh thẻ thật sự sát nhau hoặc chồng lên nhau; "
        "hai thẻ chỉ ở gần nhau, có khe hở nhìn thấy mặt bàn, thì KHÔNG phải là chạm. Nếu không chắc, đừng ghi cặp đó.\n"
        "Không đoán tên chất, không tự thêm hoặc bớt thẻ. Chú ý không nhầm C với Ca, O với Os, N với Na. "
        "Nếu không chắc về một thẻ, hãy đặt confidence thấp. Nếu không thấy thẻ nào, trả về danh sách rỗng.\n"
        'Chỉ trả về JSON đúng dạng: {"cards": [{"id": 1, "symbol": "X", "confidence": 0.9, "box_2d": [100, 100, 300, 300]}], '
        '"connections": [{"a": 1, "b": 2}]}'
    )


def frame_to_jpeg(frame_bgr) -> bytes:
    """BGR (OpenCV) -> RGB -> JPEG trong bộ nhớ; không ghi ảnh ra đĩa."""
    from PIL import Image
    rgb = frame_bgr[:, :, ::-1]
    buf = io.BytesIO()
    Image.fromarray(rgb).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _read_env_file(path: str) -> dict:
    """Đọc tệp .env dạng TÊN=giá_trị (bỏ dòng trống, dòng chú thích # và dấu nháy)."""
    values = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip().strip("\"'")
    return values


def load_api_key(*folders: str) -> str | None:
    """Thứ tự tìm: biến môi trường, rồi trong từng thư mục (.env, sau đó api_key.txt)."""
    key = os.environ.get("GEMINI_API_KEY")
    if key and key.strip():
        return key.strip()
    for folder in folders:
        env_path = os.path.join(folder, ".env")
        if os.path.exists(env_path):
            key = _read_env_file(env_path).get("GEMINI_API_KEY")
            if key:
                return key
        path = os.path.join(folder, "api_key.txt")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                key = f.read().strip()
            if key:
                return key
    return None


# --------------------------------------------------------------------------- giả lập
def _mol(atoms: str, edges):
    syms = atoms.split()
    return json.dumps({"cards": [{"id": i + 1, "symbol": s, "confidence": 0.95} for i, s in enumerate(syms)],
                       "connections": [{"a": a, "b": b} for a, b in edges]})


SCENARIOS = {
    "Nước, ghép đúng": _mol("H O H", [(1, 2), (2, 3)]),
    "Nước, sai liên kết": _mol("H H O", [(1, 2), (2, 3)]),
    "Ghép dở (H–O)": _mol("H O", [(1, 2)]),
    "Thừa một thẻ N": _mol("H O H N", [(1, 2), (2, 3), (2, 4)]),
    "CO2, ghép đúng": _mol("O C O", [(1, 2), (2, 3)]),
    "Đimetyl ete": _mol("C C O H H H H H H", [(1, 3), (2, 3), (1, 4), (1, 5), (1, 6), (2, 7), (2, 8), (2, 9)]),
    "Hai cụm rời nhau": _mol("H O H Cl", [(1, 2), (2, 3)]),
    "Ảnh chưa rõ": json.dumps({"cards": [{"id": 1, "symbol": "C", "confidence": 0.45}, {"id": 2, "symbol": "O", "confidence": 0.9}],
                               "connections": [{"a": 1, "b": 2}]}),
    "Không có thẻ": json.dumps({"cards": [], "connections": []}),
}


class DemoRecognizer:
    """Trả kết quả dựng sẵn, dùng khi không có camera hoặc khóa API."""

    def __init__(self, scenario: str = "Nước, ghép đúng"):
        self.scenario = scenario

    def recognize(self, frame_bgr=None) -> str:
        return SCENARIOS[self.scenario]


# --------------------------------------------------------------------------- bản web
class GeminiRest:
    """Gọi Gemini bằng HTTP trực tiếp, không cần thư viện google-genai (dùng cho bản web trên Vercel)."""

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, models=MODELS, timeout: float = 25.0, sleep=None, opener=None,
                 link_mode: str = "geometry", use_markers: bool = True, check_quality: bool = True):
        self.api_key, self.models, self.timeout, self.sleep, self.link_mode = api_key, models, timeout, sleep, link_mode
        self.use_markers, self.check_quality = use_markers, check_quality
        self.opener = opener or urllib.request.urlopen
        self.no_thinking: set[str] = set()      # model từ chối thinkingBudget (ví dụ gemini-flash-lite-latest)
        self.last_model = None
        self.last_data = None

    def _body(self, jpeg: bytes, thinking: bool) -> dict:
        cfg = {"temperature": TEMPERATURE, "responseMimeType": "application/json"}
        if thinking:
            cfg["thinkingConfig"] = {"thinkingBudget": THINKING_BUDGET}
        part = {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")}}
        return {"contents": [{"parts": [part, {"text": create_prompt()}]}], "generationConfig": cfg}

    def _call(self, jpeg: bytes, model: str) -> str:
        thinking = THINKING_BUDGET is not None and model not in self.no_thinking
        req = urllib.request.Request(
            self.URL.format(model=model), data=json.dumps(self._body(jpeg, thinking)).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key})
        try:
            with self.opener(req, timeout=self.timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")
            if err.code == 400 and thinking:          # nhiều model chỉ báo INVALID_ARGUMENT chung chung
                self.no_thinking.add(model)           # nhớ model này không nhận thinkingBudget, thử lại không có
                return self._call(jpeg, model)
            raise ApiError(err.code, detail[:200], _header_retry_after(err.headers)) from err
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as err:
            raise ApiError(503, str(err)[:200]) from err
        try:
            parts = payload["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError):
            text = ""
        if not text.strip():
            raise ApiError(503, "AI không trả nội dung")
        return text

    def recognize(self, frame_bgr) -> str:
        """Dùng cho ứng dụng máy tính: nhận khung hình OpenCV (BGR)."""
        return self.recognize_jpeg(frame_to_jpeg(frame_bgr), frame_bgr)

    def recognize_jpeg(self, jpeg: bytes, frame_bgr=None) -> str:
        quality = None
        if frame_bgr is not None:
            if self.use_markers:                      # thẻ có mã đánh dấu: đọc ngay trên máy, không gọi AI
                data = cards_from_markers(frame_bgr)
                if data:
                    self.last_model, self.last_data = "mã đánh dấu (ngoại tuyến)", data
                    return json.dumps(data, ensure_ascii=False)
            if self.check_quality:
                quality = assess(frame_bgr)
                if quality["blocking"]:               # ảnh hỏng nặng: không tốn một lượt gọi AI
                    self.last_model = None
                    self.last_data = {"cards": [], "connections": [], "quality": quality,
                                      "quality_problems": quality["blocking"]}
                    return json.dumps(self.last_data, ensure_ascii=False)
        kw = {"sleep": self.sleep} if self.sleep else {}
        text, model, _ = call_with_retry(lambda m: self._call(jpeg, m), self.models, **kw)
        self.last_model = model
        if frame_bgr is None or self.link_mode != "geometry":
            return text
        from .core import extract_json
        data = extract_json(text)
        if data is None:
            return text
        self.last_data = apply_geometry(frame_bgr, data)
        if quality:
            self.last_data["quality"] = quality
        return json.dumps(self.last_data, ensure_ascii=False)


def _header_retry_after(headers):
    try:
        value = headers.get("Retry-After") if headers else None
        return float(value) if value else None
    except (TypeError, ValueError):
        return None


class MarkerRecognizer:
    """Chỉ đọc mã đánh dấu in trên thẻ: chạy ngoại tuyến, không cần khóa API. Thẻ không có mã sẽ không được nhận ra."""

    last_model = "mã đánh dấu (ngoại tuyến)"

    def __init__(self):
        self.last_data = None

    def recognize(self, frame_bgr) -> str:
        data = cards_from_markers(frame_bgr) or {"cards": [], "connections": [], "links_source": "markers"}
        self.last_data = data
        return json.dumps(data, ensure_ascii=False)
