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

> 澄清注记（D-180②，R39 增补）：本表 scene_validate 行立法时误以 scene_plan 的 auto_fix 面为其面——真实 API 的 scene_validate 无 auto_fix 参数（签名为 rules/format/session_key），其披露义务实为「只读披露+修复导流+无变异故无 undo」语义；机检单源以修订版 0028-elements.yaml 为准（read_only_disclosure+repair_redirect(all:[scene_plan,auto_fix])+no_mutation_no_undo+会话前置）。A 案（裸否定词表极性守卫）否决依据实证存档：现行要素词表已含 5 个否定式 token（"not\s+undo"/"cannot be undone"/"no\s+undo"/"not\s+persist"/"does not persist"），一刀切守卫落地即自伤。

限流/安全管道等防护实现细节**不进必备**（TDQS 评描述对行为的透明度非防护清单；除非它改变调用者决策）。机检形态=`docs/adr/0028-elements.yaml` 单源清单（本 ADR 引用 + CI 消费——立法与断言同源防漂移）。

### 3. 消歧惯例=单向 `Boundary:` 行（D-174②）

每件工具描述内嵌一句 `Boundary:` 点名 1~3 个兄弟分工（扩用 `introspect_tools` 之 `scene_nodes` 既有先例）；**单向点名**——新工具自写边界句零改动旧件（双向=O(n²) 维护税；TDQS Appendix B 单侧 enforceable boundary 即满 5 分锚点）。九件消歧矩阵=elements.yaml 的 `boundary_targets`。
集中路由表对 TDQS **零贡献**（评审输入只看 name+description）；全局 instructions 仅跨模块分工用。
**禁句式**：「always call this first」类强制排序（spec 原话 "A boundary is describable; a priority is not"——写边界满分、写强制序反扣）。

### 4. 验收=复合判据（D-173②，D-182 重校准）

Glama 页面**字母档 A + min 逐工具 ≥3.0 + 零 annotation contradiction 旗标**——三要件全锚 TDQS spec 官方成文条款（字母档 A=≥3.5、「tier-B passing bar」逐件 ≥3.0、contradiction 自动 1 分+公开旗标），零推断成分。stretch=3.8 系本仓自设推断目标（乐观推演值非官方阈值，禁入对外宣称文本，D-149）。本地可用开源 tdqs repo 的 Appendix A/B prompt 预评——**仅作 PR 前回归参考，不入 CI 不作验收门**（Glama 生产 LLM 型号/温度未公开=官方自认管线唯一非确定性步骤，本地分与生产分不可对齐）。

> 原判据存照（R38 D-173② 立法原文，经 D-182 重校准不删）：「线上重评 ≥4.0（目标 4.2 防 round1 边界效应）+ min 逐工具 ≥3.0 无 C 级 + 零旗标」——4.0/4.2 系「字母档阈值官方未发文」期防御性推断；R39 复核 spec 正文已成文规定字母档（A=≥3.5/B=≥3.0「tier-B passing bar」），原推断值降 stretch 双轨，「无 C 级」并入 min≥3.0 蕴含。（GM-22-001 多基线惯例保留供审计。）

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
- 极性方向限定（D-190③）**仅由受守卫集合钉死强制，pattern 纯度无机检**（2026-10-02 审计实证）：否定式要素在同一子句通常既有正命中又有负命中，而 `negated_only = negated and not positive` 使 `matched=True`，故把 `polarity_aware` 挂到否定式 pattern 要素后 `check()` 返回 ok=True / 0 errors / 0 warnings（实测五件否定式要素 `execute_code/irreversible`、`scene_validate/read_only_disclosure`、`scene_validate/no_mutation_no_undo`、`write_module/overwrite_or_persistence_semantics`、`camera_orbit/non_idempotent` 全挂亦然）。断言层原理上测不出该违规；残余强制=人工 review。不做正则纯度 lint 的理由=那正是 D-180③/D-190③ 禁入立法面的未实测正则形态，且需自带语料验证窗。 〔结案注记 2026-10-02（R44，D-199）：改判为「挂载性=可证伪机械事实」——立法「每个 polarity_aware 要素随附否定语境 fixture+测试断言守卫开火产出 negated_only」，误挂载在写 fixture 时构造性不可表达（详见下方 R44 增补节）；人工 review 降格为过渡冗余非终点。〕
- 子句级否定窗换来的**假阴性（FN）面从未测量**（2026-10-02 审计提出）：D-190① 明知收窄方向以 FN 换 FP，但本窗只测了 FP 下降（naive 53 → 子句级 4），未构造任何真否定跨子句的语料来量 FN。此项直接卡住 D-190④ 的 warn→hard 升档——升档判据需要误拒分母，而反向的漏判分母尚无基线。 〔处置路径已立法 2026-10-02（R44，D-198）：FN 唯一合法分母=轨②手工标注判据集，轨③变异面只报计数不作分母；测量执行挂任务书，测得前此缺口保持 open 半结案态。〕
## R41 增补（D-188/D-190，2026-10-01）——判负决策树与极性硬化形态

