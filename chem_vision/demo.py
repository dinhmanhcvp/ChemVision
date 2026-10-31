"""Chạy thử nhanh: python -m chem_vision.demo"""
from .core import analyze
from .features import Challenge, SessionLog


def mol(atoms, edges):
    s = atoms.split()
    return {"cards": [{"id": i + 1, "symbol": x, "confidence": 0.95} for i, x in enumerate(s)],
            "connections": [{"a": a, "b": b} for a, b in edges]}


if __name__ == "__main__":
    for title, raw in [("Nước ghép đúng", mol("H O H", [(1, 2), (2, 3)])),
                       ("Nước sai liên kết", mol("H H O", [(1, 2), (2, 3)])),
                       ("Ghép dở", mol("H O", [(1, 2)]))]:
        a = analyze(raw)
        print(f"[{title}] {a.message}\n  đọc: {a.speech}\n")
    ch = Challenge.from_deck("Khởi động")
    print(ch.prompt())
    print(ch.submit(analyze(mol("H H O", [(1, 2), (2, 3)]))).message)
    print(ch.hint())
    log = SessionLog("nhat_ky_demo.csv")
    log.record("Nhóm 1", "H2O", analyze(mol("H O", [(1, 2)])))
    print(log.teacher_report())
