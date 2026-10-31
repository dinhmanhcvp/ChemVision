"""Nhận diện thẻ từ một khung hình: Gemini thật hoặc bộ giả lập để chạy thử không cần camera/mạng.

AI chỉ "nhìn": trả JSON gồm danh sách thẻ và các cặp thẻ chạm cạnh. Prompt không chứa
công thức hóa học nào, để AI không bị gợi ý đáp án.
"""
from __future__ import annotations

import io
import json
import os

from .geometry import apply_geometry
from .retry import ApiError, call_with_retry

# Model chính nhanh (3-4 s/ảnh khi thử), model dự phòng chậm hơn nhưng đã thử chạy tốt.
# Đã loại gemini-2.5-flash-lite (báo 404, không còn dùng được) và gemini-flash-latest (55-180 s/ảnh).
MODELS = ("gemini-flash-lite-latest", "gemini-2.5-flash")
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


class GeminiRecognizer:
    def __init__(self, api_key: str, models=MODELS, client=None, sleep=None, link_mode: str = "geometry"):
        if client is None:
            from google import genai
            client = genai.Client(api_key=api_key)
        self.client, self.models, self.sleep, self.link_mode = client, models, sleep, link_mode
        self.last_model = None
        self.last_data = None

    def _call(self, jpeg: bytes, model: str) -> str:
        from google.genai import types
        try:
            resp = self.client.models.generate_content(
                model=model,
                contents=[types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"), create_prompt()],
                config=_config(types),
            )
        except Exception as err:                      # chuyển mọi lỗi SDK về ApiError
            code = getattr(err, "code", None) or getattr(err, "status_code", None)
            if not isinstance(code, int):
                code = 503                            # lỗi mạng, hết giờ: coi là tạm thời
            raise ApiError(code, str(err)[:200], _retry_after(err)) from err
        text = getattr(resp, "text", None)
        if not text:
            raise ApiError(503, "AI không trả nội dung")
        return text

    def recognize(self, frame_bgr) -> str:
        jpeg = frame_to_jpeg(frame_bgr)
        kw = {"sleep": self.sleep} if self.sleep else {}
        text, model, _ = call_with_retry(lambda m: self._call(jpeg, m), self.models, **kw)
        self.last_model = model
        if self.link_mode != "geometry":
            return text
        from .core import extract_json
        data = extract_json(text)
        if data is None:
            return text
        self.last_data = apply_geometry(frame_bgr, data)      # liên kết do hình học quyết định
        return json.dumps(self.last_data, ensure_ascii=False)


def _config(types):
    kw = {"temperature": TEMPERATURE, "response_mime_type": "application/json"}
    supported = hasattr(types, "ThinkingConfig") and "thinking_config" in types.GenerateContentConfig.model_fields
    if THINKING_BUDGET is not None and supported:      # thư viện google-genai cũ (< 1.0) chưa có tùy chọn này
        kw["thinking_config"] = types.ThinkingConfig(thinking_budget=THINKING_BUDGET)
    return types.GenerateContentConfig(**kw)


def _retry_after(err):
    try:
        headers = getattr(getattr(err, "response", None), "headers", None) or {}
        value = headers.get("retry-after") or headers.get("Retry-After")
        return float(value) if value else None
    except (TypeError, ValueError):
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
