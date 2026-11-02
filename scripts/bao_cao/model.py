"""Mô hình tài chính của báo cáo khởi nghiệp CHEM VISION.

Mọi con số trong bảng, hình và lời văn của báo cáo đều lấy từ đây, để sửa một giả định là cả báo cáo đổi theo.
Đơn vị tiền: triệu đồng, trừ khi tên biến ghi khác.
"""

YEARS = ("Năm 1", "Năm 2", "Năm 3")

# ---- Giá bán (triệu đồng) ----
PRICE = {
    "school": 6.0,        # gói Trường / năm: lớp học trực tuyến, báo cáo giáo viên, tập huấn trực tuyến
    "class_kit": 1.2,     # bộ thẻ lớp học ép nhựa có mã ArUco (8 nhóm)
    "family_kit": 0.249,  # bộ thẻ gia đình
    "teacher": 0.39,      # gói Giáo viên Pro / năm
    "training": 3.0,      # một đợt tập huấn trực tiếp
}
# Giá vốn mỗi đơn vị (triệu đồng)
UNIT_COST = {"class_kit": 0.42, "family_kit": 0.11, "training": 1.2}
PAYMENT_FEE = 0.025       # phí cổng thanh toán, tính trên doanh thu bán lẻ trực tuyến (bộ gia đình, gói giáo viên)

# ---- Số lượng bán theo năm ----
VOLUME = {
    "school":     (40, 150, 450),
    "class_kit":  (60, 220, 600),
    "family_kit": (800, 2500, 6000),
    "teacher":    (150, 600, 1800),
    "training":   (10, 40, 100),
}
PARTNER = (0.0, 150.0, 500.0)   # chia sẻ doanh thu với đối tác thiết bị / nhà xuất bản
CLOUD = (24.0, 60.0, 150.0)     # Vercel, Upstash Redis, Gemini, tên miền

REV_LABELS = {
    "school": "Gói Trường",
    "class_kit": "Bộ thẻ lớp học",
    "family_kit": "Bộ thẻ gia đình",
    "teacher": "Gói Giáo viên Pro",
    "training": "Tập huấn",
    "partner": "Đối tác thiết bị, NXB",
}

# ---- Chi phí hoạt động tiền mặt (triệu đồng/năm) ----
OPEX = {
    "Nhân sự kỹ thuật (cộng tác viên)": (180, 600, 1300),
    "Học liệu, giáo án, bộ đề": (40, 90, 180),
    "Tiếp thị, thao giảng, hội thảo": (50, 150, 350),
    "Chăm sóc khách hàng, vận hành": (30, 120, 290),
    "Hành chính, pháp lý, sở hữu trí tuệ": (20, 40, 80),
}
CAPEX = {
    "Máy tính, camera, điện thoại thử nghiệm": 45,
    "Máy in, máy ép plastic, dao cắt thẻ": 35,
    "Thiết kế và khuôn mẫu thẻ nhựa PVC": 20,
    "Bộ thẻ trình diễn cho trường thử nghiệm": 20,
    "Nhãn hiệu, bản quyền phần mềm": 15,
    "Dự phòng": 15,
}
DEPRECIATION_YEARS = 3
TAX = (0.0, 0.10, 0.10)   # giả định ưu đãi cho doanh nghiệp nhỏ đổi mới sáng tạo; cần đối chiếu quy định khi thực hiện
WORKING_CAPITAL = 80      # khoảng 3 tháng chi phí hoạt động năm 1

# ---- Giá vốn đám mây mỗi tiết học ----
USD = 25_000
GEMINI = {"flash": (0.30, 2.50), "lite": (0.10, 0.40)}   # USD / 1 triệu token (vào, ra), bảng giá tham khảo
TOKENS_IN, TOKENS_OUT = 800, 250                          # một ảnh thẻ + lời nhắc; đầu ra JSON khung bao
GROUPS, CHECKS_PER_GROUP = 8, 12                          # một tiết: 8 nhóm, mỗi nhóm 12 lượt KIỂM TRA
GEMINI_SHARE = 0.20                                       # tỷ lệ lượt dùng thẻ thường khi trường đã có bộ thẻ in mã
LESSONS_PER_SCHOOL = 300                                  # số tiết dùng CHEM VISION mỗi trường mỗi năm

