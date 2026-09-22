#!/usr/bin/env python3
"""只读一层子目录中的 图视图.json，向 stdout 输出桌面卡片数据。"""
import argparse
from datetime import datetime
import json
import locale
from pathlib import Path
import sys

STATES = ("未生成", "已生成", "已确认", "不适用")
# 引擎把拍板时刻写在这两个字段里，按节点当前的状态各取一个；
# 未生成与不适用的节点不显示时间，所以两档都不取。
MOMENT_OF = {"已生成": "最近生成", "已确认": "最近确认"}


def display_text(value):
    if not isinstance(value, str):
        raise ValueError("机器可读视图的显示字段必须是文本")
    return value


def format_moment(stamp, this_year):
    """把引擎写的 ISO 时刻预先格式化成「9月21日」，跨年才带年；页面照印，不算日期。"""
    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        raise ValueError("机器可读视图里的时刻不是 ISO 8601 文本")
    if moment.year == this_year:
        return "{}月{}日".format(moment.month, moment.day)
    return "{}年{}月{}日".format(moment.year, moment.month, moment.day)


def node_row(node, this_year):
    row = {"标题": display_text(node["标题"]), "状态": display_text(node["状态"]),
           "高亮": display_text(node["高亮"])}
    if "时限" in node:
        row["时限"] = display_text(node["时限"])
    field = MOMENT_OF.get(row["状态"])
    if field:
        row["时间"] = display_text(node[field]["时间"])
        row["时间显示"] = format_moment(row["时间"], this_year)
    return row


def first_in_state(modules, state):
    """图序第一个处在这个状态的节点，连它所在的模块一起给出来。"""
    return next(((module, node) for module in modules for node in module["节点"]
                 if node["状态"] == state), (None, None))


def progress_of(nodes):
    progress = {state: sum(node["状态"] == state for node in nodes) for state in STATES}
    progress["总数"] = len(nodes)
    return progress


def aggregate(path, view, this_year):
    version = view["格式版本"]
    if type(version) is not int or version != 2:
        # 1 是工作台早先写过的那一版：图没有升级路径，而这一案多半已经办了一半，
        # 对它打起手会把归好的东西挪走，所以这一档只说「不接它、照旧办法办」。
        # 别的不认识的版本仍旧照实报，该做什么这张卡片答不了。
        if type(version) is int and version == 1:
            raise ValueError("老格式（格式版本 1）：这一案工作台不接，照原来的办法办，别对它打起手")
        raise ValueError("机器可读视图的格式版本是 {}，这张卡片只认 2".format(version))
    modules = []
    for module in view["模块"]:
        rows = [node_row(node, this_year) for node in module["节点"]]
        modules.append({"标题": display_text(module["标题"]), "状态": display_text(module["状态"]),
                        "进度": progress_of(rows), "节点": rows})
    nodes = [node for module in modules for node in module["节点"]]
    # 引擎的前方装的正是还没生成的那些节点，按图序。下一个与当前节点的后备都指它的第一个，
    # 所以两个都在图序里取第一个未生成的节点：同一个来源，不会各说各话；
    # 从模块里取还多带状态与高亮两列，圆圈照它画。
    next_module, next_node = first_in_state(modules, "未生成")
    # 当前模块是当前节点所在的那个模块，不是图序第一个进行中的模块：后者可能是靠前的一个
    # 空模块或律师跳过去的一块，第三层「当前模块 › 当前节点」就会印出名不副实的一行（#21）。
    current_module, current = first_in_state(modules, "已生成")
    if current is None:
        current_module, current = next_module, next_node
    return {
        "目录名": path.name, "路径": str(path), "生成时间": display_text(view["生成时间"]),
        "当前模块": current_module["标题"] if current_module else None,
        "当前节点": {key: current[key] for key in ("标题", "状态", "高亮")} if current else None,
        "下一个": next_node["标题"] if next_node else None,
        "待看数": sum(node["高亮"] == "未清" for node in nodes),
        "进度": progress_of(nodes), "模块": modules,
    }


def case_order(row):
    if row["待看数"]:
        tier = 0
    elif row["下一个"] is not None:
        tier = 1
    elif row["进度"]["总数"] == 0:
        tier = 2
    else:
        tier = 3
    return tier, locale.strxfrm(row["目录名"]), row["目录名"], row["路径"]


def scan(roots, settings):
    scanned = datetime.now().astimezone()
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
                rows.append(aggregate(path, view, scanned.year))
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
    rows.sort(key=case_order)
    return {"扫描时间": scanned.isoformat(timespec="seconds"),
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
    try:
        locale.setlocale(locale.LC_COLLATE, "zh_CN.UTF-8")
    except locale.Error:
        parser.error("系统缺少 zh_CN.UTF-8 中文排序支持，无法按中文序扫描")
    settings = args.设置.expanduser()
    roots, settings_error = (args.根, None) if args.根 else read_settings(settings)
    data = scan(roots, settings)
    data["设置错误"] = settings_error
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
