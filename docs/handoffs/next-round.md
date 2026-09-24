# next-round.md — rev29（T-21：第三轮锐评修复批 + 0.2.1 收口）

生成：2026-09-24 grill 后整理环节｜Spec：ADR-0026 + docs/decision-ledger.md D-082｜前置：ADR-0025、.scratch/t21/audit-r3.txt（审计原文）+ .scratch/t21/probe-displacement.json（P1-B 驳回真机证据+P2-E 属性面）

## 环境实况（本轮核验）

- main=b2640f1（PR #25/#26 合入，T-20 落地：设计横幅+6 行 Prompt|Result 表+绝对 URL main 钉）；工作区干净
- PyPI 0.2.0 页面 14 图全裂不可回改——随 0.2.1 顺带修（D-081 既定路线）
- main 已带真代码修复 0ccf0a1（polyhaven bare-key）→ 0.2.1 patch 语义正当（docs-only 前提作废）
- Maya 2024 活着：PID 4452，:7001 在听，HUD 英文；**场景为脏**（探针实测 pre_dirty=true）——动手前照旧走脏场景守卫
- 门禁基线：pytest 692 / ruff 79+28+.github 0 / mypy 基线 237 行（新错 0 闸）/ skeleton 26 1:1 / pre-commit 8/8

## 任务清单

### T-21a — P1-A tmp 注入卫生修（D-082①）

两处 temp-file 注入口改安全姿势：asset_tools.py:58（_mcp_asset_src.py）+ scene_tools.py:80（_mcp_scene_src.py）——mkstemp（dir=平台缓存目录）+0600+try/finally unlink；参照同仓正解 visual_module.py:311/:391。对外口径=卫生缺陷修复，非安全边界破口。

### T-21b — P1-B 残余小修+驳回留档（D-082②）

- 驳回已凭真机探针入账（disp.displacement→sg.displacementShader 连接成立，SG 源列表实见节点）
- test_asset_module.py 补 displacement 正/负例（当前 grep=0 命中）
- _wire_map 失败路径孤儿节点回收（asset_module.py:298 创建的 disp 节点失败时 delete）
- stub connectAttr 槽位类型表=记债不本轮（现只建模标量→三元组）
- displacement 渲染语义层（连接成立≠渲染生效）归 gui/human_verify 档，写进清单

### T-21c — P2-C CHANGELOG 措辞归真（D-082③）

CHANGELOG:49 "manifest-based cache reuse"→真实机制（fresh-metadata revalidation+per-file size+md5 复验；manifest.json=只写审计产物）。

### T-21d — P2-D VP2 方向运行时探针（D-082④）

首选：首次视觉工具调用时跑非对称纯色探针定 per-session 方向（复用 gui 档断言逻辑，tests 已有 :298-301 所指）。**铁约束=净零副作用**：探针瞬时搭景→断言→全拆→还原 dirty 标志；落位若被证不安全→退化为文档化逃生开关（env-var+README 环境要求节）。_VP2_READBACK_BOTTOM_UP 语义从「常量仲裁」改为「探针兜底默认值」。

### T-21e — P2-E 材质修复（D-082⑤）

_new_material blinn→standardSurface（asset_module.py:183）。**坑**：stdSurface 有 specularRoughness/metalness/normalCamera，无 roughness/diffuse/reflectivity（probe-displacement.json 实证）——AO 角色现指 diffuse 须改 base 侧目标；映射表同步重订；test_asset_module 材质断言面更新。

### T-21f — P3 六项打包（D-082⑥）

1. polyhaven.py:172/443/449 裸 int()→收口 AssetError 域（脏头/脏 size 不再抛 ValueError 逃契约）
2. search_assets /assets 索引加 TTL 缓存（对 CC0 API 失礼修复）
3. asset_tools.py:122 duration_ms=0.0→求真值或删字段（假数不如不填）
4. create_orbit_camera/create_camera_shot 默认名 orbit_cam/shot_cam→CAM_ 前缀（maya_scene_module.py:1530/1631，自家工具撞自家 CAM_ 审计）；默认名=对外行为面，CHANGELOG 记为行为变更
5. README/docs 钉法措辞+**assets 目录只加不删纪律**入 AGENTS.md（旧 PyPI 页永久引用 main 路径，删旧资产=历史页永久裂）
6. 巨石增长记账（maya_scene_module 4583 行/mypy 183 行住它）——记债不本轮修

### T-21g — meta 机制：CHANGELOG 证据指针（D-082⑦）

AGENTS.md 联动规范增条：CHANGELOG Added/Fixed bullet 必须挂 file:line 或测试 ID（lint 可查）；0.2.1 条目为首发执行对象。病灶史=CHANGELOG:33（已删）+manifest-based。

### T-21h — 门禁收口+0.2.1 备料（D-082⑧）

- 全门禁：pytest / ruff 预算 / mypy 基线闸 / skeleton / pre-commit / uv build / twine check
- bump 0.2.1+CHANGELOG 0.2.1 节（每条挂证据指针）
- README/zh 镜像按传播矩阵同步；issue #2（自家 tracker）顺手更新
- **发布动作为人工门**：tag/Release/PyPI publish 备命令清单呈报，用户执行；0.2.0 裂图页不可回改，0.2.1 发布即顺带修

## 顺延债（原样挂账不动）

N4 smell 债 / T-06 AE 归并 / T-07 validator 注册表+巨石拆分（锐评：下个 minor 该兑现一次减行）/ 依赖锁定 / coverage patch 门 / macOS smoke / Arnold / T-19 顺延批（async 阻塞下载/双次哈希/_ensure 三份复制/首 SG 位移线/_ASSET_TYPE_RE 收紧/zh 历史地址注/2 码入清单/新 callform 入账/assets-src 残留）/ **本轮新增**：stub connectAttr 槽位类型表

## 铁律

- 脏场景守卫：探针先行，脏则停（本轮实测场景即脏）
- ICEV/命名/zone/双层错误契约不破；审计 JSONL 语义不动
- 修复不夹带：只修 D-082 列项，新病灶记账另行
- 对外口径诚实：P1-A=卫生缺陷；P1-B=已驳回（探针证据）
- release/tag/push 全走人工确认门

## Suggested skills

- implement / tdd（修复批；T-21b 负例先行可复现 stub 语义差）
- gitbutler（but 提交/PR）
- handoff（下一轮交接）
- domain-modeling / neat-freak（文档收口）
- atomcode-research（仅当 P2-D 探针落位或 AO 映射需外部先例时，串行）