# ---- Thị trường (năm học 2024-2025, ước tính, cần đối chiếu niên giám thống kê Bộ GD&ĐT) ----
MARKET = {
    "schools": 10_900, "teachers": 60_000, "students_grade7": 1_650_000,
    "sam_schools": 2_700, "sam_teachers": 15_000, "sam_students": 400_000,
}


def per_call_vnd(model="flash"):
    i, o = GEMINI[model]
    return (TOKENS_IN * i + TOKENS_OUT * o) / 1e6 * USD


def per_lesson_vnd(share, model="flash"):
    return GROUPS * CHECKS_PER_GROUP * share * per_call_vnd(model)


def revenue_lines():
    lines = {k: tuple(VOLUME[k][y] * PRICE[k] for y in range(3)) for k in VOLUME}
    lines["partner"] = PARTNER
    return lines


def pnl():
    rev_l = revenue_lines()
    rows = []
    for y in range(3):
        rev = sum(v[y] for v in rev_l.values())
        cogs = (VOLUME["class_kit"][y] * UNIT_COST["class_kit"] + VOLUME["family_kit"][y] * UNIT_COST["family_kit"]
                + VOLUME["training"][y] * UNIT_COST["training"] + CLOUD[y]
                + PAYMENT_FEE * (rev_l["family_kit"][y] + rev_l["teacher"][y]))
        gp = rev - cogs
        opex = sum(v[y] for v in OPEX.values())
        dep = sum(CAPEX.values()) / DEPRECIATION_YEARS
        ebt = gp - opex - dep
        tax = max(ebt, 0) * TAX[y]
        rows.append(dict(rev=rev, cogs=cogs, gp=gp, gm=gp / rev, opex=opex, dep=dep, ebt=ebt, tax=tax,
                         ni=ebt - tax, nm=(ebt - tax) / rev))
    return rows


def market():
    m = MARKET
    tam = {"Gói Trường": m["schools"] * PRICE["school"], "Bộ thẻ lớp học": m["schools"] * PRICE["class_kit"],
           "Giáo viên KHTN": m["teachers"] * PRICE["teacher"],
           "Bộ thẻ gia đình": m["students_grade7"] * PRICE["family_kit"]}
    sam = m["sam_schools"] * (PRICE["school"] + PRICE["class_kit"]) + m["sam_teachers"] * PRICE["teacher"] \
        + m["sam_students"] * PRICE["family_kit"]
    som = sum(VOLUME[k][2] * PRICE[k] for k in ("school", "class_kit", "teacher", "family_kit"))
    return {k: v / 1000 for k, v in tam.items()}, sum(tam.values()) / 1000, sam / 1000, som / 1000   # tỷ đồng


def unit_economics():
    P = pnl()
    # Kênh trường: CAC = tiếp thị năm 1 + 30% nhân sự kỹ thuật (người đi thao giảng) chia số trường mới
    cac_school = (OPEX["Tiếp thị, thao giảng, hội thảo"][0] + 0.3 * OPEX["Nhân sự kỹ thuật (cộng tác viên)"][0]) \
        / VOLUME["school"][0]
    renew = 0.80
    life = 1 / (1 - renew)
    cloud_school = per_lesson_vnd(GEMINI_SHARE) * LESSONS_PER_SCHOOL / 1e6
    margin_school = PRICE["school"] - cloud_school
    ltv_school = margin_school * life
    # Kênh gia đình: một lần mua, CAC = hoa hồng giới thiệu 10% + quảng cáo nhóm phụ huynh
    cac_family = 0.040
    contrib_family = PRICE["family_kit"] - UNIT_COST["family_kit"] - PAYMENT_FEE * PRICE["family_kit"]
    # Hòa vốn hoạt động năm 1
    monthly_fixed = P[0]["opex"] / 12
    be_rev = monthly_fixed / P[0]["gm"]
    return dict(cac_school=cac_school, renew=renew, life=life, cloud_school=cloud_school, ltv_school=ltv_school,
                ltv_cac=ltv_school / cac_school, payback_m=cac_school / (margin_school / 12),
                cac_family=cac_family, contrib_family=contrib_family, family_ratio=contrib_family / cac_family,
                monthly_fixed=monthly_fixed, be_rev=be_rev)


