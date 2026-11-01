"""Phân tích thử nghiệm đối chứng CHEM VISION: so sánh nhóm dùng CHEM VISION với nhóm dùng mô hình bi-que.

Đầu vào: tệp CSV có các cột  lop, nhom, diem_truoc, diem_sau  (tùy chọn: diem_sau_muon).
  - lop   : mã lớp (đơn vị chia nhóm, dùng để tính sai số chuẩn theo cụm)
  - nhom  : CV (CHEM VISION) hoặc BQ (mô hình bi-que)
Chạy:  python scripts/analyze_experiment.py du_lieu.csv

Chỉ dùng numpy. Gồm: kiểm định t Welch, cỡ ảnh hưởng Hedges g, hồi quy ANCOVA (điểm sau theo điểm trước và nhóm) với sai số
chuẩn theo cụm lớp, và tính cỡ mẫu cần có. Các hàm xác suất được kiểm tra với giá trị bảng chuẩn trong kiểm thử.
"""
from __future__ import annotations

import csv
import math
import sys

import numpy as np


# --------------------------------------------------------------------------- phân phối t
def _betacf(a, b, x, max_iter=300, eps=3e-14):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1.0 + aa / c
        c = c if abs(c) > 1e-300 else 1e-300
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def betainc(a, b, x):
    """Hàm beta không đầy đủ chuẩn hóa I_x(a, b)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1 - x) / b


def t_two_sided_p(t: float, df: float) -> float:
    """Xác suất hai phía P(|T| >= |t|) của phân phối t với df bậc tự do."""
    if df <= 0:
        return float("nan")
    return betainc(df / 2.0, 0.5, df / (df + t * t))


def t_critical(df: float, alpha: float = 0.05) -> float:
    """Giá trị tới hạn hai phía (tìm bằng chia đôi)."""
    lo, hi = 0.0, 100.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if t_two_sided_p(mid, df) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- thống kê
def welch(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / na + vb / nb)
    t = (a.mean() - b.mean()) / se if se > 0 else float("inf")
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)) if se > 0 else na + nb - 2
    return {"diff": a.mean() - b.mean(), "t": t, "df": df, "p": t_two_sided_p(t, df) if se > 0 else 0.0,
            "mean_a": a.mean(), "mean_b": b.mean(), "n_a": na, "n_b": nb}


def hedges_g(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    sp = math.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    d = (a.mean() - b.mean()) / sp if sp > 0 else float("inf")
    j = 1 - 3 / (4 * (na + nb) - 9)
    g = d * j
    se = math.sqrt((na + nb) / (na * nb) + g * g / (2 * (na + nb)))
    return {"g": g, "ci_low": g - 1.96 * se, "ci_high": g + 1.96 * se}


def ancova(post, pre, group, clusters=None) -> dict:
    """Hồi quy post ~ 1 + pre + group (group = 1 cho CHEM VISION). Có clusters thì dùng sai số chuẩn cụm (CR1) và bậc tự do G-1."""
    y, x1, x2 = (np.asarray(v, float) for v in (post, pre, group))
    X = np.column_stack([np.ones_like(y), x1, x2])
    n, k = X.shape
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    if clusters is None:
        s2 = resid @ resid / (n - k)
        cov, df = s2 * xtx_inv, n - k
    else:
        ids = np.asarray(clusters)
        uniq = np.unique(ids)
        meat = np.zeros((k, k))
        for g in uniq:
            m = ids == g
            u = X[m].T @ resid[m]
            meat += np.outer(u, u)
        G = len(uniq)
        cov = xtx_inv @ meat @ xtx_inv * (G / (G - 1)) * ((n - 1) / (n - k))
        df = G - 1
    se = np.sqrt(np.diag(cov))
    t = beta[2] / se[2]
    return {"effect": float(beta[2]), "se": float(se[2]), "t": float(t), "df": float(df), "p": t_two_sided_p(float(t), df),
            "pre_slope": float(beta[1]), "clusters": None if clusters is None else int(len(np.unique(clusters)))}


def sample_size_per_group(d: float, alpha: float = 0.05, power: float = 0.8, cluster_size: int = 1, icc: float = 0.0) -> int:
    """Cỡ mẫu mỗi nhóm để phát hiện cỡ ảnh hưởng d (xấp xỉ chuẩn), nhân hệ số thiết kế 1 + (m - 1) * ICC khi chia theo lớp."""
    z = _norm_ppf(1 - alpha / 2) + _norm_ppf(power)
    n = 2 * (z / d) ** 2
    n *= 1 + (cluster_size - 1) * icc
    return math.ceil(n)


def _norm_ppf(p: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if 0.5 * (1 + math.erf(mid / math.sqrt(2))) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------------- đọc dữ liệu và báo cáo
def read_rows(path: str):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    need = {"lop", "nhom", "diem_truoc", "diem_sau"}
    if not rows or not need <= set(rows[0]):
        raise SystemExit("Tệp cần có các cột: lop, nhom, diem_truoc, diem_sau")
    out = []
    for r in rows:
        if r["nhom"] not in ("CV", "BQ"):
            raise SystemExit(f"Cột nhom chỉ nhận CV hoặc BQ, gặp: {r['nhom']!r}")
        out.append({"lop": r["lop"], "cv": 1 if r["nhom"] == "CV" else 0, "pre": float(r["diem_truoc"]), "post": float(r["diem_sau"]),
                    "late": float(r["diem_sau_muon"]) if r.get("diem_sau_muon") not in (None, "") else None})
    return out


def report(rows) -> str:
    cv = [r for r in rows if r["cv"]]
    bq = [r for r in rows if not r["cv"]]
    if len(cv) < 3 or len(bq) < 3:
        return "Mỗi nhóm cần ít nhất 3 học sinh."
    lines = [f"Số học sinh: CHEM VISION {len(cv)}, mô hình bi-que {len(bq)}; số lớp: {len({r['lop'] for r in rows})}."]
    for label, key in (("Điểm trước", "pre"), ("Điểm sau", "post")):
        a, b = [r[key] for r in cv], [r[key] for r in bq]
        lines.append(f"{label}: CV {np.mean(a):.2f} (độ lệch chuẩn {np.std(a, ddof=1):.2f}), BQ {np.mean(b):.2f} ({np.std(b, ddof=1):.2f}).")
    ga, gb = [r["post"] - r["pre"] for r in cv], [r["post"] - r["pre"] for r in bq]
    w, g = welch(ga, gb), hedges_g(ga, gb)
    lines.append(f"Mức tăng điểm: CV {w['mean_a']:.2f}, BQ {w['mean_b']:.2f}, chênh {w['diff']:+.2f}; "
                 f"Welch t = {w['t']:.2f}, df = {w['df']:.1f}, p = {w['p']:.3f}; Hedges g = {g['g']:.2f} (KTC 95%: {g['ci_low']:.2f} đến {g['ci_high']:.2f}).")
    an = ancova([r["post"] for r in rows], [r["pre"] for r in rows], [r["cv"] for r in rows])
    lines.append(f"ANCOVA (điều chỉnh theo điểm trước): chênh {an['effect']:+.2f} điểm, SE {an['se']:.2f}, p = {an['p']:.3f}.")
    classes = {r["lop"] for r in rows}
    if len(classes) >= 4:
        ac = ancova([r["post"] for r in rows], [r["pre"] for r in rows], [r["cv"] for r in rows], [r["lop"] for r in rows])
        lines.append(f"ANCOVA có sai số chuẩn theo cụm lớp ({ac['clusters']} lớp): chênh {ac['effect']:+.2f}, SE {ac['se']:.2f}, "
                     f"p = {ac['p']:.3f} (bậc tự do {ac['df']:.0f}). Nên dùng kết quả này khi chia nhóm theo lớp.")
    else:
        lines.append("Có dưới 4 lớp: sai số chuẩn theo cụm không đáng tin, hãy thêm lớp trước khi kết luận.")
    if all(r["late"] is not None for r in rows):
        a, b = [r["late"] for r in cv], [r["late"] for r in bq]
        w2 = welch(a, b)
        lines.append(f"Điểm sau muộn: CV {w2['mean_a']:.2f}, BQ {w2['mean_b']:.2f}, p = {w2['p']:.3f}.")
    lines.append("Lưu ý: p lớn hoặc khoảng tin cậy chứa 0 nghĩa là chưa đủ bằng chứng về sự khác biệt, không phải bằng chứng hai cách như nhau.")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(1)
    print(report(read_rows(sys.argv[1])))
