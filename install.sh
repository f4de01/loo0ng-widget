#!/bin/sh
# loo0ng-widget 的 mac 安装脚本：装包或更新、写案件根目录、把 Zebar 的启动项设成只有案件卡片。
# 律师整行粘贴 README 里那一条命令就到这里；再跑一次就是更新。
#
# 可用环境变量（测试与无人值守时用，平时一个都不用设）：
#   LOO0NG_SOURCE   组件包来源：zip 的 URL 或本地路径，默认公开仓库 main 的归档。
#   LOO0NG_HOME     当作用户目录的路径，默认 $HOME；设了它，桌面也按它下面找。
#   LOO0NG_ROOT     案件根目录，多个用 ; 隔开；设了就不问。只在设置文件不存在时写。
#   LOO0NG_SHORTCUT 1 建桌面快捷方式，0 不建；没设就问。
#   LOO0NG_HOST     0 表示不碰 Zebar 进程：不退出、不重开；没设则按需退出、装完打开。
#   LOO0NG_ZEBAR    Zebar 可执行文件的路径；没设就看 PATH，再看 /Applications 里的默认位置。
#
# 整个脚本包在 main 里，`curl | sh` 时 sh 先读完再执行；问话一律从 /dev/tty 读，不吃脚本自己。
set -eu

