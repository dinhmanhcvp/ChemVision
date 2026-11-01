"""Kiểm tra tĩnh giao diện web: mọi nút có xử lý và có đích thật, mọi id mà mã JS dùng đều có trong HTML, ngôn ngữ thiết kế được giữ
(tương phản, giảm chuyển động, không tải tài nguyên ngoài, linh vật hợp lệ)."""
import os
import re
import unittest
import xml.dom.minidom

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
PUB = os.path.join(ROOT, "public")


def read(name):
    return open(os.path.join(PUB, name), encoding="utf-8").read()


HTML, CSS = read("index.html"), read("style.css")
JS = read("app.js") + "\n" + read("ui.js") + "\n" + read("progress.js")
VIEWS = ["ghep", "thuthach", "canbang", "lop", "them"]

# Nút chỉ chạy trong trình duyệt (không có dữ liệu để máy chủ xử lý): lí do ghi rõ để người sau không phải đoán
CLIENT_ONLY = {
    "btn-camera": "mở camera của trình duyệt",
    "btn-close": "đóng hộp thoại",
    "class-close": "đóng hộp thoại",
    "class-copy": "chép mã vào bộ nhớ tạm",
    "class-leave": "quên mã lớp trong phiên này",
    "btn-clear": "xóa nhật ký lưu trong trình duyệt",
    "confirm-yes": "trả lời hộp xác nhận",
    "confirm-no": "trả lời hộp xác nhận",
    "welcome-close": "ẩn lời chào",
    "howto-open": "hiện lại lời chào",
    "eq-next": "chuyển sang phương trình kế tiếp",
    "btn-csv": "lưu tệp CSV đã nhận từ máy chủ",
}
for _v in VIEWS:
    CLIENT_ONLY["tab-" + _v] = "chuyển thẻ"
# Nút còn lại phải dẫn tới một lời gọi máy chủ (trực tiếp hoặc qua các hàm được gọi)
SERVER_BACKED = {
    "btn-check": "/api/analyze", "btn-demo": "/api/analyze", "ch-hint": "/api/hint", "eq-check": "/api/equation",
    "eq-reveal": "/api/equation", "btn-report": "/api/report", "class-create": "/api/classroom",
    "class-open": "/api/classroom", "class-join": "/api/classroom", "class-end": "/api/classroom",
    "ch-skip": "/api/classroom", "ch-end": "/api/classroom", "sg-yes": "/api/classroom", "sg-no": "/api/classroom",
}

def parse_functions(text):
    """Tách các khai báo hàm bằng cách đếm ngoặc nhọn (đúng cả với hàm viết một dòng)."""
    found = {}
    for m in re.finditer(r"(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*\{", text):
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        found[m.group(1)] = text[m.end():i - 1]
    return found


FUNCTIONS = parse_functions(JS)


def reaches(text: str, endpoint: str, depth: int = 4, seen=None) -> bool:
    seen = seen or set()
    if re.fullmatch(r"\w+", text.strip()):               # xử lý được gắn bằng tên hàm trần: hint, skip...
        text = FUNCTIONS.get(text.strip(), "")
    if endpoint in text:
        return True
    if depth == 0:
        return False
    for name in set(re.findall(r"\b([A-Za-z_]\w*)\(", text)):
        if name in FUNCTIONS and name not in seen:
            seen.add(name)
            if reaches(FUNCTIONS[name], endpoint, depth - 1, seen):
                return True
    return False


def handler_text(button_id: str) -> str:
    m = re.search(r'\$\("%s"\)\.addEventListener\("click",\s*(.+)\);' % re.escape(button_id), JS)
    assert m, f"nút {button_id} chưa được gắn sự kiện click"
    return m.group(1)


