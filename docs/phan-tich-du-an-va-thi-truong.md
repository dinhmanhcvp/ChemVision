# CHEM VISION: phân tích dự án, thị trường và hướng phát triển

Tài liệu này gồm ba phần: (1) CHEM VISION là gì, phục vụ ai, giải quyết bài toán nào; (2) các sản phẩm tương tự
đang có; (3) những gì nên kế thừa, khắc phục và bổ sung. Mọi nhận định về thị trường đều ghi nguồn ở cuối; chỗ nào
chưa kiểm chứng được thì ghi rõ.

## 1. Phân tích dự án

### 1.1. Đối tượng người dùng

| Nhóm | Vai trò | Họ cần gì |
|---|---|---|
| **Giáo viên Khoa học tự nhiên lớp 7** (THCS) | người dùng chính, ra quyết định dùng | kiểm tra nhanh nhiều nhóm cùng lúc, biết lớp hay sai ở đâu, ít chuẩn bị |
| **Học sinh lớp 7** | người dùng trực tiếp | thấy, chạm được phân tử; biết ngay mình ghép đúng hay sai và sai ở đâu |
| **Nhà trường / tổ chuyên môn** | người mua, người duyệt | chi phí thấp, chạy trên máy tính hoặc điện thoại có sẵn, dữ liệu học sinh an toàn |
| Phụ huynh, gia sư, câu lạc bộ STEM | người dùng phụ | học tại nhà, không cần giáo viên chấm |

Chương trình Khoa học tự nhiên lớp 7 có nội dung nguyên tử, nguyên tố, phân tử, liên kết hóa học và công thức hóa học;
đây chính là phạm vi mà cơ sở dữ liệu 31 chất của CHEM VISION bám theo.

### 1.2. Bài toán giải quyết

1. **Nội dung quá trừu tượng.** Phân tử, ion, mạng tinh thể thuộc thế giới vi mô, học sinh không nhìn thấy. Các nghiên cứu về
   quan niệm sai trong hóa học nhắc đi nhắc lại điều này.
2. **Lớp đông, giáo viên không phản hồi kịp.** Khi nhiều nhóm cùng ghép thẻ, giáo viên không thể xem từng nhóm ngay lúc đó.
3. **Cách kiểm tra cũ có hạn chế.** Nhập công thức vào phần mềm thì học sinh phải biết đáp án trước, và chỉ so được số nguyên tử chứ
   không biết các nguyên tử nối đúng cách chưa (đây là lý do đề tài chuyển sang nhận diện cấu trúc).
4. **Thiếu thiết bị thí nghiệm ở nhiều trường.** Một nghiên cứu về dạy học Sinh học THCS ở Việt Nam ghi nhận việc chuẩn bị thí nghiệm
   còn gặp nhiều khó khăn do chưa đủ trang thiết bị; các phần mềm thí nghiệm ảo thường là hướng thay thế.

### 1.3. Giải quyết bằng cách nào

```
Học sinh ghép thẻ ─▶ camera/ảnh ─▶ Gemini đọc ký hiệu + khung bao từng thẻ
                                        │
                                        ▼
                OpenCV đo khe hở mặt bàn ─▶ thẻ nào chạm thẻ nào (đồ thị)
                                        │
                                        ▼
        Đối sánh đồ thị với 31 chất ─▶ khớp / sai liên kết (nêu liên kết thừa, thiếu) / ghép dở / không nhận ra
                                        │
                                        ▼
        Gợi ý "Có phải bạn muốn ghép …?" · điểm thử thách · nhật ký lớp · báo cáo lỗi thường gặp
```

Nguyên tắc cốt lõi: **AI chỉ "nhìn", phần mềm "kết luận"**. Kết luận đúng sai là thuật toán xác định, giải thích được, không phụ
thuộc việc AI "nghĩ" gì; prompt không chứa công thức nên AI không bị gợi ý đáp án.

### 1.4. Vì sao cần CHEM VISION (khác gì các lựa chọn khác)

Điểm khác biệt nằm ở **tổ hợp** các yếu tố sau, mỗi sản phẩm khác thường chỉ có một phần:

