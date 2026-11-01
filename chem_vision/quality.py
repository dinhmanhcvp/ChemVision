"""Kiểm tra chất lượng ảnh trước khi nhận diện: quá tối, quá sáng, mờ, lóa, thiếu tương phản.

Ảnh hỏng nặng bị chặn trước khi gọi AI (tiết kiệm hạn mức, học sinh chụp lại ngay); ảnh hơi kém chỉ kèm lời nhắc.
Ngưỡng chọn theo ảnh thật thử nghiệm: ảnh tốt có độ nét 1700 đến 4700, ảnh làm mờ nặng còn dưới 3.
"""
from __future__ import annotations

# (ngưỡng nhắc nhở, ngưỡng chặn)
DARK = (70.0, 40.0)           # độ sáng trung bình (0-255): dưới ngưỡng là tối
BRIGHT = (210.0, 235.0)       # trên ngưỡng là sáng gắt
BLUR = (150.0, 20.0)          # phương sai Laplacian trên ảnh 640 px: dưới ngưỡng là mờ
GLARE = (0.10, 0.40)          # tỉ lệ điểm trắng cháy
CONTRAST = (22.0, 10.0)       # độ lệch chuẩn độ sáng


def assess(frame_bgr) -> dict:
    import cv2
    h, w = frame_bgr.shape[:2]
    scale = 640 / max(w, h)
    small = cv2.resize(frame_bgr, (max(int(w * scale), 1), max(int(h * scale), 1))) if scale < 1 else frame_bgr
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = {
        "brightness": round(float(gray.mean()), 1),
        "sharpness": round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
        "glare": round(float(((hsv[..., 2] >= 250) & (hsv[..., 1] < 40)).mean()), 3),
        "contrast": round(float(gray.std()), 1),
    }
    warnings, blocking = [], []

    def add(text, severe):
        (blocking if severe else warnings).append(text)

    b = m["brightness"]
    if b < DARK[0]:
        add("Ảnh quá tối. Hãy bật thêm đèn hoặc đặt thẻ nơi sáng hơn.", b < DARK[1])
    elif b > BRIGHT[0]:
        add("Ảnh quá sáng. Hãy giảm đèn hoặc tránh ánh sáng chiếu thẳng vào thẻ.", b > BRIGHT[1])
    if m["sharpness"] < BLUR[0]:
        add("Ảnh bị mờ. Hãy giữ camera yên và chờ lấy nét rồi chụp lại.", m["sharpness"] < BLUR[1])
    if m["glare"] > GLARE[0]:
        add("Có vùng bị lóa sáng. Hãy nghiêng thẻ hoặc đổi hướng đèn để bớt phản chiếu.", m["glare"] > GLARE[1])
    if m["contrast"] < CONTRAST[0]:
        add("Ảnh thiếu tương phản. Hãy đặt thẻ lên nền trơn, khác màu thẻ.", m["contrast"] < CONTRAST[1])
    m["warnings"] = warnings + blocking
    m["blocking"] = blocking
    m["ok"] = not blocking
    return m
