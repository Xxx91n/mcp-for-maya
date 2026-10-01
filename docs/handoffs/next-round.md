---
generated: 2026-10-01
from_round: R41（Glama TDQS B→A 落地链路+机制收口 grill 定稿 + 对账整理闭环，覆盖 D-185~193）
ledger_head: canonical=D-193（D-185..193 已随本批迁入）；.scratch/r41/decision-ledger.md 过程件按 append-only 留档不删——本文件「附」节 verbatim 副本已迁入留档勿重迁
branch: grill/round41-gate-path（本整理批，未 merge）+ 既有三 lane 未 push：grill/round39-tdqs-closeout（gr，yos+ppw）/ exec/r40-tdqs-closeout（P-A，qkn）/ exec/r40-evidence-anchors（P-B，zry）——push/PR 未授权
---

# 下轮任务书（rev52）

## 状态总览（R41 收口）

- **Glama 实况**：页面仍 B 3.4/5.0（Scored 2026-09-30 06:25 未动，25 tools）——P-A/P-B/gr 三 lane 全部落地完毕但**未 push**；B 态根因=改进批未出本地，非文本质量剩余缺陷。
- **R41 九裁决全落账**（D-185..193，见附节 verbatim + canonical）：收口窗范围 / 三独立 PR 编排（gr→P-A→P-B+互链序声明+原子声明+gr merge 金丝雀对照点）/ 0.6.0 minor 车选 / 重评验收+四分支判负预案 / evidence-anchor expiry 复核规程（preflight 第 7 行）/ 极性硬化形态立法（子句窗+positive_exemptions+方向限定+双档判据）/ 杂项三面计数口径 / P3 前置议题登记块（ADR-0023）/ 本批编排（本 lane）。
- **立法批本批已落盘**：canonical 迁入 9 行 + ADR-0023 R41 增补块（车选/preflight 第 7 行/门测量口径/P3 登记块）+ ADR-0028 R41 增补节（判负决策树+极性硬化形态）+ CONTEXT 三新词+一注记 + 本任务书。
- **调研存档**：.scratch/r41/research-q1.md ~ research-q6.md（atomcode 六轮；q7~q9 直裁无调研）。
- **审计 loop2 机件实测在案**：TDQS 36/12 OK / anchors 40 warn exit 0 / 极性语料 264docstrings→339 匹配 53 落 naive 窗（主因=无子句边界非 cue 表）。

---

## T-R42-01：三 PR 编排执行（push 授权后）

覆盖 D-186 + D-184②④⑤ + D-193。

1. `but push` 三 lane + `but pr new` 各开独立 PR——merge 序=gr（docs）→P-A→P-B；三 PR 描述互链+序声明行；P-A/P-B 各带「账本迁入/revised 属被修对象原子记录面」声明（D-109③/D-153①）。
2. gr merge 当金丝雀对照点：merge 后看 Glama last-scanned 动不动=HEAD-build vs PyPI-pull 判别素材（账本只写观察，D-129）。
3. elements.yaml 禁跨 PR 分批改（D-175④）——R40+R41 的 yaml 改动须全在 P-A 面一次 review 完。
4. **勿 push 除非用户令**——授权语义本批沿用。

## T-R42-02：极性硬化执行批（P-A lane 追加 commit 或 P-A merge 后独立小 PR，执行编排裁定）

覆盖 D-190 + D-180③。

1. `_negated` 窗口改子句级——cue 与 match 之间有子句边界则不判否定；切分符集合=执行窗产物（禁回立法行）。
2. `0028-elements.yaml` 新增 `positive_exemptions` 要素级字段枚举合法否定式披露短语（如 "not idempotent"）。
3. `polarity_aware: true` 强制挂仅限纯肯定式 pattern 的 mutation 存在性断言（现行唯一实例=camera_orbit/mutation_side_effects）；否定式 pattern 要素不挂守卫走豁免表。
4. 仍 warn 起步（negated_only→::warning::）；测试：跨子句 cue 不误伤/同子句豁免短语不误伤/肯定式漏报仍 error。
5. 语料分母口径先行（D-191①c）：主测=真实校验面（工具↔其要素）+压测=264 docstrings 笛卡尔积——两轨分别报数禁混淆。

## T-R42-03：0.6.0 发版链（人工确认门后执行）

覆盖 D-187 + D-084/D-143/D-150③ 惯例。

preflight 全过（含新第 7 行 expiry 复核=T-R42-04）→ 人工确认门点头 → `git tag -a v0.6.0`（annotated 惯例）→ push tag → release.yml PyPI → GH Release 页（minor 义务位兑现）→ PyPI 双车道复核见 0.6.0（T-30i/D-142γ 同型）。

## T-R42-04：evidence-anchor expiry 复核首跑（随 0.6.0 preflight）

覆盖 D-189 + D-183③④。