- thẻ rẻ, in được, thao tác bằng tay (học sinh được "chạm" phân tử);
- kiểm tra **cấu trúc** (kể cả đồng phân, sai liên kết), không chỉ đếm nguyên tử;
- phản hồi tức thì, nói rõ **sai ở đâu** và gợi ý chất gần nhất;
- giáo viên có **nhật ký và báo cáo lỗi thường gặp**;
- chạy bằng camera/trình duyệt có sẵn, không cần thiết bị đặc biệt hay thuê bao, giao diện tiếng Việt, bám chương trình lớp 7.

**Lưu ý trung thực về bằng chứng:** các thử nghiệm với công cụ kiểu "vật thật + camera" cho kết quả học tập **tương đương** mô hình bi–que
truyền thống chứ không vượt trội (xem mục 2). Vì vậy giá trị của CHEM VISION nên được trình bày là *phản hồi tức thì, chi phí thấp, dữ liệu cho giáo viên*,
không nên khẳng định "học tốt hơn" khi chưa có thử nghiệm của chính dự án.

### 1.5. Điểm yếu hiện tại của chính CHEM VISION

| # | Điểm yếu | Mức độ |
|---|---|---|
| 1 | Độ chính xác của Gemini với thẻ thật **chưa đo**; ảnh nhiều thẻ chồng nhau cho kết quả không ổn định giữa các lần chạy | cao |
| 2 | Phụ thuộc Internet, khóa API, hạn mức; tên model Google đổi theo thời gian (đã gặp một model bị gỡ) | cao |
| 3 | Ảnh gửi ra dịch vụ ngoài: cần chính sách quyền riêng tư của trường | trung bình |
| 4 | Chưa phân biệt bậc liên kết; hợp chất ion (NaCl, CaO…) dùng quy ước "ghép cặp", **có nguy cơ củng cố quan niệm sai** rằng mọi chất đều là phân tử (nghiên cứu ghi nhận học sinh thường gán cấu trúc phân tử cho cả hợp chất ion) | trung bình |
| 5 | Mới có 31 chất; chưa có bộ thẻ vật lý chuẩn, chưa thử với học sinh | trung bình |
| 6 | Chưa có kiểm tra chất lượng ảnh trước khi gửi (tối, mờ, lóa) | trung bình |
| 7 | Nhật ký bản web chỉ nằm trong trình duyệt, không đồng bộ giữa máy hay giữa các nhóm | thấp |

## 2. Các sản phẩm hiện có

| Sản phẩm | Cách làm | Điểm mạnh | Điểm yếu / rủi ro |
|---|---|---|---|
| **Happy Atoms** (Schell Games, 2016) | bộ nguyên tử nhựa có nam châm, mỗi nguyên tử mang mã nhận dạng; chụp phân tử bằng ứng dụng để nhận diện | thử nghiệm ngẫu nhiên 1.795 học sinh (2017–2018): kết quả ngang nhóm dùng mô hình vật lý do giáo viên giỏi dạy; ứng dụng miễn phí; có bản 2D rẻ hơn (2022); báo cho học sinh biết phân tử "không tồn tại"; có tài liệu theo chuẩn | giá cao hơn bộ mô hình thường (khoảng 25 USD); đánh giá nhận xét ứng dụng "khó tính" khi quét, cần nền trắng; thiết kế cho trung học phổ thông, tiếng Anh; ứng dụng lần cập nhật cuối ghi nhận năm 2021 (nguồn bên thứ ba, có thể đã cũ) |
| **Osmo** (Tangible Play) | gương nhỏ gắn lên camera máy tính bảng, "Reflective AI" đọc quân cờ vật lý | thao tác vật thật, phản hồi tức thì, chứng minh được mô hình "vật thật + camera" | cần ánh sáng tốt, bề mặt sạch, vân bàn làm nhiễu; cần thiết bị riêng và bộ khởi đầu (từ khoảng 80 bảng Anh); không chuyên hóa học; tình trạng công ty chưa kiểm chứng |
| **PhET** (ĐH Colorado) | mô phỏng trên màn hình, có "Build a Molecule" (phân tử, công thức, đồng phân) | miễn phí, hơn 100 mô phỏng, có bản tiếng Việt, được giáo viên Việt Nam dùng nhiều | thuần màn hình, không có vật thật; hai trang chính của PhET tôi không đọc được nội dung chi tiết nên tính năng cụ thể chưa kiểm chứng |
| **Merge Cube / Merge EDU** | khối lập phương thực tế tăng cường (AR), xem vật thể 3D | trực quan 3D | cần đăng ký trả phí để xem đủ nội dung; độ tuổi áp dụng mỗi nguồn ghi một khác (K-8 hoặc K-12); bằng chứng học tập chỉ là nghiên cứu nhỏ ở đại học |
| **Labster** | phòng thí nghiệm ảo, hơn 300 mô phỏng | tăng hứng thú, tiết kiệm hóa chất, tích hợp LMS | giá theo hợp đồng, bị nhận xét đắt với trường nhỏ; thường chỉ bổ sung chứ không thay thực hành |
| **Bộ mô hình bi–que truyền thống** | nhựa/gỗ | rẻ, bền, không cần điện | không có phản hồi, giáo viên phải tự kiểm; số mảnh hạn chế |
| **Phần mềm thí nghiệm ảo phổ biến ở Việt Nam** (Yenka, ChemLab…) | mô phỏng thí nghiệm | giảm hóa chất, an toàn | một số có phí; nguồn giới thiệu mang tính quảng cáo; chưa thấy nghiên cứu về mức phù hợp với KHTN lớp 7 |

