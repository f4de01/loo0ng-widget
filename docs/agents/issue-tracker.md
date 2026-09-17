# Issue tracker: GitHub

> **硬边界 1 在这里同样适用。** issue 的标题、正文、评论与 PR 里不出现任何真实案件材料、当事人标识、案号。这个仓库的喂料本来就全是合成的（甲乙丙），所以正常情况下没有什么可泄的；但这一条没有机械守门（本仓库没有隐私检查脚本），靠写的人自己守。要引用案件根目录时只写根，不写根下面任何一级。

这个仓库的规格与票都是 GitHub issue，全部操作走 `gh` CLI。仓库从 `git remote -v` 推出来，在 clone 里跑 `gh` 会自己认。

## 惯例

- **建 issue**：`gh issue create --title "..." --body-file <文件>`。正文多行的一律先写成文件再传，不要在命令行里拼多行字符串（Windows 上的 Git Bash 与 PowerShell 引号规则不一样，拼多行必踩）。
- **读 issue**：`gh issue view <号> --comments`
- **列 issue**：`gh issue list --state open --json number,title,body,labels --jq '[.[] | {number, title, body, labels: [.labels[].name]}]'`，按需加 `--label`、`--state`
- **评论**：`gh issue comment <号> --body-file <文件>`
- **加减标签**：`gh issue edit <号> --add-label "..."` / `--remove-label "..."`
- **关票**：`gh issue close <号> --comment "..."`

## skill 说「publish 到 issue tracker」时

建一个 GitHub issue。

## skill 说「取相关的票」时

`gh issue view <号> --comments`。

## 规格与票的形状

一张**规格票**（`/to-spec` 出的）是母票，正文是问题、解法、用户故事、实现裁定、测试裁定、范围外、补充说明。

若干张**执行票**（`/to-tickets` 出的）挂在母票下，每张正文四节：Parent（指母票）、What to build、Acceptance criteria（可勾的清单）、Blocked by。

**阻塞边**：目前写成每张票正文末尾的 `Blocked by` 一节，列真的 issue 号。GitHub 另有原生的 issue dependencies（`gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<阻塞方的数据库 id>`，那个 id 用 `gh api repos/<owner>/<repo>/issues/<n> --jq .id` 取，不是 `#号`、不是 `node_id`），要让「前沿」能被机器查就改用它。两种并存时以原生的为准。

**前沿**：blockers 全部关掉的票就可以开工。一张票的 blockers 还开着就不要动它。

## 关票门槛

票正文里 Acceptance criteria 那些勾全部为真才关。做不到的项不许默默留着：在评论里写明哪一条没做到、为什么，由人决定是缩范围还是另开一票。
