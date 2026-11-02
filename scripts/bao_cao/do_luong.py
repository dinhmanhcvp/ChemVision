"""Đo các chỉ số kỹ thuật cho báo cáo KHKT. Mọi số liệu trong báo cáo KHKT lấy từ tệp kết quả của script này.

Chạy: python do_luong.py   ->  docs/bao-cao/khkt/do_luong.json

Ảnh thử là ẢNH TỔNG HỢP: thẻ được vẽ bằng đúng hàm in thẻ (scripts/make_cards.py), xếp thành phân tử trên lưới lục giác,
rồi làm biến dạng (thu nhỏ, xoay, nghiêng phối cảnh, mờ, tối, nhiễu, nén JPEG). Đây chưa phải ảnh chụp thẻ in thật.
"""
import json
import os
import random
import statistics
import sys
import time
from collections import Counter

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import make_cards as mc  # noqa: E402
from chem_vision import core, geometry, quality, reactions  # noqa: E402
from chem_vision.core import DATABASE, Graph, analyze, is_isomorphic, match_cluster  # noqa: E402
from chem_vision.markers import cards_from_markers  # noqa: E402

OUT = os.path.join(ROOT, "docs", "bao-cao", "khkt", "do_luong.json")
RNG = random.Random(2026)
FLAT = mc.FLAT_MM * mc.MM                       # đối cạnh thẻ ở 300 dpi (điểm ảnh)
R = FLAT / np.sqrt(3)
NEIGH = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]   # toạ độ trục của lưới lục giác đỉnh nhọn hai bên
TABLE = (140, 175, 200)                          # màu mặt bàn gỗ sáng (BGR)
BACKGROUNDS = {"gỗ sáng": TABLE, "xám đậm": (70, 70, 75), "trắng": (245, 245, 245)}


# ------------------------------------------------------------------ dựng cảnh phân tử
def embed(g: Graph, limit=20000):
    """Đặt mỗi nguyên tử vào một ô lục giác: nguyên tử có liên kết ở hai ô kề nhau, không liên kết thì không kề. None nếu không đặt được."""
    n = len(g.labels)
    order, seen = [], set()
    for s in sorted(range(n), key=lambda i: -len(g.adj[i])):
        stack = [s]
        while stack:
            u = stack.pop(0)
            if u in seen:
                continue
            seen.add(u); order.append(u)
            stack.extend(sorted(g.adj[u] - seen, key=lambda i: -len(g.adj[i])))
    pos, cells, steps = {}, {}, [0]

    def ok(u, cell):
        if cell in cells:
            return False
        for d in NEIGH:
            v = cells.get((cell[0] + d[0], cell[1] + d[1]))
            if v is not None and v not in g.adj[u]:
                return False
        return all(w not in pos or (pos[w][0] - cell[0], pos[w][1] - cell[1]) in NEIGH for w in g.adj[u])

    def place(k):
        steps[0] += 1
        if steps[0] > limit:
            return False
        if k == n:
            return True
        u = order[k]
        placed = [w for w in g.adj[u] if w in pos]
        cand = [(0, 0)] if not pos else (
            [(pos[placed[0]][0] + d[0], pos[placed[0]][1] + d[1]) for d in NEIGH] if placed else [])
        for cell in cand:
            if ok(u, cell):
                pos[u] = cell; cells[cell] = u
                if place(k + 1):
                    return True
                del pos[u]; del cells[cell]
        return False

    if not place(0):
        return None
    return {u: (1.5 * q / np.sqrt(3), r + q / 2) for u, (q, r) in pos.items()}   # toạ độ phẳng, đơn vị: đối cạnh thẻ


def embed_free(g: Graph, tries=3000, seed=7):
    """Đặt tỏa tròn như học sinh xếp tay: các thẻ nối với một thẻ chia đều góc quanh nó, cách tâm đúng 1 cỡ thẻ, mỗi nhóm
    được xoay lệch ngẫu nhiên. Nhận khi mọi cặp có liên kết cách nhau ≤ 1,15 và mọi cặp không liên kết ≥ 1,4 (ngưỡng đọc 1,3)."""
    rng = np.random.default_rng(seed)
    n = len(g.labels)
    root = max(range(n), key=lambda i: len(g.adj[i]))
    for t in range(tries):
        xy, ang, queue = {root: (0.0, 0.0)}, {root: None}, [root]
        while queue:
            u = queue.pop(0)
            kids = sorted(g.adj[u] - set(xy), key=lambda i: -len(g.adj[i]))
            d = len(g.adj[u])
            jitter = 0.0 if t == 0 else rng.uniform(-np.pi / d, np.pi / d)
            start = (0.0 if ang[u] is None else ang[u] + np.pi) + jitter * (ang[u] is not None)
            for k, v in enumerate(kids, 1 if ang[u] is not None else 0):
                a = start + 2 * np.pi * k / d
                xy[v] = (xy[u][0] + np.cos(a), xy[u][1] + np.sin(a)); ang[v] = a; queue.append(v)
        if len(xy) != n:
            return None
        good = all((j in g.adj[i] and np.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]) <= 1.15) or
                   (j not in g.adj[i] and np.hypot(xy[i][0] - xy[j][0], xy[i][1] - xy[j][1]) >= 1.4)
                   for i in range(n) for j in range(i + 1, n))
        if good:
            return xy
    return None


