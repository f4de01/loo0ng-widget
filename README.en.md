# loo0ng-widget

[中文](./README.md)

A card that lives on your desktop and keeps an eye on every case you are working on: which module each case is in, how far along it is, and which node comes next.

It works alongside [loo0ng-skills](https://github.com/f4de01/loo0ng-skills). Each case is a workspace on your machine; the card only reads the `图视图.json` that the graph engine computes inside each workspace, and never writes a single byte. It is a [Zebar](https://github.com/glzr-io/zebar) widget pack, not a standalone app.

<p align="center">
  <img src="docs/images/list.png" width="280" alt="List page: one row per case">
  <img src="docs/images/module.png" width="280" alt="Case page, module view">
  <img src="docs/images/matrix.png" width="280" alt="Case page, matrix view">
</p>

The list page shows one row per case: folder name, a progress bar with "confirmed / total", the current module and current node, with an amber ring on nodes waiting for your review. Click a case to open its page: the module view lists nodes grouped by module; the matrix view draws one cell per node, one column per module, so a whole case fits in one glance. The screenshots use synthetic cases.

## Install

Install two things first:

- [Zebar](https://github.com/glzr-io/zebar/releases), the host for the card. No need to open it.
- Python 3.9 or newer. macOS ships with it; on Windows get it from [python.org](https://www.python.org/downloads/) and tick **Add python.exe to PATH** during setup.

Then paste one command. It downloads the pack, asks where your cases live, sets Zebar to open only this card at login, and opens the card. Installing needs the internet; running does not.

Windows: open **PowerShell** and paste the whole line:

```powershell
irm https://raw.githubusercontent.com/f4de01/loo0ng-widget/main/install.ps1 | iex
```

macOS: open **Terminal** and paste the whole line (not yet verified on a real Mac):

```sh
curl -fsSL https://raw.githubusercontent.com/f4de01/loo0ng-widget/main/install.sh | sh
```

It will ask you:

- **Case root folder**: the folder your cases live under, one subfolder per case. You can give several; an empty line finishes. The answer goes into `~/.loo0ng/卡片设置.json`; edit that file to change it later. It looks like `{"根目录": ["D:/cases"]}`.
- **Desktop shortcut** "打开案件卡片" (open the case card): double-click it to bring the card back after closing it.
- If Zebar is running, it asks to quit it first and reopens it when done.

Zebar is only the host here: the install rewrites its startup list to contain just the case card, so Zebar's built-in top bar (date, CPU, battery) no longer appears.

## Day to day

- The card appears at the top right at login. Drag it anywhere; it remembers the position.
- Closed it and want it back: double-click the desktop shortcut, or tell your agent "run `python ~/.glzr/zebar/loo0ng/launch.py` to open the case card" (`python3` on macOS). If it is minimized, restore it from the taskbar or Dock.
- Finished a case: click the archive icon at the right of its row on the list page. It moves into the "已归档 N" (archived) fold at the bottom, where you can restore it any time.
- If the root folder is not set up yet, the card shows only the settings path and an example; it recovers within seconds once fixed.

## Update

Run the same install command again. Your settings file, window position, current page and archived cases are kept. Release notes are on [Releases](https://github.com/f4de01/loo0ng-widget/releases).

## What it reads, and what it does not

Only `图视图.json` in each case workspace. `材料/`, `文书/`, `待归档/` and `参考/` are never read, listed or shown. The card displays what the engine has already computed and makes no judgement of its own.

This repository never contains real case material: tests use hand-written synthetic views, and screenshots and acceptance runs use synthetic workspaces replayed from loo0ng-skills, with parties named 甲, 乙 and 丙.

Development, tests and acceptance records: [docs/development.md](docs/development.md) (Chinese).
