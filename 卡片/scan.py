#!/usr/bin/env python3
"""扫根目录，把每个案件的 图视图.json 读出来，整个结果一次打到 stdout。

用法：
  python 扫描.py                      读默认设置文件
  python 扫描.py --设置 <文件>         读指定设置文件
  python 扫描.py --根 <目录> [--根 ...] 直接给根目录，不读设置

设置文件默认在 ~/.loo0ng/卡片设置.json，形状：
  {"根目录": ["D:\\Claude\\Data\\Cases", "..."]}

判定一个目录是不是案件：它底下有没有 图视图.json。只扫一层。

边界（ADR-0029）：只读 图视图.json 这一个文件。工作区里的 材料/、文书/、
待归档/、参考/ 一律不读、不列、不出现在输出里。这个脚本里只该出现一个工作区文件名。
"""
import argparse
import datetime
import json
import os
import pathlib
import sys
import tempfile
import time

视图文件名 = "图视图.json"
默认设置 = pathlib.Path.home() / ".loo0ng" / "卡片设置.json"


def 读设置(路径):
    if not 路径.is_file():
        return []
    try:
        设置 = json.loads(路径.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    根 = 设置.get("根目录") or []
    return [str(x) for x in 根 if str(x).strip()]


def 扫一个根(根):
    结果 = []
    根路径 = pathlib.Path(根).expanduser()
    if not 根路径.is_dir():
        return [{"路径": str(根路径), "目录名": 根路径.name, "错误": "根目录不存在"}]
    for 子 in sorted(根路径.iterdir(), key=lambda p: p.name):
        if not 子.is_dir():
            continue
        视图 = 子 / 视图文件名
        if not 视图.is_file():
            continue
        条 = {"路径": str(子), "目录名": 子.name}
        try:
            条["视图"] = json.loads(视图.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            条["错误"] = "{} 读不出：{}".format(视图文件名, e.__class__.__name__)
        结果.append(条)
    return 结果


def 记一行(话):
    """原型期的排障口：日志文件已经存在才追加，不存在就什么都不做。

    卡片在宿主里跑的时候看不见 stdout，这是确证「宿主真的起了这个脚本」的唯一办法。
    开：手工建一个空的 %TEMP%/loo0ng-扫描.log。关：删掉它。实现时这个函数整块去掉。
    """
    日志 = pathlib.Path(tempfile.gettempdir()) / "loo0ng-扫描.log"
    if not 日志.is_file():
        return
    刻 = datetime.datetime.now().strftime("%H:%M:%S")
    with 日志.open("a", encoding="utf-8") as f:
        f.write("{} {}\n".format(刻, 话))


def main(argv=None):
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--设置", dest="设置", default=None)
    p.add_argument("--根", dest="根", action="append", default=[])
    p.add_argument("--记", dest="记", default=None, help="只往日志写一行就退出，页面报错时用")
    p.add_argument("--标", dest="标", default="?", help="哪张卡问的，只进日志")
    args = p.parse_args(argv)

    if args.记 is not None:
        记一行("[{}] 页面报错：{}".format(args.标, args.记))
        return 0

    根 = list(args.根)
    设置路径 = pathlib.Path(args.设置).expanduser() if args.设置 else 默认设置
    if not 根:
        根 = 读设置(设置路径)

    起 = time.time()
    案件 = []
    for 一个 in 根:
        案件.extend(扫一个根(一个))

    出 = {
        "扫描时间": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "设置文件": str(设置路径),
        "根目录": 根,
        "案件": 案件,
    }
    首个生成时间 = next((c["视图"].get("生成时间") for c in 案件 if "视图" in c), "无")
    记一行("[{}] 扫了 {} 个根，{} 个案件：{}，头一个的生成时间 {}，用时 {} ms".format(
        args.标, len(根), len(案件), "、".join(c["目录名"] for c in 案件) or "无",
        首个生成时间, int((time.time() - 起) * 1000)))
    sys.stdout.write(json.dumps(出, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    if os.name == "nt":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    sys.exit(main())
