# next-round.md — rev35（R27 兑现批：R5 锐评裁决落地）

生成：2026-09-27 R27 grill 整理环节｜Spec：docs/decision-ledger.md D-121..D-126（D-038→D-124、D-116→D-122 已 revised 留痕）｜前置调研：R27-Q1..Q6 经 atomcode 派发+ctx 索引（ctx_search source=atomcode-qN 可取全文）｜题面档：.scratch/t27/questions/q1..q6-*.md

## 环境实况（本环节核验）

- main=a45f3e0；本分支 grill/round27-review5-adjudication 文档栈（账本+CONTEXT+本任务书）。
- 0.4.0 在飞（v0.3.0 已发：tag 977414b/Release/PyPI 全绿）；25 工具。
- 待删对象仍树内：src/maya_mcp_server/aesthetic_engine.py（1420 行零生产引用）+tests/test_aesthetic_engine.py（58 测试/720 行）；巨石 maya_scene_module.py 现 4589 行（D-004 时代 3564→+1025=失速实证）。
- ci.yml：lint job（ruff 预算+README 骨架+资产守卫步骤）、test 4 格矩阵、drift job（weekly 周一 06:37 UTC，schedule+dispatch 触发，现仅 contents:read）。
- ADR-0023 发布清单=「R26 增补」块（含「节内容==tag diff」硬核对）；AGENTS.md:73 陈旧计数「ADR-0001..0024」（实已 0027，T-27a 顺手修）。
- CONTEXT.md 本轮整理窗已落两处词条修订：触发条件债三档纪律句（D-122 β-ⅰ）+棘爪「高水位退化」失效模式名（D-125 结晶）。

## 批次序与规则（D-126）

序=批 1（T-27a 守卫三件套合 PR，3 commits 分立）→批 2（T-27b 代码两刀单 PR，D-122→D-124 风险递增序=先修灶后删灶）。
**andon**：批 1 红=守卫自身 bug 暂停批 2 开工（守卫语义未验证期不落删变更）；批 2 红先查 D-124（唯一运行时语义变更）。
**回滚边界**：批 1 逐 commit revert；批 2 两 commit 各自独立 revert——D-124 revert 即恢复删除（期权召回=git log -G aesthetic_engine，D-124 书面化条款）；D-122 revert 独立。
**冻结语义**：D-125 巨石预算值=批 1 落地时实测行数（非 grill 时点 4589——竞态消解项）。
两批均落 0.4.0 面。

## 任务清单

### T-27a — R27 批 1 守卫三件套，合单 PR commit 分立（D-121+D-123+D-125）

**commit ① D-121 工具计数闸**：
- CHANGELOG.md:51「…23 tools total」→「25 tools total」（节=发布物最终态陈述；:452 [0.1.0]「20 tools」历史断面不动）。
- 新增 .github/scripts/check_tool_count_claims.py（纯 stdlib+::error::file:line+docstring 挂 D-121）：源头=len(TOOL_ANNOTATIONS)（pipeline.py 单一真源）；断言面=活断面四文件 README.md/README.zh-CN.md/AGENTS.md/docs/threat-model.md+CHANGELOG **最末 release 节**（历史节豁免=规则写法只有最末节受断言）；声称形态 `(\d+) tools? (total|in total)`/`all (\d+) tools`；须区分 AGENTS.md 按文件分列计数（合法异值非 total 语境）。
- ci.yml lint job 增步+tests/ 脚本测试（循 test_check_ruff_budget.py 先例）。
- CHANGELOG Added 条目挂证据指针（D-082⑦）；forward 纪律：新 bullet 避免携带绝对总数/改写相对表述（"brings the tool surface to N"）。

**commit ② D-123 canary 通知化**：
- ci.yml drift job 增**独立 trailing notify job**（非 if:failure() 内联步）：job 级 permissions={contents: read, issues: write}（只读默认+job 级按需提权）；issue 按 workflow/branch 去重——首开新建、续败评论、恢复自动关；**notify 自身失败不遮蔽原红**（continue-on-error 级防护/独立结论面）。
- ADR-0023 发布清单增补硬项：「v1.0.0 门前须存在 ≥1 条 drift-canary 人为复核记录（运行结果+归因写账本，**红绿均可**——防「等红灯才复核」死角致清单项永远无法兑现）」。
- 账本登记新债行（下一 D 号）：该复核义务触发=v1.0.0 发布清单核对。
- CONTEXT.md「解析漂移金丝雀」词条回写——_Avoid_「金丝雀红了无人肉归因义务」的制度化对价落地后才改写该句（防前向虚指）。
- AGENTS.md:73「ADR-0001..0024」→「ADR-0001..0027」卫生修（整理环节检出）。

