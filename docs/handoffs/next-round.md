# next-round.md — rev33（T-25：fastmcp-4.x 探索窗执行 + A′ 复用重构 + 残余债登记）

生成：2026-09-26 R25 grill 整理环节｜Spec：docs/decision-ledger.md D-096..D-100（D-096/D-089 已 revised→D-099 留痕）｜前置：D-097 契约骨架、atomcode 调研经 ctx 索引（R25-Q1 章程 / R25-Q2 契约 / R25-Q3 复用 / R25-Q4+Q4' 4.x 门 / Q5 终稿审计，ctx_search source=atomcode 可取全文）

## 环境实况（本环节核验）

- main=c1ca50d+本环节文档栈；25 工具（scene_describe/scene_nodes 已落地，issue #5 已 CLOSE）。
- fastmcp 钉 >=2.14.0,<3.0.0；**4.x 已 GA**（v4.0.0 2026-08-31「FastMCP 4 is stable」→4.0.10 十 patch；官方 archive v3 docs；requires-python>=3.10 全系成立；依赖地板 pydantic[email]>=2.12/starlette>=1.0.1/httpx2>=2.5.0/mcp>=2,<3）。
- 本仓使用面实证：FastMCP() 仅身份 kwargs；mt.ToolAnnotations 走 mcp.types(camelCase kwargs,SDK v1)；单 Middleware 子类 SecurityPipeline；stdio-only；无 elicit/sampling/roots/OAuth（结构性免疫面大）。
- Maya 未运行（mayapy 档不 import fastmcp，spike 不受 Maya 存活影响）。
- **v0.3.0 残余人工门**：tag/Release/PyPI 未执行（用户专属）。pyproject version=0.3.0；0.4.0 属预期非裁决。
- 门禁基线（T-24 审计复核值）：pytest 771/26skip、ruff src 77/77+tests 27/27、mypy new:0（基线 237）、skeleton 27、pre-commit 8/8、stdio 25 工具+ping。

## 任务清单

### T-25a — fastmcp-4.x 探索窗执行（D-097 骨架+D-099 重瞄+D-100 修订批）

**形态**：time-boxed spike——探明+报告+裁决，产出=信息非代码；分支可弃不写迁移 PR。

**执行链（序）**：

1. **静态预筛⓪**：`grep -rn 'get_tools\|get_resources\|\.meta\[.*_fastmcp\|FASTMCP_\|from mcp.types' src/ tests/`；对 mcp.types 具体 import 符号列存活清单（CallToolRequestParams/ToolAnnotations/ToolResult vs SDK v2 Removed types——D-100④ 增项）。
2. **本地 venv 初筛**：`uv venv .venv-fm4 && uv pip install 'fastmcp>=4,<5' -e '.[dev]' && pytest tests/ -q`——初筛红腿清单（ImportError 类先出）。
3. **探测分支** `probe/fastmcp-4x`：允许 commit 仅三类——①pyproject pin 改 >=4,<5（注释标 spike 非收窄）②.scratch 外报告草稿③dependabot.yml 注释同步（3.x 叙述→4.x，D-100①；本环节已预改 main 版，分支核对一致性）。不夹带修复。
4. **开 PR 触发 CI 矩阵**（非裸 push——PR 语境+4 格矩阵+可评论报告），出权威红/绿清单。
5. **结构化报告** → .scratch/t25/reports/2026-XX-XX-fastmcp4-spike.md：objective/破坏面×调用面矩阵/findings/recommendation；**账本强制落两条根因修正**：#18+#36 双红史精确断点（D-100③——camelCase 误归因同染两条；ii-agent#165 实为 2.x×新 pydantic 冲突，ⓒ 触发时勿引错向 D-100⑤）。
6. **裁决点**：全绿（CI 4 格+本地 stdio_probe 级整跑双绿）→收窄 PR：pin >=4.x,<5.0.0+注释双锚（#18/#36 修正后红史+上游 releases「minor 允许破坏」政策页）+dependabot 注释终稿；部分红→逐红项债（精确断点+修复估算+触发条件=下个 minor 窗口）；阻塞级→债登记+关窗，pin 留 2.14.x+ignore 续挡。

**探针清单**（D-097②+D-099②+D-100④ 合流）：⓪静态 grep 预筛→①#18/#36 红腿精确根因→②FastMCP() 构造 kwargs 全表对→③@mcp.tool 装饰器返回值面（v3+起返回原函数；FASTMCP_DECORATOR_MODE 过渡闸已 deprecated）→④Middleware 钩子签名 diff→⑤_fastmcp meta 键消费点→⑥stdio_probe 级整跑→⑦依赖解析面（pydantic≥2.12/Starlette≥1.0.1/httpx2）→⑧mcp.types 符号存活面→⑨同步 handler 移 worker 线程核验行（本仓钩子全 async）→⑩4.x requires-python floor 复核。3.x 已知破坏面（meta 键/装饰器/FASTMCP_DECORATOR_MODE）=参考映射非专项。

