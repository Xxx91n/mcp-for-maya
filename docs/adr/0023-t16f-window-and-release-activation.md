# ADR-0023 — T-16f 真机窗口执行面与 0.1.2 发布链激活（T-18 spec 簇）

状态：accepted（grill 定稿）
日期：2026-09-22
决策来源：D-066（本轮范围）、D-067（T-16f 执行面）、D-068（发布激活序列）、D-069（#2/#7 发帖机制）

## 背景

T-17 已实施并独立审计 PASS-WITH-NITS：`origin/main` 顶=b3f4133（T-16 spec×2+impl×6+T-17×6+dependabot mypy 合并），CI 全绿；幻影簿记自清（zz 无变更、porcelain=0）；上游六 issue 评论数实测 0（人工门零越界）；PyPI 仍只有 0.1.0/0.1.1 未 yank。审计新增登记债 N7/N8/O1/O2。**关键状态位移：Maya 2024(24.0.0.4640) 已开机**——PID 18236，userSetup.py 开 `:7001 sourceType=python` LISTENING——T-16f 真机验证窗的硬阻塞解除，D-049 门从"无限期挂账"变为"本窗可满足"。

## D-066：窗口开启合并轮

Maya 开机激活整条阻塞链，本轮同裁：T-16f 执行面 + 通过后的发布链激活序列 + N7/N8/O1/O2 归置 + 0.1.0 yank 补裁 + #2/#7 发帖机制。依据=同一棵决策树：验证一过，发布/yank/回应依次激活，逐项临场裁会在窗口里卡死。

## D-067：T-16f 执行面（atomcode 调研修正版）

1. **场景处置=只读探针先行**：窗口第一步 `file(q=True,modified=True)`+`file(q=True,sceneName=True)`——场景脏则**停手报用户三选一**（存盘后跑/授权丢弃/中止窗口），干净才 `file(new=True,force=True)`。VP2 批走"干净场景+临时 namespace"组合（namespace 不替代新场景——undo 栈/selection/shader 绑定仍污染——但适合 currentTime 净零这类纯读微注入）；run 开头幂等扫残（临时对象记 namespace 全名）。**实证依据**：dcc-mcp-maya #240/#255 dirty-scene guard 先例——脏场景上不 force 会弹模态保存对话框**永久挂死 UI 线程**（等价 server 死亡）；`file(new,force)` 于脏场景=静默丢未保存工作，社区公认危险操作；直接跑用户场景零信源支持（"测试运行者的场景是不可信状态"为业界公理）。
2. **MEL 对照端口=全生命周期管理**：execute_code 先 `commandPort(":7002", query=True)` 探占用（被占换高位端口）→开 `sourceType="mel"`→验证完 try/finally 关闭+下次幂等先 close 再 open。**仅用 `:port` localhost 形式，禁用 `IP:port`**（官方原文：INET socket 无鉴权、命令以 Maya 用户权限执行含 `system()`；安全通告 adsk-sa-2025-0008："不需要就禁用"→用后即关、窗口越短越好）。预期 Maya 2022+ 首次外部连接弹 "Allow" 模态安全对话框——用户在场授权，属批次已知项。
3. **执行者=agent 自主+分级守卫**：pytest -m gui 全批+MEL eval 探针+teardown 活证由 agent 执行；唯二用户前置点=①脏场景命中时的处置三选一②断连窗口知情（报告显式标注）。"生成命令清单交用户手跑"零信源支持，否决。

## D-068：发布激活序列（atomcode 调研修正版）

**八步序定稿**（T-16f PASS 后触发）：

1. upstream-issue-status.md 验证列更新（stub 绿→real-Maya 实证）+ 备稿去 pending 限定措辞
2. N7+N8+O2 同窗修掉+门禁复跑（真机窗覆盖 N7 路径）
3. O1：CHANGELOG `[Unreleased]` 并入 `[0.1.2]` 订正真实日期，顶部留空 Unreleased 段（Keep-a-Changelog 惯例）
4. 备发布包：tag 说明/release notes（取 CHANGELOG 段原文——pyhf 教训：先拷贝再发防被覆盖）/yank 命令与 reason 文案
5. **人工门**：push tag v0.1.2 → release workflow → **盯 publish CI 到绿+验 PyPI 页面**（本项目 invalid-publisher 前科，此步不可省）
6. **逐版核实后 yank**（详见下）
7. 上游评论收尾（链接已稳定）
8. 可选：GitHub Release v0.1.1 加 "yanked on PyPI" 标注两边对齐

**a) N7=fix-forward 修进 0.1.2**：Go release cycle 准则——RC 签发前的 freeze 窗口内按 "low risk and high reward" 收放；本项目无 tag 无 RC 正处该窗口，~3 行+1 测试可与 0.1.2 同过真机窗（机会成本为零）。"缺陷修复版遗留同族缺陷"的 known-issue 披露负担大于修复成本；ship-with-known-issue 次优解否决。纪律=修完全套 CI+真机覆盖该路径。

**b) yank 改逐版核实制**（对我方"同带病"表述的修正）：PyPI 官方判定单位=**单个 release 非缺陷家族**——0.1.0/0.1.1 之间隔着 T-11b 等修复，须 `git show v0.1.0/v0.1.1` 逐版实证各带什么病，确认带病者才 yank、reason 写具体故障模式（attrs 先例：一句话说清故障模式）。PEP 592 语义钉死：yank 只挡非 pin 解析（`==0.1.1` 仍可装+warning）、可 unyank 回滚；**yank 只在 0.1.2 确认 PyPI 可用后执行**（防全项目无可用版本空窗）。

**R26 增补（D-107④ / D-108②③，2026-09-27 兑现）**：

