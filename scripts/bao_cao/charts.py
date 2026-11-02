"""Vẽ toàn bộ hình của báo cáo khởi nghiệp vào docs/bao-cao/hinh/. Chạy: python charts.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, RegularPolygon, Rectangle, FancyArrowPatch
import numpy as np
import model as M

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "bao-cao", "hinh")
os.makedirs(OUT, exist_ok=True)

NAVY, RED, GREEN, AMBER, GREY, LIGHT, YELLOW = "#1F3352", "#A3281A", "#17653A", "#B7791F", "#6B7280", "#EEF2F7", "#F2CF3D"
PAPER = "#F3F0E8"
plt.rcParams.update({"font.family": "Times New Roman", "font.size": 11, "axes.edgecolor": GREY,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#E3E6EA",
                     "axes.axisbelow": True, "savefig.dpi": 200, "savefig.bbox": "tight"})


def vn(x, d=1):
    """Số kiểu Việt Nam: 1.234,5"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "#").replace(".", ",").replace("#", ".")


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), facecolor="white")
    plt.close(fig)


def box(ax, x, y, w, h, fc="white", ec=NAVY, lw=1.6, r=0.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))


def blank(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    return fig, ax


def hexcard(ax, x, y, sym, color, r=0.5, fs=20):
    ax.add_patch(RegularPolygon((x, y), 6, radius=r, orientation=np.pi / 6, fc=color, ec=NAVY, lw=2))
    ax.text(x, y + 0.05, sym, ha="center", va="center", fontsize=fs, weight="bold", color="white" if color != "white" else NAVY)
    ax.add_patch(Rectangle((x - 0.1, y - 0.33), 0.2, 0.14, fc="black", ec="white", lw=0.8))   # mã ArUco thu nhỏ


# ---------------- Hình bìa: phân tử ghép bằng thẻ lục giác ----------------
def cover():
    fig, ax = blank((7, 3.0))
    ax.set_xlim(-0.2, 9.2); ax.set_ylim(-1.4, 1.8); ax.set_aspect("equal")
    dx, dy = 0.75, 0.433   # hai thẻ lục giác chung cạnh
    hexcard(ax, 1.2, 0.3, "O", RED); hexcard(ax, 1.2 - dx, 0.3 + dy, "H", "#4B6584"); hexcard(ax, 1.2 + dx, 0.3 + dy, "H", "#4B6584")
    ax.text(1.2, -0.9, "H₂O", ha="center", fontsize=16, color=NAVY, weight="bold")
    hexcard(ax, 3.7, 0.3, "O", RED); hexcard(ax, 3.7 + dx, 0.3 + dy, "C", "#2D2D2D"); hexcard(ax, 3.7 + 2 * dx, 0.3, "O", RED)
    ax.text(3.7 + dx, -0.9, "CO₂", ha="center", fontsize=16, color=NAVY, weight="bold")
    hexcard(ax, 7.4, 0.3, "N", "#2E6F9E")
    hexcard(ax, 7.4 - dx, 0.3 + dy, "H", "#4B6584"); hexcard(ax, 7.4 + dx, 0.3 + dy, "H", "#4B6584"); hexcard(ax, 7.4 + dx, 0.3 - dy, "H", "#4B6584")
    ax.text(7.2, -0.9, "NH₃", ha="center", fontsize=16, color=NAVY, weight="bold")
    save(fig, "h00_bia")


# ---------------- Hình: quy trình nhận diện → chấm → phản hồi ----------------
def pipeline():
    fig, ax = blank((11, 3.6))
    ax.set_xlim(0, 11); ax.set_ylim(0, 3.6)
    steps = [("1. GHÉP THẺ", "Học sinh ghép thẻ\nlục giác in sẵn", LIGHT),
             ("2. NHẬN DIỆN", "Mã ArUco: OpenCV\n(ngoại tuyến, 0 đồng)\nThẻ thường: Gemini", "white"),
             ("3. ĐO LIÊN KẾT", "Hình học OpenCV:\nthẻ nào chạm thẻ nào\n→ đồ thị phân tử", LIGHT),
             ("4. CHẤM", "Đối sánh đồ thị\nvới 70 chất\n(thuật toán xác định)", "white"),
             ("5. PHẢN HỒI", "Đúng / sai ở đâu / vì sao\nGợi ý, sao, huy hiệu\nBáo cáo giáo viên", LIGHT)]
    for i, (t, d, fc) in enumerate(steps):
        x = 0.15 + i * 2.18
        box(ax, x, 0.7, 1.95, 2.3, fc=fc, ec=RED if i == 3 else NAVY, lw=2 if i == 3 else 1.5)
        ax.text(x + 0.975, 2.62, t, ha="center", weight="bold", color=NAVY, fontsize=12)
        ax.text(x + 0.975, 1.65, d, ha="center", va="center", fontsize=10.5, linespacing=1.5)
        if i < 4:
            ax.annotate("", (x + 2.17, 1.85), (x + 1.97, 1.85), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.8))
    ax.add_patch(Rectangle((2.33, 0.25), 1.95, 0.3, fc=YELLOW, ec="none"))
    ax.text(3.3, 0.4, "AI hỗ trợ nhận diện", ha="center", va="center", fontsize=10.5, weight="bold")
    ax.add_patch(Rectangle((4.51, 0.25), 4.13, 0.3, fc=GREEN, ec="none"))
    ax.text(6.57, 0.4, "Thuật toán chấm theo cấu trúc, giải thích được", ha="center", va="center", fontsize=10.5, color="white", weight="bold")
    save(fig, "h01_quy_trinh")


