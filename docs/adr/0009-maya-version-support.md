# 支持范围：Maya 2024+（Python 3.10+）

官方支持 Maya 2024/2025/2026（Maya 内置 Python ≥3.10），与宿主 requires-python>=3.10 对齐；2023 及以下不阻止不担保，README 如实声明。

Status: accepted (2026-09-16)

> **Status note (2026-09-22, T-17/N2):** 部分被 ADR-0021 取代（superseded in part）——D-060① dual-runtime floor 裁决使注入端 floor 实际提升为 Maya>=2023（Py>=3.9，ast.unparse 可用边界）：≤2022 现由 helper 双层守卫 RuntimeError 拒载而非“不阻止”；本 ADR 的“不阻止不担保”语义仅对 Maya 2023（Py3.9）仍成立，2024+ 官方支持面与“不为 EOL 运行时写兼容 shim”不变。

## Considered Options
- 宽支持到 2022（py3.7）：否决——注入代码须降级到 py3.7 兼容，砍表达能力换覆盖面，收益不对等。
- 不声明范围：否决——发布后会被版本 issue 打脸。

## Consequences
- 注入侧代码（_mcp_scene、aesthetic_engine）可用 py3.10 语法；stub 层只需模拟一套 API 面。
