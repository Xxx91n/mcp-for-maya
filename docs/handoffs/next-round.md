# next-round.md — rev36（R28：v1.0.0 门前清单就绪裁决落地）

生成：2026-09-28 R28 grill 整理环节｜Spec：docs/decision-ledger.md D-127..D-132（本轮零 revised——全部裁决=履行既有立法）｜前置调研：R28-Q1..Q5 经 atomcode 派发+ctx 索引（ctx_search 可取）｜题面档：.scratch/t28/questions/q1..q5-*.md

## 环境实况（本环节核验 03:24 UTC）

- main=8bef528；本分支 grill/round28-v1-gate 文档栈 3 commits（uox/zkq/tkq=账本 D-128..D-132+D-127 行内注记）+本批（CONTEXT 三处+本任务书）——未推未合，合并时机用户裁。
- 0.4.0 在飞：pyproject.toml:14 classifier 仍 `3 - Alpha`（D-131 已拍板升 4-Beta，T-28a 落笔）；25 工具；pyproject:99 max_warnings=0（D-117 已兑现销账）。
- drift-canary：dispatch 首燃全绿（run 36334876189=D-127 复核记录成立）；**schedule 事件链未验**——首个 cron 窗口=2026-09-28 06:37 UTC；`gh run list --event schedule` 现为空（未到点属正常，非静默故障）。
- milestone 已就位：v1.0.0=#1←#7、v1.x=#2←#31/#6/#4/#3；#7 body 顶部 tracker 声明行已写入（body=操作副本，清单权威=ADR-0023+账本）。
- main 分支保护=未设置（gh api 404）——D-036⑤ 从未执行，gate 核对时裁（硬项或显式豁免写理由）。
- 残留待确认删除：.scratch/maya-mcp-grill/decision-ledger.md（旧档止 D-041，活账本=docs/decision-ledger.md）——未确认前不删。
- CONTEXT.md 本轮整理窗已落：金丝雀词条「事件链独立」句（D-129）+新词条「发布门前清单」「校准宣称」（D-131/D-132）。

## 批次序与规则（D-131 时序条）

序=T-28a（文档+元数据批，commits 分立）→T-28b（观测+外部门，非代码）。0.4.0 发布本体走既有 D-084/D-108 playbook（本任务书不重载）；**gate 核对时点=0.4.0 发布后**；1.0.0=0.4.0 之后下一 release，不插 0.5.x（真机窗出 feature 级 blocker 除外）。
**andon**：commit ② 若与 0.4.0 tag 竞速——先升档再 tag；一旦 0.4.0 已推 PyPI，classifier 不可回改（release 不可变），升档顺延。
**回滚边界**：文档 commits 各自 revert；milestone/issue 归置已生效（回滚=gh api 再 PATCH）。
**冻结语义**：gate 清单正文以账本 D-131 规范化列为唯一真源——ADR-0023 增补块是抄写+格式化，不得自行增删清单项。

## 任务清单

### T-28a — v1.0.0 gate 文档+元数据批（D-131+D-132，commits 分立）

**commit ① ADR-0023 R28 增补块**（清单载体）：照抄 D-131 规范化清单——硬项【#7 十框全绿(D-040)/D-115 补采同窗/D-127 复核记录(已兑现+cron 对照完成条件)/节==tag diff(D-107④)/版本阶梯 0.4.0 升 4-Beta→1.0.0 同 commit 5-Stable(D-032)/GH Release(D-084/108)/milestone 归置(D-130 已执行)/public-API 冻结声明/D-036⑤ 分支保护入硬项或显式豁免写理由】+软前置（T-24 mayapy 冒烟或 D-049 披露）+一次性过堂行（断链/陈旧宣称/实验态措辞/CVE-2026-66004 适用性核验/twine check D-080⑤）+观测项×2（schedule 链首验、notify 红路径）+裁出（D-102/D-104/D-118）+go/no-go 末行（账本行逐项挂证据指针，用户拍板）+时序条。
**commit ② classifier 升档**：pyproject.toml:14 `3 - Alpha`→`4 - Beta`；核 README:320-321 阶梯措辞一致性（已写 Beta=feature-complete+外部测试开始）。
**commit ③ 公 API 冻结声明+叙事层**（D-131+D-132）：README Versioning 节增一段（public API=MCP 工具名+IO 形状+双层错误契约+annotations 语义；additive→minor、breaking→major；不立 snapshot 新机件）；README 宣称句式校准=能力+证据指针、安全宣称指 enforcement 代码/测试节点、**不点竞品名/CVE 号**；docs/threat-model.md §4/§5 引 CVE-2026-66004（VulnCheck/issue #257 链接）作「download-and-import 类工具野生生态已实证路径穿越→任意文件写」论据+CTA 礼仪维护注记（引用未公开同行漏洞须先知会竞方）。
**commit ④ 一次性发布面过堂**：断链全扫/陈旧宣称清点/实验态措辞核对/**CVE-2026-66004 对本仓 asset_import 路径适用性核验**（CVE 本体已双源核实：BlenderMCP<30a3308 download_polyhaven_asset CWE-22 CVSS 6.0；适用性核验=查我方资产下载代码的域名白名单/路径 sanitize/md5 是否覆盖同类病灶）/twine check（D-080⑤）；结果落账本行或 docs/evidence/。

suggested skills：domain-modeling（ADR 增补措辞）、neat-freak（过堂行）、gitbutler（commits 分立）

### T-28b — 观测与外部门（非代码）

- **cron 对照核验**（D-129/D-131 执行项）：2026-09-28 06:37 UTC 后 `gh run list --event schedule` 非空+结果归因入账；静默未触发→升级方案=外部 cron 调 dispatch API（#206369 同款故障面）。
- **notify 红路径**：非 blocker 观测项——自然真红免费闭环，禁制造红（D-129 已裁，smallest-blast-radius）。
- **D-036⑤ 分支保护**：gate 核对时裁——开启（gh api 外部动作须用户确认）或账本显式豁免写理由。
- **用户专属门**：#7 十框真机项+D-115 探针工件补采（同窗）+T-24 mayapy 冒烟或 D-049 披露+最终 go/no-go 拍板。
- **0.4.0 发布本体**：D-084/D-108 playbook（tag/GH Release minor 档/PyPI）；gate 核对在其后。

suggested skills：neat-freak（cron 核验归因）、atomcode-research（静默升级需外部 cron 方案细节时）

## 债库存（触发态快照 2026-09-27 核验）

D-102（否）/D-104（否——PyPI 实测 fastmcp 最新 4.0.10、无 5.x 线）/D-115（是-不可即兑，无真机窗）/D-118（否-未实测）；D-127 已兑现出库存。

## 措辞红线

- 归因禁写「weekly schedule 已验证」（事件链独立，D-129）。
- README 禁点竞品名/CVE 号、禁「we take security seriously」类惰性语句（D-132）。
- 宣称句式=能力+证据指针；1.0.0=public API freeze 承诺非质量认证（D-132/D-131）。
- 账本唯一真源纪律：一切结论以 docs/decision-ledger.md 为准，不从对话回忆补写。
