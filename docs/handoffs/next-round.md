# next-round.md — rev34（R26 兑现批：R4 锐评裁决落地 + v0.3.0 收口人工门）

生成：2026-09-27 R26 grill 整理环节｜Spec：docs/decision-ledger.md D-106..D-114（D-033/D-048/D-068/D-093/D-101/D-103 已 revised 留痕）｜前置调研：R26-Q1..Q9 经 atomcode 派发+ctx 索引（ctx_search source=atomcode 可取全文）｜题面档：.scratch/t26/questions/q1..q9-*.md

## 环境实况（本环节核验）

- main=7e0deb3；本分支 grill/round26-review4-adjudication 文档栈（账本 commit yvr + 本环节 CONTEXT/handoff）。
- 25 工具 778 测试绿（R25 基线值：mypy new:0/ruff 预算内/stdio 25 工具+ping）。
- fastmcp 钉 >=2.14.0,<3.0.0；4.x spike **已执行完**（D-105：部分红非阻塞，CI 权威红绿面=4 pytest 腿红+mypy 红/ruff 绿，本地 stdio 全绿，PR #41 已关，探测分支 probe/fastmcp-4x 待删）。R1-R3 迁移债已登记，触发=0.4.0 窗口（本批序批 4）。
- v0.3.0=dated-but-untagged 中间态（D-107 裁决兑现收口）；pyproject version=0.3.0；Unreleased 躺 T-24/T-25 待折叠。
- GitHub Releases 现存 v0.1.0/0.1.1/0.2.0；v0.1.2/v0.2.1 patch 不补页（D-084/D-108 已裁决）。
- uv.lock 不存在→批 3 新建；.github/assets/ 无守卫→批 1 建；pyproject 无 filterwarnings→批 1 建；probe-displacement.json 仍在 .scratch/t21/→批 1 迁 docs/evidence/probes/。

## 批次序与规则（D-114）

序=批1→批2→批3→批4；批1/批2 零文件交集可并行 draft、按序 merge；批3→批4 可 stacked PR。
**andon 规则**：批 2 红=契约 bug 暂停批 3/4 先修；批 3 红（Windows UV_PROJECT_ENVIRONMENT 首验失败）循 uv#9399 登债不阻塞批 4；批 4 红按 D-105 逐红项债登记。
**回滚边界**：批 1 纯 revert / 批 2 additive 字段 revert 仅影响已消费方 / 批 3 CI-only revert 回 uv pip install / 批 4 pin 回退 >=2.14,<3。

## 任务清单

### T-26a — v0.3.0 收口执行包（D-107/D-108）

1. CHANGELOG：Unreleased 下 T-24+T-25 内容全量折叠进 `[0.3.0]` 节；日期订正为实发日；T-06/T-07 交代一行入节（挂债+触发条件形态，锐评⑥内核=给交代非做掉）。
2. 发布清单新增硬核对项：「节内容==tag diff」（锐评遗留值）。
3. release.yml 注释钉死判别：「GH Release 步=minor 版执行、patch 依 D-084」（D-108；工作流注释+清单双锚）。
4. T-24 面软前置冒烟：用户开 Maya 则跑 mayapy 冒烟（attr_meta/plug_connections/listAttr/attributeQuery 面，分钟级）；不开则 release notes 按 D-049 档披 known-unverified——**不设硬 CI 门**；T-25 免（纯宿主侧零新 cmds 面）。
5. 人工门交用户执行（D-068 序列）：tag v0.3.0→GH Release（minor 有）→publish→PyPI 验证；完成后 pyproject 升 0.4.0=在发版号承接批 1-4。

suggested skills：无（纯发布规程；gitbutler 管 commit）

### T-26b — R26 批 1 守卫批，合单 PR commit 分立（D-109+D-111+D-113）

**commit ① D-109 证据可携性迁移**：
- `.scratch/t21/probe-displacement.json` → `docs/evidence/probes/probe-displacement.json`；补 claim boundary 字段（「connected≠renders」消费处注释搬入工件）；日期/版本/PID=provenance 保留非脱敏对象（KORA 先例）。
- 3 处引用改仓内路径：asset_module.py:329 注释、tests/maya_stub/scene.py:25、tests/test_asset_module.py:263。
- D-082① 路径指针、CHANGELOG:134 Evidence Rule 引文、CONTEXT.md「实证反审计」词条（本环节已改词条文；批 1 复核落点一致）。
- ~7 处裸「verified live」注释→诚实注记（live-verified, evidence pending 类）；其余探针工件登记触发债=下真机窗补采。
- docs/evidence/ 纪律随件入账：append-only，被反驳走新工件+新裁决+旧件 superseded。

**commit ② D-111 告警棘轮**：
- pyproject [tool.pytest.ini_options] 加 `filterwarnings`：首项 "error"+两条窄豁免——`ignore::AuthlibDeprecationWarning:fastmcp`（module 正则前缀 `fastmcp` 非 `fastmcp.*`；触发=上游迁 joserfc，核销观测点已挂 D-099 探针增项）+`ignore:doesn't match a supported version:RequestsDependencyWarning`（触发=依赖刷新对齐）；每条注释挂触发债+证据指针；豁免只减不增。
- tests/test_scene_tools_json.py 两处病灶 MagicMock 化：`:241-249` 与 TestErrorPassthrough::test_server_execute_code_ok——`client.append_output = MagicMock()`（同步方法被 AsyncMock 误化；禁 await 化=测 mock 非测契约）。
- PytestUnraisableExceptionWarning 零豁免（error 闸对其经 unraisablehook 真实生效）。
- ADR-0006 或 0017 Consequences 增一行：警告维度棘轮=pyproject filterwarnings 豁免清单+触发条件债注释。
- 触发债登记两条：profiling（实测单测 ≥1s 异常再裁——锐评 5s×8 归因已驳回但耗时面未否认）；max_warnings（CI 4 格全解析 pytest≥9.1 时启用 `max_warnings=0`）。