Kết quả nghiên cứu chung đáng chú ý:

- Công cụ giao diện hữu hình hoặc AR cho kết quả học tập **tương đương** mô hình bi–que, nhưng người dùng đánh giá **dễ dùng, dễ học hơn**.
- Mô hình vật lý có ưu thế cảm giác tay và phản hồi một phần; AR cần tái tạo được điều đó.
- Mô hình vật lý bị nhận xét cồng kềnh, đắt và bị giới hạn bởi số mảnh trong bộ.

## 3. Kế thừa, khắc phục và ý tưởng mới

### 3.1. Điểm mạnh nên kế thừa

| Từ | Kế thừa gì | Áp dụng vào CHEM VISION |
|---|---|---|
| Happy Atoms | **mã nhận dạng trên từng thẻ**, báo "phân tử không tồn tại", tài liệu theo chuẩn, thử nghiệm có đối chứng | dùng mã đánh dấu (ArUco) cho nhận diện; thông báo "tổ hợp này không phải chất nào trong chương trình"; viết giáo án; thiết kế thử nghiệm đối chứng |
| Osmo | thao tác tự nhiên, phản hồi tức thì, hướng dẫn đặt thiết bị/ánh sáng | màn hình hướng dẫn đặt camera, nền trắng, đủ sáng |
| PhET | miễn phí, tiếng Việt, kèm phiếu học tập | giữ miễn phí; kèm phiếu học tập in được |
| Labster | báo cáo cho giáo viên, tích hợp lớp học | nhật ký, báo cáo và bảng theo dõi cả lớp |
| Mô hình bi–que | rẻ, bền, thao tác tay | bộ thẻ in được trên giấy, thẻ nhựa tự làm |

### 3.2. Điểm yếu cần tránh hoặc khắc phục

| Điểm yếu của đối thủ | Cách CHEM VISION khắc phục |
|---|---|
| Quét "khó tính", cần điều kiện ánh sáng (Happy Atoms, Osmo) | kiểm tra chất lượng ảnh trước khi gửi và hướng dẫn trực tiếp; nhận diện bằng mã đánh dấu, ít phụ thuộc ánh sáng |
| Phần cứng/bộ thẻ đắt (Happy Atoms, Osmo) | thẻ in được từ PDF; chạy bằng camera hoặc điện thoại có sẵn |
| Thuê bao, giá theo hợp đồng (Merge, Labster) | miễn phí, mã nguồn mở, tự triển khai |
| Chỉ có tiếng Anh, thiết kế cho cấp khác | tiếng Việt, bám KHTN lớp 7 |
| Thuần màn hình, thiếu vật thật (PhET, Labster) | giữ thao tác vật thật làm trung tâm |
| Phụ thuộc một nhà cung cấp AI | mã đánh dấu làm đường chính; Gemini chỉ là phương án dự phòng cho thẻ chưa có mã |

### 3.3. Ý tưởng tích hợp thêm, xếp theo giá trị và độ khả thi