class Wiring(unittest.TestCase):
    def test_every_id_used_by_js_exists_in_html(self):
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        used = set(re.findall(r'\$\("([^"]+)"\)', JS))
        dynamic = {"retry"} | {u for u in used if u.startswith("eq-c")}
        self.assertEqual(sorted(used - ids - dynamic), [])

    def test_tabs_and_views_match(self):
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        for v in VIEWS:
            self.assertIn("tab-" + v, ids)
            self.assertIn("view-" + v, ids)
            self.assertIn(f'data-view="{v}"', HTML)
        self.assertIn('const VIEWS = ["ghep", "thuthach", "canbang", "lop", "them"]', JS)
        self.assertRegex(JS, r'for \(const v of VIEWS\) \$\("tab-" \+ v\)\.addEventListener\("click"')
        self.assertIn('aria-label="Chức năng"', HTML)

    def test_every_button_is_classified_and_wired(self):
        buttons = set(re.findall(r'<button[^>]*\sid="([^"]+)"', HTML))
        classified = set(CLIENT_ONLY) | set(SERVER_BACKED)
        self.assertEqual(sorted(buttons - classified), [], "nút mới chưa được phân loại")
        self.assertEqual(sorted(classified - buttons), [], "phân loại nút không còn tồn tại")
        for b in buttons:
            if b.startswith("tab-") or b in ("confirm-yes", "confirm-no"):
                continue
            self.assertTrue(re.search(r'\$\("%s"\)\.(addEventListener|onclick)' % re.escape(b), JS), f"nút {b} chưa gắn xử lý")

    def test_server_backed_buttons_reach_their_endpoint(self):
        for button, endpoint in SERVER_BACKED.items():
            self.assertTrue(reaches(handler_text(button), endpoint), f"nút {button} không dẫn tới {endpoint}")

    def test_every_endpoint_called_by_js_exists_as_function(self):
        for endpoint in set(re.findall(r'"/api/([a-z]+)"', JS)):
            self.assertTrue(os.path.isfile(os.path.join(ROOT, "api", endpoint + ".py")), endpoint)

    def test_no_browser_dialogs_and_safe_text_insertion(self):
        self.assertNotRegex(JS, r"(?<![\w.])(confirm|alert|prompt)\(")
        for banned in ("innerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(banned, JS)

    def test_camera_is_requested_only_when_the_user_presses_the_button(self):
        self.assertEqual(len(re.findall(r"getUserMedia\(", JS)), 1)
        self.assertIn("getUserMedia(", FUNCTIONS["toggleCamera"])

    def test_network_failures_are_reported_not_swallowed(self):
        self.assertIn("catch", FUNCTIONS["api"])
        self.assertIn("status: 0", FUNCTIONS["api"])
        self.assertIn("unhandledrejection", JS)

    def test_ending_a_class_only_clears_state_after_server_confirms(self):
        end = FUNCTIONS["endClass"]
        self.assertLess(end.index("status !== 200"), end.index('setJson("session", CLASS_TEACHER_KEY, null)'))

    def test_challenge_buttons_are_visible_to_the_teacher_dashboard(self):
        for kind in ("start", "skip", "hint", "end", "suggest"):
            self.assertIn('sendActivity("%s"' % kind, JS)

    def test_e2e_suite_present_and_valid(self):
        path = os.path.join(ROOT, "scripts", "e2e_browser.js")
        text = open(path, encoding="utf-8").read()
        self.assertIn("window.runE2E", text)
        self.assertNotIn("alert(", text)

    def test_form_controls_have_names(self):
        for tag in re.findall(r"<(?:select|input)\b[^>]*>", HTML):
            if 'type="file"' in tag:
                continue
            self.assertRegex(tag, r'aria-label=|id="(code|group|speak|fx|sfx)"', tag)

    def test_dialogs_have_close_paths(self):
        for dialog_id, closer in (("report-dialog", "btn-close"), ("class-dialog", "class-close"), ("confirm-dialog", "confirm-no")):
            self.assertIn(f'id="{dialog_id}"', HTML)
            self.assertIn(f'id="{closer}"', HTML)


def luminance(hex_color):
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(block):
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6})", block))


