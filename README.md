# loo0ng-widget

常驻律师桌面的一张卡片，同时看住在办的多个破产案件：每案的当前模块、进度、下一个要办的节点。

它是一个 [Zebar](https://github.com/glzr-io/zebar) 组件包，不是独立应用，也不是 Claude Code 插件。窗口、拖动、置顶、多显示器、托盘常驻、安装与更新都由 Zebar 负责；这个仓库里只有组件包本身。

状态：主线已有一案一行、错误隔离、四档排序与展开，并通过 Windows 宿主验收；客户端依赖已随包提供。窗口控件、整机断网启动和最终交付验收仍待完成，见 GitHub Issues。

## 它读什么

律师用 [loo0ng-skills](https://github.com/f4de01/loo0ng-skills) 办案，每个案件是本机上的一个工作区目录，目录里有一份由图引擎重算的机器可读视图 `图视图.json`。这张卡片读的就是它。

- **发现案件**：在 `~/.loo0ng/卡片设置.json` 填 `{"根目录":["绝对路径"]}`，卡片扫下面一层，目录里有 `图视图.json` 就算一个案件。
- **只读一个文件**：卡片只读每个工作区的 `图视图.json`。`材料/`、`文书/`、`待归档/`、`参考/` 一律不读、不列、不显示。卡片的代码里只该出现这一个工作区文件名。
- **只聚合，不判定**：状态由图引擎算好一次。卡片可以计数、排序、取"前方"的第一个，但任何需要看条目才能得出的结论，都必须引擎先算好。
- **格式版本**：`图视图.json` 带一个整数 `格式版本`，现为 2。遇到不认识的版本明确报错，不猜、不降级。

首版只读进度，一个字节都不写。提醒不在首版。

## 装法

先装好 Zebar 和 Python 3.9 以上；Windows 的 `python`、mac 的 `python3` 须能在终端运行。以下命令从公开仓库的 `main` 下载完整组件包，无需 Git 或 GitHub 登录；安装时需要联网，运行时无需外网。

Windows：打开 **PowerShell**，整行粘贴：

```powershell
& { $ErrorActionPreference = 'Stop'; $dest = Join-Path $env:USERPROFILE '.glzr/zebar/loo0ng'; if (Test-Path -LiteralPath $dest) { throw 'loo0ng already exists; move it outside the Zebar directory before installing.' }; $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\'); $stage = (New-Item -ItemType Directory -Path (Join-Path $tempRoot ('loo0ng-' + [guid]::NewGuid()))).FullName; try { Invoke-WebRequest -UseBasicParsing 'https://github.com/f4de01/loo0ng-widget/archive/refs/heads/main.zip' -OutFile (Join-Path $stage 'pack.zip'); Expand-Archive -LiteralPath (Join-Path $stage 'pack.zip') -DestinationPath $stage; New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null; Copy-Item -LiteralPath (Join-Path $stage 'loo0ng-widget-main/widget') -Destination $dest -Recurse; Write-Output "Installed: $dest" } finally { if ([IO.Path]::GetDirectoryName($stage) -eq $tempRoot) { Remove-Item -LiteralPath $stage -Recurse -Force } } }
```

mac：打开**终端**，整行粘贴（此命令尚未在 mac 验收）：

```sh
( set -eu; dest="$HOME/.glzr/zebar/loo0ng"; if [ -e "$dest" ] || [ -L "$dest" ]; then printf '%s\n' 'loo0ng already exists; move it outside the Zebar directory before installing.' >&2; exit 1; fi; stage=$(mktemp -d); trap 'rm -rf "$stage"' EXIT; curl -fL 'https://github.com/f4de01/loo0ng-widget/archive/refs/heads/main.zip' -o "$stage/pack.zip"; unzip -q "$stage/pack.zip" -d "$stage"; mkdir -p "$(dirname "$dest")"; cp -R "$stage/loo0ng-widget-main/widget" "$dest"; printf 'Installed: %s\n' "$dest" )
```

安装位置是 `~/.glzr/zebar/loo0ng/`，Windows 展开为 `C:\Users\<用户名>\.glzr\zebar\loo0ng\`。命令包含整个 `vendor/` 目录。若已有安装，先关闭组件，将旧的 `loo0ng` 文件夹移到 Zebar 目录外备份，再运行命令；更新后按[开发说明](docs/development.md#页面与宿主)清该包的 WebView 缓存。

创建 UTF-8 文件 `~/.loo0ng/卡片设置.json`（父目录不存在就先创建）。Windows 示例：

```json
{"根目录": ["D:/案件"]}
```

mac 示例：

```json
{"根目录": ["/Users/你的用户名/案件"]}
```

把示例换成实际的绝对路径，可以填多个根目录。Windows 路径用 `/`，或把每个反斜杠写成 `\\`。根目录下面一层放各案工作区，卡片据此发现案件。安装命令不会创建或覆盖这份设置。

在 Zebar 里打开「loo0ng → 案件卡片 → 默认」；若列表里还没有，退出并重新启动 Zebar。卡片会出现在 Windows 任务栏 / mac 程序坞里。未配置好根目录时，卡片会显示设置路径和填写示例，修好后下一轮扫描自动恢复。

测试、显式开发预览与验收进度见[开发说明](docs/development.md)。第三方代码的固定版本、来源和许可证见[随包客户端](widget/vendor/README.md)。

## 案件数据

这个仓库永不包含任何真实案件材料。单测使用 `tests/` 中手写的合成视图；宿主验收使用 loo0ng-skills 仓库 `evals/种子/` 回放出的合成工作区。
