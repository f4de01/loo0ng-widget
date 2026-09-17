# Triage Labels

skill 那一套用五个分诊角色说话。这张表把角色映射到本仓库 issue tracker 上真实的标签字符串。

| skill 里的角色 | 本仓库的标签 | 含义 |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | 维护者还没评估 |
| `needs-info` | `needs-info` | 等报告人补信息 |
| `ready-for-agent` | `ready-for-agent` | 已经写清楚，agent 可以直接接 |
| `ready-for-human` | `ready-for-human` | 得人来做 |
| `wontfix` | `wontfix` | 不会做 |

skill 正文里提到某个角色时（例如「打上 AFK-ready 那个分诊标签」），用这张表右边那一列的字符串。

五个标签都已经在仓库里建好，`gh label list` 查得到。

## 这个仓库的用法

规格票与执行票由 `/to-spec`、`/to-tickets` 出，出来就是写清楚的，直接打 `ready-for-agent`，不走分诊。

`needs-triage` 与 `needs-info` 留给从外面进来的 issue。`ready-for-human` 留给必须人动手的那些：装宿主、人手点按钮验收、断网实测、律师 mac 上试用。这类事在本仓库不少，别把它们打成 `ready-for-agent`。
