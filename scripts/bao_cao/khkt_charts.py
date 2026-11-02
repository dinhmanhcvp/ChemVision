"""Hình cho báo cáo KHKT (docs/bao-cao/khkt/hinh/). Hình kết quả đọc từ do_luong.json. Chạy: python khkt_charts.py"""
import json
import os

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, RegularPolygon

import charts as C
import do_luong as D
from chem_vision import geometry
from chem_vision.core import BY_KEY

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = os.path.join(ROOT, "docs", "bao-cao", "khkt", "hinh")
os.makedirs(OUT, exist_ok=True)
R = json.load(open(os.path.join(ROOT, "docs", "bao-cao", "khkt", "do_luong.json"), encoding="utf-8"))
NAVY, RED, GREEN, AMBER, GREY, LIGHT = C.NAVY, C.RED, C.GREEN, C.AMBER, C.GREY, C.LIGHT
vn = C.vn


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".png"), facecolor="white")
    plt.close(fig)


def node(ax, x, y, w, h, title, body="", ec=NAVY, fc="white"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0,rounding_size=0.08", fc=fc, ec=ec, lw=1.6))
    ax.text(x, y + (0.18 if body else 0), title, ha="center", va="center", weight="bold", color=NAVY, fontsize=10.5)
    if body:
        ax.text(x, y - 0.2, body, ha="center", va="center", fontsize=9, linespacing=1.3)


def arrow(ax, a, b, label=""):
    ax.annotate("", b, a, arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.5))
    if label:
        horiz = abs(a[1] - b[1]) < 0.05
        ax.text((a[0] + b[0]) / 2 + (0 if horiz else 0.08), (a[1] + b[1]) / 2 + (0.14 if horiz else 0), label,
                fontsize=8.5, color=GREY, va="center", ha="center" if horiz else "left")


def architecture():
    fig, ax = plt.subplots(figsize=(11, 6.4)); ax.set_axis_off(); ax.set_xlim(0, 11); ax.set_ylim(-0.15, 6.4)
    node(ax, 1.3, 5.6, 2.2, 0.8, "Ảnh camera", "JPEG ≤ 1280 px")
    node(ax, 4.2, 5.6, 2.6, 0.8, "Đọc mã ArUco", "OpenCV, DICT_4X4_50", ec=GREEN)
    node(ax, 4.2, 4.1, 2.6, 0.8, "Kiểm tra chất lượng ảnh", "sáng, nét, lóa, tương phản")
    node(ax, 4.2, 2.6, 2.6, 0.8, "Gemini đọc kí hiệu", "chỉ trả khung bao + kí hiệu", ec=AMBER)
    node(ax, 7.3, 2.6, 2.6, 0.8, "Liên kết bằng hình học", "mặt nạ nền Lab, khe hở")
    node(ax, 7.3, 5.6, 2.6, 0.8, "Liên kết theo khoảng cách", "tâm ≤ 1,3 × cỡ thẻ", ec=GREEN)
    node(ax, 9.6, 4.1, 2.2, 0.8, "JSON thẻ + cặp chạm", "cùng một định dạng")
    node(ax, 9.6, 2.4, 2.2, 0.9, "Lõi đối sánh", "làm sạch → tách cụm\n→ đẳng cấu đồ thị", ec=RED, fc=LIGHT)
    node(ax, 9.6, 0.75, 2.2, 0.8, "Phản hồi", "khớp / sai liên kết / gợi ý")
    arrow(ax, (2.4, 5.6), (2.9, 5.6))
    arrow(ax, (5.5, 5.6), (6.0, 5.6), "thấy mã")
    arrow(ax, (4.2, 5.2), (4.2, 4.5), "không thấy mã")
    arrow(ax, (4.2, 3.7), (4.2, 3.0), "ảnh đạt")
    arrow(ax, (5.5, 2.6), (6.0, 2.6))
    arrow(ax, (8.6, 5.6), (9.6, 4.5)); arrow(ax, (7.3, 3.0), (8.9, 3.85)); arrow(ax, (2.9, 4.1), (2.25, 4.1))
    arrow(ax, (9.6, 3.7), (9.6, 2.85)); arrow(ax, (9.6, 1.95), (9.6, 1.15))
    ax.text(1.3, 4.1, "ảnh hỏng nặng:\nchặn, yêu cầu chụp lại", fontsize=9, color=RED, ha="center", va="center")
    ax.add_patch(plt.Rectangle((2.75, 1.9), 3.0, 4.2, fill=False, ls="--", ec=GREY))
    ax.text(2.85, 1.98, "NHẬN DIỆN", fontsize=9, color=GREY, weight="bold")
    ax.add_patch(plt.Rectangle((8.35, 0.25), 2.5, 2.7, fill=False, ls="--", ec=RED))
    ax.text(8.42, 0.05, "CHẤM (thuật toán xác định)", fontsize=8.5, color=RED, weight="bold")
    save(fig, "k01_kien_truc")


