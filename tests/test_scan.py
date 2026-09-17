import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1] / "widget"
EMPTY = {"格式版本": 2, "生成时间": "2026-09-16T12:00:00+08:00", "模块": [], "前方": []}


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
        self.assertEqual([row["目录名"] for row in data["行"]], ["丙", "乙", "甲"])
        self.assertEqual(data["读不出"], [])
        self.assertEqual(data["根目录"], [str(self.root)])
        self.assertIn("扫描时间", data)
        self.assertIn("设置文件", data)

    def test_aggregates_engine_fields_in_graph_order(self):
        view = {
            **EMPTY,
            "模块": [
                {"标题": "已结束", "状态": "已完成", "节点": [
                    {"标题": "甲", "状态": "已确认", "高亮": "已清"}]},
                {"标题": "当前", "状态": "进行中", "节点": [
                    {"标题": "乙", "状态": "已生成", "高亮": "未清"},
                    {"标题": "丙", "状态": "未生成", "高亮": "无文书"}]},
                {"标题": "稍后", "状态": "进行中", "节点": [
                    {"标题": "丁", "状态": "不适用", "高亮": "已清"}]},
            ],
            "前方": [{"标题": "当前", "节点": [
                {"标题": "丙", "时限": "雨季之前（合成示例）"}, {"标题": "戊"}]},
                {"标题": "稍后", "节点": [{"标题": "己"}]}],
        }
        path = self.case("甲", view)
        row = self.scan("--根", self.root)["行"][0]
        self.assertEqual(row["路径"], str(path))
        self.assertEqual(row["生成时间"], EMPTY["生成时间"])
        self.assertEqual(row["当前模块"], "当前")
        self.assertEqual(row["下一个"], "丙")
        self.assertEqual(row["待看"], ["乙"])
        self.assertEqual(row["进度"], {"总数": 4, "未生成": 1, "已生成": 1, "已确认": 1, "不适用": 1})
        self.assertEqual(row["前方"], [
            {"模块": "当前", "节点": "丙", "时限": "雨季之前（合成示例）"},
            {"模块": "当前", "节点": "戊"}, {"模块": "稍后", "节点": "己"}])

    def test_settings_roots_merge_and_explicit_roots_bypass_settings(self):
        one = self.root / "one"
        two = self.root / "two"
        self.case("甲", root=one)
        self.case("乙", root=two)
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"根目录": [str(one), str(two)]}), encoding="utf-8")
        data = self.scan("--设置", settings)
        self.assertEqual([row["目录名"] for row in data["行"]], ["乙", "甲"])
        self.assertEqual(data["设置文件"], str(settings))
        settings.write_text("invalid", encoding="utf-8")
        data = self.scan("--设置", settings, "--根", one, "--根", two)
        self.assertEqual([row["目录名"] for row in data["行"]], ["乙", "甲"])
        self.case("丙", root=two)
        self.assertEqual([row["目录名"] for row in self.scan("--根", one, "--根", two)["行"]],
                         ["丙", "乙", "甲"])

    def test_empty_and_not_applicable_graphs(self):
        self.case("甲")
        self.case("乙", {**EMPTY, "模块": [{"标题": "结束", "状态": "不适用", "节点": [
            {"标题": "甲", "状态": "不适用", "高亮": "无文书"},
            {"标题": "乙", "状态": "不适用", "高亮": "已清"}]}]})
        done, empty = self.scan("--根", self.root)["行"]
        for row in (done, empty):
            self.assertIsNone(row["当前模块"])
            self.assertIsNone(row["下一个"])
            self.assertEqual(row["前方"], [])
            self.assertEqual(row["待看"], [])
        self.assertEqual(empty["进度"], {"总数": 0, "未生成": 0, "已生成": 0, "已确认": 0, "不适用": 0})
        self.assertEqual(done["进度"], {"总数": 2, "未生成": 0, "已生成": 0, "已确认": 0, "不适用": 2})

    def test_ahead_keeps_only_first_five_across_modules(self):
        self.case("甲", {**EMPTY, "前方": [
            {"标题": "甲模块", "节点": [{"标题": "甲"}, {"标题": "乙"}, {"标题": "丙"}]},
            {"标题": "乙模块", "节点": [{"标题": "丁"}, {"标题": "戊"}, {"标题": "己"}]}]})
        row = self.scan("--根", self.root)["行"][0]
        self.assertEqual(row["下一个"], "甲")
        self.assertEqual(row["前方"], [
            {"模块": "甲模块", "节点": "甲"}, {"模块": "甲模块", "节点": "乙"},
            {"模块": "甲模块", "节点": "丙"}, {"模块": "乙模块", "节点": "丁"},
            {"模块": "乙模块", "节点": "戊"}])

    def test_output_never_contains_entries(self):
        self.case("甲", {**EMPTY, "条目": [{"动作": "确认"}], "模块": [
            {"标题": "甲模块", "状态": "进行中", "条目": [1], "节点": [
                {"标题": "甲", "状态": "已生成", "高亮": "未清", "条目": [{"动作": "生成"}]}]}],
            "前方": [{"标题": "乙模块", "条目": [1], "节点": [{"标题": "乙", "条目": [1]}]}]})
        self.assertNotIn('"条目"', json.dumps(self.scan("--根", self.root), ensure_ascii=False))

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

    def test_counts_are_ready_for_rendering(self):
        self.case("甲", {**EMPTY, "模块": [{"标题": "甲模块", "状态": "进行中", "节点": [
            {"标题": "甲", "状态": "已生成", "高亮": "未清"},
            {"标题": "乙", "状态": "已生成", "高亮": "未清"}]}]})
        self.case("乙")
        data = self.scan("--根", self.root)
        self.assertEqual(data["案件数"], 2)
        self.assertEqual([row["待看数"] for row in data["行"]], [0, 2])

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

    def test_nested_objects_in_display_fields_cannot_leak_entries(self):
        self.case("甲", {**EMPTY, "生成时间": {"条目": [1]}})
        data = self.scan("--根", self.root)
        self.assertEqual(data["行"], [])
        self.assertEqual(len(data["读不出"]), 1)
        self.assertNotIn('"条目"', json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
