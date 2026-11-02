"""Dựng báo cáo KHKT (docs/bao-cao/khkt/BAO_CAO_KHKT_CHEM_VISION.docx) theo khung mẫu báo cáo khoa học kỹ thuật.

Dùng lại các hàm định dạng của build_docx.py; số liệu lấy từ do_luong.json (chạy do_luong.py trước), hình từ khkt_charts.py.
"""
import json
import os

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

import build_docx as B
import do_luong  # noqa: F401  (đưa thư mục dự án vào sys.path để import chem_vision)
from chem_vision import core, geometry, markers, quality, reactions, recognizer, retry, web
from chem_vision.curriculum import CARD_ELEMENTS

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
KH = os.path.join(ROOT, "docs", "bao-cao", "khkt")
OUT = os.path.join(KH, "BAO_CAO_KHKT_CHEM_VISION.docx")
R = json.load(open(os.path.join(KH, "do_luong.json"), encoding="utf-8"))
vn, para, bullet, h, table, figure = B.vn, B.para, B.bullet, B.h, B.table, B.figure
G, EQ, SC = R["đối sánh đồ thị"], R["cân bằng phương trình"], R["cảnh tổng hợp"]
GEO = R["hình học (đường Gemini)"]
GEO_NOW, GEO_NEW = (GEO[k] for k in GEO)
RATIO_NEW = vn(float(list(GEO)[1].split("=")[1]), 1)
MAX_NOW = vn(geometry.MAX_RATIO, 1)
row = lambda key, col, v: next(r for r in R[key] if r[col] == v)
N_IMG = R["kích thước thẻ"][0]["lượt"]


def setup():
    B.doc = Document()
    B.FIG = os.path.join(KH, "hinh")
    B.setup()
    sec = B.doc.sections[0]
    sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.54)   # như mẫu: lề 1 inch
    st = B.doc.styles["Normal"]
    B.set_font(st, 14, color=RGBColor(0x22, 0x22, 0x22))
    for name, size, colour in (("Heading 1", 15, RGBColor(0x00, 0x33, 0x66)), ("Heading 2", 14, RGBColor(0x00, 0x66, 0x99)),
                               ("Heading 3", 14, RGBColor(0x00, 0x66, 0x99))):
        B.set_font(B.doc.styles[name], size, bold=True, color=colour)
    for name in ("List Bullet", "List Number"):
        B.set_font(B.doc.styles[name], 14)


def title_block():
    def c(text, size, bold=True, color=None, after=4):
        para(text, WD_ALIGN_PARAGRAPH.CENTER, size, color, bold, after)
    c("BÁO CÁO KHOA HỌC KỸ THUẬT", 16, color=RGBColor(0x00, 0x33, 0x66), after=8)
    c("DỰ ÁN: CHEM VISION – HỆ THỐNG NHẬN DIỆN VÀ CHẤM CẤU TRÚC PHÂN TỬ TỪ THẺ NGUYÊN TỐ BẰNG THỊ GIÁC MÁY TÍNH "
      "VÀ ĐỐI SÁNH ĐỒ THỊ, HỖ TRỢ DẠY HÓA HỌC THCS", 15, color=RGBColor(0x00, 0x33, 0x66), after=14)
    p = B.doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(ROOT, "docs", "bao-cao", "hinh", "h00_bia.png"), width=Cm(12))
    for line in ("Lĩnh vực dự thi: Phần mềm hệ thống",
                 "Thành viên thực hiện: [Họ và tên 1], [Họ và tên 2], [Họ và tên 3], [Họ và tên 4], [Họ và tên 5]",
                 "Giáo viên hướng dẫn: [Họ và tên]", "Đơn vị: [Trường] – [Tỉnh/thành phố]", "Năm học: 2026–2027"):
        para(line, WD_ALIGN_PARAGRAPH.LEFT, 14, bold=True, space_after=4)
    B.page_break()
    h("MỤC LỤC", 1)
    p = B.doc.add_paragraph(); B.field(p, 'TOC \\o "1-3" \\h \\z \\u')
    para("(Nếu mục lục trống: nhấp chuột phải vào đây, chọn Update Field / Cập nhật trường.)", size=10,
         color=RGBColor(0x6B, 0x72, 0x80))
    B.page_break()


def summary():
    h("TÓM TẮT DỰ ÁN", 1)
    para(f"Trong môn Khoa học tự nhiên THCS, học sinh học về nguyên tử, phân tử và liên kết hóa học bằng cách ghép mô hình, nhưng "
         f"trong một tiết đông học sinh, giáo viên không thể kiểm tra kịp từng nhóm; các phần mềm hiện có chỉ kiểm tra công thức "
         f"(đếm số nguyên tử) nên không phát hiện được lỗi về cách nối các nguyên tử. CHEM VISION giải bài toán này bằng một hệ "
         f"thống hai tầng tách bạch: **tầng nhận diện** đọc các thẻ nguyên tố lục giác trong ảnh camera, ưu tiên bằng mã đánh dấu "
         f"ArUco in trên thẻ (OpenCV, chạy ngoại tuyến), dự phòng bằng mô hình thị giác Gemini kết hợp phân tích hình học khe hở "
         f"giữa các thẻ; **tầng chấm** biểu diễn cụm thẻ thành đồ thị có nhãn và đối sánh đẳng cấu với cơ sở dữ liệu "
         f"{G['chất']} chất (lọc Weisfeiler–Lehman rồi quay lui), từ đó kết luận đúng chất, chỉ ra liên kết thừa hoặc thiếu, "
         f"hoặc gợi ý chất gần nhất. Mọi kết luận và lời giải thích đều do thuật toán xác định sinh ra, không do mô hình ngôn ngữ "
         f"tự suy diễn. Hệ thống còn cân bằng {EQ['phương trình']} phương trình hóa học lớp 8 bằng khử Gauss–Jordan trên số hữu tỉ.")
    para(f"Đánh giá bằng ảnh tổng hợp có biến dạng cho thấy: đối sánh đúng {vn(G['khớp đúng sau hoán vị'], 0)}/"
         f"{vn(G['lượt hoán vị'], 0)} lượt hoán vị nhãn, không khớp nhầm lần nào trong {G['đột biến một liên kết']} cấu trúc sai, "
         f"phân biệt đúng hai cặp đồng phân, thời gian trung vị {vn(G['ms trung vị'], 2)} ms; đường ArUco kết luận đúng chất "
         f"{vn(row('kích thước thẻ', 'cạnh thẻ px', 50)['đúng chất %'], 0)}% khi thẻ rộng từ 42 điểm ảnh, kể cả khi ảnh tối "
         f"còn 15% độ sáng. Nghiên cứu cũng phát hiện và định lượng một lỗi ngưỡng ở đường hình học: hạ ngưỡng khoảng cách từ "
         f"{MAX_NOW} xuống {RATIO_NEW} làm số phân tử kết luận đúng trên nền gỗ tăng từ "
         f"{GEO_NOW['gỗ sáng']['đúng chất']} lên {GEO_NEW['gỗ sáng']['đúng chất']}/{GEO_NOW['gỗ sáng']['phân tử']}. "
         f"Toàn bộ phép đo dùng ảnh tổng hợp; việc kiểm chứng với ảnh chụp thẻ in thật và với học sinh là bước tiếp theo.")


