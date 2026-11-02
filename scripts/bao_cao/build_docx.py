"""Dựng báo cáo khởi nghiệp CHEM VISION (.docx) từ model.py và các hình của charts.py.

Chạy: python charts.py && python build_docx.py
"""
import os
import re
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
import model as M
from charts import vn

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "..", "docs", "bao-cao", "hinh")
OUT = os.path.join(HERE, "..", "..", "docs", "bao-cao", "BAO_CAO_KHOI_NGHIEP_CHEM_VISION.docx")
NAVY, RED = RGBColor(0x1F, 0x33, 0x52), RGBColor(0xA3, 0x28, 0x1A)
FONT = "Times New Roman"

P, U, S = M.pnl(), M.unit_economics(), M.scenarios()
TAM_L, TAM, SAM, SOM = M.market()
LINES = M.revenue_lines()
CASH = M.monthly_cash()
PAYBACK = next(i + 1 for i, c in enumerate(CASH) if c >= 0)
BE_MONTH = int(-(-U["be_rev"] // (P[0]["rev"] / 78)))
CAPEX = sum(M.CAPEX.values())
FUND = CAPEX + M.WORKING_CAPITAL

doc = Document()
_fig_n = [0]
_tab_n = [0]


# ---------------- định dạng chung ----------------
def set_font(run_or_style, size=None, bold=None, color=None, italic=None):
    f = run_or_style.font
    f.name = FONT
    rpr = run_or_style.element.get_or_add_rPr() if hasattr(run_or_style.element, "get_or_add_rPr") else run_or_style.element.rPr
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts"); rpr.insert(0, rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):   # font chủ đề ghi đè tên font
        rfonts.attrib.pop(qn(a), None)
    if size: f.size = Pt(size)
    if bold is not None: f.bold = bold
    if italic is not None: f.italic = italic
    if color is not None: f.color.rgb = color


def setup():
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin = Cm(2.5), Cm(2), Cm(2), Cm(2)
    st = doc.styles["Normal"]
    set_font(st, 13)
    st.paragraph_format.space_after = Pt(6)
    st.paragraph_format.line_spacing = 1.2
    for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 13)):
        h = doc.styles[name]
        set_font(h, size, bold=True, color=NAVY, italic=False)
        h.paragraph_format.space_before = Pt(12 if name != "Heading 3" else 8)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
    for name in ("List Bullet", "List Number", "Caption"):
        set_font(doc.styles[name], 13 if name != "Caption" else 11)
    # Word tự cập nhật mục lục khi mở
    el = OxmlElement("w:updateFields"); el.set(qn("w:val"), "true")
    doc.settings.element.append(el)
    # số trang ở chân trang
    fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field(fp, "PAGE")


def field(paragraph, instr):
    r = paragraph.add_run()
    for tag, text in (("begin", None), (None, instr), ("separate", None), ("end", None)):
        if tag:
            e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), tag)
        else:
            e = OxmlElement("w:instrText"); e.set(qn("xml:space"), "preserve"); e.text = text
        r._r.append(e)
    set_font(r, 11)


def runs(p, text, size=None, color=None):
    """**đậm** trong chuỗi."""
    for i, part in enumerate(re.split(r"\*\*", text)):
        if part:
            r = p.add_run(part); set_font(r, size, bold=(i % 2 == 1), color=color)
    return p


def para(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, size=None, color=None, bold=False, space_after=None):
    p = doc.add_paragraph(); p.alignment = align
    runs(p, f"**{text}**" if bold else text, size, color)
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def bullet(text, style="List Bullet"):
    p = doc.add_paragraph(style=style); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return runs(p, text)


def h(text, level):
    return doc.add_heading(text, level)


def caption(text, kind):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    if kind == "Bảng":
        p.paragraph_format.keep_with_next = True
    r = p.add_run(f"{kind} {(_fig_n if kind == 'Hình' else _tab_n)[0]}. "); set_font(r, 11.5, bold=True, color=NAVY)
    r = p.add_run(text); set_font(r, 11.5, italic=True)


def figure(name, cap, width=16.5):
    _fig_n[0] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True; p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(FIG, name + ".png"), width=Cm(width))
    caption(cap, "Hình")
    return _fig_n[0]


def shade(cell, hex_fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    tcpr.append(shd)


def table(cap, headers, rows, widths, bold_rows=(), size=11, first_col_left=True):
    _tab_n[0] += 1
    caption(cap, "Bảng")
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER; t.autofit = False
    tblpr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblpr.append(lay)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 567)))
    for ri, row in enumerate([headers] + rows):
        tr = t.rows[ri]
        trpr = tr._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trpr.append(cs)
        if ri == 0:
            th = OxmlElement("w:tblHeader"); trpr.append(th)
        for ci, val in enumerate(row):
            c = tr.cells[ci]; c.width = Cm(widths[ci]); c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            c.paragraphs[0].text = ""
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.keep_with_next = ri < min(len(rows), 3)   # không để tiêu đề bảng nằm lẻ cuối trang
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (ci == 0 and first_col_left) or len(str(val)) > 16 else WD_ALIGN_PARAGRAPH.CENTER
            is_bold = ri == 0 or (ri - 1) in bold_rows
            r = p.add_run(str(val)); set_font(r, size, bold=is_bold, color=RGBColor(255, 255, 255) if ri == 0 else None)
            if ri == 0:
                shade(c, "1F3352")
            elif (ri - 1) in bold_rows:
                shade(c, "EEF2F7")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return _tab_n[0]


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def tr(x, d=1):
    """triệu đồng"""
    return vn(x, d)


def pct(x, d=1):
    return vn(100 * x, d) + "%"


# ---------------- nội dung ----------------
def cover():
    def c(text, size, bold=False, color=None, after=4):
        para(text, WD_ALIGN_PARAGRAPH.CENTER, size, color, bold, after)
    c("BỘ GIÁO DỤC VÀ ĐÀO TẠO", 14, True)
    c("CUỘC THI", 13, True, after=0)
    c("“HỌC SINH, SINH VIÊN VỚI Ý TƯỞNG KHỞI NGHIỆP”", 15, True, NAVY, 0)
    c("(SV_STARTUP)", 13, True, NAVY, 30)
    c("BÁO CÁO DỰ ÁN KHỞI NGHIỆP CÔNG NGHỆ GIÁO DỤC", 15, True, after=10)
    c("DỰ ÁN: CHEM VISION", 24, True, RED, 6)
    c("THẺ NGUYÊN TỐ THÔNG MINH VÀ CAMERA AI", 15, True, NAVY, 0)
    c("HỖ TRỢ DẠY HỌC HÓA HỌC TRONG MÔN KHOA HỌC TỰ NHIÊN THCS", 15, True, NAVY, 10)
    c("Lĩnh vực: Công nghệ giáo dục, Trí tuệ nhân tạo, Thị giác máy tính", 13, after=6)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(os.path.join(FIG, "h00_bia.png"), width=Cm(13))
    c("NHÓM THỰC HIỆN:", 13, True, after=2)
    for i in range(1, 4):
        c(f"{i}. [Họ và tên] – [Lớp] – [Trường]{' (trưởng nhóm)' if i == 1 else ''}", 13, after=0)
    c("Đơn vị: [Trường] – Sở Giáo dục và Đào tạo [tỉnh/thành phố]", 13, after=0)
    c("Giáo viên hướng dẫn: [Họ và tên]", 13, after=24)
    c("[Địa danh], tháng 11 năm 2026", 13, False)
    page_break()


