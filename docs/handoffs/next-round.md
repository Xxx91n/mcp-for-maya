# Handoff — maya-mcp-grill 下一轮任务书（rev20）

> 规范路径（T-11a/D-041④）：docs/handoffs/next-round.md；账本=docs/decision-ledger.md；.scratch 仅存本地过程件。

## 本轮验收事实（非计划）

- **T-12c+T-10b 已合并 main**（PR #14 spec + PR #15 impl，main@a22e148）：README PyPI 实链+badge、pre-commit 8 钩+GHA 兜底+dependabot 三生态、mass reformat+ignore-revs、per-rule 预算、mypy 基线闸（223/3 全 stub 环境）、coverage 66% 报告态
- **基线实测（main 口径）**：pytest 570 passed/4 skipped；ruff per-rule src 83/tests 39；mypy 223/3；pre-commit 8/8；uv build 0.1.1
- **真机环境就位（本轮新事实）**：用户 Maya **2024** GUI 活会话经 1mcp maya 后端连通（127.0.0.1:51217，pid 5396，空净 untitled）；后端=python -m maya_mcp_server（pid 3168）跑 repo 工作树（src 经 PYTHONPATH）≈0.1.1 运行时；mayapy 在位 D:maya2024Maya2024inmayapy.exe（py3.10.8）；仅 2024 单版本
- **首探中 ship-stopper（已入 D-046）**：scene_snapshot 真实会话报 'str' object has no attribute 'value'——scene_tools.py:124/visual_tools.py:86 传裸 "JSON" str 撞 client.py:344 result_type.value；execute_code=BaseMayaClient 共享实现故 Qt+native 双通道同炸；MCP execute_code 工具存活（server.py:306 先 ResultType() 转枚举）；**0.1.1 PyPI 在售版本 scene_* 面+视觉主路径全灭**
- **附带发现**：__init__.py __version__=0.1.0 vs pyproject 0.1.1 漂移
- 账本 49 条（D-001..D-049）；ADR 0001..0018；CONTEXT.md 32 术语（+human_verify 骨架测试/签名基线）

## 真源与上下文（先读这些）

- 决策账本 docs/decision-ledger.md（D-046..D-049=本轮 spec）
- ADR docs/adr/0018-issue7-real-maya-verification.md（本轮决策簇全录）
- issue #7 清单原文（6 真机项+4 API 审计项+status note）
- CONTEXT.md 32 术语；docs/testing.md 手动档基线
- 审计/实施报告 .scratch/maya-mcp-grill/reports/（前轮 T-10b 参考）

## 工作约定（承袭+新增）

- GitButler 专用（but；禁 git write）；文件写 Node.js fs+字节校验；每轮独立分支
- 每修复带回归测试；诚实档与代码档分 commit
- **活会话权限（D-047）**：场景变更/文件落盘/视觉/扰动全放行；**扰动类最后执行**；checkpoint 落盘限 workspace/checkpoints/
- **证据纪律（D-048）**：agent 执行+留证（transcript/图像/exit code→.scratch 报告+issue#7 评论）；**勾选权归用户**；partial/blocked 如实标
- 人工门：merge/tag/release/yank/分支保护/env reviewer/客户端实测=用户执行
- atomcode 调研串行单发；ctx 缺席走 exec 直跑

## 任务链（按序）

### T-13a 修复档（D-046 修前推进）

1. **result_type 缺陷修复**：建议 client.execute_code 入口 coerce（ResultType(result_type) 归一化，护住全部当前+未来调用方）或修两调用点传枚举——二选一由实现者定，推荐前者（边界归一比逐点修更韧）；**回归测试必须补传输缝**：str 入参→真 execute_code→fake transport 断言 wire payload（本轮失效根因=stub mock 掉 execute_code）；同扫 client_type.value 等同类 str-vs-enum 面（session_manager.py:203/371/431）
2. **__version__ 漂移修**：__init__.py 0.1.0→0.1.1（诚实档顺手修，独立 commit）
3. **修复合入后**：pid 3168 旧后端留作 as-shipped 证据面；修复码经直驱 client→Maya harness 验证（同传输绕 MCP 框架层）；MCP 面终验待用户自然重启

### T-13b manual-tier 固化（D-049a）

4. 新 marker（gui）+conftest 环境探测（无真 Maya 即 skip）+pyproject 注册 marker+--strict-markers；机器可断项真断言
5. 人眼项 human_verify 骨架测试（test 存在+打印人工步骤）；清单版本化

### T-13c 验证执行（D-047/048/049b）