def chapter1():
    h("Chương 1: LÝ DO CHỌN DỰ ÁN", 1)
    h("1.1. Thực trạng và hạn chế của cách kiểm tra hiện nay", 2)
    para("Chương trình Giáo dục phổ thông 2018 đưa nội dung nguyên tử, phân tử, liên kết hóa học và công thức hóa học vào môn Khoa "
         "học tự nhiên lớp 7, rồi mở rộng sang phản ứng hóa học ở lớp 8 và hợp chất hữu cơ ở lớp 9. Đây là kiến thức thuộc thế giới vi "
         "mô, học sinh không quan sát trực tiếp được, nên mô hình ghép (bi–que, thẻ) là học cụ quen thuộc. Khi dạy bằng mô hình, nhóm "
         "nhận thấy bốn hạn chế:")
    bullet("**Phản hồi chậm:** một giáo viên phải kiểm tra 8 đến 10 nhóm trong một tiết 45 phút; lỗi sai thường chỉ được phát hiện ở "
           "bài kiểm tra.")
    bullet("**Kiểm tra công thức thay vì cấu trúc:** phần mềm nhập công thức chỉ so số nguyên tử. Etanol C₂H₅OH và đimetyl ete "
           "CH₃OCH₃ có cùng thành phần 2C, 6H, 1O nhưng là hai chất khác nhau; một mô hình nối H với H vẫn có \"đúng\" hai H và một O.")
    bullet("**AI tạo sinh dễ đoán bừa:** hỏi trực tiếp một mô hình ngôn ngữ \"đây là chất gì\" có thể cho câu trả lời trôi chảy nhưng "
           "không kiểm chứng được, và kết quả có thể khác nhau giữa các lần hỏi.")
    bullet("**Chi phí và hạ tầng:** bộ mô hình chuyên dụng có giá cao, số mảnh hạn chế; nhiều trường thiếu thiết bị, mạng yếu.")
    h("1.2. Căn cứ khoa học", 2)
    para("**Phân tử là một đồ thị có nhãn.** Trong hóa học tính toán, một phân tử được biểu diễn bằng đồ thị G = (V, E, ℓ): mỗi đỉnh "
         "v ∈ V là một nguyên tử, mỗi cạnh là một liên kết và ℓ(v) là kí hiệu nguyên tố. Hai cách ghép biểu diễn cùng một chất khi và "
         "chỉ khi hai đồ thị **đẳng cấu có nhãn**: tồn tại song ánh φ: V₁ → V₂ giữ nguyên nhãn và giữ nguyên quan hệ kề. Kiểm tra đẳng "
         "cấu, khác với so thành phần, phân biệt được đồng phân và phát hiện được liên kết sai.")
    para("**Mã đánh dấu chuẩn (fiducial marker).** Mã ArUco là ô vuông đen trắng mã hóa một số hiệu, được thiết kế để phát hiện tin "
         "cậy, có sửa lỗi bit và cho vị trí bốn góc với độ chính xác dưới điểm ảnh (Garrido-Jurado và cộng sự, 2014). In mã lên thẻ "
         "biến bài toán \"đọc chữ trên thẻ\" vốn cần AI thành bài toán giải mã xác định, chạy được ngay trên máy.")
    para("**Phản hồi tức thì trong học tập.** Các nghiên cứu về quan niệm sai trong hóa học (Taber, 2002) ghi nhận học sinh hay gán cấu "
         "trúc phân tử cho hợp chất ion và hiểu sai về hóa trị; phát hiện và giải thích lỗi ngay khi học sinh còn đang thao tác là "
         "cơ hội sửa quan niệm sai tốt nhất.")
    table("So sánh cách kiểm tra theo công thức và theo cấu trúc", ["Tình huống", "So công thức (đếm nguyên tử)", "Đối sánh đồ thị (CHEM VISION)"], [
        ["Ghép H–O–H (nước)", "Đúng", "Đúng: khớp nước"],
        ["Ghép H–H–O", "Đúng (vẫn 2H, 1O)", "Sai: thừa liên kết H–H, thiếu liên kết H–O"],
        ["C–C–O–H so với C–O–C", "Không phân biệt", "Phân biệt etanol và đimetyl ete"],
        ["Thiếu một thẻ H", "Sai, không nói thiếu gì", "Gợi ý chất gần nhất, nêu thẻ còn thiếu"],
    ], [5.0, 5.3, 5.7], size=12)


