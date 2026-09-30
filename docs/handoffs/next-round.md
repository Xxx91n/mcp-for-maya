---
generated: 2026-09-30
from_round: R39（Glama TDQS B→A 收口路径 grill 定稿 + 对账整理闭环，覆盖 D-177~184）
ledger_head: canonical=D-184（D-177~184 已于 T-R40-01 迁入 + 四处 scoped revised（D-172α/D-174①/D-173②/D-082⑦）+两处承接注记（D-172β/D-173）已落位）；.scratch/r39/decision-ledger.md 过程件按 append-only 留档不删——本文件「附」节 verbatim 副本已迁入留档勿重迁
branch: grill/round39-tdqs-closeout（本整理批，yos 未 merge）+ 执行窗已建两分支堆叠 main tip 45231a8：exec/r40-tdqs-closeout（P-A，commit qkn）/ exec/r40-evidence-anchors（P-B，commit zry）——push/PR 未授权
---

# 下轮任务书（rev51）

## 状态总览（R39 收口）

- **Glama 实况**：页面仍 B 3.4/5.0（Scored 2026-09-30 06:25 未动）——TDQS 描述批（PR #58~61）已 merge 但未触发重扫；金丝雀观察中（D-182 决策树，只写观察不写结论）。
- **R40 执行窗实录（rev51）**：P-A 全项落地 commit qkn（账本迁入+四处 revised 中三处+两处注记/elements.yaml 对齐真实 API+camera_orbit 行/checker 极性原则+语料实测 339 匹配 53 假阳否决 naive 窗证成 opt-in 设计/ADR §2 注记+§4 重校准/camera_orbit 五要素/三面同步）；P-B 全项落地 commit zry（白名单单源+checker warn 级+模板两句+联动行+D-082⑦ revised+10 测试）；门检=803 pytest pass/ruff 预算过/mypy-baseline 0 new/pre-commit 全过/uv build 0.5.0/MCP initialize 握手实测通；observation 台账=checker 实跑 40 warnings（版本化文档裸 path:line 升级提示，exit 0）；push/PR 未授权。任务书本更新（rev51）属 grill lane 栈——须叠 rev50 载体不入 P-A diff，D-184⑤「P-A 含任务书更新」澄清为「任务书更新义务由执行窗承担、载体归 grill lane 原子面」。
- **本轮七裁决全落账**（D-178..184，见附节 verbatim）：收口窗范围 / P3 推迟维持+gate 复议点 / S-02+S-03 两翼修法 / camera_orbit 单件处置 / 验收判据双轨重校准 / 证据指针纪律一般化 / 两 PR 落地编排。
- **调研存档**：.scratch/r39/research-q1.md ~ research-q7.md（atomcode 七轮，逐题冲突标注在案）。
- **四处 scoped revised 待落地**：D-172α、D-174①（scene_validate 要素行）、D-173②（验收判据句）、D-082⑦（指针形态条款——随 P-B 非 P-A，见编排注）。
- **无新增源码改动**：本轮纯立法；camera_orbit 描述、checker 机制、yaml 改写全在执行窗。

---

## T-R40-01：P-A TDQS 收口批（单 PR，估 250~350 行）

覆盖 D-178/D-179/D-180/D-181/D-182 + D-184①~⑥。

1. **canonical 账本迁入**：D-177..184 append 进 docs/decision-ledger.md（D-177 保持 revised 态）+ 三处 scoped revised 标注落原位（D-172α、D-174①、D-173②——原记录保留+指针，D-163③/D-040 先例形态）。
2. **elements.yaml scene_validate 要素改写**（D-180①）：autofix_two_state/autofix_mutation→read_only_disclosure+repair_redirect(all:[scene_plan,auto_fix])+irreversible_when_mutating→no_mutation_no_undo；同 PR 加 camera_orbit 要素行 tier=P1（D-181②）。
3. **checker 极性感知原则立法**（D-180③）：check_tdqs_disclosure.py 立「mutation 类存在性断言须极性感知」原则——机制形态（否定词表/辖域窗口/豁免表）须先过 25 条现行描述语料零误报实测再落地，初上可 warn 观察期再升 hard。
4. **ADR-0028 §2 澄清注记**（D-180②）：accepted 不动+注记写明真实 API 无 auto_fix/立法时误植 scene_plan 面/机检单源以修订版 yaml 为准；注记须录入「现行词表已含 5 个否定式 token」实证作否决依据存档。
5. **camera_orbit 描述重写**（D-181①）：五要素=副作用（创建相机+动画曲线+mark_dirty）/非幂等/会话前置/center JSON 参数语义/Boundary: 点名 camera_create；精准命中 Behavior+Usage 两 2 分维；本地 tdqs 预评作 PR 前回归参考（不入 CI）。
6. **验收判据三面同步**（D-182）：验收门=字母档 A+min≥3.0+零旗标（ADR-0028 §4+CONTEXT「TDQS」词条+账本行一次改齐）；stretch=3.8 标自设推断；min≥3.0 蕴含无 C 级顺手合并冗余子句；原判据留 ADR 被否选项不删。
7. **D-179 承接注记**：D-172β 行 append 修理由锚（真理由=D-094 异构禁令+在飞批撞车+gate 带宽，非 semver 成本）；CONTEXT「TDQS」_Avoid 行「semver major 裁决」表述同步注记。
8. **PR 描述义务**：显式声明「账本迁入/revised 标注属被修对象原子记录面」（D-109③/D-153①）防 P-07 形态误报。
9. **F1 应急**：diff>400 行则同 PR 拆 A0（文档层）/A1（执行层）两 commit；elements.yaml 禁跨 PR 分批改。
10. **时序硬约束**：P-A 必须先于任何发版窗合入。