# ---------------- Business Model Canvas ----------------
def canvas():
    fig, ax = blank((12.5, 7.2))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    cells = [  # x, y, w, h, số, tiêu đề, nội dung
        (0, 2, 2, 4, 8, "ĐỐI TÁC CHÍNH", "• Trường THCS thử nghiệm\n• Phòng/Sở GD&ĐT\n• Đơn vị thiết bị\n  giáo dục, NXB\n• Xưởng in, ép thẻ\n• Google (Gemini),\n  Vercel, Upstash"),
        (2, 4, 2, 2, 7, "HOẠT ĐỘNG CHÍNH", "• Phát triển phần mềm\n• Biên soạn bộ đề, giáo án\n• In bộ thẻ có mã\n• Thao giảng, tập huấn"),
        (2, 2, 2, 2, 6, "NGUỒN LỰC CHÍNH", "• Lõi đối sánh 70 chất\n• Bộ nhận diện ArUco\n• 245 + 113 kiểm thử\n• Giáo viên hướng dẫn KHTN"),
        (4, 2, 2, 4, 2, "GIẢI PHÁP GIÁ TRỊ", "• Học sinh \"chạm\" được\n  phân tử, biết ngay\n  đúng/sai ở đâu, vì sao\n• Giáo viên thấy cả lớp\n  kẹt ở đâu trong tiết\n• Thẻ giấy rẻ, chạy trên\n  điện thoại/máy có sẵn\n• Thẻ có mã: ngoại tuyến,\n  không gửi ảnh ra ngoài"),
        (6, 4, 2, 2, 4, "QUAN HỆ KHÁCH HÀNG", "• Cộng đồng giáo viên\n  KHTN cốt cán\n• Tập huấn, hỗ trợ\n  trực tuyến"),
        (6, 2, 2, 2, 3, "KÊNH PHÂN PHỐI", "• Thao giảng tổ chuyên môn\n• Web miễn phí (Vercel)\n• Hộp thẻ có mã QR\n• Đại lý thiết bị"),
        (8, 2, 2, 4, 1, "KHÁCH HÀNG", "• Trường THCS\n  (người mua)\n• Giáo viên KHTN\n  6-9 (người dùng\n  chính)\n• Học sinh, phụ huynh\n• CLB STEM,\n  trung tâm"),
        (0, 0, 5, 2, 9, "CƠ CẤU CHI PHÍ (năm 3)", ""),
        (5, 0, 5, 2, 5, "DÒNG DOANH THU (năm 3)", ""),
    ]
    for x, y, w, h, n, t, d in cells:
        box(ax, x + 0.03, y + 0.03, w - 0.06, h - 0.06, fc=LIGHT if n in (2, 5, 9) else "white", ec=RED if n == 2 else NAVY)
        ax.text(x + 0.15, y + h - 0.25, f"{n}. {t}", weight="bold", color=NAVY, fontsize=9.4)
        ax.text(x + 0.15, y + h - 0.5, d, va="top", fontsize=9.6, linespacing=1.35)
    P = M.pnl()[2]
    cost = [("Nhân sự", M.OPEX["Nhân sự kỹ thuật (cộng tác viên)"][2]), ("Giá vốn thẻ, tập huấn", P["cogs"] - M.CLOUD[2]),
            ("Tiếp thị", M.OPEX["Tiếp thị, thao giảng, hội thảo"][2]), ("Khác", 0), ("Đám mây", M.CLOUD[2])]
    tot = P["cogs"] + P["opex"]
    cost[3] = ("Vận hành, học liệu, khác", tot - sum(c[1] for c in cost))
    rv = M.revenue_lines()
    rev = sorted(((M.REV_LABELS[k], v[2]) for k, v in rv.items()), key=lambda t: -t[1])
    for (x0, items, total) in ((0.15, cost, tot), (5.15, rev, P["rev"])):
        for i, (lab, v) in enumerate(items):
            yy = 1.42 - i * 0.22
            ax.add_patch(Rectangle((x0 + 1.85, yy - 0.07), 2.6 * v / total, 0.14, fc=RED if x0 > 1 else NAVY, ec="none"))
            ax.text(x0, yy, lab, va="center", fontsize=9.4)
            ax.text(x0 + 1.9 + 2.6 * v / total, yy, f"{vn(100 * v / total)}%", va="center", fontsize=9)
    save(fig, "h02_canvas")


# ---------------- Giá trị cho bốn bên ----------------
def stakeholders():
    fig, ax = blank((12, 3.6))
    ax.set_xlim(0, 12); ax.set_ylim(0, 3.6)
    cpl = M.PRICE["school"] * 1e6 / (12 * 35)
    cards = [("HỌC SINH", "70 chất", "đối sánh theo cấu trúc; nêu\nliên kết thừa, thiếu và\ngiải thích \"Vì sao?\""),
             ("GIÁO VIÊN", "8 nhóm", "theo dõi cùng lúc trên\nbảng điều khiển lớp, thấy\nnhóm kẹt, câu sai nhiều"),
             ("NHÀ TRƯỜNG", f"{vn(cpl, 0)} đ", "mỗi học sinh mỗi năm\n(gói Trường 6 triệu đồng,\n12 lớp × 35 em)"),
             ("PHỤ HUYNH", "249.000 đ", "một bộ thẻ gia đình dùng\ncả năm lớp 7-9; phần mềm\nmiễn phí, không quảng cáo")]
    for i, (t, big, d) in enumerate(cards):
        x = 0.1 + i * 3
        box(ax, x, 0.15, 2.8, 3.3, fc=LIGHT if i % 2 == 0 else "white")
        ax.text(x + 1.4, 3.0, t, ha="center", weight="bold", color=GREY, fontsize=13)
        ax.text(x + 1.4, 2.0, big, ha="center", weight="bold", color=RED, fontsize=26)
        ax.text(x + 1.4, 0.85, d, ha="center", va="center", fontsize=10.5, linespacing=1.45)
    save(fig, "h03_gia_tri")


