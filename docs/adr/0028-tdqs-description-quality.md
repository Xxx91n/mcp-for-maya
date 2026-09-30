# ADR-0028 — 工具描述质量立法：TDQS 披露要素集、单向 Boundary: 消歧惯例与要素存在性棘爪

状态：accepted（grill 定稿）
日期：2026-09-30
决策来源：D-172/D-173/D-174/D-175（R38 Glama TDQS B→A 提分题面四轮裁决）
证据面：Glama 页 TDQS 实况（B 3.4/5.0，2026-09-30 06:25 UTC）+ tdqs.dev/spec v1.2 + glama.ai/mcp/methodology + glama-ai/tool-definition-quality-score 开源 repo + Anthropic writing-tools-for-agents

## 背景

- Glama 对本 server 的 TDQS 评分 **B 3.4/5.0**（across 25 tools）：服务器级 Disambiguation 3/5（九个 scene_* 分析工具概念重叠）、Naming 4/5、Tool Count 3/5（25 件居 16~25 重端带顶）、Completeness 4/5；逐工具最弱点 `execute_code` C 2.9（未披露任意代码全权限执行+不可逆+result_type 信封）、`write_module` B 3.2、`scene_validate` A 3.5（auto_fix 变异未披露）。
- TDQS 聚合公式（官方 spec 原文）：`descQuality = 0.6×mean + 0.4×min`（min 项刻意加权——"a single garbage definition degrades selection across the whole set"）；`overall = 0.7×descQuality + 0.3×coherence`（四维等权）；tool-count 带 5 分=3~15 / 3 分=16~25 / 2 分=26+。
- 重评机制：Glama 自 **GitHub HEAD** build（methodology §1.2 "reflects the current state of the repository within minutes of a push"；tools/list 采集源=Firecracker 沙箱内源码 build 实例）；inputHash 增量继承；coherence 有独立 watermark 触发器（消歧文案须同批提交保评审一致性）。

## 决策

### 1. 提分路径=描述层非破坏改造（D-172α/D-173①）

窄焦批一 PR 收口（P0 三件重写 + P1 九件消歧 + P2 annotations 校正），预估 150~350 行 diff（落 200~400 行评审甜区）；P3 工具合并（25→~15 mode 参数化）**显式推迟单独立项**——API breaking 须 semver major+迁移期，不为 3→5 分带做一次 breaking release。

### 2. 强制披露要素集（D-174①，对照 TDQS Behavior/Completeness 5 分锚点立法）

| 工具 | 必备要素 |
|---|---|
| `execute_code` | 任意代码全权限执行 / 效果不可逆 / result_type 返回信封 / 会话前置 |
| `scene_validate` | auto_fix 二态披露（false 只读检查 / true 变异场景）/ 变异时不可逆 / 会话前置 |
| `write_module` | 会话前置 / 不可逆（overwrite 语义）/ 与 execute_code 的 when/when-not 边界句 |

限流/安全管道等防护实现细节**不进必备**（TDQS 评描述对行为的透明度非防护清单；除非它改变调用者决策）。机检形态=`docs/adr/0028-elements.yaml` 单源清单（本 ADR 引用 + CI 消费——立法与断言同源防漂移）。

### 3. 消歧惯例=单向 `Boundary:` 行（D-174②）

每件工具描述内嵌一句 `Boundary:` 点名 1~3 个兄弟分工（扩用 `introspect_tools` 之 `scene_nodes` 既有先例）；**单向点名**——新工具自写边界句零改动旧件（双向=O(n²) 维护税；TDQS Appendix B 单侧 enforceable boundary 即满 5 分锚点）。九件消歧矩阵=elements.yaml 的 `boundary_targets`。
集中路由表对 TDQS **零贡献**（评审输入只看 name+description）；全局 instructions 仅跨模块分工用。
**禁句式**：「always call this first」类强制排序（spec 原话 "A boundary is describable; a priority is not"——写边界满分、写强制序反扣）。

### 4. 验收=复合判据（D-173②）

