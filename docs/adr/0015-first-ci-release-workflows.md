# 首个 CI 与发布工作流：bookend 矩阵、两段预算门与人工门机制化

首个 GitHub Actions CI=lint（ubuntu 单格跑 ruff 两段总数预算门）+test（[ubuntu,windows]×[3.10,“3.x”] bookend 四格 pytest）两 job；release.yml 同轮交付（tag v*→test→build→publish 分离+environment:pypi required reviewer）；ruff 存量走 {“src”:N,“tests”:M} 冻结预算 ratchet；mypy 整体归 T-10b；dependabot 随 SHA 固定同配；pending publisher/tag/Release/分支保护全入人工确认门。

Status: accepted (2026-09-18)

## Considered Options

- **ubuntu-only CI**：否决——平台分叉面（socket RST/FIN、进程检测、路径）已实证一个 Windows-only 测试失败；ubuntu-only 的门会对已知 bug 亮绿灯，质量门失职。
- **macOS 首版入矩阵**：暂缓——POSIX 同族无独立分叉证据（socket/进程/路径与 Linux 同族）；公共仓库分钟免费但 6→4 格更贴“最小门”；发布后按 issue 信号补，T-10b 候选。
- **全版本矩阵（3.10-3.13×OS）**：否决——bookend（floor+head）为成文惯例（endavis pyproject-template 明文“oldest+newest”），中间版本边际信号≈0；head 用 "3.x" 浮动随 CPython 年度前移（可能无码改动红一次=本职信号）。
- **skipif win32 标记 RST 失败测试**：否决——dotnet/runtime CI 政策明文 “never mute/skip/disable”；新门首日对既有失败闭眼=masking，且永远测不到 Windows 真实路径。
- **只精确映射 ConnectionResetError**：否决——漏 Windows 常见 WSAECONNABORTED（ConnectionAbortedError）；映射整族 ConnectionError（RST/Aborted/BrokenPipe/Refused）才完整（Rodola is_connection_err、asyncio streams.py 自抛 ConnectionResetError、aiohttp ClientConnectionResetError、httpx TransportError 层级一致）。
- **裸 OSError 映射**：否决——吞 EBADF/EMFILE 等本地 bug 伪装 unavailable，破坏契约可诊断性；errno 白名单（ENET*/ENOTCONN）列后续增强。
- **`--add-noqa` 打标基线**：否决——虽为 ruff core dev 当前官方推荐（#1149 仍 Open、内建 baseline 未落地），但 237 行 noqa 污染源码、行级锚定防不了“删一加一”搬家、基线不可读。
- **diff-only lint（reviewdog 类）**：否决——是 review 辅助非门禁，存量债务永不 burn down；action-setup CVE-2025-30154 投毒前科使第三方 diff action 引入须谨慎。
- **per-file 预算粒度**：否决——237 条摊碎后预算文件膨胀、无关重构频碰预算文件；粒度单位应是“计数器/规则”非文件（Canopy ADR-030）。
- **mypy 以 continue-on-error 进 T-10a 攒信号**：否决——kicad-tools 一手腐化案例（挂一年静默涨 1472 errors 被迫开 issue 去腐化）；mypy 官方立场“缩小范围跑到真绿”非“全量跑但豁免”；T-10b 第一天直接落 mypy-baseline（baseline 入 VCS+新增即红）无需过渡态。
- **release.yml 缓到发布日再写**：否决——pending publisher 官方支持包未发布前预配置（首发自动转正）；workflow 先落保证 repo/文件名/environment 字段对齐（typo=invalid-pending-publisher 最高频故障），且 build 部分可先免费演练。
- **CI 内建 GitHub Release（action-gh-release）**：否决——GITHUB_TOKEN 创建的 release 不触发下游 workflow；`gh release create --generate-notes` 人工执行更贴合“agent 备清单”人工门约定。

## Consequences

- **CI 结构**（D-033）：lint=ubuntu 单格（ruff 预算门）；test=[ubuntu-latest,windows-latest]×["3.10","3.x"] 四格 fail-fast:false；触发 push(main)+pull_request+workflow_dispatch；concurrency group+cancel-in-progress；permissions:contents:read；外部 action 全 SHA 固定附 `# vX.Y.Z` 注释；actions/setup-python+astral-sh/setup-uv(enable-cache)+`uv pip install -e ".[dev]" --system`。
- **安装路径演进**（D-112，增量非 supersede）：test/mypy/lint 与 release 工作流的安装步骤从 `uv pip install -e ".[dev]" --system` 迁至 `uv sync --frozen` + `uv run`；dev 依赖从 `[dev]` extra 迁 PEP 735 `[dependency-groups]`；`uv.lock` 入库提供 PR 面确定性；浮动解析义务移交 weekly resolution-drift canary job（cron 37 6 * * 1，`uv lock --upgrade` + `uv sync` + pytest）——红=dep 漂移实测信号（D-100④ 触发器自动成就）；`uv sync` 无 `--system` 模式（uv#9399），Windows 侧若 sync 行为异常首查 `UV_PROJECT_ENVIRONMENT`；lock 的价值=确定性与 flake 消灭，非供应链防护（yanked 版本照装属 PEP 592 规范行为，yank 防护另由 cooldown/malware-check 承担）。
- **错误契约修复**（D-034）：client.py Qt `_send_receive` 捕获链 IncompleteReadError 支扩为 `(ConnectionError, asyncio.IncompleteReadError)→MayaUnavailableError`；typed re-raise 支保持在前；修复由既有测试（test_connection_closed_raises_unavailable）由红转绿为证；OSError errno 白名单列登记债。
- **预算门**（D-035）：.github/ 下预算文件 `{"src":N,"tests":M}`（值=修复后实测）；lint job JSON 计数分段比较，>budget fail、≤通过并提示可同 PR 降预算；预算下调只能经 PR 同 commit 改文件（floor 不可漂移），CI 内禁自动写；tests/ 探测分支——--statistics 探得 auto-fixable ≥~80% 则同 PR fix-forward 清零预算只记 src；per-rule 粒度升级归 T-10b（litellm ruff-strict-budget.json 先例）；ruff 原生 baseline（#1149）落地即迁移（登记债）。
- **发布链**（D-036）：release.yml=tag v*→test needs→build→publish 分离（environment:pypi、id-token:write、pypi-publish SHA 固定、PEP740 attestation 随 v1.11+）；发布日清单——PyPI pending publisher 人工预配（repo=Xxx91n/mcp-for-maya、workflow=release.yml、environment=pypi；不预留包名被抢即失效）+environment required reviewer 人工配+tag 推送+gh release create+分支保护 gh api PUT（contexts=先跑 CI 确认的精确 check 名）+PyPI badge 补（?cacheSeconds=300）+TestPyPI 预演可选；dependabot.yml 同轮（github-actions/weekly/minor+patch 分组）。
- **badge**（D-036）：CI badge 同轮入 README 双语；PyPI version badge 发布日补（shields+CDN+Camo 缓存链防红标挂数小时，实战案例实证）。
- **证据强度说明**：OIDC 链路无 dry-run（只能真发一次验证，TestPyPI 可预演）；pending publisher 不预留包名——首真实发布即锁名窗口风险已认知（D-028 重申）；bookend 为成文惯例非强制标准；skipif=masking 论证为社区共识推断；小团队总数 vs per-rule 维护成本无量化研究（两阶段为工程判断）。