def members():
    h("THÔNG TIN VẮN TẮT VỀ CÁC THÀNH VIÊN THAM GIA DỰ ÁN", 1)
    para("Ghi chú cho nhóm: thay các ô trong ngoặc vuông bằng thông tin thật trước khi nộp.")
    for line in ("1. Họ và tên trưởng nhóm: [Họ và tên]", "2. Trường/lớp: [Trường] – lớp [ ]",
                 "3. Số điện thoại liên hệ: [ ]", "4. Email: [ ]"):
        para(line, WD_ALIGN_PARAGRAPH.LEFT, space_after=2)
    h("5. Danh sách thành viên trong nhóm", 2)
    table("Thành viên và phân công", ["STT", "Họ và tên", "Lớp – Trường", "Vai trò trong nhóm"], [
        ["1", "[ ]", "[ ]", "Trưởng nhóm; điều phối chung, thiết kế trải nghiệm học sinh và thẻ in"],
        ["2", "[ ]", "[ ]", "Lập trình nhận diện (ArUco, OpenCV) và lõi đối sánh chất"],
        ["3", "[ ]", "[ ]", "Biên soạn bộ đề theo lớp 6-9, kiểm thử nội dung hóa học"],
        ["4", "[ ]", "[ ]", "Khảo sát giáo viên, học sinh; mô hình tài chính và hồ sơ dự thi"],
    ], [1.2, 3.8, 4.3, 7.2])
    h("6. Danh sách người hướng dẫn", 2)
    table("Người hướng dẫn", ["STT", "Họ và tên", "Đơn vị", "Trách nhiệm hướng dẫn"], [
        ["1", "[ ]", "[Giáo viên KHTN]", "Thẩm định nội dung hóa học, bộ đề và giáo án; tổ chức thử nghiệm trên lớp"],
        ["2", "[ ]", "[ ]", "Cố vấn khởi nghiệp, tài chính và kết nối trường thử nghiệm"],
    ], [1.2, 3.8, 4.3, 7.2])
    page_break()
    h("MỤC LỤC", 1)
    p = doc.add_paragraph(); field(p, 'TOC \\o "1-3" \\h \\z \\u')
    para("(Nếu mục lục trống: nhấp chuột phải vào đây, chọn Update Field / Cập nhật trường.)", size=10, color=RGBColor(0x6B, 0x72, 0x80))
    page_break()


def summary():
    h("TÓM TẮT DỰ ÁN", 1)
    h("1. Ý tưởng khởi nguồn của dự án", 2)
    para("Ở tiết Khoa học tự nhiên lớp 7, bài nguyên tử, phân tử và công thức hóa học là bài khó nhất với chúng em: các hạt quá nhỏ để "
         "nhìn thấy, còn trên lớp có 8 đến 10 nhóm cùng ghép mô hình nên thầy cô không thể xem kịp từng nhóm ghép đúng hay sai. Phần mềm "
         "nhập công thức thì bắt học sinh biết đáp án trước, và chỉ đếm số nguyên tử chứ không biết các nguyên tử đã nối với nhau đúng cách "
         "chưa. Nhóm tự hỏi: nếu mỗi nguyên tố là một tấm thẻ giấy in sẵn, học sinh ghép thẻ trên mặt bàn rồi đưa camera điện thoại vào, "
         "phần mềm có thể nói ngay \"đây là nước\" hoặc \"thiếu một liên kết O–H\" không? Câu hỏi đó trở thành CHEM VISION.")
    h("2. Mô tả sản phẩm", 2)
    para("CHEM VISION là ứng dụng web (và bản máy tính) gồm bộ thẻ nguyên tố lục giác in được và phần mềm nhận diện. Nguyên tắc "
         "thiết kế là **AI hỗ trợ nhận diện thẻ, còn đúng hay sai do thuật toán chấm theo cấu trúc**, nên kết quả nào cũng giải "
         "thích được. Với học sinh, điều đó gói gọn trong một câu: **\"Ghép là biết, sai là hiểu.\"**")
    bullet("**Nhận diện:** thẻ in có mã vuông ArUco được OpenCV đọc ngay trên máy, ngoại tuyến và không tốn tiền; thẻ thường được Gemini "
           "đọc ký hiệu và khung bao. Ảnh chất lượng kém (tối, mờ, lóa) bị cảnh báo trước khi gửi.")
    bullet("**Kết luận:** liên kết giữa các thẻ được đo bằng hình học, rồi thuật toán đối sánh đồ thị so với **70 chất** của chương trình "
           "lớp 6 đến 9 để trả lời: khớp, sai liên kết (nêu liên kết thừa hoặc thiếu), ghép dở hay không phải chất nào.")
    bullet("**Học và dạy:** giải thích \"Vì sao?\" bằng lời lớp 7, 11 bộ đề thử thách có 3 mức gợi ý, cân bằng 24 phương trình lớp 8, "
           "sao và huy hiệu (không bảng xếp hạng), lớp học trực tuyến để giáo viên thấy nhóm nào đang kẹt, báo cáo quan niệm sai.")
    h("3. Giá trị của dự án", 2)
    bullet("**Học sinh:** được chạm vào phân tử và biết ngay mình sai ở đâu, thay vì chờ thầy cô đi tới từng bàn.")
    bullet("**Giáo viên:** một bảng điều khiển cho cả lớp, thấy câu nào cả lớp sai nhiều để chữa ngay trong tiết.")
    bullet(f"**Nhà trường:** gói Trường {tr(M.PRICE['school'], 0)} triệu đồng/năm, khoảng "
           f"{vn(M.PRICE['school'] * 1e6 / (12 * 35), 0)} đồng mỗi học sinh mỗi năm (trường 12 lớp × 35 em), không cần mua thiết bị.")
    bullet(f"**Kinh doanh (dự phóng):** doanh thu năm 3 đạt {tr(P[2]['rev'])} triệu đồng, biên gộp {pct(P[2]['gm'])}, "
           f"LTV/CAC kênh trường {vn(U['ltv_cac'])} lần, thu hồi vốn đầu tư ban đầu ở tháng thứ {PAYBACK}.")
    para("**Trung thực về bằng chứng:** phần mềm đã có 245 kiểm thử tự động và 113 kiểm thử giao diện theo vai người dùng, nhưng "
         "**chưa thử nghiệm với học sinh thật**. Mục 2.3 trình bày thiết kế thử nghiệm đối chứng và các chỉ tiêu nhóm cam kết đo.")
    figure("h01_quy_trinh", "Quy trình của CHEM VISION: nhận diện thẻ, chấm theo cấu trúc, phản hồi ngay")


