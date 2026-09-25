"""包本身的守门：白名单、ASCII 文件名、随包依赖的哈希与导入闭包、窗口预设、去掉的页脚。

这些检查原先是人手跑的一串命令（见开发说明），#16 去 luxon 时要重算，所以落成测试。
不碰页面行为：两页、材质、拖动仍归原型与 Windows 人手验收。
"""
import hashlib
import json
from pathlib import Path
import re
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "widget"
VENDOR = PACKAGE / "vendor"
ZPACK = json.loads((PACKAGE / "zpack.json").read_text(encoding="utf-8"))
WIDGET = ZPACK["widgets"][0]
# 静态导入的说明符：import x from"./y.js"、export ... from"./y.js"、import"./y.js"。
SPECIFIER = re.compile(r'(?:\bfrom|\bimport)\s*["\']([^"\']+)["\']')
# 颜色字面量：#hex，以及括号里直接写数字的 rgb()/rgba()/hsl()/hsla()；rgba(var(--x), .9) 不算。
COLOR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\(\s*[\d.]')


def packaged_files():
    """包里除 zpack.json 以外的文件；zpack.json 由宿主读，不走资源服务器。"""
    for path in sorted(PACKAGE.rglob("*")):
        if path.is_file() and path.name != "zpack.json" and "__pycache__" not in path.parts:
            yield path.relative_to(PACKAGE).as_posix()


def matches(pattern, relative):
    """includeFiles 的 glob：`**` 跨目录，`*` 不跨目录。"""
    regex = "".join("[^/]*" if part == "*" else ".*" if part == "**" else re.escape(part)
                    for part in re.split(r"(\*\*|\*)", pattern))
    return re.fullmatch(regex, relative) is not None


class PackageTests(unittest.TestCase):
    def test_include_files_cover_every_packaged_file(self):
        """白名单是资源服务器的白名单：漏一个文件，宿主回 500，窗里是一张报错页。"""
        for relative in packaged_files():
            with self.subTest(file=relative):
                self.assertTrue(any(matches(p, relative) for p in WIDGET["includeFiles"]),
                                "{} 不在 includeFiles 里".format(relative))

    def test_the_entry_page_is_covered_too(self):
        entry = WIDGET["htmlPath"].removeprefix("./")
        self.assertTrue(any(matches(p, entry) for p in WIDGET["includeFiles"]))
        self.assertTrue((PACKAGE / entry).is_file())

    def test_every_packaged_name_is_ascii(self):
        for relative in packaged_files():
            with self.subTest(file=relative):
                relative.encode("ascii")

    def test_the_window_is_transparent_with_the_default_preset(self):
        self.assertIs(WIDGET["transparent"], True)
        preset = WIDGET["presets"][0]
        self.assertEqual(preset["name"], "默认")
        self.assertEqual((preset["width"], preset["height"]), ("440px", "620px"))

    def test_manifest_records_exactly_the_packaged_modules_with_their_hashes(self):
        manifest = json.loads((VENDOR / "manifest.json").read_text(encoding="utf-8"))
        recorded = {entry["file"]: entry for entry in manifest}
        self.assertEqual(sorted(recorded), sorted(p.name for p in VENDOR.glob("*.js")))
        for name, entry in recorded.items():
            with self.subTest(file=name):
                digest = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
                self.assertEqual(digest, entry["sha256"])
                self.assertTrue(entry["url"].startswith("https://"))
                self.assertRegex(entry["upstream_sha256"], r"^[0-9a-f]{64}$")

    def test_every_import_resolves_inside_the_package(self):
        """随包依赖闭包：页面与随包模块的静态导入一律落在包内，装完断网也起得来。"""
        for path in list(PACKAGE.glob("*.js")) + list(VENDOR.glob("*.js")):
            source = path.read_text(encoding="utf-8")
            for specifier in SPECIFIER.findall(source):
                with self.subTest(file=path.name, specifier=specifier):
                    self.assertTrue(specifier.startswith("./"), "不是包内相对路径")
                    self.assertTrue((path.parent / specifier).is_file(), "指向的文件不在包里")

    def test_luxon_is_gone(self):
        """没人用的 luxon 不随包：文件、许可证、manifest 条目、导入全都不留。"""
        for path in PACKAGE.rglob("*"):
            with self.subTest(file=path.name):
                self.assertNotIn("luxon", path.name.lower())
        for path in list(PACKAGE.glob("*.js")) + list(VENDOR.glob("*.js")):
            with self.subTest(file=path.name):
                # 不用 assertNotIn：它会把整份随包 bundle 打进失败信息。
                self.assertFalse("luxon" in path.read_text(encoding="utf-8").lower(),
                                 "{} 里还提到 luxon".format(path.name))

    def test_the_page_has_no_footer_and_no_manual_scan_button(self):
        """#16 去页脚：页脚、扫描时刻、手动扫描按钮都不在；开发预览通道留着。"""
        page = (PACKAGE / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<footer", page)
        self.assertNotIn("扫一次", page)
        self.assertIn('id="preview"', page)
        app = (PACKAGE / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("扫一次", app)
        self.assertIn("get('dev')", app)

    def test_every_color_lives_in_the_root_variable_table(self):
        """ADR-0004：颜色全抽成变量。#22 换冷色调只换 `:root` 那一张表，别处不许散落色值。"""
        css = (PACKAGE / "style.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        root = re.search(r":root\s*\{[^}]*\}", css)
        self.assertIsNotNone(root, "样式表里没有 :root 变量表")
        rest = css[:root.start()] + css[root.end():]
        self.assertEqual(COLOR_LITERAL.findall(rest), [])


if __name__ == "__main__":
    unittest.main()