class DesignLanguage(unittest.TestCase):
    light = tokens(re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1))
    dark = {**light, **tokens(re.search(r'prefers-color-scheme: dark\) \{\s*:root:not\(\[data-theme="light"\]\) \{(.*?)\n  \}', CSS, re.S).group(1))}

    def check_pairs(self, t, pairs):
        for fg, bg, minimum in pairs:
            ratio = contrast(t[fg], t[bg])
            self.assertGreaterEqual(ratio, minimum, f"{fg} trên {bg}: {ratio:.2f} < {minimum}")

    PAIRS = [   # (chữ, nền, ngưỡng tối thiểu): cùng một danh sách cho nền sáng và nền tối
        ("ink", "bg", 4.5), ("ink", "surface", 4.5), ("ink", "surface-2", 4.5), ("muted", "bg", 4.5), ("muted", "surface", 4.5), ("muted", "surface-2", 4.5),
        ("bg", "ink", 4.5),                                                      # chữ trên nút nền mực
        ("ok", "ok-l", 4.5), ("close", "close-l", 4.5), ("bad", "bad-l", 4.5),   # tiêu đề kết quả
        ("ok", "surface", 4.5), ("close", "surface", 4.5), ("bad", "surface", 4.5),
        ("on-hl", "hl", 4.5),                                                    # chữ trên nền bút dạ vàng (thẻ đang chọn, số sao)
        ("ink", "ok-l", 4.5),
    ]

    def test_light_theme_contrast_meets_wcag_aa(self):
        self.check_pairs(self.light, self.PAIRS)

    def test_dark_theme_contrast_meets_wcag_aa(self):
        self.check_pairs(self.dark, self.PAIRS)

    def test_status_is_never_conveyed_by_colour_alone(self):
        for seal in ("ok", "close", "bad"):                       # mỗi trạng thái có hình riêng
            self.assertTrue(os.path.isfile(os.path.join(PUB, "img", f"seal-{seal}.svg")), seal)
        glyphs = {s: re.sub(r'class="[^"]*"', "", open(os.path.join(PUB, "img", f"seal-{s}.svg"), encoding="utf-8").read().split("<g")[1])
                  for s in ("ok", "close", "bad")}
        self.assertEqual(len(set(glyphs.values())), 3)

    def test_reduced_motion_and_dark_mode_are_supported(self):
        self.assertIn("prefers-reduced-motion: reduce", CSS)
        self.assertRegex(CSS, r"prefers-reduced-motion: reduce\) \{[^}]*animation-duration: \.001ms")
        self.assertIn("#confetti { display: none; }", CSS)
        self.assertIn("reducedMotion()", read("ui.js"))

    def test_no_external_resources_so_csp_stays_strict(self):
        for name in ("index.html", "style.css", "app.js", "ui.js", "progress.js"):
            urls = re.findall(r"https?://[^\s\"')]+", read(name))
            self.assertEqual([u for u in urls if "w3.org" not in u], [], name)

    def test_seals_illustrations_and_logo_are_valid_svg(self):
        for seal in ("wait", "start", "ok", "close", "bad"):
            path = os.path.join(PUB, "img", f"seal-{seal}.svg")
            self.assertTrue(os.path.isfile(path), seal)
            xml.dom.minidom.parse(path)
        for name in ("water-cards.svg", "water-cards-on-dark.svg", "hexgrid.svg"):
            xml.dom.minidom.parse(os.path.join(PUB, "img", name))
        xml.dom.minidom.parse(os.path.join(PUB, "favicon.svg"))
        self.assertIn('rel="icon"', HTML)
        self.assertIn('const MOODS = ["wait", "happy", "cheer", "think", "oops"]', read("ui.js"))

    def test_every_icon_used_is_defined_and_drawn(self):
        used = set(re.findall(r"\bic-([a-z]+)\b", HTML)) | set(re.findall(r'ico: "([a-z]+)"', JS))
        for m in re.finditer(r"\bicon\(", JS):                    # tên biểu tượng nằm trong lời gọi icon(...), kể cả icon(a ? "x" : "y")
            depth, i = 1, m.end()
            while depth and i < len(JS):
                depth += (JS[i] == "(") - (JS[i] == ")")
                i += 1
            used |= set(re.findall(r'"([a-z]+)"', JS[m.end():i - 1]))
        defined = set(re.findall(r"\.ic-([a-z]+) \{ --ic: url\(/img/i/([a-z]+)\.svg\)", CSS))
        self.assertEqual(sorted(used - {a for a, _ in defined}), [], "biểu tượng được dùng nhưng chưa có luật CSS")
        for name, file in defined:
            self.assertEqual(name, file)
            path = os.path.join(PUB, "img", "i", file + ".svg")
            self.assertTrue(os.path.isfile(path), file)
            xml.dom.minidom.parse(path)

    def test_no_emoji_as_interface_icons(self):
        emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿⏩-⏺️‍]")      # mũi tên → trong tên phương trình là chữ, không bị cấm
        for name in ("index.html", "style.css", "app.js", "ui.js", "progress.js"):
            self.assertEqual(emoji.findall(read(name)), [], f"{name} dùng emoji hoặc kí tự biểu tượng thay cho biểu tượng SVG")

    def test_touch_targets_and_typography(self):
        self.assertRegex(CSS, r"min-height: 48px")
        self.assertRegex(CSS, r"font: 17px/1\.55")
        self.assertNotIn("ui-rounded", CSS)                       # phông bo tròn là dấu hiệu của giao diện học tập rập khuôn
        self.assertNotRegex(CSS, r"linear-gradient|radial-gradient")  # không dùng nền chuyển màu trang trí
        self.assertNotIn("box-shadow: 0 4px 0", CSS)              # không dùng nút "bóng đáy" kiểu trò chơi

    def test_layout_cannot_overflow_on_phones(self):
        self.assertIn("minmax(0, 1fr)", CSS)
        self.assertRegex(CSS, r"\.card \{[^}]*min-width: 0")
        self.assertIn("overflow-wrap: anywhere", CSS)

    def test_no_leaderboard_or_countdown_pressure(self):
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", HTML + JS, flags=re.S).lower()      # bỏ chú thích mã
        for word in ("leaderboard", "bảng xếp hạng", "countdown", "đếm ngược", "streak"):
            self.assertNotIn(word, text)

    def test_formulas_use_subscripts(self):
        self.assertIn('el("sub"', read("ui.js"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