def card_geometry():
    sc = D.render(BY_KEY["H2O"].graph, D.embed(BY_KEY["H2O"].graph))[0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.25]})
    a1.imshow(sc[:, :, ::-1]); a1.set_axis_off(); a1.set_title("Ba thẻ in ghép phân tử H₂O (vẽ bằng hàm in thẻ)", fontsize=11, color=NAVY)
    a2.set_aspect("equal"); a2.set_axis_off(); a2.set_xlim(-2.6, 2.6); a2.set_ylim(-2.3, 2.3)
    r = 1 / np.sqrt(3)
    cells = [(0, 0), (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1), (2, -1), (1, 1), (-1, 2)]
    for q, rr in cells:
        x, y = 1.5 * r * q, (rr + q / 2)
        a2.add_patch(RegularPolygon((x, y), 6, radius=r, orientation=np.pi / 6, fc=LIGHT if (q, rr) != (0, 0) else "#F6E7C1", ec=NAVY, lw=1.2))
    a2.plot([0, 1.5 * r], [0, 0.5], color=GREEN, lw=2.5); a2.text(0.45, 0.42, "1,00", color=GREEN, fontsize=11, weight="bold")
    a2.plot([0, 3 * r], [0, 0], color=RED, lw=2.5, ls="--"); a2.text(0.95, -0.2, "1,73 (cách một ô)", color=RED, fontsize=11, weight="bold")
    for rad, lab, c in ((1.3, "ngưỡng ArUco 1,3", GREEN), (1.7 * 1.16, "ngưỡng hình học 1,7 × 1,16 ≈ 1,97", RED)):
        a2.add_patch(plt.Circle((0, 0), rad, fill=False, ec=c, ls=":", lw=1.5))
        a2.text(0, -rad - 0.13, lab, ha="center", fontsize=9.5, color=c)
    a2.set_title("Khoảng cách tâm trên lưới lục giác (đơn vị: đối cạnh thẻ)", fontsize=11, color=NAVY)
    save(fig, "k02_hinh_hoc_the")


def detection_example():
    s = BY_KEY["CH3COOH"]
    img = D.distort(D.render(s.graph, D.layout(s.graph)[0])[0], card_px=70, rot=24, tilt=20)
    from chem_vision.markers import cards_from_markers
    data = cards_from_markers(img)
    ann = geometry.annotate(img, data)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    a1.imshow(img[:, :, ::-1]); a1.set_title("Ảnh thử: CH₃COOH xếp tỏa tròn, thẻ 70 px, xoay 24°, nghiêng 20°", fontsize=10.5, color=NAVY)
    a2.imshow(ann[:, :, ::-1]); a2.set_title(f"Kết quả: {len(data['cards'])} thẻ, {len(data['connections'])} liên kết → axit axetic", fontsize=10.5, color=NAVY)
    for a in (a1, a2):
        a.set_axis_off()
    save(fig, "k03_vi_du_nhan_dien")


def draw_graph(ax, g, pos, title):
    for i, j in g.edges:
        ax.plot([pos[i][0], pos[j][0]], [pos[i][1], pos[j][1]], color=GREY, lw=2, zorder=1)
    for i, l in enumerate(g.labels):
        c = {"C": "#2D2D2D", "H": "#E8ECF1", "O": RED}.get(l, NAVY)
        ax.scatter(*pos[i], s=520 if l != "H" else 300, color=c, edgecolor=NAVY, zorder=2)
        ax.text(*pos[i], l, ha="center", va="center", color="white" if l != "H" else NAVY, weight="bold", fontsize=11, zorder=3)
    ax.set_title(title, fontsize=11, color=NAVY); ax.set_axis_off(); ax.set_aspect("equal")