def chapter2():
    h("Chương 2: ĐẶT VẤN ĐỀ NGHIÊN CỨU", 1)
    h("2.1. Vấn đề nghiên cứu và câu hỏi đặt ra", 2)
    para("Bài toán cốt lõi: **từ một ảnh chụp các thẻ nguyên tố trên mặt bàn, làm thế nào xác định tự động, chính xác và giải thích "
         "được rằng học sinh đã ghép đúng chất nào, hay sai ở đâu?** Nhóm đặt ra bốn câu hỏi:")
    for t in ("**Câu hỏi 1 (Nhận diện):** thiết kế thẻ và thuật toán nào để đọc được kí hiệu từng thẻ nhanh, ổn định, không cần mạng "
              "và không tốn chi phí cho mỗi lượt?",
              "**Câu hỏi 2 (Liên kết):** làm thế nào suy ra thẻ nào chạm thẻ nào từ vị trí các thẻ trên ảnh, kể cả khi ảnh bị nghiêng, nhỏ, mờ?",
              "**Câu hỏi 3 (Chấm):** thuật toán nào xác định đúng chất, phân biệt đồng phân, và chỉ ra chính xác liên kết thừa hoặc thiếu?",
              "**Câu hỏi 4 (Tin cậy):** làm thế nào dùng AI ở chỗ cần mà không để AI tự đưa ra kết luận không kiểm chứng được?"):
        bullet(t)
    h("2.2. Giải pháp và điểm mới của đề tài", 2)
    bullet("**Tách nhận diện khỏi chấm:** tầng nhận diện chỉ trả về danh sách thẻ, vị trí và cặp thẻ chạm nhau dưới một định dạng "
           "JSON chung; tầng chấm là thuật toán xác định. Lời nhắc gửi Gemini không chứa công thức nên AI không bị gợi ý đáp án.")
    bullet(f"**Thẻ lục giác in kèm mã ArUco:** {len(CARD_ELEMENTS)} nguyên tố được gán số hiệu trong từ điển {markers.DICT_NAME}; kích "
           f"thước thẻ suy ra trực tiếp từ cạnh mã (tỉ lệ {vn(markers.CARD_TO_MARKER, 1)}), nên liên kết được tính bằng khoảng cách "
           f"tâm mà không cần biết khoảng cách camera.")
    bullet("**Liên kết bằng hình học khi không có mã:** mặt nạ nền trong không gian màu Lab và độ dài khe hở dọc đoạn nối tâm, "
           "thay cho việc để AI đoán thẻ nào chạm thẻ nào.")
    bullet("**Đối sánh đẳng cấu có nhãn với chẩn đoán lỗi:** Weisfeiler–Lehman để lọc nhanh, quay lui để xác nhận; hiệu đa tập "
           "kiểu liên kết để chỉ ra liên kết thừa, thiếu; khoảng cách thành phần và đồ thị con để gợi ý.")
    bullet("**Kiểm tra chất lượng ảnh trước khi gọi AI:** chặn ảnh hỏng nặng, tiết kiệm hạn mức và cho học sinh chụp lại ngay.")
    h("2.3. Mục tiêu kỹ thuật", 2)
    table("Mục tiêu kỹ thuật và cách đo", ["Mục tiêu", "Chỉ số", "Cách đo"], [
        ["Chấm đúng mọi cách đánh số thẻ", "100% khớp đúng sau hoán vị nhãn", "20 hoán vị ngẫu nhiên cho mỗi chất"],
        ["Không bao giờ chấm nhầm cấu trúc sai thành đúng", "0 khớp nhầm", "Mọi đột biến dời một liên kết"],
        ["Phân biệt đồng phân", "2/2 cặp", "Etanol/đimetyl ete, butan/isobutan"],
        ["Đọc thẻ có mã ổn định", "≥ 95% đúng chất", "Ảnh tổng hợp: thu nhỏ, nghiêng, mờ, tối"],
        ["Phản hồi tức thì", "< 50 ms xử lý mỗi ảnh", "Thời gian trung vị trên máy tính xách tay"],
        ["Cân bằng phương trình chính xác", "24/24, không sai số làm tròn", "Kiểm tra bảo toàn nguyên tố"],
    ], [5.4, 4.6, 6.0], size=12)


