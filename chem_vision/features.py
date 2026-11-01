"""Hai tính năng mới của CHEM VISION.

1. Chế độ thử thách: giáo viên chọn bộ đề, học sinh ghép thẻ, hệ thống tự chấm, có
   3 mức gợi ý (trừ điểm) và tổng kết.
2. Nhật ký lớp học: ghi mỗi lượt kiểm tra vào tệp CSV (không lưu ảnh, không lưu tên
   học sinh) và tổng hợp "lỗi thường gặp" để giáo viên điều chỉnh bài giảng.
"""
from __future__ import annotations

import csv
import os
import time
from collections import Counter
from dataclasses import dataclass

from .pedagogy import ADVICE, row_tags
from .curriculum import DECK_GRADE, DECK_STYLE, DECKS, ROMAN, valence_task  # noqa: F401
from .core import (BY_KEY, Analysis, ELEMENT_NAMES, card_label, count_phrase,
                   describe_structure)

# --------------------------------------------------------------------------- 1. thử thách
BASE_SCORE, WRONG_PENALTY, HINT_PENALTY, MIN_SOLVED = 10, 1, 2, 1
MAX_HINTS = 3


@dataclass
class Task:
    key: str
    attempts: int = 0
    hints: int = 0
    solved: bool = False
    skipped: bool = False
    score: int = 0


@dataclass
class Attempt:
    task_key: str
    correct: bool
    message: str
    kind: str          # MATCH_TARGET | MATCH_OTHER | WRONG_BONDS | SUGGEST | UNKNOWN | RECAPTURE | EMPTY


def hint_for(key: str, level: int) -> str:
    """Gợi ý mức 1 (nguyên tố), 2 (số thẻ), 3 (cách nối) cho một chất."""
    g = BY_KEY[key].graph
    if level <= 1:
        names = ", ".join(card_label(s) for s in sorted(set(g.labels)))
        return f"Gợi ý 1: phân tử gồm các nguyên tố {names}."
    if level == 2:
        return f"Gợi ý 2: cần {count_phrase(g.composition())}."
    return f"Gợi ý 3: cách nối: {describe_structure(g)}."


def valence_prompt(key: str) -> str | None:
    """Đề theo hóa trị: nêu hai nguyên tố và hóa trị, không nêu công thức hay tên chất."""
    s = BY_KEY[key]
    task = valence_task(s.graph.composition(), s.formula)
    if task is None:
        return None
    a, va, b, vb = task
    return (f"lập công thức hóa học của hợp chất tạo bởi {ELEMENT_NAMES.get(a, a)} {a} (hóa trị {ROMAN[va]}) "
            f"và {ELEMENT_NAMES.get(b, b)} {b} (hóa trị {ROMAN[vb]}), rồi ghép phân tử đó.")