**commit ③ D-113 资产守卫**：
- `.github/scripts/check_assets_append_only.py`：纯 Python 无依赖；`git diff --no-renames --diff-filter=D`（rename 展开 D+A 确定性化；过滤集须覆盖 D+M——实现时复核 `--diff-filter` 字符集，M 也必拦）非空→列文件+`::error::`+逃生口指引（维护者知情合入+PR 声明+账本注记）+docstring 挂 D-113/D-081。
- ci.yml lint job 增一步（README 骨架检查旁）；PR 事件=merge-base..HEAD（checkout fetch-depth:0）；push(main)=before..after（before 全零跳过）。
- CONTEXT.md「只加不删资产目录」补「CI 守卫见 check_assets_append_only.py」互锚+CHANGELOG Added 挂脚本 path:line。
- 守卫文案=「防误删机制」，禁写「保证不裂图」（D-017⑥）。

suggested skills：gitbutler（commit 分立）、neat-freak（措辞面核对）

### T-26c — R26 批 2 scene_describe 预算，单独 PR（D-110）

- attrs 软顶 200+connections 顶 200+显式放宽硬顶 1000（对齐 scene_nodes limit=50/cap=100 软顶语义）；披露字段 `attrs_truncated`/`connections_truncated`/`total_count`（*_truncated 词族统一）。
- connections 不加 cursor：v1=total_count+截断+调用方收窄再查；日后若立 cursor 债须绑过滤集快照（D-102 教训前置吸收）。
- cap=写死常量+注释挂证据指针（D-082⑦）；上调走账本 revise；不做 env/config 开关。
- cap 只封响应体积；主线程 ~10 次 attributeQuery/attr 耗时面独立——真机实测超标另立采样/批量 query 债（债文留区分句）。
- AGENTS.md 联动表 introspect 行全项：introspect_module+introspect_tools 契约文本+pipeline+server instructions+threat-model §5+visual-callform-matrix+双 README+tests/maya_stub attr_meta/plug_connections 面+双测试文件。
- D-094 契约文本增项同步：attrs=None 语义=给全切面至预算、超预算截断+披露（additive 不 revised）。

suggested skills：domain-modeling（契约增项措辞）、atomcode-research（如遇 cap 值再标定争议）

### T-26d — R26 批 3 uv.lock 双轨，单独 PR（D-112）

- 入 uv.lock；test/lint job 安装迁 `uv sync --frozen`（uv pip 不读 lockfile）；dev 依赖从 `[dev]` extra 迁 PEP 735 `[dependency-groups]`（最大隐藏迁移成本）。
- Windows 侧 `uv sync` 不落 `--system`：UV_PROJECT_ENVIRONMENT 方案=迁移 PR **首验点**（uv#9399）。
- 新增 weekly scheduled resolution-drift job（浮动解析专任金丝雀）：红=D-100④ 触发债自动成就+承接 D-099 fresh-resolution 探针义务。无 uv 生态逐字模板=自研轻量件。
- ADR-0015 Consequences 增补安装路径演进注记（增量非 supersede）；D-033「测用户实装面」论证转任 weekly job 承接。
- 注意：本批动 pyproject [dev] 引用面，批 1 的 filterwarnings 在 [tool.pytest.ini_options] 不纠缠（D-114 排序已化解）。

suggested skills：gitbutler、atomcode-research（sync --frozen Windows 面若踩坑）

### T-26e — R26 批 4 D-105 迁移执行+pin 收窄（D-097/D-099/D-100/D-105）

- spike 报告已有（.scratch/t25/reports/2026-09-26-fastmcp4-spike.md 或 ctx 索引）；R1-R3 迁移债清单以报告红腿为准。
- 收窄 PR：pin >=4.x,<5.0.0+注释双锚（#18/#36 修正后红史——camelCase 误归因双染+ii-agent#165 实为 2.x×新 pydantic 勿引错向 D-100⑤+上游「minor 允许破坏」政策页）+dependabot 注释终稿。
- 收窄前提=CI 4 格+stdio_probe 双绿（D-105④）；红则逐红项债含触发条件。
- 探测分支 probe/fastmcp-4x 删除=本批或前置家务（D-105 可弃）。
- authlib.jose 存活面核验=批 1 登记的 D-099 探针增项在本批兑现（核销 D-111 authlib 豁免的观测点）。

suggested skills：atomcode-research（红腿根因再核）、code-vulnscan 不需要

## 常驻提醒

- **人工门**（用户专属）：v0.3.0 tag/Release/PyPI；T-24 面 mayapy 冒烟（开 Maya 时）。
- **触发债库存**：hub connections>500 已由 D-110 提前兑现销账；D-102 positional cursor 债照旧；新债=D-111 profiling/max_warnings 两条+D-110 采样耗时区分句+D-109 工件补采（真机窗）。
- **禁项**：grill 已过——本清单即实现窗授权；但每批仍窄 diff+全联动面+审计复核。
- **措辞红线**：live-verified 类声明必挂工件/档名（D-109）；「保证不裂图」禁写（D-113⑤）；「5s×8」归因已驳回勿再引用（D-111④）。

---

生成于 R26 grill 整理环节（账本 commit yvr 之后）；数据源=docs/decision-ledger.md，未从对话补结论。