def chapter3():
    h("Chương 3: THIẾT KẾ VÀ PHƯƠNG PHÁP NGHIÊN CỨU", 1)
    h("3.1. Kiến trúc tổng thể", 2)
    figure("k01_kien_truc", "Kiến trúc hai tầng: nhận diện (ArUco hoặc Gemini + hình học) và chấm (đối sánh đồ thị)")
    para("Ảnh từ camera (thu nhỏ để cạnh dài nhất không quá 1.280 điểm ảnh) đi qua bộ đọc ArUco trước. Nếu đọc được mã, liên kết "
         "được tính ngay theo khoảng cách tâm và ảnh không bao giờ rời khỏi máy chủ. Nếu không có mã (thẻ học sinh tự vẽ), ảnh được "
         "kiểm tra chất lượng; ảnh đạt mới được gửi tới Gemini, và Gemini chỉ trả về kí hiệu cùng khung bao của từng thẻ. Liên kết "
         "khi đó được tính lại bằng hình học trên ảnh. Cả hai đường cho ra cùng một JSON, nên tầng chấm không cần biết thẻ được đọc "
         "bằng cách nào.")
    h("3.2. Thiết kế thẻ và mã đánh dấu", 2)
    figure("k02_hinh_hoc_the", "Thẻ in thật (trái) và khoảng cách tâm trên lưới lục giác so với các ngưỡng (phải)")
    table("Thông số thẻ nguyên tố", ["Thông số", "Giá trị", "Lí do"], [
        ["Hình dạng", "Lục giác đều, đối cạnh 40 mm", "Sáu cạnh cho sáu hướng nối, gần với hình ảnh vòng benzen, mạng tinh thể"],
        ["Mã đánh dấu", f"ArUco {markers.DICT_NAME}, cạnh 40/{vn(markers.CARD_TO_MARKER, 1)} ≈ 18 mm", "Mã 4×4 có ô lớn, đọc được ở ảnh nhỏ; 50 mã đủ cho 22 nguyên tố"],
        ["Viền trắng quanh mã", "16% cạnh mã", "Bắt buộc để bộ phát hiện tìm được đường biên mã"],
        ["Màu nền thẻ", "Màu nguyên tố pha 45% trắng", "Mã đen trắng nổi rõ, vẫn giữ màu quy ước"],
        ["Bộ thẻ in", "PDF A4 300 dpi cho lớp 7, 8, 9", "Mỗi bộ đủ ghép mọi chất của lớp hai lần cùng lúc"],
    ], [3.4, 5.3, 7.3], size=12)
    para(f"Với mỗi mã đọc được, kích thước thẻ trên ảnh được ước lượng là s = {vn(markers.CARD_TO_MARKER, 1)} × (trung bình bốn cạnh "
         f"mã). Hai thẻ i, j được coi là có liên kết khi **‖cᵢ − cⱼ‖ ≤ {vn(markers.LINK_RATIO, 1)} × (sᵢ + sⱼ)/2**, trong đó c là tâm mã. "
         f"Trên lưới lục giác, hai thẻ chung cạnh có tâm cách nhau đúng 1 đối cạnh, còn hai thẻ cách một ô cách nhau √3 ≈ 1,73 "
         f"(Hình 2, phải); ngưỡng {vn(markers.LINK_RATIO, 1)} nằm giữa hai giá trị này nên chịu được sai lệch đặt thẻ khoảng ±30%.")
    h("3.3. Kiểm tra chất lượng ảnh", 2)
    para("Trước khi gửi ảnh tới AI, ảnh được thu về 640 điểm ảnh và đo bốn chỉ số. Độ nét dùng phương sai của toán tử Laplace "
         "(Pech-Pacheco và cộng sự, 2000): ảnh nét có nhiều cạnh nên đáp ứng Laplace phân tán mạnh.")
    table("Chỉ số và ngưỡng kiểm tra chất lượng ảnh", ["Chỉ số", "Cách tính", "Nhắc nhở", "Chặn"], [
        ["Độ sáng", "trung bình mức xám (0–255)", f"< {vn(quality.DARK[0], 0)} hoặc > {vn(quality.BRIGHT[0], 0)}", f"< {vn(quality.DARK[1], 0)} hoặc > {vn(quality.BRIGHT[1], 0)}"],
        ["Độ nét", "Var(∇²I) trên ảnh 640 px", f"< {vn(quality.BLUR[0], 0)}", f"< {vn(quality.BLUR[1], 0)}"],
        ["Lóa", "tỉ lệ điểm V ≥ 250 và S < 40 (HSV)", f"> {vn(quality.GLARE[0] * 100, 0)}%", f"> {vn(quality.GLARE[1] * 100, 0)}%"],
        ["Tương phản", "độ lệch chuẩn mức xám", f"< {vn(quality.CONTRAST[0], 0)}", f"< {vn(quality.CONTRAST[1], 0)}"],
    ], [2.8, 6.4, 3.4, 3.4], size=12)
    h("3.4. Xác định liên kết bằng hình học (đường không có mã)", 2)
    para("Gemini chỉ trả về khung bao của từng thẻ. Để biết thẻ nào chạm thẻ nào mà không phải tin AI, hệ thống phân tích mặt bàn:")
    for t in ("**Mặt nạ nền:** ảnh được làm mờ Gauss 5×5, chuyển sang không gian Lab. Màu bàn là nhóm màu phổ biến nhất ở dải viền 5% "
              f"ảnh (lượng tử hóa 16 mức). Điểm có ‖Lab − màu bàn‖ < {vn(geometry.BG_DIST, 0)} là mặt bàn; phép đóng {geometry.CLOSE_PX} px nối "
              f"vân gỗ, phép mở {geometry.OPEN_PX} px xóa đốm nhỏ.",
              f"**Điều kiện chạm:** với mỗi cặp thẻ, nếu khoảng cách tâm không quá {vn(geometry.MAX_RATIO, 1)} lần kích thước thẻ (căn bậc "
              f"hai diện tích khung bao), lấy mẫu mặt nạ dọc đoạn nối hai tâm và tìm đoạn mặt bàn liên tục dài nhất. Hai thẻ chạm nhau khi "
              f"đoạn đó ngắn hơn {vn(geometry.GAP_FRAC * 100, 0)}% kích thước thẻ.",
              f"**Khử trùng:** hai khung bao cùng kí hiệu có IoU ≥ {vn(geometry.DUP_IOU, 1)} được coi là một thẻ bị liệt kê hai lần."):
        bullet(t)
    h("3.5. Mô hình đồ thị và thuật toán đối sánh", 2)
    figure("k04_dong_phan", "Hai đồ thị cùng thành phần nhưng không đẳng cấu: etanol và đimetyl ete")
    para("Sau khi làm sạch dữ liệu (bỏ thẻ trùng số hiệu, kí hiệu không hợp lệ, cạnh trỏ tới thẻ không tồn tại; thẻ có độ tin cậy "
         f"dưới {vn(core.MIN_CONFIDENCE, 1)} buộc chụp lại), các thẻ được tách thành **thành phần liên thông** bằng duyệt đồ thị; mỗi "
         "thành phần là một phân tử. Mỗi thành phần được đối sánh như sau:")
    for t in ("**Lọc theo chữ kí:** chữ kí của đồ thị là đa tập nhãn (ví dụ {C: 2, H: 6, O: 1}). Cơ sở dữ liệu được lập chỉ mục theo "
              "chữ kí, nên chỉ so với các chất cùng thành phần.",
              "**Lọc Weisfeiler–Lehman (WL):** mỗi đỉnh được gán màu ban đầu là nhãn nguyên tố, rồi qua 3 vòng cập nhật "
              "cᵢ ← băm(cᵢ, đa tập {cⱼ : j kề i}). Hai đồ thị đẳng cấu thì có cùng đa tập màu; khác đa tập màu thì chắc chắn không đẳng cấu "
              "(Weisfeiler và Leman, 1968; Shervashidze và cộng sự, 2011).",
              "**Quay lui xác nhận:** đặt lần lượt các đỉnh theo bậc giảm dần; một đỉnh u chỉ được ánh xạ tới đỉnh v cùng màu WL, sao cho "
              "mọi hàng xóm đã đặt của u ánh xạ tới hàng xóm của v và số hàng xóm đã đặt hai bên bằng nhau. Với phân tử tối đa "
              f"{G['cỡ phân tử lớn nhất']} nguyên tử và màu WL đã tách gần hết các đỉnh, nhánh cần thử rất ít.",
              "**Chẩn đoán khi không khớp:** nếu có chất cùng thành phần nhưng không đẳng cấu, kết luận **sai liên kết**; liên kết thừa "
              "= B(G) − B(chuẩn) và liên kết thiếu = B(chuẩn) − B(G), với B là đa tập kiểu liên kết (ví dụ H–O ×2). Nếu không có chất "
              f"cùng thành phần, tìm **gợi ý**: chất có số thẻ thiếu + thừa ≤ {core.MAX_D}, thừa ≤ {core.MAX_EXTRA}, trùng ít nhất "
              f"{vn(core.MIN_OVERLAP * 100, 0)}% số thẻ; xếp theo khoảng cách, ưu tiên khi cụm là đồ thị con của chất đó, rồi theo số "
              "liên kết chung.",
              "**Cảnh báo hóa trị:** số liên kết tối đa của mỗi nguyên tố được học từ chính cơ sở dữ liệu; thẻ chạm nhiều thẻ hơn mức này "
              "được nêu trong lời giải thích."):
        bullet(t)
    figure("k05_quyet_dinh", "Lưu đồ quyết định của tầng chấm cho một cụm thẻ")
    h("3.6. Cân bằng phương trình hóa học", 2)
    para("Với phương trình có m chất và k nguyên tố, lập ma trận A cỡ k × m: phần tử aₑ,ᵢ là số nguyên tử nguyên tố e trong chất i, "
         "mang dấu dương ở vế trái và âm ở vế phải. Hệ số cân bằng là nghiệm dương của A·x = 0. Hệ thống khử Gauss–Jordan bằng "
         "**phân số chính xác** (không dùng số thực nên không có sai số làm tròn); nếu không gian nghiệm có đúng một chiều và nghiệm "
         "dương, nhân với bội chung nhỏ nhất của các mẫu số rồi chia cho ước chung lớn nhất để được bộ hệ số nguyên nhỏ nhất.")
    co = reactions.balance(["CH4", "O2"], ["CO2", "H2O"])
    table("Ví dụ: ma trận nguyên tố của CH₄ + O₂ → CO₂ + H₂O", ["Nguyên tố", "CH₄", "O₂", "CO₂", "H₂O"], [
        ["C", "1", "0", "−1", "0"], ["H", "4", "0", "0", "−2"], ["O", "0", "2", "−2", "−1"],
        ["Nghiệm x", *[str(v) for v in co]]], [3.6, 3.1, 3.1, 3.1, 3.1], bold_rows=(3,), size=12)
    para(f"Nghiệm ({', '.join(str(v) for v in co)}) cho phương trình CH₄ + 2O₂ → CO₂ + 2H₂O. Khi học sinh nhập hệ số, hệ thống đếm "
         "nguyên tử từng nguyên tố ở hai vế và tô nổi nguyên tố còn lệch.")
    h("3.7. Gọi mô hình thị giác có kiểm soát", 2)
    bullet(f"Model chính {recognizer.MODELS[0]}, dự phòng {recognizer.MODELS[1]}; nhiệt độ {vn(recognizer.TEMPERATURE, 1)}, tắt suy luận "
           "mở rộng; yêu cầu trả về JSON đúng lược đồ.")
    bullet(f"Lời nhắc chỉ giao nhiệm vụ quan sát (liệt kê thẻ, khung bao, độ tin cậy), cấm đoán tên chất, nhắc các cặp dễ nhầm "
           "(C/Ca, O/Os, N/Na).")
    bullet(f"Thử lại: mã lỗi tạm thời {sorted(retry.TRANSIENT)} thử tối đa 3 lần với thời gian chờ 2, 4, 6 giây trong ngân sách "
           f"15 giây; lỗi 404 chuyển ngay sang model dự phòng; lỗi {sorted(retry.FATAL)} dừng.")
    bullet(f"Bảo vệ hạn mức: mã truy cập và giới hạn {web.RATE_LIMIT[0]} lượt mỗi {vn(web.RATE_LIMIT[1], 0)} giây cho mỗi địa chỉ IP; "
           f"ảnh tối đa {web.MAX_IMAGE_BYTES // (1024 * 1024)} MB; ảnh không được lưu.")
    h("3.8. Phương pháp đánh giá", 2)
    para(f"Vì chưa có bộ ảnh chụp thẻ in thật có gán nhãn, nhóm xây dựng **bộ ảnh tổng hợp** có thể lặp lại: thẻ được vẽ bằng "
         f"chính hàm in thẻ của dự án, xếp thành phân tử theo hai cách (theo lưới lục giác: {SC['đặt theo lưới']} chất; xếp tỏa tròn "
         f"quanh nguyên tử trung tâm: {SC['đặt tỏa tròn']} chất), đặt trên mặt bàn gỗ, rồi biến dạng có kiểm soát: thu nhỏ, xoay ngẫu "
         f"nhiên 0–360°, méo phối cảnh, làm mờ Gauss, giảm độ sáng kèm nhiễu, nén JPEG chất lượng 85. Mỗi mức đo trên {N_IMG} ảnh "
         f"({SC['chất dựng được']} chất × 2 góc xoay). Chỉ số: tỉ lệ ảnh đọc đủ mọi thẻ và tỉ lệ ảnh kết luận đúng chất. Toàn bộ quy "
         f"trình nằm trong tệp scripts/bao_cao/do_luong.py, hạt giống ngẫu nhiên cố định nên chạy lại cho cùng kết quả.")
    figure("k03_vi_du_nhan_dien", "Một ảnh thử và kết quả nhận diện: khung thẻ, số hiệu và liên kết (đường xanh)")


