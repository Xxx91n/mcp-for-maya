---
generated: 2026-09-30
from_round: R37（执行窗 A 首次门检落账 + 审计返修闭环 + 三帧续期生效，覆盖 D-168~170）
ledger_head: GC-2026-09-30（账本总决策至 D-171，首检留痕补正权责分离与替代出路复验）
branch: exec/r37-gate-check-fixes（栈 qqz→xnw→unq→ynz + 审计返修提交，本地未推；堆叠于 grill/round36-v1-gate-path）
---

# 下轮任务书（rev48）

## 状态总览（首检已落账并通过审计返修）

- **首次门检状态**：已完成（时间戳 `2026-09-30T15:31Z`）。三态读数：Pass=6（框3/6/7/8/9/10）、Waived=5（框1/2/2b/4/5）、Blocked=0。
- **豁免到期处分与审计整改（V1/W1-W6）**：
  - 框1、框4、框2b/2c 重验根因未消解，同时复验替代出路（Linux WSL 42/42 + mock 790 passed 均通畅，要件4 闭环）。
  - 维护者 `@Xxx91n` 获人类用户明确赋权签署展期，生成独立签认工件 `docs/evidence/waiver-renewal-r37-signoff.md`（要件1 闭环，实现 owner=user 与 signer=@Xxx91n 权责分离）。
  - 机检清单 `gate-waiver-list-1.0.0.json` 补齐 `probes/` 相对路径（W4），2b/2c 行明确配额共享机制（W3），`renewals: 1` 写入。
  - `CHANGELOG.md [Unreleased]` 补正运行时与测试修复条目及 evidence 指针（W1）。
- **基建闭环**：fastmcp 2.14.7 兼容性断裂点（`mimeType` / `ToolResult` / `FunctionTool.fn` / dist version）全数修复，790 passed / 2 failed（框2 VP2 豁免项）/ 19 skipped；编译、打包（sdist/wheel）、进程 STDIO initialize 探活全量绿。

---

## 叙事窗 γ（锚已解锁：首检落账完成，立即开火）

- **轻叙事轨**（构建实录 / known-limitations postmortem）：
  - **只描已验证面**（D-163β① + D-149②）。
  - 核心弹药：首次 gate-check 真实读数（6 Pass / 5 Waived / 0 Blocked）、waiver 重读留痕、三帧严格续期五要件（D-168④）治理实践、fastmcp 4.x/2.14.x 现代生态适配经验。
  - 产出路径：`.scratch/r37-gate-check/narrative/` 或 docs 相关轻叙事位置。
- **重叙事轨**（HN 格式：own voice / 无最高级 / 免费试用路径 / 链 repo）：
  - 备稿**不发射**（D-163β② 锁：v1.0.0 门审通过 或 框5 像素面先到）。
  - 覆盖 D-167γ / D-163β。

---

## 执行窗 B：债消解信号响应（常备规则，D-170）

user 侧义务信号清单（到场即当场跑门检落新快照）：
- **mayapy 簇修复**或 Linux-capable/fixed-mayapy env 搭建（框1/4 | D-159）
- **框5 像素面见证**：Maya GUI 在场 30s 客户端渲染点击 或 Inspector web（D-155β；兼重叙事解锁锚）
- **第二站 VP2 插验**：第二台 Maya 2024 站在场时按 agent 预设备件跑 viewport_snapshot（D-151②）
- **Maya 2025/2026 装机**（2b/2c，最低优先——not-verified 行保留本合规，装机仅收紧宣称）
- **AC-06 残余**：Linux 宿主 Maya 内 Qt 通道（无 Linux Maya 可装=结构性等待 | D-158/D-162）

任一信号到场 → **当场跑门检落新快照**（信号须对号到行 expiry/消解锚；同窗多信号幂等去重）。覆盖 D-158/D-159/D-162/D-151②/D-155β/D-170。

---

## 执行窗 C：门审召集评估（D-170③/D-171）

- 当前快照读数：「Blocked 空 + Waived 全有效」。
- 依照 D-170③：快照已具备呈报终审条件，但当前存在 5 行豁免（框1/2/2b/4/5），由 **user 自行裁量何时召集终审（gate review）**。
- 判负三轨兜底：当期不发布+案卷落账 / re-review 凭新快照重召集 / descope 走 revise 呈报+披露（**任何时点禁静默缩门**）。覆盖 D-170/D-171。

---

## 观察窗（纯留痕）

- **10-05 双源观测**：native cron `37 6 * * 1` + Task Scheduler 周一——`gh run list` 核自触发；未观测前禁写「已验证」（D-129）；双双失效 → D-135③ 升级。
- **10-30 D-146 核销窗**：mcp.so/PulseMCP/VS Code gallery 收录态核验 + surfaces 表更新；顺带 D-147 Cline 信号。
- **awesome PR #15382 合并跟踪**：OPEN 态中——合并后 distribution-surfaces.md 对应行转已合并（D-166 承接）。
- **waiver 重读留痕**：每次 release-preflight 强制重算。

---

## 边界警示

- **执行窗≠grill 窗**：本任务书由执行窗 agent 接力；grill 大脑窗只做裁决/立法/文档。
- atomcode 件偶发跨会话污染——入账前逐字核 repo slug（正确=`Xxx91n/mcp-for-maya`）/版本号/commit 哈希。
- D-069 逐件过目授权链不变：外部可见动作发出前 user 保留最终否决点。
- 续期上限每行 2 次（第 2 次须 user 显式拍板；当前框1/4/2b均为 renewals:1）；门审后豁免车道关闭（D-168④⑤）。
- #7 关闭判据 ≡ 三态门通过（ADR-0023 R36 块已立等价关系）。

---

## Suggested skills

- `but`（GitButler）：分支/commit 管理，保持 `exec/r37-gate-check-fixes` 与主线协作，勿推勿 PR 除非用户令
- `atomcode-research`：外部渠道动态或新生态调研（串行一次一跑）
- `implement`：源码/测试/轻叙事文档写作与验证
- `handoff`：再交接时任务书续写
