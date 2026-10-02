---
generated: 2026-10-02
from_round: R45（跨三轮遗留清零+Glama 收口编排+dcc-mcp-maya 竞品取长补短 grill 定稿，覆盖 D-202~210）
ledger_head: canonical=D-210（D-202..210 已随本批迁入）；.scratch/r45/decision-ledger.md 过程件 append-only 留档不删——本文件「附」节 verbatim 副本已迁入留档勿重迁
branch: 四 lane 布局——R44 三 lane（grill/round44-sub-a-closeout / exec/r44-description-floor / exec/r44-checker-mechanics）待 merge 波+本批新 lane grill/round45-closeout（纯 docs）；merge 序 gr44→exec-A→exec-B（D-201），gr45 账本尾部坐在 D-210 之后排 gr44 之后（D-206）
---

# 下轮任务书（rev54）

## 状态总览（R45 收口）

- **R45 九裁决全落账**（D-202..210，canonical 已迁）：范围排序依赖链/样本量地板立法（TN+F 口径+12 覆盖论证+per-element≥3TN+Ro3 移位）/F4 到期分级（==due warn、>due error+preflight 第8行+D-168 续期纪律）/断言与证据纪律立法（AGENTS.md 三主线节+pre-commit 钩=exec lane 实现件）/合流全链编排（tag 挂 exec-A 不等 exec-B+[Unreleased] 隔离+Glama Scored>T+24h 窗）/竞品增量组九项逐项/范式 pitch 六件登记（ADR-0023 扩列）/reject 组+遥测 observe/三小项结案。
- **立法批本批已落盘**：canonical 迁入 9 行+ADR-0028 R45 增补段（地板立法+到期分级）+ADR-0023 R45 增补（preflight 第8/9行+六 pitch 登记块）+CONTEXT 四新词（判决承载标签/候选 pitch 登记/机制 vs 范式分离/结案判定词）+本任务书。
- **竞品档案**：dcc-mcp-maya v0.9.33 本机 clone 于 D:/Aworker/maya/dcc-mcp-maya（自述 245 typed tools/30 skill 包/Rust sidecar 网关/渐进加载/dcc-mcp-cli 控制面/遥测闭环；裁决底稿=.scratch/r45/atomcode-q1..q9.txt+ctx 索引报告）。我方差异化=TDQS 治理机件+scene 智能面（aesthetics/review/validate/measure/plan）+checkpoint/rollback 事务安全+ICEV+审计日志+threat-model。
- **Glama 实况**（2026-10-01 12:25 UTC 扫描）：总 A 3.6/5.0；camera_orbit C2.9（时滞伪影待 merge 后重扫自愈验证）、scene_measure B3.1（修复在 exec-A lane 未合流）。
- **R44 三 lane 现场**：全审计闭环（F1~F7，844 passed/26 skipped），未 push 未 merge；push/PR/merge/tag 全链授权已由 D-206 给出（PyPI publish 仍人工门）。

---

## T-R45-01：merge 波+0.6.0 发版链（第一优先；D-206 全链授权）

覆盖 D-206 + D-201 + D-197。

1. `but push` 三 R44 lane→`but pr` 三 PR（描述互链+建议合入序）→按序 squash-merge：gr44→exec-A→exec-B（手动 merge queue 等价物；workspace 合态 844 passed 已测、文件面零重叠）。
2. exec-A 落地即跑 release-preflight 全清单（含新第 8 行 TDQS 到期豁免+第 9 行 pitch 呈报）→人工确认门呈报核对单→`git tag -a v0.6.0` 打在 exec-A squash commit 上（不等 exec-B——纯 CI 面不进 wheel）。
3. exec-B 全部产出留 [Unreleased] 不入 [0.6.0] 节（preflight 主动核对防 D-107④ lint 红）。
4. gr45 docs lane 排 gr44 之后 merge（账本尾部 EOF 邻接依赖；纯 docs 无代码依赖）。

## T-R45-02：Glama 观察协议执行（merge 波完成后启动）