# ---------------- TAM / SAM / SOM ----------------
def funnel():
    tam_l, tam, sam, som = M.market()
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [1.2, 1]})
    ax.set_axis_off(); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    for i, (lab, v, w, c) in enumerate((("TAM", tam, 9.6, NAVY), ("SAM", sam, 6.6, "#4B6584"), ("SOM (năm 3)", som, 3.6, RED))):
        y = 4.2 - i * 1.9
        ax.add_patch(Rectangle(((10 - w) / 2, y), w, 1.6, fc=c, ec="white"))
        ax.text(5, y + 1.05, lab, ha="center", color="white", weight="bold", fontsize=14)
        ax.text(5, y + 0.45, f"{vn(v, 2)} tỷ đồng/năm", ha="center", color="white", fontsize=12)
    ax2.set_title("Cơ cấu TAM theo nhóm khách hàng (tỷ đồng)", fontsize=12, color=NAVY)
    labs, vals = zip(*sorted(tam_l.items(), key=lambda t: t[1]))
    ax2.barh(labs, vals, color=[NAVY, NAVY, NAVY, RED][:len(vals)], height=0.55)
    for i, v in enumerate(vals):
        ax2.text(v + 5, i, vn(v, 2), va="center")
    ax2.set_xlim(0, max(vals) * 1.22); ax2.grid(axis="y", visible=False)
    save(fig, "h04_thi_truong")


# ---------------- Ma trận mức sẵn sàng của sản phẩm ----------------
READY = [  # tính năng, đã làm, kiểm thử tự động, kiểm chứng thực tế (0 chưa, 1 một phần, 2 đủ)
    ("Đọc mã ArUco trên thẻ (22 nguyên tố)", 2, 2, 1),
    ("Gemini đọc thẻ thường", 2, 2, 1),
    ("Đo liên kết bằng hình học", 2, 2, 0),
    ("Đối sánh 70 chất, chẩn đoán lỗi", 2, 2, 0),
    ("Kiểm tra chất lượng ảnh", 2, 2, 1),
    ("Giải thích \"Vì sao?\", quan niệm sai", 2, 2, 0),
    ("Thử thách 11 bộ đề, sao, huy hiệu", 2, 2, 1),
    ("Cân bằng 24 phương trình (lớp 8)", 2, 2, 1),
    ("Lớp học trực tuyến (Upstash Redis)", 2, 1, 0),
    ("Bộ thẻ in PDF lớp 7, 8, 9", 2, 2, 0),
    ("Triển khai Vercel", 2, 0, 0),
    ("Thử nghiệm đối chứng với học sinh", 1, 1, 0),
]


def readiness():
    fig, ax = plt.subplots(figsize=(9, 6.2))
    data = np.array([r[1:] for r in READY])
    cmap = matplotlib.colors.ListedColormap(["#F4D6D2", "#F6E7C1", "#CFE6D7"])
    ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=2)
    txt = {0: "Chưa", 1: "Một phần", 2: "Đã xong"}
    for i in range(len(READY)):
        for j in range(3):
            ax.text(j, i, txt[data[i, j]], ha="center", va="center", fontsize=10.5,
                    color={0: RED, 1: AMBER, 2: GREEN}[data[i, j]], weight="bold")
    ax.set_xticks(range(3), ["Đã lập trình", "Kiểm thử tự động", "Kiểm chứng thực tế\n(thẻ thật, lớp thật)"])
    ax.set_yticks(range(len(READY)), [r[0] for r in READY])
    ax.xaxis.tick_top(); ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, 3), minor=True); ax.set_yticks(np.arange(-.5, len(READY)), minor=True)
    ax.grid(which="minor", color="white", lw=3); ax.tick_params(which="both", length=0)
    save(fig, "h05_san_sang")


# ---------------- Ma trận cạnh tranh ----------------
COMP_COLS = ["CHEM VISION", "Happy Atoms", "PhET", "Osmo", "Labster", "Bi–que"]
COMP_ROWS = [  # 0 chưa có, 1 một phần, 2 đầy đủ
    ("Thao tác bằng vật thật", (2, 2, 0, 2, 0, 2)),
    ("Kiểm tra cấu trúc (đồng phân, liên kết)", (2, 2, 1, 0, 0, 0)),
    ("Phản hồi tức thì, nói rõ sai ở đâu", (2, 1, 1, 1, 1, 0)),
    ("Dữ liệu cả lớp cho giáo viên", (2, 1, 0, 0, 2, 0)),
    ("Tiếng Việt, bám KHTN 6-9", (2, 0, 1, 0, 0, 1)),
    ("Chi phí thấp cho trường", (2, 1, 2, 0, 0, 2)),
    ("Chạy ngoại tuyến", (1, 1, 2, 2, 0, 2)),
    ("Bằng chứng học tập đã công bố", (0, 2, 1, 1, 1, 1)),
]


