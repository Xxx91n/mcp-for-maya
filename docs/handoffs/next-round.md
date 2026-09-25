# next-round.md — rev31（T-23：scene_export 功能轮 + 家政批 + issue #2 收口 → 0.3.0）

生成：2026-09-25 grill 后整理环节｜Spec：docs/decision-ledger.md D-087~D-093｜前置：ADR-0026/0027、.scratch/t22-audit/reports/2026-09-24-audit-report.md（T-22 审计）、.scratch/atomcode-q{5..9}.txt（本轮五轮调研题面）

## 环境实况（本轮核验）

- main=f2b33f9（T-22 双 PR #28/#29 已合入，审计两轮 PASS）。工作区干净。
- **Maya 2024 活着**（PID 13276，:7001 Qt framed LISTENING）——真机窗当前可用；本会话四次只读探针净零验证（场景 modified=false，临时文件已清）。
- 真机探针实证：fbxmaya/objExport/mayaUsdPlugin/AbcExport 四插件全已加载；`cmds.file` 导出 type 映射钉死 {fbx:"FBX export", obj:"OBJexport", usd:"USD Export"}（空场景实测 8144/88/547 B）；`type="Alembic"` 失败=异构 AbcExport API 判出局。
- 门禁基线（审计复核值）：pytest 715/17skip、gui 7/7、ruff src 77/77 + tests 27/27、mypy 新错 0（基线 237）、skeleton 26 1:1、pre-commit 8/8、build+twine PASS、stdio 22 工具全过。
- Dependabot 实况：PR #18 fastmcp<5.0.0 CI 真红（ToolAnnotations kwargs camelCase→snake_case，API 迁移级；本地 2.14.7，PyPI 最新 4.0.9）；PR #16 ruff-pre-commit 0.15.20→0.16.7 本地实证新版 104 findings 全在 per-rule 预算内（此前 CI 红是旧树）。
- ruff 钉点两处须同步 bump：.pre-commit-config.yaml rev + ci.yml `uvx ruff@0.15.20`（pre-commit 注释明示钩子/CI/dev venv 三对齐）。
- issue #2 实况：5 项验收 4 项已兑现；唯一未兑现=「集成进 scene_plan 推荐」（asset×scene 跨域残余）。

## 任务清单

### T-23a — 家政批（D-089 + D-090 + D-091 附带项）

1. **PR #18 处置**：`gh pr close` + 评论引 CI 红证据（ToolAnnotations kwargs 更名）。dependabot.yml 加 `ignore: fastmcp semver-major` 止血每周重开。顺延债记「fastmcp-3.x 探索窗」带触发条件=下个 minor 窗口：届时探 3.x 兼容面，探通收窄 `>=3.x,<4.0.0` 且 pyproject 注释引 CI 红记录；4.x 迁移另排队。
2. **PR #16 处置**：不合 bot PR 本体——自开原子 PR 同步 bump 两处钉点至 0.16.7（.pre-commit-config.yaml rev + ci.yml uvx pin）。CI 绿则合；红则修或显式 ignore 新 findings（**预算棘轮永不上调**，D-044）；若 formatter 有行为差异单独 commit。合后 bot PR 自然过时关闭。
3. **P-5 `_delete_if_exists`**：asset_module.py 内抽私有原语收敛 ~5 处 `objExists→delete` 调用点（:139-146 批量环改循环内单点调用；:301-305、:333-338 两回滚块内嵌处同收敛但**块本体保留**——2 实例 incidental duplication 未达抽取线）。TestBumpOrphan+既有 disp 测试全绿为回归网。visual_module 同型 2 处不动（注入模块自包含约束）。不抽 create-with-rollback 管理器（参数化=wrong-abstraction 起点）。
4. **AGENTS.md 准入三判据**：注入模块准入三判据写入联动规范节（独立注入时机/独立 Maya 侧 API 面/独立失败域），锚链 ADR-0027。
5. **台账联动**：docs/agents/issue-tracker.md 随 T-23c 同步（issue #2 状态+新 issue 登记）。

### T-23b — scene_export 实现（D-091 落位 + D-092 契约）

