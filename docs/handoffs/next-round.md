---
generated: 2026-09-30
from_round: R35（R6 锐评核销核验+D-164/165 残余外挂面裁决）
ledger_head: D-165
branch: grill/round35-r6-residuals（栈 ppr→xto，未推未合；上轮 r34 两分支已 integrated）
---

# 下轮任务书

## 收录外挂执行窗（D-164α/D-165 已立法+内容已定稿——纯执行）

**顺序：①awesome PR（agent 全程可做）→ ②Glama claim（须用户 OAuth 在场）**

1. **awesome-mcp-servers PR**（T-30g）：fork punkpeye/awesome-mcp-servers → 行稿按字母序插入「mcp-for-maya」位置段：
   `- [Xxx91n/mcp-for-maya](https://github.com/Xxx91n/mcp-for-maya) 🐍 🏠 🪟 🐧 - MCP server giving AI agents spatial awareness inside Autodesk Maya — scene inspection, deterministic audit, checkpoint/rollback transactional safety, screenshot-based visual verification (Beta).`
   PR title 带 `🤖🤖🤖` fast-track 前缀；PR body 按对方模板 checklist 逐项打勾（link 活/字母序/格式/描述非空泛）。发出前用户保留最终否决点（D-069）。覆盖 D-164α+D-165αβ | skills：gitbutler（fork/branch/commit via gh）、任一 web 工具核目标仓现行行格式

2. **Glama claim**（T-30f）：用户 GitHub OAuth 在场时——glama.ai claim flow 直连个人账号（免 glama.json）；描述文本终稿：`MCP server for Autodesk Maya — scene inspection, deterministic audit, checkpoint/rollback transactional safety, screenshot-based visual verification. Local stdio; verified on Windows with Maya 2024; Linux host untested (Beta).`；**禁启 Docker 构建/健康检查面**（构建失败=profile 保留+分发隐藏=D-144③ 占位预期形态，勿设防措辞勿点 Configure Docker image）。claim 后把收录态+探针实况落 distribution-surfaces.md。覆盖 D-164α+D-165γ+D-144③ | skills：任一浏览器/文档工具

3. **distribution-surfaces.md 同步**：两件落地后更新对应行（Glama 已收录戳/awesome PR 链接+合并态）。覆盖 D-145α

## 观察窗（零新立法，纯留痕）

- **10-05 双源观测**（γ①）：native cron `37 6 * * 1` + Task Scheduler 06:40 UTC 周一两载体——2026-10-05 后查 `gh run list` 是否自触发；结果落账本行；native cron 未观测前禁写「已验证 weekly schedule」（D-129）；scheduler 也失效→D-135③ 升级条款
- **D-146 核销窗**（γ②）：**2026-10-30** 当日核验 mcp.so/PulseMCP/VS Code gallery 收录态（Glama 官方宣称分钟级同步、mcp.so 人工提交面不查）；顺带 D-147 Cline 信号同窗；结果落账+surfaces 表更新；PulseMCP 暂停提交单源注记届时先复核
- **waiver 清单重读留痕**（γ③）：每次 release-preflight 重读 `docs/evidence/gate-waiver-list-1.0.0.json` 并落账本行作兑现凭证；frame5 expiry=client-UI 渲染见证或 gate review 先到；任一行到期未消解→fail-closed 判 Blocked

## 帧债继承（rev45 未变项）

- 框5 像素面补证（Maya GUI 在场时 30s 点击/Inspector web 或 claude TUI）| D-155β
- 框2 判定复核窗（第二台 2024 站在场即插验 VP2）| D-151②
- AC-06 残余：Linux 宿主 Maya 内 Qt | D-158/D-162
- AC-01 runbook 修订 | D-159 | mayapy 簇 | #53 VP2
- 轻叙事轨（D-163β①已解锁）：构建实录/known-limitations postmortem 备稿——只描已验证面

## 边界警示

- atomcode 件会偶发跨会话污染（本轮误植 `Euiop1/maya-mcp-server` slug）——**入账前逐字核 repo slug/版本号/commit 哈希**
- awesome PR 与 Glama claim 已授权**内容**，发出动作仍需用户最终过目（D-069 逐件制）
- 叙事轨仍锁：v1.0.0 或框5 像素面关闭先到为准（D-163β②）
