# 原型：两页两形式与材质（#13）

抛弃式原型，只在 `prototype/呈现` 分支上，不合并进 main。它回答两个纸上答不了的问题：Acrylic 在 Zebar 3.3.1 的透明窗里行不行；清单页、案件页、模块视、矩阵视加自绘卡片放在一起好不好看、色值定成什么。材质结论已写回 main 的 `docs/adr/0004`；色值与变量表以本文为准，#16 从这里取值。2026-09-22。

## 结论

1. **Acrylic 行，且没有性能代价**：`tauriWindow.setEffects({effects:['acrylic']})` 在 Windows 11 的 Zebar 透明窗里立刻生效，桌面透过卡片被模糊；程序移窗、程序缩放、鼠标拖动、鼠标缩放四项的帧间隔均值 4.2ms、峰值 ≤ 25ms、没有一帧超过 33ms，与不开效果时无差。
2. **但它盖的是整个窗口矩形**：12px 透明外边距与圆角外的四个角都被磨砂成一块方板，柔投影也画在这块板上。要圆角就得接受角上那一小块方磨砂，要方板消失就得放弃系统模糊。见 `prototype-呈现/host-corners.png`（左：Acrylic 带外边距；中：Acrylic 去外边距；右：不开效果）。
3. **`setEffects` 的返回值不等于「看得见」**：`mica`、`tabbed`、带 `color` 的 `acrylic` 全部返回成功，其中 mica 在这扇窗里没有任何可见变化，`blur` 返回成功但整块窗口变成深灰黑。所以实现里只能试 `acrylic` 这一种（Win10 1803+ 与 Win11 都有），并把它的成功当成功；不能靠「哪个成功用哪个」去探。
4. **不开效果时透明窗干净**：`clearEffects` 之后外边距完全透明，自绘卡片（90% 底、细描边、柔投影、18px 圆角）单独成立，这是可靠的底层。
5. **观感**：两页两形式加自绘卡片放在一起成立，三套色值都在「收紧不推倒」那条线上，差别在纸色冷暖与对比，供律师在浏览器里翻着挑。默认取 A 纸。

## 怎么跑

浏览器看观感（不装宿主）：

```
python -m http.server 8000 --bind 127.0.0.1 --directory widget
http://127.0.0.1:8000/prototype.html?dev=1&variant=A
```

- `variant=A|B|C`，或键盘 ← →；底部黑色药丸是原型切换条，不是设计的一部分。`60%` 按钮模拟系统模糊成功时的底色（浏览器里只模糊页面自己，桌面不会透）；`背景` 换三种假桌面。
- 合成数据由 `widget/prototype-data.js` 在代码里生出（甲乙丙，园艺词，形状按 #12 的扫描契约）；左下角的文件框可换成任何同形状的 JSON。
- 截图用：`frame=440x620&shot=1&case=甲乙丙公司&form=matrix`，把卡片定成那个窗的大小、藏起原型工具、直接落到某一案某一形式。
- 案件页里点格子跳模块视并闪一下；停在格子上出悬浮概览；模块行折叠；返回键回清单页；页、案、形式记在本地存储。

真宿主看材质（Windows）：把 `widget/` 里的 `prototype.html`、`prototype.css`、`prototype.js`、`prototype-data.js`、`zpack.json`（`htmlPath` 指向 `prototype.html`，`transparent: true`，默认窗 440×620）装进 `~/.glzr/zebar/loo0ng/`，先把原装的备份到 Zebar 目录外；清 `%APPDATA%\zebar\webview-cache\loo0ng`；`zebar start-widget-preset --pack loo0ng --widget-name 案件卡片 --preset 默认`。页面在宿主里：

- 启动即试 `acrylic`，成功把底色降到 60%；结果与基准写在卡片底部的黑色诊断面板里（`d` 键藏起面板与切换条）。
- 装后第一次启动 3 秒后自动跑基准（`b` 键再跑）：acrylic → none → acrylic 各做 60 步 `setPosition`、61 步 `setSize`，记每步耗时与帧间隔。
- `e` 键轮换效果：acrylic+color → mica → blur → tabbed → none → acrylic；`m` 键把透明外边距切成 0。
- 整卡可拖（交互区除外，阈值 4px），拖动与缩放结束各写一行帧间隔统计。

验完按字节哈希恢复原设置与原组件，清缓存，重开。

## 变量表

三套共用的（`:root`）：

