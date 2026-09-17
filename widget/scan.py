#!/usr/bin/env python3
"""只读一层子目录中的 图视图.json，向 stdout 输出桌面卡片数据。"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


def display_text(value):
    if not isinstance(value, str):
        raise ValueError("机器可读视图的显示字段必须是文本")
    return value


def aggregate(path, view):
    if type(view["格式版本"]) is not int or view["格式版本"] != 2:
        raise ValueError("机器可读视图的格式版本是 {}，这张卡片只认 2".format(view["格式版本"]))
    modules = view["模块"]
    nodes = [node for module in modules for node in module["节点"]]
    ahead = view["前方"]
    preview = []
    for module in ahead:
        for node in module["节点"]:
            item = {"模块": display_text(module["标题"]), "节点": display_text(node["标题"])}
            if "时限" in node:
                item["时限"] = display_text(node["时限"])
            preview.append(item)
    progress = {state: sum(node["状态"] == state for node in nodes)
                for state in ("未生成", "已生成", "已确认", "不适用")}
    progress["总数"] = len(nodes)
    pending = [display_text(node["标题"]) for node in nodes if node["高亮"] == "未清"]
    return {
        "目录名": path.name, "路径": str(path), "生成时间": display_text(view["生成时间"]),
        "当前模块": next((display_text(module["标题"]) for module in modules if module["状态"] == "进行中"), None),
        "下一个": display_text(ahead[0]["节点"][0]["标题"]) if ahead and ahead[0]["节点"] else None,
        "待看": pending, "待看数": len(pending),
        "前方": preview[:5], "进度": progress,
    }


def scan(roots, settings):
    rows = []
    errors = []
    for root in roots:
        root_path = Path(root).expanduser().absolute()
        try:
            children = list(root_path.iterdir())
        except OSError as error:
            reason = "根目录不存在" if isinstance(error, FileNotFoundError) else "根目录读不出，请检查路径和读取权限"
            errors.append({"目录名": root_path.name, "路径": str(root_path), "原因": reason})
            continue
        for path in children:
            try:
                if not path.is_dir() or not (path / "图视图.json").is_file():
                    continue
                view = json.loads((path / "图视图.json").read_text(encoding="utf-8"))
                rows.append(aggregate(path, view))
            except (OSError, ValueError, KeyError, TypeError) as error:
                if isinstance(error, json.JSONDecodeError):
                    reason = "机器可读视图不是有效的 JSON"
                elif isinstance(error, UnicodeError):
                    reason = "机器可读视图不是有效的 UTF-8 文本"
                elif isinstance(error, OSError):
                    reason = "机器可读视图无法读取，请检查读取权限或文件是否被占用"
                elif type(error) is ValueError:
                    reason = str(error)
                else:
                    reason = "机器可读视图结构不完整或字段类型不正确"
                errors.append({"目录名": path.name, "路径": str(path), "原因": reason})
    rows.sort(key=lambda row: row["目录名"])
    return {"扫描时间": datetime.now().astimezone().isoformat(timespec="seconds"),
            "设置文件": str(settings), "根目录": roots, "行": rows, "读不出": errors,
            "案件数": len(rows)}


def read_settings(settings):
    try:
        value = json.loads(settings.read_text(encoding="utf-8"))
    except FileNotFoundError:
        category, instruction = "文件不存在", "设置文件不存在，请创建"
    except (json.JSONDecodeError, UnicodeError):
        category, instruction = "不是 JSON", "设置文件不是有效的 UTF-8 JSON，请修改"
    except OSError:
        category, instruction = "文件读不出", "设置文件读不出，请检查读取权限并修改"
    else:
        if not isinstance(value, dict) or "根目录" not in value:
            category, instruction = "缺少根目录", "设置缺少“根目录”键，请修改"
        elif not isinstance(value["根目录"], list) or any(
                not isinstance(root, str) or not root.strip() or "\0" in root
                for root in value["根目录"]):
            category, instruction = "根目录格式错误", "“根目录”须为路径字符串数组，请修改"
        elif not value["根目录"]:
            category, instruction = "根目录为空", "尚未填写案件根目录，请修改"
        else:
            return value["根目录"], None
    return [], {"类别": category, "原因":
                '{} {}，写成 {{"根目录": ["绝对路径"]}}，'
                '把“绝对路径”替换为案件根目录（Windows 路径可用 /）。'.format(instruction, settings)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--设置", type=Path, default=Path.home() / ".loo0ng" / "卡片设置.json")
    parser.add_argument("--根", action="append", default=[])
    args = parser.parse_args()
    settings = args.设置.expanduser()
    roots, settings_error = (args.根, None) if args.根 else read_settings(settings)
    data = scan(roots, settings)
    data["设置错误"] = settings_error
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