def chapter4():
    h("Chương 4: KẾT QUẢ NGHIÊN CỨU VÀ GIẢI TRÌNH KỸ THUẬT", 1)
    h("4.1. Thuật toán đối sánh đồ thị", 2)
    iso = G["đồng phân"]
    table("Kết quả kiểm tra tầng chấm", ["Phép thử", "Số lượt", "Kết quả"], [
        ["Hoán vị ngẫu nhiên số hiệu thẻ (20 lần/chất)", vn(G["lượt hoán vị"], 0), f"{vn(G['khớp đúng sau hoán vị'], 0)} khớp đúng (100%)"],
        ["Dời một đầu liên kết sang nguyên tử khác", vn(G["đột biến một liên kết"], 0),
         f"{G['khớp nhầm']} khớp nhầm; {G['báo sai liên kết']} báo đúng \"sai liên kết\""],
        ["Đồng phân etanol / đimetyl ete", "2", "Phân biệt đúng" if iso["C2H5OH/CH3OCH3"]["phân biệt đúng"] else "Sai"],
        ["Đồng phân butan / isobutan", "2", "Phân biệt đúng" if iso["C4H10/C4H10-iso"]["phân biệt đúng"] else "Sai"],
        ["Thời gian đối sánh một cụm", vn(G["lượt hoán vị"], 0),
         f"trung vị {vn(G['ms trung vị'], 2)} ms; 95% dưới {vn(G['ms p95'], 2)} ms; chậm nhất {vn(G['ms lớn nhất'], 2)} ms"],
        ["Cân bằng phương trình lớp 8", str(EQ["phương trình"]), f"{EQ['cân bằng đúng']}/{EQ['phương trình']} bảo toàn nguyên tố; "
         f"chậm nhất {vn(EQ['ms lớn nhất'], 2)} ms"],
    ], [6.6, 2.2, 7.2], size=12)
    para(f"Đột biến \"dời một liên kết\" giữ nguyên thành phần nhưng đổi cấu trúc, đúng loại lỗi học sinh hay mắc (như nối H với H). "
         f"Những đột biến tình cờ tạo ra một chất có thật trong cơ sở dữ liệu đã bị loại khỏi phép đếm. Trong {G['đột biến một liên kết']} "
         f"trường hợp còn lại, hệ thống không lần nào kết luận nhầm là đúng, và lần nào cũng chỉ ra được liên kết thừa, thiếu.")
    h("4.2. Độ bền của nhận diện bằng mã ArUco", 2)
    figure("k06_do_ben_aruco", "Tỉ lệ đọc đủ thẻ và kết luận đúng chất theo bốn loại biến dạng ảnh")
    s36, s42 = row("kích thước thẻ", "cạnh thẻ px", 36), row("kích thước thẻ", "cạnh thẻ px", 42)
    s30 = row("kích thước thẻ", "cạnh thẻ px", 30)
    b1, b15, b2 = (row("mờ", "mờ σ px", v) for v in (1, 1.5, 2))
    t35, t50, t60 = (row("nghiêng", "nghiêng độ", v) for v in (35, 50, 60))
    rows = [["Kích thước thẻ trên ảnh", f"≥ 42 px: {vn(s42['đúng chất %'], 0)}%; 36 px: {vn(s36['đúng chất %'], 1)}%; 30 px: {vn(s30['đúng chất %'], 1)}%"],
            ["Méo phối cảnh (mép xa co lại)", f"còn 82%: 100%; còn 65%: {vn(t35['đúng chất %'], 1)}%; còn 40%: {vn(t50['đúng chất %'], 1)}%; còn 13%: {vn(t60['đúng chất %'], 1)}%"],
            ["Mờ Gauss", f"σ = 1 px: {vn(b1['đúng chất %'], 0)}%; σ = 1,5: {vn(b15['đúng chất %'], 1)}%; σ = 2: {vn(b2['đúng chất %'], 1)}%"],
            ["Độ sáng (kèm nhiễu σ = 4)", f"từ 100% xuống 15% độ sáng: {vn(row('tối', 'độ sáng ×', 0.15)['đúng chất %'], 0)}% ở mọi mức"],
            ["Thời gian đọc mã + chấm", f"trung vị {vn(row('kích thước thẻ', 'cạnh thẻ px', 60)['ms trung vị'], 1)} ms mỗi ảnh (thẻ 60 px)"]]
    table(f"Tóm tắt độ bền đường ArUco (tỉ lệ kết luận đúng chất, mỗi mức {N_IMG} ảnh)", ["Biến dạng", "Kết quả"], rows, [5.0, 11.0], size=12)
    para(f"Ngưỡng làm việc rút ra: thẻ cần rộng **từ khoảng 40 điểm ảnh** trên ảnh 1.280 điểm ảnh, tức một khung hình chứa được cả "
         f"chục thẻ, đủ cho phân tử lớn nhất ({G['cỡ phân tử lớn nhất']} nguyên tử). Độ sáng gần như không ảnh hưởng vì mã đen trắng "
         f"giữ tương phản, nhưng **độ mờ là kẻ thù chính**: mờ từ σ = 1,5 điểm ảnh trở lên tỉ lệ giảm nhanh. Điều này khớp với thiết "
         f"kế kiểm tra chất lượng ảnh, ở đó độ nét là chỉ số chặn. Khi méo phối cảnh mạnh, mọi thẻ vẫn đọc được nhưng tỉ lệ kết luận đúng "
         f"giảm ở các phân tử xếp tỏa tròn: phối cảnh làm khoảng cách tâm co lại không đều, một số cặp không liên kết lọt dưới ngưỡng "
         f"{vn(markers.LINK_RATIO, 1)}. Cách khắc phục là hướng dẫn chụp gần vuông góc với mặt bàn, hoặc nắn phối cảnh theo bốn góc mã "
         f"trước khi đo khoảng cách (hướng phát triển).")
    h("4.3. Đường hình học và một cải tiến được định lượng", 2)
    figure("k07_hinh_hoc", "Quyết định nối theo khe hở (trái) và số phân tử kết luận đúng trước và sau khi hạ ngưỡng (phải)")
    g1 = GEO_NOW["gỗ sáng"]
    rows = []
    for b in GEO_NOW:
        a, n = GEO_NOW[b], GEO_NEW[b]
        rows.append([f"Nền {b}", f"{a['đúng chất']}/{a['phân tử']}", f"{a['liên kết thừa']} / {a['liên kết thiếu']}",
                     f"{n['đúng chất']}/{n['phân tử']}", f"{n['liên kết thừa']} / {n['liên kết thiếu']}"])
    table(f"Đường hình học với thẻ thường, khung bao đúng: ngưỡng hiện tại {MAX_NOW} và đề xuất {RATIO_NEW}",
          ["Mặt bàn", f"Đúng chất ({MAX_NOW})", "Thừa / thiếu", f"Đúng chất ({RATIO_NEW})", "Thừa / thiếu"], rows,
          [3.2, 3.3, 3.0, 3.3, 3.2], size=12)
    para(f"Với hai thẻ đơn lẻ trên nền gỗ, thuật toán phân định đúng: khe hở dưới khoảng 7% cạnh thẻ thì nối, từ 8% trở lên thì "
         f"không (Hình 7, trái). Nhưng ở cả phân tử, chỉ {g1['đúng chất']}/{g1['phân tử']} phân tử được kết luận đúng. Phân tích lỗi "
         f"cho thấy **toàn bộ {g1['liên kết thừa']} liên kết thừa đều là cặp thẻ có tâm cách nhau đúng 1,73 cạnh thẻ**, tức hai thẻ cách "
         f"một ô: đoạn nối tâm của cặp này đi qua đúng góc chung của hai thẻ nằm giữa nên không thấy mặt bàn. Ngưỡng khoảng cách "
         f"{MAX_NOW} tính theo khung bao (khung bao rộng hơn đối cạnh 1,16 lần) tương đương 1,97 cạnh thẻ, không loại được "
         f"cặp này. Hạ ngưỡng xuống {RATIO_NEW} (≈ 1,5 cạnh thẻ) đưa liên kết thừa về 0 trên cả ba nền và nâng số phân tử đúng trên "
         f"nền gỗ lên {GEO_NEW['gỗ sáng']['đúng chất']}/{GEO_NEW['gỗ sáng']['phân tử']}. Trên nền xám đậm và nền trắng vẫn còn nhiều "
         f"liên kết thiếu: chữ đen hoặc thẻ H màu trắng có màu gần màu bàn nên bị coi nhầm là khe hở. Vì vậy hướng dẫn sử dụng yêu cầu "
         f"đặt thẻ trên nền trơn khác màu thẻ, và đường có mã ArUco được dùng làm đường chính.")
    h("4.4. Kiểm tra chất lượng ảnh", 2)
    figure("k08_chat_luong", "Độ nét đo được khi làm mờ dần một ảnh thử và kết luận của bộ kiểm tra", 13.5)
    para("Ảnh nét có độ nét khoảng vài trăm; chỉ cần mờ σ = 1 điểm ảnh, độ nét đã giảm hơn mười lần và hệ thống nhắc chụp lại; từ "
         "σ = 2 ảnh bị chặn trước khi tốn một lượt gọi AI. So với Mục 4.2, ngưỡng chặn nằm đúng vùng mà bộ đọc mã bắt đầu thất bại.")
    h("4.5. Kiểm thử phần mềm", 2)
    bullet("**245 kiểm thử tự động** cho lõi (làm sạch dữ liệu, đối sánh, gợi ý, hóa trị, cân bằng phương trình, thử lại khi gọi API, "
           "lớp học trực tuyến, máy chủ web), chạy không cần camera hay mạng; có vòng khép kín \"in thẻ rồi đọc lại\" trên trang PDF thật, "
           "kể cả khi thu nhỏ, nghiêng 9°, hơi mờ.")
    bullet("**113 kiểm thử giao diện** trong trình duyệt thật, đóng vai học sinh lớp 7, lớp 8, giáo viên, người không có camera, "
           "người mất mạng; kiểm tra cả bố cục ở khung 320–1.180 điểm ảnh, tương phản chữ đạt WCAG AA, nút chạm tối thiểu 48 px.")
    h("4.6. Ma trận quyết định của tầng chấm", 2)
    table("Ma trận quyết định và phản hồi cho học sinh", ["Kết luận", "Điều kiện", "Phản hồi", "Ví dụ"], [
        ["MATCH", "Có chất cùng chữ kí và đẳng cấu", "Con dấu xanh, tên chất, phân tử khối; chú thích nếu là hợp chất ion", "H–O–H → nước, PTK 18"],
        ["WRONG_BONDS", "Có chất cùng chữ kí nhưng không đẳng cấu", "Con dấu đỏ, nêu liên kết thừa/thiếu và cấu trúc đúng", "H–H–O → thừa H–H, thiếu H–O"],
        ["SUGGEST", "Không cùng chữ kí; có chất cách ≤ 3 thẻ", "\"Có phải bạn muốn ghép…?\", nêu thẻ thiếu/thừa", "O–H → gợi ý nước, thiếu 1 H"],
        ["UNKNOWN", "Không có ứng viên nào", "Đề nghị kiểm tra lại cách ghép theo hóa trị", "Cu–Cu–Cu"],
        ["RECAPTURE", "Ảnh hỏng nặng hoặc thẻ có độ tin cậy < 0,6", "Nêu lí do (tối, mờ, lóa…) và yêu cầu chụp lại", "Ảnh rung tay"],
    ], [2.9, 4.4, 5.3, 3.4], size=11.5)
    h("4.7. Giới hạn của nghiên cứu", 2)
    for t in ("Mọi phép đo nhận diện dùng **ảnh tổng hợp**; chưa có bộ ảnh chụp thẻ in thật bằng điện thoại có gán nhãn. Ánh sáng "
              "không đều, bóng đổ, thẻ cong vênh chưa được mô phỏng.",
              f"{len(SC['không dựng được'])}/{SC['tổng số chất']} chất ({', '.join(SC['không dựng được'])}) không xếp phẳng được mà giữ mọi "
              f"cặp thẻ không liên kết cách nhau trên ngưỡng đọc: hai nguyên tử C liền nhau, mỗi nguyên tử bốn liên kết, buộc thẻ H của "
              f"chúng phải gần nhau. Đây là giới hạn của quy ước \"chạm cạnh là liên kết\"; hướng giải quyết ở Mục 5.2.",
              "Độ chính xác của Gemini trên ảnh thật chưa được đo; đường hình học mới được đo với khung bao đúng tuyệt đối.",
              "Hiệu quả dạy học chưa được đánh giá; thiết kế thử nghiệm đối chứng đã sẵn sàng nhưng chưa tiến hành."):
        bullet(t)