覆盖 D-206④ + D-197② + D-188。T=merge 波完成时刻；验收读数只取 Scored>T 的扫描（中间态只写观察不写结论 D-129）；24h 后 camera_orbit 仍 C→提 glama-ai issue（inputHash 重评异常，24h=官方分钟级承诺千倍余量的推断值改口径须另裁）；scene_measure 同窗验证；达标=快照归档 docs/evidence/+distribution-surfaces 同步+账本事件行。

## T-R45-03：exec/r45-governance-fixes lane（merge 波后从 main 新开）

覆盖 D-203 + D-204 + D-205（实现件）。

1. D-203：polarity_corpus_probe MIN_ADJUDICABLE 计数基改 TN+F 子集+per-element ≥3TN 断言+常量注释挂 D-203；语料经轨③晋升补 5 条 TN/F（顺带产出 exemption_list_changed_verdicts 首次实测改判机会）。
2. D-204：checker `current==due`→warning / `current>due`→error 逐件点名；延期 YAML 修改须满足 D-168 waiver 续期五要件；读不到版本维持 warn。
3. D-205：AGENTS.md「断言与证据纪律」节 ≤10 行祈使句（三主线：枚举/计数断言声明域带口径+版本化文档枚举/计数/退役型断言默认机检载体而宣称型归 D-149+不可复现记「未验证」；机制指针行 blob-vs-工作区 pre-commit mixed-line-ending；行尾引 D-109）挂 D-205 出处；.pre-commit-config.yaml 加 mixed-line-ending 钩（CI 行尾扫描已裁否不加）。

## T-R45-04：竞品增量实现批（D-207；建议同 T-R45-03 lane 不同 commit 面）

覆盖 D-207 ①③④⑤⑨。

1. 严格策略模式（①⑦ 同批不可分）：MAYA_MCP_DISABLE_EXECUTE/WRITE_MODULE/ARBITRARY 三旗标+pipeline.py 单点 enforce+被关工具从 tools/list 过滤或加「Boundary: disabled by policy」行+threat-model 增补重申「误用护栏非恶意 agent 边界」+policy-guard stub 测试（禁用生效断言+只读面不受影响）进 CI。
2. llms.txt ≤100 行单文件（不做 llms-full）+CI 从 TOOL_ANNOTATIONS 生成/校验（防第三真源 D-183）。
3. docs/guide/session-lifecycle.md 一页四列矩阵（会话建立/断连路径×teardown 触发×残留状态×最坏残留窗口）标「汇总视图语义以 ADR 为准」。
4. error-codes：先核代码稳定错误码字段存在性——无则先改代码后立页（文档先行=虚账禁态）；有则 docs/guide/error-codes.md 每码挂 pytest node ID+CI 校验「文档码集==代码码集」。
5. check_version_consistency.py 进 lint job（pyproject==__init__.__version__==CHANGELOG 最新节头==llms.txt 版本字段；须容忍未发布态否则开发期常绿转红）。

## T-R45-05：strict 回归套真机档（挂真机窗 -m gui）

覆盖 D-207⑦ 真机档。typed workload（建球+材质+关键帧+scene_export）+只读 soak ~100 次（P50/P95/P99/max/failure_count）JSON 工件落 docs/evidence/probes/（D-109 纪律：工件一旦落仓后续宣称须挂新读数）+`-m gui` 手动标记不进 CI。

## T-R45-06：N1 根因验证协议（下次 but commit 时顺手）

覆盖 D-210③。下次 but workspace commit 后立即 `git diff --cached`——index 停 base 即坐实「GitButler 未同步 index」推断→AGENTS.md known-quirk 行+酌情上游 issue；两窗未复现→标「多窗未复现维持未验证」显式关闭不无限挂。

---

## 承继项（自 rev53 更新）

