# 给关键 CI 找个 PR 改不了的执行来源（#250）

## 结论

现在的 CI 能发现不少接线错误，也能在整份工作流没运行时挡住合并；但它不能证明 lint、mypy 和 pytest 真跑过。要是 PR 留着 `ci`、`ruff budget gate`、`mypy baseline gate` 这三个名字，却把实际命令改成 `echo PASS`，同一份工作流里的自检也能一起被改掉。

**建议方向：由独立 GitHub App 在 PR 的代码上运行检查，并用这个 App 的专属状态作为必需检查。**检查程序和策略应由 App 一侧维护，不能从待检查 PR 里读取执行命令。这样普通 PR 改不了检查程序；有权更改分支规则、卸载 App 或绕过规则的管理员仍能改变结果，这不在防护范围内。

这只是当前最贴近个人账号仓库的可行路线，不代表 App 已有、已部署或已验收。仓库的完整保护配置 API 目前读不到；本票要求的假绿 PR 实验也没有获准推送和建 PR。因此，**独立执行来源尚未落地，端到端验收未通过**。

## 开工核对

- 本票 #250 是首次实现，没有关联的现有 PR，也没有审查评论。
- 父规格 #221 仍开放；#223、#226、#228 已完成，相关实现和 A3 记录已在本票基线中。父规格仍明确说，仓库内自检不能证明工作流本身不可被改掉。
- #250 没有前置票；依赖 #226 已在当前基线中。当前工作树开工时干净。
- **本票起始基准 SHA：**`1781296289da7ec66495c9c7d6a8438159c8ed32`。

## 2026-11-14 可访问的实测

读取对象是 `main`，SHA 与本票起始基准相同。

