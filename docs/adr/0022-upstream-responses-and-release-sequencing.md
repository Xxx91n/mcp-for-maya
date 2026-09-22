# ADR-0022 — 上游 issue 回应策略与修复公开化时序（T-17 spec 簇）

状态：accepted（grill 定稿）
日期：2026-09-22
决策来源：D-061（本轮范围）、D-062（公开化时序）、D-063（回应形态）、D-064（回应矩阵+对照表）、D-065（N1~N6 归置）

## 背景

上游 chadrik/maya-mcp-server：6 个 open issue 维护者零应答，最后 push 2026-07-15——issue 区已成用户互助荒原（#1 唯一评论为旁观用户证实 Maya 2026 同病）。本仓已 PUBLIC（Xxx91n/mcp-for-maya），README 双语披露 fork 血缘+MIT 保留，PyPI mcp-for-maya 0.1.0/0.1.1 在售且未 yank。T-16 已实施（impl/t16-upstream-issues 6 commits，审计 PASS-WITH-NITS 五门绿）但未落主干——公开版本不含 T-16 修复。用户提出新题面：要不要在上游 issue 内给宣传回应。

### 证据订正轨迹

D-061 约束区写入时（预核验）称「在售 0.1.1 带 #7 吞错缺陷」；随后 git show 实证 **v0.1.0/v0.1.1 的 server.py 均含 raise_for_error**——上游 #7 报告的精确症状在任一已发布版本不存在；0.1.1 wheel 依赖面无 fakeredis（#2 同）。0.1.1 的「坏」实为 T-14 期传输路径/call-form 缺陷（D-049 语境），非 #7 症状。此订正不改 D-061 决策（本轮范围），D-064 已采信实证——留此轨迹而非隐去。

## D-062：公开化时序——立即落地，发布守 D-049 门

裁决：

1. **立即落地**：but land 落 impl/t16-upstream-issues + grill/round16 spec 分支进主干。依据=审计全绿+悬置分支漂移成本真实（CHANGELOG/README 同文件区是未来发布冲突热点）；落地=agent 可执行动作（T-14a but land 先例）。
2. **0.1.2 守 D-049 真机门不松**：同类传输路径真机验证=T-16f 窗口前提，Maya 未开机则门不满足。放宽须走 revise 流程——本轮明确不走。
3. **0.1.1 yank 维持随 0.1.2 同发**：0.1.0 同带病，单独 yank 0.1.1 会把 pip 引到同样坏的 0.1.0=净损。
4. **落地≠宣称修好**：#1/#4 在 T-16f 真机定型前，一切对外文案带 pending-real-Maya-confirmation 措辞（D-059 纪律延伸）。

否决项：(B) 放宽 D-049 门立即发 0.1.2——真机门是 D-049 明文，松口=质量叙事先例事件；(C) 落地也等 T-16f——审计已判 PASS-WITH-NITS 非半成品，悬置只有成本。

## D-063：上游回应形态——技术+署名型

裁决：每 issue 一条评论=根因分析→修复路径→「已在 fork Xxx91n/mcp-for-maya 实现，版本见对照表」指针→fork 关系披露→「若维护者需要可回哺修法」礼貌句。

定位：回应第一功能=给卡在 issue 上的真用户留路标（维护者零应答的荒原上补位），引流为副产品非目的。纪律：一 issue 一评不追评；措辞事实陈述非广告；最坏情况=评论被删零成本。发布动作=人工门（agent 备稿，用户发或显式授权）。

否决项：引流型/promotion-first（spam 邻域+与诚实姿态冲突——用户原词「宣传回应」经 domain-modeling 钉义为技术回应含署名指针）；纯技术型（对 stranded 用户无导航价值）；不回应（issue 区继续荒原化）；PR 回哺主路径（绞杀者式重写 diff 无维护者可接，仅留口头回哺意愿）。

## D-064：回应矩阵与时机——分段 + 对照表

矩阵（模板统一，内容逐条）：

| issue | 时机 | 版本指针 | 形态备注 |
|---|---|---|---|
| #2 FakeConnection | 现在可发 | ≥0.1.0 已含 | 依赖面移除 fakeredis；耐久真话不受 yank 影响 |
| #7 吞 result.error | 现在可发 | ≥0.1.0 已含 | raise_for_error 自 v0.1.0 在 server.py；注明传输加固随 0.1.2 |
| #1 MEL 探测 | 0.1.2 后 | ≥0.1.2 | eval("1/2")+豁免集+端口过滤；T-16f 翻车则如实写豁免集方案 |
| #3 ast.unparse | 0.1.2 后 | ≥0.1.2 | 不修边界声明（dual-runtime floor+显式能力错误），非修复公告 |
| #4 teardown | 0.1.2 后 | ≥0.1.2 | _mcp_teardown 钩子+Qt 信号断开；T-16f 背书 |
| #5 多实例文档 | 0.1.2 后 | ≥0.1.2 | README/testing.md 分层文档章节链接 |

附带项：**docs/ 下新增 upstream issue 对照表**（6 issue×我方处置×版本号×验证状态）——回应固定锚点+透明度叙事资产；须与账本/CHANGELOG 同源不失真。

否决项：统一批次（#2/#7 真陈述陪绑不定期真机门）；逐条按验证状态（六窗口成本高）。

## D-065：N1~N6 审计遗留归置

- **N1~N3 随 T-16 落地窗口同批修**（合计<20 行）：N1=_bootstrap 收返回值 log teardown warning 不静默吞；N2=ADR-0009 superseded-by-0021 注记；N3=AGENTS.md tests/ 清单+adr 描述同步。
- **N4 五条 smell 登记债**入任务书不自动认领：write_module 双通道 warning 重复/_port_type 私有访问×2/__build__ 无断言消费方/_parse_port_filter 裸 ValueError+反向区间静默/add_session host 不归一。
- **N5 归 T-16f 内收**：MEL eval→UNKNOWN→冷却即 ADR-0021 已登记退路形态。
- **N6=删 .github/assets-src/*.py** 两个 untracked facade 孤儿（用户选 A 含此子裁决）。zz 区幻影 5 条 @2x R 残留不属此列，仍严禁 discard。

## 证据强度说明

- 上游 issue 状态/维护者零应答/最后 push 经 gh API 实证；本仓可见性+PyPI 版本+yank 状态经 gh/pypi JSON 实证
- #2/#7「全版本已修」经 git show tag 内文件直读+PyPI requires_dist 实证——非记忆推断
- 分段时机的全部宣称均以「评论发出时公开版本真实包含」为前提