**判负决策树（唯一真源=账本 D-188 行）**：Glama 重评后按可观测信号分四支——

| 分支 | 信号 | 归因假设 | 合法动作 |
|---|---|---|---|
| Br-a | 字母升档但某件 min<3.0 | 单件执行/描述质量 | 描述再修（非破坏）；结构性归因（如 schema 多类型/必填参数）→D-181③ schema/breaking 窗另裁 |
| Br-b | min 全过但整体仍 B | coherence 结构性拖（Disambiguation/Tool Count 文本够不到面） | 三档只记观察——P3 触发债条件①复合核验=「是-可即兑 / 是-实证义务已触发 / 否」+如实记读数；**P3 解冻判定权归 gate review 前置议题（ADR-0023 R41 登记块，D-192），本树不直接触发** |
| Br-c | Scored 时间戳不动 | PyPI-pull 实锤或更深缺口 | 0.6.0 publish 后 PyPI 拉取核验→仍不动则新缺口立项（D-182③+D-187③） |
| Br-d | annotation 旗标非零 | 描述自相矛盾 | 逐旗检修描述（最直接可修面） |

判据值源=账本 D-182① 三要件未减；判负≠缩门（D-171③ 车道隔离）；全过=验收（D-182②）→账本事件行+docs/evidence/ 快照归档+distribution-surfaces 同步；**Glama 徽章达标前禁写、达标后可选**（滚动宣称纪律 D-149/D-184③）。

**极性硬化形态立法（D-190，唯一真源=账本行）**：①子句级否定窗——cue 与 match 之间无子句边界才算否定（80char 固定窗=被淘汰的 NegEx 前形态；收窄方向 FP 必降，代价=跨子句真否定漏判归 FN 面，防假绿场景 FN 危害远低 FP）；②`0028-elements.yaml` 新增 `positive_exemptions` 要素级字段枚举合法否定式披露短语（ConText pseudo-trigger 同构——无豁免表则强制挂扩面时否定式 pattern 要素全自伤）；③方向限定条款——`polarity_aware: true` 强制挂载仅限 pattern 集纯肯定式的 mutation 存在性断言（现行唯一实例=camera_orbit/mutation_side_effects）；否定式 pattern 要素不挂守卫、其保护走豁免表；④warn 起步挂 0.6.0 preflight 复核——分母=被判 negated_only 的 polarity_aware 要素数、分子=其中实为合法肯定披露，零误拒→升 hard、>30%→退人工抽查。切分符/cue 表/豁免短语清单禁入立法行只进执行窗产物（D-180③）；warn 降级仅限 negated_only 分支，P0/Boundary 存在性判定保持 hard。