## T-R40-02：P-B 证据纪律机件批（单 PR，估 80~150 行）

覆盖 D-183 + D-082⑦ scoped revised（原子性细化：被修对象指针纪律机制在本批，其 revised 标注随本 PR——D-184③ 原则顺位应用）。

1. 白名单单源机读文件（仿 0028-elements.yaml 形态）：优先级 pytest node ID＞path::symbol＞sha:path:line＞裸 path:line；脚本与模板双消费。
2. check_evidence_anchors.py 循 check_monolith_budget.py 骨架（纯 stdlib+::warning::+lint job 挂载）：扫 CHANGELOG 最末 release 节+decision-ledger+docs/adr+docs/evidence/**；path::symbol 走 ast.parse 验存在+def 行一致；裸 path:line 无 sha 前缀→升级提示；全 warn 级 exit 0 起步。
3. expiry 锚落机检工件：首次 release-preflight 复核误报率——零/低→path::symbol 缺失类升 hard；裸 path:line 提示永久 warn。
4. 模板两句结构化要求：命令附「环境+退出码+工件落点」三联；Fixed 条目附「故障版本→修复版本」字段。
5. AGENTS.md 联动表加行（账本/CHANGELOG 修改→check_evidence_anchors.py）+ 测试随行为同 commit。
6. warn 软化辨析已在 D-183 账本行写明——执行窗措辞不得把 warn 写成永久态。

## T-R40-03：Glama 金丝雀观察窗（持续，非 PR）

观察台账（rev51）：金丝雀机制存在=.github/workflows/ci.yml drift+drift-notify 双 job；decision tree 未触发（无新 Scored 事件）；暂无需 docs/evidence 工件——继续观察至 release-preflight。

覆盖 D-182③④。三分支：merge 后 last-scanned 动→HEAD-build 直接验收 / 不动→PyPI-pull 实锤→描述批搭下一实质发版车复验（禁为文本单发版，D-175③）/ 发版后仍不动→新缺口立项。账本事件行只写观察不写归因结论（D-129）。

## T-R40-04：v1.0.0 gate review 前置议题登记（到期兑现）

覆盖 D-179②③。届时将 P3 复议作 gate review 前置独立议题（非门清单行）：判据=同构族测试（3+ 操作共享大部分参数）+合并前 LLM 实测选错率；裁不合并→转触发条件债三条件（Disambiguation 仍 3/5 且实证选错 / Glama 调分带收益归零自动作废 / 工具面越 ~35 件转可用性题）。gate 前若现真实客户端选错实证→按触发条件债提前解冻不等 gate。

---

## 承继项（自 rev48/rev49 不变）

- **叙事窗 γ**：轻叙事只描已验证面；重叙事仍锁（v1.0.0 门审或框5像素面先到）。
- **债消解信号常备**：mayapy/Linux env、框5 像素面见证、第二站 VP2、Maya 2025/2026 装机——到场即门检落新快照。
- **门审召集**：归 user 裁量。
- **观察窗**：10-05 双源观测 / 10-30 D-146 核销 / awesome PR #15382（OPEN）合并跟踪。
- **审计残余**：R2 根因 probe JSON 补强（可选）/ R3 拆行配额规则下次拆行立法 / R4 顺手补。

## 边界警示

- 执行窗≠grill 窗：措辞终稿归执行窗+人工过目（D-174③）；极性机制形态同样归执行窗（D-180③）——立法只到原则，禁越界钉死未实测形态。
- P3 工具合并仍锁——D-179 已立法推迟至 gate review 复议；合并集仅限同构子集（D-094 硬约束），异构合并须先 revise D-094。
- atomcode 件跨会话污染警惕延续（正确 slug=Xxx91n/mcp-for-maya）。
- 续期上限每行 2 次不变；debt_owner/gate_authority 拆词已立法。
- D-069 逐件过目链不变；勿 push/PR 除非用户令；版本控制走 but。
- elements.yaml=单源件（D-175④）：任何变更走 PR 显式 review，禁跨 PR 分批改。
- stretch=3.8 禁入对外宣称文本（D-149）。

## Suggested skills

- $implement：P-A/P-B 两批落地（执行窗主力）
- $but：分支与 commit（两 PR 各自栈；无授权不 push）
- $tdd：check_evidence_anchors.py 测试随行为同 commit
- $code-review：P-A 收口前自审（描述措辞+断言语义校准面）
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