| # | Ý tưởng | Giải quyết | Công sức | Giá trị |
|---|---|---|---|---|
| 1 | **Nhận diện bằng mã đánh dấu (ArUco) làm chế độ chính, Gemini dự phòng.** Mỗi thẻ in kèm một mã nhỏ; OpenCV đọc mã và vị trí ngay trên máy: chạy ngoại tuyến, miễn phí, tức thì, không ảnh gửi ra ngoài. Đã kiểm tra: OpenCV đang dùng đọc đúng mã thử | điểm yếu #1, #2, #3, #6 | vừa | **rất cao** |
| 2 | **Chất lượng ảnh và hướng dẫn đặt thẻ:** đo độ sáng, độ nét, lóa ngay trên khung hình trực tiếp, cảnh báo trước khi gửi | #6, gánh nặng "quét khó tính" | thấp | cao |
| 3 | **Bộ thẻ in được:** tạo PDF thẻ lục giác (khổ A4, kèm mã, màu theo nguyên tố) và hướng dẫn cắt, ép | #5, chi phí | thấp | cao |
| 4 | **Phân loại liên kết ion và cộng hóa trị** trong kết quả: hợp chất ion hiển thị chú thích "quy ước ghép cặp, thực tế là mạng tinh thể", nét liên kết khác nhau | #4, quan niệm sai | thấp | cao |
| 5 | **Hóa trị và phân tử khối:** hiển thị hóa trị còn thiếu của từng thẻ, tự tính phân tử khối của chất ghép được; chế độ "lập công thức theo hóa trị" (bám nội dung lớp 7) | bám chương trình | thấp đến vừa | cao |
| 6 | **Bảng điều khiển cả lớp:** mỗi nhóm vào bằng mã lớp, giáo viên xem nhóm nào đã xong, nhóm nào kẹt, câu nào sai nhiều (cần lưu trữ phía máy chủ) | #7, phản hồi cả lớp | cao | cao |
| 7 | **Gắn lỗi với quan niệm sai:** mỗi kiểu lỗi (nối H–H, coi NaCl là phân tử…) kèm gợi ý sửa cho giáo viên | báo cáo có hành động | vừa | vừa |
| 8 | **Giải thích vì sao sai bằng ngôn ngữ lớp 7:** lấy chẩn đoán xác định của phần mềm làm nền, nhờ AI diễn đạt lại dễ hiểu (giữ nguyên tắc "kết luận do phần mềm") | phản hồi dễ hiểu | vừa | vừa |
| 9 | **Mở rộng sang lớp 8:** phản ứng hóa học, cân bằng phương trình bằng thẻ | mở rộng thị trường | cao | vừa, làm sau |
| 10 | **Thử nghiệm có đối chứng** ở 2 đến 4 lớp (nhóm dùng CHEM VISION và nhóm mô hình bi–que), đo bằng bài kiểm tra trước và sau | bằng chứng cho giá trị thật | vừa | **rất cao khi bảo vệ dự án** |

### 3.3b. Tình trạng thực hiện các ý tưởng (cập nhật)

| # | Ý tưởng | Tình trạng |
|---|---|---|
| 1 | Mã đánh dấu ArUco, Gemini dự phòng | **Đã làm và kiểm thử tự động** (đọc 22 nguyên tố, vòng in thẻ rồi đọc lại); chưa thử với thẻ in thật chụp bằng điện thoại |
| 2 | Kiểm tra chất lượng ảnh | **Đã làm** (trên camera trực tiếp và ở máy chủ, ngưỡng chọn theo ảnh thật) |
| 3 | Bộ thẻ in được | **Đã làm** (PDF lớp 7, 8, 9); chưa in thử ra giấy |
| 4 | Liên kết ion và cộng hóa trị | **Đã làm** (chú thích, nét đứt trên ảnh, giải thích) |
| 5 | Hóa trị và phân tử khối | **Đã làm** (phân tử khối, đề "lập công thức theo hóa trị") |
| 6 | Bảng điều khiển cả lớp | **Đã làm**; kiểm thử với kho trong bộ nhớ và lệnh Upstash giả, **chưa thử với Upstash thật** |
| 7 | Gắn lỗi với quan niệm sai | **Đã làm** (báo cáo giáo viên và bảng lớp có cách xử lý) |
| 8 | Giải thích vì sao sai | **Đã làm bằng chẩn đoán xác định**, chưa dùng AI diễn đạt lại (cố ý, để giữ nguyên tắc "phần mềm kết luận") |
| 9 | Mở rộng sang lớp 8, 9 | **Đã làm**: 70 chất theo lớp, 24 phương trình cân bằng; chưa có glucozơ và polime |
| 10 | Thử nghiệm đối chứng | **Đã chuẩn bị** (thiết kế, bộ câu hỏi, công cụ phân tích); **chưa tiến hành thử nghiệm nào** |