**执行窗落地注记（D-190，2026-10-02）**：立法面只到形态层，机制清单按 D-180③ 纪律不入本节。清单落点两处且互不重叠——**子句切分符集合 + cue 表**属机制形态，单源在 `.github/scripts/check_tdqs_disclosure.py`（`CLAUSE_BOUNDARIES` / `NEGATION_CUES`）；**要素级豁免短语**属要素数据，与其余要素字段同处 `docs/adr/0028-elements.yaml` 的 `positive_exemptions`（含 D-190③ 方向限定条款）。落地判据（常驻可复跑）= 主测面零误拒，由 `tests/test_check_tdqs_disclosure.py::test_live_corpus_has_no_polarity_warnings` 断言；方向限定条款（D-190③）的强制方式是**受守卫集合精确钉死**，不是警告机制：测试常量 `LEGISLATED_GUARDED` 断言受守卫集合恰为 `camera_orbit/mutation_side_effects`，任何新增挂载即转红（2026-10-02 实测：给 `scene_validate/read_only_disclosure` 挂守卫 → `AssertionError: guarded set drifted`，exit 1）。**钉死式强制不覆盖 pattern 纯度**——见下方缺口披露第 4 条。压测面计数由 `.github/scripts/polarity_corpus_probe.py`（手工测量件，不入 CI）两轨分报：主测 36 要素 / 1 挂守卫 / 0 误拒；压测 287 个带 docstring 的函数 × 全要素 pattern = 357 匹配，naive 80 字符窗 53 → 子句级 4（**子句收窄**赦免 49 次 naive 误拒；`positive_exemptions` 豁免表今日改变判定 0 次，测得值见探针 `exemption_list_changed_verdicts=0`——勿把两者混为一谈）。分母口径注记（D-191①c）：早前证据中的 264 系探针把 docstring 按裸函数名收进单个 dict、塌缩 23 个同名函数所致，非语料属性，勿与 287 直接比较。warn → hard 仍待 0.6.0 preflight 复核（D-189）。

## R44 增补（D-195/D-196/D-198/D-199/D-200，2026-10-02）——零断言地板、三轨语料与 fixture 开火

**枚举完整性断言（D-195）**：checker 新增覆盖率面——`pipeline.py` `TOOL_ANNOTATIONS` 每个键必须在 `0028-elements.yaml` 出现（挂要素或显式 `exempt`+理由字段），缺席即 CI 红；登记断言立即全员强制、零存量豁免（账本完整性非质量负担）。**推导最低集**：按签名事实推导必挂要素——带 `session_key`→`session_prerequisite` 必挂、有功能兄弟面→`boundary_line`+`boundary_targets_named` 必挂；对新增/被修改工具立即生效，存量 13 件限期一个 minor 窗收敛（补挂或显式 exempt），此后只收紧不放松。推导映射表实现为 checker 代码内常量+测试、走 PR 评审，不落版本化文档（D-191① 冲突缓解经呈报采纳）。接 CI 红前必先对现有 25 件 dry-run 验误报；mutation 工具推导最低集沿用极性感知，覆盖率层禁引入极性盲断言。

**scene_measure 处置（D-196）**：tier=P1+推导最低集三件入 yaml（PR review 义务照常触发，D-175④）；描述批按四失分维度回写——Boundary 行点名兄弟+使用触发句+行为语境（session 前提/只读幂等）+mode 语义差异补 schema 之缺；删 docstring 中 schema 已覆盖的参数枚举复述段（Conciseness 权重 10% 同样因复述扣分）；验收门维持既定三要件（tier A+min≥3.0+零旗标），「五维≥4」降格为质量志向非门——第三方 LLM 评分方差不可作验收方差。

**三轨语料口径（D-198）**：轨①287 真实 docstring=FP/赦免面；轨②手工合成标注判据集=**唯一合法 FN 分母**（每条须一句可独立辩护的标注理由）；轨③程序化变异集=压测/覆盖面，只报绝对数与构式覆盖、**永不作分母**，样本经人工确认真否定可晋升轨②。三类标签=真否定应触发/否定式披露应赦免/跨子句按设计漏判——第三类计「设计已知限制」计数而非 FN（不阻断 hard 化，须显式区分防混入分母）。hard 准入双要件=主测零误拒（已达成）AND 轨② FN 率≤阈值——阈值先记录不设阈、测得后再立法。三轨数字禁同现一个比值（D-191①c 口径注记扩展）；标签枚举清单只进执行产物。

**fixture 开火立法（D-199）**：每个 `polarity_aware` 要素须随附一条否定语境 fixture 样本+测试断言守卫开火（产出 `negated_only`）——「能写出开火 fixture」与「守卫可挂载」在体系内逻辑等价=构造性排除（误挂载在写 fixture 时即不可表达）。分档：缺 fixture→warn、fixture 不开火→error 立即（硬逻辑违规非风格），存量补齐后缺 fixture 亦升 error。fixture 原料复用轨②判据集「真否定应触发」类样本（同源语料喂两机制，防手工造句绕过正命中路径的假绿）；`LEGISLATED_GUARDED` 钉死集合×fixture 清单交叉断言（fixture⊆guarded 双锚）；PR 复核行保留为过渡冗余不升格为准机制。

