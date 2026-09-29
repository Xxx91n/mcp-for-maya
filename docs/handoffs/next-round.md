# next-round.md — rev42（R32 毕：v1.0.0 硬项清账轮立法完成 D-148..D-150；执行窗=runbook 起草 + 0.4.1 发版 + 真机窗 + T-30 人工门并行）

生成：2026-09-29 R32 整理环节｜Spec：docs/decision-ledger.md D-148..D-150｜前档：rev41（R31 收录面三态立法）

## 环境实况（本环节核验）

- main=db037c9（PR #52 已合并 R30+R31 全栈：T-31a/b 落地、D-139 双车道复核销账）；账本 150 行（135 current+15 revised）；R32 账本栈 `grill/round32-v1-gate-window`（uvr→qzy→svx）未推未合。
- 本机 Maya=**仅 2024**（`D:\maya2024\Maya2024\`，mayapy 3.10.8 实测可用）——#7 框2 的 2025/2026 版本矩阵走 D-049 披露档+条件判位（D-149②）。
- #7 十框 0/10；v0.4.0 body 仍无披露附录（T-30a 待人工门）；T-30i 已完成（D-139 销账）；mayapy env-broken→GUI 通道。
- ADR-0023 已含 R32 增补块（D-146 锚=0.4.1-publish、tag/Release 前向立法、0.4.1 两行 preflight）；CONTEXT 棘爪/发布编排纪律两词条已补注记。

## 任务清单

### T-32a — 真机窗 runbook 起草 — 覆盖 D-148①/D-149

落 `.scratch/t32/runbook.md`（操作档非耐久件不入仓）。骨架：①**三车道**——桌面道（框7 静态签名审计+框8 回灌 diff/allowlist 下游）/mayapy 道（框1,4,8,10；框10 于 maya.standalone 实证，standalone/GUI 差异嫌疑走 AC 卡 escape hatch 升级 GUI 道）/GUI 道（框2,3,5,6,9；框6 拆=Windows 面入道+Linux CI 面另立登记债届时独立 D 号+用户确认）；②**逐框 AC 卡**按框写不按车道写（车道进 scope 字段）：scope 固定行（Maya 版本/build/通道/端口态）+动作+预期读回物（scene_assert/JSONL 审计行/截图——VERIFY 步产物非终点态）+工件落点 docs/evidence/probes/（provenance+claim_boundary，D-109）；③**跑序**=环境快照→观测窗只读先行（10-05 双窗与 notify 观测面）→D-115 补采→十框依赖序→andon 收尾；④**失败框三选一**（approved/conditional 带 owner+期限/rejected）映 D-131 用户末行，ship-with-known-issue 走 D-049/D-142α 披露链；⑤末节=D-146 预签页（逐句引 D-145β+D-150① 锚）。**AC 卡骨架与逐框结果表=裁决产物**，窗收尾时入 docs/evidence/+账本行（D-041④ 结论进 docs 边界）；客户端预检（框5 须 MCP Inspector+Claude Code+Codex 在机）列入 runbook readiness 节。

suggested skills：handoff（runbook 即常驻操作书）、domain-modeling（AC 卡字段与词条对齐）

### T-32b — 0.4.1 patch 发版窗 — 覆盖 D-150①③

序：CHANGELOG [0.4.1] 节（delta=docs+packaging 元数据，叙事界如实）→**人工 `git tag -a` 建锚**（D-150③ 首个 annotated tag）+push tag→release.yml 自跑（test→build→publish，trusted publisher）→**跳 GH Release**（D-084 判别）→preflight 两行（ADR-0023 R32 增补）：PyPI 双车道复核见 0.4.1 带时间戳+0.4.1 wheel README 含 mcp-name 行。tag 推送=用户人工门。发完即解锁 T-30h。

suggested skills：neat-freak（发布编排纪律嵌套）、but（分支/提交面）

### T-32c — 真机窗执行（事件驱动=Maya 开机触发，不裁日历日） — 覆盖 D-148①/D-149/D-115

用户开 Maya 2024 GUI 即触发：按 T-32a runbook 逐框执行→工件循 D-109 入 docs/evidence/probes/→逐框结果表+AC 卡骨架入仓→#7 body 逐框打勾（2025/26 面显式 not-verified 非勾选）→失败框三选一呈报用户（D-131 末行）。观测义务与验证义务分账不混装；观测步必先于变更步。

suggested skills：implement（工具面实跑）、domain-modeling（结果表形态）

### T-30a — v0.4.0 Release body 补挂披露附录（人工门，未变） — 覆盖 D-049/D-115/D-142α

备稿在 .scratch/t30/release-appendix-v040-draft.md；序：用户过目批准→gh release edit v0.4.0 就地补挂→账本注记「D-138③ 所记 body 形态自此不再准确」→check_release_appendix.py 复核转绿。

suggested skills：handoff、neat-freak

### T-30f — Glama Add-Server+claim（人工门，未变） — 覆盖 D-143α/D-144③

Add MCP Server 提交 repo URL→GitHub OAuth claim。**禁启 Docker 构建面**；预期=占位+元数据所有权非分发流量；claim 后改元数据须重走 claim flow。

suggested skills：—（用户 OAuth 人工门）

### T-30g — awesome-mcp-servers PR（人工门，未变） — 覆盖 D-143α

照抄格式+字母序+🤖🤖🤖 fast-track；行稿在 .scratch/t30/；不押时点。

suggested skills：—（用户推 fork 或授权）

### T-30h — server.json+Registry publish（**锚前移：绑 0.4.1 发版窗**，D-150①） — 覆盖 D-143β/D-145

草稿在 .scratch/t30/server.json；动作序：version 改 0.4.1（须与 PyPI 精确一致）→mcp-publisher validate→人工门 login github+publish→核验 curl+registry status；**publish 完成即刻账本落 publish 日期=D-146 起算点**。

suggested skills：neat-freak（发布编排纪律嵌套）

## 结转挂账（非本轮新增，时点/事件驱动）

- **D-146 核销窗**：Registry publish（预期=0.4.1 窗）后 30 天；锚=publish 落账日非发版日；D-147 Cline 信号核验同窗顺带。
- **2026-10-05 双窗观测**（D-127/D-137）：并入真机窗观测先行段（若 Maya 窗晚于该日则观测面独立先记，勿为等窗而拖）；weekly 探针首跑仍未发生持续观察。
- **框6 Linux CI 复核面**：登记债届时立独立 D 号+用户确认（append-only 纪律），不占人工窗。
- **大二进制证据件归宿**（D-149 登记的开放立法点）：录屏类工件若被要求入仓届时再裁，不预裁。
- **notify 红路径**：观测项挂起，无自然红不制造。
- **叙事传播**（D-143γ）：备稿不发，v1.0.0+#7 全绿后启用；收录轨兜底条款不豁免本门。
- **叙事轨备选面**：r/Maya、r/vfx、TA 论坛=高密度叙事渠道，v1.0.0 叙事轮调研面。
- **mypy-baseline/tag 卫生注记已落地**（CONTEXT 棘爪+发布编排纪律词条、ADR-0023 R32 块）——本轮整理产物，勿重复劳动。

## 措辞红线

- 收录轨价值=可发现性兜底非拉新主力；渠道处置先落账本再改表；表外渠道默认被动观察。
- 附录=装船时点快照+声明性指针，禁计数型/tracker-dump；措辞过 D-132 句式（4-Beta 禁 stable）。
- 验证宣称=声明集即已验证集（D-149②）：未测版本显式 not-verified 不冒充；无工件 verified-live 禁声称（D-109④）。
- 账本唯一真源 docs/decision-ledger.md；ADR-0023 增补块为操作提醒抄写载体。
