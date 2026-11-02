# Hướng dẫn đưa CHEM VISION lên mạng: Vercel và Render

Hai nơi chạy được, chọn một hoặc dùng cả hai:

| | **Vercel** | **Render** |
|---|---|---|
| Phù hợp | Bản chính thức, nhanh, không bao giờ "ngủ" | Quay video, thử lớp học trực tuyến nhanh |
| Lớp học trực tuyến | Cần thêm **Upstash Redis** (miễn phí, 3 phút cài) | Bật bằng một biến `CLASSROOM_MEMORY=1` |
| Gói miễn phí | Đủ dùng | Máy chủ **ngủ sau 15 phút** không ai truy cập, lần mở đầu chờ khoảng 1 phút; lớp học đang mở mất khi máy chủ ngủ hoặc khởi động lại |
| Địa chỉ | `https://<tên>.vercel.app` | `https://<tên>.onrender.com` |

Cả hai đều cho địa chỉ **HTTPS**, điều bắt buộc để mở được camera trên điện thoại.

**Khuyên dùng cho ngày quay video:** Render (bật lớp học nhanh). Nhớ **mở trang trước giờ quay 2 phút** cho máy chủ thức dậy, và tạo lớp mới ngay trước cảnh 8.

---

## Bước 0: Chuẩn bị (làm một lần, dùng cho cả hai)

### 0.1. Tài khoản
- Tài khoản **GitHub** có quyền với kho `dinhmanhcvp/ChemVision`.
- Đăng ký **vercel.com** và/hoặc **render.com** bằng chính tài khoản GitHub đó (nút "Continue with GitHub").

### 0.2. Đưa mã mới nhất lên GitHub
Vercel và Render lấy mã từ GitHub, không lấy từ máy tính. Các thay đổi mới (tệp `render.yaml`, sửa `scripts/dev_server.py`) phải được đẩy lên trước. Mở terminal trong thư mục dự án:

```bash
git add render.yaml scripts/dev_server.py
```
```bash
git commit -m "Cho phép chạy máy chủ trên Render.com"
```
```bash
git push origin main
```

Mở `https://github.com/dinhmanhcvp/ChemVision`, thấy tệp `render.yaml` ở danh sách là được.

### 0.3. Khóa Gemini và mã truy cập (không bắt buộc)
**Thẻ in có mã vuông (bộ thẻ PDF) chạy được mà không cần khóa hay mã gì.** Chỉ cần bước này nếu muốn đọc cả thẻ thường (thẻ tự vẽ, không có mã vuông).

1. Vào **aistudio.google.com** → đăng nhập Google → **Get API key** → **Create API key**. Sao chép khóa (dạng `AIza...`).
2. Trong Google AI Studio, đặt **hạn mức chi tiêu** cho khóa để không bị tính tiền ngoài ý muốn.
3. Tự đặt một **mã truy cập**, ví dụ `chemvision2026`. Mã này để người lạ không dùng hết hạn mức của nhóm. Người dùng nhập mã ở thẻ **Thêm** → ô **Mã truy cập (cho thẻ không có mã vuông)**.

**Không bao giờ** dán khóa API vào mã nguồn, ảnh chụp màn hình hay video. Khóa chỉ nhập ở trang cài đặt của Vercel hoặc Render.

---

## Phần A: Deploy lên Vercel

### A1. Tạo dự án
1. Vào **vercel.com/new** (hoặc **Add New… → Project**).
2. Ở mục **Import Git Repository**, tìm `ChemVision` → nhấn **Import**.
   Không thấy kho? Nhấn **Adjust GitHub App Permissions** và cho Vercel quyền đọc kho này.
3. Màn hình **Configure Project**:
   - **Framework Preset:** chọn **Other**.
   - **Root Directory:** để nguyên `./`.
   - **Build and Output Settings:** để nguyên (tệp `vercel.json` đã khai báo thư mục `public` và các hàm `api/*.py`).

### A2. Biến môi trường (chỉ khi làm bước 0.3)
Ngay trên màn hình đó, mở **Environment Variables**, thêm:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | khóa `AIza...` |
| `ACCESS_CODE` | mã truy cập đã đặt |