**三待裁项清零（D-200）**：①warn→hard 老 0/1 分母口径作废——判据=D-198 双要件+最小样本量下限内置（轨②未达下限时第二要件判「未可判」维持 warn；Ro3 惯例参照 n≥30、本仓可另定口径，此为类比推理无直接判例）；②`positive_exemptions` 保留作前向守卫（YAGNI 不适用于防御性机制）+实测零改判如实注记维持+触发条件式出口锚——「若挂载规则扩面仍未产生首次改判届时按 YAGNI 复议移除」；③known-gap 注册表=本 ADR 缺口披露节常设章节+账本债行指针（「找家≠新建房产」，T-R42-09 结案无新面），披露节只记「缺口+影响面+兜底」不长成运维手册。

## R45 增补（D-203/D-204，2026-10-02）——样本量地板立法与豁免到期分级

**样本量地板立法（D-203）**：`MIN_ADJUDICABLE` 的计数基从全语料收窄为**判决承载标签子集**（`true_negative`+`forgiven`）——`known_limitation` 类剔除：探针 mismatch 判定本就只对 TN/F 标签生效，KL 连判决参与资格都没有（同函数内 FN 分母排 KL 而地板含 KL=内部不一致，D-198④「防混入分母」精神同型覆盖）。值 12 的立法理由=**覆盖论证非统计论证**：12 ≥ 轨③ 的 8 个构式类（4 cue×prefix+4 split）+豁免短语族 2+余量 2=「每个已知构式类至少一条判决承载样本」的 test262 式最小工程面（如实标注工程推导/类比非判例）。新增 per-element 下限=每受守卫要素 ≥3 TN（防守卫扩面时语料未长的稀释）。Ro3（n≥30）移位声明：不作地板锚（其管零事件率上界非标签一致性），移作 D-198⑤「FN 率阈值」未来立法的参照锚。探针常量注释挂 D-203；未达地板维持「未可判」warn 不升 hard。

**豁免到期分级（D-204）**：`coverage_exemptions` 到期行为分两档——`current==due`→逐件 `::warning`、`current>due`→`::error` 逐件点名（Django 两周期阶梯/C# 分版本升级同构；业界无「due 即 error」单跳先例）。即时牙=release-preflight 第 8 行（见 ADR-0023）：到期豁免未消解且未显式延期→no-go。延期须满足 D-168 waiver 续期五要件（owner 外重签+续期上限）防无限续期掏空。读不到 pyproject 版本维持 warn（不可评估≠违规）。两牙独立冗余：机械牙不靠人、即时牙不靠版本 bump。

## 关联

- 前置：ADR-0012（对标与宣称纪律链）、ADR-0023（发布门三态——本轮为 listing 面非门清单项）、ADR-0027（消歧惯例先例出处域）
- 同步工件：`docs/adr/0028-elements.yaml`（单源）、`docs/evidence/gate-waiver-list-1.0.0.json`（无涉——本轮非门面）、`docs/distribution-surfaces.md`（Glama 行同步）

### 执行窗结果（R44 执行窗 + 独立审计，2026-10-02）

上述「存量 13 件」是立法时的零断言数，本节不改写该记录（保留多基线供审计，GM-22-001），只记录实际执行结果：

- **13 → 12**：执行窗已将 `scene_measure` 补入覆盖面，实际 `coverage_exemptions` = **12 件**，每件带 `reason` + `due`（`0.7.0`）。
- **推导债 8 对不在豁免表**：它们是已带完整 `tools` 条目、但缺一个可推导要素的工具；覆盖与豁免互斥本身就是门规，所以这 8 对只能存在 checker 内的 `DERIVATION_BASELINE` 常量里。
- **`due` 已接机制**：checker 把 `due` 解析为版本号与 `pyproject.toml` 的 `version` 比较，到期点名不刷。不可解析的 `due` 报错；读不到版本号时报 **warning**（避免静默过期）。
- **事实更正（F1，P0）**：`scene_measure` 首版重写曾写错 `clearance` 语义（断言「0 意味着各轴恰好相切」，实际可能是两轴穿透+一轴相切仍返回 0），已按 `maya_scene_module.py` 实现重写并补 stub 回归用例。
