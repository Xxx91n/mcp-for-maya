---
generated: 2026-09-30
from_round: R36（v1.0.0 门两事件制+豁免生命周期立法，D-167~171）
ledger_head: D-171
branch: grill/round36-v1-gate-path（栈 zsr→zzz→vns→yvz→kqk，本地未推；锚定 exec/round35-residuals）
---

# 下轮任务书（rev47）

## 执行窗 A：首次门检（D-169 立法——开场即跑，非可选）

1. **跑 gate-check**：重读 `docs/evidence/gate-waiver-list-1.0.0.json` + 逐行三态重算（当前 6 pass/5 waived）。
2. **到期四行处分**（框1/4/2b/2c，expiry=首次门检触发）：逐行 reason 重验（mayapy 仍 0xC0000005？2025/26 仍未装？Linux env 替代出路仍通？）→
   - 根因未变未消解 → **续期 renewals:1**：JSON 行内 `renewals:1` + 新 expiry=「下次 gate-check 或 gate review 先到为准」+ `renewed_by: "user @<date>"` 重签（须呈报 user 逐行签认，owner 外门权者要件 D-168④）
   - 根因已消解 → pass 挂证物；恶化 → Blocked 呈报
   - **首检不预判**：只落当时真实读数
3. **落账**：账本事件行（时间戳+逐行三态+到期处分+证据指针，D-164γ 同构）+ JSON 就地更新。
   覆盖 D-168/D-169/D-170 | skills：无（纯工件操作+账本行）

## 执行窗 B：债消解信号响应（常备规则，D-170）

user 侧义务清单（owner=user/agent 备件）：
- **mayapy 簇修复**或 Linux-capable/fixed-mayapy env 搭建（框1/4 | D-159）
- **框5 像素面见证**：Maya GUI 在场 30s 客户端渲染点击 或 Inspector web（D-155β；兼重叙事解锁锚）
- **第二站 VP2 插验**：第二台 Maya 2024 站在场时按 agent 预设备件跑 viewport_snapshot（D-151②）
- **Maya 2025/2026 装机**（2b/2c，最低优先——not-verified 行保留本合规，装机仅收紧宣称）
- **AC-06 残余**：Linux 宿主 Maya 内 Qt 通道（无 Linux Maya 可装=结构性等待 | D-158/D-162）
任一信号到场→**当场跑门检落新快照**（信号须对号到行 expiry/消解锚；同窗多信号幂等去重）。覆盖 D-158/D-159/D-162/D-151②/D-155β/D-170

## 执行窗 C：门审召集（D-170③/D-171——条件达成才动）

快照检出「Blocked 空+Waived 全有效」→ agent 以快照工件为凭据呈报 → **user 召集终审**。判负时按三轨：当期不发布+案卷落账 / re-review 凭新快照重召集 / descope 走 revise 呈报+披露（**任何时点禁静默缩门**）。覆盖 D-170/D-171

## 叙事窗 γ（锚已前移：首检落账后即可开火）

轻叙事轨（构建实录/known-limitations postmortem）——**只描已验证面**（D-163β①+D-149②）；首检产出的新鲜工件（waiver 重读留痕/三态重算）=最佳弹药，先跑 A 窗后写稿。重叙事稿（HN 格式：own voice/无最高级/免费试用路径/链 repo）可备**不发射**（D-163β② 锁=v1.0.0 或框5 像素面先到）。覆盖 D-167γ/D-163β

## 观察窗（纯留痕）

- **10-05 双源观测**：native cron `37 6 * * 1` + Task Scheduler 周一——`gh run list` 核自触发；未观测前禁写「已验证」（D-129）；双双失效→D-135③ 升级
- **10-30 D-146 核销窗**：mcp.so/PulseMCP/VS Code gallery 收录态核验+surfaces 表更新；顺带 D-147 Cline 信号
- **awesome PR #15382 合并跟踪**：OPEN 态中——合并后 distribution-surfaces.md 对应行转已合并（D-166 承接）
- **waiver 重读留痕**：已并入执行窗 A/C（每次 preflight 强制）

## 边界警示

- **执行窗≠grill 窗**：本任务书由执行窗 agent 接力；grill 大脑窗只做裁决/立法/文档
- atomcode 件偶发跨会话污染——入账前逐字核 repo slug（正确=`Xxx91n/mcp-for-maya`）/版本号/commit 哈希
- D-069 逐件过目授权链不变：外部可见动作发出前 user 保留最终否决点
- 续期上限每行 2 次（第 2 次须 user 显式拍板）；门审后豁免车道关闭（D-168④⑤）
- #7 关闭判据≡三态门通过（ADR-0023 R36 块已立等价关系）；本轮未裁 #7 关闭动作

## Suggested skills

- `but`（GitButler）：分支/commit 管理，勿推勿 PR 除非用户令
- `atomcode-research`：外部渠道动态或新生态调研（串行一次一跑）
- `domain-modeling`：CONTEXT 词条维护（新词落词不过夜）
- `handoff`：再交接时任务书续写
- `implement`：若任务扩展到源码/测试改动
