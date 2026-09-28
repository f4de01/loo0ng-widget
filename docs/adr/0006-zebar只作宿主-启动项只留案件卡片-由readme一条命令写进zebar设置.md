---
status: accepted
date: 2026-09-28
---

# Zebar 只作宿主：启动项只留案件卡片，由 README 一条命令写进 Zebar 的设置

律师在 Windows 上看到 Zebar 自带的起步组件（`glzr-io.starter` 的 `vanilla`，屏幕顶上一条日期、CPU、电量的栏），两个平台都不要它：Zebar 在这里只是承载卡片的宿主。那条栏出现，是因为 Zebar 第一次启动时在 `~/.glzr/zebar/settings.json` 的 `startupConfigs` 里写了它。裁定：README「随宿主启动」那一条从「托盘里勾 Run on startup」换成整行粘贴的一条命令，Windows 一条、mac 一条，把 `startupConfigs` 整个写成只有 `loo0ng / 案件卡片 / 默认` 一项。以后登录即开卡片，起步组件的栏不再出现；真要看它，仍可从托盘里手动打开。

命令要求 Zebar 已退出，免得和运行中的宿主各写各的；它覆盖整份设置，别的启动项一并清掉，这正是「只作宿主」的意思。命令本身只含 ASCII，组件名写成 JSON 转义，与安装命令同一种写法。

这不碰硬边界 2：写 Zebar 设置的是律师照 README 跑的一条安装命令，与把组件包拷进 `~/.glzr/zebar/loo0ng/` 同类；卡片本身照旧一个字节都不写。也不碰不变量 4：唤起脚本仍只找宿主、调一条命令，不顺手改设置。

这改写了 ADR-0001 里「README 先教勾托盘里的 Run on startup」那一句，其余照旧。考虑过：照旧在托盘里操作，勾上卡片、再到 `glzr-io.starter` 下取消那条栏，两个菜单、两个平台各点一遍，律师记不住，被否；让唤起脚本顺手写设置，破不变量 4，被否。