def competition():
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    data = np.array([r[1] for r in COMP_ROWS])
    cmap = matplotlib.colors.ListedColormap(["#F7F7F7", "#BFCBDB", NAVY])
    ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=2)
    sym = {0: "–", 1: "◐", 2: "●"}
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, sym[data[i, j]], ha="center", va="center", fontsize=15, color="white" if data[i, j] == 2 else NAVY, fontfamily="DejaVu Sans")
    ax.set_xticks(range(len(COMP_COLS)), COMP_COLS, weight="bold"); ax.xaxis.tick_top()
    ax.set_yticks(range(len(COMP_ROWS)), [r[0] for r in COMP_ROWS])
    ax.set_xticks(np.arange(-.5, len(COMP_COLS)), minor=True); ax.set_yticks(np.arange(-.5, len(COMP_ROWS)), minor=True)
    ax.grid(False); ax.grid(which="minor", color="white", lw=3); ax.tick_params(which="both", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.add_patch(Rectangle((-0.5, -0.5), 1, len(COMP_ROWS), fill=False, ec=RED, lw=2.5))
    ax.text(len(COMP_COLS) - 0.5, len(COMP_ROWS) + 0.1, "●  đầy đủ     ◐  một phần     –  chưa có", ha="right", va="top", fontsize=10, color=GREY, fontfamily="DejaVu Sans")
    save(fig, "h06_canh_tranh")


def positioning():
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    pts = [  # tên, chi phí ban đầu cho một lớp (triệu đồng, ước tính), mức phản hồi (0-10, đánh giá định tính)
        ("CHEM VISION", 1.2, 8.5, RED), ("Happy Atoms", 8.0, 7.0, NAVY), ("PhET", 0.05, 5.0, NAVY),
        ("Osmo", 12.0, 4.0, NAVY), ("Labster", 20.0, 6.0, NAVY), ("Bộ bi–que", 2.0, 1.0, NAVY)]
    for n, x, y, c in pts:
        ax.scatter(x, y, s=420 if c == RED else 220, color=c, zorder=3, edgecolor="white", lw=1.5)
        ax.annotate(n, (x, y), xytext=(10, 8), textcoords="offset points", fontsize=11.5, weight="bold" if c == RED else None, color=c)
    ax.set_xscale("log"); ax.set_xlim(0.03, 40); ax.set_ylim(0, 10)
    ax.set_xticks([0.05, 0.1, 0.5, 1, 2, 5, 10, 20], ["0,05", "0,1", "0,5", "1", "2", "5", "10", "20"])
    ax.axvline(2.5, color=GREY, ls=":", lw=1); ax.axhline(5.5, color=GREY, ls=":", lw=1)
    ax.text(0.035, 9.5, "Rẻ, phản hồi cao\n(vị trí mục tiêu)", color=GREEN, fontsize=10.5, va="top", weight="bold")
    ax.text(38, 0.3, "Đắt, phản hồi thấp", color=GREY, fontsize=10.5, ha="right")
    ax.set_xlabel("Chi phí ban đầu cho một lớp 8 nhóm (triệu đồng, thang log, ước tính)")
    ax.set_ylabel("Mức phản hồi về cấu trúc và lỗi sai (0-10, đánh giá định tính)")
    save(fig, "h07_dinh_vi")


def swot():
    fig, ax = blank((11, 6.4))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    q = [(0, 3, "S", "ĐIỂM MẠNH", GREEN, "• Kết luận bằng thuật toán, giải thích được\n• Thẻ có mã đọc ngoại tuyến, 0 đồng/lượt\n• 70 chất, 24 phương trình, bám KHTN 6-9\n• 245 kiểm thử lõi + 113 kiểm thử giao diện\n• Không cần cài đặt, chạy trên điện thoại"),
         (5, 3, "W", "ĐIỂM YẾU", RED, "• Chưa thử nghiệm với học sinh thật\n• Độ chính xác Gemini với thẻ thật chưa đo\n• Chưa triển khai thật lên Vercel, Upstash\n• Chưa có glucozơ, polime, kim loại\n• Nhóm học sinh, thời gian có hạn"),
         (0, 0, "O", "CƠ HỘI", NAVY, "• Chương trình GDPT 2018 gộp môn KHTN,\n  giáo viên cần công cụ dạy tích hợp\n• Chủ trương chuyển đổi số, STEM ở THCS\n• Nhiều trường thiếu thiết bị thí nghiệm\n• Mở rộng sang Vật lý, Sinh học bằng thẻ"),
         (5, 0, "T", "THÁCH THỨC", AMBER, "• Mua sắm công kéo dài theo năm ngân sách\n• Phụ thuộc giá, hạn mức của Google\n• Đối thủ lớn có thể nội địa hóa\n• Phần mềm miễn phí (PhET) quen thuộc\n• Quy định bảo vệ dữ liệu học sinh")]
    for x, y, letter, t, c, d in q:
        box(ax, x + 0.05, y + 0.05, 4.9, 2.9, fc="white", ec=c, lw=2)
        ax.add_patch(Rectangle((x + 0.05, y + 2.35), 4.9, 0.6, fc=c, ec=c))
        ax.text(x + 0.3, y + 2.65, f"{letter}  |  {t}", color="white", weight="bold", va="center", fontsize=13)
        ax.text(x + 0.3, y + 2.15, d, va="top", fontsize=10.8, linespacing=1.5)
    save(fig, "h08_swot")


def decision_cycle():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    seg = [("Phụ huynh (bộ gia đình)", 1, 7, 0.249), ("Giáo viên (gói Pro)", 1, 14, 0.39), ("CLB STEM, trung tâm", 14, 45, 3.0),
           ("Trường tư thục, tự chủ", 30, 90, 7.2), ("Trường công lập", 90, 180, 7.2)]
    for i, (n, a, b, budget) in enumerate(seg):
        ax.barh(i, b - a, left=a, color=RED if i < 2 else NAVY, height=0.5)
        ax.text(b + 3, i, f"{a}-{b} ngày  ·  {vn(budget, 3 if budget < 1 else 1)} tr. đồng/lần mua", va="center", fontsize=10.5)
    ax.set_yticks(range(len(seg)), [s[0] for s in seg]); ax.invert_yaxis()
    ax.set_xlim(0, 290); ax.set_xlabel("Thời gian từ lần dùng thử đầu tiên đến khi trả tiền (ngày, ước tính)")
    ax.grid(axis="y", visible=False)
    save(fig, "h09_chu_ky_mua")


def flywheel():
    fig, ax = blank((9, 5))
    ax.set_xlim(-5, 5); ax.set_ylim(-2.9, 2.9); ax.set_aspect("equal")
    nodes = ["Thao giảng tại\ntổ chuyên môn", "Dùng thử miễn phí\n1 học kỳ", "Ký gói Trường\n+ bộ thẻ lớp",
             "Học sinh mang\nhộp thẻ QR về nhà", "Phụ huynh mua\nbộ gia đình", "Giáo viên chia sẻ\nbộ đề, kết quả"]
    R = 2.2
    pos = [(R * 1.6 * np.cos(np.pi / 2 - i * 2 * np.pi / 6), R * np.sin(np.pi / 2 - i * 2 * np.pi / 6)) for i in range(6)]
    for i, ((x, y), n) in enumerate(zip(pos, nodes)):
        box(ax, x - 1.15, y - 0.42, 2.3, 0.84, fc=LIGHT if i % 2 else "white", ec=RED if i in (2, 4) else NAVY, r=0.12)
        ax.text(x, y, n, ha="center", va="center", fontsize=10.2)
        x2, y2 = pos[(i + 1) % 6]
        ax.add_patch(FancyArrowPatch((x, y), (x2, y2), connectionstyle="arc3,rad=-0.25", arrowstyle="-|>", mutation_scale=16,
                                     color=GREY, lw=1.4, shrinkA=32, shrinkB=32))
    ax.text(0, 0.15, "VÒNG LAN TỎA", ha="center", weight="bold", color=NAVY, fontsize=13)
    ax.text(0, -0.3, "người giới thiệu là giáo viên,\nkhông phải quảng cáo", ha="center", va="top", fontsize=10, color=GREY)
    save(fig, "h10_vong_lan_toa")


def revenue():
    lines = M.revenue_lines(); P = M.pnl()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    items = sorted(((M.REV_LABELS[k], v[2]) for k, v in lines.items()), key=lambda t: -t[1])
    cols = [NAVY, RED, "#4B6584", AMBER, GREEN, GREY]
    w, _ = a1.pie([v for _, v in items], colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.38, ec="white"))
    a1.text(0, 0.06, vn(P[2]["rev"] / 1000, 2), ha="center", fontsize=18, weight="bold", color=NAVY)
    a1.text(0, -0.18, "tỷ đồng năm 3", ha="center", fontsize=10, color=GREY)
    a1.legend(w, [f"{n}  {vn(100 * v / P[2]['rev'])}%" for n, v in items], loc="upper center", bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=10, ncol=2)
    x = np.arange(3)
    a2.bar(x - 0.2, [p["rev"] for p in P], 0.4, color=NAVY, label="Doanh thu thuần")
    a2.bar(x + 0.2, [p["ni"] for p in P], 0.4, color=RED, label="Lợi nhuận ròng")
    for i, p in enumerate(P):
        a2.text(i - 0.2, p["rev"] + 80, vn(p["rev"]), ha="center", fontsize=10)
        a2.text(i + 0.2, p["ni"] + 80, vn(p["ni"]), ha="center", fontsize=10, color=RED)
    a2.set_xticks(x, M.YEARS); a2.set_ylabel("triệu đồng"); a2.legend(frameon=False); a2.grid(axis="x", visible=False)
    save(fig, "h11_doanh_thu")


