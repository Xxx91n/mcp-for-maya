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
