"""唤起脚本的命令行测试：真起子进程调它，不导入脚本里的函数。

假宿主是临时目录里一个叫 zebar 的可执行文件（Windows 上是 zebar.bat），
它把收到的参数写成 JSON 再按给定的码退出。测试从不碰本机真装的 Zebar：
PATH 一律换成测试自己的目录，固定路径一律由 `--固定路径 平台=路径` 注入。
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "widget"
COMMAND = ["start-widget-preset", "--pack", "loo0ng",
           "--widget-name", "案件卡片", "--preset", "默认"]
RECORDER = """import json, os, sys
with open(os.environ["FAKE_HOST_RECORD"], "w", encoding="utf-8") as recorded:
    json.dump(sys.argv[1:], recorded, ensure_ascii=False)
sys.exit(int(os.environ["FAKE_HOST_EXIT"]))
"""


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.empty = self.root / "empty"
        self.empty.mkdir()
        self.recorded = self.root / "argv.json"

    def fake_host(self, name):
        """临时目录里放一个假宿主，返回它的路径。"""
        directory = self.root / name
        directory.mkdir()
        recorder = directory / "recorder.py"
        recorder.write_text(RECORDER, encoding="utf-8")
        if os.name == "nt":
            host = directory / "zebar.bat"
            host.write_text('@echo off\r\n"{}" "{}" %*\r\n'.format(sys.executable, recorder),
                            encoding="utf-8")
        else:
            host = directory / "zebar"
            host.write_text('#!/bin/sh\nexec "{}" "{}" "$@"\n'.format(sys.executable, recorder),
                            encoding="utf-8")
            host.chmod(0o755)
        return host

    def launch(self, *args, path=None, exit_code=0):
        env = {key: value for key, value in os.environ.items() if key.upper() != "PATH"}
        env["PATH"] = str(path if path is not None else self.empty)
        env["FAKE_HOST_RECORD"] = str(self.recorded)
        env["FAKE_HOST_EXIT"] = str(exit_code)
        return subprocess.run([sys.executable, str(PACKAGE / "launch.py"), *map(str, args)],
                              env=env, cwd=str(self.empty), capture_output=True,
                              encoding="utf-8")

    def argv(self):
        return json.loads(self.recorded.read_text(encoding="utf-8"))

    def test_calls_the_host_on_path_with_exactly_that_one_command(self):
        host = self.fake_host("onpath")
        result = self.launch(path=host.parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.argv(), COMMAND)

    def test_falls_back_to_the_fixed_paths_of_this_platform_in_order(self):
        host = self.fake_host("fixed")
        missing = self.root / "missing" / "zebar"
        result = self.launch("--平台", "darwin",
                             "--固定路径", "darwin={}".format(missing),
                             "--固定路径", "darwin={}".format(host))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.argv(), COMMAND)

    def test_fixed_paths_of_another_platform_are_never_looked_at(self):
        host = self.fake_host("elsewhere")
        result = self.launch("--平台", "darwin", "--固定路径", "win32={}".format(host))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.recorded.exists())

    def test_the_host_on_path_wins_over_the_fixed_paths(self):
        on_path = self.fake_host("onpath")
        fixed = self.fake_host("fixed")
        result = self.launch("--平台", "win32", "--固定路径", "win32={}".format(fixed),
                             path=on_path.parent)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.argv(), COMMAND)

    def test_nothing_found_says_where_to_install_and_exits_non_zero(self):
        missing = self.root / "missing" / "zebar"
        result = self.launch("--平台", "win32", "--固定路径", "win32={}".format(missing))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertIn("Zebar", result.stdout)
        self.assertIn("https://github.com/glzr-io/zebar", result.stdout)

    def test_a_platform_without_a_fixed_path_only_looks_at_path(self):
        result = self.launch("--平台", "linux")
        self.assertEqual(result.returncode, 1)
        self.assertIn("https://github.com/glzr-io/zebar", result.stdout)

    def test_the_host_exit_code_is_passed_through(self):
        host = self.fake_host("onpath")
        for code in (1, 3):
            with self.subTest(code=code):
                result = self.launch(path=host.parent, exit_code=code)
                self.assertEqual(result.returncode, code)
                self.assertEqual(self.argv(), COMMAND)

    def test_the_two_real_install_paths_are_spelled_out_in_the_script(self):
        # 这两个路径一跑就会把本机真装的 Zebar 起来、把卡片开出来，所以测试不许走它们；
        # 盯字面值是唯一防手滑的办法。真的跑通归 Windows 人手验收与 mac 交付票。
        source = (PACKAGE / "launch.py").read_text(encoding="utf-8")
        # 连两端的引号一起断言，不然 zebarr 这种多一个字母的手滑照样当子串通过。
        self.assertIn('"/Applications/Zebar.app/Contents/MacOS/zebar"', source)
        self.assertIn(r'"C:\Program Files\glzr.io\Zebar\zebar.exe"', source)

    def test_a_fixed_path_that_is_a_directory_is_not_taken_for_the_host(self):
        host = self.fake_host("fixed")
        result = self.launch("--平台", "darwin",
                             "--固定路径", "darwin={}".format(host.parent),
                             "--固定路径", "darwin={}".format(host))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.argv(), COMMAND)


if __name__ == "__main__":
    unittest.main()