class Challenge:
    def __init__(self, targets, style: str = "name"):
        unknown = [t for t in targets if t not in BY_KEY]
        if unknown:
            raise ValueError(f"Chất không có trong cơ sở dữ liệu: {', '.join(unknown)}")
        if not targets:
            raise ValueError("Bộ đề không có câu nào.")
        self.tasks = [Task(t) for t in targets]
        self.style = style
        self.index = 0

    @classmethod
    def from_deck(cls, name):
        return cls(DECKS[name], DECK_STYLE.get(name, "name"))

    @property
    def current(self) -> Task | None:
        return self.tasks[self.index] if self.index < len(self.tasks) else None

    @property
    def finished(self) -> bool:
        return self.index >= len(self.tasks)

    def prompt(self) -> str:
        t = self.current
        s = BY_KEY[t.key]
        head = f"Câu {self.index + 1}/{len(self.tasks)}: "
        if self.style == "valence":
            text = valence_prompt(t.key)
            if text:
                return head + text
        return head + f"hãy ghép phân tử {s.name} ({s.formula})."

    def submit(self, analysis: Analysis) -> Attempt:
        t = self.current
        if t is None:
            raise RuntimeError("Bộ đề đã kết thúc.")
        if analysis.status != "OK":
            # ảnh hỏng không bị tính là lần sai
            kind = analysis.status
            return Attempt(t.key, False, analysis.message, kind)
        t.attempts += 1
        target = BY_KEY[t.key]
        for _, r in analysis.clusters:
            if r.kind == "MATCH" and r.substance.key == t.key:
                t.solved = True
                t.score = max(MIN_SOLVED, BASE_SCORE - WRONG_PENALTY * (t.attempts - 1) - HINT_PENALTY * t.hints)
                self.index += 1
                return Attempt(t.key, True, f"Chính xác! Đã ghép đúng {target.name} ({target.formula}). Điểm câu này: {t.score}.", "MATCH_TARGET")
        matched = [r.substance for _, r in analysis.clusters if r.kind == "MATCH"]
        if matched:
            other = matched[0]
            msg = f"Bạn đã ghép đúng {other.name} ({other.formula}), nhưng đề yêu cầu {target.name} ({target.formula})."
            return Attempt(t.key, False, msg, "MATCH_OTHER")
        first = analysis.clusters[0][1]
        msg = "Chưa đúng. " + analysis.message
        return Attempt(t.key, False, msg, first.kind)

    def hint(self) -> str:
        t = self.current
        if t is None:
            raise RuntimeError("Bộ đề đã kết thúc.")
        if t.hints >= MAX_HINTS:
            return "Đã dùng hết 3 gợi ý cho câu này."
        t.hints += 1
        return hint_for(t.key, t.hints)

    def skip(self) -> None:
        t = self.current
        if t is not None:
            t.skipped = True
            self.index += 1

    def summary(self) -> dict:
        total = sum(t.score for t in self.tasks)
        return {
            "điểm": total,
            "tối đa": BASE_SCORE * len(self.tasks),
            "đúng": sum(t.solved for t in self.tasks),
            "bỏ qua": sum(t.skipped for t in self.tasks),
            "gợi ý đã dùng": sum(t.hints for t in self.tasks),
            "câu khó nhất": self._hardest(),
        }

    def _hardest(self):
        done = [t for t in self.tasks if t.attempts or t.hints]
        if not done:
            return None
        t = max(done, key=lambda x: (x.attempts + 2 * x.hints, x.key))
        return BY_KEY[t.key].formula


# --------------------------------------------------------------------------- 2. nhật ký lớp học
FIELDS = ["thời gian", "nhóm", "chất mục tiêu", "kết quả", "thẻ thiếu", "thẻ thừa", "liên kết sai"]