def chapter5():
    h("Chương 5: KẾT LUẬN KHOA HỌC VÀ HƯỚNG PHÁT TRIỂN", 1)
    h("5.1. Kết luận", 2)
    bullet(f"**Mô hình hóa đúng bài toán:** biểu diễn cách ghép thẻ thành đồ thị có nhãn và kiểm tra đẳng cấu cho phép chấm theo cấu "
           f"trúc, phân biệt đồng phân và chỉ ra chính xác liên kết sai; thực nghiệm cho 100% khớp đúng và 0 khớp nhầm trên "
           f"{G['đột biến một liên kết']} cấu trúc sai, với thời gian dưới một phần nghìn giây.")
    bullet(f"**Nhận diện rẻ và ổn định:** thẻ giấy in mã ArUco cho phép đọc ngoại tuyến, không tốn chi phí mỗi lượt, đúng 100% khi thẻ "
           f"rộng từ 42 điểm ảnh và bền với thiếu sáng; độ mờ là yếu tố cần kiểm soát, đã được bộ kiểm tra chất lượng ảnh xử lý.")
    bullet("**AI được dùng có kiểm soát:** mô hình thị giác chỉ làm phần \"nhìn\" khi không có mã, mọi kết luận do thuật toán xác định "
           "nên giải thích và lặp lại được.")
    bullet(f"**Phương pháp đánh giá tìm ra lỗi thật:** bộ ảnh tổng hợp có kiểm soát đã chỉ ra nguyên nhân hình học của liên kết thừa "
           f"ở đường không có mã và định lượng được cải tiến ({GEO_NOW['gỗ sáng']['đúng chất']} → {GEO_NEW['gỗ sáng']['đúng chất']} "
           f"phân tử đúng trên {GEO_NOW['gỗ sáng']['phân tử']}).")
    h("5.2. Hướng phát triển", 2)
    for t in (f"Đưa ngưỡng MAX_RATIO = {RATIO_NEW} vào sản phẩm sau khi kiểm chứng trên ảnh thật; thêm phép nắn phối cảnh theo bốn góc "
              "mã ArUco trước khi đo khoảng cách.",
              "Xây dựng bộ ảnh chụp thẻ in thật có gán nhãn (nhiều điện thoại, mặt bàn, ánh sáng) để đo độ chính xác thực tế của cả hai đường.",
              "Giải quyết các phân tử có chuỗi C bão hòa: thẻ H nhỏ hơn thẻ C, hoặc chuyển quy ước liên kết sang \"cạnh hướng vào nhau\" "
              "dựa trên góc xoay của mã ArUco, thay cho khoảng cách tâm.",
              "Mở rộng sang liên kết đôi, liên kết ba (thẻ nối riêng) và sang Vật lý (mạch điện), Sinh học (ADN) dùng chung lõi nhận diện.",
              "Tiến hành thử nghiệm đối chứng với học sinh theo thiết kế đã chuẩn bị (chia ngẫu nhiên theo lớp, ANCOVA)."):
        bullet(t)