| 变量 | 值 | 说明 |
| --- | --- | --- |
| `--radius` | 18px | 卡片圆角 |
| `--pad` | 16px | 卡片内边距 |
| `--margin` | 12px | 透明外边距，放柔投影；Acrylic 下它会被磨砂成方板 |
| `--font` | `-apple-system, "PingFang SC", "Segoe UI", "Microsoft YaHei", sans-serif` | |
| `--fs-title` / `--fs-body` / `--fs-secondary` / `--fs-min` | 15 / 13 / 12 / 11px | 目录名 / 正文 / 次要 / 最小 |
| `--shadow` | `0 8px 24px rgba(0,0,0,.12)` | 外加 `0 0 0 1px rgba(0,0,0,.06)` 描边与 `inset 0 1px 0 rgba(255,255,255,.55)` 内高光 |
| `--card-alpha` | .9；`html[data-blur="1"]` 时 .6 | 自绘底不透明度 |
| `--dot` | 12px | 圆圈直径 |
| `--ease` | 180ms ease-out | 横滑、折叠、按钮显隐 |

矩阵格（CSS 布局，不是页面算法）：`--cell: clamp(10px, calc(100cqw / var(--n) * .83), 26px)`，`--gap: calc(var(--cell) / 5)`；`.matrix-wrap { container-type: inline-size }`，`--n` 是模块数。列名 `writing-mode: vertical-rl; max-height: 6em; text-overflow: ellipsis`。

三套色值（`html[data-variant]`）：

| 变量 | A 纸（默认） | B 雾 | C 墨 | 用在 |
| --- | --- | --- | --- | --- |
| `--card-rgb` | 243,242,236 | 249,250,248 | 236,235,226 | 卡片底 |
| `--ink` | #283c36 | #1f2b27 | #1c2c26 | 正文、标题 |
| `--ink-2` | #5f6f66 | #5b6862 | #4d5c55 | 计数、当前行、返回键 |
| `--ink-3` | #717f76 | #75837d | #66746b | 时限、时间、列名、模块状态、顶行 |
| `--line` / `--line-soft` | #d9dbd2 / #e7e8e1 | #e0e4df / #edf0ec | #cdd0c4 / #dddfd3 | 分隔线 |
| `--button` / `--button-ink` / `--button-line` | #e3e9dc / #365845 / #cdd8c7 | #eef2ee / #2e5243 / #d7ded8 | #dbe3d5 / #244336 / #bfcbb8 | 「模块」「矩阵」按钮 |
| `--button-on` / `--button-on-ink` | #365845 / #f3f2ec | #2e5243 / #f9faf8 | #244336 / #eceae0 | 选中的那个按钮 |
| `--confirmed` | #3d6a54 | #2f6b52 | #2a5a45 | 已确认实心；已生成的半实那一半 |
| `--generated` | #8fb2a0 | #93bda9 | #79a48e | 进度条的已生成段 |
| `--unstarted` / `--unstarted-bg` | #a6b0a9 / #e2e5df | #b1bbb5 / #e9ede9 | #98a39b / #d9dcd1 | 未生成的空心描边 / 进度条的未生成段 |
| `--na` / `--na-slash` | #d7d9d2 / #a2a79f | #e0e3df / #adb4b0 | #cfd1c8 / #93999a | 不适用的淡灰 / 斜线 |
| `--amber` / `--amber-ink` | #b5761f / #9a6229 | #c27f2c / #a0651f | #a8681e / #8d5516 | 高亮未清的琥珀圈 / 「等你看」文字 |
| `--hover` | rgba(40,60,54,.06) | rgba(31,43,39,.05) | rgba(28,44,38,.07) | 行悬停、读不出行 |
| `--pop-rgb` | 255,254,250 | 255,255,255 | 250,249,243 | 悬浮概览底 |
| `--error-ink` / `--error-bg` | #974c35 / #f1e6dc | #9a4a33 / #f4e9e2 | #8f4530 / #ecdfd4 | 横幅（原型未画） |

五态编码（圆圈与矩阵格共用）：未生成 = 空心，描边 `--unstarted`；已生成 = 左半实 `--confirmed`；已确认 = 实心 `--confirmed`；不适用 = `--na` 底加一道 `--na-slash` 斜线；高亮未清 = 再加 `0 0 0 1.5px 卡片底色, 0 0 0 3px --amber` 两圈。进度条四段：已确认 `--confirmed`、已生成 `--generated`、未生成 `--unstarted-bg`、不适用 `--na` 斜纹，段间 2px 空隙。

### 校验

用 dataviz 的 `validate_palette.js`。五态里靠颜色单独区分的只有三个：已确认绿、不适用斜线灰、琥珀（实心 / 半实 / 空心 / 斜线是形状，是次要编码，故意的）。三套的这三色 all-pairs：

| | CVD 最差 ΔE（protan） | 正常视觉最差 ΔE | 说明 |
| --- | --- | --- | --- |
| A | 11.9 | 15.8 | 琥珀从 #b07a2a 提到 #b5761f 才过 15 |
| B | 13.9 | 16.9 | |
| C | 12.0 | 16.1 | 斜线灰从 #8f958c 换成更冷的 #93999a 才过 15 |