def canvas():
    h("NỘI DUNG CHÍNH CỦA DỰ ÁN", 1)
    h("A. MÔ HÌNH KINH DOANH CANVAS (BUSINESS MODEL CANVAS)", 2)
    figure("h02_canvas", "Mô hình kinh doanh canvas của CHEM VISION (tỷ trọng chi phí và doanh thu tính ở năm thứ ba)")
    para(f"Điểm mấu chốt của mô hình là sự gắn kết giữa Giải pháp giá trị (ô 2) và Kênh phân phối (ô 3): phần mềm luôn miễn phí trên "
         f"web nên giáo viên dùng thử ngay trong một tiết thao giảng, còn doanh thu đến từ những thứ trường và gia đình thực sự cần trả "
         f"tiền là **bộ thẻ vật lý bền** và **dữ liệu cả lớp cho giáo viên**. Gói Trường chiếm {pct(LINES['school'][2] / P[2]['rev'])} "
         f"doanh thu năm 3. Nhờ thẻ có mã đọc ngoại tuyến, chi phí đám mây chỉ chiếm "
         f"{pct(M.CLOUD[2] / (P[2]['cogs'] + P[2]['opex']))} tổng chi phí, nên nguồn lực dồn cho nhân sự kỹ thuật và học liệu.")


def problem():
    h("1. ĐẶT VẤN ĐỀ: GIÁ TRỊ CỐT LÕI, TẦM NHÌN, SỨ MỆNH", 2)
    h("1.1. Bốn bài toán thực tế trong lớp học Khoa học tự nhiên", 3)
    bullet("**Nội dung quá trừu tượng.** Nguyên tử, phân tử, ion thuộc thế giới vi mô. Các nghiên cứu về quan niệm sai trong hóa học "
           "ghi nhận học sinh hay gán cấu trúc phân tử cho cả hợp chất ion như NaCl.")
    bullet("**Lớp đông, phản hồi chậm.** Khi 8 đến 10 nhóm cùng ghép mô hình, giáo viên không thể kiểm tra từng nhóm ngay lúc đó; "
           "lỗi sai được phát hiện muộn, thường là ở bài kiểm tra.")
    bullet("**Cách kiểm tra cũ chỉ đếm nguyên tử.** Butan và isobutan, etanol và đimetyl ete có cùng công thức phân tử nhưng khác cấu "
           "trúc; phần mềm nhập công thức không phân biệt được.")
    bullet("**Thiếu thiết bị.** Nhiều trường THCS chưa đủ bộ mô hình và hóa chất; chương trình GDPT 2018 lại yêu cầu dạy học tích hợp, "
           "tăng hoạt động thực hành.")
    h("1.2. Tầm nhìn và sứ mệnh", 3)
    bullet("**Tầm nhìn:** trở thành bộ học cụ \"vật thật + AI\" tiêu chuẩn cho môn Khoa học tự nhiên THCS ở Việt Nam, từ hóa học mở "
           "rộng sang vật lý và sinh học.")
    bullet("**Sứ mệnh:** để mỗi học sinh được chạm vào kiến thức và được phản hồi ngay; để AI hỗ trợ việc nhận diện, còn việc chấm "
           "đúng sai luôn minh bạch, giải thích được.")
    h("1.3. Giá trị cho bốn bên liên quan", 3)
    figure("h03_gia_tri", "Giá trị cho bốn nhóm thụ hưởng")
    para("Bốn con số trên đều là đặc tính của sản phẩm hoặc của mức giá, không phải kết quả học tập. Nhóm cố ý không đưa ra con số "
         "\"tăng bao nhiêu điểm\" vì chưa thử nghiệm với học sinh; các nghiên cứu với công cụ tương tự (Happy Atoms, Augmented Chemistry) "
         "cho thấy kết quả học tập **ngang bằng** mô hình bi–que, còn ưu thế nằm ở phản hồi tức thì, chi phí và dữ liệu cho giáo viên.")
    h("1.4. Vì sao một nhóm học sinh làm được sản phẩm này", 3)
    para("Nhóm là những người vừa học xong chính các bài này nên hiểu chỗ khó của người học. Sản phẩm được chia nhỏ thành các phần "
         "có thể kiểm chứng: lõi đối sánh chất là thuật toán đồ thị thuần (không phụ thuộc AI), được kiểm tra bằng 245 kiểm thử tự động; "
         "bộ thẻ in được tạo bằng mã nguồn và tự kiểm tra vòng \"in thẻ rồi đọc lại\" trên trang in thật, kể cả khi thu nhỏ, nghiêng, hơi "
         "mờ. Giao diện được kiểm thử theo vai (học sinh lớp 7, lớp 8, giáo viên, người không có camera, người mất mạng) với 113 kiểm tra.")


