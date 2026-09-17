#!/usr/bin/env python3
"""原型期的排障通道：只听 127.0.0.1 的一个小服务，收卡片页面 POST 过来的诊断。

卡片在宿主里跑的时候，控制台看不见、stdout 也看不见。这根探针是唯一能问出
「页面到底卡在哪一步」的办法。答完题这个文件与页面里那段探针一起删。

跑法：python 原型/探针.py    收到什么打什么，Ctrl-C 停。
"""
import datetime
import http.server
import json

端口 = 8787


class 处理(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        长度 = int(self.headers.get("Content-Length") or 0)
        原文 = self.rfile.read(长度).decode("utf-8", "replace")
        刻 = datetime.datetime.now().strftime("%H:%M:%S")
        try:
            print("{} {}".format(刻, json.dumps(json.loads(原文), ensure_ascii=False)), flush=True)
        except ValueError:
            print("{} {}".format(刻, 原文), flush=True)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_GET(self):
        刻 = datetime.datetime.now().strftime("%H:%M:%S")
        print("{} GET {}".format(刻, self.path), flush=True)
        self.send_response(200)
        self.send_header("Content-Type", "image/gif")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        # 一个 1x1 的透明 gif，纯粹为了让 <img> 有东西可收。
        self.wfile.write(bytes.fromhex(
            "47494638396101000100800000000000ffffff21f90401000000002c00000000"
            "010001000002024401003b"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("探针听在 http://127.0.0.1:{}/".format(端口), flush=True)
    http.server.HTTPServer(("127.0.0.1", 端口), 处理).serve_forever()
