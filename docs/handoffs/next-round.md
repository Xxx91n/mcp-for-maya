# next-round.md — rev30（T-22：R3 锐评残余收口 + 真机证据窗）

生成：2026-09-24 grill 后整理环节｜Spec：docs/decision-ledger.md D-083~D-086｜前置：ADR-0026、.scratch/t21/probe-displacement.json、.scratch/t21/handoffs/2026-09-24-audit-closeout.md（T-21 审计交接）

## 环境实况（本轮核验）

- main=c0134dc（PR #27 合入，T-21 全量落地：mkstemp 注入/disp 孤儿回收/CHANGELOG 归真/VP2 运行时探针/standardSurface 迁移/P3 打包/AGENTS.md 证据指针规范）
- **v0.2.1 已发布**：tag 在 c0134dc、Release workflow 6 job 全绿、PyPI 0.2.1 whl+sdist 上架未 yank、14 图全绝对 URL（裂图修复实证生效）；无 GH Release=0.1.2 先例（D-084）
- **Maya 未运行**（:7001 无监听、无 maya.exe）——T-22b 全部前置依赖用户开 Maya GUI
- 门禁基线（审计复核值）：pytest 704/24、ruff src 79 + tests 27/28、mypy 新错 0（基线 237 行/183 住巨石）、skeleton 26 1:1、pre-commit 8/8、uv build+twine PASSED
- 工作区干净；docs/agents/issue-tracker.md 已补齐（ba78337）

## 任务清单

### T-22a — 次要面修复批（D-083①② + D-086）

1. **bump2d 孤儿回收对称化**：`_wire_map` normal 角色在 asset_module.py 约 :290 创建 `bump2d` 节点，其后的 connectAttr 失败路径无回收（disp 角色 :314-330 已有同款 try/except+objExists+delete 姿势——照抄对齐）。覆盖 bump 全部失败路径；test_asset_module.py 补 orphan-cleanup 负例（与 TestDisplacement 同构）。
2. **注入函数去重**：`scene_tools._ensure_module_injected`（:57）与 `asset_tools._ensure_asset_injected` 为 ~30 行同构平行实现，差异仅四处——模块名（_mcp_scene/_mcp_asset）、mkstemp prefix、session 集合、pre-import 行。提取共用 helper（参数化这四项），两 call-site 改调它。**不得改变行为契约**：15000B native 阈值、framed_channel 判 Qt 走 write_module、mkstemp+0600+finally-unlink、ResultType.NONE 执行+pre-import。现有 TestInjectionHygiene 双套件必须保持全绿。
3. **AGENTS.md 坑注**（D-086）：shell 约定节一行——Git Bash 下禁 `2> nul`（Windows 保留设备名被当普通文件创建实体，致 `but status` 崩 os error 1；con/aux/prn 同坑），stderr 丢弃写 `2>/dev/null`。
4. CHANGELOG Unreleased 记 bump 孤儿修复 Fixed 条（挂证据指针，D-082⑦ 规范）；注入去重=内部重构不进 CHANGELOG。

### T-22b — 真机窗三件套（D-085；前置=用户开 Maya GUI）

1. `-m gui` 档跑 test_gui_session.py 的 VP2 不对称纯色断言——验证 _probe_vp2_direction 真机首触行为（探针代码已过 stub/host/包/进程四档，此为其一未闭合面）。
2. **displacement 渲染语义人工视验**——P1-B 驳回的范围是「连接成立」；「渲得出来」由本项实证。证据留档 .scratch/t22/。
3. **presence 基线重采集**：核销 presence-allowlist.json 中 polyCube/undoInfo 两条 provisional 条目（锚 docs/visual-callform-matrix.md#vp2-direction-probe-d-082d）。**回退条款**：真机采集若与 provisional 假设不符，须回退评估探针实现。

### T-22c — 门禁收口

- 全门禁复跑（pytest/ruff 预算/mypy 基线闸/skeleton/pre-commit）；but 提交走 impl 分支惯例。
- 本批无版本动作：T-22a 属未发布面的内部修复，CHANGELOG 挂 Unreleased。

## 顺延债（原样挂账不动）

巨石 maya_scene_module.py 4583 行（mypy 183/237 住它）/ T-06 AE 归并 / T-07 拆分 / stub connectAttr 槽位类型表 / N4 smell 债 / 依赖锁定 / coverage patch 门 / macOS smoke / Arnold / T-19 顺延批（async 阻塞下载/双次哈希/_ensure 三份复制/首 SG 位移线/_ASSET_TYPE_RE 收紧/zh 历史地址注/2 码入清单/新 callform 入账/assets-src 残留）

## 铁律

- 脏场景守卫：真机操作前探针先行，脏则停
- ICEV/命名/zone/双层错误契约不破；审计 JSONL 语义不动
- 修复不夹带：只修 D-083/D-086 列项，新病灶记账另行
- 诚实口径：P1-B=连接已证渲染待验（D-085② 完成前不得宣称全闭环）；P1-A=卫生缺陷非边界破口
- release/tag/push/GH Release 全走人工确认门；patch 不建 GH Release 为既定先例

## Suggested skills

- implement / tdd（T-22a；bump 负例先行对齐 disp 测试模式）
- gitbutler（but 提交/PR）
- handoff（再交接时）
- domain-modeling / neat-freak（文档收口）