def market():
    m = M.MARKET
    h("2. NGHIÊN CỨU VÀ KHẢO SÁT THỊ TRƯỜNG", 2)
    h("2.1. Quy mô thị trường từ dưới lên", 3)
    para("Quy mô thị trường được tính từ dưới lên: số đơn vị khách hàng nhân với giá niêm yết. Số liệu đầu vào là ước tính cho năm học "
         "2024-2025 và **cần đối chiếu với niên giám thống kê của Bộ GD&ĐT** trước khi nộp:")
    bullet(f"Khoảng {vn(m['schools'], 0)} trường THCS (kể cả liên cấp), mỗi trường một gói Trường và một bộ thẻ lớp thay mới mỗi năm.")
    bullet(f"Khoảng {vn(m['teachers'], 0)} giáo viên dạy Khoa học tự nhiên THCS.")
    bullet(f"Khoảng {vn(m['students_grade7'] / 1e6, 2)} triệu học sinh vào lớp 7 mỗi năm, là thời điểm gia đình mua bộ thẻ dùng cho lớp 7 đến 9.")
    para("Công thức: TAM = Σ Nᵢ × Pᵢ, trong đó Nᵢ là số đơn vị khách hàng nhóm i, Pᵢ là giá năm của nhóm đó.")
    tam_rows = [[f"Toàn diện – {k.lower()}", "", vn(v, 2), ""] for k, v in TAM_L.items()]
    formulas = [f"{vn(m['schools'], 0)} trường × {tr(M.PRICE['school'], 0)} tr.đ", f"{vn(m['schools'], 0)} trường × {tr(M.PRICE['class_kit'])} tr.đ",
                f"{vn(m['teachers'], 0)} GV × {vn(M.PRICE['teacher'] * 1e6, 0)} đ", f"{vn(m['students_grade7'], 0)} HS × {vn(M.PRICE['family_kit'] * 1e6, 0)} đ"]
    notes = ["Mọi trường THCS dùng gói Trường", "Một bộ thẻ lớp mỗi trường mỗi năm", "Mọi giáo viên KHTN dùng gói Pro", "Mọi học sinh vào lớp 7 có bộ thẻ"]
    for r, f, n in zip(tam_rows, formulas, notes):
        r[1], r[3] = f, n
    rows = tam_rows + [
        ["TAM", "Tổng bốn nhóm", vn(TAM, 2), "Dung lượng lý thuyết"],
        ["SAM", f"{vn(m['sam_schools'], 0)} trường + {vn(m['sam_teachers'], 0)} GV + {vn(m['sam_students'], 0)} HS", vn(SAM, 2),
         "Các tỉnh miền Bắc nhóm tiếp cận được trong 3 năm (khoảng 25%)"],
        ["SOM (năm 3)", f"{M.VOLUME['school'][2]} trường + {M.VOLUME['class_kit'][2]} bộ lớp + {vn(M.VOLUME['teacher'][2], 0)} GV + "
         f"{vn(M.VOLUME['family_kit'][2], 0)} bộ GĐ", vn(SOM, 2), f"{pct(SOM / SAM)} SAM, {pct(SOM / TAM, 2)} TAM"],
    ]
    table("Quy mô thị trường phân tầng (tỷ đồng/năm)", ["Cấp độ", "Công thức", "Giá trị (tỷ đ)", "Giả định"], rows,
          [3.4, 5.6, 2.3, 5.2], bold_rows=(4, 5, 6), size=10.5)
    figure("h04_thi_truong", "Tháp thị trường TAM, SAM, SOM và cơ cấu TAM theo nhóm khách hàng")
    fam = TAM_L["Bộ thẻ gia đình"] / TAM
    para(f"Bộ thẻ gia đình chiếm {pct(fam)} dung lượng lý thuyết, nhưng đây cũng là nhóm khó tiếp cận nhất vì phụ huynh chỉ mua khi "
         f"giáo viên giới thiệu. Vì vậy nhóm coi **trường học là cửa vào** (gói Trường chiếm {pct(LINES['school'][2] / P[2]['rev'])} "
         f"doanh thu năm 3) và bộ gia đình là dòng doanh thu theo sau. Mục tiêu SOM năm 3 chỉ bằng {pct(SOM / SAM)} SAM: một mục tiêu "
         f"thận trọng, đạt được bằng kênh thao giảng mà không cần chạy quảng cáo.")
    h("2.2. Phân tích SWOT", 3)
    figure("h08_swot", "Ma trận SWOT của CHEM VISION")
    para("Ma trận SWOT cho thấy điểm yếu lớn nhất không nằm ở công nghệ mà ở **bằng chứng**: sản phẩm chạy được, được kiểm thử kỹ, "
         "nhưng chưa có số liệu với học sinh thật. Chiến lược của nhóm vì vậy là dùng điểm mạnh \"chạy ngoại tuyến, chi phí 0 đồng mỗi lượt\" "
         "để mở cửa vào các trường thiếu thiết bị (S–O), đồng thời đặt thử nghiệm đối chứng lên đầu lộ trình (W–T).")
    h("2.3. Bằng chứng hiện có và kế hoạch thử nghiệm đối chứng", 3)
    para("Thử nghiệm đã được thiết kế đầy đủ (tài liệu docs/thiet-ke-thu-nghiem.md) nhưng **chưa tiến hành**. Thiết kế: chia ngẫu "
         "nhiên theo lớp, nhóm CHEM VISION (CV) so với nhóm mô hình bi–que (BQ), cùng giáo án, cùng 2 tiết; hai dạng đề song song A/B; "
         "phân tích ANCOVA có sai số chuẩn theo cụm lớp. Giả thuyết được đặt trước: CHEM VISION **không thấp hơn** mô hình bi–que và có thể "
         "cao hơn ở kỹ năng \"cách nối quyết định chất\".")
    table("Cỡ mẫu cần thiết (α = 0,05, hiệu lực 0,8; ICC = 0,1 là giả định)",
          ["Cỡ ảnh hưởng muốn phát hiện (d)", "Mỗi nhóm nếu chia theo học sinh", "Mỗi nhóm nếu chia theo lớp 30 em"],
          [["0,5 (trung bình)", "63 học sinh", "245 học sinh, khoảng 9 lớp"],
           ["0,3 (nhỏ)", "175 học sinh", "683 học sinh, khoảng 23 lớp"]], [5.5, 5.5, 5.5])
    table("Chỉ tiêu nhóm cam kết đo trong thử nghiệm (mục tiêu, chưa phải kết quả)",
          ["Chỉ tiêu", "Cách đo", "Mục tiêu"], [
              ["Điểm kiểm tra sau bài", "ANCOVA theo điểm trước, sai số theo cụm lớp", "Không thấp hơn BQ quá 0,5 điểm (biên tương đương)"],
              ["Kỹ năng \"cấu trúc quyết định chất\"", "Câu hỏi đồng phân trong đề A/B", "Cao hơn nhóm BQ"],
              ["Độ chính xác nhận diện thẻ có mã", "Ảnh chụp thẻ in thật, có đáp án", "≥ 95% lượt đọc đúng toàn bộ thẻ"],
              ["Lỗi kỹ thuật trong tiết", "Phiếu trung thực thực hiện", "≤ 1 lần làm lại mỗi nhóm mỗi tiết"],
              ["Thái độ học tập", "Phiếu 5 câu, thang 1-5", "Trung bình ≥ 4,0"],
              ["Kiến thức còn lại sau 4-6 tuần", "Bài kiểm tra muộn", "Báo cáo trung thực, không đặt ngưỡng"],
          ], [4.6, 6.2, 5.7], size=10.5)
    para("Thử nghiệm thử 2 đến 4 lớp chỉ đủ để kiểm tra khả thi và ước lượng độ biến thiên, không đủ kết luận có khác biệt. Đây là lý do "
         "Giai đoạn 0 của lộ trình (Mục 9) gồm cả thử nghiệm thử và thử nghiệm đủ cỡ mẫu.")


def product():
    h("3. TÍNH NĂNG, KIẾN TRÚC LÕI VÀ LỢI THẾ CẠNH TRANH", 2)
    h("3.1. Kiến trúc: tách nhận diện khỏi chấm điểm", 3)
    para("Hệ thống tách hai việc mà các sản phẩm AI thường gộp làm một. **Việc nhận diện** (thẻ nào ở đâu) do bộ đọc mã ArUco đảm nhận khi "
         "thẻ có mã, và do Gemini đảm nhận khi thẻ không có mã; lời nhắc gửi Gemini không chứa công thức nên AI không bị gợi ý đáp án. "
         "**Việc chấm** (đây là chất gì, sai ở đâu) luôn do thuật toán xác định: liên kết được đo bằng khe hở giữa các thẻ trên ảnh, "
         "rồi đồ thị phân tử được đối sánh với cơ sở dữ liệu 70 chất. Mọi lời giải thích lỗi sinh ra từ chẩn đoán này, không do AI tự nghĩ.")
    para(f"Lợi ích kinh doanh trực tiếp: khi trường dùng bộ thẻ in có mã, mỗi lượt KIỂM TRA không tốn tiền đám mây và không gửi ảnh ra "
         f"ngoài. Gemini chỉ là phương án dự phòng, có model dự phòng thứ hai (gemini-flash-lite-latest) khi model chính lỗi hoặc hết hạn mức.")
    h("3.2. Ma trận mức sẵn sàng của sản phẩm", 3)
    figure("h05_san_sang", "Mức sẵn sàng của từng tính năng: đã lập trình, đã kiểm thử tự động, đã kiểm chứng thực tế", 15)
    para("Cột thứ ba là cột nhóm cần lấp đầy trước khi bán: triển khai thật lên Vercel, kết nối Upstash Redis thật, in thẻ ra giấy và "
         "chụp bằng điện thoại, đo độ chính xác của Gemini trên bộ ảnh có đáp án, và thử với học sinh. Những ô \"Một phần\" ở cột này là "
         "các phần đã chạy thử trong trình duyệt tích hợp hoặc với 2 ảnh thẻ thật (thời gian 3 đến 7 giây khi gọi Gemini).")
    h("3.3. Đối sánh cạnh tranh", 3)
    figure("h06_canh_tranh", "Ma trận đối sánh tám tiêu chí của sáu giải pháp (đánh giá định tính của nhóm)")
    figure("h07_dinh_vi", "Bản đồ định vị: chi phí ban đầu cho một lớp và mức phản hồi về cấu trúc", 13.5)
    para("Ma trận là đánh giá định tính theo ba mức, dựa trên tài liệu công khai của từng sản phẩm; chi phí trên bản đồ định vị là ước "
         "tính và cần xác minh ở nhà cung cấp. Happy Atoms là đối thủ gần nhất về ý tưởng (nguyên tử vật lý có mã, chụp để nhận diện) và "
         "là sản phẩm duy nhất có thử nghiệm ngẫu nhiên lớn (1.795 học sinh), nhưng giá cao, tiếng Anh và thiết kế cho THPT. CHEM VISION "
         "kế thừa ý tưởng mã nhận dạng trên từng thẻ, và khác biệt ở tổ hợp: thẻ giấy rẻ, kiểm tra cấu trúc, tiếng Việt bám KHTN 6-9, "
         "dữ liệu cả lớp. Ô trống duy nhất của CHEM VISION, bằng chứng học tập, cũng là việc ưu tiên số một.")
    h("3.4. Hướng nâng cấp", 3)
    for t in ("Tài khoản, phân quyền và lưu trữ bền vững (PostgreSQL) trước khi bán cho trường công lập.",
              "Bổ sung glucozơ, saccarozơ bằng thẻ nhóm nguyên tử; phân biệt bậc liên kết (đôi, ba).",
              "Bộ thẻ Vật lý (mạch điện) và Sinh học (ADN, di truyền) dùng chung lõi nhận diện ArUco.",
              "Chế độ ngoại tuyến toàn phần (PWA) cho trường mạng yếu."):
        bullet(t)


