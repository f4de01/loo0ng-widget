from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "widget"
EMPTY = {"格式版本": 2, "生成时间": "2026-09-16T12:00:00+08:00", "模块": [], "前方": []}
THIS_YEAR = datetime.now().astimezone().year
MADE_AT = "{}-09-21T15:04:05+08:00".format(THIS_YEAR)
CONFIRMED_AT = "{}-09-22T09:00:00+08:00".format(THIS_YEAR)
ANOTHER_YEAR = "2019-01-05T08:00:00+08:00"


def made(title, highlight="未清", at=MADE_AT, **extra):
    """引擎给已生成节点写的那一份最近生成，测试只补它要的几个键。"""
    return {"标题": title, "状态": "已生成", "高亮": highlight,
            "最近生成": dict({"次数": 1, "时间": at, "来源": "agent"}, **extra)}


def confirmed(title, highlight="已清", at=CONFIRMED_AT):
    return {"标题": title, "状态": "已确认", "高亮": highlight,
            "最近确认": {"时间": at, "原话": "确认 " + title}}


def counts(总数=0, 未生成=0, 已生成=0, 已确认=0, 不适用=0):
    return {"总数": 总数, "未生成": 未生成, "已生成": 已生成, "已确认": 已确认, "不适用": 不适用}


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def case(self, name, view=None, root=None):
        path = (root or self.root) / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "图视图.json").write_text(
            json.dumps(EMPTY if view is None else view, ensure_ascii=False), encoding="utf-8")
        return path

    def scan(self, *args):
        result = subprocess.run([sys.executable, str(PACKAGE / "scan.py"), *map(str, args)],
                                capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_discovers_three_cases_skips_ordinary_directories_and_does_not_recurse(self):
        for name in ("甲", "乙", "丙"):
            self.case(name)
        (self.root / "ordinary").mkdir()
        self.case("nested", root=self.root / "ordinary")
        data = self.scan("--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["丙", "甲", "乙"])
        self.assertEqual(data["读不出"], [])
        self.assertEqual(data["根目录"], [str(self.root)])
        self.assertIn("扫描时间", data)
        self.assertIn("设置文件", data)

    def test_aggregates_engine_fields_in_graph_order(self):
        view = {
            **EMPTY,
            "模块": [
                {"标题": "已结束", "状态": "已完成", "节点": [confirmed("甲")]},
                {"标题": "当前", "状态": "进行中", "节点": [
                    made("乙"),
                    {"标题": "丙", "状态": "未生成", "高亮": "无文书",
                     "时限": "雨季之前（合成示例）"}]},
                {"标题": "稍后", "状态": "进行中", "节点": [
                    {"标题": "丁", "状态": "不适用", "高亮": "已清"}]},
            ],
            "前方": [{"标题": "当前", "节点": [{"标题": "丙", "时限": "雨季之前（合成示例）"}]}],
        }
        path = self.case("甲", view)
        row = self.scan("--根", self.root)["行"][0]
        self.assertEqual(row["路径"], str(path))
        self.assertEqual(row["生成时间"], EMPTY["生成时间"])
        self.assertEqual(row["当前模块"], "当前")
        self.assertEqual(row["下一个"], "丙")
        self.assertEqual(row["待看数"], 1)
        self.assertNotIn("待看", row)
        self.assertEqual(row["进度"], counts(总数=4, 未生成=1, 已生成=1, 已确认=1, 不适用=1))
        self.assertEqual(row["当前节点"], {"标题": "乙", "状态": "已生成", "高亮": "未清"})
        self.assertEqual(row["模块"], [
            {"标题": "已结束", "状态": "已完成", "进度": counts(总数=1, 已确认=1),
             "时间": CONFIRMED_AT, "时间显示": "9月22日",
             "节点": [{"标题": "甲", "状态": "已确认", "高亮": "已清",
                     "时间": CONFIRMED_AT, "时间显示": "9月22日"}]},
            {"标题": "当前", "状态": "进行中", "进度": counts(总数=2, 未生成=1, 已生成=1),
             "时间": MADE_AT, "时间显示": "9月21日",
             "节点": [{"标题": "乙", "状态": "已生成", "高亮": "未清",
                     "时间": MADE_AT, "时间显示": "9月21日"},
                    {"标题": "丙", "状态": "未生成", "高亮": "无文书",
                     "时限": "雨季之前（合成示例）"}]},
            {"标题": "稍后", "状态": "进行中", "进度": counts(总数=1, 不适用=1),
             "节点": [{"标题": "丁", "状态": "不适用", "高亮": "已清"}]},
        ])

    def test_each_module_counts_its_own_nodes_and_empty_modules_stay(self):
        self.case("甲", {**EMPTY, "模块": [
            {"标题": "甲模块", "状态": "进行中", "节点": [
                made("甲"), {"标题": "乙", "状态": "未生成", "高亮": "无文书"}]},
            {"标题": "乙模块", "状态": "进行中", "节点": []},
            {"标题": "丙模块", "状态": "已完成", "节点": [confirmed("丙")]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "乙"}]}]})
        row = self.scan("--根", self.root)["行"][0]
        self.assertEqual([module["标题"] for module in row["模块"]], ["甲模块", "乙模块", "丙模块"])
        self.assertEqual([module["进度"] for module in row["模块"]], [
            counts(总数=2, 未生成=1, 已生成=1), counts(), counts(总数=1, 已确认=1)])
        self.assertEqual(row["模块"][1]["节点"], [])
        self.assertEqual(row["进度"], counts(总数=3, 未生成=1, 已生成=1, 已确认=1))

    def test_node_time_follows_state_and_arrives_preformatted(self):
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            dict(confirmed("甲"), 最近生成={"次数": 2, "时间": MADE_AT, "来源": "agent"}),
            made("乙"),
            {"标题": "丙", "状态": "未生成", "高亮": "无文书"},
            {"标题": "丁", "状态": "不适用", "高亮": "已清",
             "最近生成": {"次数": 1, "时间": MADE_AT, "来源": "agent"}}]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "丙"}]}]})
        甲, 乙, 丙, 丁 = self.scan("--根", self.root)["行"][0]["模块"][0]["节点"]
        self.assertEqual((甲["时间"], 甲["时间显示"]), (CONFIRMED_AT, "9月22日"))
        self.assertEqual((乙["时间"], 乙["时间显示"]), (MADE_AT, "9月21日"))
        for node in (丙, 丁):
            with self.subTest(节点=node["标题"]):
                self.assertNotIn("时间", node)
                self.assertNotIn("时间显示", node)

    def test_time_display_carries_the_year_only_across_years(self):
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            made("甲", at=ANOTHER_YEAR)]}]})
        node = self.scan("--根", self.root)["行"][0]["模块"][0]["节点"][0]
        self.assertEqual((node["时间"], node["时间显示"]), (ANOTHER_YEAR, "2019年1月5日"))

    def test_module_time_is_the_latest_moment_among_its_nodes(self):
        """矩阵视横轴标签的悬浮（#24）：每个模块挂它最近一次动过的时刻，确认与生成都算；取最晚的在这里做，页面照印。"""
        self.case("甲", {**EMPTY, "模块": [
            {"标题": "甲模块", "状态": "进行中", "节点": [
                confirmed("甲"), made("乙", at="{}-09-23T08:00:00+08:00".format(THIS_YEAR)),
                made("丙", at=ANOTHER_YEAR)]},
            {"标题": "乙模块", "状态": "进行中", "节点": [
                {"标题": "丁", "状态": "未生成", "高亮": "无文书"},
                {"标题": "戊", "状态": "不适用", "高亮": "已清"}]},
            {"标题": "丙模块", "状态": "进行中", "节点": []},
            {"标题": "丁模块", "状态": "进行中", "节点": [made("己", at=ANOTHER_YEAR)]}],
            "前方": [{"标题": "乙模块", "节点": [{"标题": "丁"}]}]})
        甲, 乙, 丙, 丁 = self.scan("--根", self.root)["行"][0]["模块"]
        latest = "{}-09-23T08:00:00+08:00".format(THIS_YEAR)
        self.assertEqual((甲["时间"], 甲["时间显示"]), (latest, "9月23日"))
        # 跨年：显示串带年。
        self.assertEqual((丁["时间"], 丁["时间显示"]), (ANOTHER_YEAR, "2019年1月5日"))
        for module in (乙, 丙):
            with self.subTest(模块=module["标题"]):
                for key in ("时间", "时间显示"):
                    self.assertNotIn(key, module)

    def test_current_module_is_the_module_the_current_node_lives_in(self):
        """第三层印的是「当前模块 › 当前节点」，模块必须是那个节点自己的。"""
        self.case("甲", {**EMPTY, "模块": [
            {"标题": "甲模块", "状态": "进行中", "节点": [
                {"标题": "甲", "状态": "未生成", "高亮": "无文书"}]},
            {"标题": "乙模块", "状态": "进行中", "节点": [made("乙")]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "甲"}]}]})
        self.case("乙", {**EMPTY, "模块": [
            {"标题": "空模块", "状态": "进行中", "节点": []},
            {"标题": "甲模块", "状态": "进行中", "节点": [made("甲")]}]})
        rows = {row["目录名"]: row for row in self.scan("--根", self.root)["行"]}
        self.assertEqual(rows["甲"]["当前模块"], "乙模块")
        self.assertEqual(rows["甲"]["当前节点"]["标题"], "乙")
        self.assertEqual(rows["甲"]["下一个"], "甲")
        self.assertEqual(rows["乙"]["当前模块"], "甲模块")
        self.assertEqual(rows["乙"]["当前节点"]["标题"], "甲")

    def test_current_module_follows_the_next_node_when_nothing_is_generated(self):
        self.case("甲", {**EMPTY, "模块": [
            {"标题": "空模块", "状态": "进行中", "节点": []},
            {"标题": "已完模块", "状态": "已完成", "节点": [confirmed("甲")]},
            {"标题": "乙模块", "状态": "进行中", "节点": [
                {"标题": "乙", "状态": "未生成", "高亮": "无文书"}]}],
            "前方": [{"标题": "乙模块", "节点": [{"标题": "乙"}]}]})
        row = self.scan("--根", self.root)["行"][0]
        self.assertEqual(row["当前模块"], "乙模块")
        self.assertEqual(row["当前节点"], {"标题": "乙", "状态": "未生成", "高亮": "无文书"})
        self.assertEqual(row["下一个"], "乙")

    def test_a_leftover_empty_module_is_not_a_current_module(self):
        """整案办完、图里只剩一个空模块时，第三层没有东西可印，两个字段一起为空。"""
        self.case("甲", {**EMPTY, "模块": [
            {"标题": "已完模块", "状态": "已完成", "节点": [confirmed("甲")]},
            {"标题": "空模块", "状态": "进行中", "节点": []}]})
        row = self.scan("--根", self.root)["行"][0]
        self.assertIsNone(row["当前节点"])
        self.assertIsNone(row["当前模块"])
        self.assertIsNone(row["下一个"])

    def test_deadline_rides_along_only_when_the_engine_wrote_one(self):
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            {"标题": "甲", "状态": "未生成", "高亮": "无文书", "时限": "雨季之前（合成示例）"},
            {"标题": "乙", "状态": "未生成", "高亮": "无文书"}]}],
            "前方": [{"标题": "甲模块", "节点": [
                {"标题": "甲", "时限": "雨季之前（合成示例）"}, {"标题": "乙"}]}]})
        甲, 乙 = self.scan("--根", self.root)["行"][0]["模块"][0]["节点"]
        self.assertEqual(甲["时限"], "雨季之前（合成示例）")
        self.assertNotIn("时限", 乙)

    def test_current_node_takes_the_first_generated_then_the_next_one(self):
        generated = {**EMPTY, "模块": [
            {"标题": "甲模块", "状态": "进行中", "节点": [
                {"标题": "甲", "状态": "未生成", "高亮": "无文书"}, made("乙")]},
            {"标题": "乙模块", "状态": "进行中", "节点": [made("丙", highlight="已清")]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "甲"}]}]}
        ahead_only = {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            confirmed("甲"), {"标题": "乙", "状态": "未生成", "高亮": "无文书"},
            {"标题": "丙", "状态": "未生成", "高亮": "无文书"}]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "乙"}, {"标题": "丙"}]}]}
        finished = {**EMPTY, "模块": [{"标题": "甲模块", "状态": "已完成", "节点": [confirmed("甲")]}]}
        self.case("甲", generated)
        self.case("乙", ahead_only)
        self.case("丙", finished)
        rows = {row["目录名"]: row for row in self.scan("--根", self.root)["行"]}
        self.assertEqual(rows["甲"]["当前节点"], {"标题": "乙", "状态": "已生成", "高亮": "未清"})
        self.assertEqual(rows["乙"]["当前节点"], {"标题": "乙", "状态": "未生成", "高亮": "无文书"})
        self.assertEqual(rows["乙"]["下一个"], "乙")
        self.assertIsNone(rows["丙"]["当前节点"])
        self.assertIsNone(rows["丙"]["下一个"])

    def test_settings_roots_merge_and_explicit_roots_bypass_settings(self):
        one = self.root / "one"
        two = self.root / "two"
        self.case("甲", root=one)
        self.case("乙", root=two)
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"根目录": [str(one), str(two)]}), encoding="utf-8")
        data = self.scan("--设置", settings)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲", "乙"])
        self.assertEqual(data["设置文件"], str(settings))
        settings.write_text("invalid", encoding="utf-8")
        data = self.scan("--设置", settings, "--根", one, "--根", two)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲", "乙"])
        self.case("丙", root=two)
        self.assertEqual([row["目录名"] for row in self.scan("--根", one, "--根", two)["行"]],
                         ["丙", "甲", "乙"])

    def test_empty_and_not_applicable_graphs(self):
        self.case("甲")
        self.case("乙", {**EMPTY, "模块": [{"标题": "结束", "状态": "不适用", "节点": [
            {"标题": "甲", "状态": "不适用", "高亮": "无文书"},
            {"标题": "乙", "状态": "不适用", "高亮": "已清"}]}]})
        empty, done = self.scan("--根", self.root)["行"]
        for row in (done, empty):
            self.assertIsNone(row["当前模块"])
            self.assertIsNone(row["下一个"])
            self.assertIsNone(row["当前节点"])
            self.assertEqual(row["待看数"], 0)
        self.assertEqual(empty["进度"], counts())
        self.assertEqual(empty["模块"], [])
        self.assertEqual(done["进度"], counts(总数=2, 不适用=2))
        self.assertEqual(done["模块"], [
            {"标题": "结束", "状态": "不适用", "进度": counts(总数=2, 不适用=2), "节点": [
                {"标题": "甲", "状态": "不适用", "高亮": "无文书"},
                {"标题": "乙", "状态": "不适用", "高亮": "已清"}]}])

    def test_pending_ahead_empty_and_finished_cases_sort_in_four_tiers(self):
        self.case("乙", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            made("甲"), {"标题": "乙", "状态": "未生成", "高亮": "无文书"}]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "乙"}]}]})
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            {"标题": "甲", "状态": "未生成", "高亮": "无文书"}]}],
            "前方": [{"标题": "甲模块", "节点": [{"标题": "甲"}]}]})
        self.case("丙")
        self.case("丁", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "已完成",
                                         "节点": [confirmed("甲")]}]})
        data = self.scan("--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["乙", "甲", "丙", "丁"])

    def test_each_tier_uses_chinese_name_order_independent_of_generation_time(self):
        views = [
            {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [made("甲")]}]},
            {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
                {"标题": "甲", "状态": "未生成", "高亮": "无文书"}]}],
                "前方": [{"标题": "甲模块", "节点": [{"标题": "甲"}]}]},
            EMPTY,
            {**EMPTY, "模块": [{"标题": "甲模块", "状态": "已完成", "节点": [confirmed("甲")]}]},
        ]
        for view in views:
            with self.subTest(view=view):
                for name in ("乙", "甲", "丙"):
                    self.case(name, view)
                first = self.scan("--根", self.root)["行"]
                self.assertEqual([row["目录名"] for row in first], ["丙", "甲", "乙"])
                self.case("甲", {**view, "生成时间": "2026-09-17T12:00:00+08:00"})
                second = self.scan("--根", self.root)["行"]
                self.assertEqual([row["路径"] for row in second], [row["路径"] for row in first])

    def noisy(self):
        """一份什么都带着的合成视图：条目、生成出来的那些路径、整条前方。"""
        self.case("甲", {**EMPTY, "条目": [{"动作": "确认"}], "模块": [
            {"标题": "甲模块", "状态": "进行中", "条目": [1], "节点": [
                dict(made("甲", 文书="文书/甲模块/甲/甲.docx",
                          审查报告="文书/甲模块/甲/甲-审查报告.md"), 条目=[{"动作": "生成"}]),
                {"标题": "乙", "状态": "未生成", "高亮": "无文书", "条目": []}]}],
            "前方": [{"标题": "甲模块", "条目": [1], "节点": [{"标题": "乙", "条目": [1]}]}]})
        return json.dumps(self.scan("--根", self.root), ensure_ascii=False)

    def test_output_never_contains_entries(self):
        self.assertNotIn('"条目"', self.noisy())

    def test_output_never_contains_documents(self):
        output = self.noisy()
        self.assertNotIn('"文书"', output)
        self.assertNotIn('"审查报告"', output)
        # 「无文书」是引擎的高亮值，照带；路径一个都不许漏出来。
        self.assertNotIn(".docx", output)
        self.assertNotIn("-审查报告.md", output)

    def test_output_never_contains_an_ahead_list(self):
        self.assertNotIn('"前方"', self.noisy())

    def test_source_mentions_only_the_allowed_workspace_filename(self):
        for path in PACKAGE.rglob("*"):
            if path.suffix in (".py", ".js", ".html", ".css", ".json"):
                with self.subTest(path=path):
                    source = path.read_text(encoding="utf-8").replace("图视图.json", "")
                    for forbidden in ("材料", "文书", "待归档", "参考", "图.json", "图视图.md"):
                        self.assertNotIn(forbidden, source)

    def test_unknown_version_and_broken_json_are_isolated(self):
        self.case("甲")
        self.case("乙", {**EMPTY, "格式版本": 3})
        broken = self.case("丙")
        (broken / "图视图.json").write_text("{", encoding="utf-8")
        data = self.scan("--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲"])
        errors = {row["目录名"]: row["原因"] for row in data["读不出"]}
        self.assertIn("3", errors["乙"])
        self.assertIn("只认 2", errors["乙"])
        self.assertIn("JSON", errors["丙"])

    def test_format_version_one_says_what_the_lawyer_can_do(self):
        """老格式那一档要给出可照做的话，而且不能教他去打起手：那会把已经归好的东西挪走。"""
        self.case("甲")
        self.case("乙", {**EMPTY, "格式版本": 1})
        data = self.scan("--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲"])
        reason = {row["目录名"]: row["原因"] for row in data["读不出"]}["乙"]
        self.assertIn("1", reason)
        self.assertIn("别对它打起手", reason)
        self.assertNotIn("只认 2", reason)

    def test_counts_are_ready_for_rendering(self):
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            made("甲"), made("乙")]}]})
        self.case("乙")
        data = self.scan("--根", self.root)
        self.assertEqual(data["案件数"], 2)
        self.assertEqual([row["待看数"] for row in data["行"]], [2, 0])
        for row in data["行"]:
            with self.subTest(目录名=row["目录名"]):
                self.assertNotIn("待看", row)

    def test_missing_root_does_not_hide_other_roots(self):
        self.case("甲")
        missing = self.root / "missing"
        data = self.scan("--根", missing, "--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲"])
        self.assertEqual(data["读不出"], [{"目录名": "missing", "路径": str(missing),
                                         "原因": "根目录不存在"}])

    def test_unreadable_view_does_not_hide_other_cases(self):
        self.case("甲")
        view = self.case("乙") / "图视图.json"
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                          wintypes.HANDLE]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.CreateFileW(str(view), 0x80000000, 0, None, 3, 0, None)
            self.assertNotEqual(handle, wintypes.HANDLE(-1).value)
            self.addCleanup(kernel.CloseHandle, handle)
        else:
            if os.geteuid() == 0:
                self.skipTest("root bypasses file permissions")
            view.chmod(0)
            self.addCleanup(view.chmod, 0o600)
        data = self.scan("--根", self.root)
        self.assertEqual([row["目录名"] for row in data["行"]], ["甲"])
        self.assertEqual(data["读不出"][0]["目录名"], "乙")
        self.assertIn("无法读取", data["读不出"][0]["原因"])

    def test_default_settings_are_read_from_home(self):
        settings = self.root / ".loo0ng" / "卡片设置.json"
        settings.parent.mkdir()
        cases = self.root / "cases"
        self.case("甲", root=cases)
        settings.write_text(json.dumps({"根目录": [str(cases)]}), encoding="utf-8")
        env = {**os.environ, "HOME": str(self.root), "USERPROFILE": str(self.root)}
        result = subprocess.run([sys.executable, str(PACKAGE / "scan.py")],
                                env=env, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["设置文件"], str(settings))
        self.assertEqual(data["案件数"], 1)

    def test_missing_settings_give_creation_instructions(self):
        settings = self.root / "settings.json"
        data = self.scan("--设置", settings)
        self.assertEqual(data["设置错误"]["类别"], "文件不存在")
        self.assertIn(str(settings), data["设置错误"]["原因"])
        self.assertIn("创建", data["设置错误"]["原因"])
        self.assertIn('{"根目录": ["绝对路径"]}', data["设置错误"]["原因"])
        self.assertEqual(data["行"], [])
        self.assertEqual(data["读不出"], [])
        self.assertEqual(data["案件数"], 0)

    def test_invalid_settings_give_distinct_repair_instructions(self):
        settings = self.root / "settings.json"
        for content, category in (("{", "不是 JSON"), ('{}', "缺少根目录"),
                                  ('{"根目录": []}', "根目录为空"),
                                  ('{"根目录": "wrong"}', "根目录格式错误"),
                                  ('{"根目录": [null]}', "根目录格式错误")):
            with self.subTest(category=category, content=content):
                settings.write_text(content, encoding="utf-8")
                data = self.scan("--设置", settings)
                self.assertEqual(data["设置错误"]["类别"], category)
                self.assertIn(str(settings), data["设置错误"]["原因"])
                self.assertIn('{"根目录": ["绝对路径"]}', data["设置错误"]["原因"])
                self.assertEqual(data["行"], [])
                self.assertEqual(data["读不出"], [])

    def test_nested_objects_in_display_fields_cannot_leak_entries(self):
        self.case("甲", {**EMPTY, "生成时间": {"条目": [1]}})
        data = self.scan("--根", self.root)
        self.assertEqual(data["行"], [])
        self.assertEqual(len(data["读不出"]), 1)
        self.assertNotIn('"条目"', json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
