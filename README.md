# CHEM VISION

Ứng dụng hỗ trợ dạy hóa học lớp 7: học sinh ghép thẻ nguyên tố thành phân tử dưới camera, nhấn **KIỂM TRA**,
phần mềm cho biết cấu trúc vừa ghép có đúng một chất trong cơ sở dữ liệu (31 chất) hay không.

Nguyên tắc: **AI chỉ "nhìn", phần mềm "kết luận"**. Gemini chỉ đọc kí hiệu và khung bao của từng thẻ (prompt không
chứa công thức). Liên kết giữa các thẻ do phần mềm đo bằng hình học (OpenCV), việc xác định chất do thuật toán
đối sánh đồ thị quyết định.

Có hai cách dùng, chung một phần lõi (`chem_vision/core.py`):

| | Bản web (triển khai lên Vercel) | Bản máy tính (Tkinter) |
|---|---|---|
| Camera | camera của trình duyệt, hoặc chọn ảnh | camera USB (OpenCV) |
| Giọng nói | giọng đọc của trình duyệt (vi-VN) | gTTS + pygame |
| Nhật ký, điểm | lưu trong trình duyệt, xuất CSV | tệp CSV cạnh dự án |
| Cài đặt | không cần | `pip install -r requirements-desktop.txt` |

## Bản web: chạy thử ở máy

```
pip install -r requirements.txt
python scripts/dev_server.py 3000
```

Mở http://localhost:3000. Máy chủ thử đọc `GEMINI_API_KEY` từ `chem_vision/.env` (sao chép từ `.env.example`) và cần
biến môi trường `ACCESS_CODE` để nhận ảnh thật. Nút **Chạy thử** dùng dữ liệu dựng sẵn, không cần khóa hay mã.

## Triển khai lên Vercel

Cấu hình đã có sẵn: `vercel.json` (thư mục `public`, hàm `api/*.py`, tối đa 60 giây, vùng `sin1`, header bảo mật và
quyền camera), `requirements.txt` (chỉ `numpy` và `opencv-python-headless`), `.python-version` (3.12), `.vercelignore`.

1. Đưa mã lên GitHub, vào vercel.com, **Add New → Project**, chọn repo. **Framework Preset: Other**; để trống
   Build Command và Output Directory (đã khai trong `vercel.json`).
2. Ở **Settings → Environment Variables** thêm hai biến cho Production (và Preview nếu cần):

   | Biến | Giá trị |
   |---|---|
   | `GEMINI_API_KEY` | khóa API Gemini của bạn |
   | `ACCESS_CODE` | mã truy cập do bạn đặt (giáo viên nhập trên trang để dùng nhận diện ảnh) |

   Khóa API chỉ nằm ở phía máy chủ, không bao giờ gửi xuống trình duyệt. **Không đặt `ACCESS_CODE` thì máy chủ từ chối
   nhận ảnh**, để tránh trang công khai bị người lạ dùng hết hạn mức API của bạn.
3. **Deploy**, rồi mở địa chỉ được cấp. Camera chỉ hoạt động trên HTTPS (Vercel đã có sẵn).
4. Kiểm tra sau khi triển khai: nhấn **Chạy thử** (phải ra kết quả), nhập mã truy cập rồi chọn một ảnh thẻ và nhấn
   **KIỂM TRA**.

Dùng dòng lệnh thay cho giao diện web: `npm i -g vercel`, `vercel link`, `vercel env add GEMINI_API_KEY`,
`vercel env add ACCESS_CODE`, `vercel --prod`.

Lưu ý khi vận hành:

- Mỗi lượt KIỂM TRA gọi Gemini một lần và tính vào hạn mức của khóa API. Mỗi địa chỉ IP bị giới hạn 20 lượt/phút
  (tính trong từng phiên bản máy chủ, chỉ là lớp bảo vệ phụ); lớp bảo vệ chính là `ACCESS_CODE`. Nên đặt hạn mức chi
  tiêu cho khóa API trong Google AI Studio.
- Ảnh được gửi qua máy chủ Vercel tới Google và không được lưu. Nhắc học sinh không để người hoặc thông tin cá nhân
  vào khung hình.
