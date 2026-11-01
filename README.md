# CHEM VISION

Ứng dụng hỗ trợ dạy hóa học THCS (Khoa học tự nhiên lớp 6 đến 9): học sinh ghép thẻ nguyên tố thành phân tử dưới camera, nhấn
**KIỂM TRA**, phần mềm cho biết cấu trúc vừa ghép có đúng một chất trong cơ sở dữ liệu (70 chất) hay không, sai ở đâu và vì sao.

Nguyên tắc: **AI chỉ "nhìn", phần mềm "kết luận"**. Thẻ có mã vuông (ArUco) được đọc ngay trên máy, ngoại tuyến, miễn phí; thẻ thường
được Gemini đọc ký hiệu và khung bao. Liên kết giữa các thẻ do phần mềm đo bằng hình học (OpenCV), việc xác định chất do thuật toán
đối sánh đồ thị quyết định. Mọi lời giải thích lỗi sinh ra từ chẩn đoán xác định, không do AI tự nghĩ.

## Phạm vi chương trình

| Lớp | Nội dung | Bộ đề, công cụ |
|---|---|---|
| 6 | Chất quanh ta | bộ đề "Lớp 6: Chất quanh ta" |
| 7 | Nguyên tử, phân tử, hóa trị, công thức, phân tử khối | 4 bộ đề gốc + "Lập công thức theo hóa trị"; phân tử khối; chú thích hợp chất ion |
| 8 | Oxit, axit, bazơ, muối, phân bón, phản ứng hóa học | 3 bộ đề; **cân bằng 24 phương trình**, kiểm tra bảo toàn khối lượng |
| 9 | Hiđrocacbon, rượu, axit axetic, đồng phân | 2 bộ đề (có butan và isobutan, etanol và đimetyl ete) |

Chưa có: glucozơ, saccarozơ, polime (quá nhiều nguyên tử để ghép bằng thẻ), kim loại và hợp kim (không phải phân tử).

## Tính năng

- **Nhận diện:** mã ArUco trên thẻ (ngoại tuyến) hoặc Gemini (khung bao + ký hiệu); liên kết đo bằng hình học; loại thẻ bị liệt kê hai lần
- **Kiểm tra chất lượng ảnh:** cảnh báo trực tiếp trên camera (tối, mờ, lóa, thiếu tương phản); ảnh hỏng nặng bị chặn trước khi gọi AI
- **Đối sánh 70 chất:** khớp, sai liên kết (nêu liên kết thừa/thiếu), ghép dở, không nhận ra; tách cụm thẻ rời nhau
- **Giải thích "Vì sao?"** bằng lời lớp 7 (hóa trị, liên kết thừa/thiếu, đồng phân); phân tử khối; chú thích hợp chất ion (liên kết ion, mạng tinh thể, nét đứt trên ảnh)
- **Gợi ý** "Có phải bạn muốn ghép …?" kèm nút Đúng / Không phải, nêu thẻ thiếu hoặc thừa
- **Chế độ thử thách:** 11 bộ đề theo lớp, tự chấm, 3 mức gợi ý, tính điểm; đề theo hóa trị ("lập công thức của Al (III) và O (II) rồi ghép")
- **Sao và huy hiệu:** 1 đến 3 sao cho mỗi chất giải đúng, 5 huy hiệu, lưu ngay trong trình duyệt; không có bảng xếp hạng, đồng hồ đếm ngược hay "mất chuỗi"
- **Cân bằng phương trình (lớp 8):** nhập hệ số bằng nút − và +, bảng đếm nguyên tử cho thấy ngay nguyên tố nào lệch, xem đáp án
- **Nhật ký và báo cáo giáo viên:** lỗi thường gặp, **quan niệm sai kèm cách xử lý**, xuất CSV
- **Lớp học trực tuyến:** giáo viên tạo lớp lấy mã, các nhóm vào bằng mã, bảng điều khiển thấy bộ đề và tiến độ từng nhóm, số lần bỏ qua và xin gợi ý, nhóm kẹt, nhóm đang rảnh, câu sai nhiều; lớp kết thúc thì máy học sinh tự ra khỏi lớp (cần Upstash Redis)
- **Giao diện "phiếu thí nghiệm":** năm thẻ (Ghép thẻ, Thử thách, Cân bằng, Lớp học, Thêm), thanh bước 01-02-03, nền giấy ấm, con dấu lục giác cho kết quả, tổ ong tiến độ, biểu tượng SVG (không emoji), chế độ tối, tôn trọng "giảm chuyển động"; căn cứ và điều chưa kiểm chứng ở `docs/ngon-ngu-thiet-ke.md`
- **Bộ thẻ in được:** PDF A4 cho lớp 7, 8, 9 (`public/the-in/`), tạo bằng `scripts/make_cards.py`
- **Thử nghiệm đối chứng:** bộ câu hỏi trước/sau, thiết kế và công cụ phân tích thống kê (`docs/`, `scripts/analyze_experiment.py`)

