# Handoff — maya-mcp-grill 下一轮任务书（rev21）

> 规范路径（T-11a/D-041④）：docs/handoffs/next-round.md；账本=docs/decision-ledger.md；.scratch 仅存本地过程件。

## 本轮验收事实（非计划）

- **T-13 已结案**：`impl/t13a-result-type-coerce`（13+1 commits）+ `grill/round13-issue7-verification-spec`（2+1 commits）经审计 conditional pass 后合并 main 并 push；0.1.2 备单就绪（CHANGELOG/pyproject/__init__ 已 bump），**tag/release/yank 0.1.1/后端重启/issue #7 评论+勾选=用户门未动**
- **审计结论（T-13 轮）**：conditional pass —— 硬验收全部独立复现（pytest 590/10、gui 5/5 真机、ruff 83/83+29/29、mypy new=0、uv build 0.1.2、stdio 探针、pre-commit 8/8、直驱 harness 4/4）；mayapy blocked(env) 亲验属实（`import maya.standalone`→AV 0xC0000005）。审计报告 `.scratch/maya-mcp-grill/reports/2026-09-20-audit-t13.md`
- **审计返工已落（rev21 本 commit）**：ADR-0013:26 捕获路径修正注记；testing.md 补回 width/height metadata 项+`gui_session_required` batch 门挂账+`.scratch` machine-local 注记；`test_signature_baseline.py` 版本断言放宽为 `Maya \d{4}` 戳存在性
- **真机环境**：Maya 2024 GUI 活（Qt 分帧端口每次连接动态分配，native :7001 恒在，`MAYA_MCP_GUI_ADDR` 可缺省）；旧后端 pid 3168 跑 0.1.1 待用户重启换 0.1.2；mayapy/-batch 本机 env-blocked
- 账本 49 条（D-001..D-049）；ADR 0001..0018；CONTEXT.md 34 术语

## 真源与上下文（先读这些）

- 审计报告 `.scratch/maya-mcp-grill/reports/2026-09-20-audit-t13.md`（声明→证据→结论 23 行对照表，弱化/跑偏清单）
- T-13 实施报告 `.scratch/maya-mcp-grill/reports/2026-09-20-report.md`（§5 issue #7 逐项、§6 发布人工门七步）
- 决策账本 docs/decision-ledger.md；ADR docs/adr/0018-issue7-real-maya-verification.md
- issue #7 清单原文；CONTEXT.md；docs/testing.md 三层档定义

## 工作约定（承袭）

- GitButler 专用（but；禁 git write）；文件写 Node.js fs+字节校验；每轮独立分支
- 每修复带回归测试；诚实档与代码档分 commit
- 活会话权限沿用 D-047；扰动类最后执行；checkpoint 落盘限 scratch 区
- 证据纪律 D-048：agent 执行+留证→.scratch；勾选权归用户；partial/blocked 如实标
- 人工门：tag/release/yank/issue 勾选/后端重启/分支保护/env reviewer=用户执行
- atomcode 调研串行单发；ctx 缺席走 exec 直跑

## 任务链（按序）

### T-14a 弱点裁决（审计 §3.2 遗留，先 grill 后动）

1. **presence-baseline 追认或补强**：`signature-baseline.json` 实为 presence/method-list 基线（signature 全 null，cmds builtins 无可查签名+mayapy blocked）。裁决：更名 presence-baseline / meta 补注追认 / 健康机重采真签名——三选一立案
2. **call-form smoke 独立层取舍**：现由 gui 档实质承担；裁决独立成档 or spec 追认现覆盖
3. **visual_module ~10 调用对官方文档**：无独立对照表工件；裁决补表 or 并入 allowlist 理由追认
4. **MVector(MPoint) stub 继承拆解**：allowlist 化漂移债，裁决拆 or 留

### T-14b issue #7 残余清点（v1.0 定义性门）