- Tên model nằm ở `chem_vision/recognizer.py` (`MODELS`). Tên model của Google thay đổi theo thời gian; nếu
  gặp lỗi 404 hoặc 502, đổi tên model rồi triển khai lại.

## Bản máy tính

```
pip install -r requirements-desktop.txt
```

| Lệnh | Tác dụng |
|---|---|
| `python -m chem_vision` | Camera + Gemini (cần camera và khóa API) |
| `python -m chem_vision --demo` | Chế độ thử: không cần camera, mạng hay khóa API |
| `python -m chem_vision --camera 1` | Dùng camera thứ hai |
| `python -m chem_vision --image anh.jpg --debug-out kq.png` | Nhận diện một ảnh có sẵn, lưu ảnh vẽ khung thẻ và liên kết |
| `python -m chem_vision --image anh.jpg --ai-links` | Như trên nhưng dùng liên kết do AI đoán (để so sánh) |
| `chay_chem_vision.bat` | Chạy nhanh trên Windows |

Khóa API: sao chép `chem_vision/.env.example` thành `chem_vision/.env` rồi điền `GEMINI_API_KEY=...`
(`.env` đã nằm trong `.gitignore`). Thứ tự tìm khóa: biến môi trường, rồi `.env` và `api_key.txt` trong `chem_vision`,
rồi trong thư mục gốc.

## Tính năng

- Nhận diện thẻ (Gemini đọc kí hiệu và khung bao), liên kết đo bằng hình học, loại thẻ bị liệt kê hai lần
- Đối sánh với 31 chất: khớp, sai liên kết (nêu liên kết thừa/thiếu), ghép dở, không nhận ra; tách cụm thẻ rời nhau
- Gợi ý "Có phải bạn muốn ghép …?" kèm nút Đúng / Không phải, nêu thẻ thiếu hoặc thừa
- Yêu cầu chụp lại khi ảnh chưa rõ; tự thử lại và chuyển model dự phòng khi API lỗi
- **Chế độ thử thách**: bộ đề, tự chấm, 3 mức gợi ý, tính điểm
- **Nhật ký lớp học**: ghi từng lượt (không lưu ảnh, không lưu tên), báo cáo lỗi thường gặp, xuất CSV

## Kiểm thử

```
python -m unittest discover -s chem_vision/tests -t .
```

96 kiểm thử, không cần camera hay mạng (Gemini được thay bằng bản giả). Kiểm thử giao diện máy tính cần màn hình.

## Cấu trúc

| Tệp | Nội dung |
|---|---|
| `chem_vision/core.py` | làm sạch dữ liệu AI, cơ sở dữ liệu 31 chất, đối sánh đồ thị, gợi ý, lời thông báo |
| `chem_vision/geometry.py` | liên kết thẻ bằng hình học, loại thẻ trùng |
| `chem_vision/recognizer.py` | prompt, gọi Gemini bằng REST, bộ giả lập |
| `chem_vision/retry.py` | thử lại, model dự phòng, ngân sách thời gian |
| `chem_vision/features.py` | chế độ thử thách, nhật ký lớp học |
| `chem_vision/web.py` | các điểm vào của bản web (mã truy cập, giới hạn tần suất, kiểm tra ảnh) |
| `api/*.py` | hàm serverless Vercel (mỏng, gọi `web.py`) |
| `public/` | giao diện web |
| `chem_vision/app.py`, `speech.py` | giao diện và giọng nói bản máy tính |
| `scripts/dev_server.py` | máy chủ thử cục bộ giống Vercel |

## Đã và chưa kiểm chứng

Đã thử với Gemini thật bằng 2 ảnh thẻ nguyên tố (thẻ chữ nhật, không phải thẻ lục giác ghép phân tử), qua cả máy chủ
thử cục bộ lẫn giao diện web: mỗi ảnh khoảng 3-6 giây. Chưa triển khai thật lên Vercel, chưa chạy với camera và bộ thẻ
lục giác thật, chưa đo độ chính xác trên bộ ảnh có đáp án.
