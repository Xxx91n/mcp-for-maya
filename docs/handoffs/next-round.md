---
generated: 2026-09-30
from_round: R38（Glama TDQS 提分题面 grill 定稿 + V1-R 词义拆修闭环，覆盖 D-172~176 + D-168④ scoped revised）
ledger_head: D-176（账本 176 条 D 记录 + GC-2026-09-30 事件行；current 157 / revised 19）
branch: grill/round38-tdqs-quality（栈 pxq→wnq→pto→vup→qwx + 收口 commit；堆叠于 5bacfe8 公共基线；本地未推）
---

# 下轮任务书（rev49）

## 状态总览（R38 收口）

- **题面**：Glama TDQS = **B 3.4/5.0**（2026-09-30 06:25 UTC，across 25 tools）——Disambiguation 3/5 + Tool Count 3/5（16~25 重端带顶）+ execute_code C 2.9（min-term 放大）三处失分源。
- **已立法**：ADR-0028（要素集+单向 Boundary: 惯例+复合验收+生效面+棘爪）+ docs/adr/0028-elements.yaml（JSON-syntax YAML 单源，json.loads/yaml.safe_load 双解析）+ CONTEXT 五新词（TDQS/Boundary: 行/要素存在性棘爪/debt_owner/gate_authority）+ waiver JSON meta.vocabulary + 签认工件授权链注记 + ADR-0023 R36 块注记。
- **开放项清零**：V1-R（D-168④ 词义碰撞）已拆词闭环；R2/R3/R4 残余仍挂（见承继项）。

---

## 执行窗 A：TDQS 窄焦批（D-172/D-173/D-174）

单一 PR 收口（预估 150~350 行 diff，落 200~400 行评审甜区）：

1. **P0 三件描述重写**（要素集=ADR-0028 §2 + elements.yaml 断言件）：
   - `execute_code`（server.py）：任意代码全权限 / 不可逆 / result_type 信封 / 会话前置 —— 四必备
   - `scene_validate`（scene_tools.py）：auto_fix 二态披露（false 只读 / true 变异）/ 变异时不可逆 / 会话前置 —— 三必备
   - `write_module`（server.py）：会话前置 / overwrite-持久性语义 / vs execute_code 边界句 —— 三必备
   - 措辞终稿=执行窗产物呈用户过目（判据立法/措辞执行两分，D-174③）
2. **P1 九件消歧同批**：scene_snapshot/inspect/nodes/describe/validate/assert/review/plan/aesthetics 逐件加单向 `Boundary:` 行，点名目标=elements.yaml boundary_targets；**必须同批提交**（coherence 评审一致性，非 inputHash 硬约束）
3. **P2 annotations 校正**：scene_validate destructive 语义与 auto_fix 披露一致——annotations 错比缺更糟（contradiction=自动 1 分+旗标）
4. **联动面三面强制**：pipeline TOOL_ANNOTATIONS / server.py instructions / docs/threat-model.md（execute_code 披露双向对齐）；README 低优先（不进 TDQS 输入）
5. **禁**：虚假披露/关键词堆砌/always-call-first 句式/动工具名或 wire signature/25 件增减
6. 可选：开源 tdqs repo Appendix A/B prompt 本地预评——仅 PR 前回归参考不入 CI
覆盖 D-172/D-173/D-174；执行分支建议=exec 窗分支堆叠于 grill/round38-tdqs-quality

## 执行窗 B：要素棘爪 CI（D-175④⑥）

- 新增 `.github/scripts/check_tdqs_disclosure.py`：读 0028-elements.yaml（stdlib json.loads 即可），断言结构化要素存在（`any`=任一 regex 命中 / `all`=全部字面词命中），失败输出指明缺失要素 id
- 入 ci.yml lint job 与 check 家族并列=**hard gate**；Boundary:/P0 要素类保持 hard，个别实测误报高断言可降 warn
- elements.yaml 变更须 PR 显式 review（防改措辞顺手删断言）
- 覆盖 D-175

## 验收窗：Glama 重评核对（D-173②/D-175②）

- merge to main 后观察 Glama 页：last-scanned 时间戳 + 逐工具分 + 总分。复合判据=**≥4.0（目标 4.2 防 round1 边界）+ min 逐工具≥3.0 + 零 contradiction 旗标**
- **金丝雀校验**：首个纯描述 commit merge 后若分数不动 → Dockerfile 走 PyPI 拉包分支实锤 → 描述随下一实质变更发版后复验（不为文本单独发版）
- 达标后：账本事件行留痕 + docs/distribution-surfaces.md Glama 行同步
- 覆盖 D-173/D-175

---

## 承继项（rev48 不变）

- **叙事窗 γ**：轻叙事只描已验证面（6 Pass/5 Waived+续期治理+fastmcp 适配+本轮新增弹药=TDQS 治理实录）；重叙事仍锁（v1.0.0 门审 或 框5 像素面先到）
- **执行窗 B（债消解信号常备）**：mayapy/Linux env、框5 像素面见证、第二站 VP2、Maya 2025/2026 装机——到场即门检落新快照
- **执行窗 C（门审召集）**：当前快照 Blocked 空+Waived 全有效，召集与裁决归 user 裁量
- **观察窗**：10-05 双源观测 / 10-30 D-146 核销 / awesome PR #15382（OPEN）合并跟踪
- **审计残余**：R2 根因 probe JSON 补强（可选）/ R3 拆行配额规则下次拆行立法 / R4 顺手补

## 边界警示

- 执行窗≠grill 窗：措辞终稿归执行窗+人工过目；grill 立法的只是要素清单非措辞
- P3 工具合并禁偷渡本轮（breaking 须独立立项+semver 裁决）
- atomcode 件跨会话污染警惕（本轮剔除「ADR-0078」伪词条；正确 slug=Xxx91n/mcp-for-maya）
- 续期上限每行 2 次（框1/4/2b 均 renewals:1）；debt_owner/gate_authority 拆词已立法——下次续期 renewed_by 按三元组
- D-069 逐件过目链不变；勿 push / PR 除非用户令
- #7 关闭判据 ≡ 三态门通过；门审后豁免车道关闭

## Suggested skills

- `implement`：描述重写+消歧句+CI 脚本落地（执行窗主力）
- `but`：分支/commit 管理
- `atomcode-research`：外部生态/新题面调研（串行一次一跑）
- `domain-modeling`：新词再落
- `handoff`：再交接时任务书续写