- **文件**：新建 `src/maya_mcp_server/export_module.py`（Maya 侧，注入名 `_mcp_export`，懒注入首个 export 调用触发，复用 `client.ensure_module_injected`）+ `export_tools.py`（宿主侧 register_export_tools）；server.py 并排注册；pipeline.TOOL_ANNOTATIONS 增行。
- **契约**（D-092 定稿，实现以账本行全文为准）：
  - `path` 必填+归一化+父目录自动创建+exists→域错误（`overwrite=False` 默认）+Maya 侧 `prompt=False` 强制（防模态挂死）
  - `format` 枚举 {fbx,obj,usd}；缺省从扩展名推断；缺扩展名按显式 format 追加；显式 format 与扩展名冲突→报错不猜；镜像规则双向测试
  - `objects=None`→exportAll；list→逐个 `objExists` 预校验（缺一即域错误，无部分导出）+save/restore 选择集 finally 还原
  - 返回 `{path, format, objects_exported:int, size_bytes, duration_ms 真值, warnings[]}`
  - 域错误族：invalid_format/invalid_path/empty_objects/plugin_missing（先 loadPlugin 尝试，败则结构化错）/missing_objects
  - annotations：readOnlyHint=false、destructiveHint=false（docstring 注明 overwrite=True 不可逆）、idempotentHint=false、openWorldHint=false
- **stub**：cmds.file 导出面补齐（exportAll/exportSelected/type/force/prompt），按 D-074 资产面先例扩 maya_stub。
- **测试面**：格式推断/显式/扩展名追加/冲突报错/overwrite 拒/父目录创建/全对象预校验/选择集还原（成功+失败两径）/plugin 加载失败/prompt=False 断言/返回形状+duration_ms 真值/annotations/双通道（native+Qt）行为。
- **文档**：threat-model §5 矩阵补「本地文件写入」行——任意绝对路径是知情接受（execute_code 天花板下 confinement=剧场），symlink/路径归一化残余如实登记；CHANGELOG Unreleased Added 挂证据指针；工具计数面同步（22→23：README/AGENTS.md/测试常数）。
- **边界**：abc/Alembic 不在首片（探针实证异构 API）；exporter option flags 等实现级细节属 spec 裁量面。

### T-23c — issue #2 收口（D-093）

1. `gh issue edit 2`：body 收窄至已兑现范围——4 项验收打勾各挂证据指针（asset_tools.py 实现+测试锚点），残余条保留为「Remaining → #N」指针。
2. close comment：「partially shipped (0.2.0); remaining work split to #N」——partial-fix 不静默关。
3. `gh issue create` 新 issue：scene_plan 资产推荐集成（zone 语义+bbox 尺寸），注明「Split from #2，thin-slice 定位已毕此项为完整集成」；双向回链；后续 PR 用 `Refs #N` 不自动关。
4. README roadmap/issue 列表引用同步；docs/agents/issue-tracker.md 同步。

### T-23d — 门禁收口 + 0.3.0 人工门（D-093）

- 全门禁复跑（pytest/ruff 预算/mypy 基线闸/skeleton/pre-commit）；but 提交走 impl 分支惯例。
- CHANGELOG Unreleased 折叠入 [0.3.0] 订正日期+顶部留空 Unreleased；tag/release 备单**走人工门**（PyPI 14 天不可变+逐版核实纪律沿用）。

## 顺延债（原样挂账 + 本轮新增）

原清单：巨石 maya_scene_module.py 4583 行（mypy 183/237）/ T-06 AE 归并 / T-07 拆分 / stub connectAttr 槽位类型表 / N4 smell 债 / 依赖锁定 / coverage patch 门 / macOS smoke / Arnold / T-19 顺延批（async 阻塞下载/双次哈希/首 SG 位移线/_ASSET_TYPE_RE 收紧/zh 历史地址注/2 码入清单/新 callform 入账/assets-src 残留——「_ensure 三份复制」项已随 T-22a 去重核销）

本轮新增：
- **scene-graph introspection spec 轮**（D-088 拆出：独立立项，不随 export 顺带）
- **fastmcp-3.x 探索窗**（D-089，触发条件债：下个 minor 窗口开探；探通收窄 `>=3.x,<4.0.0`，4.x 迁移另排队）
- **Alembic/AbcExport 导出能力**（D-092 判出局项：异构 API 非 cmds.file 面，未来单独立项）

## 铁律

- 脏场景守卫：真机操作前探针先行，脏则停
- `prompt=False` 硬约束（模态对话框可挂死命令通道）
- 修复不夹带：只修 D-089~D-093 列项；预算棘轮只降不升（D-044）
- 诚实口径：文件写入是事实能力照实登记（threat-model §5），不宣称未实现的 confinement；partial-fix 不静默关 issue
- release/tag/push/GH Release 全走人工确认门；0.3.0 切分动作归用户

## Suggested skills

- implement / tdd（T-23b；stub 契约先行，负例测试随被验行为）
- gitbutler（but 提交/PR；dependabot 双 PR 处置用 gh）
- neat-freak（T-23c 台账同步）
- domain-modeling（introspection spec 轮开烤时）
- atomcode-research（fastmcp-3.x 探索窗触发时）
