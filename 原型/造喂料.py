#!/usr/bin/env python3
"""造一个合成的案件根目录，给原型喂料。

跑法（在这个仓库的根目录下）：
    python 原型/造喂料.py

它做三件事：
1. 调 loo0ng-skills 的 scripts/skill-eval.py --materialize 现生几个合成工作区，
   拷进一个临时的「案件根目录」里，一个种子一个案件。
2. 用 卡片/scan.py 扫那个根，把结果写成 卡片/stub.json，供浏览器模式（没装宿主
   时直接开 index.html）读。
3. 往 ~/.loo0ng/卡片设置.json 写下那个根目录，供宿主模式读。

这里没有任何真实案件：工作区全是种子回放出来的合成件，当事人一律写甲乙丙。
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

默认种子 = ["在办中", "重出", "空图"]
默认仓库 = pathlib.Path(r"D:\Claude\Programs\loo0ng-skills")
默认根 = pathlib.Path(tempfile.gettempdir()) / "loo0ng-原型根"
设置文件 = pathlib.Path.home() / ".loo0ng" / "卡片设置.json"
这里 = pathlib.Path(__file__).resolve().parent.parent


def 现生(仓库, 种子):
    出 = subprocess.run(
        [sys.executable, "scripts/skill-eval.py", "--materialize", 种子],
        cwd=str(仓库), capture_output=True, text=True, encoding="utf-8",
    )
    if 出.returncode != 0:
        raise SystemExit("种子 {} 回放失败：\n{}".format(种子, 出.stderr[-2000:]))
    return pathlib.Path(出.stdout.strip().splitlines()[-1])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--仓库", default=str(默认仓库))
    p.add_argument("--根", default=str(默认根))
    p.add_argument("--种子", action="append", default=[])
    p.add_argument("--不写设置", action="store_true")
    args = p.parse_args()

    仓库 = pathlib.Path(args.仓库)
    根 = pathlib.Path(args.根)
    种子 = args.种子 or 默认种子

    if 根.exists():
        shutil.rmtree(根)
    根.mkdir(parents=True)

    for 名 in 种子:
        print("回放种子 {} ...".format(名), flush=True)
        源 = 现生(仓库, 名)
        shutil.copytree(源, 根 / 名)
        shutil.rmtree(源, ignore_errors=True)
        print("  -> {}".format(根 / 名))

    扫描 = subprocess.run(
        [sys.executable, str(这里 / "卡片" / "scan.py"), "--根", str(根)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if 扫描.returncode != 0:
        raise SystemExit("扫描失败：\n{}".format(扫描.stderr[-2000:]))
    结果 = json.loads(扫描.stdout)
    (这里 / "卡片" / "stub.json").write_text(
        json.dumps(结果, ensure_ascii=False), encoding="utf-8"
    )
    print("\n扫出 {} 个案件：{}".format(
        len(结果["案件"]), "、".join(c["目录名"] for c in 结果["案件"])))
    print("已写 卡片/stub.json（浏览器模式读它）")

    if not args.不写设置:
        设置文件.parent.mkdir(parents=True, exist_ok=True)
        设置文件.write_text(
            json.dumps({"根目录": [str(根)]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("已写 {}（宿主模式读它）".format(设置文件))


if __name__ == "__main__":
    main()