def radial(g):
    """Bố trí tỏa tròn đơn giản chỉ để vẽ đồ thị (không kiểm tra va chạm)."""
    root = max(range(len(g.labels)), key=lambda i: len(g.adj[i]))
    xy, ang, queue = {root: (0.0, 0.0)}, {root: None}, [root]
    while queue:
        u = queue.pop(0)
        kids = sorted(g.adj[u] - set(xy), key=lambda i: -len(g.adj[i]))
        d = len(g.adj[u])
        start = 0.0 if ang[u] is None else ang[u] + np.pi
        for k, v in enumerate(kids, 1 if ang[u] is not None else 0):
            a = start + 2 * np.pi * k / d + (np.pi / 4 if ang[u] is not None and d == 4 else 0)
            xy[v] = (xy[u][0] + np.cos(a), xy[u][1] + np.sin(a)); ang[v] = a; queue.append(v)
    return xy


def isomers():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, key, title in ((axes[0], "C2H5OH", "Etanol C₂H₅OH: C–C–O–H"), (axes[1], "CH3OCH3", "Đimetyl ete CH₃OCH₃: C–O–C")):
        g = BY_KEY[key].graph
        pos = radial(g)
        draw_graph(ax, g, pos, title)
    fig.suptitle("Cùng thành phần 2C, 6H, 1O nhưng hai đồ thị không đẳng cấu: phần mềm phân biệt được hai chất", fontsize=11, y=0.02)
    save(fig, "k04_dong_phan")


def decision():
    fig, ax = plt.subplots(figsize=(11, 4.6)); ax.set_axis_off(); ax.set_xlim(0, 11); ax.set_ylim(0, 4.6)
    node(ax, 1.4, 2.3, 2.4, 0.9, "Một cụm thẻ", "đồ thị G có nhãn")
    node(ax, 4.4, 3.4, 2.8, 0.9, "Có chất cùng thành phần?", "tra chỉ mục theo chữ kí")
    node(ax, 4.4, 1.2, 2.8, 0.9, "Gợi ý gần nhất", "thiếu + thừa ≤ 3, thừa ≤ 1")
    node(ax, 7.6, 4.0, 2.6, 0.75, "G đẳng cấu?", "WL 3 vòng + quay lui")
    node(ax, 10.0, 4.0, 1.7, 0.75, "MATCH", "", ec=GREEN, fc="#CFE6D7")
    node(ax, 10.0, 2.85, 1.7, 0.75, "WRONG_BONDS", "", ec=RED, fc="#F4D6D2")
    node(ax, 7.6, 1.2, 2.6, 0.75, "Có ứng viên?", "")
    node(ax, 10.0, 1.6, 1.7, 0.7, "SUGGEST", "", ec=AMBER, fc="#F6E7C1")
    node(ax, 10.0, 0.6, 1.7, 0.7, "UNKNOWN", "", ec=GREY)
    arrow(ax, (2.6, 2.5), (3.0, 3.2)); arrow(ax, (2.6, 2.1), (3.0, 1.4))
    arrow(ax, (5.8, 3.6), (6.3, 3.95), "có"); arrow(ax, (4.4, 2.95), (4.4, 1.65), "không")
    arrow(ax, (8.9, 4.0), (9.15, 4.0), "có"); arrow(ax, (8.4, 3.62), (9.15, 2.95), "không: nêu liên kết thừa/thiếu")
    arrow(ax, (5.8, 1.2), (6.3, 1.2)); arrow(ax, (8.9, 1.35), (9.15, 1.6), "có"); arrow(ax, (8.9, 1.0), (9.15, 0.65), "không")
    save(fig, "k05_quyet_dinh")


def robustness():
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2))
    for ax, key, xk, xl in ((axes[0, 0], "kích thước thẻ", "cạnh thẻ px", "Đối cạnh thẻ trên ảnh (điểm ảnh)"),
                            (axes[0, 1], "nghiêng", "nghiêng độ", "Méo phối cảnh: mép xa còn bao nhiêu % chiều rộng"),
                            (axes[1, 0], "mờ", "mờ σ px", "Độ mờ Gauss σ (điểm ảnh)"),
                            (axes[1, 1], "tối", "độ sáng ×", "Hệ số độ sáng (1 = bình thường)")):
        rows = R[key]
        x = [r[xk] for r in rows]
        if key == "nghiêng":                      # đổi tham số nghiêng sang tỉ lệ co của mép xa, dễ hình dung hơn
            x = [round(100 * (1 - np.tan(np.radians(v)) * 0.5)) for v in x]
            ax.invert_xaxis()
        ax.plot(x, [r["đọc đủ thẻ %"] for r in rows], "o-", color=NAVY, lw=2, label="Đọc đủ mọi thẻ")
        ax.plot(x, [r["đúng chất %"] for r in rows], "s--", color=RED, lw=2, label="Kết luận đúng chất")
        ax.set_ylim(-3, 105); ax.set_xlabel(xl); ax.set_ylabel("%")
        if key == "tối":
            ax.invert_xaxis()
        for xi, yi in zip(x, [r["đúng chất %"] for r in rows]):
            ax.annotate(vn(yi, 0), (xi, yi), xytext=(0, -14), textcoords="offset points", ha="center", fontsize=8.5, color=RED)
    axes[0, 0].legend(frameon=False, loc="lower right")
    n = R["kích thước thẻ"][0]["lượt"]
    fig.suptitle(f"Mỗi điểm: {n} ảnh tổng hợp ({R['cảnh tổng hợp']['chất dựng được']} chất × 2 góc xoay ngẫu nhiên), nén JPEG 85",
                 fontsize=10.5, y=0.005)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    save(fig, "k06_do_ben_aruco")