按 ADR-0023 R41 增补第 7 行执行：分桶（裸 path:line=合法 advisory 不计分母 / 可硬化类逐条人工核验）→ FP/(TP+FP) 仅对可硬化类 → 判据直引 D-183④（零/低→升 hard；>30%→退人工抽查+修 checker 债）→ 账本事件行+分类工件归档 docs/evidence/。存量 ~40 条裸 path:line=登记升级债逐步消化不强清零（T-R42-08）。

## T-R42-05：Glama 重评验收（Scored 事件触发）

覆盖 D-188 + D-182①②③。

三步核验=字母档+min 逐件+旗标零；判负走 ADR-0028 R41 增补四分支树（Br-a 执行质量返修或 D-181③ schema 窗 / Br-b 触发态三档只记观察 P3 解冻权归门审 / Br-c PyPI-pull 核验开新缺口 / Br-d 逐旗检修）；达标=账本事件行+docs/evidence/ 页快照归档+distribution-surfaces 同步+徽章可选（**达标前禁写**）。

## T-R42-06：金丝雀观察窗（持续，非 PR）

覆盖 D-182③ + D-187③。观测点=gr merge 后时间戳 / 0.6.0 publish 后时间戳；账本只写观察。

## T-R42-07：P3 复议议程材料填充（门审召集窗）

覆盖 D-192 + D-179②③。ADR-0023 R41 登记块为骨架本体；召集窗按当刻快照填证据指针（Glama 批后维度读数/客户端实测/工具面计数）；**禁预填判决倾向**。

## T-R42-08：升级债+housekeeping 承继

覆盖 D-189⑦ + rev50 遗留项。

- 存量 ~40 条裸 `path:line` 锚点按白名单优先级逐步升级（触发债登记，非本窗清零义务）。
- housekeeping 遗留：license 文件残留判断 / mystubs CI 页脚残留 / Glama 收录动作绑维护页签期窗（等首次门检结果定剪除窗口）/ sync matrix 单任务字段修剪 / docs/testing.md 增量轮更新。

## T-R42-09：known-gap 登记（tools/list live 捕获局限）

覆盖 D-191②。审计部分 PASS 项——处置=按 D-183⑤ 模板挂「环境+退出码+工件落点」三联证据指针入 known-gap 登记，非缺陷。

---

## 承继项（自 rev48~51 不变）

- **叙事窗 γ**：轻叙事只描已验证面；重叙事仍锁（v1.0.0 门审或框5像素面先到）。
- **债消解信号常备**：mayapy/Linux env、框5 像素面见证、第二站 VP2、Maya 2025/2026 装机——到场即门检落新快照。
- **门审召集**：归 user 裁量。
- **观察窗**：10-30 D-146 核销 / awesome PR #15382（OPEN）合并跟踪 / Glama Scored 时间戳（金丝雀）。
- **审计残余**：R2 根因 probe JSON 补强（可选）/ R3 拆行配额规则下次拆行立法 / R4 顺手补。

## 边界警示

- 执行窗≠grill 窗：措辞终稿+极性切分符/cue 表/豁免短语清单全归执行窗产物（D-174③/D-180③/D-190 负①）——立法只到形态层。
- P3 工具合并仍锁——D-179 立法推迟至 gate review 复议；合并集仅限同构子集（D-094 硬约束），异构合并须先 revise D-094；Br-b 观察≠P3 解冻（D-192 登记块才持判定权）。
- atomcode 件跨会话污染警惕延续（正确 slug=Xxx91n/mcp-for-maya）。
- 续期上限每行 2 次不变；debt_owner/gate_authority 拆词已立法。
- 勿 push/PR 除非用户令；版本控制走 but。
- elements.yaml=单源件（D-175④）：任何变更走 PR 显式 review，禁跨 PR 分批改。
- stretch=3.8 禁入对外宣称文本（D-149）；Glama 徽章达标前禁写（D-188）。
- 0.6.0 发版动作前须有人工确认门点头（D-187）；annotated tag 惯例（D-150③）。

## Suggested skills

- $implement：T-R42-02 极性硬化执行批（checker+yaml+测试）
- $but：三 lane push/PR 编排（T-R42-01）+0.6.0 tag（T-R42-03）
- $tdd：极性窗/豁免表测试随行为同 commit
- $code-review：P-A 追加 commit 前自审
- $atomcode-research：新题面调研（串行一次一跑）
- $domain-modeling：新词再落；$handoff：再交接时续写

---

## 附：R39 会话账本 verbatim（已迁入 canonical D-177..184——本区留档对照勿重迁；canonical 行还额外带 scoped revised 注记）

