# loo0ng-widget

常驻律师桌面的一张卡片，同时看住在办的多个破产案件：每案的当前模块、进度、下一个要办的节点。

它是一个 [Zebar](https://github.com/glzr-io/zebar) 组件包，不是独立应用，也不是 Claude Code 插件。窗口、拖动、置顶、多显示器、托盘常驻、安装与更新都由 Zebar 负责；这个仓库里只有组件包本身。

状态：Windows 上首版（#8）与呈现定形（#20）两轮人手验收都已通过，矩阵视重做（#24，0.2.0）律师在宿主里看过；Python 3.9 全套测试通过。逐项证据见 [验收记录](docs/acceptance-windows.md)。mac 实机验收另进交付票。

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

安装位置是 `~/.glzr/zebar/loo0ng/`，Windows 展开为 `C:\Users\<用户名>\.glzr\zebar\loo0ng\`。命令包含整个 `vendor/` 目录。已经装过的照下面的[更新](#更新)做：安装命令见到已有安装会拒绝，不会覆盖。

创建 UTF-8 文件 `~/.loo0ng/卡片设置.json`（父目录不存在就先创建）。Windows 示例：

```json
{"根目录": ["D:/案件"]}
```

mac 示例：

```json
{"根目录": ["/Users/你的用户名/案件"]}
```

把示例换成实际的绝对路径，可以填多个根目录。Windows 路径用 `/`，或把每个反斜杠写成 `\\`。根目录下面一层放各案工作区，卡片据此发现案件。安装命令不会创建或覆盖这份设置。

### 更新

新版本就在公开仓库的 `main` 上（当前版本号见 `widget/zpack.json`，各版说明见 GitHub Releases）。更新是三步：把旧包挪开、重跑上面的安装命令、清掉这个包的 WebView 缓存。设置文件 `~/.loo0ng/卡片设置.json` 不在包里，更新不碰它。

1. 退出 Zebar：右键托盘里的 Zebar 图标 → `Exit`。只关组件不够，缓存被占着删不掉。
2. 挪开旧包、清缓存。Windows：在 **PowerShell** 里整行粘贴。它把旧包挪到用户目录下一个带时间的备份文件夹，只删 `loo0ng` 这一个包的缓存（`%APPDATA%\zebar\webview-cache\loo0ng`），别的组件不动：

   ```powershell
   & { $ErrorActionPreference = 'Stop'; if (Get-Process zebar -ErrorAction SilentlyContinue) { throw 'Zebar is running; exit it from the tray first.' }; $pack = Join-Path $env:USERPROFILE '.glzr/zebar/loo0ng'; $old = Join-Path $env:USERPROFILE ('loo0ng-old-' + (Get-Date -Format 'yyyyMMdd-HHmmss')); Move-Item -LiteralPath $pack -Destination $old; $cache = Join-Path $env:APPDATA 'zebar/webview-cache/loo0ng'; if (Test-Path -LiteralPath $cache) { Remove-Item -LiteralPath $cache -Recurse -Force }; Write-Output "Old pack moved to: $old" }
   ```

   mac：把 `~/.glzr/zebar/loo0ng` 挪到 Zebar 目录外（比如 `~/loo0ng-old`）。mac 上这个包的 WebView 缓存在哪还没验过；更新后卡片若还是旧样子，多半是缓存没清。
3. 重跑上面的安装命令，再照[打开卡片](#打开卡片)打开。清缓存会一并清掉卡片记住的窗口位置与停在哪一页，要重新摆一次。

确认新版正常后，备份文件夹可以删掉。

在 Zebar 里打开「loo0ng → 案件卡片 → 默认」；若列表里还没有，退出并重新启动 Zebar。卡片会出现在 Windows 任务栏 / mac 程序坞里。未配置好根目录时，卡片会显示设置路径和填写示例，修好后下一轮扫描自动恢复。

测试、显式开发预览与验收进度见[开发说明](docs/development.md)。第三方代码的固定版本、来源和许可证见[随包客户端](widget/vendor/README.md)。

## 打开卡片

三个入口都落到包里同一条命令（`launch.py`）：宿主没开就连宿主一起拉起，卡片**已经开着（含最小化）时什么都不发生**——不聚焦、不还原、不多开一扇。最小化了要从 Windows 任务栏 / mac 程序坞还原，这条命令做不到（[ADR-0001](docs/adr/0001-唤起走宿主cli-语义只是没开就开-命令归本仓库-skill侧另立adr.md)）。

**一、随宿主启动。** 勾一次就行，推荐先做这个：右键托盘里的 Zebar 图标 → `Widget packs` → `loo0ng` → `案件卡片` → 勾上 `Run on startup`。以后登录即在，下面两条留给「关过了想立刻开回来」。

**二、桌面快捷方式。** 装好组件包之后跑一次，桌面上就多一个「打开案件卡片」。

Windows：打开 **PowerShell**，整行粘贴：

```powershell
& { $ErrorActionPreference = 'Stop'; $target = Join-Path $env:USERPROFILE '.glzr\zebar\loo0ng\launch.py'; if (-not (Test-Path -LiteralPath $target)) { throw "Not installed: $target" }; $py = (Get-Command python).Source; $quiet = Join-Path (Split-Path $py) 'pythonw.exe'; if (Test-Path -LiteralPath $quiet) { $py = $quiet }; $link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) '打开案件卡片.lnk')); $link.TargetPath = $py; $link.Arguments = '"' + $target + '"'; $link.WorkingDirectory = (Split-Path $target); $link.Save(); Write-Output "Created: $($link.FullName)" }
```

mac：打开**终端**，整行粘贴（此命令尚未在 mac 验收）：

```sh
( set -eu; target="$HOME/.glzr/zebar/loo0ng/launch.py"; [ -f "$target" ] || { printf 'Not installed: %s\n' "$target" >&2; exit 1; }; link="$HOME/Desktop/打开案件卡片.command"; printf '#!/bin/sh\nexec /usr/bin/python3 "$HOME/.glzr/zebar/loo0ng/launch.py"\n' > "$link"; chmod +x "$link"; printf 'Created: %s\n' "$link" )
```

**三、对 agent 说一句。** 照抄这句——Windows：

> 跑一下 `python ~/.glzr/zebar/loo0ng/launch.py`，把案件卡片打开。

mac：

> 跑一下 `python3 ~/.glzr/zebar/loo0ng/launch.py`，把案件卡片打开。

Windows 上 agent 认不出 `~` 就把路径写成 `%USERPROFILE%\.glzr\zebar\loo0ng\launch.py`。

没装 Zebar 时脚本只说一句「没找到 Zebar：先去 https://github.com/glzr-io/zebar 装一个，再跑这条命令。」并以非零码退出，不刷一串错误；桌面快捷方式走的是不带控制台的 `pythonw`，那里这句话改用一个提示框说。

**Zebar 当时没在跑，这条命令会自己变成宿主进程**：卡片照样出来，但命令要等 Zebar 退出才返回。三个入口各受什么影响：桌面快捷方式在 Windows 上没有窗口，只是多一个后台 `pythonw` 陪着 Zebar，不碍事；**mac 的 `.command` 会让那扇终端窗口一直开着，关掉它会把 Zebar 一起关掉**（这一条尚未在 mac 实机验过）；agent 那一句若因此卡住，让它把命令放到后台再继续。勾了上面第一条「Run on startup」，平时就碰不到这种情形。

## 案件数据

这个仓库永不包含任何真实案件材料。单测使用 `tests/` 中手写的合成视图；宿主验收使用 loo0ng-skills 仓库 `evals/种子/` 回放出的合成工作区。
