# 审美引擎单一真源：aesthetic_engine.py 注入 Maya

双实现已漂移（standalone 引擎 classify_light_type 返回 unclassified，而 compute_lighting_quality_score 用 other 键 → KeyError）。决定：aesthetic_engine.py（纯 Python）为唯一真源，经 write_module 注入 Maya；_mcp_scene 审美函数改为 采集场景数据 → 调用注入引擎 → 格式化输出，并对齐 analyze_aesthetics 与 scene_review 的采集字段契约。

Status: accepted (2026-09-16)

> **Status note (2026-09-18, T-11):** 本决定尚未兑现（as of 0.1.0）—— aesthetic_engine.py 仍为零生产引用的休眠代码（dormant），Maya 端内联 _score_* 实现是现役实现。引擎注入的归置决策推迟至 T-06（届时自由选“修复注入”或“从内联版抽取重写”）；休眠期内引擎仅是素材、非承诺。详见 ADR-0016 与 docs/decision-ledger.md D-038。
>
> **Errata (2026-09-27, T-27b / D-124):** 本决定“生产逻辑只能靠 stub 间接测”的前提在九轮后被证伪——`tests/test_maya_scene_module.py` 经 stub 直接覆盖内联 `_score_*` 生产路径，且休眠引擎自身的 58 条测试九轮内未抓住过一次生产回归（休眠=零生产引用）。原否决项「删引擎留内联」即当前采纳形态：本记录不撤回（ADR 不改判只标注），但其 Consequences 第 1 条「引擎直接进 CI 测生产代码」从未兑现、现确认不兑现。
>
> **Status note (2026-09-27, T-27b / D-124):** `aesthetic_engine.py` 与 `tests/test_aesthetic_engine.py` 已于 0.4.0 开发面随 T-27b 删除；Maya 端 `maya_scene_module.py` 内联 `_score_*` 函数为唯一现役实现（单一真源以另一形态达成）。D-038 在账本标记 revised→D-124；召回路径 `git log -G aesthetic_engine`。

## Considered Options
- 删引擎留 Maya 端内联实现：否决——生产逻辑只能靠 stub 间接测。
- 双实现 + parity 测试：否决——债还在，只是加报警器。

## Consequences
- 引擎直接进 CI 测生产代码；双实现漂移问题根除。
