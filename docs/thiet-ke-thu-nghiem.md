# Thiết kế thử nghiệm đối chứng cho CHEM VISION

Mục đích: có bằng chứng của chính dự án về việc CHEM VISION giúp học sinh lớp 7 học phân tử và công thức hóa học ở mức nào so với
cách dạy quen thuộc (mô hình bi–que). Đây là kế hoạch để thực hiện, **chưa có kết quả nào**.

## 1. Câu hỏi và giả thuyết

- **Câu hỏi chính:** học sinh học bằng CHEM VISION có điểm kiểm tra sau bài cao hơn, bằng hay thấp hơn học sinh học bằng mô hình bi–que?
- **Giả thuyết:** cách dùng CHEM VISION cho kết quả **không thấp hơn** mô hình bi–que và có thể cao hơn ở kĩ năng "cách nối quyết định chất"
  (nhờ phản hồi tức thì). Cần nói trước điều này vì nghiên cứu trước đó với công cụ tương tự (Happy Atoms, Augmented Chemistry) chỉ
  thấy kết quả **ngang bằng**, không vượt trội, nên đừng đặt mục tiêu "học tốt hơn" khi chưa có dữ liệu.
- **Câu hỏi phụ:** thái độ học tập, kĩ năng nào tiến bộ nhiều nhất, kết quả sau 4 đến 6 tuần.

## 2. Thiết kế

- **Đơn vị chia nhóm là lớp**, không phải từng học sinh, vì học sinh cùng lớp học chung và ảnh hưởng lẫn nhau. Chọn ngẫu nhiên lớp nào dùng
  CHEM VISION (CV), lớp nào dùng mô hình bi–que (BQ). Nếu một giáo viên dạy cả hai nhóm, ưu tiên cách này để loại ảnh hưởng của người dạy.
- **Nội dung và thời lượng giống nhau:** cùng bài (phân tử, công thức, hóa trị), cùng 2 tiết, cùng phiếu học tập; chỉ khác công cụ ghép.
- **Cỡ mẫu** (tính bằng `scripts/analyze_experiment.py`, hàm `sample_size_per_group`, xấp xỉ chuẩn, α = 0,05, hiệu lực 0,8):

  | Cỡ ảnh hưởng muốn phát hiện (d) | Mỗi nhóm nếu chia theo học sinh | Mỗi nhóm nếu chia theo lớp 30 em, ICC = 0,1 |
  |---|---|---|
  | 0,5 (trung bình) | 63 học sinh | 245 học sinh, khoảng 9 lớp |
  | 0,3 (nhỏ) | 175 học sinh | 683 học sinh, khoảng 23 lớp |

  ICC (mức giống nhau giữa học sinh cùng lớp) là giả định; hãy lấy ICC thực từ điểm trước thử nghiệm để tính lại. **Thử nghiệm thử với 2
  đến 4 lớp chỉ đủ để kiểm tra khả thi và ước lượng độ biến thiên, không đủ để kết luận có hay không có khác biệt.**
- **Hai dạng đề song song (A, B)** trong `docs/bo-cau-hoi-kiem-tra.json`: chia đôi mỗi lớp, nửa làm A trước và B sau, nửa làm B trước và A sau,
  để học sinh không nhớ đáp án và để kiểm tra hai dạng có độ khó tương đương.

## 3. Quy trình

| Thời điểm | Việc làm |
|---|---|
| Tuần 0 | Xin phép nhà trường, phụ huynh. Làm bài kiểm tra trước (15 phút). Ghi mã học sinh (không ghi tên vào tệp dữ liệu). |
| Tuần 1 | 2 tiết học cùng giáo án; nhóm CV dùng CHEM VISION và bộ thẻ in sẵn, nhóm BQ dùng mô hình bi–que. Một quan sát viên điền phiếu trung thực thực hiện. |
| Tuần 1 (cuối) | Bài kiểm tra sau (15 phút) và phiếu khảo sát thái độ 5 câu (thang 1 đến 5). |
| Tuần 5 đến 6 | Bài kiểm tra muộn (dạng chưa dùng) để xem kiến thức còn lại. |

**Phiếu trung thực thực hiện** (mỗi tiết): thời lượng thực tế, số nhóm, số lần công cụ lỗi hoặc phải làm lại, giáo viên có giải thích thêm ngoài giáo án không.
Nếu nhóm CV hay gặp lỗi kĩ thuật thì kết quả phản ánh sản phẩm chưa ổn chứ không phản ánh phương pháp.