Có hai cách dùng, chung phần lõi `chem_vision/core.py`:

| | Bản web (Vercel) | Bản máy tính (Tkinter) |
|---|---|---|
| Camera | camera trình duyệt, hoặc chọn ảnh | camera USB (OpenCV) |
| Giọng nói | giọng đọc trình duyệt (vi-VN) | gTTS + pygame |
| Nhật ký, điểm | trong trình duyệt, xuất CSV; hoặc lớp trực tuyến | tệp CSV cạnh dự án |
| Cài đặt | không cần | `pip install -r requirements-desktop.txt` |

## In bộ thẻ

Mở mục "Tải bộ thẻ in" trên trang (hoặc `public/the-in/bo-the-lop-7.pdf`), in **khổ A4, tỉ lệ 100%** (không chọn "Vừa trang"), cắt theo viền
lục giác, tốt nhất ép nhựa. Ghép các thẻ của một phân tử cho **các cạnh chạm sát nhau**, để các phân tử khác nhau cách nhau ít nhất một thẻ,
đặt trên nền trơn khác màu thẻ, đủ sáng. Không che mã vuông đen trắng ở giữa thẻ. Trang đầu của PDF có hướng dẫn và số thẻ trong bộ.
Tạo lại: `python scripts/make_cards.py` (đổi kích thước thẻ phải đổi cả `CARD_TO_MARKER` trong `chem_vision/markers.py`).

## Bản web: chạy thử ở máy

```
pip install -r requirements.txt
python scripts/dev_server.py 3000
```

Mở http://localhost:3000. Máy chủ thử đọc `GEMINI_API_KEY` từ `chem_vision/.env` (sao chép từ `.env.example`). Biến môi trường tùy chọn:
`ACCESS_CODE` (mã truy cập cho thẻ không có mã vuông), `CLASSROOM_MEMORY=1` (bật lớp học trực tuyến bằng bộ nhớ, chỉ để thử).
Nút **Chạy thử** dùng dữ liệu dựng sẵn, không cần khóa hay mã.

## Triển khai lên Vercel

Cấu hình có sẵn: `vercel.json` (thư mục `public`, hàm `api/*.py` tối đa 60 giây, vùng `sin1`, header bảo mật và quyền camera),
`requirements.txt` (chỉ `numpy` và `opencv-python-headless`), `.python-version` (3.12), `.vercelignore`.

1. Đưa mã lên GitHub, vào vercel.com, **Add New → Project**, chọn repo, **Framework Preset: Other**.
2. **Settings → Environment Variables:**

   | Biến | Bắt buộc | Giá trị |
   |---|---|---|
   | `GEMINI_API_KEY` | để đọc thẻ không có mã vuông | khóa API Gemini |
   | `ACCESS_CODE` | cùng điều kiện trên | mã do bạn đặt; thiếu thì máy chủ từ chối nhận ảnh thẻ thường |
   | `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN` | để bật lớp học trực tuyến | từ Vercel Marketplace → **Upstash for Redis** (cũng chấp nhận tên cũ `KV_REST_API_URL`, `KV_REST_API_TOKEN`) |

   Thẻ **có mã vuông** (bộ thẻ in) đọc được mà không cần `GEMINI_API_KEY` hay `ACCESS_CODE`. Khóa API chỉ nằm ở máy chủ.