文字对卡片底的对比度（WCAG）：`--ink` 10.5 / 14.0 / 12.1；`--ink-2` 4.7 / 5.6 / 5.9；`--ink-3` 3.7 / 3.8 / 4.1（原先 2.6–3.0，压深了一档，它承载 11–12px 的时限与时间，不能再淡）；`--confirmed` 5.5 / 6.0 / 6.6；`--amber-ink` 4.5 / 4.6 / 5.1；`--amber` 圈 3.4 / 3.2 / 3.7（它是图形不是字）。

## Acrylic 实测

机器：Windows 11 Pro 10.0.26200，DPR 1.5，WebView2 Edg/153，Zebar 3.3.1，Tauri 2 的 `plugin:window|set_effects` 走随包 `vendor/zebar-3.3.1.js` 里的 `tauriWindow`。窗 440×620（物理 660×930）。

| 项 | acrylic | none | 备注 |
| --- | --- | --- | --- |
| `setEffects` 调用 | 1.0–2.6ms 返回成功 | `clearEffects` 1.0–1.5ms | |
| 程序移窗 60 步 | 2.2–2.9 ms/步；帧均 4.1–4.2ms，峰 ≤ 5ms | 2.0–2.4 ms/步；峰 ≤ 5ms | 三轮 |
| 程序缩放 61 步 | 6.1–9.5 ms/步；峰 8–25ms | 6.3–8.0 ms/步；峰 4ms | 峰值只在第一轮出现一次 |
| 鼠标拖 300px / 60 步 | 225 帧，均 4.2ms，峰 4ms | | 整卡可拖那条路 |
| 鼠标从右下角缩放 | 96–265 帧，均 4.2ms，峰 4ms | | 宿主自己的缩放热区 |
| > 33ms 的帧 | 0 | 0 | 所有项 |

看得见的：

- `acrylic`：桌面透过 60% 的卡片被模糊，字全部可读；整个窗口矩形（含 12px 外边距与圆角外的四个角）被磨砂。
- `acrylic` + `color [243,242,236,120]`：返回成功，60% 底下看不出差别。
- `mica`：返回成功，没有任何可见变化。
- `blur`：返回成功，整块窗口变深灰黑，不能用。
- `tabbed`：返回成功，看起来同 blur。
- `none`：外边距完全透明，自绘卡片与柔投影干净。

失败路径在这台机器上触发不了：Windows 上 `setEffects` 对不支持的名字也返回成功。所以「失败一言不发停在自绘层」在实现里要写成两层：调用抛错时停在自绘层；调用不抛错但没效果时没法知道，只能靠只试 `acrylic` 一种来把这种情况压到最小。

## 给 #16 的备忘

- 矩阵在 28 个模块时格子落到 10px 下限、总宽 334px 放得下，但 11px 的竖排列名比格子宽，列名彼此挤到一起。建议 ≥ 18 列时列名只在悬浮里出，或隔列显示。
- 清单页没有当前节点那一行，原型按 `进度.总数 === 0` 印「图还是空的」、否则印「没有前方了」。这是页面在判。扫描契约里加一个档位字段（四档排序已经算过了）让页面照印更干净。
- `diag`、切换条、`e`/`m`/`b`/`d` 键、基准全是原型工具，不进实现。
- Acrylic 下 60% 底可读；不开效果时 90% 底可读；不要在没有真实模糊时用 60%。
- 窗口按钮（右上角）与案件页表头的「模块」「矩阵」按钮抢同一个角：原型里第一版「矩阵」压在最小化底下，用鼠标点它把窗最小化了两次。原型加了 `body.win .case-head { padding-right: 58px }` 让位；实现里把两页的表头都给窗口按钮留出这一块，mac 在左上角同理。
- 源码禁用名那条测试扫整个 `widget/`，而引擎给 `高亮` 的三个值里有一个含「文书」二字。页面只比较「未清」就永远不用写它；扫描脚本原样透传也不用写它；只有手写合成数据会撞上（原型里拼出来绕过）。#16 别在页面里比较那个值。
- `focused: true` 的宿主窗会在启动时抢焦点，与「常驻」不太合，实现票里看要不要关。

## 截图

`docs/prototype-呈现/`：

- `list-A.png` `list-B.png` `list-C.png`：清单页三套色值（浏览器，假桌面）。
- `module-A.png`、`matrix-A.png`、`matrix28-A.png`：模块视、矩阵视、28 模块的矩阵。
- `list-A-60.png`：60% 底 + 页面自身 backdrop-filter 的模拟。
- `host-acrylic-margin.png`、`host-none-margin.png`、`host-corners.png`：真宿主里 Acrylic 与不开效果，角上的方板。
- `host-module.png`、`host-matrix-hover.png`：真宿主里的案件页与悬浮概览。
- `host-diag-final.png`：诊断面板里的基准数字。