Glama 线上重评 **≥4.0（目标 4.2 防 round1 边界效应）+ min 逐工具 ≥3.0 无 C 级 + 零 annotation contradiction 旗标**。本地可用开源 tdqs repo 的 Appendix A/B prompt 预评——**仅作 PR 前回归参考，不入 CI 不作验收门**（Glama 生产 LLM 型号/温度未公开=官方自认管线唯一非确定性步骤，本地分与生产分不可对齐）。

### 5. 生效面与发版纪律（D-175①③）

**merge to main 即触发重评，不为描述文本单独发版**——描述改动搭下一实质变更的发版车（server.json+Registry publish 绑发版既有立法不变）。残余缺口：Glama 推断构建若从 PyPI 拉包则 merge 不生效——**金丝雀校验**：首个纯描述 commit merge 后观察页面 last-scanned 时间戳+分数变化定分支。

### 6. 防回归棘爪=要素存在性 hard gate（D-175④⑥）

CI 断言「结构化要素存在」非「关键词字面」（`Boundary:` 行=自造结构分隔符=合法断言对象，措辞自由度在行内容）；要素单源=elements.yaml；失败信息须指明缺失要素 id；**elements.yaml 变更须 PR 显式 review**（防改措辞顺手删断言）；个别实测误报高断言可降 warn，Boundary:/P0 要素类保持 hard。无需 baseline 文件（要素全齐后无存量豁免问题）。

## 被否选项

- **全量审计批**（25 件逐件重写）：分差高度集中时 Delimit 式全量动机不成立+评审稀释致校准审查系统性失真（>1000 行 <50% 检测率——描述失真比平庸扣分更重）。
- **最小锚点批**（只修 execute_code）：min 项消解但 Disambiguation 3/5 封 coherence 3.25→总分≈3.9 恰好卡 A 带线下。
- **分值棘爪**（存 25 件分值基线比对）：LLM 步=官方自认唯一非确定性步骤，假阳性不可归因。
- **字面关键词断言**：快照脆性（合法措辞迭代误报）；断言对象=要素存在非措辞。
- **双向 Boundary:**：O(n²) 维护税且评分不要求对称性。
- **虚假披露/关键词堆砌**：annotation contradiction=自动 1 分+公开旗标、Conciseness 维反扣。
- **B/C 文规约形态**（治理窗逐字定稿终稿 / 仅账本行承载）：前者违「grill 不改源码」分工+让 ADR 承载高变异措辞；后者无法承载正向要素清单、验收无对照锚点。

## 后果

- **描述文本=宣称文本**：每句可验证+描述↔annotations 零矛盾——D-149② 校准纪律在 TDQS 向的正向一致延伸（披露不足扣分/虚假披露定罪，两向同罪）。
- **联动面强制**：`pipeline.py` TOOL_ANNOTATIONS（scene_validate destructive 语义一致）、`server.py` instructions（边界句同义）、`docs/threat-model.md`（execute_code 任意代码披露双向对齐，防「文档承认了但威胁模型没记」或反向矛盾）；README 不进 TDQS 输入=低优先同步。
- **判据立法/措辞执行两分**：要素清单入本 ADR+elements.yaml（跨轮有效、难逆转），终稿措辞=执行窗产物走人工过目。
- **验收凭据**：merge 后 Glama 页重评读数→账本事件行+distribution-surfaces.md 同步。

## 缺口披露

- Glama 各字母带阈值官方未发文（≥4.0/目标 4.2 系边界余量防御性推断）；生产评分 LLM 型号/温度未公开。
- Dockerfile 分支（推断构建走 PyPI 拉包时 merge 不生效）置信度中——金丝雀实验兜底。
- TDQS 对消歧形态无逐项官方表态（内嵌胜出系 Appendix B 评审输入面高置信推断）。

## 关联

- 前置：ADR-0012（对标与宣称纪律链）、ADR-0023（发布门三态——本轮为 listing 面非门清单项）、ADR-0027（消歧惯例先例出处域）
- 同步工件：`docs/adr/0028-elements.yaml`（单源）、`docs/evidence/gate-waiver-list-1.0.0.json`（无涉——本轮非门面）、`docs/distribution-surfaces.md`（Glama 行同步）