- **PV4 触发债**：对外宣称须挂 R44 工件的结论出现时→D-109 单件冻结入 docs/evidence/（D-210②；当前触发态=否）。
- **pitch/observe 呈报**：preflight 第 9 行义务（ADR-0023；六 pitch+遥测 observe 项状态盘点落账本观察行）。
- **多实例 reject 边界**：SessionManager 多会话能力不受影响不更名；唯一回归路径=ADR-0023 pitch-3（触发须附 SessionManager 不可满足场景，D-209②）。
- **叙事窗 γ**：轻叙事只描已验证面；重叙事仍锁（v1.0.0 门审或框5像素面先到）。
- **债消解信号常备**：mayapy/Linux env、框5 像素面见证、第二站 VP2、Maya 2025/2026 装机。
- **门审召集**：归 user 裁量。
- **观察窗**：10-30 D-146 核销 / awesome PR #15382 合并跟踪 / Glama Scored 时间戳（merge 后按 T-R45-02 协议）。
- **审计残余**：R2 probe JSON 补强 / R3 拆行配额规则 / R4 顺手补。

## 边界警示

- D-206③：R45 deltas 禁混入已审三 R44 lane（审计不可变——已审 head 变更=授权过期须重审）。
- exec-B 产出禁入 [0.6.0] 节（D-107④ tag==diff 硬核对，preflight 主动核对）。
- pitch 登记块非 pitch 本体仓库（≤5 行预算超则回账本另裁载体）；observe 态措辞禁「拒绝/否决」。
- 「军备竞赛 reject」措辞永不得扩大解释为新工具立项禁令；遥测 observe 非承诺落地（触发后仍须立项+threat-model 披露面扩展裁决链）。
- 竞品裁决禁止一揽子重提——reject 项带回归条件、pitch 项带触发条件、defer 项带量化触发信号。
- 样本量地板只数判决承载标签（TN+F）；Ro3 不得回挪为地板锚（只作 D-198⑤ 比率阈值参照）。
- 数字必带域（D-205）：枚举/计数断言声明域否则只写规则；不可复现记「未验证」不猜归因。
- 勿对外写 stretch 目标/未验证读数（D-149）；Glama merge 波中间态只写观察。
- 版本控制走 but；发版/tag/PyPI/对外评论仍走人工确认门。

## Suggested skills

- $implement / $tdd：T-R45-03/04/05 全部实现件（旗标测试/探针/fixture 随行为同 commit）
- $but（gitbutler）：merge 波编排+lane 管理+tag（T-R45-01/06）
- $code-review：elements.yaml/错误码页/严格模式旗标显式 review（D-175④/D-207⑤）
- $atomcode-research：pitch 触发成就时的 shaping 调研（串行一次一跑）
- $domain-modeling：新词续落；$handoff：再交接时续写
- $grill-with-docs：下轮 grill 走同流程

---

## 附：R45 会话账本 verbatim（已迁入 canonical D-202..210——本区留档对照勿重迁）