class SessionLog:
    """Ghi một dòng cho mỗi lượt kiểm tra hợp lệ. Nhóm là nhãn như "Nhóm 1"; không lưu ảnh."""

    def __init__(self, path: str | None = None, rows: list[dict] | None = None):
        self.path = path
        self.rows: list[dict] = list(rows or [])
        if path and os.path.exists(path):
            with open(path, newline="", encoding="utf-8-sig") as f:
                self.rows = list(csv.DictReader(f))

    def record(self, group: str, target_key: str, analysis: Analysis, when: float | None = None):
        if analysis.status != "OK":
            return None
        results = [r for _, r in analysis.clusters]
        ok = next((r for r in results if r.kind == "MATCH" and r.substance.key == target_key), None)
        r = ok or results[0]
        missing, extra, bonds = Counter(), Counter(), ""
        if r.kind == "SUGGEST":
            sug = next((s for s in r.suggestions if s.substance.key == target_key), r.suggestions[0])
            missing, extra = sug.missing, sug.extra
        elif r.kind == "WRONG_BONDS":
            bonds = ", ".join(f"{a}-{b}" for (a, b) in r.extra_bonds) + " | " + ", ".join(f"{a}-{b}" for (a, b) in r.missing_bonds)
        outcome = "ĐÚNG" if ok else {"MATCH": "ĐÚNG CHẤT KHÁC", "WRONG_BONDS": "SAI LIÊN KẾT", "SUGGEST": "GHÉP DỞ", "UNKNOWN": "KHÔNG NHẬN RA"}[r.kind]
        row = {
            "thời gian": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(when if when is not None else time.time())),
            "nhóm": group, "chất mục tiêu": target_key, "kết quả": outcome,
            "thẻ thiếu": " ".join(f"{s}x{n}" for s, n in sorted(missing.items())),
            "thẻ thừa": " ".join(f"{s}x{n}" for s, n in sorted(extra.items())),
            "liên kết sai": bonds,
        }
        self.rows.append(row)
        if not self.path:               # chạy không có tệp (bản web: nhật ký nằm ở trình duyệt)
            return row
        new = not os.path.exists(self.path) or os.path.getsize(self.path) == 0
        with open(self.path, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if new:
                w.writeheader()
            w.writerow(row)
        return row

    def to_csv(self) -> str:
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="ignore", lineterminator="\r\n")
        w.writeheader()
        for row in self.rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})
        return buf.getvalue()

    def stats(self) -> dict:
        per: dict[str, dict] = {}
        first_seen: set = set()
        first_ok = first_total = 0
        for row in self.rows:
            key = row["chất mục tiêu"]
            p = per.setdefault(key, {"lượt": 0, "đúng": 0, "lỗi": Counter(), "thiếu": Counter(), "thừa": Counter()})
            p["lượt"] += 1
            if row["kết quả"] == "ĐÚNG":
                p["đúng"] += 1
            else:
                p["lỗi"][row["kết quả"]] += 1
                for field_name, bucket in (("thẻ thiếu", "thiếu"), ("thẻ thừa", "thừa")):
                    for token in row[field_name].split():
                        p[bucket][token.split("x")[0]] += int(token.split("x")[1])
            pair = (row["nhóm"], key)
            if pair not in first_seen:
                first_seen.add(pair)
                first_total += 1
                first_ok += row["kết quả"] == "ĐÚNG"
        return {"theo chất": per, "đúng ngay lần đầu": first_ok, "số cặp nhóm-chất": first_total}

    def teacher_report(self) -> str:
        st = self.stats()
        if not self.rows:
            return "Chưa có lượt kiểm tra nào được ghi."
        lines = [f"Tổng số lượt kiểm tra: {len(self.rows)}."]
        if st["số cặp nhóm-chất"]:
            pct = 100 * st["đúng ngay lần đầu"] / st["số cặp nhóm-chất"]
            lines.append(f"Tỉ lệ nhóm ghép đúng ngay lần đầu: {pct:.0f}% ({st['đúng ngay lần đầu']}/{st['số cặp nhóm-chất']}).")
        hard = sorted(((p["lượt"] - p["đúng"], k) for k, p in st["theo chất"].items() if p["lượt"] > p["đúng"]), reverse=True)
        if hard:
            lines.append("Chất học sinh hay ghép sai nhất:")
            for wrong, key in hard[:3]:
                p = st["theo chất"][key]
                s = BY_KEY[key]
                kind, _ = p["lỗi"].most_common(1)[0]
                line = f"- {s.name} ({s.formula}): sai {wrong}/{p['lượt']} lượt, lỗi chính: {kind.lower()}"
                if p["thiếu"]:
                    sym, n = p["thiếu"].most_common(1)[0]
                    line += f"; hay thiếu thẻ {sym} ({ELEMENT_NAMES.get(sym, sym)})"
                if p["thừa"]:
                    sym, n = p["thừa"].most_common(1)[0]
                    line += f"; hay thừa thẻ {sym} ({ELEMENT_NAMES.get(sym, sym)})"
                lines.append(line + ".")
            lines.append("Gợi ý: dành vài phút ôn lại cấu tạo của các chất trên trước tiết sau.")
        else:
            lines.append("Chưa có chất nào bị ghép sai.")
        tags = Counter(t for row in self.rows for t in row_tags(row))
        if tags:
            lines.append("Quan niệm sai thường gặp và cách xử lý:")
            for code, n in tags.most_common(4):
                label, advice = ADVICE[code]
                lines.append(f"- {label}: {n} lượt. {advice}")
        return "\n".join(lines)
