# loo0ng-widget 的 Windows 安装脚本：装包或更新、写案件根目录、把 Zebar 的启动项设成只有案件卡片。
# 律师整行粘贴 README 里那一条命令（irm … | iex）就到这里；再跑一次就是更新。
#
# 这个文件是不带 BOM 的 UTF-8：irm 按服务器给的 charset 解码，带了 BOM 反而会在 iex 时多出一个坏记号。
# 所以本地别用 -File 跑它（Windows PowerShell 5.1 会按 ANSI 读、汉字全坏），要像 README 那样走 iex：
#   powershell -NoProfile -Command "iex (Get-Content -Raw -Encoding UTF8 install.ps1); if (-not `$ok) { exit 1 }"
#
# 可用环境变量（测试与无人值守时用，平时一个都不用设）：
#   LOO0NG_SOURCE   组件包来源：zip 的 URL 或本地路径，默认公开仓库 main 的归档。
#   LOO0NG_HOME     当作用户目录的路径，默认 %USERPROFILE%；设了它，缓存与桌面也按它下面找。
#   LOO0NG_ROOT     案件根目录，多个用 ; 隔开；设了就不问。只在设置文件不存在时写。
#   LOO0NG_SHORTCUT 1 建桌面快捷方式，0 不建；没设就问。
#   LOO0NG_HOST     0 表示不碰 Zebar 进程：不退出、不重开；没设则按需退出、装完打开。
#   LOO0NG_ZEBAR    Zebar 可执行文件的路径；没设就看 PATH，再看默认安装位置。
$ErrorActionPreference = 'Stop'
# 输出被重定向（测试、agent 抓输出）时按 UTF-8 写，否则 Windows PowerShell 5.1 按 OEM 代码页写、汉字全坏；控制台里不动。
if ([Console]::IsOutputRedirected) { [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false) }

$Source = if ($env:LOO0NG_SOURCE) { $env:LOO0NG_SOURCE } else { 'https://github.com/f4de01/loo0ng-widget/archive/refs/heads/main.zip' }
$HomeDir = if ($env:LOO0NG_HOME) { $env:LOO0NG_HOME } else { $env:USERPROFILE }
$AppData = if ($env:LOO0NG_HOME) { Join-Path $HomeDir 'AppData\Roaming' } else { $env:APPDATA }
$TouchHost = $env:LOO0NG_HOST -ne '0'
$Interactive = [Environment]::UserInteractive -and -not [Console]::IsInputRedirected

$ZebarDir = Join-Path $HomeDir '.glzr\zebar'
$Pack = Join-Path $ZebarDir 'loo0ng'
$ZebarSettings = Join-Path $ZebarDir 'settings.json'
$Cache = Join-Path $AppData 'zebar\webview-cache\loo0ng'
$Settings = Join-Path $HomeDir '.loo0ng\卡片设置.json'
$Utf8 = New-Object Text.UTF8Encoding($false)
# 组件名与预设名在 JSON 里写成转义；这份文件与原先 README 那条命令写出来的字节一致（ADR-0006）。
$StartupJson = '{"$schema": "https://github.com/glzr-io/zebar/raw/v3.3.1/resources/settings-schema.json", "startupConfigs": [{"pack": "loo0ng", "widget": "\u6848\u4ef6\u5361\u7247", "preset": "\u9ed8\u8ba4"}]}'

function Say($text) { Write-Host $text }
function Ask($prompt, $default) {
  if (-not $Interactive) { return $default }
  $answer = Read-Host $prompt
  if ($answer -eq '') { return $default }
  return $answer
}
function Yes($prompt, $default) {
  $hint = if ($default) { ' [Y/n]' } else { ' [y/N]' }
  $fallback = if ($default) { 'y' } else { 'n' }
  return (Ask ($prompt + $hint) $fallback) -match '^[Yy]'
}