def customers():
    h("4. KHÁCH HÀNG MỤC TIÊU", 2)
    para("Người trả tiền và người dùng không trùng nhau. Nhà trường trả tiền để có công cụ dạy tích hợp và dữ liệu cho tổ chuyên môn; "
         "giáo viên là người quyết định dùng; học sinh là người dùng trực tiếp; phụ huynh trả tiền cho bộ thẻ ở nhà khi giáo viên giới thiệu.")
    table("Phân khúc khách hàng", ["Phân khúc", "Người dùng", "Người trả tiền", "Họ cần gì", "Sản phẩm"], [
        ["Trường THCS", "GV và HS trong tiết", "Ban giám hiệu", "Công cụ rẻ, dữ liệu lớp, an toàn dữ liệu", "Gói Trường + bộ thẻ lớp"],
        ["Giáo viên KHTN", "Giáo viên", "Giáo viên", "Kiểm tra nhanh nhiều nhóm, bộ đề sẵn", "Gói Giáo viên Pro"],
        ["Gia đình", "Học sinh 7-9", "Phụ huynh", "Học ở nhà không cần người chấm", "Bộ thẻ gia đình"],
        ["CLB STEM, trung tâm", "Học viên", "Trung tâm", "Hoạt động thực hành hấp dẫn", "Bộ thẻ lớp + tập huấn"],
    ], [3.0, 3.0, 2.8, 4.4, 3.3], size=10.5)
    figure("h09_chu_ky_mua", "Chu kỳ ra quyết định mua và ngân sách mỗi lần mua theo phân khúc")
    para("Chu kỳ mua chênh nhau rất xa, từ vài ngày với phụ huynh đến 90-180 ngày với trường công lập. Nhóm dùng các khách hàng quyết "
         "nhanh (giáo viên, phụ huynh, trường tư thục) để có dòng tiền trong lúc chờ quy trình ngân sách của trường công. Gói Trường được đặt "
         "ở mức đủ nhỏ để nằm trong khoản chi thường xuyên cho ứng dụng công nghệ thông tin của trường.")


def revenue():
    h("5. MÔ HÌNH DOANH THU VÀ PHƯƠNG THỨC BÁN HÀNG", 2)
    h("5.1. Vòng lan tỏa từ tiết thao giảng", 3)
    figure("h10_vong_lan_toa", "Vòng lan tỏa: thao giảng, dùng thử, ký gói Trường, học sinh mang thẻ về nhà, phụ huynh mua", 13.5)
    para("Phần mềm miễn phí là chi phí tiếp thị của dự án. Một tiết thao giảng ở tổ chuyên môn cho giáo viên thấy sản phẩm chạy thật; "
         "trường dùng thử một học kỳ rồi ký gói Trường; mỗi hộp thẻ có mã QR dẫn về trang hướng dẫn, mở đường cho bộ thẻ gia đình. Người "
         "giới thiệu là giáo viên nên chi phí có được khách hàng thấp.")
    h("5.2. Cơ cấu nguồn thu", 3)
    para(f"Sáu nguồn thu: gói Trường {tr(M.PRICE['school'], 0)} triệu đồng/năm; bộ thẻ lớp {tr(M.PRICE['class_kit'])} triệu đồng; bộ thẻ "
         f"gia đình {vn(M.PRICE['family_kit'] * 1e6, 0)} đồng; gói Giáo viên Pro {vn(M.PRICE['teacher'] * 1e6, 0)} đồng/năm; tập huấn "
         f"{tr(M.PRICE['training'], 0)} triệu đồng/đợt; và chia sẻ doanh thu với đối tác thiết bị, nhà xuất bản từ năm 2.")
    figure("h11_doanh_thu", "Cơ cấu doanh thu năm 3 và doanh thu, lợi nhuận ròng ba năm đầu (triệu đồng)")
    para(f"Không nguồn nào chiếm quá một nửa doanh thu: gói Trường {pct(LINES['school'][2] / P[2]['rev'])}, bộ gia đình "
         f"{pct(LINES['family_kit'][2] / P[2]['rev'])}. Doanh thu phần cứng (bộ thẻ) có biên thấp hơn phần mềm nhưng là thứ khách hàng "
         f"chạm vào được và tạo lý do mua lặp lại khi thẻ hỏng hoặc học sinh lên lớp.")


