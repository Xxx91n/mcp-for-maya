---
generated: 2026-10-05
from_round: R47（钉类别法典立法+tag 改锚+残余微裁决收口，覆盖 D-223..227）
ledger_head: canonical=D-227（D-223..227 已随本批迁入；.scratch/r47-grill/decision-ledger.md 过程件留档勿重迁）
branch: R47 docs 批（ADR-0030+ADR-0029 指针 amend+AGENTS+CONTEXT+canonical 迁+本任务书）待 push/PR/merge；上游 main=032ea03（PR #72 已合，CI 首绿含 ubuntu）
---

# 下轮任务书（rev56）

## 状态总览（R47 收口）

- **R47 五裁决全落账**（D-223..227，canonical 已迁）：D-222 框架扩展序/tag 改锚 HEAD bump（D-218 revised）/三类法典+R7/R8+分类迁移（D-213 scoped revised→ADR-0030）/交接载体全量强制+R7/R8 单翻/[0.6.0] 选择性折节/豁免事件锚+到期处置菜单+B 触发锐化+两行执行纪律。
- **立法批本批已落盘**：ADR-0030 新篇（三类法典+R7/R8+迁移+豁免菜单+翻转+交接载体+披露）+ADR-0029 §3 supersession note+AGENTS 两行（gate-integrity 三要件限定+handoff carrier 条款）+CONTEXT 四新词（live 对照钉/性质断言/交接载体/孤儿钉，反事实钉词条 amend 类别限定）+canonical 迁 5 行+本任务书。
- **实况**：main=032ea03（R46 governance lane 已合，CI 首次全绿含 ubuntu 3.10/3.x）；registry 17 条目 45 钉（仅 4/45 合规范式——迁移批对象）；check_gate_registry 仍在 ::warning:: 观察期；v0.6.0 tag 未打（目标=HEAD 上 bump commit）；Glama 观察=glmax.txt（10-04 19:53 抓取）证实评语评旧文案=A4.1→C2.9 回归，staleness issue 待 tag 后发。
- **N1 维持结案**（D-219）：多窗未复现；reopener=下次真实 but commit 顺手 git diff --cached（阳性即复活）。R47 docs 批 commit 后已顺手执行见下。

---

## T-R47-00：v0.6.0 tag 链（第一优先；D-224 改锚授权）

覆盖 D-224 + D-226③ + D-227④ + D-206 残留 + ADR-0023 preflight 全清单。

1. release-prep 分支→bump commit：pyproject/__init__/llms.txt 0.5.0→0.6.0 + **选择性折节** [Unreleased]→[0.6.0]（用户面入=描述地板批+R45 strict policy/llms.txt/error-codes/session-lifecycle+相关 Fixed；R46 纯 CI 治理件+exec-B 类留 [Unreleased]——D-107④/D-206③）；CHANGELOG/发布说明记 f97857f 为「tag 语义基点」；
2. preflight 九行对 **bump-commit 树**跑（非 f97857f 树——D-224③）；
3. 全绿→人工确认门呈报核对单→git tag -a v0.6.0（annotated，D-150③）→push tag；任一行红→停住呈报；
4. PyPI publish 不在此授权——另走人工确认门（D-206 负向①）。

## T-R47-01：Glama staleness issue（tag 后；D-220+D-227④）

1. **时序写死**：bump→tag→发 issue（引 sha:path:line 锚须指最终树）；
2. 文案骨架（D-220 陈旧分支）：camera_orbit C2.9+scene_measure B3.1 评语指控的缺陷在当前描述中不存在（附 A4.1 post-T 实测→C2.9 回归证据=索引回退非单纯时滞）；附当前描述原文+glmax.txt 抓取时间戳；对象=glama-ai；
3. 观察日志落 docs/evidence/+distribution-surfaces 同步+账本事件行。

## T-R47-02：R47 docs 批 push/PR/merge

覆盖 D-225⑤/D-226①③/D-227 载体面。but commit 本批（ADR-0030/ADR-0029 amend/AGENTS/CONTEXT/canonical/next-round）→but push→but pr→squash-merge。