| 项目 | 实测 | 能说明什么 |
|---|---|---|
| 仓库 | `public`，所有者类型为 `User`，默认分支 `main` | 这是个人账号仓库，不是组织仓库。 |
| 分支 | GitHub API 的分支摘要显示 `protected: true` | 只能说明有分支保护；看不到具体规则。 |
| 当前提交的检查 | `ci`、`ruff budget gate`、`mypy baseline gate`、四个 pytest 矩阵项均成功；这些检查均由 GitHub Actions app `15368` 报告 | 这次成功运行没有独立于工作流的 lint/mypy/pytest 执行来源。见 [该提交的检查记录](https://github.com/Xxx91n/mcp-for-maya/commit/1781296289da7ec66495c9c7d6a8438159c8ed32/checks)。 |
| 仓库规则集 | `GET /repos/Xxx91n/mcp-for-maya/rules/branches/main` 返回 `[]` | 当前没有此 API 可见的仓库级规则集。 |
| 完整分支保护 | `GET /repos/Xxx91n/mcp-for-maya/branches/main/protection` 返回 HTTP 403 `Resource not accessible by integration` | **`required checks`、App 绑定、`strict`、`enforce_admins` 都无法在本次会话确认；标记 `human_verify`。**不能把旧记录当作当前读数。 |
| Actions 设置 | `GET /repos/Xxx91n/mcp-for-maya/actions/permissions` 返回同样的 HTTP 403 | 本次也无法核实仓库 Actions 权限设置。 |

父票 #228 的维护者记录（2026-11-14，历史读数，并非本次重读）曾记下 `ci`、`ruff budget gate`、`mypy baseline gate` 均绑定 Actions app `15368`，`strict: false`、`enforce_admins: false`、没有规则集。应以维护者重新读取到的设置为准。

当前可见的正常 CI 成功，不能替代负向实验。此前 #228 的 PR 实测只覆盖“必需检查缺报”和“`ci` 被跳过”，没有覆盖“保留名称、把命令换成成功空操作”。

## 两条路线对比

### 路线一：独立 GitHub App 跑检查——建议继续评估

App 收到 PR 事件后，在隔离环境里检出 PR 的确切 SHA，按 App 端固定的策略运行 ruff、mypy gate 和 pytest，再由 App 自己报告检查结果。命令、工具版本和必须满足的配置（例如严格类型检查与受检范围）都要在 PR 修改范围之外维护；不能把 PR 自带的 workflow、配置或锁文件当作可信规则。分支规则应把新的状态检查锁到该 App 的身份，而不是只锁名字。对不受信任的 PR 不能暴露密钥。旧的 Actions 工作流可以保留作快速反馈，但不应充当独立防线。

- **能挡住：**普通 PR 或代码 Agent 只改本仓库工作流、把命令换成 `echo PASS`、或删掉原工作流。只要 App 仍能接到事件、必需检查仍启用，App 就会在该 SHA 上重新执行真实检查并给出自己的结果。
- **挡不住：**有权修改保护规则、卸载/停用 App、允许绕过规则的管理员；App 自身配置或供应链被攻破；检查运行环境错误地信任 PR 中的测试配置。管理员边界必须明说。
- **当前可用性：**技术上适用于个人仓库，但本仓库当前这批检查里只看到 GitHub Actions app `15368`，没有看到独立 App 的检查结果。App 是否已安装、仓库能否提供/购买托管服务、本次 API 身份能否设置专属必需检查，均未证实。需要 owner 选择或提供一个维护的 App/服务，并确认费用、维护人和权限。

### 路线二：组织级必需工作流，从受保护的独立仓库运行

把仓库迁入组织，在独立、受保护的策略仓库维护真实检查工作流，再由组织级 ruleset 强制执行该工作流。不能只在本仓库里写一个 reusable workflow 调用：PR 仍可删除那个调用。

- **能挡住：**目标仓库里的 PR 改不了组织规则或来源仓库中的工作流；只要组织规则处于 Active 且目标分支匹配，保留本仓库三个 job 名称也不会替代组织要求的工作流。
- **挡不住：**能修改组织 ruleset、来源仓库或绕过规则的组织/企业管理员；来源工作流权限或身份配置错误；使用不支持的计划或规则目标。
- **当前可用性：当前不能直接用。**仓库属于个人账号；GitHub 文档说明“Require workflows to pass before merging”的 ruleset 配置在组织/企业层。改走此路需要先迁入组织并确认适用计划、组织管理权限和迁移影响。GitHub 文档还提醒此规则会阻止直接推送，应该只用于通过 PR 更新的目标分支。

GitHub 文档：[Ruleset 可用规则](https://docs.github.com/en/enterprise-cloud@latest/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets#require-workflows-to-pass-before-merging)；[组织级 Ruleset](https://docs.github.com/en/organizations/managing-organization-settings/creating-rulesets-for-repositories-in-your-organization)。

### 不选：继续给同一份工作流加自检

这只能检查“当前工作流看起来有没有接线”，不能构成独立执行来源。能一起改 workflow 和自检的 PR，也能一起改掉两者。#223/#226 仍有价值，继续保留；但它们不是本票要找的根防线。

## 尚未完成：一次性假绿 PR

按本票要求，这个实验必须在独立、可销毁的 PR 上进行，且不能触碰 `main`。实验应保留 `ci`、`ruff budget gate`、`mypy baseline gate` 三个状态名，让 lint、mypy、pytest 的实际步骤直接返回成功，同时在实验副本里停用会先拦住这类改动的仓库内自检。然后记录：

1. 实验提交的完整 SHA、PR URL 和每个状态检查的名称、来源 App、结果；
2. GitHub 对 PR 的实际 `mergeStateStatus` / `mergeable`，先解决评审线程等无关阻塞，不能把它们误当成检查的结果；
3. 清理前后的分支规则读数；关闭 PR 并删除临时分支，确认没有改动 `main` 或保护设置。

**本次没有执行。**当前会话不允许未经明确授权推送或创建 PR；已有成功运行和静态阅读都不能代替这个实验。不要据此宣称“假绿已被挡住”。

## Owner 下一步

1. 用有仓库管理权限的身份重新读取并保存当前保护设置：
   - `gh api repos/Xxx91n/mcp-for-maya/branches/main/protection`
   - `gh api repos/Xxx91n/mcp-for-maya/rules/branches/main`
   - `gh api repos/Xxx91n/mcp-for-maya/actions/permissions`
2. 选路线一或路线二。若选路线一，先确定 App/服务、执行策略的可信存放位置、费用、维护人、事件覆盖（含 merge queue，如适用）和失败时如何拒绝合并。若选路线二，先确认组织迁移和计划条件；不要仅因仓库规则集 API 返回空就假设组织级规则不存在。
3. 明确授权建立并推送一次性实验分支/PR。只在该 PR 上做假绿变更，不合并；实验前后读回规则，完成后关 PR、删分支。
4. 只有 App 或组织规则能从独立来源重新运行真实检查，且假绿实验确实被该来源判红并阻止合并，才可以把本票的端到端验收标为通过。若不能部署，记录明确阻塞项，保持父规格 #221 开放。