def costs():
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1, 1.2]})
    items = sorted(M.CAPEX.items(), key=lambda t: -t[1])
    cols = [NAVY, RED, "#4B6584", AMBER, GREEN, GREY]
    w, _ = a1.pie([v for _, v in items], colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.38, ec="white"))
    a1.text(0, 0.05, f"{sum(M.CAPEX.values())}", ha="center", fontsize=20, weight="bold", color=NAVY)
    a1.text(0, -0.2, "triệu đồng CAPEX", ha="center", fontsize=10, color=GREY)
    a1.legend(w, [f"{n}: {v}" for n, v in items], loc="upper center", bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=9.5, ncol=1)
    bottom = np.zeros(3)
    for (n, v), c in zip(M.OPEX.items(), cols):
        a2.bar(M.YEARS, v, bottom=bottom, color=c, label=n, width=0.55)
        bottom += v
    for i, b in enumerate(bottom):
        a2.text(i, b + 40, vn(b, 0), ha="center", weight="bold")
    a2.set_ylabel("triệu đồng/năm"); a2.legend(frameon=False, fontsize=9.5, loc="upper left"); a2.grid(axis="x", visible=False)
    a2.set_ylim(0, bottom.max() * 1.15)
    save(fig, "h12_chi_phi")


def cloud_cost():
    fig, ax = plt.subplots(figsize=(10, 4.2))
    cases = [("100% thẻ thường, Gemini 2.5 Flash", M.per_lesson_vnd(1.0)), ("100% thẻ thường, Flash-Lite", M.per_lesson_vnd(1.0, "lite")),
             (f"Bộ thẻ in mã, {int(M.GEMINI_SHARE * 100)}% thẻ thường (cơ sở)", M.per_lesson_vnd(M.GEMINI_SHARE)),
             ("100% thẻ có mã ArUco", 0.0)]
    names, vals = zip(*cases)
    ax.barh(names, vals, color=[GREY, GREY, NAVY, GREEN], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v + 25, i, f"{vn(v, 0)} đồng/tiết", va="center", fontsize=11, weight="bold" if i >= 2 else None)
    ax.invert_yaxis(); ax.set_xlim(0, max(vals) * 1.3); ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"Chi phí gọi AI cho một tiết ({M.GROUPS} nhóm × {M.CHECKS_PER_GROUP} lượt KIỂM TRA)")
    save(fig, "h13_gia_von_tiet")


