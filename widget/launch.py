#!/usr/bin/env python3
"""找到 Zebar 宿主并让它打开案件卡片；宿主没开就连宿主一起起来。"""
import argparse
import os
import shutil
import subprocess
import sys

# 唤起的三个入口（随宿主启动、桌面快捷方式、agent 一句话）共用这一条命令。
# 宿主对已经开着的预设无事发生，所以这里不做任何「带到前面」。
COMMAND = ("start-widget-preset", "--pack", "loo0ng",
           "--widget-name", "案件卡片", "--preset", "默认")

# PATH 里没有 zebar 时，按平台挨个看这些固定路径。
FIXED_PATHS = {
    "darwin": ("/Applications/Zebar.app/Contents/MacOS/zebar",),
    "win32": (r"C:\Program Files\glzr.io\Zebar\zebar.exe",),
}

NOT_FOUND = "没找到 Zebar：先去 https://github.com/glzr-io/zebar 装一个，再跑这条命令。"


def say(text):
    """桌面快捷方式走 pythonw，那里 stdout 是 None；这句话不许因此没人看见。"""
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")
        print(text)
    elif sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, "案件卡片", 0x10)  # MB_ICONERROR


def parse_fixed_path(item):
    """把 `平台=路径` 拆开；`--固定路径` 用它，测试注入自己的路径表。"""
    platform, separator, path = item.partition("=")
    if not (separator and platform and path):
        raise argparse.ArgumentTypeError("要写成 平台=路径")
    return platform, path


def fixed_paths(platform, injected):
    if not injected:
        return FIXED_PATHS.get(platform, ())
    return tuple(path for key, path in injected if key == platform)


def find_host(platform, injected):
    """PATH 里的 zebar 优先，再按平台顺序看固定路径；都没有返回 None。"""
    on_path = shutil.which("zebar")
    if on_path:
        return on_path
    for candidate in fixed_paths(platform, injected):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--平台", default=sys.platform,
                        help="按哪个平台找固定路径，默认本机（测试注入用）")
    parser.add_argument("--固定路径", action="append", default=[], type=parse_fixed_path,
                        metavar="平台=路径", help="替换固定路径表，可重复（测试注入用）")
    args = parser.parse_args()
    host = find_host(args.平台, args.固定路径)
    if host is None:
        say(NOT_FOUND)
        return 1
    return subprocess.run([host, *COMMAND]).returncode


if __name__ == "__main__":
    sys.exit(main())