def monthly_cash():
    """Dòng tiền lũy kế 36 tháng: năm 1 doanh thu tăng đều theo tháng, năm 2 và 3 chia đều."""
    P = pnl()
    capex = sum(CAPEX.values())
    cum, out = -capex, []
    a = P[0]["rev"] / 78    # doanh thu tháng m của năm 1 = a·m, tổng 12 tháng = 78a
    for m in range(1, 37):
        y = (m - 1) // 12
        rev = a * m if y == 0 else P[y]["rev"] / 12
        cash = rev * P[y]["gm"] - P[y]["opex"] / 12 - P[y]["tax"] / 12
        cum += cash
        out.append(cum)
    return out


def scenarios():
    """Kịch bản: số lượng bán (mọi dòng) nhân hệ số; chi phí hoạt động giữ nguyên."""
    base = pnl()[2]
    res = {}
    for name, f in (("Xấu", 0.6), ("Cơ sở", 1.0), ("Tốt", 1.3)):
        rev = base["rev"] * f
        cogs = (base["cogs"] - CLOUD[2]) * f + CLOUD[2]
        ebt = rev - cogs - base["opex"] - base["dep"]
        res[name] = dict(rev=rev, ebt=ebt, ni=ebt - max(ebt, 0) * TAX[2])
    return res


def tornado():
    """Lợi nhuận trước thuế năm 3 khi từng giả định lệch ±20%."""
    base = pnl()[2]["ebt"]
    v = VOLUME
    out = []
    drivers = [
        ("Số trường mua gói", lambda d: d * v["school"][2] * PRICE["school"] * 0.98),
        ("Giá gói Trường", lambda d: d * v["school"][2] * PRICE["school"]),
        ("Số bộ thẻ gia đình", lambda d: d * v["family_kit"][2] * (PRICE["family_kit"] * (1 - PAYMENT_FEE)
                                                                      - UNIT_COST["family_kit"])),
        ("Chi phí nhân sự kỹ thuật", lambda d: -d * OPEX["Nhân sự kỹ thuật (cộng tác viên)"][2]),
        ("Số giáo viên Pro", lambda d: d * v["teacher"][2] * PRICE["teacher"] * (1 - PAYMENT_FEE)),
        ("Giá vốn bộ thẻ", lambda d: -d * (v["class_kit"][2] * UNIT_COST["class_kit"]
                                           + v["family_kit"][2] * UNIT_COST["family_kit"])),
        ("Chi phí đám mây", lambda d: -d * CLOUD[2]),
    ]
    for name, f in drivers:
        out.append((name, base + f(-0.2), base + f(0.2)))
    return base, sorted(out, key=lambda t: abs(t[2] - t[1]))


if __name__ == "__main__":
    # self-check: các tổng phải khớp nhau
    P = pnl()
    lines = revenue_lines()
    for y in range(3):
        assert abs(sum(v[y] for v in lines.values()) - P[y]["rev"]) < 1e-9
        assert abs(P[y]["rev"] - P[y]["cogs"] - P[y]["opex"] - P[y]["dep"] - P[y]["tax"] - P[y]["ni"]) < 1e-9
    assert abs(monthly_cash()[11] - (sum(P[0][k] for k in ("gp",)) - P[0]["opex"] - sum(CAPEX.values()))) < 1e-6
    for r in P:
        print({k: round(v, 3) for k, v in r.items()})
    print("market", market())
    print("unit", {k: round(v, 3) for k, v in unit_economics().items()})
    print("per call", round(per_call_vnd(), 2), "per lesson 20%", round(per_lesson_vnd(0.2)), "100%",
          round(per_lesson_vnd(1)), "lite100%", round(per_lesson_vnd(1, "lite")))
    print("scen", scenarios())
    cash = monthly_cash()
    print("cash payback month", next(i + 1 for i, c in enumerate(cash) if c >= 0), "cum36", round(cash[-1], 1))