## T-R47-03：钉形态闸实现 lane（D-225/D-226②）

1. check_gate_registry.py 新增 **R7 形态判红**（gate 类：反事实钉三要件——fails_the_gate 命名+Counterfactual docstring+AST 非空断言；对照钉反向——命中 fails_the_gate 后缀=形式撒谎红）+**R8 反向判红**（bound 对象对应测试文件内 fails_the_gate 未注册→红，不扫全 tests/）；
2. 自身钉=喂空断言钉/错误命名钉/未注册钉→红（落 R8 覆盖）；
3. 迁移批（与 registry 编辑同批不分离）：~24 反事实钉改名+docstring 同步；~8 性质断言迁出 pin_node_ids；迁出归零条目新写反事实钉；
4. 豁免燃烧清单：当期未配齐条目 exemption{reason,expires|issue}——**expires 默认=next release-preflight 事件锚**，per-entry override；到期处置三选一（补钉/续期签认/退役条目）=执行窗提呈+用户批准；
5. ci.yml 注释随本批更新单翻语义（D-226②）。

## T-R47-04：checker 翻转 commit（D-226②）

前置=R47-03 合入（=首个正常 PR 周期走完）+覆盖自查 →小 commit 翻 R1-R8 全 blocking；前提=R7/R8 落地 PR 已配齐自身反事实钉，否则回退独立观察一周期。

## T-R47-05：B 扩面挂账（D-223④+D-227③）

**锐化触发条件**：守护面外文档（含 .github/）内发现一处经独立复算确认、且所属宣称族无既有 deriver 可覆盖的规范性计数错误→开扩面立法轮；F6 四错数字系已修 bug 非新发现不触发。规范性面错数字若发现=bug 直修非立法。

## T-R47-06：baseline 强制再生 lane 槽（D-223⑤）

baseline 文件再生校验闸（ruff/monolith/mypy-baseline/TDQS derivable-set）——实现缺口非立法，下一实现窗开 lane。

---

## 承继项（自 rev55 更新）

- **PV4 触发债**：对外宣称须挂 R44 工件结论出现时→D-109 单件冻结入 docs/evidence/（触发态=否）。
- **pitch/observe 呈报**：preflight 第 9 行义务（六 pitch+遥测 observe 项状态盘点落账本观察行）——D-208 pitch 全部维持 observe-state（竞品分析已毕非未做）。
- **T-R45-05**：strict 回归套真机档 -m gui 仍 deferred（需真实 Maya 会话，D-211 维持）。
- **观察窗**：10-30 D-146 核销/awesome PR #15382 合并跟踪/Glama（T-R47-01 收口）。
- **审计残余**：R2 probe JSON 补强/R3 拆行配额规则（承继未动）。
- **N1 reopener**：下次真实 but commit 顺手 git diff --cached。

## 硬约束继承

- 交接载体=.scratch/{slug}/handoffs/ 强制，%TEMP%/仓外路径禁用（D-226①，skill 默认对本仓无效）；
- PyPI publish 人工门（D-206 负向①+D-224）；tag=annotated+挂 bump commit 版本一致树（D-224/D-150③）；
- registry 人编禁脚本生成（D-215）；豁免必带 expires|issue+到期处置菜单（D-215/ADR-0030 §4）；
- 三类法典：fails_the_gate=反事实钉专属后缀，对照钉禁用（ADR-0030 §1）；性质断言不入 pin_node_ids；
- 不可复现标未验证不猜因（D-205③）；非机器载体宣称不作数（D-205②——覆盖率/计数宣称须挂机检载体）。

## suggested skills

- $implement / $tdd：T-R47-03/04/06 实现件（钉测试随行为同 commit）
- $gitbutler（but）：全部版本控制写操作（T-R47-00/02）
- $code-review：R47 实现 lane 评审面（迁移批+新判红集）
- $atomcode-research：B 扩面开轮时的分族判别先例、Glama issue 措辞佐证
- $handoff：收尾交接（载体=.scratch/{slug}/handoffs/，非 %TEMP%）
- $domain-modeling / $neat-freak：结案批术语与文档面对齐
