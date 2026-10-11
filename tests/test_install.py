"""安装脚本的命令行测试：真起子进程跑 install.ps1 / install.sh，不解析脚本文本。

用户目录换成临时目录（LOO0NG_HOME），组件包来源换成从工作树打出来的本地 zip（LOO0NG_SOURCE），
宿主可执行文件换成临时目录里一个假文件（LOO0NG_ZEBAR），并且 LOO0NG_HOST=0：脚本不退出、不打开 Zebar。
**测试一次都不许碰本机真装的 Zebar**，也不碰 ~/.glzr、~/.loo0ng、%APPDATA%。

Windows 上两份脚本都跑（Git Bash 带 sh、unzip、find）；mac 与 Linux 只跑 install.sh。
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


REPO = Path(__file__).resolve().parents[1]
PACKAGE = REPO / "widget"
STARTUP = ('{"$schema": "https://github.com/glzr-io/zebar/raw/v3.3.1/resources/settings-schema.json", '
           '"startupConfigs": [{"pack": "loo0ng", "widget": "\\u6848\\u4ef6\\u5361\\u7247", '
           '"preset": "\\u9ed8\\u8ba4"}]}')
POWERSHELL = shutil.which("powershell") if os.name == "nt" else None
SH = shutil.which("sh") if shutil.which("unzip") else None


def packaged_files():
    """工作树里组件包的文件，相对路径 -> 字节；__pycache__ 不算。"""
    return {path.relative_to(PACKAGE).as_posix(): path.read_bytes()
            for path in PACKAGE.rglob("*") if path.is_file() and "__pycache__" not in path.parts}


def posix(path):
    """Git Bash 的 sh 认 D:/x/y 这种写法；mac 上本来就是 POSIX 路径。"""
    return str(path).replace("\\", "/")


class InstallerCase(unittest.TestCase):
    """每条测试一个临时目录：home、假宿主、包来源、给脚本用的 python 垫片都在里面。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.zebar = self.root / "zebar.exe"
        self.zebar.write_bytes(b"")
        self.zip = self.root / "pack.zip"
        self.make_archive(self.zip, "loo0ng-widget-main")
        self.bin = self.root / "bin"
        self.bin.mkdir()

    def make_archive(self, target, top, with_pack=True):
        """像 GitHub 的归档那样：顶层一个目录，下面 widget/。"""
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("{}/README.md".format(top), "# x\n")
            if with_pack:
                for relative, data in packaged_files().items():
                    archive.writestr("{}/widget/{}".format(top, relative), data)

    @property
    def pack(self):
        return self.home / ".glzr" / "zebar" / "loo0ng"

    @property
    def settings(self):
        return self.home / ".loo0ng" / "卡片设置.json"

    @property
    def zebar_settings(self):
        return self.home / ".glzr" / "zebar" / "settings.json"

    def environment(self, **extra):
        env = dict(os.environ)
        env.update({"LOO0NG_HOME": str(self.home), "LOO0NG_SOURCE": str(self.zip),
                    "LOO0NG_ZEBAR": str(self.zebar), "LOO0NG_HOST": "0", "LOO0NG_SHORTCUT": "0"})
        env.pop("LOO0NG_ROOT", None)   # 没给根目录就是没给，不从外面继承
        env.update(extra)
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        return env

    def assert_pack_matches_working_tree(self):
        installed = {path.relative_to(self.pack).as_posix(): path.read_bytes()
                     for path in self.pack.rglob("*") if path.is_file()}
        self.assertEqual(installed, packaged_files())