def references():
    h("TÀI LIỆU THAM KHẢO", 1)
    for t in ("Bộ Giáo dục và Đào tạo (2018), Chương trình giáo dục phổ thông môn Khoa học tự nhiên, ban hành kèm Thông tư 32/2018/TT-BGDĐT.",
              "Garrido-Jurado, S., Muñoz-Salinas, R., Madrid-Cuevas, F. J., & Marín-Jiménez, M. J. (2014), Automatic generation and "
              "detection of highly reliable fiducial markers under occlusion, Pattern Recognition, 47(6), 2280–2292.",
              "Bradski, G. (2000), The OpenCV Library, Dr. Dobb's Journal of Software Tools.",
              "Weisfeiler, B., & Leman, A. (1968), The reduction of a graph to canonical form and the algebra which appears therein, "
              "NTI, Series 2, 9, 12–16.",
              "Shervashidze, N., Schweitzer, P., van Leeuwen, E. J., Mehlhorn, K., & Borgwardt, K. M. (2011), Weisfeiler–Lehman graph "
              "kernels, Journal of Machine Learning Research, 12, 2539–2561.",
              "Cordella, L. P., Foggia, P., Sansone, C., & Vento, M. (2004), A (sub)graph isomorphism algorithm for matching large graphs, "
              "IEEE Transactions on Pattern Analysis and Machine Intelligence, 26(10), 1367–1372.",
              "Pech-Pacheco, J. L., Cristóbal, G., Chamorro-Martínez, J., & Fernández-Valdivia, J. (2000), Diatom autofocusing in "
              "brightfield microscopy: a comparative study, Proceedings of the 15th International Conference on Pattern Recognition, 3, 314–317.",
              "Taber, K. S. (2002), Chemical Misconceptions: Prevention, Diagnosis and Cure, Royal Society of Chemistry.",
              "Google (2026), Gemini API documentation: image understanding and structured output, ai.google.dev."):
        bullet(t)


