# next-round.md — rev26（T-18：T-16f 真机验证窗 + 0.1.2 发布链激活）

生成：2026-09-22 grill 后整理环节｜Spec：ADR-0023 + docs/decision-ledger.md D-066~D-069｜前置：ADR-0022、.scratch/t17/handoffs/2026-09-22-audit-handoff.md（N7/N8/O1/O2 原始件）

## 环境实况（本轮核验）

- `origin/main`=b3f4133：T-16+T-17 全批次+dependabot mypy 合并；CI 全绿；工作区干净（zz 无变更、幻影已自清）
- **Maya 2024(24.0.0.4640) 运行中**：PID 18236，`:7001 sourceType=python` LISTENING（userSetup.py 开）——T-16f 窗口已开
- PyPI：0.1.0/0.1.1 在售未 yank；上游 6 issue 评论数=0
- 备稿在库：docs/upstream-issue-response-drafts.md（六条分区标注）；对照表 docs/upstream-issue-status.md

## 任务清单

### T-18a — T-16f 真机验证批（D-067, D-056⑤, D-058, D-059, N5）

1. **前置探针**：`execute_code` 跑 `cmds.file(q=True,modified=True)`+`file(q=True,sceneName=True)`——**脏则停手报用户三选一**（存盘/授权丢弃/中止）；干净才 `file(new=True,force=True)`
2. **MEL 对照端口**：`commandPort(":7002",query=True)` 探占用（占则换高位）→开 `sourceType="mel"`→批末 try/finally 关闭+幂等先 close 再 open；仅用 `:port` 形式；预期首次连接 "Allow" 弹窗（用户在场点过）
3. **跑批**：`pytest -m gui`（VP2 非对称纯色断言钉 _VP2_READBACK_BOTTOM_UP+BGR/RGB+callform surface probe+render_preview 净零+bootstrap framed Qt）+ MEL `eval("1/2")` 回传形状定型 + #4 create_module(overwrite) 重连 teardown 活证（commandPort -query/回调计数自证孤儿不再泄漏）+ `hasattr(MImage,'convertPixelFormat')` 复核
4. **报告**：断连时段显式标注；翻车如实——#1 探针翻车→D-059 豁免集退路；其余翻车→fix-forward（D-068 外延：pre-RC 窗口修而不带病发）；不可速修→门守住呈报用户

### T-18b — 同窗清账（D-068）

- **N7**：client.py `_bootstrap` 热更新点查 `error` 键——module_create_failed 不再吞且不误报 "module updated"（对照 write_module raise 于 client.py:766-773；~3 行+1 回归测试）
- **N8**：AGENTS.md tests/ 清单补 `test_check_ruff_budget.py`+`test_presence_baseline.py`（磁盘 23 vs 清单 21）
- **O2**：#5 备稿补 root-cause 段（docs 类 issue 的根因=README 未文档化，一句话）
- 门禁复跑：pytest/ruff 预算/mypy 基线/pre-commit 全绿

### T-18c — 发布包备制（D-068，人工门前置作业）

- **O1**：CHANGELOG `[Unreleased]` 并入 `[0.1.2]` 订正真实日期+顶部留空 Unreleased 段
- upstream-issue-status.md 验证列去 pending（按 T-18a 实测结果）；#1/#3/#4/#5 备稿去 pending 措辞
- **逐版核实**：`git show v0.1.0:...`/`v0.1.1:...` 确认各版带病面→yank reason 文案（一句话故障模式）
- 备发布包：v0.1.2 tag 说明+release notes（取 CHANGELOG 段原文）+yank 命令序列

### T-18d — #2/#7 发帖（D-069）

- 终稿贴出→**用户过目**→gh 评论发出（过目=授权前置）；不依赖 T-18a 可与并行
- 一 issue 一评；措辞改动须回草稿重过目

### 人工门（用户执行，agent 备单）

push tag v0.1.2 → release workflow → **盯 publish CI 绿+验 PyPI 页面**（invalid-publisher 前科）→ 逐版核实后 yank（附 reason）→ #1/#3/#4/#5 评论（同过目授权流程）→ 可选 v0.1.1 Release 加 yanked 标注

## 顺延队列（原主不动）

N4 五条 smell 债 / T-06 dormant 引擎归置 / T-07 注册表 / 依赖锁定 / coverage patch 门 / macOS 冒烟 / T-14b #7 残余矩阵 / social+About 门面人工项

## 铁律

- 脏场景未授权绝不 `file(new,force)`；临时端口用后即关不常开、禁 IP:port 形式
- yank 不早于 0.1.2 确认 PyPI 可用；tag 前可改 tag 后只加不减
- 一切评论发出必过用户目；幻影簿记禁 discard（虽已自清，写操作前仍 git ls-tree 对账）
- VC 全走 `but`；grill/实现分离

## suggested skills

- `$implement` / `$tdd` — T-18a/b 执行与修复面
- `$but` — 全部 VC 写操作
- `$handoff` — 窗口结束再翻页
- `$atomcode-research` — 争议调研（串行单发）