class PowerShellInstallerTests(InstallerCase):
    """install.ps1：像律师那样走 iex（文件不带 BOM，-File 会按 ANSI 读坏汉字），stdin 关掉，脚本按无人值守走。
    脚本把结果留在 $ok 里，这里据它定退出码。"""

    def setUp(self):
        if not POWERSHELL:
            self.skipTest("没有 Windows PowerShell")
        super().setUp()
        # 脚本按 PATH 找 python：垫片指向跑测试的解释器，并把它的真实路径报回去（快捷方式要它旁边的 pythonw）。
        self.shim("python")

    def shim(self, name):
        (self.bin / (name + ".cmd")).write_text('@"{}" %*\r\n'.format(sys.executable), encoding="utf-8")

    def run_installer(self, **extra):
        env = self.environment(**extra)
        command = ("iex (Get-Content -Raw -Encoding UTF8 '{}'); if (-not $ok) {{ exit 1 }}"
                   .format(REPO / "install.ps1"))
        return subprocess.run([POWERSHELL, "-NoProfile", "-Command", command], env=env, cwd=str(self.root),
                              stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8",
                              errors="replace")

    def test_the_store_stub_python_is_skipped_for_py(self):
        """#32：PATH 上的 python 是微软商店的占位（往 stderr 写一句、以 9009 退出）时，退到 py，安装照常。"""
        (self.bin / "python.cmd").write_text("@echo Python was not found 1>&2\r\n@exit /b 9009\r\n",
                                             encoding="utf-8")
        self.shim("py")
        result = self.run_installer(LOO0NG_ROOT=r"D:\案件", LOO0NG_SHORTCUT="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertTrue((self.home / "Desktop" / "打开案件卡片.lnk").is_file())

    def test_fresh_install_lays_down_pack_settings_and_startup(self):
        result = self.run_installer(LOO0NG_ROOT=r"D:\案件;E:\别的案件", LOO0NG_SHORTCUT="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        # 根目录照 README 的约定写成 /，设置文件是不带 BOM 的 UTF-8。
        self.assertEqual(self.settings.read_bytes(),
                         '{"根目录": ["D:/案件", "E:/别的案件"]}'.encode("utf-8"))
        self.assertEqual(self.zebar_settings.read_bytes(), STARTUP.encode("utf-8"))
        self.assertTrue((self.home / "Desktop" / "打开案件卡片.lnk").is_file())
        self.assertIn("已安装 loo0ng", result.stdout)

    def test_update_replaces_the_pack_but_keeps_settings_and_local_storage(self):
        self.pack.mkdir(parents=True)
        (self.pack / "stale.txt").write_text("old", encoding="utf-8")
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text('{"根目录": ["D:/mine"]}', encoding="utf-8")
        cache = self.home / "AppData" / "Roaming" / "zebar" / "webview-cache" / "loo0ng" / "EBWebView" / "Default"
        for name in ("Cache", "Code Cache", "Local Storage"):
            (cache / name).mkdir(parents=True)
            (cache / name / "x").write_bytes(b"x")
        result = self.run_installer(LOO0NG_ROOT=r"D:\ignored")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertEqual(self.settings.read_text(encoding="utf-8"), '{"根目录": ["D:/mine"]}')
        self.assertFalse((cache / "Cache").exists())
        self.assertFalse((cache / "Code Cache").exists())
        self.assertTrue((cache / "Local Storage" / "x").is_file())
        self.assertIn("已更新 loo0ng", result.stdout)
        self.assertFalse((self.home / "Desktop" / "打开案件卡片.lnk").exists())

    def test_without_a_root_it_installs_and_says_where_the_settings_go(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertFalse(self.settings.exists())
        self.assertIn(str(self.settings), result.stdout)

    def test_an_archive_without_the_pack_changes_nothing(self):
        self.make_archive(self.zip, "something-else", with_pack=False)
        self.pack.mkdir(parents=True)
        (self.pack / "keep.txt").write_text("keep", encoding="utf-8")
        result = self.run_installer(LOO0NG_ROOT=r"D:\案件")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.pack / "keep.txt").is_file())
        self.assertFalse(self.settings.exists())
        self.assertFalse(self.zebar_settings.exists())

    def test_missing_host_stops_before_touching_anything(self):
        result = self.run_installer(LOO0NG_ZEBAR=str(self.root / "nowhere.exe"), LOO0NG_ROOT=r"D:\案件")
        self.assertEqual(result.returncode, 1)
        self.assertIn("github.com/glzr-io/zebar", result.stdout)
        self.assertFalse(self.pack.exists())


class ShInstallerTests(InstallerCase):
    """install.sh：用 sh 跑它，stdout 不是终端，脚本按无人值守走。"""

    def setUp(self):
        if not SH:
            self.skipTest("没有 sh 或 unzip")
        super().setUp()
        shim = self.bin / "python3"
        shim.write_text('#!/bin/sh\nexec "{}" "$@"\n'.format(posix(sys.executable)), encoding="utf-8")
        shim.chmod(0o755)

    def run_installer(self, **extra):
        env = self.environment(**extra)
        env.update({"LOO0NG_HOME": posix(self.home), "LOO0NG_SOURCE": posix(self.zip),
                    "LOO0NG_ZEBAR": posix(self.zebar)})
        if "LOO0NG_ZEBAR" in extra:
            env["LOO0NG_ZEBAR"] = posix(extra["LOO0NG_ZEBAR"])
        return subprocess.run([SH, posix(REPO / "install.sh")], env=env, cwd=str(self.root),
                              stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8",
                              errors="replace")

    def test_fresh_install_lays_down_pack_settings_and_startup(self):
        self.zebar.chmod(0o755)
        result = self.run_installer(LOO0NG_ROOT="/Users/x/案件;/Volumes/y/别的案件", LOO0NG_SHORTCUT="1")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertEqual(self.settings.read_bytes(),
                         '{"根目录": ["/Users/x/案件", "/Volumes/y/别的案件"]}'.encode("utf-8"))
        self.assertEqual(self.zebar_settings.read_bytes(), STARTUP.encode("utf-8"))
        link = self.home / "Desktop" / "打开案件卡片.command"
        self.assertIn("launch.py", link.read_text(encoding="utf-8"))
        self.assertIn("已安装 loo0ng", result.stdout)

    def test_update_replaces_the_pack_but_keeps_settings(self):
        self.zebar.chmod(0o755)
        self.pack.mkdir(parents=True)
        (self.pack / "stale.txt").write_text("old", encoding="utf-8")
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text('{"根目录": ["/Users/x/mine"]}', encoding="utf-8")
        result = self.run_installer(LOO0NG_ROOT="/ignored")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertEqual(self.settings.read_text(encoding="utf-8"), '{"根目录": ["/Users/x/mine"]}')
        self.assertIn("已更新 loo0ng", result.stdout)
        self.assertFalse((self.home / "Desktop" / "打开案件卡片.command").exists())

    def test_without_a_root_it_installs_and_says_where_the_settings_go(self):
        self.zebar.chmod(0o755)
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_pack_matches_working_tree()
        self.assertFalse(self.settings.exists())
        self.assertIn("卡片设置.json", result.stdout)

    def test_an_archive_without_the_pack_changes_nothing(self):
        self.zebar.chmod(0o755)
        self.make_archive(self.zip, "something-else", with_pack=False)
        result = self.run_installer(LOO0NG_ROOT="/x")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.pack.exists())
        self.assertFalse(self.zebar_settings.exists())

    def test_missing_host_stops_before_touching_anything(self):
        result = self.run_installer(LOO0NG_ZEBAR=str(self.root / "nowhere"), LOO0NG_ROOT="/x")
        self.assertEqual(result.returncode, 1)
        self.assertIn("github.com/glzr-io/zebar", result.stdout)
        self.assertFalse(self.pack.exists())


if __name__ == "__main__":
    unittest.main()