## 4. Đo lường

- **Chính:** điểm bài kiểm tra sau (0 đến 8), điều chỉnh theo điểm trước.
- **Phụ:** điểm từng kĩ năng (công thức, hóa trị, phân tử khối, phân tử, liên kết, ion, cấu trúc); thái độ; điểm muộn.
- **Từ nhật ký CHEM VISION** (nhóm CV): số lượt mỗi nhóm cần để ghép đúng, loại lỗi hay gặp. Dữ liệu này mô tả quá trình học, không dùng để so sánh với nhóm BQ.

## 5. Kế hoạch phân tích

Đặt trước khi có dữ liệu, tránh chọn kiểu phân tích sau khi thấy kết quả:

1. **Phân tích chính:** ANCOVA, điểm sau theo điểm trước và nhóm, sai số chuẩn theo cụm lớp. Báo cáo chênh lệch điều chỉnh và khoảng tin cậy 95%.
2. **Phân tích phụ:** t Welch và Hedges g trên mức tăng điểm; từng kĩ năng; điểm muộn.
3. Chạy: `python scripts/analyze_experiment.py du_lieu.csv`, tệp CSV có cột `lop, nhom, diem_truoc, diem_sau` (và `diem_sau_muon` nếu có); `nhom` là `CV` hoặc `BQ`.
4. Nếu muốn khẳng định hai cách "tương đương", cần đặt trước một **biên tương đương** (ví dụ 0,5 điểm) và kiểm định tương đương;
   p lớn thì chỉ nói được là chưa đủ bằng chứng về khác biệt, không phải bằng chứng hai cách bằng nhau.
5. Dưới 4 lớp thì sai số chuẩn theo cụm không đáng tin; công cụ sẽ cảnh báo.

## 6. Đạo đức và dữ liệu

- Xin phép nhà trường và có sự đồng ý của phụ huynh; học sinh được quyền không tham gia mà không bị ảnh hưởng.
- Không chụp ảnh khuôn mặt học sinh; khung hình camera chỉ chứa thẻ và mặt bàn. Nhật ký lớp học chỉ lưu nhãn nhóm, không lưu tên.
- Tệp dữ liệu dùng mã học sinh, không ghi tên; cất bảng đối chiếu mã và tên ở nơi riêng, xóa sau khi phân tích xong.
- Ảnh thẻ được gửi tới Google khi dùng nhận diện bằng AI; thẻ có mã đánh dấu thì đọc ngay trên máy, không gửi ảnh đi. Nên dùng thẻ có mã khi thử nghiệm ở trường.

## 7. Mối đe dọa đến độ tin cậy

| Mối đe dọa | Cách giảm |
|---|---|
| Lớp khác nhau về trình độ | Chia ngẫu nhiên theo lớp; điều chỉnh theo điểm trước; đủ số lớp |
| Giáo viên khác nhau | Một giáo viên dạy cả hai nhóm nếu có thể; cùng giáo án |
| Hiệu ứng mới lạ (học sinh hứng thú vì công cụ mới) | Điểm muộn sau 4 đến 6 tuần; nhóm BQ cũng dùng vật thật |
| Đề kiểm tra thiên vị công cụ CV | Đề không nhắc tới công cụ; hai dạng song song; nhờ giáo viên khác duyệt đề |
| Lỗi kĩ thuật ở nhóm CV | Phiếu trung thực thực hiện; ghi nhận riêng |
| Mất học sinh giữa chừng | Ghi số mất mẫu theo nhóm; báo cáo trung thực |
| Cỡ mẫu nhỏ | Nêu rõ đây là thử nghiệm thử; không kết luận mạnh |

## 8. Việc cần làm trước khi bắt đầu

1. In bộ thẻ (`public/the-in/bo-the-lop-7.pdf`), cắt, ép nhựa.
2. Nhờ giáo viên khác duyệt bộ câu hỏi; làm thử với 5 đến 10 học sinh để bỏ câu quá dễ hoặc quá khó.
3. Xin phép và thống nhất lịch với nhà trường.
4. Quyết định số lớp theo bảng cỡ mẫu và khả năng thực tế.