### A3. Deploy
Nhấn **Deploy**, chờ 1-2 phút đến khi hiện pháo giấy và ảnh trang. Nhấn **Continue to Dashboard** → bấm vào địa chỉ ở mục **Domains** (dạng `chem-vision-xxx.vercel.app`).

### A4. Bật lớp học trực tuyến (Upstash Redis)
1. Trong dự án trên Vercel: thẻ **Storage** → **Create Database** (hoặc **Marketplace**) → chọn **Upstash for Redis** → **Continue**.
2. Chọn gói **Free**, vùng **Singapore** (gần Việt Nam nhất) → đặt tên → **Create**.
3. Ở bước **Connect Project**, chọn dự án ChemVision → **Connect**. Vercel tự thêm các biến `KV_REST_API_URL`, `KV_REST_API_TOKEN` (hoặc `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`). Mã nguồn chấp nhận cả hai bộ tên.
4. **Bắt buộc deploy lại** để biến mới có hiệu lực: thẻ **Deployments** → bản trên cùng → nút **⋯** → **Redeploy**.

### A5. Kiểm tra
Làm theo **Phần C**.

### Cập nhật về sau
Mỗi lần `git push` lên nhánh `main`, Vercel tự deploy lại. Đổi biến môi trường thì phải **Redeploy** như bước A4.4.

---

## Phần B: Deploy lên Render

Kho đã có sẵn tệp `render.yaml` khai báo toàn bộ cấu hình, nên chỉ cần vài cú nhấp.

### B1. Tạo dịch vụ từ Blueprint
1. Vào **dashboard.render.com** → nút **+ New** → **Blueprint**.
2. Lần đầu: **Connect GitHub** → cho Render quyền đọc kho `ChemVision`.
3. Chọn kho `dinhmanhcvp/ChemVision`, nhánh `main` → **Connect**.
4. Render đọc `render.yaml` và hiện một dịch vụ web tên **chem-vision** (Python, vùng Singapore, gói Free).
5. Đặt **Blueprint Name** tùy ý, ví dụ `chemvision`.
6. Render hỏi giá trị cho hai biến để trống:
   - `GEMINI_API_KEY`: dán khóa nếu đã làm bước 0.3, không thì để trống.
   - `ACCESS_CODE`: dán mã truy cập, không thì để trống.
7. Nhấn **Deploy Blueprint** (có thể là **Apply**).

### B2. Chờ build
Vào dịch vụ **chem-vision** → thẻ **Logs**. Lần đầu mất 3-5 phút (cài numpy và OpenCV). Thành công khi thấy dòng:

```
http://0.0.0.0:10000  (GEMINI_API_KEY: ..., ACCESS_CODE: ...)
```

và trạng thái đầu trang chuyển sang **Live** màu xanh. Địa chỉ trang ở góc trên bên trái, dạng `https://chem-vision-xxxx.onrender.com`.

### B3. Cách làm thủ công (nếu không dùng Blueprint)
**+ New → Web Service** → chọn kho → điền:

| Ô | Giá trị |
|---|---|
| Language | Python 3 |
| Branch | main |
| Region | Singapore |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python scripts/dev_server.py` |
| Instance Type | Free |

Rồi mở **Advanced → Add Environment Variable**: `HOST` = `0.0.0.0`, `CLASSROOM_MEMORY` = `1`, và nếu có thì `GEMINI_API_KEY`, `ACCESS_CODE`. Mục **Health Check Path** điền `/api/meta`. Nhấn **Deploy Web Service**.

Quan trọng: thiếu biến `HOST=0.0.0.0` thì máy chủ chỉ nghe nội bộ, Render báo lỗi "No open ports detected" và deploy thất bại.

### B4. Kiểm tra
Làm theo **Phần C**.

### Cập nhật về sau
Mỗi lần `git push` lên `main`, Render tự build lại (khoảng 2-3 phút). Đổi biến ở thẻ **Environment** → **Save Changes**, Render tự khởi động lại.

---

## Phần C: Kiểm tra sau khi deploy (cả hai nơi)

Mở địa chỉ trang **trên điện thoại** (Chrome trên Android, Safari trên iPhone) và làm lần lượt:

| # | Thao tác | Kết quả đúng |
|---|---|---|
| 1 | Mở `https://<địa chỉ>/api/meta` | Hiện chữ JSON bắt đầu bằng `{"ok": true` |
| 2 | Mở trang chính → thẻ **Thêm** → **Chạy thử** | Thẻ **Ghép thẻ** hiện kết quả dựng sẵn |
| 3 | Thẻ **Ghép thẻ** → **Bật camera** | Trình duyệt hỏi quyền camera → **Cho phép** → thấy hình camera |
| 4 | Ghép thẻ H₂O từ bộ thẻ in → **KIỂM TRA** | Con dấu xanh, "Cấu trúc khớp với nước…" |
| 5 | Ghép H–H–O → **KIỂM TRA** | Con dấu đỏ, "thừa liên kết H–H" |
| 6 | Laptop: thẻ **Lớp học** → **Tôi là giáo viên** → **Tạo lớp** | Hiện mã lớp 6 ký tự |
| 7 | Điện thoại: **Lớp học** → **Tôi là học sinh** → nhập mã → **Vào lớp**, làm một câu | Laptop → **Mở bảng điều khiển** thấy nhóm vừa vào và kết quả |
| 8 | (Nếu có khóa Gemini) Thẻ **Thêm** nhập mã truy cập, chụp một thẻ không có mã vuông | Có kết quả sau 3-7 giây |

Bước 3 thử trên **chính điện thoại sẽ dùng quay video**, vì quyền camera và cách hiển thị khác nhau giữa các máy.

---

## Phần D: Lỗi thường gặp

| Hiện tượng | Nguyên nhân và cách sửa |
|---|---|
| Không bật được camera | Phải mở bằng `https://`. Kiểm tra quyền camera của trình duyệt trong Cài đặt điện thoại. Trên iPhone dùng Safari. |
| Render: "No open ports detected", deploy thất bại | Thiếu biến `HOST=0.0.0.0`. Thêm ở thẻ **Environment**. |
| Render: trang mở rất lâu lần đầu | Máy chủ gói Free đang ngủ. Chờ khoảng 1 phút; trước giờ quay mở trang sẵn. |
| Render: mã lớp vừa tạo bỗng "không tồn tại" | Máy chủ vừa ngủ hoặc khởi động lại nên lớp trong bộ nhớ bị xóa. Tạo lớp mới. Cần lớp bền thì dùng Vercel + Upstash. |
| Vercel: "Tính năng lớp học trực tuyến chưa được bật" | Chưa kết nối Upstash, hoặc kết nối rồi mà chưa **Redeploy** (bước A4). |
| "Máy chủ chưa đặt ACCESS_CODE nên chưa nhận ảnh" | Đang chụp thẻ **không có mã vuông**. Dùng thẻ in từ PDF, hoặc đặt `ACCESS_CODE` + `GEMINI_API_KEY` rồi deploy lại. |
| Thẻ thường báo lỗi 404 hoặc 502 từ Gemini | Google đổi tên model. Sửa danh sách `MODELS` trong `chem_vision/recognizer.py`, `git push` để deploy lại. |
| Báo "quá nhiều yêu cầu" | Mỗi IP tối đa 20 lượt nhận diện mỗi phút; chờ một phút. |
| Thẻ in nhận diện sai | In lại đúng **A4, tỉ lệ 100%** (không chọn "Vừa trang"), nền bàn trơn khác màu thẻ, đủ sáng, không che mã vuông. |
| Vercel build lỗi liên quan đến `cv2.aruco` | README ghi việc này chưa được kiểm chứng trên Vercel. Tạm dùng Render, và báo lỗi kèm phần Logs để sửa. |

---

## Ghi chú về dữ liệu

- Ảnh thẻ **có mã vuông** chỉ được xử lý tại máy chủ (Vercel hoặc Render), không gửi đi đâu khác.
- Ảnh thẻ **thường** được gửi tới Google để đọc, không được lưu.
- Lớp học chỉ lưu nhãn nhóm và kết quả từng lượt (không ảnh, không tên), tự xóa sau 24 giờ (trên Render: mất sớm hơn nếu máy chủ khởi động lại).