def appendix():
    h("PHỤ LỤC: THÔNG SỐ KỸ THUẬT CỦA HỆ THỐNG", 1)
    table("Thông số kỹ thuật", ["Hạng mục", "Thông số"], [
        ["Ngôn ngữ, thư viện", "Python 3.12, NumPy, OpenCV (cv2.aruco); giao diện HTML/CSS/JavaScript thuần"],
        ["Triển khai", "Hàm serverless Vercel (vùng Singapore) hoặc máy chủ Render; bản máy tính Tkinter"],
        ["Thẻ", f"Lục giác đối cạnh 40 mm, {len(CARD_ELEMENTS)} nguyên tố, ArUco {markers.DICT_NAME}, PDF A4 300 dpi"],
        ["Ngưỡng liên kết ArUco", f"khoảng cách tâm ≤ {vn(markers.LINK_RATIO, 1)} × cỡ thẻ; cỡ thẻ = {vn(markers.CARD_TO_MARKER, 1)} × cạnh mã"],
        ["Ngưỡng hình học", f"tâm ≤ {vn(geometry.MAX_RATIO, 1)} × cỡ khung bao (đề xuất {RATIO_NEW}); khe hở < {vn(geometry.GAP_FRAC * 100, 0)}%; "
                            f"nền: ΔLab < {vn(geometry.BG_DIST, 0)}"],
        ["Cơ sở dữ liệu", f"{G['chất']} chất lớp 6–9, tối đa {G['cỡ phân tử lớn nhất']} nguyên tử; {EQ['phương trình']} phương trình lớp 8"],
        ["Đối sánh", "Chỉ mục theo chữ kí; Weisfeiler–Lehman 3 vòng; quay lui có ràng buộc màu và kề"],
        ["Gợi ý", f"thiếu + thừa ≤ {core.MAX_D}; thừa ≤ {core.MAX_EXTRA}; trùng ≥ {vn(core.MIN_OVERLAP * 100, 0)}%; tối đa {core.MAX_SUGGESTIONS} gợi ý"],
        ["Mô hình thị giác (dự phòng)", f"{recognizer.MODELS[0]} → {recognizer.MODELS[1]}; nhiệt độ {vn(recognizer.TEMPERATURE, 1)}; JSON"],
        ["Giới hạn", f"ảnh ≤ {web.MAX_IMAGE_BYTES // (1024 * 1024)} MB; {web.RATE_LIMIT[0]} lượt nhận diện/phút/IP; lớp học tự xóa sau 24 giờ"],
        ["Kiểm thử", "245 kiểm thử tự động + 113 kiểm thử giao diện; bộ đo scripts/bao_cao/do_luong.py"],
    ], [4.6, 11.4], size=12)


if __name__ == "__main__":
    setup()
    for part in (title_block, summary, chapter1, chapter2, chapter3, chapter4, chapter5, references, appendix):
        part()
    B.doc.save(OUT)
    print("Đã lưu", os.path.abspath(OUT), "-", B._fig_n[0], "hình,", B._tab_n[0], "bảng")