### 3.4. Thứ tự đề xuất

1. **Ngay (tuần này):** ý tưởng 2, 3, 4, và việc đo độ chính xác Gemini trên bộ ảnh có đáp án (cần ảnh ghép thật).
2. **Tiếp theo:** ý tưởng 1 (mã đánh dấu) và 5 (hóa trị, phân tử khối).
3. **Sau khi có thẻ thật và dùng thử:** ý tưởng 10, rồi 6 và 7.
4. **Tùy hướng đi:** 8 và 9.

## 4. Giới hạn của bản phân tích này

- Tôi không đọc được nhiều trang nguồn đầy đủ (trang đánh giá của Common Sense trả lỗi 403, trang mô phỏng PhET chỉ cho tiêu đề), nên một
  số nhận xét lấy từ đoạn trích của kết quả tìm kiếm và đã đánh dấu là thứ cấp.
- Phần lớn nghiên cứu về giao diện hữu hình/AR trong hóa học là nghiên cứu nhỏ, nhiều nghiên cứu ở bậc đại học hoặc trung học phổ thông, không phải THCS.
- Giá bán, tình trạng công ty và ngày cập nhật ứng dụng cần xác minh trực tiếp ở nhà cung cấp trước khi trích dẫn ra ngoài.
- Chưa có số liệu về mức độ phổ biến của từng sản phẩm tại Việt Nam.

## Nguồn

- Happy Atoms: [IES SBIR](https://ies.ed.gov/funding/research/programs/small-business-innovation-research-sbir/sbir-success-stories/success-stories-out-of-the-ed-ies-sbir-program-schell-games-happy-atoms), [Schell Games](https://www.schellgames.com/games/happy-atoms), [STEMfinity](https://stemfinity.com/products/happy-atoms-complete-set), [bản 2D](https://legacymicrosites.schellgames.com/blog/schell-games-and-thames-kosmos-announce-new-2d-version-of-the-award-winning-happy-atoms-chemistry-learning-tool), [Common Sense Education](https://www.commonsense.org/education/app/happy-atoms)
- Osmo: [EdSurge](https://www.edsurge.com/n/2014-05-22-tangible-play-launches-crowdfunding-campaign-to-bridge-digital-and-physical-fun), [iMore](https://www.imore.com/osmo-game-ipad-hands-on), [TechCrunch](https://techcrunch.com/2019/06/24/byjus-owned-osmo-education-startup-enters-pre-schoolers-market/), [trang Osmo](https://playosmo.com/en-GB)
- Merge: [Merge EDU](https://mergeedu.com/merge-cube), [nghiên cứu ĐH Iowa](https://iro.uiowa.edu/esploro/outputs/journalArticle/Visualizing-3D-Objects-in-Analytical-Chemistry/9984539759902771)
- Labster: [bảng giá](https://www.labster.com/es/precios), [G2](https://www.g2.com/products/labster/reviews_and_filters), [FitGap](https://us.fitgap.com/products/labster), [Lumen Learning](https://courses.lumenlearning.com/chemistryformajors/chapter/virtual-lab-recommendations/)
- PhET và Việt Nam: [Build a Molecule](https://phet.colorado.edu/en/simulations/build-a-molecule), [PhET trong dạy học KHTN](https://vjol.vista.gov.vn/tctbgd/article/view/100059), [phần mềm thí nghiệm ảo hóa học](https://mytour.vn/vi/blog/kinh-nghiem-hay/top-7-phan-mem-thi-nghiem-ao-hoa-hoc-tot-nhat-nam-2025-mytour.html)
- AR và giao diện hữu hình: [ĐH Waterloo](https://uwaterloo.ca/chemistry/news/app-visualizing-chemistry), [ASU AR-some](https://meteor.ame.asu.edu/airtable-media/publications/publications-pdfs/arsomechem.pdf), [Augmented Chemistry](https://research.chalmers.se/en/publication/24633), [AR và hiểu biết 3D](https://www.scitepress.org/Papers/2013/43495/)
- Quan niệm sai về liên kết hóa học: [RSC](https://edu.rsc.org/structure-and-bonding/students-ideas-about-chemical-bonding-beyond-appearances/4017806.article), [CHIMIA](https://chimia.ch/chimia/article/download/2023_679/6320/21296), [Weizmann](https://stwww1.weizmann.ac.il/chemistry/wp-content/uploads/sites/4/2016/05/CERP.pdf)