3. **Deploy**, rồi thử: nhấn **Chạy thử**; chọn một ảnh thẻ có mã và nhấn **KIỂM TRA**; nếu bật lớp học, thử **Tạo lớp**.

Dòng lệnh: `npm i -g vercel`, `vercel link`, `vercel env add ...`, `vercel --prod`.

Lưu ý vận hành:

- Mỗi lượt đọc thẻ thường gọi Gemini một lần, tính vào hạn mức khóa API; mỗi IP giới hạn 20 lượt/phút (lớp phòng thủ phụ, chính là `ACCESS_CODE`).
  Nên đặt hạn mức chi tiêu cho khóa trong Google AI Studio.
- Ảnh thẻ thường được gửi qua Vercel tới Google và không được lưu; ảnh thẻ có mã được xử lý tại máy chủ Vercel và không gửi đi đâu khác.
- Dữ liệu lớp học trực tuyến chỉ gồm nhãn nhóm và kết quả từng lượt (không ảnh, không tên), tự xóa sau 24 giờ.
- Tên model nằm ở `chem_vision/recognizer.py` (`MODELS`); tên model của Google đổi theo thời gian, gặp lỗi 404 hoặc 502 thì đổi tên rồi triển khai lại.

## Bản máy tính

```
pip install -r requirements-desktop.txt
```

| Lệnh | Tác dụng |
|---|---|
| `python -m chem_vision` | Camera; có khóa API thì đọc cả thẻ thường, không có thì chỉ đọc thẻ có mã (ngoại tuyến) |
| `python -m chem_vision --demo` | Chế độ thử: không cần camera, mạng hay khóa API |
| `python -m chem_vision --camera 1` | Dùng camera thứ hai |
| `python -m chem_vision --image anh.jpg --debug-out kq.png` | Nhận diện một ảnh có sẵn, lưu ảnh vẽ khung thẻ và liên kết |
| `python -m chem_vision --image anh.jpg --ai-links` | Như trên nhưng dùng liên kết do AI đoán (để so sánh) |
| `chay_chem_vision.bat` | Chạy nhanh trên Windows |

Khóa API: sao chép `chem_vision/.env.example` thành `chem_vision/.env` rồi điền `GEMINI_API_KEY=...` (`.env` nằm trong `.gitignore`).

## Thử nghiệm đối chứng

`docs/thiet-ke-thu-nghiem.md` (thiết kế, cỡ mẫu, đạo đức, mối đe dọa), `docs/bo-cau-hoi-kiem-tra.json` (hai dạng đề song song, đáp án được kiểm bằng mã),
`python scripts/analyze_experiment.py du_lieu.csv` (t Welch, Hedges g, ANCOVA có sai số chuẩn theo cụm lớp, cỡ mẫu). **Chưa có kết quả thử nghiệm nào.**

## Kiểm thử

```
python -m unittest discover -s chem_vision/tests -t .
```

245 kiểm thử, không cần camera hay mạng (Gemini được thay bằng bản giả; vòng "in thẻ rồi nhận diện" chạy trên trang in thật). Kiểm thử giao diện
máy tính cần màn hình.

### Kiểm thử giao diện theo vai người dùng

`scripts/e2e_browser.js` chạy trong trình duyệt thật, đóng vai học sinh lớp 7 lần đầu dùng, học sinh lớp 8 làm thử thách và cân bằng phương trình,
giáo viên và nhóm trong lớp, người không có camera, người dùng mất mạng; 113 kiểm tra (gồm cân bằng cả 24 phương trình, sao và huy hiệu,
vòng đời lớp học, bố cục không tràn ngang, nút đủ lớn để chạm, mọi điều khiển có tên truy cập, không vi phạm CSP).

```
ACCESS_CODE=thu CLASSROOM_MEMORY=1 E2E=1 python scripts/dev_server.py 3111
```

Mở http://localhost:3111, rồi dán vào console của trình duyệt:

```
document.head.append(Object.assign(document.createElement('script'), { src: '/__e2e.js' }));
await runE2E();
```

