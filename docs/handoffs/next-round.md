# next-round.md — rev38（R29 收尾：0.4.0 已发布，gate 核对+Release 页待决）

生成：2026-09-28 T-29a..c 执行后｜Spec：docs/decision-ledger.md D-133..D-137｜执行报告：.scratch/t29/reports/2026-09-28-report.md（逐条命令+输出摘要）

## 环境实况（本环节核验 ~09:40 UTC）

- main=b977908（PR #44 merge commit，09:08:32Z）；grill/round29-release-window 栈已整合移除；**v0.4.0 tag 已推**（轻量 tag→b977908，D-136 merge-then-tag 序，is-ancestor 已验）。
- release.yml run 36401741670 **全绿**：pytest×4（uv sync --frozen 锁定集）+build+publish；upload 200×2 + PEP 740 attestations（sdist b359c282…/wheel 66773559…）。
- **PyPI 维护窗干扰**：status.python.org=Service Under Maintenance；0.4.0 JSON per-version 就位（4-Beta/>=3.10/desc 23549c），直连 wheel 冒烟绿（import+入口点双验）；维护窗收敛后 canonical 补验已闭环：版本页 200 + `pip install mcp-for-maya==0.4.0` 索引路径 70 包闭包装入临时 venv + import/--help 绿（D-135① 全项兑现）。
- T-29b 已落地（D-137）：Task Scheduler mcp-for-maya-drift-canary（周一 14:40 +08=06:40 UTC，gh workflow run ci.yml）端到端实证通；ci.yml disable/enable 重注册完成（state=active）。dispatch run 36401533215 被 main-push 并发组 supersede 取消=正常并发语义非失败。
- T-29c 已落地：.scratch/maya-mcp-grill/decision-ledger.md 顶部 SUPERSEDED 横幅留档；P-01 校正命令已用于 T-29 报告。
- closeout 分支 grill/round29-release-closeout：D-136/D-137 账本行+本任务书 rev38（commit svn+本笔），待 PR 合 main。
- GH Release：**未建**——body 已起草（# v0.4.0+[0.4.0] 节 103 行逐字），等 go-signal ②。

## 批次序与规则（发布编排纪律词条全约束）

序=T-29a✅→T-29b✅→T-29c✅→T-29d（gate 核对）。
**andon 三段**（D-133②）：PyPI 推送=不可回改点已过且成功——其后一切瑕疵走 0.4.1 patch+waiver 带 expiry；中止即 incident 入账。
**go-signal ②**（D-134 α）：GH Release 创建前呈 body→点头→建 minor 档（D-084/D-108）。
**冻结语义**：CHANGELOG 节==tag diff（D-107④）。

## 任务清单

### T-29a — 0.4.0 发布执行窗 — ⑤完成，⑥待 go-signal ②

已完成：release commit 70c96c7→PR #44（CI 六格全绿）→merge b977908→tag v0.4.0→release.yml 全绿→PyPI 文件+attestations 落地。
GH Release 已建（v0.4.0 非 draft，body=103 行逐字）；PyPI canonical 验证已闭环——T-29a 全部完成。

suggested skills：neat-freak（补验逐项挂证据）

### T-29b — canary 外部调度 — 已落地，下窗核验挂 2026-10-05

下窗双源观测：native cron 37 6 * * 1 是否自愈（D 重注册之效）+ scheduler 14:40 +08 自触发；任一/双通道出 run 即记归因，闭环 D-127 对照条件。若双双静默→incident 行+升第三载体。

suggested skills：neat-freak（归因入账）

### T-29c — 文档顺手批 — 完成

（superseded 横幅+P-01 校正均已兑现，见 T-29 报告 22-23 条）

### T-29d — 0.4.0 发布后 gate 核对（D-131 清单唯一载体=ADR-0023 R28 增补块）

触发点（D-135③）：β 观测已闭环（静默归因入账）+PyPI 冒烟全项绿——**核对已可开**。议程=ADR-0023 增补块逐项挂证据指针：#7 十框全绿（用户真机窗）/D-115 补采同窗/D-127 复核（含 T-29b 2026-10-05 下窗）/节==tag diff（v0.4.0 节↔b977908 diff）/版本阶梯（0.4.0 落地，latest 索引待传播确认）/GH Release 存在性/milestone 归置/公 API 声明（README 冻结段已在档）/D-036⑤ 分支保护 404=硬项或豁免裁决/T-24 mayapy 冒烟或 D-049 披露/**asset_import resolve().startswith 断言债裁**（D-133③）/一次性过堂行已完成（docs/evidence/release-surface-review-2026-09-28.md）/notify 红路径观测/裁出 D-102/D-104/D-118。末行 go/no-go=用户拍板。

suggested skills：neat-freak（逐项证据指针核验）、domain-modeling（债裁决措辞）

## 债库存（触发态快照 2026-09-28 ~09:40 UTC）

D-102（否）/D-104（否——fastmcp 最新 4.0.10 无 5.x 线）/D-115（是-不可即兑，无真机窗）/D-118（否-未实测）；asset_import 断言债=待裁（T-29d gate）；D-127=载体已落地，闭环条件=2026-10-05 下窗双源观测。

## 措辞红线

- 归因禁写「weekly schedule 已验证」——schedule 链静默死亡已实证（D-129），新载体 A+D 已落地（D-137），自愈与否待 10-05 窗核验。
- PyPI 验证状态禁写「已验证」——直连冒烟绿≠canonical 索引绿；页面 503=维护窗，补验挂起如实标。
- README 禁点竞品名/CVE 号、禁惰性安全语句；宣称=能力+证据指针。
- CONDITIONAL GO 的条件项必须有独立跟踪路径不许失联（D-133①）。
- 账本唯一真源：docs/decision-ledger.md，不从对话回忆补写。