def pricing():
    fig, ax = blank((12, 4.3))
    ax.set_xlim(0, 12); ax.set_ylim(0, 4.3)
    tiers = [("MIỄN PHÍ", "0 đ", "Ứng dụng web đầy đủ\nPDF bộ thẻ tự in\nThử thách, cân bằng PT\nNhật ký trong trình duyệt", "white"),
             ("BỘ THẺ GIA ĐÌNH", "249.000 đ", "Thẻ ép nhựa có mã\nmột lần mua\ndùng cả lớp 7-9\nhộp có mã QR hướng dẫn", LIGHT),
             ("GIÁO VIÊN PRO", "390.000 đ/năm", "Bộ đề tự tạo\nBáo cáo quan niệm sai\nXuất CSV, lưu đám mây\n(≈ 32.500 đ/tháng)", "white"),
             ("BỘ THẺ LỚP HỌC", "1,2 triệu đ", "8 bộ thẻ ép nhựa\ncho 8 nhóm\nhộp đựng, thẻ dự phòng\nmột lần mua", LIGHT),
             ("GÓI TRƯỜNG", "6 triệu đ/năm", "Lớp học trực tuyến\nkhông giới hạn lớp\nBảng điều khiển, báo cáo\ntập huấn trực tuyến", "white")]
    for i, (t, p, d, fc) in enumerate(tiers):
        x = 0.1 + i * 2.38
        box(ax, x, 0.1, 2.25, 4.0, fc=fc, ec=RED if i == 4 else NAVY, lw=2.2 if i == 4 else 1.5)
        ax.text(x + 1.125, 3.7, t, ha="center", weight="bold", color=GREY, fontsize=11.5)
        ax.text(x + 1.125, 3.05, p, ha="center", weight="bold", color=RED, fontsize=15)
        ax.plot([x + 0.3, x + 1.95], [2.65, 2.65], color="#D0D5DC", lw=1)
        ax.text(x + 1.125, 1.5, d, ha="center", va="center", fontsize=10.3, linespacing=1.6)
    ax.annotate("", (11.8, 0.0), (0.2, 0.0), arrowprops=dict(arrowstyle="-|>", color=GREY))
    save(fig, "h14_bang_gia")


def waterfall():
    P = M.pnl()[2]
    steps = [("Doanh thu thuần", P["rev"], "total"), ("Giá vốn", -P["cogs"], "d"), ("Lợi nhuận gộp", P["gp"], "total"),
             ("Chi phí hoạt động", -P["opex"], "d"), ("Khấu hao", -P["dep"], "d"), ("Thuế TNDN", -P["tax"], "d"),
             ("Lợi nhuận ròng", P["ni"], "total")]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    run = 0
    for i, (n, v, k) in enumerate(steps):
        if k == "total":
            ax.bar(i, v, color=NAVY if i < 6 else RED, width=0.6); run = v; top = v
        else:
            ax.bar(i, v, bottom=run, color="#C9CFD8", width=0.6, edgecolor=GREY); top = run; run += v
        ax.text(i, top + 90, vn(v), ha="center", fontsize=10.5, weight="bold" if k == "total" else None)
    ax.set_xticks(range(len(steps)), [s[0] for s in steps]); ax.set_ylabel("triệu đồng"); ax.grid(axis="x", visible=False)
    ax.set_ylim(0, P["rev"] * 1.12)
    save(fig, "h15_thac_nuoc")