def layout(g: Graph):
    """(toạ độ, cách đặt): ưu tiên lưới lục giác (thẻ chạm cạnh), không được thì đặt tỏa tròn."""
    xy = embed(g)
    if xy:
        return xy, "lưới"
    xy = embed_free(g)
    return (xy, "tỏa tròn") if xy else (None, None)


def draw_plain(img, symbol, cx, cy):
    """Thẻ thường (không có mã vuông) như học sinh tự làm: lục giác màu đậm, viền, kí hiệu lớn. Dùng cho đường Gemini."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    hexa = mc.hexagon(cx, cy, FLAT)
    d.polygon(hexa, fill=mc.COLORS.get(symbol, (220, 220, 220)))
    d.line(hexa + [hexa[0]], fill=(70, 70, 70), width=3)
    d.text((cx, cy), symbol, font=mc.font(48, bold=True), fill=(20, 20, 20), anchor="mm")


def render(g: Graph, pos, gap_frac=0.0, table=TABLE, plain=False):
    """Ảnh BGR 300 dpi của phân tử trên mặt bàn; gap_frac: giãn lưới để tạo khe hở giữa các thẻ (theo kích thước thẻ)."""
    k = (1 + gap_frac) * FLAT
    xy = {u: (x * k, y * k) for u, (x, y) in pos.items()}
    xs, ys = [p[0] for p in xy.values()], [p[1] for p in xy.values()]
    pad = FLAT * 1.2
    w, h = int(max(xs) - min(xs) + 2 * pad), int(max(ys) - min(ys) + 2 * pad)
    img = Image.new("RGB", (w, h), tuple(table[::-1]))
    for u, (x, y) in xy.items():
        (draw_plain if plain else mc.draw_card)(img, g.labels[u], x - min(xs) + pad, y - min(ys) + pad)
    boxes = {u: (x - min(xs) + pad, y - min(ys) + pad) for u, (x, y) in xy.items()}
    return np.array(img)[:, :, ::-1].copy(), boxes


def distort(img, card_px=80, rot=0.0, tilt=0.0, blur=0.0, gain=1.0, noise=0.0, jpeg=85, rng=RNG):
    """Thu nhỏ để thẻ còn `card_px` điểm ảnh, xoay, nghiêng phối cảnh `tilt` độ, mờ Gauss, đổi độ sáng, nhiễu, nén JPEG."""
    s = card_px / FLAT
    img = cv2.resize(img, (max(int(img.shape[1] * s), 8), max(int(img.shape[0] * s), 8)), interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    padd = int(max(h, w) * 0.4)
    img = cv2.copyMakeBorder(img, padd, padd, padd, padd, cv2.BORDER_CONSTANT, value=TABLE)
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0)
    img = cv2.warpAffine(img, m, (w, h), borderValue=TABLE)
    if tilt:
        t = np.tan(np.radians(tilt)) * 0.5        # mép xa co lại như khi chụp chéo
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[w * t / 2, 0], [w - w * t / 2, 0], [w, h], [0, h]])
        img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=TABLE)
    if blur:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    img = img.astype(np.float32) * gain
    if noise:
        img = img + np.random.default_rng(rng.randint(0, 10**6)).normal(0, noise, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, jpeg])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def pipeline(img, key):
    """(đọc đủ thẻ, đúng chất) cho một ảnh."""
    data = cards_from_markers(img)
    if not data:
        return False, False
    a = analyze(json.dumps(data))
    cards_ok = Counter(c["symbol"] for c in data["cards"]) == core.BY_KEY[key].graph.composition()
    right = a.status == "OK" and len(a.clusters) == 1 and a.clusters[0][1].kind == "MATCH" and a.clusters[0][1].substance.key == key
    return cards_ok, right


# ------------------------------------------------------------------ các thí nghiệm
def exp_graph():
    """Đối sánh đồ thị: hoán vị nhãn, đột biến một liên kết, phân biệt đồng phân, thời gian."""
    times, perm_ok, perm_n = [], 0, 0
    for s in DATABASE:
        for _ in range(20):
            n = len(s.graph.labels)
            p = list(range(n)); RNG.shuffle(p)
            g = Graph.from_edges([s.graph.labels[p.index(i)] for i in range(n)], [(p[a], p[b]) for a, b in s.graph.edges])
            t = time.perf_counter(); r = match_cluster(g); times.append((time.perf_counter() - t) * 1000)
            perm_n += 1; perm_ok += r.kind == "MATCH" and r.substance.key == s.key
    # đột biến: dời một đầu liên kết sang nguyên tử khác (cùng thành phần, sai cấu trúc)
    mut_n = false_match = wrong_bonds_detected = 0
    for s in DATABASE:
        edges, n = s.graph.edges, len(s.graph.labels)
        for (a, b) in edges:
            for c in range(n):
                if c in (a, b) or c in s.graph.adj[a]:
                    continue
                new = [e for e in edges if e != (a, b)] + [(a, c)]
                g = Graph.from_edges(s.graph.labels, new)
                if any(is_isomorphic(g, t.graph) for t in DATABASE if t.graph.signature() == g.signature()):
                    continue        # đột biến tình cờ thành một chất có thật (ví dụ đồng phân) thì không tính
                mut_n += 1
                r = match_cluster(g)
                false_match += r.kind == "MATCH"
                wrong_bonds_detected += r.kind == "WRONG_BONDS"
    iso = {}
    for a, b in (("C2H5OH", "CH3OCH3"), ("C4H10", "C4H10-iso")):
        ga, gb = core.BY_KEY[a].graph, core.BY_KEY[b].graph
        iso[f"{a}/{b}"] = {"cùng thành phần": ga.signature() == gb.signature(), "phân biệt đúng":
                           match_cluster(ga).substance.key == a and match_cluster(gb).substance.key == b}
    times.sort()
    return {"chất": len(DATABASE), "lượt hoán vị": perm_n, "khớp đúng sau hoán vị": perm_ok,
            "đột biến một liên kết": mut_n, "khớp nhầm": false_match, "báo sai liên kết": wrong_bonds_detected,
            "đồng phân": iso, "ms trung vị": round(statistics.median(times), 3),
            "ms p95": round(times[int(0.95 * len(times))], 3), "ms lớn nhất": round(times[-1], 3),
            "cỡ phân tử lớn nhất": max(len(s.graph.labels) for s in DATABASE)}


def exp_reactions():
    ok, times = 0, []
    for re_, pr in reactions.EQUATIONS:
        t = time.perf_counter(); co = reactions.balance(re_, pr); times.append((time.perf_counter() - t) * 1000)
        L, Rr = Counter(), Counter()
        for i, f in enumerate(re_ + pr):
            for e, k in reactions.parse_formula(f).items():
                (L if i < len(re_) else Rr)[e] += k * co[i]
        ok += L == Rr
    return {"phương trình": len(reactions.EQUATIONS), "cân bằng đúng": ok,
            "ms trung vị": round(statistics.median(times), 3), "ms lớn nhất": round(max(times), 3)}


def scenes():
    out = []
    for s in DATABASE:
        p, kind = layout(s.graph)
        if p:
            out.append((s, kind, render(s.graph, p)[0]))
    return out


def exp_sweep(sc, name, values, make):
    res = []
    for v in values:
        n = cards = full = 0
        t_all = []
        for s, _, img in sc:
            for _ in range(2):
                im = make(img, v)
                t = time.perf_counter(); c, right = pipeline(im, s.key); t_all.append((time.perf_counter() - t) * 1000)
                n += 1; cards += c; full += right
        res.append({name: v, "lượt": n, "đọc đủ thẻ %": round(100 * cards / n, 1), "đúng chất %": round(100 * full / n, 1),
                    "ms trung vị": round(statistics.median(t_all), 1)})
        print(name, v, res[-1], flush=True)
    return res


def exp_geometry(table):
    """Đường Gemini: giả sử Gemini cho khung bao đúng, đo liên kết bằng hình học khi giãn khe hở giữa các thẻ."""
    pairs = []
    g = Graph.from_edges(["O", "H"], [(0, 1)])
    pos = {0: (0.0, 0.0), 1: (np.sqrt(3) / 2, 0.5)}
    for gap in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15, 0.20):
        img, centres = render(g, pos, gap, table, plain=True)
        h, w = img.shape[:2]
        cards = []
        for u, (x, y) in centres.items():
            half = FLAT * 0.58
            cards.append({"id": u + 1, "symbol": g.labels[u], "confidence": 1,
                          "box_2d": [(y - half) / h * 1000, (x - half) / w * 1000, (y + half) / h * 1000, (x + half) / w * 1000]})
        small = cv2.resize(img, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        links, info = geometry.card_links(small, cards)
        pairs.append({"khe hở % cạnh thẻ": round(gap * 100), "khe hở px": info["pairs"][0]["gap_px"] if info["pairs"] else None,
                      "nối": bool(links)})
    # toàn bộ phân tử, khung bao đúng, thẻ sát nhau
    total = right = tp = fp = fn = 0
    fp_dist = []
    for s in DATABASE:
        p, _ = layout(s.graph)
        if not p:
            continue
        img, centres = render(s.graph, p, 0.0, table, plain=True)
        h, w = img.shape[:2]
        cards = [{"id": u + 1, "symbol": s.graph.labels[u], "confidence": 1,
                  "box_2d": [(y - FLAT * .58) / h * 1000, (x - FLAT * .58) / w * 1000, (y + FLAT * .58) / h * 1000, (x + FLAT * .58) / w * 1000]}
                 for u, (x, y) in centres.items()]
        small = cv2.resize(img, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
        data = geometry.apply_geometry(small, {"cards": cards, "connections": []})
        a = analyze(json.dumps(data))
        got = {frozenset((c["a"] - 1, c["b"] - 1)) for c in data["connections"]}
        true = {frozenset(e) for e in s.graph.edges}
        tp += len(got & true); fp += len(got - true); fn += len(true - got)
        for e in got - true:      # liên kết thừa: hai thẻ cách nhau bao xa (theo cạnh thẻ)
            u, v = tuple(e)
            fp_dist.append(round(float(np.hypot(centres[u][0] - centres[v][0], centres[u][1] - centres[v][1]) / FLAT), 2))
        total += 1
        right += len(a.clusters) == 1 and a.clusters[0][1].kind == "MATCH" and a.clusters[0][1].substance.key == s.key
    return {"khe hở": pairs, "phân tử": total, "đúng chất": right, "liên kết đúng": tp, "liên kết thừa": fp,
            "liên kết thiếu": fn, "khoảng cách liên kết thừa": dict(Counter(fp_dist))}


def exp_quality(sc):
    img = distort(sc[0][2], card_px=90)
    rows = []
    for blur in (0, 1, 2, 3, 5, 8):
        m = quality.assess(cv2.GaussianBlur(img, (0, 0), blur) if blur else img)
        rows.append({"mờ σ": blur, "độ nét": m["sharpness"], "kết luận": "chặn" if m["blocking"] else ("nhắc" if m["warnings"] else "đạt")})
    for gain in (1.0, 0.5, 0.3, 0.15):
        m = quality.assess(np.clip(img.astype(np.float32) * gain, 0, 255).astype(np.uint8))
        rows.append({"độ sáng ×": gain, "độ sáng": m["brightness"], "kết luận": "chặn" if m["blocking"] else ("nhắc" if m["warnings"] else "đạt")})
    return rows


if __name__ == "__main__":
    t0 = time.time()
    result = {"đối sánh đồ thị": exp_graph(), "cân bằng phương trình": exp_reactions()}
    print(result, flush=True)
    sc = scenes()
    result["cảnh tổng hợp"] = {"chất dựng được": len(sc), "đặt theo lưới": sum(k == "lưới" for _, k, _ in sc),
                               "đặt tỏa tròn": sum(k == "tỏa tròn" for _, k, _ in sc), "tổng số chất": len(DATABASE),
                               "không dựng được": [s.key for s in DATABASE if s.key not in {x[0].key for x in sc}]}
    rnd = lambda: RNG.uniform(0, 360)
    result["kích thước thẻ"] = exp_sweep(sc, "cạnh thẻ px", [30, 36, 42, 50, 60, 80, 120],
                                         lambda im, v: distort(im, card_px=v, rot=rnd()))
    result["nghiêng"] = exp_sweep(sc, "nghiêng độ", [0, 20, 35, 50, 60],
                                  lambda im, v: distort(im, card_px=70, rot=rnd(), tilt=v))
    result["mờ"] = exp_sweep(sc, "mờ σ px", [0, 1, 1.5, 2, 2.5, 3],
                             lambda im, v: distort(im, card_px=70, rot=rnd(), blur=v))
    result["tối"] = exp_sweep(sc, "độ sáng ×", [1.0, 0.6, 0.4, 0.25, 0.15],
                              lambda im, v: distort(im, card_px=70, rot=rnd(), gain=v, noise=4))
    result["hình học (đường Gemini)"] = {}
    for ratio in (geometry.MAX_RATIO, 1.3):          # ngưỡng hiện tại của sản phẩm và ngưỡng đề xuất
        geometry.MAX_RATIO, keep = ratio, geometry.MAX_RATIO
        result["hình học (đường Gemini)"][f"MAX_RATIO={ratio}"] = {name: exp_geometry(t) for name, t in BACKGROUNDS.items()}
        geometry.MAX_RATIO = keep
    result["chất lượng ảnh"] = exp_quality(sc)
    result["thời gian chạy s"] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Đã lưu", os.path.abspath(OUT))