**4.x 注意点**（注记节内容）：SDK v2 camelCase→snake_case+FASTMCP_MCP_CAMELCASE_COMPAT 桥（默认开、读旧名出 DeprecationWarning）；ctx.elicit sessionless raise（本仓不用）；httpx→httpx2 异常类静默失配；背景任务入 fastmcp[tasks] extra；pydantic>=2.12 floor；fastmcp.__version__ 移除（本仓用 importlib.metadata 不受影响）；Middleware on_initialize 新协议 era 不触发（stdio+握手 era 暂免）。

### T-25b — A′ 复用重构（D-098）

- client.py 加模块级 `module_call(module,fn,*args,**kw)`+`exec_module_code(client,code)`（循 D-083 ensure_module_injected 形态不进类本体）；P0-2 安全 docstring 从 _scene_call 迁到 module_call。
- _scene_call 不留别名：scene_tools/introspect_tools 全仓直调 `module_call("_mcp_scene",...)`；_execute_scene_code 留 scene_tools 保缓存分支（exec_module_code=其无缓存核）。
- export_tools/asset_tools 删 _export_call/_exec_export/_asset_call/_exec_asset 私有拷贝调泛型；_ensure_X_injected 各域薄绑定保留。
- 补 module_call 单测（payload JSON 形状+模块名嵌入）作安全原语回归锚；现有各域测试原样通过即行为不变式。
- **翻车预案**：若某域 _exec_X 已微漂移→该域按 D-090 剧本 inline 保留不硬塞泛型。

### T-25c — 残余债触发条件登记（D-096 捎带尾）

账本/任务书登记触发条件（非实现）：hub 节点 connections 无界（触发=实测单节点 connections>500 出现）；positional cursor 不绑过滤集（触发=下个分页工作或正确性投诉）；Q3 契约正式追认（触发=首个 introspection 契约修订请求；optional）。**fastmcp-5.x 探索窗**触发条件=同构复合门（GA+沉淀/4.x 沉寂/依赖冲突，届时再立）。

### T-25d — 门禁 + 发布关联

全门禁复跑（基线上表）；收窄 PR 若成+A′ 重构→进 0.4.0 minor 车身（预期非裁决）；v0.3.0 tag/GH Release/PyPI 人工门仍挂。覆盖 D-097⑥/D-099③。

## 顺延债

原样挂账：T-07 巨石拆分（introspect_module=首批迁移单元）/issue #31（scene_plan 资产推荐）/coverage patch 门/macOS smoke/Arnold/Alembic 导出/issue #7 真机验证窗/real-Maya introspection 冒烟（用户开 Maya 后跑 tests/test_mayapy_smoke.py::_injection_unit 脚手架）。

## 铁律

- 探测分支可弃：仅三类 commit、不夹带修复、不合并进 main
- 收窄 PR=证据型上界：注释必须双锚（修正后红史+上游政策页），措辞以 spike 报告修正版为准
- grill 期不动源码；执行窗才跑探测链
- release/tag/push/GH Release 全走人工确认门

## Suggested skills

- implement / tdd（T-25a 探测链+T-25b 重构——stub/测试先行）
- atomcode-research（spike 撞未文档化破坏面时定点深挖；serial 纪律）
- gitbutler / gh（探测分支+PR 机制：but push→gh pr create→gh pr merge --merge）
- neat-freak（账本/dependabot 注释/文档同步复核）
- domain-modeling（spike 报告术语结晶时）
- handoff（下一轮收口）

## T-25 执行回写（2026-09-26）

- T-25a 裁决=**部分红非阻塞**：CI 权威面（PR #41 / run 36225673230）4 pytest 腿+mypy 红/ruff 绿；本地 stdio initialize/25 工具/ping/tools-call 全绿。#18/#36 根因修正与 R1-R3 迁移债束已落账本 D-105（触发=0.4.0 minor 窗口，更名与收窄 pin 同 PR）；探测分支 probe/fastmcp-4x 三类 commit 闭环不合并待删。spike 报告=.scratch/t25/reports/2026-09-26-fastmcp4-spike.md（gitignore 过程件）+ probe 分支 FASTMCP4-SPIKE-REPORT.md。
- T-25b 已落 impl/t25-module-call-reuse：client.py module_call+exec_module_code 收编 scene/asset/export/introspect 四域私有拷贝，P0-2 docstring 随迁，tests/test_client.py::TestModuleCall 7 测试为安全原语回归锚。
- T-25c 四项触发债已登记账本 D-101..D-104（hub connections>500 / positional cursor 下个分页或投诉 / Q3 契约首个修订请求 / 5.x 同构复合门届时再立）。