def costs():
    h("6. CƠ CẤU CHI PHÍ ĐẦU TƯ BAN ĐẦU VÀ VẬN HÀNH", 2)
    h("6.1. CAPEX và OPEX", 3)
    figure("h12_chi_phi", f"CAPEX ban đầu {CAPEX} triệu đồng và chi phí hoạt động tiền mặt ba năm đầu")
    table("Chi phí hoạt động tiền mặt (triệu đồng/năm)", ["Khoản mục", *M.YEARS],
          [[k, *[vn(x, 0) for x in v]] for k, v in M.OPEX.items()] + [["Tổng", *[vn(p["opex"], 0) for p in P]]],
          [7.6, 3.0, 3.0, 2.9], bold_rows=(len(M.OPEX),))
    para(f"Nhân sự kỹ thuật là khoản lớn nhất ({pct(M.OPEX['Nhân sự kỹ thuật (cộng tác viên)'][0] / P[0]['opex'], 0)} năm 1), vì giai "
         f"đoạn đầu cần hoàn thiện lưu trữ, tài khoản và kiểm chứng trên thiết bị thật. CAPEX được khấu hao đều trong "
         f"{M.DEPRECIATION_YEARS} năm ({vn(P[0]['dep'], 0)} triệu đồng/năm).")
    h("6.2. Giá vốn đám mây: công thức token", 3)
    i, o = M.GEMINI["flash"]
    para(f"Nhóm tính theo bảng giá tham khảo Gemini 2.5 Flash {vn(i, 2)} USD mỗi triệu token vào và {vn(o, 2)} USD mỗi triệu token ra "
         f"(Flash-Lite {vn(M.GEMINI['lite'][0], 2)} và {vn(M.GEMINI['lite'][1], 2)} USD); 1 USD = {vn(M.USD, 0)} đồng; **cần cập nhật bảng "
         f"giá trước khi nộp**. Mỗi lượt gửi một ảnh và lời nhắc (khoảng {M.TOKENS_IN} token vào), nhận về khoảng {M.TOKENS_OUT} token JSON.")
    para(f"Chi phí một lượt = ({M.TOKENS_IN} × {vn(i, 2)} + {M.TOKENS_OUT} × {vn(o, 2)}) / 10⁶ × {vn(M.USD, 0)} ≈ "
         f"**{vn(M.per_call_vnd(), 1)} đồng**", WD_ALIGN_PARAGRAPH.CENTER)
    para(f"Chi phí một tiết = {M.GROUPS} nhóm × {M.CHECKS_PER_GROUP} lượt × tỷ lệ thẻ thường × {vn(M.per_call_vnd(), 1)} đồng",
         WD_ALIGN_PARAGRAPH.CENTER)
    figure("h13_gia_von_tiet", "Chi phí gọi AI cho một tiết theo loại thẻ")
    para(f"Ở kịch bản cơ sở ({int(M.GEMINI_SHARE * 100)}% lượt dùng thẻ thường), một trường dùng {M.LESSONS_PER_SCHOOL} tiết mỗi năm tốn "
         f"khoảng {vn(U['cloud_school'] * 1e6, 0)} đồng tiền AI, bằng {pct(U['cloud_school'] / M.PRICE['school'])} giá gói Trường. Kể cả khi "
         f"100% lượt dùng thẻ thường, chi phí vẫn chỉ {vn(M.per_lesson_vnd(1) * M.LESSONS_PER_SCHOOL / 1e6 / M.PRICE['school'] * 100, 1)}% "
         f"giá gói. Khoản đám mây trong giá vốn ({vn(M.CLOUD[2], 0)} triệu đồng năm 3) còn gồm Vercel, Upstash Redis và dự phòng.")
    h("6.3. Nhu cầu vốn và phương án huy động", 3)
    table("Nhu cầu vốn ban đầu (triệu đồng)", ["Hạng mục", "Số tiền", "Ghi chú"],
          [[k, vn(v, 0), ""] for k, v in M.CAPEX.items()] +
          [["Vốn lưu động", vn(M.WORKING_CAPITAL, 0), "Khoảng 3 tháng chi phí hoạt động năm 1"],
           ["Tổng nhu cầu vốn", vn(FUND, 0), ""]], [8.0, 2.5, 6.0], bold_rows=(len(M.CAPEX) + 1,))
    para(f"Tổng nhu cầu {vn(FUND, 0)} triệu đồng dự kiến huy động từ: giải thưởng và quỹ hỗ trợ khởi nghiệp học sinh, sinh viên; tài trợ "
         f"hiện vật (máy in, thẻ nhựa) của đơn vị thiết bị giáo dục; và doanh thu bán trước bộ thẻ lớp cho các trường thử nghiệm.")


def pricing():
    h("7. GIÁ BÁN SẢN PHẨM", 2)
    figure("h14_bang_gia", "Thang giá cho người dùng cá nhân và tổ chức")
    para(f"Giá được đặt theo khả năng chi trả của người mua, không tính ngược từ giá vốn. Bộ thẻ gia đình "
         f"{vn(M.PRICE['family_kit'] * 1e6, 0)} đồng tương đương một cuốn sách tham khảo, có biên đóng góp "
         f"{vn(U['contrib_family'] * 1e6, 0)} đồng sau giá vốn và phí thanh toán. Gói Trường 6 triệu đồng/năm chia cho một trường 12 lớp "
         f"là khoảng {vn(M.PRICE['school'] * 1e6 / (12 * 35), 0)} đồng mỗi học sinh mỗi năm. Bộ thẻ lớp có giá vốn "
         f"{vn(M.UNIT_COST['class_kit'] * 1e6, 0)} đồng (in màu, ép nhựa, hộp), biên gộp "
         f"{pct(1 - M.UNIT_COST['class_kit'] / M.PRICE['class_kit'], 0)}.")