| D-177 | R39-Q1 题面范围裁决（A 窄窗=handoff 三件：S-02 ADR-0028 §2 表述失配/S-03 elements.yaml 断言极性盲视/证据纪律一般化；B TDQS 收口窗=三件+camera_orbit C2.9 缺口+重评触发时机+P3 推迟复核；C 全开=B+P3 工具合并解冻裁决） | 我倾向C，但是将当前问题完整提交 atomcode-research 深度调研，调研时必须回顾：decision-ledger 中全部 current 记录、docs/adr 与 CONTEXT.md 现有条目、工业界成熟落地的心智模型（重点），给出推荐与理由。调研的结果辩证性看待。若调研结论与账本中任何 current 决策冲突：禁止静默改向——把对应 D-xxx 标记为 revised（保留原记录），生成新的 D-xxx 记录呈报给我，等我拍板后才继续下探。 | R39 题面=全开五件：S-02 立法文本失配修法 + S-03 断言极性盲视修法 + 证据纪律一般化 + camera_orbit C2.9 漏网处置 + Glama 重评触发路径 + P3（25→~15 mode 参数化合并）推迟依据复核/解冻裁决；裁决前置=atomcode-research 深研一轮，输入须含账本全 current 记录+ADR 全量+CONTEXT+工业界成熟心智模型，产出=逐题推荐+理由 | ①调研结论辩证看待不照单全收；②若与任何 current D-xxx 冲突→禁止静默改向：原记录标 revised（保留原记录）+生成新 D-xxx 呈报、等拍板后才继续下探；③atomcode 串行一次一跑（skill 硬护栏）；④grill 中不动源码、不另设目标 | revised（最终选 B，见 D-178；调研前置委托已执行完毕）|
| D-178 | R39-Q1' 题面范围裁决（atomcode 调研后重选同一题：A 窄窗=仅 handoff 三件；B TDQS 收口窗=三件照做+camera_orbit 处置+重评触发/验收复核+P3 推迟依据复核；C 全开=B+P3 解冻裁决） | 采纳B。但是我要重新给你提醒一下，atomcode调研之后给你的是要你改进Q的选项，而不是让Q++，不是让问题序号i++，所以我相当于是重新选中Q1的答案。Q2要重新出 | R39 题面=收口窗五件：S-02 ADR-0028 §2 表述失配修法 + S-03 elements.yaml 断言极性盲视修法 + 证据纪律（P-03b）一般化 + camera_orbit C2.9 处置 + Glama 重评触发/复合验收复核 + P3 推迟依据复核（不解冻裁决只复核依据）；调研四题推荐（P3 不解冻/camera_orbit 补描述/③两翼修法+澄清注记/金丝雀绑 0.5.0）作各题选项素材不自动成立 | ①atomcode 调研定位=改进当前题选项，禁 Q++ 前移（用户纠正的协议）；②题③ 推荐与 D-172α/D-174① 冲突→按 D-177② 呈报程序走（标 revised+新记录+拍板后下探）；③grill 不动源码；④P3 本轮只复核推迟依据非解冻裁决（C 的增量部分被调研结论吸收：不解冻） | current |
| D-179 | R39-Q2' P3（25→~15 工具合并）推迟依据复核（atomcode 调研辩证版：semver §4/cluster-api VERSIONING 攒批惯例/c2pa-rs 弃用政策/Kevin Tan tool-sprawl 实证/Anthropic 参数化合并指引；本地核验 D-094 异构禁令+CONTEXT「TDQS」_Avoid 原文成立；置信度高） | 采纳 | B=维持推迟+增补复议点：①推迟理由锚修正——真理由=D-094 异构合并禁令（九件 scene_* 异构、可合并集仅限同构子集、「25→15」目标数未证待重论证）+在飞 P0-P2 描述批撞车+gate 三态清账带宽，非「semver major 成本」（0.x breaking 合法，semver §4）；②v1.0.0 gate review 设为 API 面冻结前 P3 最后复议点——作 gate review 前置独立议题（非门清单行），届时按设计面裁决（同构族测试=3+ 操作共享大部分参数；合并前须 LLM 驱动实测选错率）；③gate review 裁不合并→P3 转触发条件债（三条件：Boundary 批后 Disambiguation 仍 3/5 且真实客户端实证选错/Glama 调分带收益归零自动作废/工具面越~35 件转可用性题）；④D-172β 不标 revised（结论不变），承接注记修理由锚（D-108② 先例）；CONTEXT「TDQS」_Avoid 行「semver major 裁决」表述同步注记 | 负向：①合并集仅限同构子集——异构合并伤参数准确率（D-094 硬约束，修订须先 revise D-094）；②P3 复议禁塞进门清单行（加行=扩门须另立法，D-171 豁免/缩门车道隔离）；③gate review 前若现真实客户端选错实证→按触发条件债提前解冻不等 gate；④合并若落地而拒发 major（静默 1.x 内做）=违 D-131 冻结承诺禁止；⑤调研结论辩证看待已履行（保留 A/C 否决理由+B 证伪点入库） | current |
| D-180 | R39-Q3' S-02/S-03 修法裁决（atomcode 调研辩证版：BMC Bioinformatics 2023 否定辖域误报 41%+okfctl prose 门 v1 ~75% FP+Google Error Prone ERROR 级零误报基准+GOV.UK ADR 立法粒度惯例；本地增量实锤=irreversible_when_mutating/overwrite_or_persistence_semantics 词表已含 5 个否定式 token；置信度高） | 采纳 | B=两翼分责：①elements.yaml scene_validate 要素改写对齐真实 API——autofix_two_state/autofix_mutation→read_only_disclosure+repair_redirect(all:[scene_plan,auto_fix])+irreversible_when_mutating→no_mutation_no_undo；②ADR-0028 §2 走 D-038② 澄清注记（accepted 不动+注记写明真实 API 无 auto_fix/立法时误以 scene_plan 的 auto_fix 面为其面/机检单源以修订版 yaml 为准；注记须录入「现行词表已含 5 个否定式 token」实证作 A 案否决依据）；③checker 只立法「mutation 类存在性断言须极性感知」原则——机制形态（窗口宽度/否定词表/正向豁免表）归执行窗，经 25 条语料零误报实测后落地、初上可先 warn 观察期再升 hard（D-175④ 逃生门忠实实现） | 负向：①D-172α/D-174① 的 scene_validate 要素行标 scoped revised（原记录保留+scoped 指针，D-163③/D-040 先例）；②极性盲视按一类缺陷立法原则非个案（write_module/export 未来 mutation 断言同受其辖）；③禁把未实测正则形态钉进立法；④yaml 变更走 D-175④ PR 显式 review 逃生门；⑤修立法不修描述——已上描述是正确披露，反向改描述暗示有 auto_fix=虚假披露（D-172γ 罪重向） | current |
| D-181 | R39-Q4' camera_orbit C2.9 处置裁决（atomcode 调研辩证版：TDQS spec 行为维锚点+arXiv 2602.14878 smell 实证+Glama methodology 选中率+Anthropic writing-tools；调研一处事实错误已纠正——「D-173 批未执行」不实，P0-P2 批已 merge=PR #58，按调研自身判据落 merge 后单开分支；置信度选项裁定高/重写后达 3.0 中） | 采纳 | A=单件重写+新开小 PR：①描述五要素——副作用披露（创建相机+动画曲线改场景+mark_dirty）/非幂等（重复调用产生额外相机）/会话前置/center JSON string 参数语义/Boundary: 单向点名 camera_create；精准命中 Behavior/Usage 两个 2 分维+Params 3 分低垂果实；②camera_orbit 要素行同 PR 入 0028-elements.yaml（tier=P1——棘爪护已落地披露非等重评，调研两轮分歧的裁量：第一轮「暂不扩件」真顾虑=给未修复件预立法 Boundary 目标，本条不冲突）；③D-173 行加承接注记「camera_orbit 因 Glama 逐件实锤为并列 min 锚纳入处置」（D-108② 改指针不改语义先例，非 revise）；④本地 tdqs 预评作 PR 前回归参考（D-173③ 适用场景） | 负向：①重写后重评仍 <3.0→归 schema 结构性缺陷（center:str JSON 形态压制 Params 维），center 拆 x/y/z 属 breaking 并入下一版本窗裁，不为单件做 breaking release（ADR-0028/P3 同构）；②camera_create 不动——D-174② 单向惯例零改动旧件，其缺兄弟点名系 4 分 justification 注记非扣分因，camera_orbit 单向点名后对偶缺口自然消解；③Conciseness 反噬风险（10 行→~25 行）须预评校准；④本裁决不含验收时点让步——min≥3.0 达标判定归重评观察窗非文本落地日 | current |
| D-182 | R39-Q5' Glama 复合验收判据现实性复核+重评触发路径定案（atomcode 调研辩证版：决定性新证据=TDQS spec 正文已成文规定字母档 A=≥3.5/B=≥3.0「tier-B passing bar」官方原话——「仅 FAQ 半官方」认识过时；GM-22-001 重基线惯例+OKR committed/aspirational 两分+D-129 归因纪律复核；置信度高） | 采纳 | B=双轨重校准：①验收门=Glama 页面字母档=A+min 逐件≥3.0+零 annotation contradiction 旗标——三要件全锚官方成文条款零推断成分；②4.0/4.2 降为自设 stretch 目标（改定为 3.8=乐观推演值，标注自设推断非官方阈值）；③触发路径=决策树非定论：merge 后 last-scanned 动→HEAD-build 分支直接验收/不动→PyPI-pull 分支实锤→描述批搭下一实质发版车复验/发版后仍不动→新缺口立项（平扫 cadence 或 build 长期失败）；④金丝雀状态记账纪律=只写观察不写结论（D-129）——「观察中」非「PyPI-pull 初步成立」 | 负向：①D-173② 标 scoped revised——验收判据句整体改写，原判据保留在 ADR-0028 被否选项/修订注记不删（GM-22-001 多基线供审计+D-171③ 门本体修订走 revise 呈报+披露义务禁静默缩门）；②三处立法面一次改齐防漂移（D-098 单源纪律）：账本行+ADR-0028 §4+CONTEXT「TDQS」词条；③min≥3.0 已蕴含无 C 级——冗余子句顺手合并；④重评判负（字母档仍 B）归因落点=执行质量非判据——B 是带牙的门非放水；⑤禁为达 4.0 打开 P3（D-179 两轮论证）/禁为文本单发版（D-175③ 不动） | current |
| D-183 | R39-Q6' 证据指针纪律一般化裁决（P-03b→常设纪律；atomcode 调研辩证版：GitHub permalink 官方文档+drift 工具+qlty CI lint DX+ESLint warn 反模式 7 全文读；缺口=无逐字同构工业先例如实披露；置信度高） | 采纳 | B=文本纪律+CI warn 级锚点校验：①锚点形态白名单单源机读文件（仿 0028-elements.yaml 形态，脚本与模板双消费防双真源）——优先级：pytest node ID＞path::symbol（AST 符号存在性抗漂移）＞sha:path:line（commit 钉死，D-136 同族）＞裸 path:line（版本化文档中=warn 提示升级，.scratch 中合法临时态）；②check_evidence_anchors.py warn 级入 lint job（扫 CHANGELOG 最末 release 节+decision-ledger+docs/adr+docs/evidence/**；exit 0+::warning::；循 check_monolith_budget.py 骨架纯 stdlib 零新范式）；③expiry 锚=首次 release-preflight 复核误报率——零/低误报→path::symbol 缺失类升 hard，裸 path:line 提示永久保持 warn；④覆盖面=机检只管版本化文档（.scratch gitignore CI 不可达），scratch 走模板白名单+审计抽查项；⑤模板两句结构化要求：命令附「环境+退出码+工件落点」三联、Fixed 条目附「故障版本→修复版本」字段；⑥AGENTS.md 联动表加行 | 负向：①D-082⑦ 标 scoped revised（file:line 降权=一般化非反转，机制本体不变）；②warn 软化辨析须入账本行——D-175 禁 warn 管确定性无误报面要素断言，本案 warn 管误报未实测新机件=D-180 观察期原则适用场景，禁无 expiry 挂 warn；③机检边界=指针可达性+结构化要素存在性；内容真值+语义方向归人工（虚构 --help/不可复现命令/Fixed 方向写反机检覆盖不了）；④可证伪点入账：误报率>30%（动态名/__all__/嵌套符号）→降回 A+审计抽查；版本化文档指针总量<10→C 复活须实测失效速率；warn 被永久无视→B 退化（expiry 锚落机检工件即防此） | current |
| D-184 | R39-Q7' R39 收口窗落地编排裁决（atomcode 调研辩证版：SmartBear/cubic.dev/bssw.io/growingdev.net/MS Learn ADR 6 篇全读+本仓一手核验；置信度高） | 采纳 | A=两 PR 编排：P-A=TDQS 收口批（估 250–350 行落甜区——D-180 要素改写+极性感知原则立法+ADR-0028 §2 注记；D-181 camera_orbit 五要素重写+yaml tier=P1 要素行；D-182 判据重校准三面同步：账本行+ADR-0028 §4+CONTEXT TDQS 词条；D-179 承接注记；canonical 账本迁入 D-177..183+四处 scoped revised 标注+next-round.md 更新）；P-B=证据纪律机件批（估 80–150 行——D-183 全项：check_evidence_anchors.py warn 级+白名单单源+模板两句+AGENTS.md 联动+测试） | 负向：①F1 应急——P-A 实际 diff>400 行则同 PR 拆 P-A0（账本+revised 文档层）/P-A1（执行层）两 commit，账本/revised 与被修对象不许跨 PR；②P-A PR 描述须显式声明「账本迁入/revised 标注属本批被修对象的原子记录面」（D-109③/D-153①）防审计按 P-07 形态误报；③D-149 校准宣称——stretch=3.8 为内部推断值禁入对外宣称文本（README/distribution-surfaces 只写官方判据 A+min≥3.0+零旗标）；④elements.yaml 单源件禁跨 PR 分批改（每次 review 须见全图）；⑤P-A 必须先于任何发版窗合入（金丝雀对两 PR 顺序无判别力）；⑥canonical 迁入=append 行+revised 注记，过程账本件留 .scratch append-only 不删（D-082⑥⑤）；⑦版本控制走 but/GitButler 栈 | current |

