---
generated: 2026-09-30
from_round: R34（真机验证窗 R2 执行+T-30h/a 兑现+WSL 补验+Q5' v1.0.0 门修订+0.5.0 预备封存）
ledger_head: D-163
branch: grill/round34-closeout-v1-gate（9 commits lwt→wsn，未推）
---

# 下轮任务书

## 0.5.0 发布执行窗口（显式——最优先，先跑这个）

**前置已就绪（勿重做）**：`wsn` commit 已含 pyproject/`__version__`/uv.lock→0.5.0+CHANGELOG 段；win 785 绿；wheel+sdist 构建通过。0.5.0=验证里程碑包，src 与 v0.4.1 字节同码（notes 已诚实声明）。

**执行序列**（push+对外发布为不可逆外部副作用，开跑前向用户确认一次）：
1. `but push` 本分支 → `gh pr create` → CI 绿 → 合入 main
2. merge commit 上 `git tag -a v0.5.0`（bare title，无 body 历史包袱纪律）→ `git push origin v0.5.0` → release.yml trusted-publisher 自动发 PyPI
3. `gh release edit v0.5.0`（或 release body）**必须挂 Known-unverified 附录**——#7 仍 open 故弱断言义务生效；跑 `uv run python scripts/check_release_appendix.py --skip-label-verify` 核
4. registry 重 publish：`.scratch/t30/server.json` `version`→`0.5.0` + `mcp-publisher validate` → `publish`（Windows amd64 v1.7.9 在 `.scratch/t34/tools/`，设备码新领）；验 `GET /v0/servers?q=Xxx91n` isLatest 翻转
5. `docs/distribution-surfaces.md` 官方行版本戳→0.5.0+publisher 1.7.9+Δ=isLatest 翻转
6. PyPI 复核 `uvx mcp-for-maya@0.5.0 --help` + docs/releases 版本指针更新
覆盖：D-163α①、D-143α、D-115①、D-136 时序、D-036⑤ | 建议技能：gitbutler、odl（如需再下工具）、sqlite-utils-skill（核验件）

## 帧级剩余项

- **框5 像素面补证**（conditional→升绿路径）：Maya GUI 在场时任选——Inspector web 工具面板调 `scene_render_preview` 截图 / claude TUI `--mcp-config .scratch/t34/box5/claude-mcp.json`（kimi-k3 在 TUI 道或活）→ 产物解 image block。覆盖 D-155β
- **D-146 核销窗**：registry 上线~2026-10-30 满 30d 时核 mcp.so/PulseMCP/Glama 被动同步（Glama 官方宣称分钟级、mcp.so 人工提交不查）；需同步→下一收录发布窗执行。覆盖 D-144γ+D-146
- **轻叙事轨启动**（D-163β①解锁）：构建实录贴/known-limitations postmortem 备稿——只描已验证面：win+2024 已验面全绿、playblast 视觉环实证、staging 勘误披露范式、registry 收录、WSL server 侧。禁描 waived 集为绿
- **框2 判定复核窗**：第二台 2024 站在场即插验 VP2（封闭判据 D-151②：三条件全绿→豁免→关 #53）；期间不声明已修
- **waiver 清单维护**：`docs/evidence/gate-waiver-list-1.0.0.json` 随每次 preflight 重读；waived 行消解→Pass、expiry 超期→Blocked fail-closed

## 挂账区

| 事项 | 到期/锚 |
|---|---|
| AC-06 残余：Linux 宿主 Maya 内 Qt 通道 | 过期即 fail-closed（已收窄，server 侧 784p+42/42 绿+uvx Linux 起活已证） |
| AC-01 跑本修订（D-159） | 修订窗未至 |
| mayapy 环境簇（14284 分支+签名道） | 过期即 fail-closed |
| 框5 像素面 | expiry=Codex 席实证/gate review 先到 |
| #53 VP2 | owner=用户侧授权 probe/update-core |

## 边界警示

- **不补还愿试** only on green path——waiver 里任何行到期未消解，下一轮先 fail-closed 判 Blocked 再谈别的（D-163α②）
- `execute_code` 成功空 content 契约怪癖记档（box5 claim_boundary 红线 B）；若用户报实际受影响再开 investigating
- CC Switch 代理层（deepseekpro/kimi-k3）是本地环境层堵非产品层——客户端席三因里模型道已两次实证，勿归咎 MCP server
- WSL `.venv` 共享路径会跨平台污染：本轮已重建 win venv（`.venv` 现 windows-313）；WSL 再跑 `uv sync` 会再染（隐患件，何时解都行）
- 栈顶 `wsn` 为发版预备件非越界——但勿在其上叠加更多执行件直到执行窗启动
