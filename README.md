# CHEM VISION

Ứng dụng hỗ trợ dạy hóa học lớp 7: học sinh ghép thẻ nguyên tố lục giác thành phân tử dưới camera,
nhấn **KIỂM TRA**, phần mềm cho biết cấu trúc vừa ghép có đúng một chất trong cơ sở dữ liệu hay không.

Nguyên tắc: **AI chỉ "nhìn", phần mềm "kết luận"**. Gemini chỉ trả danh sách thẻ và các cặp thẻ chạm
cạnh (prompt không chứa công thức). Việc xác định chất do thuật toán đối sánh đồ thị quyết định.

## Cài đặt

```
pip install -r requirements.txt
```

Khóa API Gemini: sao chép `chem_vision/.env.example` thành `chem_vision/.env` rồi điền `GEMINI_API_KEY=...`
(tệp `.env` nằm trong `.gitignore`, không bị đẩy lên GitHub). Thứ tự tìm khóa: biến môi trường `GEMINI_API_KEY`,
rồi `.env` và `api_key.txt` trong thư mục `chem_vision`, rồi trong thư mục gốc dự án.

## Chạy

| Lệnh | Tác dụng |
|---|---|
| `python -m chem_vision` | Camera + Gemini (cần camera và khóa API) |
| `python -m chem_vision --demo` | Chế độ thử: không cần camera, mạng hay khóa API; chọn tình huống giả lập |
| `python -m chem_vision --camera 1` | Dùng camera thứ hai |
| `python -m chem_vision --image anh.jpg --debug-out kq.png` | Nhận diện một ảnh có sẵn (không cần camera), lưu ảnh vẽ khung thẻ và liên kết để kiểm tra bằng mắt |
| `python -m chem_vision --image anh.jpg --ai-links` | Như trên nhưng dùng liên kết do AI đoán (để so sánh với hình học) |
| `chay_chem_vision.bat` | Chạy nhanh trên Windows |

Thiếu camera hoặc khóa API thì ứng dụng tự chuyển sang chế độ thử và ghi lý do ở góc phải.

## Tính năng

- Camera Live, nút KIỂM TRA (chỉ một khung hình được gửi đi, không ghi ảnh ra đĩa)
- Nhận diện thẻ: Gemini đọc kí hiệu và khung bao; **liên kết giữa các thẻ được tính bằng hình học (OpenCV)**, không để AI đoán; loại thẻ bị liệt kê hai lần
- Đối sánh với 31 chất, phân biệt: khớp, sai liên kết, ghép dở, không nhận ra
- Gợi ý "Có phải bạn muốn ghép …?" kèm nút Đúng / Không phải, nêu thẻ thiếu hoặc thừa
- Tách cụm thẻ rời nhau, yêu cầu chụp lại khi ảnh chưa rõ
- Đọc kết quả bằng giọng nói tiếng Việt (gTTS + pygame)
- Tự thử lại và chuyển model dự phòng khi API lỗi
- **Chế độ thử thách**: bộ đề, tự chấm, 3 mức gợi ý, tính điểm
- **Nhật ký lớp học**: ghi CSV (không lưu ảnh, không lưu tên) và báo cáo lỗi thường gặp

## Kiểm thử

```
python -m unittest discover -s chem_vision/tests -t .
```

62 kiểm thử, không cần camera hay mạng (Gemini được thay bằng bản giả). Kiểm thử giao diện cần màn hình.

## Cấu trúc

| Tệp | Nội dung |
|---|---|
| `core.py` | làm sạch dữ liệu AI, cơ sở dữ liệu 31 chất, đối sánh đồ thị, gợi ý, lời thông báo |
| `retry.py` | thử lại, model dự phòng, ngân sách thời gian |
| `recognizer.py` | prompt, gọi Gemini, bộ giả lập |
| `speech.py` | giọng nói |
| `features.py` | chế độ thử thách, nhật ký lớp học |
| `app.py` | giao diện Tkinter |

## Đã và chưa kiểm chứng

Đã thử với Gemini thật bằng 2 ảnh thẻ nguyên tố (thẻ chữ nhật, không phải thẻ lục giác ghép phân tử): đọc đúng kí hiệu
thẻ nhìn rõ, khung bao chuẩn, mỗi ảnh xử lý trong khoảng 4-6 giây. Chưa chạy với camera và bộ thẻ lục giác thật; chưa đo
độ chính xác trên bộ ảnh có đáp án.

Model (`recognizer.MODELS`): `gemini-flash-lite-latest` (chính, 3-4 giây/ảnh) và `gemini-2.5-flash` (dự phòng). Khi thử,
`gemini-2.5-flash-lite` báo 404 (không còn dùng được) và `gemini-flash-latest` mất 55-180 giây/ảnh nên không dùng. Tên model
thay đổi theo thời gian: nếu gặp lỗi 404, đổi tên trong `MODELS` (liệt kê model dùng được bằng API `v1beta/models`).
Tùy chọn tắt suy luận mở rộng (`THINKING_BUDGET`) chỉ có tác dụng với `google-genai` từ bản 1.x trở lên.
