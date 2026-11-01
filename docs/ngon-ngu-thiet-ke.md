# Ngôn ngữ thiết kế Chem Vision: "phiếu thí nghiệm"

Tài liệu này giải thích vì sao giao diện được thiết kế như hiện tại, dựa trên điều đã biết về tải nhận thức, thiết kế cảm xúc và trò chơi hóa
trong học tập. Chỗ nào bằng chứng còn yếu thì ghi rõ để không đặt cược quá mức vào một chi tiết.

## 0. Vì sao làm lại bản đầu

Bản đầu ("Phòng thí nghiệm của Atom") đúng về nghiên cứu nhưng **rập khuôn**: nút bo tròn có bóng đáy, phông bo tròn, thẻ nào cũng viền xanh nhạt
trên nền chuyển màu xanh tím, linh vật hành tinh có mặt cười, emoji làm biểu tượng (🧪 🎯 ⚖️ …), dải màu tím, hồng, lục lam chỉ để phân biệt bộ đề.
Đó là bộ đồ nghề chung của "ứng dụng học tập" nên không nói gì về sản phẩm này, và emoji còn khác nhau trên mỗi hệ điều hành.
Bản hiện tại giữ các quyết định có căn cứ (một việc chính mỗi màn hình, phản hồi không đổ lỗi, vùng chạm lớn, tương phản AA, không bảng xếp hạng)
nhưng đổi toàn bộ hình thức, lấy chất liệu từ chính thẻ nguyên tố: **hình lục giác, màu CPK, mã vuông, cạnh chạm nhau**.

## 1. Bằng chứng nghiên cứu và điều rút ra

| Điều tìm thấy | Mức tin cậy | Quyết định thiết kế |
|---|---|---|
| **Lý thuyết học qua đa phương tiện (Mayer):** bỏ yếu tố thừa (coherence), dùng dấu hiệu chỉ điểm (signaling), chia nhỏ và để người học tự điều khiển nhịp (segmenting), đặt chữ và hình liên quan cạnh nhau (contiguity). Nguồn là các trang tổng hợp, cần đối chiếu sách gốc khi trích dẫn chính xác | Khá tốt (dựa trên hàng trăm thí nghiệm theo tổng hợp thứ cấp) | Mỗi màn hình một việc chính; kết quả hiện kèm hình ngay cạnh chữ; chi tiết ẩn sau "Vì sao?"; thanh bước 01-02-03 chỉ rõ đang ở đâu; bỏ trang trí không mang thông tin (nền chuyển màu, bóng đổ) |
| **Thiết kế cảm xúc (Brom và cộng sự, 2018, 33 mẫu):** thêm khuôn mặt vào hình và dùng màu dễ chịu tăng nhẹ ghi nhớ (d ≈ 0,39) và hiểu (d ≈ 0,32). **Nhưng riêng nhân hóa khuôn mặt cho kết quả không nhất quán; màu sắc là đòn bẩy đáng tin hơn** | Trung bình, hiệu ứng nhỏ | **Bỏ linh vật có mặt.** Dùng nền giấy ấm, tương phản tốt; màu chỉ xuất hiện khi mang thông tin. Cảm xúc đến từ con dấu kết quả và lời phản hồi chứ không từ khuôn mặt |
| **Trò chơi hóa:** điểm, huy hiệu, bảng xếp hạng ít ảnh hưởng trực tiếp đến kết quả học, nhưng có thể giúp động lực; thiết kế dựa trên cốt truyện và cấp độ cho kết quả tốt hơn; học sinh phổ thông hưởng lợi nhiều hơn đại học; có dấu hiệu thiên lệch xuất bản nên con số chỉ mang tính tạm thời | Trung bình đến thấp | Dùng **nhiệm vụ theo lớp** và **tổ ong** (mỗi chất một ô lục giác, đầy dần) thay cho bảng xếp hạng; sao và huy hiệu chỉ để ghi nhận tiến bộ cá nhân; **không có bảng xếp hạng, đồng hồ đếm ngược hay "mất chuỗi"** |
| **Phản hồi vi mô kiểu Duolingo:** khen cả nỗ lực, không chỉ đáp án đúng; chuyển động nhỏ ăn mừng tiến bộ. Nguồn chủ yếu là bình luận thiết kế; các số liệu thống kê lưu hành trên mạng không được kiểm chứng nên **không dùng** | Thấp đến trung bình (kinh nghiệm thiết kế) | Giữ **nguyên tắc** (lời phản hồi không đổ lỗi: "Gần đúng rồi!"; hiệu ứng ngắn, tắt được) nhưng **không bắt chước hình thức** (nút bóng đáy, phông bo tròn, linh vật), vì đó là bản sắc của một thương hiệu khác và dễ bị đọc là trẻ con với học sinh THCS |
| **Giao diện cho trẻ:** trẻ trượt mục tiêu chạm nhiều hơn người lớn, nhất là mục tiêu nhỏ (nghiên cứu về trẻ 7 đến 10 tuổi); WCAG 2.2 tối thiểu 24 px, thông lệ di động 44 px; tương phản chữ tối thiểu 4,5:1. **Bằng chứng riêng cho lứa 10 đến 14 tuổi mỏng**, các con số cỡ chữ không thống nhất | Thấp cho lứa tuổi này | Mục tiêu chạm tối thiểu 48 px; chữ nền 17 px; tương phản AA ở cả nền sáng và tối (có kiểm thử tự động); tôn trọng `prefers-reduced-motion`; **cần thử với học sinh thật** trước khi coi là đạt |