Kết quả dạng `{ passed: 113, failed: [] }` (ở khung hẹp dưới 200 px các kiểm tra bố cục tự bỏ qua nên số kiểm tra ít hơn). Kịch bản dùng dữ liệu "Chạy thử"
nên không cần camera hay khóa API; đã chạy ở khung máy tính 1180 px, điện thoại 390 px (cả sáng và tối) và kiểm tra tràn ngang ở 320 px.
`chem_vision/tests/test_ui_wiring.py` kiểm tra tĩnh: mọi nút có xử lý và được phân loại (gọi máy chủ hay chỉ chạy trong trình duyệt), không dùng hộp
`confirm()` mặc định, không dùng `innerHTML`, camera chỉ mở khi bấm nút; cùng các ràng buộc của ngôn ngữ thiết kế (tương phản chữ đạt WCAG AA ở cả
nền sáng và tối, nút chạm tối thiểu 48 px, tôn trọng giảm chuyển động, không tải tài nguyên bên ngoài, không emoji làm biểu tượng, không nền chuyển màu, không bảng xếp hạng hay đồng hồ đếm ngược).

## Cấu trúc

| Tệp | Nội dung |
|---|---|
| `chem_vision/core.py` | làm sạch dữ liệu AI, 70 chất, đối sánh đồ thị, gợi ý, lời thông báo |
| `chem_vision/curriculum.py` | nguyên tử khối, hóa trị, màu thẻ, lập công thức theo hóa trị, bộ đề theo lớp |
| `chem_vision/markers.py`, `quality.py`, `geometry.py` | đọc mã ArUco, kiểm tra chất lượng ảnh, liên kết bằng hình học |
| `chem_vision/recognizer.py`, `retry.py` | gọi Gemini bằng REST, thử lại và model dự phòng, bộ giả lập |
| `chem_vision/pedagogy.py`, `reactions.py` | giải thích lỗi và quan niệm sai; cân bằng phương trình |
| `chem_vision/features.py`, `classroom.py` | thử thách, nhật ký; lớp học trực tuyến |
| `chem_vision/web.py`, `api/*.py` | bản web (điểm vào, hàm serverless) |
| `public/` | giao diện web: `index.html`, `style.css`, `app.js` (điều khiển), `ui.js` (biểu tượng, con dấu, pháo giấy, thông báo), `progress.js` (sao, huy hiệu), `img/` (con dấu, minh họa, 27 biểu tượng) |
| `chem_vision/app.py`, `speech.py` | giao diện và giọng nói bản máy tính |
| `scripts/` | `dev_server.py`, `make_cards.py`, `analyze_experiment.py` |
| `docs/` | phân tích thị trường, ngôn ngữ thiết kế giao diện, thiết kế thử nghiệm, bộ câu hỏi |

## Đã và chưa kiểm chứng

Đã thử với Gemini thật bằng 2 ảnh thẻ nguyên tố (thẻ chữ nhật, không phải thẻ lục giác ghép phân tử), qua máy chủ thử và giao diện web (3 đến 7 giây).
Đã thử giao diện web trong trình duyệt tích hợp (không phải điện thoại thật): lọc theo lớp, đề theo hóa trị, phương trình, ảnh thẻ có mã, lớp học (bằng kho trong bộ nhớ), sao và huy hiệu, chế độ tối, không vi phạm CSP.
Vòng in thẻ rồi đọc lại đã kiểm tra tự động trên trang in thật, kể cả khi thu nhỏ, nghiêng, hơi mờ.

**Chưa kiểm chứng:** triển khai thật lên Vercel (gồm việc `cv2.aruco` có trong gói headless trên môi trường chạy của Vercel), kết nối Upstash Redis thật,
camera thật trong trình duyệt, thẻ thật in ra giấy rồi chụp bằng điện thoại, độ chính xác Gemini trên bộ ảnh có đáp án, giọng đọc của trình duyệt,
giao diện trên điện thoại thật và với học sinh thật (mức hứng thú, tải nhận thức, độ dễ dùng của nút chỉ được đánh giá theo nghiên cứu và đo bố cục, chưa đo trên người dùng),
và hiệu quả dạy học (cần thử nghiệm đối chứng).
