# next-round.md — rev40（R30 毕：锐评三发现+平台扩张裁决已立 D-141..D-143；执行窗待开）

生成：2026-09-28 R30 整理环节｜Spec：docs/decision-ledger.md D-141..D-143｜前档：rev39（R29 发布窗全录）

## 环境实况（本环节核验 ~15:00 UTC）

- main=a8870bb（PR #50）；账本 143 行；工作区净；栈 grill/round30-critique-registry（opk→tlq→upx 三笔账本提交，未推未合）。
- v0.4.0 已发布态：tag→b977908、release.yml 36401741670 全绿、GH Release 已建非 draft（body=103 行逐字=**缺披露附录，T-30a 待补**）。
- PyPI：锐评 R6 报索引已自愈（latest=0.4.0）——**须先复核再销账 D-139**（T-30i）。
- canary 双载体在位：schtasks mcp-for-maya-drift-canary（周一 14:40 +08）+ci.yml active；下窗 2026-10-05 双源观测。
- 分支保护已开；mayapy env-broken 实锤（#7 走 GUI 通道）。

## 任务清单

### T-30a — v0.4.0 Release body 补挂披露附录（人工门） — 覆盖 D-049/D-115/D-142α

序：①`gh release view v0.3.0 --json body` 取附录结构源文→②备稿（装船时点快照语义：#7 链接+D-049/D-115 引用+mayapy env-broken 实测结论；**去计数化**；措辞过 D-132）→③**用户过目批准**→④`gh release edit v0.4.0` 就地补挂→⑤账本注记「D-138③ 所记 body 形态自此不再准确」。只动 body 不碰 CHANGELOG/tag。

suggested skills：handoff（备稿交接）、neat-freak（措辞校准核验）

### T-30b — preflight 附录断言脚本 PR — 覆盖 D-142β/D-134γ

新增 .github/scripts/check_release_appendix.py：弱断言=release body 存在披露附录节+非空+引用 #7+issue open；条件=「#7 未勾项>0 或存在未兑现声明⇒附录恒非空」不写死 0/10；附录可在 body 任意位置；fail-loud 三显式报错（gh 不可用/HTTP 非 200/rate-limit 403）；配 pytest 回归（每修必带测试）。挂发布窗 preflight 第 6 行（ADR-0023 增补块），不进 push CI。agent 自主 PR。

suggested skills：tdd（断言面先测）、domain-modeling（核对单行措辞）

### T-30c — PyPI 索引双源探针并 canary 链 — 覆盖 D-139/D-142γ/D-123

weekly drift job 增探针步：主=GET pypi.org/simple/mcp-for-maya/（Accept: application/vnd.pypi.simple.v1+json）断言含最新版本串；副=project JSON info.version==最新 tag（去 v 前缀）。双绿=健康；simple 红=安装面断（最高 severity）；simple 绿+JSON 红=API 漂移。红→D-123 notify 通道，维护窗假红人肉归因消化。

suggested skills：tdd、neat-freak（归因入账）

### T-30d — CONTRIBUTING 预算注记 — 覆盖 D-142δ

预算段加一句：「CI 按被检 commit 的 tip（=PR 终态）判定，PR 中途 commit 瞬时超预算不构成门失败语义」。机制不动（D-125 棘爪不触）。

suggested skills：—（单句文档）

### T-30e — README mcp-name 标记行+PyPI badge — 覆盖 D-143δ/D-036④

README.md+README.zh-CN.md 同步（D-072）：①HTML 注释行 `<!-- mcp-name: io.github.Xxx91n/mcp-for-maya -->`（边界规则：后跟换行/-->）；②PyPI version badge（shields.io 动态端点）。现在合 main——Registry publish 绑下次发版窗生效。

suggested skills：neat-freak（双语镜像对齐）

### T-30f — Glama 查+claim — 覆盖 D-143α

先查 glama.ai 是否已自动索引本仓（大概率是）；在列→GitHub OAuth claim（个人账号直连，免 glama.json）；不在列→Add MCP Server 提交 repo URL。**禁启用 Docker 构建面**（stdio+Maya 宿主健康检查恒红）。宣称文本过 D-132。

suggested skills：—（平台操作，含用户 OAuth 人工门）

### T-30g — awesome-mcp-servers PR — 覆盖 D-143α

punkpeye/awesome-mcp-servers 提 PR：照抄现有行格式+三 emoji（语言/范围/OS）+一句话描述（D-132 句式，beta 语气）+字母序+PR title 加 🤖🤖🤖 fast-track。可提不押时点（3000+ open PR 队列，合并非里程碑）。

suggested skills：—（外部 PR，须用户推自己 fork 或授权）

### T-30h — server.json 备稿+Registry publish（绑下次发版） — 覆盖 D-143β

agent 备稿 server.json（$schema 2025-12-11/name=io.github.Xxx91n/mcp-for-maya/registryType=pypi/identifier=mcp-for-maya/version=届时版本/transport=stdio）+`mcp-publisher validate` 离线预检；**人工门**：用户 `mcp-publisher login github`（device flow）+publish；agent 备核验 curl（registry API search）。version 须与 PyPI 精确一致；发新版需重 publish。执行窗=下次发版（0.4.1/0.5.0）后。

suggested skills：neat-freak（发布编排纪律嵌套）

### T-30i — D-139 销账复核 — 覆盖 D-139

`pip index versions mcp-for-maya`+project JSON latest 复核；若 0.4.0 在列→账本行注记「索引已自愈+时间戳」销账（锐评 R6 已报 latest=0.4.0，须独立复核确认）；不复位→用户拍板删版重传或 0.4.1 patch（D-133②）。

suggested skills：neat-freak（带时间戳销账）

## 结转挂账（非本轮新增，时点驱动）

- **2026-10-05 双窗观测**（D-127/D-137）：native cron 37 6 * * 1 是否自愈+scheduler 14:40 +08 自触发；任一/双通道出 run 记归因闭环；双双静默→incident 行+第三载体。
- **#7 十框+D-115 探针补采**（真机窗）：Maya 2024 在机，mayapy env-broken→GUI 通道；v1.0.0 硬项。
- **notify 红路径**：观测项挂起，无自然红不制造。
- **叙事传播**（D-143γ）：备稿不发，v1.0.0+#7 全绿后启用。

## 措辞红线

- 附录=装船时点快照+声明性指针，禁计数型内容、禁 tracker-dump、禁抄 v0.3.0 未校准措辞。
- Registry/Glama/awesome 描述=4-Beta 语气+能力+证据指针，禁 stable 宣称。
- D-138③ body 描述在 T-30a 后为陈旧快照，引用须带「superseded」意识。
- 账本唯一真源 docs/decision-ledger.md。
