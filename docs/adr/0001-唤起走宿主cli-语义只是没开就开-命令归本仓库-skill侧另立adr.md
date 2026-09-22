---
status: accepted
date: 2026-09-22
---

# 唤起走宿主 CLI，语义只是「没开就开」，命令归本仓库，skill 侧的接入另立 ADR

律师实机反馈：托盘里「右键 → Widget packs → loo0ng → 案件卡片 → Run」太长、记不住，要一键打开或由 agent 打开。核实 Zebar 3.3.1 源码：`zebar start-widget-preset --pack loo0ng --widget-name 案件卡片 --preset 默认` 能在宿主没开时连宿主一起拉起；预设已开（含最小化）时**无事发生**，不聚焦、不还原、不新开窗；没有任何给组件传参数的口子。据此裁定：

- 「唤起」只承诺「没开就开」。还原交给任务栏 / 程序坞，「打开并定位到某一案」整条放弃，卡片回到律师上次停的页面与案子（见 ADR-0002）。
- 包里放一个 ASCII 名的启动脚本（Python 3.9 标准库），按 PATH 里的 `zebar`、mac 的 `/Applications/Zebar.app/Contents/MacOS/zebar`、Windows 的 `C:\Program Files\glzr.io\Zebar\zebar.exe` 顺序找宿主，找到即调上面那条命令，找不到就一句话说去哪装。桌面快捷方式与 agent 一句话都指向它。README 先教勾托盘里的「Run on startup」，登录即在；关过了才用这条。
- 本仓库这一轮只交命令与文档。「律师说打开卡片就跑这条命令」要写进 skill 正文，那要反转 ADR-0029「卡片与 agent 之间没有调用关系」那一条，属 loo0ng-skills 自己的裁定，等本轮呈现验完再去那边立 ADR。律师机上 agent 跑在沙箱里，能不能起宿主进程未知，进交付票验。

考虑过：卡片自己用客户端 API 开第二个组件窗当「案件页」，因传不了参数被否；靠本地存储传话是 hack。