main() {
  source=${LOO0NG_SOURCE:-https://github.com/f4de01/loo0ng-widget/archive/refs/heads/main.zip}
  home=${LOO0NG_HOME:-$HOME}
  touch_host=1; [ "${LOO0NG_HOST:-1}" = 0 ] && touch_host=0
  interactive=0; [ -t 1 ] && [ -r /dev/tty ] && interactive=1

  zebar_dir="$home/.glzr/zebar"
  pack="$zebar_dir/loo0ng"
  zebar_settings="$zebar_dir/settings.json"
  settings="$home/.loo0ng/卡片设置.json"
  # 组件名与预设名在 JSON 里写成转义；这份文件与原先 README 那条命令写出来的字节一致（ADR-0006）。
  startup_json='{"$schema": "https://github.com/glzr-io/zebar/raw/v3.3.1/resources/settings-schema.json", "startupConfigs": [{"pack": "loo0ng", "widget": "\u6848\u4ef6\u5361\u7247", "preset": "\u9ed8\u8ba4"}]}'

  # ---- 前提：python3 3.9 以上（卡片用它跑扫描脚本），Zebar 装好了。
  # mac 自带的 /usr/bin/python3 要先装命令行工具，否则一碰就弹安装框；先看 xcode-select 再碰它。
  if command -v python3 >/dev/null 2>&1 && { [ "$(command -v python3)" != /usr/bin/python3 ] || xcode-select -p >/dev/null 2>&1; } \
     && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then :; else
    printf '%s\n' '没找到 Python 3.9 以上：在终端里跑 xcode-select --install 装上命令行工具（自带 python3），装完再跑这条命令。'
    exit 1
  fi
  zebar_exe=${LOO0NG_ZEBAR:-$(command -v zebar 2>/dev/null || true)}
  [ -n "$zebar_exe" ] || zebar_exe=/Applications/Zebar.app/Contents/MacOS/zebar
  if [ ! -x "$zebar_exe" ]; then
    printf '%s\n' '还没装 Zebar：先去 https://github.com/glzr-io/zebar/releases 装一个（装完不用打开），再回来跑这条命令。'
    exit 1
  fi

  # ---- 已有安装就是更新：换包前要 Zebar 退出。
  updating=0; [ -e "$pack" ] && updating=1
  if [ "$touch_host" = 1 ] && pgrep -x zebar >/dev/null 2>&1; then
    if yes_no '安装前要先退出 Zebar，装完会自动打开。现在退出？' y; then
      pkill -x zebar || true
      sleep 1
    else
      printf '%s\n' '那就先从菜单栏退出 Zebar，再跑一次这条命令。'
      exit 1
    fi
  fi

  # ---- 下载并解包到临时目录，确认里面有组件包再动现有安装。
  stage=$(mktemp -d)
  trap 'rm -rf "$stage"' EXIT
  case $source in
    http://*|https://*) printf '下载组件包：%s\n' "$source"; curl -fsSL "$source" -o "$stage/pack.zip" ;;
    *) cp "$source" "$stage/pack.zip" ;;
  esac
  unzip -q "$stage/pack.zip" -d "$stage/unpacked"
  widget=$(find "$stage/unpacked" -type f -name zpack.json -path '*/widget/zpack.json' | head -n 1)
  [ -n "$widget" ] || { printf '%s\n' '下载到的归档里没有组件包（没有 widget/zpack.json）。'; exit 1; }
  widget=$(dirname "$widget")
  version=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "$widget/zpack.json")

  if [ "$updating" = 1 ]; then rm -rf "$pack"; fi
  mkdir -p "$zebar_dir"
  cp -R "$widget" "$pack"
  if [ "$updating" = 1 ]; then verb=已更新; else verb=已安装; fi
  printf '%s loo0ng %s：%s\n' "$verb" "$version" "$pack"

  # ---- 案件根目录：设置文件已存在就一个字都不动；不存在就问一次写一份。
  if [ -e "$settings" ]; then
    printf '案件根目录照旧：%s\n' "$settings"
  else
    roots=''
    if [ -n "${LOO0NG_ROOT:-}" ]; then
      roots=$(printf '%s' "$LOO0NG_ROOT" | tr ';' '\n')
    elif [ "$interactive" = 1 ]; then
      printf '%s\n' '案件都放在哪个文件夹下面？每个案件是它下面的一个子文件夹。可以填多个，一行一个，空行结束。'
      while :; do
        printf '案件根目录：'
        IFS= read -r line </dev/tty || line=''
        line=$(printf '%s' "$line" | sed 's/^[[:space:]"]*//; s/[[:space:]"]*$//')
        [ -n "$line" ] || break
        [ -d "$line" ] || printf '%s\n' '  （现在还没有这个文件夹，先记下，建好就能用）'
        roots=$(printf '%s\n%s' "$roots" "$line")
      done
    fi
    roots=$(printf '%s\n' "$roots" | sed '/^[[:space:]]*$/d')
    if [ -n "$roots" ]; then
      mkdir -p "$(dirname "$settings")"
      printf '%s\n' "$roots" | python3 -c 'import json, sys; print(json.dumps({"根目录": [l.strip() for l in sys.stdin if l.strip()]}, ensure_ascii=False), end="")' > "$settings"
      printf '已写入案件根目录：%s\n' "$settings"
    else
      printf '还没填案件根目录。之后创建 UTF-8 文件 %s，内容形如 {"根目录": ["/Users/你的用户名/案件"]}；卡片上也会显示这段提示。\n' "$settings"
    fi
  fi

  # ---- Zebar 只作宿主（ADR-0006）：启动项整个写成只有案件卡片。
  printf '%s' "$startup_json" > "$zebar_settings"
  printf 'Zebar 启动项已设成只开案件卡片：%s\n' "$zebar_settings"

  # ---- 桌面快捷方式（可选）：双击打开案件卡片的 .command 文件。
  case ${LOO0NG_SHORTCUT:-ask} in
    1) want_shortcut=1 ;;
    0) want_shortcut=0 ;;
    *) if yes_no '要在桌面放一个「打开案件卡片」吗？' y; then want_shortcut=1; else want_shortcut=0; fi ;;
  esac
  if [ "$want_shortcut" = 1 ]; then
    mkdir -p "$home/Desktop"
    link="$home/Desktop/打开案件卡片.command"
    printf '#!/bin/sh\nexec python3 "%s/launch.py"\n' "$pack" > "$link"
    chmod +x "$link"
    printf '桌面快捷方式：%s\n' "$link"
  fi

  # ---- 打开：Zebar 起来就按启动项开出卡片。
  if [ "$touch_host" = 1 ]; then
    if [ "$(uname)" = Darwin ] && [ -d /Applications/Zebar.app ]; then open -a Zebar; else "$zebar_exe" >/dev/null 2>&1 & fi
    printf '%s\n' '正在打开 Zebar，案件卡片马上出现在屏幕右上。'
  fi
}

# 问一句是否，默认值在 [] 里大写；不在终端里就按默认走。
yes_no() {
  if [ "$interactive" != 1 ]; then [ "$2" = y ]; return; fi
  if [ "$2" = y ]; then hint=' [Y/n] '; else hint=' [y/N] '; fi
  printf '%s%s' "$1" "$hint"
  IFS= read -r answer </dev/tty || answer=''
  [ -z "$answer" ] && answer=$2
  case $answer in [Yy]*) return 0 ;; *) return 1 ;; esac
}

main "$@"