| D-202 | R45-Q1' R45 题面范围与排序裁决（atomcode 调研辩证版：divim.io 发布节奏+Basecamp Shape Up Ch.7 原文+Productboard 竞品分析指南+GrowthBook flag 债+AWS MCP 工具设计指南+developersdigest 渐进披露+债务分级文献 7 源全读；排序重构为依赖链；置信度高，dcc 外部不可核验如实标注） | 采纳 | A（依赖链版）=四件全收按序：①遗留清零（MIN_ADJUDICABLE 首裁→F4→纪律立法）→②Glama 收口编排（三 lane 合流授权+0.6.0 门+重扫观察条款）→③竞品分四组裁决（增量采纳组逐项 adopt/adapt/reject：compact manifest/llms.txt/shutdown-matrix/error-codes 文档惯例；范式评估组=33 skill 包/minimal 模式/Rust sidecar/Streamable HTTP 登记为 0.7+ shape 轮候选 pitch 本轮不采纳附理由；reject 组=212 工具军备竞赛+多实例部署入账防重提；遥测闭环=观察项待 0.6.0 真实用量再议）→④小事（CRLF 表述更正+PV4 选址（docs/evidence/ vs known-gap 登记二裁）+N1 根因验收） | 负向：①grill 窗不动源码不实施——本轮只出裁决文本，任何实施归后续执行窗；②排序即依赖链非偏好不可乱序；③竞品采纳禁止一揽子，逐项入账含显式 reject；④范式组裁决=登记候选 pitch 留回归路径，非 backlog 悬挂也非本轮采纳；⑤发现竞品描述与源码不符时呈报而非带病裁决；⑥lane 滞留=利息递增资产，收口编排须在竞品裁决前钉死现有 25 件面 | current |
| D-203 | R45-Q2' MIN_ADJUDICABLE 追认裁决（atomcode 调研辩证版：Hanley&Hand 1983 Ro3 原文边界+Eypasch 1995+test262 README 原文「每可观测行为有测试」+LaunchDarkly 文档实读（更正：无字面「Needs more data」态，实为样本量估算器+风险早退）+Stryker/PIT 分数阈值惯例+policy-as-code 常量出处纪律 8 源全读；置信度：口径诊断高/值 12 中-工程推导） | 采纳 | A（修正版）=①口径修正：地板计数基从全语料收窄为判决承载标签子集 TN+F（KL 剔除——探针 :240 mismatch 判定本就只对 TN/F 生效，KL 连判决参与资格都没有；同函数内分母排 KL 而地板含 KL=内部不一致，D-198④「防混入分母」精神同型覆盖）；②值 12 追认但补立法理由=覆盖论证非统计论证：12 ≥ 轨③ 8 构式类（4 cue×prefix+4 split）+豁免短语族 2+余量 2=「每已知构式类至少一条判决承载样本」的 test262 式最小工程面（如实标注工程推导/类比非判例）；③per-element 下限新增：每受守卫要素 ≥3 TN（防守卫扩面时语料未长的稀释）；④Ro3 移位声明：n≥30 不作地板锚（其管零事件率上界非标签一致性），移作 D-198⑤「FN 率阈值」未来立法的参照锚（届时 n≥30→上界 ≤10% 参照）；⑤出处=本 D+ADR-0028 增补「样本量地板立法」段+探针常量注释挂 D-203；⑥现况 TN+F=7<12 维持 warn 行为不变，语料缺口 5 条走轨③晋升通道（D-198②），顺带产出 exemption_list_changed_verdicts 首次实测改判机会 | 负向：①KL 永不得计入地板（任何形态）；②Ro3 仅作比率阈值参照锚不得回挪为地板锚；③探针为手工测量件不入 CI 但其输出被 0.6.0 preflight 消费故出处义务成立；④12 之论证为工程推导须如实标注；⑤〔更正注记：D-200 调研引用「LaunchDarkly『Needs more data』制度化状态」经实读其文档证无字面命名态——实为样本量估算器+风险比例早退条款；D-200 决策本体（floor 内置判据）不受影响，仅引用措辞更正〕 | current |
| D-204 | R45-Q3' F4 豁免到期 warn-vs-hard 裁决（atomcode 调研辩证版：Django deprecation timeline/PEP 387/K8s deprecation policy/kubectl --warnings-as-errors KEP 官方原文+unicorn expiring-todo-comments 规则全文+SO 到期编译阻止共识帖+LaunchDarkly/Unleash flag 债指南+testdouble ratcheting-to-zero+BugMojo 发布门 14 源全读；置信度高） | 采纳 | B+C（复合版）=①机械牙分级：checker 改 current==due→warning、current>due→::error 逐件点名（Django 两周期阶梯/C# v2 warn→v3 error→v4 throw 分版本升级精确同构——每次 hard 化伴随新版本号新预告，业界无「due 即 error」单跳先例）；②即时牙：release-preflight 清单增行「跑 check_tdqs_disclosure，到期豁免未消解且未显式延期→no-go」（kubectl warnings-as-errors 分流先例+D-189 evidence-anchor 复核同构放置——本仓 warn→hard 判据惯例是「误报已排除」非「到点了」）；③延期纪律对齐 D-168 waiver 续期五要件（owner 外重签+续期次数上限），防 C 通道被无限续期掏空；④读不到 pyproject 版本维持 warn 不变（不可评估≠违规）；⑤B/C 独立冗余：机械牙不依赖人工、即时牙不依赖版本 bump | 负向：①A（到期即 hard）被实证否决——SO 共识「到期大面积红→团队批量删标注而非清债」+unicorn 作者对到期检查双默认关闭的人因毒性自知+ratchet 正统形态（ruff/mypy baseline）本不设 due 只锁不增长；②B 的 0.8.0 必红残余面已化解论证：届时豁免应已被 0.7.0 preflight 消解或显式延期，爆红面只剩绕过 preflight 的违规发版=恰是该红时刻；③延期 yaml 修改仍过 D-175④ 显式 PR review（静默延期结构性不可行）；④「ratchet 只锁不增长」与「due 定时炸弹」是两种机制不得互套文案 | current |
| D-205 | R45-Q4' 纪律立法裁决（atomcode 调研辩证版：Anthropic 官方 memory 文档（≤200 行目标/更长=adherence 降/矛盾规则任意取舍）+actual.ai ADR 惯例（decision 存 ADR/rule 编译进 agent 文件）+DbC require/TLA+ type invariant/hypothesis assume 三体系成文先例+living documentation/executable spec 文化+crosley 实测（prose 段落与模糊指令被稳定忽略/祈使句+可判定+带出处才被执行）+ETH Zurich/Lulla 评估（瘦身规则文件 runtime-29% tokens-17%）12 源；置信度：落点高/机检义务限定中） | 采纳 | A（修正版）=AGENTS.md 新增「断言与证据纪律」节（≤10 行压缩预算，祈使句+可判定+挂 D-205 出处，不携带案例叙事——案例留账本与审计报告）：①主线一「枚举/计数型断言必须声明域否则只写规则，报数必带口径（先重算再背书，复述他人结论前自算）」——F1 幻觉根因；②主线二「版本化文档中枚举/计数/退役型断言默认选可机检载体（checker 断言/docstring 钉死测试/elements.yaml 单源），宣称型归 D-149 校准宣称不进 checker」——分界句写入防完备主义滑梯；③主线三「不可复现记『未验证』不猜归因（与 D-198『未可判』三态同构）」+行尾引 D-109 覆盖无效实验不算证据；④机制指针一行「blob vs 工作区：pre-commit mixed-line-ending 落地（机制化）+报『N 文件有问题』前先证层」——顺带结案 handoff §4-4（CI 行尾扫描裁否：blob 已净则常绿死检查）；⑤不立 ADR（规则面非架构权衡+诱枚举进正文撞 D-180③） | 负向：①散文纪律面不可机检=须写成 operational policy 形态非说理段；②⑤不独立立条（D-109 已覆盖，重复=矛盾源）；③「散文断言须机检」非全称义务——限枚举/计数/退役型；④CI 不加 line-ending 扫描（已裁）；⑤AGENTS.md 超 200 行基线的既有账不属本项范围 | current |
| D-206 | R45-Q5' Glama 收口合流编排裁决（atomcode 调研辩证版：GitHub merge queue/Mergify/bors 官方+release-please tag 语义原文+momentic/CraftUp/TestCollab 发版门三源+审计不可变性行业共识+Glama 重扫观测协议外推 13 源；置信度高） | 采纳 | A（增补版）=①全链授权：but push 三 lane→but pr 三 PR→按 D-201 序 GitHub squash-merge（gr→exec-A→exec-B）——手动 merge queue 等价物，workspace 合态已测（844 passed 于三 lane 同应用树）故 semantic conflict 风险≈0；②exec-A 落地即 preflight→人工确认门→0.6.0 tag 打在其 squash commit（release-please 语义=tag 挂承载发版内容的 merge，exec-B 纯 CI 面不承载）；③增量 a：exec-B 全部产出留 [Unreleased] 不入 [0.6.0] 节（D-107④ tag==diff 硬核对，preflight 主动核对防 lint 红）；④增量 b：Glama 观察协议量化——T=merge 波完成时刻、验收读数只取 Scored>T 的扫描、merge 波中间态读数只记观察（D-129）、24h 窗口后 camera_orbit 仍 C→提 glama-ai issue（D-197② 时滞量化，24h=官方分钟级承诺千倍余量的推断值可另定口径）；⑤R45 deltas（D-203/204/205 实现件）走新 lane exec/r45-governance-fixes 于 merge 波后从 main 新开——审计不可变性（已审 head 变更=授权过期须重审） | 负向：①PyPI publish 与 tag 的对外不可逆点仍走人工确认门未打包授权；②merge 波中间态 Glama 瞬态读数不作验收凭据；③R45 deltas 禁混入已审三 lane；④0.6.0 节禁写 exec-B 产出；⑤24h 为推断值若改口径须另立裁决 | current |
| D-207 | R45-Q6' 竞品增量采纳组逐项处置裁决（atomcode 调研辩证版：MCP 官方安全最佳实践原文+OWASP MCP cheat sheet+MongoDB/postgresql×2 MCP readOnly 先例+VSCode Workspace Trust+Ahrefs 137K 站 llms.txt 实证+Limy 5.15 亿 bot+Otterly GEO+Stripe error-codes 页+SSOT 文献+dcc 五文档原文+本仓 ledger/threat-model/ADR 摘要 16 源；置信度总高） | 采纳 | A（修正表）=九项逐项：①严格策略=adapt（最高优先）——三旗标拓扑 MAYA_MCP_DISABLE_EXECUTE/WRITE_MODULE/ARBITRARY、enforce 点=pipeline.py 单处（面件化架构优于 dcc 逐工具检查）、被关工具从 tools/list 过滤或加「Boundary: disabled by policy」行（ADR-0028 Boundary 惯例落点）、threat-model 增补须重申「误用护栏非恶意 agent 边界」；②manifest=reject（无可卸载面无题）+回归条件三条：引入按需装载/实测 tools/list token 成本成瓶颈/真实网关接入方要求；③llms.txt=adapt-lite——≤100 行单文件不做 llms-full、必须 CI 从 TOOL_ANNOTATIONS 生成/校验（D-183 防第三真源；实证两面：AI 爬虫不读但 Claude Code/Cursor 是真读者恰是我方场景）；④shutdown 矩阵=adapt——只引文档范式不引机制（其四重安全网解 FileRegistry 幽灵行=stdio 架构无此病）、docs/guide/session-lifecycle.md 一页四列（退出路径×保障×最坏残留窗口×触发网）标「汇总视图语义以 ADR 为准」；⑤error-codes=adapt-lite+强制前置——先核代码里有无稳定错误码字段，无则先改代码后立页（文档先行=虚账）、每码挂 pytest node ID+CI 校验「文档码集==代码码集」；⑥capability-audit=defer-lite 降档——诚实披露已有三载体（TDQS 要素/D-183 锚点/D-109 工件），能力表=第二宣称面违 D-183；触发条件：能力不均匀/v1.0 后企业评估索取≥2 次/skill 域分化，届时五级证据分级直接借用（与 stub/mayapy/GUI 三层一一对应）；⑦strict 回归套=adapt 升档——它是①的验收件必须同批立项：stub 档进 CI（禁用生效断言+只读面不受影响）、真机档挂 -m gui（typed workload+只读 soak ~100 次 P50/P95/P99/max/failure_count JSON 工件落 docs/evidence/probes 受 D-109 约束）；⑧zh 全量=defer+触发条件（PyPI 中文区占比/issue 信号≥2，届时只镜像 docs/guide 不镜像 ADR）；⑨release-please=reject 无回归条件（人工门与文化绑定）+version-consistency=adapt-lite（check_version_consistency.py 进 lint job 须容忍未发布态） | 负向：①所有采纳禁一揽子逐项入账；②①⑦ 耦合——严格策略无 policy-guard 验收件=无验收件采纳违文化；③机制 vs 范式分离护栏——绑定不存在架构前提的机制即 reject 仅范式可议；④一切新文档面过 D-183 双真源测试（已有真源→只能派生+gate）；⑤⑥降档理由=防第二宣称面非价值否定；⑥调研如实标注三缺口：dcc strict 企业采用数据无考证/version-consistency 实现细节未深读/错误目录漂移失败案例系惯例外推 | current |
| D-208 | R45-Q7' 竞品范式组 pitch 登记裁决（atomcode 调研辩证版：Basecamp Shape Up Write-the-Pitch 原文+Scale X 两年复盘+Bitwarden ADR rejected-alternatives+code-copilot pitches/ spec+Skills-Directory G14+OUT-OF-SCOPE.md+Speakeasy 100x token 基准原文+GitHub MCP toolsets 官方文档+MCP 官方 transport 双轨博客+gingerlabs+SpiceAI/Plural sidecar 代价文献 14 源；置信度中高，「pitch 挂多久」无权威定量先例如实标注） | 采纳 | A（四条约束版）=六件范式全登记为 0.7+ shape 轮候选 pitch 入 ADR-0023 D-192 登记块扩列：①skill 包制（触发=工具面超 ~35 件挂既有 tool-count CI 闸复用 D-179③③ 原文/域分化实证）②minimal 渐进加载（触发=D-179③① 原文 Disambiguation 批后仍 3/5 且真实客户端实证选错——与 P3 合并是同病灶两反向解，显式互引同窗竞裁不分别处置）③Rust sidecar（触发=多实例部署需求实证；sidecar 机制绑定我方不存在的网关/多实例架构前提=机制 vs 范式分离判定）④Streamable HTTP（触发=远程会话/render-farm/CI 远操实证；官方双轨 stdio=本地一等公民无迁移压力）⑤dcc-mcp-cli 控制面（③伴生面条目写明禁独立 re-shape）⑥core 共享多适配器（触发=第二 DCC 立项 fail-loud 事件非持续观测）。四条对冲约束：a 每件≤5 行紧凑条目（动机+不-bet 理由+触发条件+证据指针占位，fat-marker 心智模型——pitch 本体属触发成就后 shaping 工作禁入登记块）b 「与门同寿」扩为「与登记所锚事件同寿」——②锚 v1.0.0 门审与 P3 同窗、①③④⑤⑥锚 0.7+ shape 轮开窗，条目显式标各自事件锚 c observe 态措辞纪律统一「本轮未 bet，re-shape 触发条件=X」禁拒绝/否决字样 d 机检条件挂既有探针、非机检条件入 release-preflight 呈报义务行并如实披无自动探针缺口 | 负向：①C 独立 docs/pitches/ 目录不可执行——D-148 同型否决先例+触发条件与 ledger 触发债构成双真源违 D-183；②登记块非 pitch 本体仓库——≤5 行预算超则回 ledger 另立载体再裁不得原地膨胀；③0.7+ shape 轮若从不开窗条目按触发债「已触发未兑现」显式悬账不静默消失；④25 件≈27k tokens/学界 20-25 件准确率降阈=②病灶真实存在但安全切片已归 D-207①、残余归 Glama 批后快照不预判；⑤TDQS toolCount 维与分组激活的张力（每组建 5-15 件可能占高分便宜）属 shaping 期账目登记期不判 | current |
| D-209 | R45-Q8' 竞品 reject 组+遥测观察项裁决（atomcode 调研辩证版：arXiv 2605.24660 短名单选对率原文+arXiv 2411.15399 Less-is-More+Russ Cox Go 遥测 opt-in 原文+marcon.me CLI 遥测六实践+AlexHorovitz ADR-0011 Revisit-when 形态+dcc multi-instance.md/llms.txt/README 一手+Skills-Directory G14 多源；置信度高） | 采纳 | A（加固版）=①「212 工具军备竞赛」方向 reject——措辞=「reject 以工具广度为竞争主轴的增长方向，非拒新工具（新工具仍走常规立项）」；回归条件=域分化实证（须满足 ADR-0027 注入模块准入判据）∨工具数自然增长至 30（锚 D-094『30 阈值安全区』边界）；实证补强：dcc 自述已膨胀至 245 工具/30 skill 包且其 capability manifest+skill stub 机制本就是为对冲自家广度税打的补丁（广度税自担）；学界阈值（自适应短名单 93.1% vs 固定 87.1%、OpenAI<20/Anthropic 30-50 阈值）与本仓 TDQS 判据（3~15=5 分/16~25=3 分/26+=2 分，25 件已居 3 分带顶第 26 件掉带）三源同向②「多实例部署拓扑」reject-with-pitch 桥——自洽性检查成立（reject 宾语=网关居中管 N 进程+LAN 接入+FileRegistry 机器级注册的部署形态=机制层；pitch 宾语=多实例需求=需求层，与 D-060② 分层多实例文档先例不冲突，SessionManager 多会话能力不受影响不更名）；唯一回归路径=D-208 pitch③ 且触发可证伪化加固「须附不可由 SessionManager 满足的具体场景（跨机/进程级隔离/独立失败域）」防一句话重提③遥测闭环=observe 项登记——关键洞察：D-018 审计 JSONL（outcome 含 rejected）已是本地遥测的 ~80%，触发后首选形态=「本地审计聚合→人工审阅」可能完全不碰 D-030 zero-telemetry 宣称（比 dcc cli stats 路径更优，作方向注记入登记）；措辞=「0.6.0 发布后≥1 季度真实使用窗口+出现『改进依据不足』具体痛点（定性为 issue/反馈原文非推测）届时立项；任何采集面落地前须过 threat-model 披露面扩展裁决；本 observe 项不引入任何当前行为变更」；兜底=若届时披露面裁决被否→债转 README/issue 显式征集反馈替代路径 | 负向：①竞品事实更正须入账——dcc 现为 245 工具非 212（旧口径更正沿 ac153fc 注记惯例）；②「军备竞赛」措辞永不得扩大解释为新工具立项禁令；③多实例 reject 不得被读为「多会话能力」否定（SessionManager 面不受影响）；④遥测 observe 非承诺落地——触发后仍须走完整立项+披露裁决链；⑤Go opt-in 判例启示入档：opt-out 存在本身会被正当化更不谨慎采集面，故任何未来遥测默认 opt-in | current |
| D-210 | R45-Q9' stage-④ 三小项结案裁决（atomcode 调研辩证版：ISO 9001 APG 不符合项关闭判据+SOC2 evidence-vs-documentation 二分+PCAOB AS 1105/1215 底稿分层+PMBOK assumption log 惯例+D-004/065/122 非缺陷归置先例；置信度高，CMMI 逐字原文未取得降惯例层类比如实标注） | 采纳 | A（硬化版）=三小项合并一本行落 canonical closeout 记录：①CRLF 表述更正=verified-fixed 结案——correction=canonical 账本/ADR grep 证零残留旧表述（域=docs/decision-ledger.md+docs/adr/* 全量）；cause=审计方自认「本机工作区污染非仓库属性」范围性幻觉；action=D-205④ pre-commit mixed-line-ending 护栏已立（CI 行尾扫描裁否=知情放弃纵深符合风险比例）；环境面残余=worktree 已净（git status 空）非仓库变更不当关闭条件②PV4 证据载体=no-actionable 结案+触发债登记——决策级层已 canonical：结论层=ledger D-194..201、执行层=exec-B lane 仓内测试件（checker/语料/firing fixture 随 merge 进仓）+.github/scripts/ 探针；过程报告留 .scratch 符 D-109 KORA 合同；触发条件债=「出现对外宣称须挂工件的 R44 结论时→按 D-109 单件冻结」，当前触发态=否③N1 根因=open-assumption 登记——验证协议=下次 but workspace commit 后立即 git diff --cached，index 停 base 即坐实「GitButler 未同步 index」推断；协议入 docs/handoffs/next-round.md standing task book；坐实→AGENTS.md known-quirk 行+酌情上游 issue；出口锚=两窗未复现→标「多窗未复现维持未验证」显式关闭不无限挂 | 负向：①本行同时充当三小项的 canonical closeout 记录不留散注；②PV4 触发债非口头备注须以触发条件债形态存在；③N1 验证靠人记得易漂移故须入 standing task book；④三判定词（verified-fixed/no-actionable/open-assumption）分别对应 ISO 9001/SOC2/PMBOK 判据面不得混用 | current |