def financials():
    h("8. DỰ KIẾN DOANH THU VÀ LỢI NHUẬN TRONG BA NĂM", 2)
    h("8.1. Báo cáo kết quả kinh doanh dự phóng", 3)
    rows = [["Doanh thu thuần", *[tr(p["rev"]) for p in P]], ["Giá vốn hàng bán", *[tr(p["cogs"]) for p in P]],
            ["Lợi nhuận gộp", *[tr(p["gp"]) for p in P]], ["Biên lợi nhuận gộp", *[pct(p["gm"]) for p in P]],
            ["Chi phí hoạt động tiền mặt", *[tr(p["opex"]) for p in P]], ["Khấu hao CAPEX", *[tr(p["dep"]) for p in P]],
            ["Lợi nhuận trước thuế", *[tr(p["ebt"]) for p in P]],
            ["Thuế TNDN (giả định 0% năm 1, 10% từ năm 2)", *[tr(p["tax"]) for p in P]],
            ["Lợi nhuận ròng", *[tr(p["ni"]) for p in P]], ["Biên lợi nhuận ròng", *[pct(p["nm"]) for p in P]]]
    table("Dự phóng kết quả kinh doanh ba năm đầu (triệu đồng)", ["Chỉ tiêu", *M.YEARS], rows, [7.6, 3.0, 3.0, 2.9], bold_rows=(0, 2, 8))
    figure("h15_thac_nuoc", "Thác nước kết quả kinh doanh năm 3, từ doanh thu đến lợi nhuận ròng (triệu đồng)")
    p3 = P[2]
    para(f"Năm 3, giá vốn lấy {pct(p3['cogs'] / p3['rev'])} doanh thu (chủ yếu là in bộ thẻ), chi phí hoạt động lấy "
         f"{pct(p3['opex'] / p3['rev'])}, thuế {pct(p3['tax'] / p3['rev'])}, còn lại lợi nhuận ròng {pct(p3['nm'])}. Biên gộp tăng từ "
         f"{pct(P[0]['gm'])} lên {pct(p3['gm'])} vì tỷ trọng phần mềm (gói Trường, gói Giáo viên) tăng dần. Năm 1 chỉ lãi mỏng "
         f"({tr(P[0]['ni'])} triệu đồng): đây là năm xây kênh. Thuế suất ưu đãi cần đối chiếu quy định hiện hành khi thực hiện.")
    h("8.2. Dựng doanh thu từ dưới lên", 3)
    rev_rows = []
    for k in ("school", "class_kit", "family_kit", "teacher", "training"):
        price = M.PRICE[k]
        rev_rows.append([M.REV_LABELS[k], vn(price * 1e6, 0) if price < 1 else vn(price, 1) + " tr",
                         *[f"{vn(M.VOLUME[k][y], 0)} → {tr(LINES[k][y])}" for y in range(3)]])
    rev_rows.append([M.REV_LABELS["partner"], "hợp đồng", *[tr(x) for x in M.PARTNER]])
    rev_rows.append(["Tổng doanh thu", "", *[tr(p["rev"]) for p in P]])
    table("Doanh thu = số lượng × đơn giá (số lượng → triệu đồng)", ["Dòng doanh thu", "Đơn giá (đ)", *M.YEARS], rev_rows,
          [3.6, 2.4, 3.5, 3.5, 3.5], bold_rows=(len(rev_rows) - 1,), size=10.5)
    para(f"Số trường tăng {M.VOLUME['school'][0]} → {M.VOLUME['school'][1]} → {M.VOLUME['school'][2]} tương ứng với lộ trình mở rộng "
         f"theo vùng ở Mục 9. Bộ thẻ gia đình giả định khoảng {vn(M.VOLUME['family_kit'][2] / M.VOLUME['school'][2], 1)} bộ cho mỗi trường "
         f"đang dùng ở năm 3, tức chưa đến 2% học sinh của các trường đó mua.")
    h("8.3. Kinh tế đơn vị và điểm hòa vốn", 3)
    figure("h16_kinh_te_don_vi", "Kinh tế đơn vị kênh trường và điểm hòa vốn hoạt động năm 1")
    table("Các chỉ số kinh tế đơn vị", ["Chỉ số", "Cách tính", "Giá trị"], [
        ["CAC kênh trường", f"({tr(M.OPEX['Tiếp thị, thao giảng, hội thảo'][0], 0)} tiếp thị + 30% × "
                            f"{tr(M.OPEX['Nhân sự kỹ thuật (cộng tác viên)'][0], 0)} nhân sự) / {M.VOLUME['school'][0]} trường",
         f"{tr(U['cac_school'])} tr.đ"],
        ["Tỷ lệ gia hạn, vòng đời", f"gia hạn {pct(U['renew'], 0)} → 1 / (1 − {vn(U['renew'], 1)})", f"{vn(U['life'], 0)} năm"],
        ["LTV kênh trường", f"({tr(M.PRICE['school'], 0)} − {vn(U['cloud_school'], 3)} tiền AI) × {vn(U['life'], 0)} năm",
         f"{tr(U['ltv_school'])} tr.đ"],
        ["LTV / CAC", "ngưỡng an toàn thường dùng: 3 lần", f"{vn(U['ltv_cac'])} lần"],
        ["Thu hồi CAC", "CAC / lợi nhuận gộp gói Trường mỗi tháng", f"{vn(U['payback_m'])} tháng"],
        ["Biên đóng góp bộ gia đình", f"{vn(M.PRICE['family_kit'] * 1e6, 0)} − {vn(M.UNIT_COST['family_kit'] * 1e6, 0)} − phí thanh toán",
         f"{vn(U['contrib_family'] * 1e6, 0)} đ"],
        ["Biên đóng góp / CAC gia đình", f"CAC giả định {vn(U['cac_family'] * 1e6, 0)} đ (hoa hồng giới thiệu, nhóm phụ huynh)",
         f"{vn(U['family_ratio'])} lần"],
        ["Ngưỡng hòa vốn hoạt động", f"({tr(P[0]['opex'], 0)} / 12) / biên gộp {pct(P[0]['gm'])}", f"{tr(U['be_rev'])} tr.đ/tháng"],
    ], [4.4, 8.4, 3.7], size=10.5)
    para(f"Với giả định doanh thu năm 1 tăng đều theo tháng, doanh thu vượt ngưỡng hòa vốn hoạt động khoảng tháng {BE_MONTH}. Thực tế "
         f"doanh thu trường học dồn vào đầu năm học, nên mốc này phụ thuộc thời điểm bắt đầu bán; đây là giả định cần theo dõi.")
    h("8.4. Dòng tiền và thời gian thu hồi vốn", 3)
    figure("h17_dong_tien", f"Dòng tiền lũy kế 36 tháng, tính cả CAPEX {CAPEX} triệu đồng ở tháng 0")
    para(f"Dòng tiền lũy kế trở về 0 ở **tháng {PAYBACK}**, tức thu hồi toàn bộ CAPEX sau khoảng một năm vận hành, và đạt "
         f"{tr(CASH[-1], 0)} triệu đồng sau 36 tháng. Phần âm thấp nhất của dòng tiền "
         f"({tr(-min([-CAPEX] + CASH), 0)} triệu đồng) nằm trong tổng nhu cầu vốn {vn(FUND, 0)} triệu đồng ở Mục 6.3.")
    h("8.5. Phân tích độ nhạy và kịch bản", 3)
    figure("h18_do_nhay", "Độ nhạy của lợi nhuận trước thuế năm 3 với từng giả định và ba kịch bản lượng bán")
    para(f"Hai giả định quan trọng nhất là **số trường** và **giá gói Trường**: lệch 20% làm lợi nhuận trước thuế năm 3 đổi khoảng "
         f"{tr(M.VOLUME['school'][2] * M.PRICE['school'] * 0.2, 0)} triệu đồng. Chi phí đám mây gần như không ảnh hưởng, nhờ thẻ có mã. "
         f"Ở kịch bản xấu (lượng bán mọi dòng chỉ bằng 60% kế hoạch, chi phí hoạt động giữ nguyên) dự án vẫn có lợi nhuận ròng năm 3 "
         f"{tr(S['Xấu']['ni'], 0)} triệu đồng; ở kịch bản tốt (+30%) đạt {tr(S['Tốt']['ni'], 0)} triệu đồng.")


def strategy():
    h("9. CHIẾN LƯỢC BÁN HÀNG VÀ LỘ TRÌNH TRIỂN KHAI", 2)
    h("9.1. Land-and-Expand", 3)
    para("Quy trình bốn bước: (1) thao giảng tại tổ chuyên môn KHTN, tặng bộ thẻ lớp dùng thử một học kỳ; (2) sau một tháng, gửi ban "
         "giám hiệu báo cáo lớp học (số lượt, lỗi thường gặp, nhóm kẹt); (3) ký gói Trường cho toàn bộ lớp 6-9; (4) học sinh mang hộp thẻ "
         "có mã QR về nhà, mở kênh bộ thẻ gia đình. Năm 1 tập trung vào các tỉnh nhóm có quan hệ trực tiếp, năm 2 mở rộng qua đối tác "
         "thiết bị giáo dục, năm 3 liên kết nhà xuất bản và Sở GD&ĐT.")
    h("9.2. Lộ trình bốn giai đoạn", 3)
    figure("h19_lo_trinh", "Lộ trình theo quý; năm vận hành thứ nhất bắt đầu từ Quý 2/2027")
    para("Giai đoạn 0 không có doanh thu: nhóm kiểm chứng những gì còn trống ở cột thứ ba của ma trận sẵn sàng (Hình 6) và tiến hành "
         "thử nghiệm đối chứng. Chỉ khi có số liệu thử nghiệm, nhóm mới đưa con số hiệu quả học tập vào tài liệu bán hàng.")
    h("9.3. Ma trận tăng trưởng Ansoff", 3)
    figure("h21_ansoff", "Ma trận Ansoff: thứ tự mở rộng sản phẩm và thị trường", 13)