## 附：R41 会话账本 verbatim（已迁入 canonical D-185..193——本区留档对照勿重迁）

| D-185 | R41-Q1' 题面范围裁决（atomcode 调研辩证版：Fowler release train/SmartBear 400行甜区/Google Eng Practices/ESLint warn→hard+eslint#18517+strict-lint/Agile freeze 粒度四惯例交叉验证；本地补核 CHANGELOG Unreleased 实质内容在装车=发版车在月台非空等；置信度高） | 采纳 | R41 题面=收口窗六题：①B→A 落地链路三题（push/PR 编排含 gr docs lane 归置、发版车选、重评验收+判负预案）；②evidence-anchors expiry 复核规程立法（首 release-preflight 误报率复核→升 hard 判据按 D-183④ <30% 线）；③极性硬化立法（opt-in 正向豁免表+子句级否定窗口形态选择层，条款写可证伪点对齐 D-183④ 风格）；④杂项清零三件（337/339 计数口径定案、tools/list 捕获局限挂三联证据指针入 known-gap、mypy baseline 计数规则声明）；⑤C 尾项并入——P3 复议议程骨架+证据指针占位+三条件原文摘录，零结论标注「材料于门审召集窗按快照重算」 | ①极性硬化禁把 D-175④ 保留 hard 面（Boundary:/P0 要素）降 warn；②expiry 规程不改门定义不触 D-171③ 缩门车道；③P3 尾项禁预制判决倾向（门审 _Avoid_ 陈旧快照判案）；④调研辩证已履行——A/C 否决理由与证伪点存档 .scratch/r41/research-q1.md；⑤发版车选仍受 D-175③ 禁为文本单发版+D-184⑤ P-A 先于发版窗硬约束 | current |
| D-186 | R41-Q2' 落地编排裁决（atomcode 调研辩证版：GitHub Docs about-stacked-prs 全文/Pragmatic Engineer 引 Graphite 创始人/davepacheco 实操/merge queue 对比/dandoescode 3-4层天花板/thetshaped 级联攒批/HN#49112232；本地实证=三 lane 文件交集零 hunk 重叠；置信度高） | 采纳 | A=三独立 PR 编排：①merge 序 gr→P-A→P-B（裁决面先于执行面=D-154 同构；P-A 先于 P-B 兑 D-184⑤；gr 先合的 rev51 hash 悬空小窗由同窗连发吸收，评审间隔多日则微调 P-A→gr→P-B 亦合法）；②三 PR 描述各写「建议合入序 gr→P-A→P-B」并互链；③P-A 描述履行 D-184② 原子声明（账本迁入/revised 属被修对象原子记录面），P-B 描述履行 D-082⑦/D-183 scoped revised 声明；④gr 纯 docs merge 后观察 Glama last-scanned 作金丝雀对照点入 canary ledger（只写观察不写结论 D-129）——判别 HEAD-build vs PyPI-pull 素材 | 负向：①禁栈化（B 撞 D-184 两 PR 形态=须 revised 的改向；D-184⑦「栈」=lane 组织方式非 stacked-PR 立法依据不可引用）；②禁 gr 攒批（撞 D-153① 收口悬置+D-109③ 引用面漂移+D-070 事件窗经济）；③stretch=3.8 禁入任何 PR 描述（D-149）；④push/PR 动作为用户令本题仅立编排 | current |
| D-187 | R41-Q3' 发版车选裁决（atomcode 调研辩证版：semver §7 双命中/thoughtspile 批量取最高跳档/PyTorch RELEASE.md patch 判据/Protean ADR-0004 changelog-trigger 逐字/D-093 正确消化为单次质量门非频率上限；置信度高零冲突） | 采纳 | A=0.6.0 minor 发版车：①定性=新机件 minor 窗（2 新 CI 机件+36 要素单源）+描述批搭车+金丝雀决定性实验三重身份，各踩 D-175③/D-182③/D-184⑤ 既定轨道非纯文本专列；②执行链=三 PR 全合+CI 绿→release-preflight 全过（check_release_appendix 断言行+PyPI 双车道复核+annotated tag）→人工确认门呈报核对单→git tag -a v0.6.0→盯 publish CI→GH Release（D-084 minor 义务位兑现）→PyPI 验证→金丝雀观察落账；③0.6.0 发版后 Glama 仍不动→PyPI-pull 分支实锤转新缺口立项（平扫 cadence 或 build 长期失败调查）；动了→HEAD-build 分支直接验收 | 负向：①发版动作=人工确认门（gate_authority=用户）不变，本裁决只立车选立法；②禁 0.5.1 patch 降档误标（PyTorch 判据+D-081② 档位失真精神）；③禁攒批悬置（D-081 顺延须排序+D-107④ 审计面膨胀）；④金丝雀全程只写观察不写结论（D-129） | current |
| D-188 | R41-Q4' 重评验收执行+判负预案裁决（atomcode 调研辩证版：Nosek PNAS 2018 预注册+COS decision-tree FAQ/SRE Workbook ch2 SLO-without-policy/SonarQube fail 条件预置三源印证；四分支穷尽字母×min×旗标×时间戳判定空间；置信度高） | 采纳 | A修正版=预立法四分支判负决策树+验收载体：①Br-a 字母升但某件 min<3.0→单件执行质量→描述再修（非破坏）或归 schema 结构性缺陷按 D-181③ breaking 窗另裁；②Br-b min 全过但字母仍 B→coherence 结构性拖→P3 触发债条件①核验写成「是-可即兑/是-不可即兑/否」三档只记观察（复合条件=Disambiguation 仍3/5 AND 真实客户端实证选错，后者无本地测量路径须 LLM 实测→只登记实证义务触发不预设结论），P3 解冻判定权仍归 gate review 前置议题（D-179②）；③Br-c Scored 时间戳不动=D-182③ 第三条+D-187③ 收口原文衔接→新缺口立项；④Br-d 旗标非零→逐旗检修描述（D-172α 轨道）；⑤验收载体=执行窗 Glama 页快照归档 docs/evidence/（D-109/D-153② 形态，claim boundary 写明支持层）+账本事件行+distribution-surfaces.md 同步；⑥徽章达标后可选达标前禁写（D-149/D-184③ 已立法非新裁量——badge=滚动宣称非时刻快照） | 负向：①禁临场即兴归因（B 否决锚=D-171「判负当刻=交付压力最大时临时立法最易扭曲」）；②禁前瞻宣称（C 否决锚=D-149/D-184③⑤）；③判负归因落点=执行质量非判据（D-182④）；④Br-b 不得以本预案名义直接解冻 P3 | current |
| D-189 | R41-Q5' evidence-anchors expiry 复核规程立法裁决（atomcode 调研辩证版：口径修正=裸 path:line 合法 advisory 不计误报分母，误报只发生在可硬化类 unresolvable/not-exist-at-HEAD；Notion 棘轮存量合法+增量硬化同构；SRE policy/Nosek 预注册复用；置信度高零 revise） | 采纳 | A=全案立法：①时点=0.6.0 preflight 即首复核点（D-187 执行链天然承载）；②测量法=按形态分桶计数，误报率仅对可硬化类计（path::symbol/pytest node ID 的 unresolvable+sha:path 的 not-exist-at-HEAD；裸 path:line 升级提示=设计内合法 advisory 只登记存量不计分母）；③逐条核验协议=unresolvable 类逐条人工核文件存在性+符号真缺失 vs AST 盲区（_symbol_exists 只认顶层 def/class+一层方法；__all__/动态名/深层嵌套→记 FP）；④判据直引 D-183④ 不改一字（FP率=FP/(TP+FP)；零/低→path::symbol 缺失类升 hard；>30%→退人工抽查+修 checker 债）；⑤载体=ADR-0023 preflight 清单加行（循第6行弱断言人工执行项先例——复核是 measurement 非 gate 不进 push CI）+账本事件行（时间戳+逐类计数+FP率+判定+证据指针）+分类计数工件入 docs/evidence/（D-109）；⑥存量 40 条裸 path:line 登记 D-122 触发条件债逐步升级消化不强清零 | 负向：①判据直引 D-183④ 禁止在判定条内改判据；②不触 D-171③（机件收紧非门本体修订）；③禁跳过测量直接升 hard（C 三重冲突：D-183③/AST盲区未实测/D-184⑤ 插队）；④本批 R41 各行随 canonical 迁入同批 append 勿悬空引用未迁行 | current |
| D-190 | R41-Q6' 极性硬化机制形态立法裁决（atomcode 调研辩证版：ConText Harkema2009 PMC2757457 句界 scope 谱系+BMC2023 scope-FP41%+negspacy pseudo_negations+strict-lint maxSeverity+Error Prone ERROR 零误拒准入；首跑 provider 中断按续跑锚定 -c 恢复；置信度高） | 采纳 | A 全案附三限定：①窗口=子句级（cue 与 match 之间无子句边界才算否定——80char 固定窗=NegEx 前形态被淘汰，收窄方向 FP 必降，代价 FN 升但防假绿场景 FN 危害远低 FP 且 A③ 兜住关键件）；②yaml 新增 positive_exemptions 要素级字段枚举合法否定式披露短语（ConText pseudo-trigger 优先于 negation trigger 同构；无豁免表则强制挂扩面时 6 件否定式 pattern 要素立即全自伤——"not idempotent" 同子句必含 cue not 永远 negated_only）；③覆盖规则附极性方向限定条款——强制 polarity_aware:true 仅限「pattern 集纯肯定式的 mutation 类存在性断言」（现行唯一实例=camera_orbit/mutation_side_effects），pattern 否定式要素（irreversible/no_mutation_no_undo/read_only_disclosure/overwrite_or_persistence_semantics/non_idempotent 否定分支）不挂守卫其保护走豁免表——不加限定则③④互相架空；④路径=仍 warn 起步→挂 0.6.0 preflight 复核规程（D-189 同位），双档判据显式定义：分母=被判 negated_only 的 polarity_aware 要素数、分子=其中实为合法肯定披露、升 hard=零误拒（Error Prone ERROR 准入同构）、>30%=退人工抽查+修 checker 债；⑤落地 lane 归置=随 D-186 编排协调，建议 P-A lane 追加 commit（同域同单源件同批 review）或 P-A merge 后独立小 PR 由执行编排裁定 | 负向：①切分符/cue 表/豁免短语清单禁入立法行只进执行窗产物（D-180③）；②warn 降级仅限 negated_only 分支，P0/Boundary 存在性 matched 判定保持 hard；③前置项=语料分母口径先行定案（脚本注释 264×pattern=339/53 vs 脚本输出 30/11 vs yaml 实际 36/12 三处打架，并入杂项题 Q7 先行解决否则零误拒分母不闭环）；④yaml 改动走 D-175④ PR 显式 review 逃生门；⑤C 否决锚=D-180③ 交付义务+D-185③ 既定范围+D-180② 一类缺陷正面冲突三合一 | current |
| D-191 | R41-Q7 杂项清零裁决 | A | A=三件全清：①计数口径三面定案——diff 行数以 numstat 为 canonical 口径声明（--stat 337 vs numstat 339 差=口径非错误）；要素/工具计数以 0028-elements.yaml 解析值为唯一真值（checker 输出 30/11=P-A 前时点快照非陈旧代码，camera_orbit 行恰 +1tool+6elements 闭合差值，如实注明防后轮审计误判）；极性语料分母=真实校验面为主测（工具↔其要素的断言面）+264 docstrings 全量笛卡尔积作压测面——零误拒判据的分母自此闭环（D-190③ 前置兑现）；②tools/list live 捕获局限挂「环境+退出码+工件落点」三联证据指针入 known-gap（D-183⑤ 模板纪律适用）；③mypy baseline 口径声明：new:0=「raw 184 vs baseline 199 过滤后无新增」语义写明 | 负向：①全部为登记级处置不新增裁决面；②30/11 vs 36/12 判定=时点差非缺陷须如实注明；③语料分母「主测+压测」两轨口径写入账本禁混淆 | current |
| D-192 | R41-Q8 P3 复议议程骨架载体裁决 | a（采纳 A） | A=ADR-0023 gate review 节增设「前置议题登记」块：①议题槽=P3 工具面合并复议作 v1.0.0 gate review 前置独立议题（非门清单行，D-171 隔离条款）；②判据直引 D-179② 原文（同构族测试=3+操作共享大部分参数+合并前 LLM 驱动实测选错率）；③触发债三条件原文摘录（D-179③：Disambiguation 仍3/5 且真实客户端实证选错/Glama 调分带收益归零自动作废/工具面越~35 件转可用性题）；④证据指针占位符（Glama 批后维度读数快照/客户端实测报告/工具面计数——占位待门审窗填）；⑤标注「材料于门审召集窗按快照重算」零结论禁预制判决倾向 | 负向：①骨架禁含判决倾向（门审 _Avoid_ 陈旧快照判案）；②任务书 T-R40-04 保留瞬态指针改指 ADR-0023 登记块防双真源；③D-094 异构禁令仍是 P3 硬前提不入骨架正文仅作判据引用层 | current |

