# next-round.md — rev43（R32 毕：T-32a runbook 审计闭环 + T-32b 0.4.1 patch 发版完成；执行窗=T-30h Registry publish + T-32c 真机窗执行 + T-30 人工门并行）

生成：2026-09-29 R32 整理与发版闭环环节｜Spec：docs/decision-ledger.md D-148..D-150｜前档：rev42（R32 启动与任务书）

## 环境实况（本环节核验）

- main 分支已合并 R32 账本与发版栈：T-32a（runbook rev 1.1 独立双轴审计闭环）与 T-32b（0.4.1 patch 发版包落位、annotated tag `v0.4.1` 已推）；账本 150 行（135 current+15 revised）。
- 0.4.1 发版窗完成：`CHANGELOG.md [0.4.1]` 携带全量可执行证据指针（D-082⑦）、wheel README 含 `<!-- mcp-name: -->` 标记（D-143）、annotated tag `v0.4.1` 已创建并推送激活 release.yml 发布管线。
- 本机 Maya=**仅 2024**（`D:\maya2024\Maya2024\`，mayapy 3.10.8 实测可用，GUI 端口 7001 监听中）——#7 框2 的 2025/2026 版本矩阵走 D-049 披露档+条件判位（D-149②）。
- #7 十框 0/10 待实跑（T-32c 窗就绪）；v0.4.0 body 仍无披露附录（T-30a 待人工门）；T-30i 已完成（D-139 销账）。
- ADR-0023 已含 R32 增补块（D-146 锚=0.4.1-publish、tag/Release 前向立法、0.4.1 两行 preflight）；CONTEXT 棘爪/发布编排纪律两词条已补注记。

## 任务清单

### T-30h — server.json+Registry publish（**0.4.1 发版完成即刻解锁**，D-150①） — 覆盖 D-143β/D-145

草稿在 `.scratch/t30/server.json`（版本已同步 0.4.1）；动作序：`mcp-publisher validate`→人工门 login github+publish→核验 curl+registry status；**publish 完成即刻账本落 publish 日期=D-146 起算点（30 天核销倒计时启动）**。

suggested skills：neat-freak（发布编排纪律嵌套）

### T-32c — 真机窗执行（事件驱动=Maya 开机触发，就绪待跑） — 覆盖 D-148①/D-149/D-115

当前环境 Maya 2024 GUI（PID 3468，端口 7001）实测可用：按 T-32a runbook（rev 1.1）逐框执行→工件循 D-109 入 `docs/evidence/probes/`→逐框结果表+AC 卡骨架入仓→#7 body 逐框打勾（2025/26 面显式 not-verified 非勾选）→失败框三选一呈报用户（D-131 末行）。观测义务与验证义务分账不混装；观测步必先于变更步。

suggested skills：implement（工具面实跑）、domain-modeling（结果表形态）

### T-30a — v0.4.0 Release body 补挂披露附录（人工门，未变） — 覆盖 D-049/D-115/D-142α

备稿在 `.scratch/t30/release-appendix-v040-draft.md`；序：用户过目批准→gh release edit v0.4.0 就地补挂→账本注记「D-138③ 所记 body 形态自此不再准确」→`check_release_appendix.py` 复核转绿。

suggested skills：handoff、neat-freak

### T-30f — Glama Add-Server+claim（人工门，未变） — 覆盖 D-143α/D-144③

Add MCP Server 提交 repo URL→GitHub OAuth claim。**禁启 Docker 构建面**；预期=占位+元数据所有权非分发流量；claim 后改元数据须重走 claim flow。

suggested skills：—（用户 OAuth 人工门）

### T-30g — awesome-mcp-servers PR（人工门，未变） — 覆盖 D-143α

照抄格式+字母序+🤖🤖🤖 fast-track；行稿在 `.scratch/t30/`；不押时点。

suggested skills：—（用户推 fork 或授权）

## 结转挂账（非本轮新增，时点/事件驱动）

- **D-146 核销窗**：Registry publish（0.4.1 完成后即刻落地）后 30 天；锚=publish 落账日非发版日；D-147 Cline 信号核验同窗顺带。
- **2026-10-05 双窗观测**（D-127/D-137）：并入真机窗观测先行段（若 Maya 窗晚于该日则观测面独立先记，勿为等窗而拖）；weekly 探针首跑仍未发生持续观察。
- **框6 Linux CI 复核面**：登记债届时立独立 D 号+用户确认（append-only 纪律），不占人工窗。
- **大二进制证据件归宿**（D-149 登记的开放立法点）：录屏类工件若被要求入仓届时再裁，不预裁。
- **notify 红路径**：观测项挂起，无自然红不制造。
- **叙事传播**（D-143γ）：备稿不发，v1.0.0+#7 全绿后启用；收录轨兜底条款不豁免本门。
- **叙事轨备选面**：r/Maya、r/vfx、TA 论坛=高密度叙事渠道，v1.0.0 叙事轮调研面。
- **mypy-baseline/tag 卫生注记已落地**（CONTEXT 棘爪+发布编排纪律词条、ADR-0023 R32 块）——勿重复劳动。

## 措辞红线

- 收录轨价值=可发现性兜底非拉新主力；渠道处置先落账本再改表；表外渠道默认被动观察。
- 附录=装船时点快照+声明性指针，禁计数型/tracker-dump；措辞过 D-132 句式（4-Beta 禁 stable）。
- 验证宣称=声明集即已验证集（D-149②）：未测版本显式 not-verified 不冒充；无工件 verified-live 禁声称（D-109④）。
- 账本唯一真源 docs/decision-ledger.md；ADR-0023 增补块为操作提醒抄写载体。