**commit ③ D-125 巨石行数棘轮**：
- 新增 .github/scripts/check_monolith_budget.py（循 check_ruff_budget.py 骨架：纯 stdlib+::error::+lint job）+预算文件入库——冻结值=**本批落地时实测** maya_scene_module.py 行数；计数口径=物理行。
- CI 棘爪：当前行数<预算→输出「可收紧」警告提示（非 fail；防 OmniRoute 式高水位退化）；预算下调须 PR 同 commit+写明理由（冻结预算词条既有纪律）。
- 报错文案两段：豁免通道=「不得 shuffle lines/删注释凑数；合理加行经人工批准下调预算并写明理由」（fissile 格言内核）+拆分去向指路=「新 Maya 侧能力走 ADR-0027 判据④同注入单元独立文件（introspect_module.py 首案）」——闸从阻止变导向。
- AGENTS.md 联动表登记脚本行。
- CONTEXT 词条结晶随批可选：若行数棘轮成常驻词汇，实现窗内补（防前向虚指）。

suggested skills：gitbutler（commit 分立）、domain-modeling（金丝雀词条回写）、neat-freak（AGENTS 卫生）

### T-27b — R27 批 2 代码两刀，单 PR 两 commit（D-122→D-124）

**commit ① D-122 慢测试修复+债纪律兑现**：
- tests/maya_stub fake 视口默认尺寸缩至几十像素级（如 64×48；逐像素 pattern(x,y) 扫成本∝面积降 ~99%）；尺寸语义断言测试（test_visual_tools.py :264/:267/:272/:396 一带）单独参数化/显式覆盖尺寸需求而非抬默认。
- 修复后本机+CI 4 格 --durations 全表复测：确认无 ≥1s 异常残留；兑现记录落账本——D-116 行内注明「裁决=无预算门（根因=fixture 尺寸非回归面）」+证据指针（D-082⑦）。
- 存量债逐条补标当前触发态（新纪律首例执行，附廉价核验证据）：D-102（否）、D-104（须查 fastmcp 5.x GA 现况后定档）、D-115（是-不可即兑〔无真机窗〕）、D-117（查 CI 4 格 pytest 版本后定档）、D-118（否-未实测）。
- 不动 per-test 超时硬闸（跨机方差 3.8×实证）；耗时回归防护如需另立=债文挂触发态按新纪律办理。

**commit ② D-124 删休眠引擎**：
- `git rm src/maya_mcp_server/aesthetic_engine.py + tests/test_aesthetic_engine.py` 同 commit（SCC 判据：测试随库同命运）。
- ruff/mypy/测试预算同 commit 下调写明理由（D-044 棘轮正向行使；删文件后 warn_unused_ignores 棘爪会显形——该文件内既有 ignore 计数须同步清出预算）。
- ADR-0003 双注记：勘误注记（当年否决「删引擎留内联」理由=「生产逻辑只能靠 stub 间接测」——前提 9 轮后已倒置：58 测试测陈旧副本不触生产路径；循 D-038②「accepted 不重开，澄清注记为唯一允许修改」不静默翻案）+status 注记「宿主模块已退役（T-06 判决 v0.4.0），Maya 内联 _score_*=唯一实现」。
- AGENTS.md 休眠痕迹清除：仓库结构树 test_aesthetic_engine.py 行、联动表 aesthetic_engine 休眠行、aesthetic 函数联动行改写、相关 docstring 税。
- CONTEXT「休眠代码」词条本体保留（定义非断言）；其他文档若存「aesthetic_engine.py 休眠中」式现役陈述随批改历史态。
- CHANGELOG Removed/Changed 条目挂证据指针；覆盖率叙事模板=「数字下降=删零生产引用 dormant 测试面、生产路径覆盖不变」（禁反向虚增叙事）。
- 核验 grep 全仓 aesthetic_engine 引用面（题面记零生产引用，实现时复核含 import 兜底防御代码）。

suggested skills：gitbutler、atomcode-research（D-104 触发态核验须 fastmcp 5.x 现况）、domain-modeling（休眠词条引例处置）

## 常驻提醒

- **人工门**（用户专属）：D-115 真机窗——开 Maya 时补采 shader_probe/mcp_stdio_probe/rst-fin-probe 等工件入 docs/evidence/probes/（D-109 形态：provenance+claim_boundary）+T-24 面 mayapy 冒烟（attr_meta/plug_connections/listAttr/attributeQuery，分钟级）——docs/testing.md 口径照走。
- **触发债库存**（触发态以批 2 补标为准）：D-102 positional cursor（否）、D-104 fastmcp-5.x 探索窗（待核）、D-115 工件补采（是-不可即兑）、D-117 max_warnings=0（待核 CI 4 格）、D-118 describe 耗时（否-未实测）、新债 D-127 canary 人肉复核（T-27a 内登记，触发=v1.0.0 清单核对）。
- **T-07 绞杀者纪律照旧**：D-125 棘轮为机械臂非替代——新 Maya 侧能力走判据④独立文件，巨石只降不升。
- **禁项**：实现窗内每批仍窄 diff+全联动面+审计复核；D-124 不许顺手做引擎/内联调和（合并路线已否决）。
- **措辞红线**：bullet 不带绝对工具总数（D-121 forward）；「23/25」矛盾勿再引；「wait_for 实等」归因已证伪勿再引（D-122）；覆盖率下降叙事按 D-124 模板；「保证不裂图」禁写（D-113⑤）；known-unverified 披露照旧（D-049）。

---

生成于 R27 grill 整理环节（账本 D-121..D-126 落盘后）；数据源=docs/decision-ledger.md，未从对话补结论。