def unit_breakeven():
    U = M.unit_economics(); P = M.pnl()
    fig = plt.figure(figsize=(12, 4.8))
    axc = fig.add_axes([0, 0, 0.42, 1]); axc.set_axis_off(); axc.set_xlim(0, 4.2); axc.set_ylim(0, 4.2)
    cards = [("CAC trường", f"{vn(U['cac_school'], 1)} tr.đ", "tiếp thị + 30% nhân sự\nthao giảng / trường mới"),
             ("LTV trường", f"{vn(U['ltv_school'], 1)} tr.đ", f"gia hạn {int(U['renew'] * 100)}% → vòng đời\n{vn(U['life'], 0)} năm"),
             ("LTV / CAC", f"{vn(U['ltv_cac'], 1)} lần", "ngưỡng an toàn\nthường dùng: 3 lần"),
             ("Thu hồi CAC", f"{vn(U['payback_m'], 1)} tháng", "theo lợi nhuận gộp\ngói Trường")]
    for i, (t, big, d) in enumerate(cards):
        x, y = (i % 2) * 2.1 + 0.05, (1 - i // 2) * 2.1 + 0.05
        box(axc, x, y, 1.95, 1.95, fc=LIGHT if i == 2 else "white", ec=RED if i == 2 else NAVY)
        axc.text(x + 0.975, y + 1.6, t, ha="center", weight="bold", color=GREY, fontsize=11.5)
        axc.text(x + 0.975, y + 1.0, big, ha="center", weight="bold", color=RED if i == 2 else NAVY, fontsize=17)
        axc.text(x + 0.975, y + 0.38, d, ha="center", va="center", fontsize=9.5, linespacing=1.4)
    ax = fig.add_axes([0.5, 0.12, 0.48, 0.82])
    a = P[0]["rev"] / 78
    m = np.arange(0, 13)
    ax.plot(m, a * m, color=RED, lw=2.5, label="Doanh thu tháng (giả định tăng đều năm 1)")
    ax.axhline(U["be_rev"], color=NAVY, ls="--", lw=2, label=f"Ngưỡng hòa vốn: {vn(U['be_rev'], 1)} triệu đồng/tháng")
    be_m = U["be_rev"] / a
    ax.scatter([be_m], [U["be_rev"]], s=90, color=NAVY, zorder=3)
    ax.annotate(f"Hòa vốn hoạt động\nkhoảng tháng {int(np.ceil(be_m))}", (be_m, U["be_rev"]), xytext=(be_m + 1.5, U["be_rev"] - 25),
                arrowprops=dict(arrowstyle="->"), fontsize=11)
    ax.set_xlabel("Tháng vận hành thứ (năm 1)"); ax.set_ylabel("triệu đồng/tháng"); ax.legend(frameon=False, fontsize=10, loc="upper left")
    ax.set_xlim(0, 12.5); ax.set_ylim(0, a * 12 * 1.15)
    save(fig, "h16_kinh_te_don_vi")


def cashflow():
    cash = M.monthly_cash()
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    m = np.arange(0, 37); c = [-sum(M.CAPEX.values())] + cash
    ax.fill_between(m, c, 0, where=np.array(c) < 0, color="#F4D6D2", step=None)
    ax.fill_between(m, c, 0, where=np.array(c) >= 0, color="#CFE6D7")
    ax.plot(m, c, color=NAVY, lw=2.2)
    pb = next(i + 1 for i, v in enumerate(cash) if v >= 0)
    ax.axvline(pb, color=RED, ls="--"); ax.text(pb + 0.5, max(c) * 0.55, f"Thu hồi vốn\ntháng {pb}", color=RED, fontsize=12, weight="bold")
    ax.text(36, c[-1], vn(c[-1], 0), ha="right", va="bottom", weight="bold")
    ax.axhline(0, color=GREY, lw=1); ax.set_xticks([0, 6, 12, 18, 24, 30, 36])
    ax.set_xlabel("Tháng vận hành"); ax.set_ylabel("Dòng tiền lũy kế (triệu đồng)")
    save(fig, "h17_dong_tien")


def sensitivity():
    base, rows = M.tornado(); S = M.scenarios()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
    for i, (n, lo, hi) in enumerate(rows):
        a1.barh(i, lo - base, left=base, color=RED, height=0.55)
        a1.barh(i, hi - base, left=base, color=NAVY, height=0.55)
        a1.text(min(lo, hi) - 30, i, vn(min(lo, hi), 0), ha="right", va="center", fontsize=9.5)
        a1.text(max(lo, hi) + 30, i, vn(max(lo, hi), 0), ha="left", va="center", fontsize=9.5)
    a1.axvline(base, color="black", lw=1)
    a1.barh([], [], color=RED, label="Giả định giảm 20%"); a1.barh([], [], color=NAVY, label="Giả định tăng 20%")
    a1.legend(frameon=False, fontsize=9.5, loc="lower right")
    a1.set_yticks(range(len(rows)), [r[0] for r in rows]); a1.grid(axis="y", visible=False)
    a1.set_xlabel(f"Lợi nhuận trước thuế năm 3 khi giả định lệch ±20% (cơ sở {vn(base, 0)} triệu đồng)")
    lo = min(r[1] for r in rows + [("", base, base)]); hi = max(r[2] for r in rows)
    a1.set_xlim(min(min(r[1], r[2]) for r in rows) - 500, max(max(r[1], r[2]) for r in rows) + 500)
    names = list(S)
    a2.bar(names, [S[n]["rev"] for n in names], color="#C9CFD8", width=0.55, label="Doanh thu")
    a2.bar(names, [S[n]["ni"] for n in names], color=[RED, NAVY, GREEN], width=0.55, label="Lợi nhuận ròng")
    for i, n in enumerate(names):
        a2.text(i, S[n]["rev"] + 100, vn(S[n]["rev"], 0), ha="center", fontsize=10)
        a2.text(i, S[n]["ni"] / 2, vn(S[n]["ni"], 0), ha="center", color="white", weight="bold", fontsize=10)
    a2.set_xticks(range(3), ["Xấu\n(−40% lượng bán)", "Cơ sở", "Tốt\n(+30% lượng bán)"])
    a2.set_ylabel("triệu đồng, năm 3"); a2.legend(frameon=False, fontsize=9.5); a2.grid(axis="x", visible=False)
    save(fig, "h18_do_nhay")


def roadmap():
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    quarters = ["Q1/27", "Q2/27", "Q3/27", "Q4/27", "Q1/28", "Q2/28", "Q3/28", "Q4/28", "Q1/29", "Q2/29", "Q3/29", "Q4/29", "Q1/30"]
    tasks = [("GĐ0  Kiểm chứng: in thẻ thật, đo độ chính xác, triển khai Vercel", 0, 1, GREY),
             ("GĐ0  Thử nghiệm đối chứng 2-4 lớp (thử), sau đó ≥ 9 lớp mỗi nhóm", 0, 3, GREY),
             ("GĐ1  Thương mại hóa: 40 trường Phú Thọ, Vĩnh Phúc, Hà Nội", 1, 4, NAVY),
             ("GĐ1  Bộ thẻ gia đình qua cửa hàng trực tuyến", 2, 4, NAVY),
             ("GĐ2  Mở rộng 150 trường miền Bắc, đối tác thiết bị", 5, 4, "#4B6584"),
             ("GĐ2  Thêm Vật lý, Sinh học bằng thẻ; tài khoản, PostgreSQL", 5, 4, "#4B6584"),
             ("GĐ3  450 trường toàn quốc; liên kết NXB, Sở GD&ĐT", 9, 4, RED)]
    for i, (n, s, d, c) in enumerate(tasks):
        ax.barh(i, d, left=s, color=c, height=0.55)
    for x, lab in ((1, "Năm 1 bắt đầu"), (5, "Năm 2"), (9, "Năm 3")):
        ax.axvline(x, color=RED, ls=":", lw=1.2); ax.text(x + 0.05, -0.8, lab, color=RED, fontsize=10)
    ax.set_xticks(np.arange(len(quarters)) + 0.5, quarters, fontsize=10, rotation=45); ax.set_xlim(0, 13)
    ax.set_yticks(range(len(tasks)), [t[0] for t in tasks], fontsize=12); ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(tasks) - 0.4, -1.1); ax.grid(axis="y", visible=False)
    save(fig, "h19_lo_trinh")


