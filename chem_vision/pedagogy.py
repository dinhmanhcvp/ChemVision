"""Giải thích lỗi bằng lời lớp 7 và gắn lỗi với quan niệm sai thường gặp.

Mọi câu giải thích sinh ra từ chẩn đoán xác định của phần mềm (liên kết thừa, thiếu, thẻ thiếu, thẻ thừa, hóa trị),
không do AI tự nghĩ ra, nên giữ nguyên nguyên tắc "AI chỉ nhìn, phần mềm kết luận".
"""
from __future__ import annotations

from .core import ELEMENT_NAMES, BY_KEY, ClusterResult
from .curriculum import ROMAN, VALENCE


def _name(sym: str) -> str:
    return f"{sym} ({ELEMENT_NAMES.get(sym, sym)})"


def _valence_phrase(sym: str) -> str:
    vals = VALENCE.get(sym)
    return f"hóa trị {ROMAN[vals[0]]}" if vals else "hóa trị đã biết"


def explain(r: ClusterResult) -> list[str]:
    """Các câu giải thích vì sao kết quả như vậy, nói với học sinh lớp 7."""
    out: list[str] = []
    if r.kind == "MATCH":
        if r.substance.ionic:
            out.append("Các nguyên tố trong chất này liên kết bằng liên kết ion: kim loại nhường electron, phi kim nhận electron "
                       "tạo thành ion trái dấu hút nhau. Vì vậy chất không gồm những phân tử riêng lẻ mà gồm nhiều ion xếp đều đặn.")
        else:
            out.append("Mỗi thẻ nối đủ số thẻ mà hóa trị của nguyên tố cho phép, nên cấu trúc này là một phân tử bền.")
    elif r.kind == "WRONG_BONDS":
        out.append(f"Em dùng đúng và đủ các thẻ của {r.substance.name}, nhưng nối chưa đúng: cùng các nguyên tử mà nối khác nhau "
                   "thì tạo ra chất khác hoặc không tạo ra chất nào.")
        for a, b in sorted(r.extra_bonds.elements()):
            for sym in (a, b):
                vals = VALENCE.get(sym)
                if vals and max(vals) == 1:
                    out.append(f"Thẻ {_name(sym)} có {_valence_phrase(sym)}: mỗi thẻ {sym} chỉ nối được với MỘT thẻ khác, "
                               f"nên không nối {a}–{b} được.")
                    break
            else:
                out.append(f"Trong cấu trúc đúng của {r.substance.name} không có liên kết {a}–{b}.")
        for a, b in sorted(r.missing_bonds.elements()):
            out.append(f"Cần thêm liên kết {a}–{b}: hãy cho thẻ {a} chạm thẻ {b}.")
        if len(r.same_composition) > 1:
            others = ", ".join(s.name for s in r.same_composition if s is not r.substance)
            out.append(f"Chú ý: cùng bộ thẻ này còn ghép được {others} (đồng phân: cùng thành phần, khác cách nối).")
    elif r.kind == "SUGGEST" and r.suggestions:
        s = r.suggestions[0]
        if s.missing:
            parts = ", ".join(f"{n} thẻ {_name(sym)}" for sym, n in sorted(s.missing.items()))
            out.append(f"{s.substance.name.capitalize()} ({s.substance.formula}) cần thêm {parts}.")
        if s.extra:
            parts = ", ".join(f"{n} thẻ {_name(sym)}" for sym, n in sorted(s.extra.items()))
            out.append(f"{parts} không thuộc {s.substance.name}: hãy bỏ ra hoặc đặt riêng.")
        if not s.missing and not s.extra:
            out.append("Đủ thẻ rồi; hãy kiểm tra lại cách nối.")
    elif r.kind == "UNKNOWN":
        out.append("Bộ thẻ này không tạo thành chất nào trong chương trình. Hãy xem hóa trị của từng nguyên tố rồi chọn số thẻ cho đúng.")
    for w in r.valence_warnings:
        out.append("Lưu ý hóa trị: " + w + ".")
    return out


# --------------------------------------------------------------------------- quan niệm sai theo nhật ký lớp
ADVICE = {
    "H-H": ("Nối hai thẻ hiđro với nhau (H–H) trong hợp chất",
            "Nhắc lại: H có hóa trị I, mỗi nguyên tử H chỉ tạo một liên kết; trong H2O, mỗi H nối với O chứ không nối với H."),
    "MONOVALENT": ("Nối một thẻ hóa trị I với nhiều thẻ",
                   "Ôn hóa trị: H, Cl, Na, K, Ag có hóa trị I nên chỉ nối một thẻ; chỉ nguyên tố hóa trị cao (O, C, N...) mới làm trung tâm."),
    "MISSING_H": ("Quên thẻ hiđro",
                  "Yêu cầu học sinh đếm số H cần có theo hóa trị của nguyên tố còn lại (ví dụ nhóm –OH cần một H cho mỗi O)."),
    "EXTRA_CARD": ("Dùng thừa thẻ không thuộc chất",
                   "Cho học sinh liệt kê nguyên tố có trong công thức trước khi lấy thẻ."),
    "ISOMER": ("Nhầm đồng phân (cùng thành phần, khác cách nối)",
               "Dùng cặp C2H5OH và CH3OCH3 để cho thấy công thức phân tử chưa đủ, cần cả cách nối."),
    "WRONG_ORDER": ("Nối sai thứ tự nguyên tử",
                    "Cho học sinh vẽ sơ đồ nối trước khi ghép thẻ, rồi đối chiếu cấu trúc đúng."),
    "ION_AS_MOLECULE": ("Ghép hợp chất ion theo quy ước ghép cặp",
                        "Nhắc: NaCl, CaO... không có phân tử riêng lẻ mà là mạng tinh thể ion; ghép cặp chỉ là quy ước của trò chơi."),
}


def row_tags(row: dict) -> list[str]:
    """Suy ra mã quan niệm sai từ một dòng nhật ký (chỉ dùng các cột đã có sẵn, không cần thêm cột)."""
    result = row.get("kết quả", "")
    bonds = row.get("liên kết sai", "")
    missing, extra = row.get("thẻ thiếu", ""), row.get("thẻ thừa", "")
    key = row.get("chất mục tiêu", "")
    tags: list[str] = []
    if result == "SAI LIÊN KẾT":
        extra_bonds = bonds.split("|")[0].replace(" ", "").split(",") if bonds else []
        if "H-H" in extra_bonds:
            tags.append("H-H")
        elif any(b.split("-")[0] in ("Cl", "Na", "K", "Ag") or b.split("-")[-1] in ("Cl", "Na", "K", "Ag")
                 for b in extra_bonds if "-" in b):
            tags.append("MONOVALENT")
        else:
            tags.append("WRONG_ORDER")
        sub = BY_KEY.get(key)
        if sub is not None and any(o is not sub and o.graph.signature() == sub.graph.signature() for o in BY_KEY.values()):
            tags.append("ISOMER")
    elif result == "GHÉP DỞ" and any(tok.split("x")[0] == "H" for tok in missing.split()):
        tags.append("MISSING_H")
    elif result == "GHÉP DỞ" and extra.strip():
        tags.append("EXTRA_CARD")
    elif result == "ĐÚNG CHẤT KHÁC":
        sub = BY_KEY.get(key)
        if sub is not None and any(o is not sub and o.graph.signature() == sub.graph.signature() for o in BY_KEY.values()):
            tags.append("ISOMER")
    if result == "ĐÚNG" and BY_KEY.get(key) is not None and BY_KEY[key].ionic:
        tags.append("ION_AS_MOLECULE")
    return tags