5. 多客户端渲染席位：Inspector/Claude Code/Codex=用户环境项，出可执行 checklist 交用户
6. Maya 2025/2026 矩阵：MImage 双布局已备未验；human_verify 骨架含 modelPanel -camera 挂账项
7. mayapy env-blocked：换机或修环境；健康机上 `test_mayapy_smoke.py`+签名重采即解锁 Tier-2
8. headless temp-file fallback：随 7 解锁

### T-14c 发布链状态核对

9. 0.1.2：merge 已执行；核对 tag v0.1.2/release notes/PyPI 产物/yank 0.1.1 是否用户已落；issue #7 评论+勾选状态核对（不代勾）
10. 后端重启实证：用户重启后 `scene_*` 面经 1MCP 复测一遍收尾 D-046

### T-14d 登记债择题（ grill 出题，勿全吞 ）

- 高值候选：T-06 dormant aesthetic_engine 归置（ADR-0003 挂账）；ctx 沙箱 preload 缺陷；D-011 validator
- 长尾沿用 rev20 清单不变（PyPI yank 无先例仍适用——若 9 已执行则消）

## DoD checkbox

- [ ] 弱点裁决四项各有立案结论（补做 or spec 追认，不悬置）
- [ ] issue #7 残余项各自有主（agent 可跑项跑完留证；用户项出 checklist）
- [ ] 0.1.2 发布链逐环核对完毕（已落核销/未落列出）
- [ ] 重启后后端 scene_* 面复测 transcript 入库
- [ ] 新发现缺陷照例每修带回归钉

## 负向清单

- grill/spec 期不动源码；checkbox 勾选权归用户不代勾
- 裁决项只出结论不夹带实施（实施归实现阶段）
- 不宣称 2025/2026 已验；不把 partial 当 green；证据件留 .scratch 不入 git
- 用户门（tag/yank/重启/勾选/多客户端环境）不代执行不催促
- 提交前自查 markdown 内 `$`/`%`/反斜杠字面量未被壳层吞食（rev20 教训：技能名被剥、路径丢 `\` 进 git）

## 登记债（碰到再修，勿认领）

- 本轮新挂：signature-baseline 名实不符（presence≠signature）；next-round.md rev20 曾被壳层剥名（根因=写入路径模板展开，写作面须字面量自保）；testing.md 曾丢清单项（checklist 项迁移须全量映射自查）
- 沿用 rev20：PyPI yank 流程无本仓先例（若已执行则消）；多客户端项 blocked 待用户；Maya 2025/2026 覆盖缺；MVector(MPoint) 拆解低优先
- 沿用 rev19.1：runtime deps lock 政策缓（fastmcp/psutil/platformdirs/PySide6 浮动）；mypy 2.x 输出格式变更重验；coverage patch 门触发=T-06 归置+真机档后；macOS 单冒烟触发条件不变；pre-commit.ci 不装；ruff format E501 ignore 评估已弱
- 沿用 rev17 长尾：T-06 休眠归置/T-07 validator/Poly Haven issue#2/ctx 沙箱 preload 缺陷/AE dormant 覆盖披露/Maya 2022+ commandPort 未公开/_suggest_layout 截断/checked-skipped 异构/orbit-shot 前缀/玄学评分/test_security:389 I001/AsyncMock/connection_guide 三连/ADR-0010 O-2/_probe_port 泄漏/native 丢 code/_visual_injected 重连/双胞胎 helpers/Scene.gui/OSError 白名单/ruff 原生 baseline(#1149)/but pr forge/pending publisher/ci↔release 重复/unavailable 消息丢 {e}/budget argv/Qt Raises

## suggested skills

- $grill-me / $grill-with-docs — T-14 裁决项出题
- $implement / $tdd — 裁决后实施驱动
- $but（GitButler）— 全部版本控制写操作
- $atomcode-research — 争议点调研（串行单发）
- $handoff — 下轮翻页
- domain-modeling / neat-freak — CONTEXT.md/ADR 维护