def marketing():
    h("10. CHIẾN LƯỢC TIẾP THỊ VÀ PHÁT TRIỂN CỘNG ĐỒNG", 2)
    for t in ("**Sản phẩm kéo người dùng:** web miễn phí, không cần cài đặt, có nút \"Chạy thử\" không cần camera; PDF bộ thẻ tải về in ngay.",
              "**Giáo viên cốt cán:** mỗi tỉnh 3-5 giáo viên KHTN được tập huấn sâu, dùng bộ đề tự tạo và chia sẻ trong nhóm chuyên môn.",
              "**Bằng chứng minh bạch:** công bố thiết kế thử nghiệm trước khi làm, công bố kết quả kể cả khi chỉ \"ngang bằng\".",
              "**Sân chơi không áp lực:** sao và huy hiệu thay cho bảng xếp hạng, đồng hồ đếm ngược; phù hợp học sinh THCS và phụ huynh.",
              f"**Ngân sách:** {tr(M.OPEX['Tiếp thị, thao giảng, hội thảo'][0], 0)} triệu đồng năm 1, dành cho thao giảng, bộ thẻ "
              f"trình diễn và hội thảo; không quảng cáo trả tiền theo lượt."):
        bullet(t)


def risks():
    h("11. QUẢN TRỊ RỦI RO VÀ PHÁT TRIỂN BỀN VỮNG", 2)
    figure("h20_rui_ro", "Ma trận rủi ro: vị trí trước và sau biện pháp phòng vệ", 13)
    table("Rủi ro và biện pháp", ["Mã", "Rủi ro", "Biện pháp"], [
        ["R1", "Gemini đọc sai thẻ thường", "Bộ thẻ có mã ArUco là đường chính; kiểm tra chất lượng ảnh; học sinh chọn lại thẻ bị đọc sai"],
        ["R2", "Giá, hạn mức, đổi tên model Google", "Model dự phòng; thẻ có mã không cần AI; giới hạn 20 lượt/phút mỗi IP; hạn mức chi tiêu"],
        ["R3", "Thử nghiệm không cho kết quả vượt trội", "Giả thuyết \"không thấp hơn\" đặt trước; bán bằng giá trị phản hồi, chi phí, dữ liệu"],
        ["R4", "Mua sắm công kéo dài", "Bán trước cho giáo viên, phụ huynh, trường tư thục; gói Trường giá nhỏ"],
        ["R5", "Dữ liệu, quyền riêng tư học sinh", "Không chụp khuôn mặt; lớp học chỉ lưu nhãn nhóm, tự xóa sau 24 giờ; thẻ có mã không gửi ảnh"],
        ["R6", "Thẻ in sai tỉ lệ, mất thẻ", "Trang hướng dẫn in 100%; thẻ dự phòng trong bộ lớp; tải lại PDF miễn phí"],
    ], [1.2, 5.0, 10.3], size=10.5)
    para("Về phát triển bền vững: thẻ giấy và phần mềm thay một phần mô hình nhựa và hóa chất; trường thiếu thiết bị vẫn có hoạt động "
         "thực hành; dữ liệu chỉ dùng cho mục đích dạy học.")


def conclusion():
    h("KẾT LUẬN VÀ KIẾN NGHỊ", 1)
    para(f"CHEM VISION giải một bài toán cụ thể của lớp học Khoa học tự nhiên: cho học sinh chạm vào phân tử và được phản hồi ngay về "
         f"cấu trúc, cho giáo viên thấy cả lớp đang kẹt ở đâu. Sản phẩm đã chạy được với 70 chất, 24 phương trình, 11 bộ đề và được kiểm "
         f"thử tự động kỹ. Mô hình tài chính có công thức kiểm tra lại được: doanh thu năm 3 {tr(P[2]['rev'])} triệu đồng, biên gộp "
         f"{pct(P[2]['gm'])}, LTV/CAC kênh trường {vn(U['ltv_cac'])} lần, thu hồi vốn tháng {PAYBACK}, vẫn có lãi ở kịch bản xấu.")
    para("Điều nhóm còn thiếu là bằng chứng với học sinh thật. Nhóm kính đề nghị Ban Giám khảo xem xét và hỗ trợ dự án: kết nối 4 đến 9 "
         "trường THCS để thử nghiệm đối chứng, và hỗ trợ kinh phí in bộ thẻ trình diễn cho Giai đoạn 0.")
    h("PHỤ LỤC: BẢNG CHỈ SỐ KINH DOANH TỔNG HỢP", 1)
    table("Bảng chỉ số tổng hợp", ["Nhóm chỉ số", "Chỉ số", "Giá trị"], [
        ["Thị trường", "TAM / SAM / SOM năm 3 (tỷ đồng)", f"{vn(TAM, 2)} / {vn(SAM, 2)} / {vn(SOM, 2)}"],
        ["Doanh thu", "Năm 1 / 2 / 3 (triệu đồng)", " / ".join(tr(p["rev"]) for p in P)],
        ["Tăng trưởng", "Năm 2 / năm 3 so với năm trước", f"{vn(P[1]['rev'] / P[0]['rev'], 2)} lần / {vn(P[2]['rev'] / P[1]['rev'], 2)} lần"],
        ["Lợi nhuận", "Biên gộp năm 1 / 3", f"{pct(P[0]['gm'])} / {pct(P[2]['gm'])}"],
        ["Lợi nhuận", "Lợi nhuận ròng năm 1 / 2 / 3 (triệu đồng)", " / ".join(tr(p["ni"]) for p in P)],
        ["Lợi nhuận", "Biên ròng năm 3", pct(P[2]["nm"])],
        ["Kinh tế đơn vị", "CAC / LTV kênh trường (triệu đồng)", f"{tr(U['cac_school'])} / {tr(U['ltv_school'])}"],
        ["Kinh tế đơn vị", "LTV/CAC; thu hồi CAC", f"{vn(U['ltv_cac'])} lần; {vn(U['payback_m'])} tháng"],
        ["Vốn", "CAPEX; tổng nhu cầu vốn (triệu đồng)", f"{CAPEX}; {FUND}"],
        ["Vốn", "Hòa vốn hoạt động; thu hồi vốn", f"tháng {BE_MONTH}; tháng {PAYBACK}"],
        ["Chi phí AI", "Mỗi tiết: thẻ có mã / cơ sở / 100% thẻ thường",
         f"0 / {vn(M.per_lesson_vnd(M.GEMINI_SHARE), 0)} / {vn(M.per_lesson_vnd(1), 0)} đồng"],
        ["Rủi ro", "Lợi nhuận ròng năm 3, kịch bản xấu / tốt", f"{tr(S['Xấu']['ni'], 0)} / {tr(S['Tốt']['ni'], 0)} triệu đồng"],
        ["Sản phẩm", "Chất / phương trình / bộ đề / kiểm thử", "70 / 24 / 11 / 245 + 113"],
    ], [3.5, 7.0, 6.0], size=10.5)
    para("Mọi số liệu tài chính trong báo cáo là dự phóng dựa trên giả định của nhóm, được tính bằng tệp scripts/bao_cao/model.py; "
         "đổi một giả định ở đó và chạy lại sẽ cập nhật toàn bộ bảng và hình.", size=11)


if __name__ == "__main__":
    setup()
    for part in (cover, members, summary, canvas, problem, market, product, customers, revenue, costs, pricing, financials,
                 strategy, marketing, risks, conclusion):
        part()
    doc.save(OUT)
    print("Đã lưu", os.path.abspath(OUT), "-", _fig_n[0], "hình,", _tab_n[0], "bảng")
