# next-round.md — rev44（R33 毕：开窗令+并行道+收尾编排全立法 D-151/152/153；执行窗=T-32c 真机窗现在开 + T-30h/T-30a 同窗人工道）

生成：2026-09-29 R33 整理环节｜Spec：docs/decision-ledger.md D-151..D-153｜前档：rev43（R32 毕 0.4.1 已发）

## 环境实况（本环节核验）

- main=`31bc8bc`；栈 `grill/round33-real-maya-window`（srm=D-151、plx=D-152、xyr=D-153）未推未合；账本 153 行（138 current+15 revised）。
- Maya 2024 GUI 在机：PID 3468、`:7001`/`:50007` LISTENING、build 202302170737/24.0.0.4640——**开窗触发条件成就中**。
- v0.4.1 已在 PyPI 用户面可装（0.1.0–0.4.1 全阶梯）；server.json 已 0.4.1 待 publish。
- 本机仅 Maya 2024：框2 拆 2a（2024 勾）/2b/2c（2025/2026 = `not verified on this machine` 非勾选披露档，条件判位债）。
- #7 十框 0/10；`docs/evidence/probes/` 仅 `probe-displacement.json`；v0.4.0 body 无附录。
- 框5 三客户端二进制在机（claude.exe/codex/npx），但 `.claude.json`/`.codex/config.toml` 均无本 server MCP 注册——窗内 Step 1.2 现配现验，配不上即 conditional。
- `.scratch/` 滞留探针工件 ~8 件（shader_probe/mcp_stdio_probe/rst_fin_probe/r27 等），S2 按 D-109 元数据筛选归档。
- 今天 < 2026-10-05：双窗观测本体维持日历债，窗内只做 notify 状态核查（D-151① carve-out，结果表注记分账）。

## 任务清单

### T-32c — 真机窗执行（**开窗令已下**，D-152α） — 覆盖 D-148①/D-149/D-151/D-152/D-153/D-115 + issue #7

按 `.scratch/t32/runbook.md` rev1.1 跑 S0→S7。授权形态=事件门（D-152γ）：S0–S5 全自主（失败记录后继依赖序允许的下一项）；**红灯即停**呈报三选一（D-131 用户末行）；**脏场景守卫不可授权越过**；**GUI 道（S6）前先打招呼**；单框 30min 未收敛=视同条件判位停手呈报。Step 1 只做 notify 状态核查（10-05 本体是日历债）。逐框结果实时报；AC 卡骨架+结果表为裁决产物入 `docs/evidence/`+账本行（D-149④）；PNG ≤512KB 与 JSON 同址入 `docs/evidence/probes/`，超限走 sha256+路径+再生脚本三联指针并停手呈报再裁（D-153②）。收尾=同窗一栈三层 commit（①工件→②结果表+账本行→③issue 注记）；#7 body=S7 一次性终态更新+更新前先贴十框摘要评论（D-153③）；窗内过程性结论实时落账本行；R6 锐评对账表并入收尾账本行（D-151④）。

suggested skills：implement（逐框实跑）、domain-modeling（结果表/账本行形态）、neat-freak（收尾同步）

### T-30h — Registry publish 同窗人工道（**槽位=S3 mayapy 道期间**，D-152β） — 覆盖 D-143β/D-145β/D-146/D-150①/D-152

动作序：agent 跑 `mcp-publisher validate`（.scratch/t30/server.json=0.4.1）+ publish 前顺手核 Registry GA 态（preview 横幅摘否，影响披露措辞）→ 用户 OAuth device flow login github+publish→agent 核验 curl+registry status→**publish 日期落账本行=D-146 起算点**。硬边界：红灯裁决暂停优先于 OAuth——只在无悬停裁决的连续段启动。

suggested skills：neat-freak（发布编排+落账）

### T-30a — v0.4.0 body 附录补挂同窗人工道（**槽位=S5/S6 交界或 S7**，D-152β） — 覆盖 D-049/D-115/D-142α/D-152

备稿 `.scratch/t30/release-appendix-v040-draft.md`：用户过目批准→`gh release edit v0.4.0` 就地补挂→账本注记「D-138③ 所记 body 形态自此不再准确」→`check_release_appendix.py` 复核转绿。

suggested skills：neat-freak、handoff

### T-30f — Glama Add-Server+claim（人工门，未变） — 覆盖 D-143α/D-144③

Add MCP Server 提交 repo URL→GitHub OAuth claim。**禁启 Docker 构建面**；预期=占位+元数据所有权。

suggested skills：—（用户 OAuth）

### T-30g — awesome-mcp-servers PR（人工门，未变） — 覆盖 D-143α

照抄格式+字母序+🤖🤖🤖 fast-track；行稿在 `.scratch/t30/`；不押时点。

suggested skills：—

## 结转挂账（时点/事件驱动）

- **D-146 核销窗**：Registry publish 落账日起算 30 天一次性核销 mcp.so/PulseMCP/VS Code gallery 收录态（按 distribution-surfaces.md 三态落账）；D-147 Cline 信号核验同窗顺带。
- **2026-10-05 双窗观测**（D-127/D-137）：日历债独立存续；窗内 Step 1 仅做 notify 状态核查（D-151①），观测本体不并入、勿为等观测拖窗。
- **框6 Linux CI 复核面**：窗内登记债，收尾时立独立 D 号+用户确认（D-149①/append-only 纪律）。
- **大二进制录屏归宿**：≤512KB 规则只管 PNG 级；录屏类超限件出现即停呈报，触发 D-149 登记的再裁。
- **R6 锐评对账表**：窗收尾段产一张账本行（循 D-109 形态）——⑤证据回填=窗内产出、P1 补挂=T-30a、P2/P3/①-④已落。
- **notify 红路径**：观测项挂起，无自然红不制造。
- **叙事传播**（D-143γ）：备稿不发，v1.0.0+#7 全绿后启用。
- **下一轮候选=C**：v1.0.0 冲刺编排轮——#7 窗结果产出后届时做（填证据非改判据，D-133③）。

## 措辞红线

- 验证宣称=声明集即已验证集：2b/2c 显式 `not verified on this machine` 非勾选，禁冒充（D-149②/D-109④）。
- 附录=装船时点快照+声明性指针，禁计数型/tracker-dump；措辞过 D-132 句式。
- issue #7 body=操作副本（D-130）：终态一次更新+评论过程记录，禁逐框改写。
- 账本唯一真源 docs/decision-ledger.md；runbook=操作档非裁决源。
