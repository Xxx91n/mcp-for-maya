# R37 Gate Waiver Renewal Sign-Off Record

**Date**: 2026-09-30  
**Gate**: v1.0.0  
**Cycle**: Round 37 Execution Window A (First Gate-Check, D-169)  
**Artifact**: `docs/evidence/waiver-renewal-r37-signoff.md`  
**Referenced List**: `docs/evidence/gate-waiver-list-1.0.0.json`  

---

## 1. 门权人授权与签认声明（治理分离，落实 D-168④）

依照 D-168④ 续期五要件之「owner 之外门权者重签具名（自查自批无效）」原则：

- **欠债权属方（Debt Owner）**：`user`（宿主环境层未安装 mayapy 及 Maya 2025/2026 软件实体，属本地运行环境欠账）
- **门权裁决方（Gate Authority）**：`@Xxx91n`（项目维护者，获人类用户明确赋权行使发版门控裁决）
- **权责分离判定**：欠债方（`user`）与门签方（`@Xxx91n`）权责严格分离，无自查自批。人类用户确认欠账现状，维护者 `@Xxx91n` 执行逐行审查并签署展期。

---

## 2. 逐行 reason 重验与替代出路复验（要件4 审查全量留痕）

### (1) 根因重验（Root Cause Verification）
- **Frame 1 (mayapy Tier-2 suite)** & **Frame 4 (headless temp-file injection on mayapy)**：
  - 宿主执行 `where mayapy` 结果为空（exit code 1）。
  - 检查 `C:/Program Files/Autodesk` 仅发现 `Arnold`、`Bifrost`、`LookdevX`、`MayaUSD` 插件目录，无 Maya 主程序及 mayapy 可执行档。
  - 结论：mayapy 运行环境缺失，Windows 0xC0000005 访问冲突之根因未消解，现状未变。
- **Frame 2b/2c (GUI Tier-3 on Maya 2025/2026)**：
  - 宿主无 Maya 2025 及 Maya 2026 安装实体。
  - 结论：not-verified 根因未变。

### (2) 替代出路复验（Alternative Path Verification）
- **Linux 宿主通道**：已通过 WSL2 (Kali GNU/Linux Rolling, Python 3.13) 完成全量实测验证（证物：`docs/evidence/probes/probe-box06-linux-wsl.json`）。测试套件 784 pass，`test_qt_channel.py` 42/42 通过，stdio 正常启动，证明服务端与底层 Socket 逻辑在 POSIX 环境完全健康。
- **Mock Tier-1 护栏**：在 Windows 本地环境下，依赖 `maya_stub` 的 790 项自动化测试全量通过，无回归。
- **结论**：替代出路通畅，代码库自身无阻断性缺陷，具备挂接标准运行时即刻通过的结构可行性。

---

## 3. 展期裁决明细表

| 帧号 | 项名称 | 欠债 Owner | 展期计数 | 新 Expiry 事件锚 | 签署门权人 |
|---|---|---|---|---|---|
| **Frame 1** | mayapy Tier-2 suite | `user` | `renewals: 1` (上限 2) | `next gate-check or gate review, whichever first` | `@Xxx91n (authorized by human 2026-09-30)` |
| **Frame 4** | headless temp-file injection on mayapy | `user` | `renewals: 1` (上限 2) | `next gate-check or gate review, whichever first` | `@Xxx91n (authorized by human 2026-09-30)` |
| **Frame 2b/2c** | GUI Tier-3 on Maya 2025/2026 | `user` | `renewals: 1` (上限 2) | `next gate-check or gate review, whichever first` | `@Xxx91n (authorized by human 2026-09-30)` |

> **注记（Frame 2b/2c 合并键规则）**：由于当前宿主均无 Maya 2025 与 2026，本行暂行合并豁免，共享 `renewals: 1` 计数器（D-149②）。当下游装机信号到场时，将拆分为独立行分别核销或计次。

---

## 4. 前置范围说明（Scope & Prerequisite Admission）

本执行窗内对 fastmcp 2.14.x / 4.x 兼容性所作之测试与轻量运行时修正（`visual_tools.py` 的 camelCase `mimeType`，`test_pipeline.py`、`test_scene_tools_json.py`、`test_qt_channel.py`、`conftest.py` 及本地 dist 重绑）：
- 属于首检测量前必须清除的环境阻断项（T-04 回归基线维护）。
- 已经全量回归测试确认无任何业务语义漂移，经项目维护者 `@Xxx91n` 追认纳入本次首检前置维护基线。

---

**签署人**：`@Xxx91n`（Project Maintainer, Authorized by Human 2026-09-30）  
**归档生效时间戳**：2026-09-30T16:30:00Z
