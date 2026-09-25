# next-round.md — rev32（T-24：scene-graph introspection spec→实现 + 家政批）

生成：2026-09-25 R24 grill 整理环节｜Spec：docs/decision-ledger.md D-094/D-095｜前置：ADR-0027（含 D-095 修订节）、.scratch/t24/questions/q1-introspection-shape.md + q2-module-placement.md、atomcode 调研经 ctx 索引（q10=形态 / q11=落位，ctx_search source=atomcode 可取全文）

## 环境实况（本轮核验）

- main=4272d28（T-23 三栈 PR #32/#33/#34 全合入）。工作区=本环节文档改动。
- **Maya 未在运行**（无 maya.exe 进程、:7001 无监听）——真机验证窗须用户开 Maya 后再跑。
- issue #5 OPEN：export_scene 半项已交付 0.3.0（issue checkbox 未勾属文档滞后）；scene-graph introspection=残余项=本轮对象。
- 门禁基线（T-23 审计复核值）：pytest 749/17skip、ruff src 77/77+tests 27/27、mypy new:0（基线 237）、skeleton 27、pre-commit 8/8、stdio 23 工具。
- dependabot 三连：#36 fastmcp<4.0.0（D-089 冻结项；ignore:semver-major 已入 dependabot.yml 但 #36 仍开出——约束放宽型 PR 可能不吃 update-types 分类，处置时先复核）；#35 ruff-pre-commit 0.16.8；#30 setup-uv 10.1.0→10.2.0（actions-minor-patch 组）。
- **0.3.0 残余人工门**：tag v0.3.0→GH Release→PyPI 未执行（用户专属，勿代办）。

## 任务清单

### T-24a — 家政批（政策源 D-089；队列实况承 t23 审计交接）

1. **PR #36**：按 D-089 同款处置——close+评论引证据（CI 红引 CI，CI 绿引冻结决策本体）；顺带核查 ignore 为何未拦约束放宽型 PR（确认一次性残留或规则补 wording），结论记债台账。覆盖 D-089。
2. **PR #35**：原子 bump 模式复用——自开 PR 同步 bump .pre-commit-config.yaml rev（0.16.7→0.16.8）+ci.yml uvx 钉点；formatter 差异单独 commit；预算棘轮永不上调（D-044）。覆盖 D-089。
3. **PR #30**：actions-minor-patch 组成员，按组策略评估直合或随批。覆盖 D-089（dependabot 政策面）。
4. **stub 预勘**（T-24b 前置）：maya_stub 现有 objExists/nodeType/listConnections（简版）；listAttr/attributeQuery/listConnections(plugs/d) 面缺失须扩，按 D-074 先例。覆盖 D-094（测试面分支）。

### T-24b — introspection 实现（D-094 形态 + D-095 落位）

- **形态**（D-094 定稿）：
  - scene_describe(node)：实例级自描述 {type, attrs[组合调用必需切面], connections[{src_plug,dst_plug,direction}]}；connections 默认返回（轻字段不藏开关后），开关只控重字段（值/softRange）
  - scene_nodes(type?,pattern?,dag_only?)：枚举含非 DAG 节点（材质/工具节点等 snapshot 盲区）；返回 count+截断名单(默认~50)+has_more/next_cursor+可选 type_counts
  - 两工具 description 互写边界句：scene_describe≠scene_inspect（空间级）、scene_nodes≠scene_snapshot（低清概览）
- **落位**（D-095 定稿）：B'——归 _mcp_scene 注入单元域 + 独立宿主侧文件装配（非追加巨石本体）；装配机制二选一在契约裁：①注入前拼接进 _mcp_scene payload ②注入后挂接命名空间。宿主侧 introspect_tools.py 独立成文件（同 export_tools 例）。定位 T-07 首批迁移单元。
- **契约细部=Q3 提案表未裁决**（下窗首题；以下为提案非账本结论）：
  - 提案：scene_describe(node, attrs=None|list[str], include_values=False, include_connections=True)；attrs 条目=组合调用必需切面 14 字段（attr_type/writable/readable/connectable/keyable/multi/enum+listEnum/min+max+exists/hidden/locked/storable/children/indexMatters）；scene_nodes(type, pattern=glob, dag_only, limit=50 且服务端 min(limit,100), cursor)；json-only 无 cos 分支；annotations readOnly=T/destructive=F/idempotent=T/openWorld=F；域错误族 node_not_found/attr_not_found/invalid_cursor/query_failed；include_values 可能触发 DG evaluation 须如实写 description+threat-model
  - 提案叉子与建议：attrs 过滤=list[str]；json-only；include_values 默认 False；type 过滤加 inherited flag
  - 提案负向：不做属性写入/类型级 schema/递归连接遍历/超限静默截断
- **测试面**：stub 补 listAttr/attributeQuery/listConnections 参数面；契约+annotations+双通道测试；真机档（Maya 须用户开启）describe/nodes 冒烟留证
- **文档**：README/README.zh-CN/AGENTS.md 工具计数 23→25；server.py instructions；pipeline.TOOL_ANNOTATIONS 两行；threat-model §5 纯读面如实登记（无新威胁面则写明）；CONTEXT.md 视落地补 introspection 术语

### T-24c — issue #5 收口（D-093 先例复用）

落地后：#5 两 checkbox 勾齐+证据指针（export→0.3.0；introspection→本批测试锚点）+close comment；PR 用 Refs #5 不自动关；docs/agents/issue-tracker.md 同步。覆盖 D-094（兑现 issue 残余）+D-093（流程先例）。

### T-24d — 门禁 + 版本人工门

全门禁复跑；introspection=feature→预期 minor（0.4.0 属预期非裁决，切分归人工门）；0.3.0 tag/Release/PyPI 人工门仍挂，可与本批同窗口处理。覆盖 D-093（发布节奏惯例）。

## 顺延债

原样挂账：巨石 4583 行/T-06/T-07（introspection 独立文件=首批迁移单元候选）/stub connectAttr 槽位表/N4/依赖锁定/coverage patch 门/macOS smoke/Arnold/T-19 顺延批/Alembic 导出立项；issue #31（scene_plan 资产推荐残余）。
- **fastmcp-3.x 探索窗**（触发条件=下个 minor 窗口——T-24 落版即达标，届时开探收窄 >=3.x,<4.0.0）
- 新增：**Q3 契约细部提案待裁**（T-24b 首题）

## 铁律

- 判据语义读法=ADR-0027 修订后官方释法；新能力落位一律过判据流程
- 诚实截断：has_more/total_count 是契约一部分，禁静默截断
- 脏场景守卫照旧（真机操作前探针先行）；execute_code 天花板下不假装有 confinement
- release/tag/push/GH Release 全走人工确认门

## Suggested skills

- to-spec（T-24b 契约定稿——Q3 提案表待裁或再过一轮 atomcode）
- implement / tdd（T-24b；stub 契约先行）
- gitbutler / gh（T-24a dependabot 处置+提交）
- domain-modeling（introspection 术语定型时）
- atomcode-research（fastmcp-3.x 探索窗触发时；Q3 若需二审）
- neat-freak（台账/文档同步）
