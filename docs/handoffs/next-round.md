---
generated: 2026-10-03
from_round: R46（机械核验完整性通则立法 grill 定稿+未闭项随裁，覆盖 D-211~222）
ledger_head: canonical=D-222（D-211..222 已随本批迁入）；.scratch/r46-grill/decision-ledger.md 过程件留档勿重迁
branch: R46 docs 批（ADR-0029+CONTEXT+AGENTS+CHANGELOG+ledger 迁+本任务书）待 commit/push；实现 lane 序=L1+L2 同波→L3 并行→L4 殿后（D-222）
---

# 下轮任务书（rev55）

## 状态总览（R46 收口）

- **R46 十二裁决全落账**（D-211..222，canonical 已迁）：范围排序/适用面五档（否决权判据）/钉形态法典化/外部派生双轨/登记表五判红+过渡 warning/裸计数四问判别+统一 check_count_claims 载体/ADR-0029 载体裁决/tag 一次授权全链/N1 出口锚结案/Glama 双层时间戳+无 C 通过线/S1-S4+R4+R7 处置/实现件打包序。
- **立法批本批已落盘**：ADR-0029 专篇+CONTEXT 八新词（oracle 锚定/反事实钉/治理vs机制常量/规范性宣称vs时点记录/钉登记表/终止层/否决权判据/双层时间戳判据）+AGENTS 指针行+canonical 迁 12 行+CHANGELOG 五 Fixed 补 broken→fixed 字段（S1）+R4 碎屑删除+本任务书（R7 过期同步）。
- **上游实况**：origin/main=87a1b6a（merge 波完成，PR #66..71 全合）；909 passed/26 skipped；**v0.6.0 tag 未打**（T-R46-00 待点火，目标 f97857f）。
- **N1 结案**（D-219）：多窗未复现→维持未验证显式关闭；收尾注脚=下次真实 but commit 顺手 git diff --cached（阳性即 reopen）。
- **Glama 实况**（2026-10-03）：聚合 A3.6 Scored 10-01=pre-T 观察非验收；camera_orbit A4.1/scene_inspect A4.5/maya_setup_guide A4.2 已刷 post-T 局部；scene_measure B3.1 陈旧读数待 post-T 判读。

---

## T-R46-00：0.6.0 tag 链点火（第一优先；D-218 一次授权）

覆盖 D-218 + D-206 残留 + ADR-0023 preflight 全清单。

1. release-preflight 九行对 f97857f 树跑（含第 8 行 TDQS 到期豁免+第 9 行 pitch 呈报+D-107④ tag==diff 核对+exec-B 产出留 [Unreleased] 核对）；
2. 任一行红→停住呈报不点火；全绿→人工确认门呈报核对单→git tag -a v0.6.0 打 f97857f→push tag；
3. PyPI publish 不在此授权——另走人工确认门（D-206 负向①）。

## T-R46-01：R46 docs 批 push/PR/merge

覆盖 D-217/D-221①④/D-222①。but commit 本批 docs（ADR-0029/CONTEXT/AGENTS/CHANGELOG/ledger/next-round）→but push→but pr→squash-merge；无代码依赖可与 L1+L2 并行筹备。

## T-R46-02：Glama 观察协议执行（D-220）

1. 判读时点=聚合徽章 Scored>T（T=merge 波完成）且该工具评估块时间戳>T——双层各自卡住；
2. 通过线=无关键工具 C 及以下（camera_orbit A4.1 已达标）；
3. scene_measure post-T 读数：评语引新文案仍 B→按批评点挂定向改进任务不阻塞；评语引旧文案→报 glama-ai staleness issue；C 及以下→当轮迭代+下窗复评+两轮（24h×2）不动报 issue；
4. 聚合 T+72h 不翻页→staleness issue；全程观察日志落 docs/evidence/+distribution-surfaces 同步+账本事件行。

## T-R46-03：L1 登记表脊骨 lane（D-215）

1. .github/gate-registry.yaml 人编首版（逐闸盘点 gate_id/bound_class/pin_node_ids/expected_source/exemption）——bound 全集从 check_*.py glob+仪器清单机器枚举；
2. .github/scripts/check_gate_registry.py 五判红+expected_source 弱校验（path::symbol 形态）；
3. 自身钉=喂腐坏登记表→红（终止层）；CI 接线 ::warning:: 模式起步；
4. 翻转 blocking=合入后首个正常 PR 周期走完+覆盖自查（D-222⑤）。

## T-R46-04：L2 常量迁移+S3/S4 lane（D-214/D-221②）

1. 五处治理常量迁分散 spec 文件按严重度序：MIN_ADJUDICABLE/MIN_TN_PER_ELEMENT→LINE_CAP→GUARDED→ISSUE=7→PROTOCOL；
2. S4 修复（counts+=1 出 per-element 循环）——先按 D-203 口径核对分子定义语义再改+配钉；S3 恢复 D-198⑤ caveat（同文件同评审面）；
3. baseline 文件语义条款落地：存档帧禁手写数字。

## T-R46-05：L3 check_count_claims lane（D-216/D-221③）

统一入口 check_count_claims.py+per-family deriver（tools AST 键数/11 checks 检查器枚举/5 dims/8 shot types）+denylist 层+docs/guide/*.md 守护面纳入 lint job。

## T-R46-06：L4 钉回填 lane（D-212/D-213）

薄钉/零钉闸补进程内钉+live-green 对照（疑似零钉：evidence_anchors/readme_skeleton/version_unification/liveness_probe/notify_drift_canary——逐闸复核钉现状再补）；探针敏感度实验形态+周跑 cadence+豁免抽样。

## T-R46-07：S2 事后补验（D-221③）

轨③→轨② 5 条晋升语料样本逐条人工抽验→记录如实标 post-hoc review @R46（禁伪造前置时间戳）。

---

## 承继项（自 rev54 更新）

- **PV4 触发债**：对外宣称须挂 R44 工件的结论出现时→D-109 单件冻结入 docs/evidence/（触发态=否）。
- **pitch/observe 呈报**：preflight 第 9 行义务（六 pitch+遥测 observe 项状态盘点落账本观察行）。
- **T-R45-05**：strict 回归套真机档 -m gui 仍 deferred（需真实 Maya 会话）。
- **观察窗**：10-30 D-146 核销/awesome PR #15382 合并跟踪/Glama Scored>T（T-R46-02）。
- **审计残余**：R2 probe JSON 补强/R3 拆行配额规则（rev54 承继未动）。

## 硬约束继承

- exec-B 产出禁入 [0.6.0] 节（D-107④）/PyPI publish 人工门（D-206 负向①+D-218⑤）/登记禁脚本生成（D-215）/豁免条目必带 expires|issue/新宣称写时判别（D-216⑥）/不可复现标未验证不猜因（D-205③）。

## suggested skills

- $implement / $tdd：T-R46-03..07 全部实现件（钉测试随行为同 commit）
- $gitbutler：T-R46-00 tag 链+T-R46-01 docs 批+四 lane 管理
- $code-review：ADR-0029 立法文本+各 lane 闸件显式 review
- $atomcode-research：仅注册 pitch 触发条件命中时（每会话一 run 护栏）
- $handoff：R46 exec 收官时出下一轮交接

## 附：R46 账本存档说明

R46 十二行 verbatim 已迁入 canonical D-211..222（勿重迁）；过程件留 .scratch/r46-grill/（atomcode-q6..q9 调研题+GOAL.md+本 handoff）。