Nguồn: [Mayer, nguyên tắc đa phương tiện](https://edtechbooks.org/designing_transmedia_learning_environments/principles_of_multimedia_design) ·
[Brom và cộng sự, thiết kế cảm xúc](https://fis.leuphana.de/en/publications/emotional-design-and-positive-emotions-in-multimedia-learning-an-/) ·
[Tổng quan 2024 về nhân hóa](https://link.springer.com/article/10.1186/s40561-024-00332-7) ·
[Meta-analysis trò chơi hóa](https://repositorio.iscte-iul.pt/handle/10071/29213) ·
[Duolingo, ngôn ngữ thiết kế](https://keplerdesign.substack.com/p/duolingo) ·
[Trẻ em và thao tác chạm](https://lisa-anthony.com/wp-content/uploads/2013/04/anthony-et-al-jpuc2013.pdf).

## 2. Nguyên tắc

1. **Một màn hình, một việc chính.** Học sinh chỉ thấy: nhiệm vụ hiện tại, camera, nút KIỂM TRA, kết quả. Cân bằng phương trình, lớp học, thiết lập nằm ở các thẻ riêng. Mỗi màn hình chỉ có một nút nền đặc.
2. **Nói ít, nói đúng.** Kết quả gồm một câu tiêu đề (tối đa 8 từ) và một câu giải thích (tối đa 20 từ); phần còn lại ẩn sau "Vì sao?". Câu ngắn, từ lớp 6 đến 7. Giọng của một phiếu hướng dẫn, không giả làm bạn chat.
3. **Không đổ lỗi.** "Gần đúng rồi!" thay cho "Sai". Mọi lỗi đều đi kèm bước kế tiếp cụ thể.
4. **Màu là thông tin.** Nền trung tính (giấy, mực); màu chỉ xuất hiện ở ba chỗ: màu CPK của nguyên tố, trạng thái (xanh lá đúng, hổ phách gần đúng, đỏ gạch chưa đúng) và vàng bút dạ để đánh dấu "bạn đang ở đây". Trạng thái **không bao giờ chỉ khác nhau bằng màu**: mỗi trạng thái có hình riêng (tích, xoay lại, chéo).
5. **Người học điều khiển nhịp.** Không tự động chuyển câu; hiệu ứng ngắn và tắt được; không đồng hồ đếm ngược.
6. **Giàn giáo rồi gỡ dần.** Bảng đếm nguyên tố ở mục cân bằng phương trình giúp nhìn thấy chỗ lệch; có thể bỏ qua khi đã quen.
7. **Thưởng cho nỗ lực, không so sánh với người khác.** Sao, tổ ong và huy hiệu chỉ so với chính mình.
8. **Dùng hình ảnh của chính sản phẩm.** Lục giác, cạnh chung, mã vuông, màu CPK xuất hiện ở nhãn hiệu, con dấu, thẻ nguyên tố, tiến độ, huy hiệu, nền camera và pháo giấy; không dùng minh họa chung chung.

## 3. Nhận diện thị giác

- **Màu nền và mực:** giấy ấm `#f3f0e8`, mặt thẻ `#fffefa`, mực `#1d1c19`, chữ phụ `#5b584e`, đường kẻ `#d9d3c4`. Chế độ tối dùng nền nâu đen ấm `#14130f` chứ không dùng xanh đêm.
- **Màu có nghĩa:** vàng bút dạ `#f2cf3d` (thẻ đang chọn, số sao, góc ngắm camera); xanh lá `#17653a` đúng; hổ phách `#7a4b00` gần đúng; đỏ gạch `#a3281a` chưa đúng. Mọi cặp chữ/nền đạt AA (4,5:1) ở cả hai nền, kiểm bằng `test_ui_wiring.py`.
- **Màu nguyên tố:** theo quy ước CPK (đã dùng cho thẻ in) nên thẻ in và giao diện nói cùng một ngôn ngữ.
- **Chữ:** ba giọng. Tiêu đề, công thức và tên chất dùng chữ có chân hệ thống (Iowan Old Style, Palatino, Noto Serif hoặc Georgia); nhãn, số liệu và mã lớp dùng chữ đơn cách (ui-monospace, Cascadia Mono, Consolas); thân chữ dùng chữ không chân của hệ thống, cỡ 17 px. Không tải phông ngoài để giữ CSP chặt. Công thức hóa học luôn có chỉ số dưới đúng (H₂O).
- **Hình khối:** góc bo nhỏ (6 đến 10 px), đường kẻ mảnh 1 px thay cho bóng đổ; phân cấp bằng cỡ chữ và khoảng trống, không bằng hộp lồng hộp. Không dùng nền chuyển màu hay nút bóng đáy (có kiểm thử để không quay lại).
- **Lục giác:** nhãn hiệu (thẻ có mã vuông 3×3 ở giữa, giống thẻ in), con dấu kết quả (5 trạng thái), thẻ nguyên tố tô màu CPK, chấm tiến độ nhiệm vụ, tổ ong trên mỗi bộ đề, khung huy hiệu, nền tổ ong của khung camera, mảnh pháo giấy.
- **Biểu tượng:** 27 biểu tượng nét mảnh vẽ bằng SVG, nạp bằng mặt nạ CSS nên cùng màu với chữ; **không dùng emoji** (kiểm thử tự động chặn).
- **Minh họa:** phân tử nước ghép từ ba thẻ H–O–H, cạnh chung tô vàng, dùng ở lời chào và khung camera trống để giải thích luật ghép mà không cần chữ.
- **Chuyển động:** 150 đến 250 ms; con dấu "đóng" xuống mỗi lần có kết quả mới; pháo giấy 1,4 giây; tắt hoàn toàn khi hệ điều hành bật "giảm chuyển động" hoặc khi người dùng tắt hiệu ứng.
- **Âm thanh:** tiếng "ting" ngắn tạo bằng Web Audio, **tắt theo mặc định**.

## 4. Cấu trúc thông tin

| Thẻ | Dành cho | Nội dung |
|---|---|---|
| Ghép thẻ | mọi người | nhiệm vụ hiện tại, camera, KIỂM TRA, kết quả |
| Thử thách | học sinh | chọn lớp, bộ đề, tổ ong, sao đã đạt, huy hiệu |
| Cân bằng | học sinh lớp 8 | phương trình, bảng đếm nguyên tố |
| Lớp học | giáo viên và nhóm | tạo lớp, vào lớp, bảng điều khiển |
| Thêm | giáo viên, người quản lý | mã truy cập, tên nhóm, hiệu ứng, thẻ in, nhật ký, chạy thử |

## 5. Phần thưởng và cấp độ

- **Sao (1 đến 3) cho mỗi câu giải đúng:** 3 sao nếu đạt từ 9 điểm, 2 sao từ 6 điểm, còn lại 1 sao; giữ kết quả tốt nhất của từng chất, nên làm lại để cải thiện chứ không "cày".
- **Tổ ong:** mỗi bộ đề là một dãy ô lục giác, một ô một chất. Xám nhạt: chưa làm; viền đen: 1 sao; đen đặc: 2 sao; tâm vàng: 3 sao. Mức tô khác nhau bằng hình, không chỉ bằng độ đậm.
- **Huy hiệu** (5 cái): mảnh ghép đầu tiên, thợ ghép (5 chất), hoàn thành bộ đề, nhà cân bằng, bậc thầy phương trình (10 phương trình). Hiện một lần, không gây áp lực.
- Dữ liệu chỉ lưu trong trình duyệt; không có bảng xếp hạng.

## 6. Điều chưa kiểm chứng

Giao diện được thử bằng trình duyệt tự động ở khung máy tính, điện thoại (390 và 320 px), chế độ sáng và tối; **chưa thử với học sinh thật** và chưa thử trên điện thoại thật.
Việc bản mới "bớt rập khuôn" là đánh giá thẩm mỹ của người thiết kế, không đo được. Hiệu quả của con dấu, tổ ong, màu sắc và sao với sự hứng thú, tải nhận thức chỉ được đánh giá là hợp lý theo nghiên cứu ở trên.
Hai rủi ro cần quan sát: (1) học sinh nhỏ có thể thấy phong cách giấy và chữ có chân "nghiêm" hơn bản trước; (2) phông chữ phụ thuộc hệ điều hành nên hình dáng chữ khác nhau giữa Windows, Android và iOS.
Nên thử với 5 đến 8 học sinh (quan sát có nói to suy nghĩ) rồi chỉnh trước khi triển khai rộng.