# 整个过程包在一个函数里：irm | iex 时 exit 会把律师的 PowerShell 窗口一起关掉，所以失败只 return；
# 结果放在 $ok 里交给调用方。
function Install-Loo0ng {
  # ---- 前提：Python 3.9 以上在 PATH 上（卡片用 python 或 py 跑扫描脚本），Zebar 装好了。
  function Find-Python {
    foreach ($program in 'python', 'py') {
      $command = Get-Command $program -ErrorAction SilentlyContinue
      if (-not $command) { continue }
      # 商店的 0 字节占位（#32）会往 stderr 写一句、以 9009 退出；Stop 模式下 stderr 本身就算错，这里先放宽再探。
      $previous = $ErrorActionPreference
      $ErrorActionPreference = 'Continue'
      try {
        $version = & $command.Source -c 'import sys; print(sys.version_info[0], sys.version_info[1], sys.executable)' 2>&1 |
          Where-Object { $_ -is [string] }
        $code = $LASTEXITCODE
      } finally { $ErrorActionPreference = $previous }
      if ($code -ne 0 -or -not $version) { continue }
      $parts = "$version".Trim().Split(' ', 3)
      if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 9)) { return $parts[2] }
    }
    return $null
  }
  $Python = Find-Python
  if (-not $Python) {
    Say '没找到 Python 3.9 以上：先去 https://www.python.org/downloads/ 装一个，安装时勾上「Add python.exe to PATH」，再重新打开 PowerShell 跑这条命令。'
    return $false
  }
  $Zebar = Get-Command zebar -ErrorAction SilentlyContinue
  $ZebarExe = if ($env:LOO0NG_ZEBAR) { $env:LOO0NG_ZEBAR } elseif ($Zebar) { $Zebar.Source } else { 'C:\Program Files\glzr.io\Zebar\zebar.exe' }
  if (-not (Test-Path -LiteralPath $ZebarExe)) {
    Say '还没装 Zebar：先去 https://github.com/glzr-io/zebar/releases 装一个（装完不用打开），再回来跑这条命令。'
    return $false
  }

  # ---- 已有安装就是更新：换包前要 Zebar 退出，否则缓存删不掉、包也可能被占着。
  $Updating = Test-Path -LiteralPath $Pack
  if ($TouchHost -and (Get-Process zebar -ErrorAction SilentlyContinue)) {
    if (-not (Yes '安装前要先退出 Zebar，装完会自动打开。现在退出？' $true)) {
      Say '那就先右键托盘里的 Zebar 图标 → Exit，再跑一次这条命令。'
      return $false
    }
    Stop-Process -Name zebar -Force
    Start-Sleep -Seconds 1
  }

  # ---- 下载并解包到临时目录，确认里面有组件包再动现有安装。
  $TempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
  $Stage = (New-Item -ItemType Directory -Path (Join-Path $TempRoot ('loo0ng-' + [guid]::NewGuid()))).FullName
  try {
    $Zip = Join-Path $Stage 'pack.zip'
    if ($Source -match '^https?://') {
      Say "下载组件包：$Source"
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      Invoke-WebRequest -UseBasicParsing $Source -OutFile $Zip
    } else {
      Copy-Item -LiteralPath $Source -Destination $Zip
    }
    Expand-Archive -LiteralPath $Zip -DestinationPath (Join-Path $Stage 'unpacked')
    $Widget = Get-ChildItem -Path (Join-Path $Stage 'unpacked') -Directory -Recurse -Filter widget |
      Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'zpack.json') } | Select-Object -First 1
    if (-not $Widget) { throw '下载到的归档里没有组件包（没有 widget/zpack.json）。' }
    $Version = (Get-Content -LiteralPath (Join-Path $Widget.FullName 'zpack.json') -Raw -Encoding UTF8 | ConvertFrom-Json).version

    if ($Updating) {
      # 旧包整个换掉；缓存只删这个包的 Cache 与 Code Cache，记住的窗口位置、停在哪一页、已归档的案件都留着。
      Remove-Item -LiteralPath $Pack -Recurse -Force
      if (Test-Path -LiteralPath $Cache) {
        Get-ChildItem -LiteralPath $Cache -Directory -Recurse |
          Where-Object { $_.Name -eq 'Cache' -or $_.Name -eq 'Code Cache' } |
          ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
      }
    }
    New-Item -ItemType Directory -Force -Path $ZebarDir | Out-Null
    Copy-Item -LiteralPath $Widget.FullName -Destination $Pack -Recurse
    $Verb = if ($Updating) { '已更新' } else { '已安装' }
    Say "$Verb loo0ng $Version：$Pack"
  } finally {
    if ([IO.Path]::GetDirectoryName($Stage) -eq $TempRoot) { Remove-Item -LiteralPath $Stage -Recurse -Force }
  }

  # ---- 案件根目录：设置文件已存在就一个字都不动；不存在就问一次写一份。
  if (Test-Path -LiteralPath $Settings) {
    Say "案件根目录照旧：$Settings"
  } else {
    $roots = @()
    if ($env:LOO0NG_ROOT) {
      $roots = @($env:LOO0NG_ROOT.Split(';') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    } elseif ($Interactive) {
      Say '案件都放在哪个文件夹下面？每个案件是它下面的一个子文件夹。可以填多个，一行一个，空行结束。'
      while ($true) {
        $line = (Read-Host '案件根目录').Trim().Trim('"')
        if ($line -eq '') { break }
        if (-not (Test-Path -LiteralPath $line -PathType Container)) { Say '  （现在还没有这个文件夹，先记下，建好就能用）' }
        $roots += $line
      }
    }
    if ($roots.Count -gt 0) {
      $quoted = $roots | ForEach-Object { '"' + (($_ -replace '\\', '/') -replace '"', '\"') + '"' }
      $json = '{"根目录": [' + ($quoted -join ', ') + ']}'
      New-Item -ItemType Directory -Force -Path (Split-Path $Settings) | Out-Null
      [IO.File]::WriteAllText($Settings, $json, $Utf8)
      Say "已写入案件根目录：$Settings"
    } else {
      Say "还没填案件根目录。之后创建 UTF-8 文件 $Settings，内容形如 {`"根目录`": [`"D:/案件`"]}；卡片上也会显示这段提示。"
    }
  }

  # ---- Zebar 只作宿主（ADR-0006）：启动项整个写成只有案件卡片，登录即在，自带的那条顶栏不再出现。
  [IO.File]::WriteAllText($ZebarSettings, $StartupJson, $Utf8)
  Say "Zebar 启动项已设成只开案件卡片：$ZebarSettings"

  # ---- 桌面快捷方式（可选）：关过了想立刻开回来用它；走 pythonw，不带黑窗。
  $WantShortcut = if ($env:LOO0NG_SHORTCUT) { $env:LOO0NG_SHORTCUT -eq '1' } else { Yes '要在桌面放一个「打开案件卡片」吗？' $true }
  if ($WantShortcut) {
    $quiet = Join-Path (Split-Path $Python) 'pythonw.exe'
    $target = if (Test-Path -LiteralPath $quiet) { $quiet } else { $Python }
    $desktop = if ($env:LOO0NG_HOME) { Join-Path $HomeDir 'Desktop' } else { [Environment]::GetFolderPath('Desktop') }
    New-Item -ItemType Directory -Force -Path $desktop | Out-Null
    $link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop '打开案件卡片.lnk'))
    $link.TargetPath = $target
    $link.Arguments = '"' + (Join-Path $Pack 'launch.py') + '"'
    $link.WorkingDirectory = $Pack
    $link.Save()
    Say "桌面快捷方式：$($link.FullName)"
  }

  # ---- 打开：Zebar 起来就按启动项开出卡片。
  if ($TouchHost) {
    Start-Process -FilePath $ZebarExe
    Say '正在打开 Zebar，案件卡片马上出现在屏幕右上。'
  }
  return $true
}

# $ok 留在调用方的作用域里：测试与 agent 用 iex 跑完看它定退出码；律师的窗口不因失败而被关掉。
$ok = Install-Loo0ng