| D-193 | R41-Q9 R41 立法批落地编排裁决 | a（采纳 A） | A=新开 grill lane（grill/round41-gate-path）+第四独立 docs PR：①承载=D-185..192 canonical 迁入 append+ADR-0023 两处（preflight 复核规程行+P3 前置议题登记块）+ADR-0028 §4 判负决策树附件+杂项登记三件+任务书 rev52；②与 D-186 三 PR 编排同构顺延，docs-only 零代码依赖，合入序排 P-B 后或视评审并行；③极性硬化执行批（checker+yaml 改动）归执行窗——建议随 P-A lane 追加 commit（D-175④ 单源件同批 review）或 P-A merge 后独立小 PR 由执行编排裁定 | 负向：①禁并入 round39 既有 gr lane（命名失真两轮混栈）；②禁攒批悬置（D-153① 本窗落仓）；③本批仍受防丢纪律——落账先行、迁入随编排批 | current  〔承接注记 2026-10-01（D-108②）：「新开 grill/round41-gate-path 独立 lane」因 GitButler 依赖模型物理不可行——本批 hunks 坐在三条未 merge lane 内容上（CONTEXT/任务书属 gr、账本尾部属 exec 双 lane），并行 lane 共享同一 base 无法承载跨 lane 依赖。实际落法=docs 四件入 gr 追加 commit zko+账本迁入入 xe 追加 commit wnn（同类迁入操作同 lane 惯例）；语义等效载体层不同，merge 序 gr→P-A→P-B 不变〕 |