6. **as-shipped 证据先采**：旧后端上复现 0.1.1 失败态（scene_* 报错 transcript）入报告——修复合入前
7. **Tier-2 mayapy 档**：D:maya2024Maya2024inmayapy.exe -m pytest tests/ -m mayapy（含 checkpoint/rollback reference-edit 硬用例）
8. **GUI Tier-3 活会话项**：viewport_snapshot pixel sanity（agent 读图判）/render_preview save-restore+净零副作用实证/verticalFlip 方向/modelPanel -camera 形态（2024；2025/2026→partial）
9. **PySide2 分帧通道**：会话已通=正向证据，正式留 transcript
10. **headless temp-file fallback**：mayapy 环境 R-2 项
11. **native commandPort 无 
 +500ms 读实证**：raw socket 探针（D-041 挂账项）
12. **签名审计**：visual_module ~10 调用人工对官方文档全量+mayapy inspect.signature 采集项目调用面→stub 自动 diff→signature-baseline.json+allowlist 入库；call-form smoke 补行为层
13. **连接扰动（最后）**：RST/FIN 杀连接语义（WinError64 真机面）
14. **多客户端渲染**：Devin/1mcp=一席（ImageContent 实际渲染已可用）；Inspector/Claude Code/Codex=blocked 待用户
15. **证据汇总**：.scratch/maya-mcp-grill/reports/ 验证报告+issue #7 评论（gh），checkbox 不勾

### T-13d 收尾（D-049c）

16. **0.1.2 patch 备单**：修复同类传输路径全验证过（execute_code 全调用形态/Qt/checkpoint/headless）→CHANGELOG [0.1.2]+版本 bump+发布人工门清单（merge/tag/release/yank 0.1.1）；release notes 按 tier 披露+known-issues
17. **既有未落人工门**：main 分支保护 contexts（lint「ruff budget gate」/mypy「mypy baseline gate」/test 四格/ci 聚合）+environment pypi required reviewer

## DoD checkbox

- [ ] result_type 修复+传输缝回归测试合入（str 入参不再炸，双通道同护）
- [ ] issue #7 真机项逐项执行+证据链入库（.scratch 报告+issue 评论）
- [ ] manual-tier pytest 档位可复跑（gui/human_verify marker 注册）
- [ ] signature-baseline.json+allowlist 入库
- [ ] 0.1.2 发布人工门清单备妥（含 yank 0.1.1 步骤）
- [ ] 证据报告区分 as-shipped(0.1.1 坏) vs post-fix(修后) 两态

## 负向清单

- grill/spec 期不动源码；checkbox 勾选权归用户不代勾
- GUI 断言不硬写（人眼项骨架化）；签名采集限项目调用面非全 API
- 0.1.2 门=修复同类路径验证≠issue #7 全绿（后者 v1.0.0 门不倒挂）
- 不杀 pid 3168 探 1mcp 重生行为（未知不主动试）；扰动测试排最后
- 不宣称 2025/2026 已验（单版本实测）；不把 partial 当 green
- 证据件留 .scratch 不入 git；不夹带无关源码改动

## 登记债（碰到再修，勿认领）

- 本轮新挂：PyPI yank 流程首次执行无本仓先例；mayapy 内 pytest 可用性待确认（若无 pytest 需 mayapy -m pip 装或裸脚本跑）；多客户端项（Inspector/Claude Code/Codex）blocked 待用户环境；Maya 2025/2026 覆盖缺
- 沿用 rev19.1：runtime deps lock 政策缓（fastmcp/psutil/platformdirs/PySide6 浮动）；mypy 2.x 输出格式变更重验；coverage patch 门触发=T-06 归置+真机档后；macOS 单冒烟触发条件不变；pre-commit.ci 不装；ruff format E501 ignore 评估已弱
- 沿用 rev17 长尾：T-06 休眠归置/T-07 validator/Poly Haven issue#2/ctx 沙箱 preload 缺陷/AE dormant 覆盖披露/Maya 2022+ commandPort 未公开/_suggest_layout 截断/checked-skipped 异构/orbit-shot 前缀/玄学评分/test_security:389 I001/AsyncMock/connection_guide 三连/ADR-0010 O-2/_probe_port 泄漏/native 丢 code/_visual_injected 重连/双胞胎 helpers/Scene.gui/OSError 白名单/ruff 原生 baseline(#1149)/but pr forge/pending publisher/ci↔release 重复/unavailable 消息丢 {e}/budget argv/Qt Raises

## suggested skills

-  / tdd — T-13a 修复与回归测试驱动
- （GitButler）— 全部版本控制写操作
- -research — 争议点调研（串行单发）
-  — 下轮翻页
- domain-modeling / neat-freak — CONTEXT.md/ADR 维护
