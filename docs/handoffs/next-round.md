# next-round.md — rev27（T-19：README 门面升级 + Poly Haven 资产导入 → 0.2.0）

生成：2026-09-23 grill 后整理环节｜Spec：ADR-0024 + docs/decision-ledger.md D-071~D-077｜前置：ADR-0023、.scratch/t18/handoffs/2026-09-22-audit-handoff.md（T-18 闭环实录）

## 环境实况（本轮核验）

- `origin/main`=0d0f242：v0.1.2 已发 PyPI、0.1.0/0.1.1 已 yank、上游 6 条评论全发；工作区干净
- **Maya 当前未运行**——采集窗需用户以英文 UI 启动（MAYA_UI_LANGUAGE=en_US 系统环境变量，**禁写 Maya.env**）
- 采集管线先例：.scratch/facade/dogfood_capture.py（stdio→repo HEAD server→建场景→捕获）
- 现状资产：README.md=中文337行（GitHub+PyPI 默认面）、README_en.md=英文312行；shot-hero/shot-alt/orbit.gif=原始体场景待重拍

## 任务清单

### T-19a — Poly Haven 资产导入功能核（D-074/D-075）

1. **asset_search**：Poly Haven API（api.polyhaven.com，免 key，**必填 User-Agent**）→ 元数据列表（限 20 条保 total_count）；注解={readOnlyHint+idempotentHint+openWorldHint:true, destructiveHint:false}
2. **asset_import**：descriptor 入（本地路径+源URL+CC0+依赖路径）→ 宿主侧 https 下载（白名单 api.polyhaven.com+dl.polyhaven.com、尺寸/超时护栏、默认 1k 贴图档）→ platformdirs 缓存（key={asset}/{res}/{file}、文件名 sanitize）→ files_hash 校验 → fbxmaya.mll 幂等 loadPlugin → Maya cmds.file(i=True, unit=meters 显式) 导入 → **纹理自动接线**（PH 命名约定 diffuse/rough/nor_gl→file 节点、normal 过 normalMap——主工程量）→ dimensions sanity check → 归组命名 → 回报 bbox/元数据；注解={readOnly:false,destructive:false,openWorld:true}（idempotentHint 仅当同名去重才标）
3. **护栏**：polycount>100k 默认拒（参数可覆盖+审计披露）；坏 FBX 容错（PH 部分 FBX 本身有损）；无网=显式 network_unavailable 域错（非 isError）禁静默陈旧缓存；cache 命中审计标 source:cache；审计记 URL/size/files_hash
4. **联动面**：pipeline.py TOOL_ANNOTATIONS、server.py instructions、threat-model.md §5 矩阵、AGENTS.md（工具数 20→22+联动表）、tests/（stub 层：API mock+下载+导入链路；PH FBX 真测归真机窗）

### T-19b — README 英文默认化（D-072；与 T-19a 可并行）

- README.md←英文正文（唯一 source-of-truth）、README.zh-CN.md←中文镜像（头注锚英文 commit hash）、**删 README_en.md 不留 stub**；两文件顶部语言选择器置于一切内容前（当前语言加粗不链接）
- CI 挂标题骨架校验（EN↔zh 标题序列一一对应）入 lint job；AGENTS.md 联动表 README_en.md→README.zh-CN.md 六处
- pyproject readme 字段不动；PyPI 页随 0.2.0 发版自动转英（不为刷页单独发版）

### T-19c — 演示场景构建+采集窗（D-071/D-073/D-076/D-077；前置=用户开 Maya en_US）

1. **场景**（agent 经本 MCP 工具实况迭代，看截图调构图）：展厅环境（地台/射灯阵/围栏/zone 分区以材质与灯光色温暗示**禁线框彩色描边**）+主展品机械虹膜雕塑（revolve 机壳+光圈叶片阵列+透镜玻璃+曲线线缆）+第二展品脚本复刻 Utah 茶壶+第三展品 asset_import 真导入（建议 Camera_01 vintage rangefinder=光学之眼呼应）——**禁原始体堆叠观感，复杂多边形+曲线硬约束**
2. **工艺**：VP2 全开 SSAO/MSAA/DoF/depth-map 软阴影/暗色自定义背景+相机父级约束 rim 光（orbit 每角度稳定）；前中后三层+对比度集中 focal point
3. **出片**（一个冻结 session 一次出齐）：hero.png 嵌新无 HUD 中景雕塑+shot-hero/shot-alt 带 HUD+orbit.gif 5-15s 环绕+social-preview.png 1280×640/<1MB 实底+例表 4 图（第4行 before/after 双帧）；HUD 分层=hero 关/shot 留
4. **结晶**：定稿后场景构建+采集脚本固化入 .github/assets-src/+复现 README（Maya 版本/PH 资产 ID/VP2 参数）+采集 transcript 留档
5. **验收门**：全套素材贴图呈报用户过目签字才入库（发布 checklist 显式 gate）

### T-19d — README 内容收口（D-071/D-076；等 T-19c 素材）

- prompt→结果例表 4 行（| Prompt | Result | 每行内嵌实拍）：①Build a showroom displaying a mechanical iris sculpture ②Rebuild the Utah teapot and place it on a pedestal ③Find a CC0 vintage camera on Poly Haven and import it ④Audit this scene and fix violations
- 能力矩阵 20→22 工具+资产行；blender-mcp 对比表重分档（资产生态=部分对齐：Poly Haven vs 其 4 源，如实写）；双语同改（EN 先行 zh 镜像跟随同 PR）

### T-19e — 门禁+0.2.0 备料（D-075/D-077）

- 门禁：pytest/ruff 预算/mypy 基线/pre-commit 全绿+真机窗覆盖 asset_import 路径（下载→导入→接线→断网降级域错）
- CHANGELOG 0.2.0 段（新功能=minor bump）；关闭/更新本仓 roadmap issue #2
- 发布备料：tag/release notes/人工门清单

### 人工门（用户执行，agent 备单）

开 Maya（en_US）→素材过目签字→0.2.0 push tag→release workflow→盯 publish CI+验 PyPI→可选上游/social 跟进

## 顺延队列（原主不动）

N4 五条 smell 债 / T-06 dormant 引擎归置 / T-07 注册表 / 依赖锁定 / coverage patch 门 / macOS 冒烟 / T-14b #7 残余 / sha 戳 post-inject / stub setFloatPixels / nested retry / Arnold 静帧可选项（届时走账本裁决）

## 铁律

- dogfood 不破：全部素材产品工具链实拍禁 mock/生成图；脏场景守卫沿用（探针先行脏则停）
- 复刻限公版/CC0 对象禁版权角色；有机生物/角色不进脚本复刻题材
- 素材未过目不入库；半旧半新素材禁混用（一次 session 出齐）
- 资产导入安全骨架不降级（白名单/护栏/审计）；Maya 零网络面
- VC 全走 but；grill/实现分离

## suggested skills

- `$implement` / `$tdd` — T-19a 功能核与测试面
- `$but` — 全部 VC 写操作
- `$handoff` — 翻页
- `$atomcode-research` — 争议调研（串行单发）
- `$domain-modeling` — 术语增量入 CONTEXT.md 时