RISKS = [  # mã, tên, (khả năng, ảnh hưởng) trước, sau  — thang 1-5
    ("R1", "Gemini đọc sai thẻ thường", (4, 4), (2, 2)),
    ("R2", "Giá, hạn mức, đổi tên model Google", (3, 4), (2, 2)),
    ("R3", "Kết quả thử nghiệm không vượt trội", (3, 5), (3, 3)),
    ("R4", "Mua sắm công kéo dài", (4, 4), (3, 3)),
    ("R5", "Dữ liệu, quyền riêng tư học sinh", (2, 5), (1, 3)),
    ("R6", "Thẻ in sai tỉ lệ, mất thẻ", (3, 2), (2, 1)),
]


def risk_matrix():
    fig, ax = plt.subplots(figsize=(8.5, 6.4))
    for i in range(1, 6):
        for j in range(1, 6):
            s = i * j
            ax.add_patch(Rectangle((i - 0.5, j - 0.5), 1, 1, fc="#CFE6D7" if s <= 4 else ("#F6E7C1" if s <= 11 else "#F4D6D2"), ec="white", lw=2))
    for k, (code, name, (l0, i0), (l1, i1)) in enumerate(RISKS):
        o = (k - 2.5) * 0.1
        ax.annotate("", (l1 + o, i1 + o), (l0 + o, i0 + o), arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2, ls="--"))
        ax.scatter(l0 + o, i0 + o, s=380, color="white", edgecolor=RED, lw=2, zorder=3)
        ax.text(l0 + o, i0 + o, code, ha="center", va="center", fontsize=9, color=RED, weight="bold", zorder=4)
        ax.scatter(l1 + o, i1 + o, s=380, color=NAVY, zorder=3)
        ax.text(l1 + o, i1 + o, code, ha="center", va="center", fontsize=9, color="white", weight="bold", zorder=4)
    ax.set_xlim(0.5, 5.5); ax.set_ylim(0.5, 5.5); ax.grid(False)
    ax.set_xticks(range(1, 6), ["Rất thấp", "Thấp", "Trung bình", "Cao", "Rất cao"])
    ax.set_yticks(range(1, 6), ["Rất nhẹ", "Nhẹ", "Vừa", "Nặng", "Rất nặng"])
    ax.set_xlabel("Khả năng xảy ra"); ax.set_ylabel("Mức ảnh hưởng")
    ax.scatter([], [], s=120, color="white", edgecolor=RED, lw=2, label="Trước biện pháp")
    ax.scatter([], [], s=120, color=NAVY, label="Sau biện pháp")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    save(fig, "h20_rui_ro")


def ansoff():
    fig, ax = blank((9, 5.6))
    ax.set_xlim(0, 10); ax.set_ylim(0, 6.2)
    q = [(1, 3, "THÂM NHẬP THỊ TRƯỜNG", "Năm 1: hóa học KHTN 7-9\ncho trường THCS miền Bắc", RED),
         (5.5, 3, "PHÁT TRIỂN SẢN PHẨM", "Năm 2-3: thẻ Vật lý (mạch điện),\nSinh học (ADN, di truyền)", NAVY),
         (1, 0, "PHÁT TRIỂN THỊ TRƯỜNG", "Năm 2-3: CLB STEM, trung tâm,\nphụ huynh; toàn quốc", "#4B6584"),
         (5.5, 0, "ĐA DẠNG HÓA", "Sau năm 3: hóa học THPT,\nbản tiếng Anh cho khu vực", GREY)]
    for x, y, t, d, c in q:
        box(ax, x, y + 0.1, 4.4, 2.8, fc="white", ec=c, lw=2.2)
        ax.text(x + 2.2, y + 2.35, t, ha="center", weight="bold", color=c, fontsize=12)
        ax.text(x + 2.2, y + 1.2, d, ha="center", va="center", fontsize=11, linespacing=1.6)
    ax.text(3.2, 6.05, "Sản phẩm hiện có", ha="center", color=GREY, weight="bold"); ax.text(7.7, 6.05, "Sản phẩm mới", ha="center", color=GREY, weight="bold")
    ax.text(0.6, 4.5, "Thị trường\nhiện có", ha="center", va="center", rotation=90, color=GREY, weight="bold")
    ax.text(0.6, 1.5, "Thị trường\nmới", ha="center", va="center", rotation=90, color=GREY, weight="bold")
    save(fig, "h21_ansoff")


if __name__ == "__main__":
    for f in (cover, pipeline, canvas, stakeholders, funnel, readiness, competition, positioning, swot, decision_cycle,
              flywheel, revenue, costs, cloud_cost, pricing, waterfall, unit_breakeven, cashflow, sensitivity, roadmap,
              risk_matrix, ansoff):
        f()
    print("Đã vẽ", len(os.listdir(OUT)), "hình vào", os.path.abspath(OUT))