def geometry_fig():
    G = R["hình học (đường Gemini)"]
    keys = list(G)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1, 1.2]})
    rows = G[keys[0]]["gỗ sáng"]["khe hở"]
    x = [r["khe hở % cạnh thẻ"] for r in rows]
    a1.step(x, [1 if r["nối"] else 0 for r in rows], where="mid", color=NAVY, lw=2.5)
    a1.axvline(geometry.GAP_FRAC * 100 / 1.16, color=RED, ls=":")
    a1.set_yticks([0, 1], ["không nối", "nối"]); a1.set_xlabel("Khe hở giữa hai thẻ (% đối cạnh thẻ)")
    a1.set_title("Hai thẻ O–H trên nền gỗ sáng", fontsize=11, color=NAVY)
    bgs = list(G[keys[0]])
    w = 0.38
    for k, (key, c) in enumerate(zip(keys, [GREY, GREEN])):
        vals = [G[key][b]["đúng chất"] for b in bgs]
        xs = np.arange(len(bgs)) + (k - 0.5) * w
        a2.bar(xs, vals, w, color=c, label=("hiện tại " if k == 0 else "đề xuất ") + key.replace("MAX_RATIO=", "MAX_RATIO = "))
        for xi, v in zip(xs, vals):
            a2.text(xi, v + 0.8, str(v), ha="center", fontsize=10)
    tot = G[keys[0]][bgs[0]]["phân tử"]
    a2.axhline(tot, color=GREY, ls=":"); a2.text(-0.45, tot + 0.8, f"{tot} phân tử thử", ha="left", fontsize=9, color=GREY)
    a2.set_xticks(range(len(bgs)), [f"Nền {b}" for b in bgs]); a2.set_ylabel("Số phân tử kết luận đúng")
    a2.set_ylim(0, tot * 1.32); a2.legend(frameon=False, loc="upper right", fontsize=9.5); a2.grid(axis="x", visible=False)
    a2.set_title("Cả phân tử, thẻ thường, khung bao đúng", fontsize=11, color=NAVY)
    save(fig, "k07_hinh_hoc")


def quality_fig():
    rows = [r for r in R["chất lượng ảnh"] if "mờ σ" in r]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = [r["mờ σ"] for r in rows]; y = [max(r["độ nét"], 0.5) for r in rows]
    cols = {"đạt": GREEN, "nhắc": AMBER, "chặn": RED}
    ax.bar([str(v) for v in x], y, color=[cols[r["kết luận"]] for r in rows])
    ax.set_yscale("log"); ax.axhline(150, color=AMBER, ls="--"); ax.axhline(20, color=RED, ls="--")
    ax.text(5.4, 160, "nhắc: < 150", color=AMBER, ha="right"); ax.text(5.4, 21, "chặn: < 20", color=RED, ha="right")
    for i, (v, r) in enumerate(zip(y, rows)):
        ax.text(i, v * 1.15, f"{vn(r['độ nét'], 0)}\n{r['kết luận']}", ha="center", fontsize=9)
    ax.set_xlabel("Độ mờ Gauss σ thêm vào ảnh (điểm ảnh)"); ax.set_ylabel("Phương sai Laplacian (log)")
    ax.set_ylim(0.5, max(y) * 8)
    save(fig, "k08_chat_luong")


if __name__ == "__main__":
    for f in (architecture, card_geometry, detection_example, isomers, decision, robustness, geometry_fig, quality_fig):
        f()
    print("Đã vẽ", len(os.listdir(OUT)), "hình vào", os.path.abspath(OUT))
