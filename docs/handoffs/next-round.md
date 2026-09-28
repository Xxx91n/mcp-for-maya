# next-round.md — rev39（R29 毕：0.4.0 已发布+gate 已核 D-138；PyPI 索引注册回归中=D-139；仍开=真机窗/10-05 双窗/notify 红路径）

生成：2026-09-28 T-29a..c 执行后｜Spec：docs/decision-ledger.md D-133..D-137｜执行报告：.scratch/t29/reports/2026-09-28-report.md（逐条命令+输出摘要）

## 环境实况（本环节核验 ~09:40 UTC）

- main=b977908（PR #44 merge commit，09:08:32Z）；grill/round29-release-window 栈已整合移除；**v0.4.0 tag 已推**（轻量 tag→b977908，D-136 merge-then-tag 序，is-ancestor 已验）。
- release.yml run 36401741670 **全绿**：pytest×4（uv sync --frozen 锁定集）+build+publish；upload 200×2 + PEP 740 attestations（sdist b359c282…/wheel 66773559…）。
- **PyPI 维护窗干扰**：status.python.org=Service Under Maintenance；0.4.0 JSON per-version 就位（4-Beta/>=3.10/desc 23549c），直连 wheel 冒烟绿（import+入口点双验）；canonical 补验上传时点曾闭环（页面 200+索引路径 70 包装入+冒烟绿），后复核回归=D-139（索引注册丢失，latest=0.3.0，工件完好，等维护收敛）。
- T-29b 已落地（D-137）：Task Scheduler mcp-for-maya-drift-canary（周一 14:40 +08=06:40 UTC，gh workflow run ci.yml）端到端实证通；ci.yml disable/enable 重注册完成（state=active）。dispatch run 36401533215 被 main-push 并发组 supersede 取消=正常并发语义非失败。
- T-29c 已落地：.scratch/maya-mcp-grill/decision-ledger.md 顶部 SUPERSEDED 横幅留档；P-01 校正命令已用于 T-29 报告。
- closeout 分支 grill/round29-release-closeout：已合 main（PR #45，merge a0a088d）；后续文档修正批=PR #46(f9e732f)/#48(5c5a165)/#49(cdc5cb2) 均已合。
- GH Release：**已建**（go-signal ②=「ok」后创建；v0.4.0 非 draft，body=103 行逐字）。

## 批次序与规则（发布编排纪律词条全约束）

序=T-29a✅→T-29b✅→T-29c✅→T-29d（gate 核对）。
**andon 三段**（D-133②）：PyPI 推送=不可回改点已过且成功——其后一切瑕疵走 0.4.1 patch+waiver 带 expiry；中止即 incident 入账。
go-signal ①②均兑现：tag push 后 release.yml 全绿→GH Release 已建。
**冻结语义**：CHANGELOG 节==tag diff（D-107④）。

## 任务清单

### T-29a — 0.4.0 发布执行窗 — 全毕（tag/CI/PyPI 上传/GH Release 齐）

已完成：release commit 70c96c7→PR #44（CI 六格全绿）→merge b977908→tag v0.4.0→release.yml 全绿→PyPI 文件+attestations 落地。
GH Release 已建（v0.4.0 非 draft，body=103 行逐字）；PyPI canonical=曾成立后回归（D-139 详录，等维护收敛复核）

suggested skills：neat-freak（补验逐项挂证据）

### T-29b — canary 外部调度 — 已落地，下窗核验挂 2026-10-05

下窗双源观测：native cron 37 6 * * 1 是否自愈（D 重注册之效）+ scheduler 14:40 +08 自触发；任一/双通道出 run 即记归因，闭环 D-127 对照条件。若双双静默→incident 行+升第三载体。

suggested skills：neat-freak（归因入账）

### T-29c — 文档顺手批 — 完成

（superseded 横幅+P-01 校正均已兑现，见 T-29 报告 22-23 条）

### T-29d — 0.4.0 发布后 gate 核对 — 核对已执行，产出=账本 D-138

核对产出=D-138 账本行（逐项证据指针已挂）。机器可验项全绿：节==tag diff/版本阶梯/GH Release/milestone/公 API 声明/**D-036⑤ 已执行**（main 保护=ci strict+禁 force-push/删除）/**asset_import 断言债=立即修已落地**（PR #47，path_escape belt+回归测试）/一次性过堂行在档。T-24 mayapy=env-broken 复核实锤（DLL init failed→AV）→D-049 披露义务随 v1.0.0 窗结转。
**仍开（结转项）**：#7 十框 0/10（真机窗）/D-115 同窗/D-127=2026-10-05 双窗观测/notify 红路径观测（无自然红挂起）。go/no-go 末行=用户拍板。

suggested skills：neat-freak（逐项证据指针核验）、domain-modeling（债裁决措辞）

## 债库存（触发态快照 2026-09-28 ~09:40 UTC）

D-102（否）/D-104（否——fastmcp 最新 4.0.10 无 5.x 线）/D-115（是-不可即兑，无真机窗）/D-118（否-未实测）；asset_import 断言债=**已偿还**（D-138⑧，PR #47 belt+回归测试，非挂账）；D-127=载体已落地，闭环条件=2026-10-05 下窗双源观测；D-036⑤=已执行（分支保护开启）。

## 措辞红线

- 归因禁写「weekly schedule 已验证」——schedule 链静默死亡已实证（D-129），新载体 A+D 已落地（D-137），自愈与否待 10-05 窗核验。
- PyPI 验证状态禁写「已验证」——直连冒烟绿≠canonical 索引绿；页面 503=维护窗，补验挂起如实标。
- README 禁点竞品名/CVE 号、禁惰性安全语句；宣称=能力+证据指针。
- CONDITIONAL GO 的条件项必须有独立跟踪路径不许失联（D-133①）。
- 账本唯一真源：docs/decision-ledger.md，不从对话回忆补写。