- 发布清单硬核对项：`[X.Y.Z]` 节内容 == tag diff —— 节内每条叙事条目可归因到 `git diff <prev-tag>..<tag-commit>` 的文件集；对不上即不可发。
- GH Release 判别钉死：minor 版执行、patch 版依 D-084 跳过（release.yml 注释同锚；D-068 原序列文本在此修订）。
- tag 前软前置冒烟：本批新 cmds 面（T-24 = attr_meta / plug_connections / listAttr / attributeQuery）——Maya 开机则跑 `pytest -m mayapy` 冒烟；未开机则 release notes 按 D-049 档披 known-unverified。不设硬 CI 门。

**R27 增补（D-123①，2026-09-27）**：

- 发布清单硬项：v1.0.0 门前须存在 **≥1 条 drift-canary 人为复核记录**（运行结果+归因写账本，**红绿均可**——防「等红灯才复核」死角致清单项永远无法兑现）。红→人知通道=ci.yml `drift-notify` 独立 trailing job（去重 issue/续败评论/恢复自动关）；复核义务登记为 D-127。

**R28 增补（D-131/D-132，2026-09-28）——v1.0.0 门前清单**：

清单唯一真源=账本 D-131 规范化列；本块为抄写+格式化载体，清单项增删须回账本裁决（冻结语义）。

- **硬项**（全绿方可 tag v1.0.0）：
  - issue #7 十框真机验证清单全绿（D-040）
  - D-115 探针工件补采同窗（下个真机窗按 D-109 形态入 docs/evidence/）
  - D-127 drift-canary 复核记录 ≥1 条——已兑现（run 36334876189，workflow_dispatch 首燃全绿）；完成条件另含 cron 对照核验（schedule 事件链首验）
  - 「`[X.Y.Z]` 节内容 == tag diff」硬核对（D-107④）
  - 版本阶梯履行：0.4.0 升 `4 - Beta` → 1.0.0 与 `5 - Production/Stable` 同 commit（D-032 阶梯履行非修改；0.4.0 发布计划调整已单独拍板）
  - GitHub Release 依 D-084/D-108 判别（minor 建、patch 跳过）
  - milestone 归置（D-130 执行面，已执行：v1.0.0←#7、v1.x←#31/#6/#4/#3）
  - public-API 冻结声明（README Versioning 节一段：public API=MCP 工具名+IO 形状+双层错误契约+annotations 语义；additive→minor、breaking→major；不立 snapshot 新机件）
  - D-036⑤ main 分支保护：入硬项执行（gh api PUT，外部动作须用户确认）或显式豁免写理由
- **软前置**：T-24 mayapy 冒烟；未跑则 release notes 按 D-049 档披 known-unverified
- **一次性过堂行**（发布面卫生核验，结果落账本行或 docs/evidence/）：
  - 断链全扫 / 陈旧宣称清点 / 实验态措辞核对
  - CVE-2026-66004 对本仓 asset_import 路径适用性核验（引用前必核）
  - twine check（D-080⑤）
- **观测项**（非 blocker，显式入账防静默收窄）：
  - drift schedule 事件链首验——2026-09-28 06:37 UTC 后 `gh run list --event schedule` 非空+结果归因入账（静默未触发→升级方案=外部 cron 调 dispatch API）
  - notify 红路径真实验证（自然真红免费闭环；禁制造红）
- **裁出**（触发态均否，2026-09-27 核验）：D-102 / D-104 / D-118
- **时序**：0.4.0 先落地（4-Beta）；1.0.0=0.4.0 之后下一 release，不插 0.5.x（真机窗出 feature 级 blocker 除外）；gate 核对时点=0.4.0 发布后
- **go/no-go**：核对产出=账本行逐项挂证据指针，用户拍板

**R30 增补（D-142β，2026-09-28）**：

- 发布窗 preflight 第 6 行：release body 披露附录断言——`python .github/scripts/check_release_appendix.py <tag>`（弱断言=附录节存在+非空+引用 #7；#7 open⇒义务生效、closed⇒义务解除，不数 `- [ ]`；fail-loud 三显式报错：gh 不可用/HTTP 非 200/rate-limit 403）。人工执行项，不进 push CI；断言脚本随 pytest 回归（tests/test_check_release_appendix.py）。

## D-069：#2/#7 发帖机制

本窗口即发（备稿就绪+"≥0.1.0 已含"耐久真话不依赖 0.1.2）；执行=**agent 贴终稿→用户过目→gh 以用户账号发出**。过目为授权前置条件，发出前用户有最终否决点；其余四条（#1/#3/#4/#5）仍等 0.1.2 发布后同流程；一 issue 一评不追评纪律不变；措辞改动须回草稿重过目。

## 否决与约束

- 脏场景未授权绝不 `file(new,force)`；不生成命令清单交用户手跑；临时端口不常开、不用 IP:port 形式
- yank 不早于 0.1.2 上线；tag 之前一切可改、tag 之后只加不减
- T-16f 翻车预案：#1 探针翻车→D-059 豁免集退路如实降级；其余翻车→fix-forward 准则外延（pre-RC 窗口修而不带病发）；不可速修→门如实守住呈报用户
- 人工门全保留：tag/release/yank/#1~#5 评论发出均用户执行或过目授权
- 调研缺口如实记：live GUI session 跑验证批无权威标准文档（多先例归纳）；孤儿监听器断言无公开范本，需以 commandPort -query/回调计数自证；adsk-sa-2025-0008 全文 403 未读（摘要级）

## 关联

- 前置：ADR-0018（D-049 真机门——本轮是满足它的路径非放宽）、ADR-0021（T-16 spec）、ADR-0022（回应策略+时序——本轮激活其执行面）
- 审计残留源：.scratch/t17/reports/2026-09-22-audit.md（N7/N8/O1/O2 原始件）
