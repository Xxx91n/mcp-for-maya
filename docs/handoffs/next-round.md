# next-round.md — rev37（R29：0.4.0 发布执行窗就绪）

生成：2026-09-28 R29 grill 整理环节｜Spec：docs/decision-ledger.md D-133..D-135（+D-129 行内 schedule 静默归因）｜前置调研：R29-Q1..Q3 经 atomcode 派发｜题面档：.scratch/t29/questions/q1..q3-*.md

## 环境实况（本环节核验 ~07:45 UTC）

- main=89fac22；本分支 grill/round29-release-window 账本栈 4 commits（uom/rkn/xvr/rks）+本批（CONTEXT 两处+本任务书）——未推未合，合并时机用户裁。
- 0.4.0 在飞：classifier 已 4-Beta（T-28a 落地）、25 工具、760+26s 测试绿、uv build+twine PASSED；CHANGELOG [Unreleased] 节=0.4.0 全部内容（Evidence 指针齐）。
- **drift-canary schedule 链已实证死亡**：2026-09-28 06:37 UTC 首窗后 61min 三次核验恒空（结构性静默失效，非延迟）——外部调度升级已触发（D-135③），载体裁决呈报中（建议 A=本机 Task Scheduler + D=disable/enable 重注册顺手修），**等用户拍板**。
- D-127 复核记录仍成立（dispatch 首燃绿 run 36334876189）；D-127 的 schedule 对照完成条件→由 T-29b 兑现后闭环。
- 发布通道：release.yml 触发=tag `v*` push→test 4 格→build→publish(PyPI trusted publisher，无人批门)；GH Release=minor 档手动建（D-084/D-108）；v0.3.0 body 惯例=#vX.Y.Z+CHANGELOG 节逐字搬运。
- CONTEXT.md 本轮已落：金丝雀词条静默实证句+新词条「发布编排纪律」。

## 批次序与规则（发布编排纪律词条全约束）

序=T-29a（0.4.0 发布窗）→T-29b（canary 外部调度）→T-29c（文档顺手批）→T-29d（gate 核对）。
**andon 三段**（D-133②）：tag 后 CI 红→中止+revert 重发不窗内修/PyPI 推送=不可回改点其后瑕疵走 0.4.1+waiver 带 expiry/中止即 incident 入账（归因+回退+重发时点）。
**go-signal×2**（D-134 α）：tag push 前呈核对单逐项核验→点头→push；GH Release 创建前呈 body→点头→建。
**冻结语义**：CHANGELOG 节==tag diff（D-107④）；发布本体不改代码。

## 任务清单

### T-29a — 0.4.0 发布执行窗（D-134/D-135，agent 执行+双 go-signal）

段序：①release commit=CHANGELOG [Unreleased]→[0.4.0] - 2026-09-28+顶部补空 Unreleased 头（keep-a-changelog 惯例；v0.3.0 同款工艺）→②本地 uv build+twine 复测→③preflight 五行核对单呈报【Unreleased 节 Evidence 指针齐/version=0.4.0（pyproject:14 区+PKG-INFO）/classifier=4-Beta/build+twine 复测过/**tag commit SHA==核对单记录 SHA**】（单子一次性 expiry：0.5.0 前复审）→④go-signal ①：用户点头→tag v0.4.0 push→⑤盯 release.yml 全格+PyPI 验证=页面渲染+临时 venv `pip install mcp-for-maya==0.4.0` 冒烟（D-135①；yank 路径下版本号永不复用）→⑥go-signal ②：呈 GH Release body→点头→建 minor 档。可选强化：仓库启用 Immutable Releases（tag 锁 SHA，Trivy 供链先例）。

suggested skills：gitbutler（release commit）、neat-freak（核对单逐项核验）

### T-29b — canary 外部调度承载（D-129/D-135③，等用户裁决载体）

待定裁决：A)Windows Task Scheduler 本机每周一 06:40 UTC `gh workflow run ci.yml --repo Xxx91n/mcp-for-maya`（零新凭据面，机器须开机）/B)托管 cron 服务（PAT 外露，否决倾向）/C)第二仓 schedule 反 dispatch（同静默风险+PAT，否决倾向）；D)并行顺手修=disable/enable 重注册 schedule 下周一窗验证自愈。已呈报建议 A+D。落地后：新调度链归因入账+下窗核验闭环 D-127 对照条件。

suggested skills：atomcode-research（载体细节如需）、neat-freak（归因入账）

### T-29c — 文档顺手批（D-133⑤+P-01）

- 旧 scratch 账本 prose 退役：活账本一行标 superseded+留原文件不删（D-082⑥⑤ 同构）。
- P-01 报告模板命令校正：`ruff check . -ojson`→真命令 `--output-format=json --exit-zero`+预算脚本第二参数 `.github/ruff-baseline.json`（下次报告模板改）。

suggested skills：neat-freak

### T-29d — 0.4.0 发布后 gate 核对（D-131 清单唯一载体=ADR-0023 R28 增补块）

触发点（D-135③）：β 观测闭环+PyPI 冒烟完成后即开。议程=ADR-0023 增补块逐项挂证据指针：#7 十框全绿（用户真机窗）/D-115 补采同窗/D-127 复核（含 T-29b 闭环）/节==tag diff/版本阶梯/GH Release/milestone 归置/公 API 声明（README 冻结段已在档）/D-036⑤ 分支保护 404=硬项或豁免裁决/T-24 mayapy 冒烟或 D-049 披露/**asset_import resolve().startswith 断言债裁**（D-133③）/一次性过堂行已完成（docs/evidence/release-surface-review-2026-09-28.md）/notify 红路径观测/裁出 D-102/D-104/D-118。末行 go/no-go=用户拍板。

suggested skills：neat-freak（逐项证据指针核验）、domain-modeling（债裁决措辞）

## 债库存（触发态快照 2026-09-28）

D-102（否）/D-104（否——fastmcp 最新 4.0.10 无 5.x 线）/D-115（是-不可即兑，无真机窗）/D-118（否-未实测）；asset_import 断言债=待裁（gate 核对时，D-133③）；D-127 已兑现（schedule 对照条件随 T-29b 闭环）。

## 措辞红线

- 归因禁写「weekly schedule 已验证」——且现已实证 schedule 链静默死亡，金丝雀词条已记。
- README 禁点竞品名/CVE 号、禁惰性安全语句；宣称=能力+证据指针。
- CONDITIONAL GO 的条件项必须有独立跟踪路径不许失联（D-133①）。
- 账本唯一真源：docs/decision-ledger.md，不从对话回忆补写。
