# Handoff — maya-mcp-grill 下一轮任务书（rev23）

> 规范路径（T-11a/D-041④）：docs/handoffs/next-round.md；账本=docs/decision-ledger.md；.scratch 仅存本地过程件。

## 本轮验收事实（非计划）

- **T-15 门面轮审计 PASS**（复审 R-1..R-5 全验收）：18 渲染件+76 源件入库——logo.svg/hero/section×5/social-preview/真截图 shot-hero+shot-alt/orbit.gif；门面三 commit（psu/e4a781d/1591b4f）**未推送未开 PR=人工门**
- **T-14a 裁决轮定稿**（D-055/D-056→ADR-0020）：五项弱点各有立案结论（补做×4+追认落纸×1）
- **基线实测（审计亲跑）**：pytest 590/10、ruff 83/83+29/29、mypy new=0、uv build 0.1.2、20 tools、audit_readme 双语 9 引用 PASS
- **幻影簿记警示（必读）**：but/git status 残留 D/R 条目=索引层假象（HEAD 树==磁盘已证）；**严禁 but discard**（会真删磁盘）；一切 VC 操作先 git ls-tree 对账
- 真机环境：Maya 2024 GUI 可用（用户开机窗口）；mayapy 本机 env-blocked；旧后端 pid 3168 仍 0.1.1
- 账本 56 条（D-001..D-056）；ADR 0001..0020；CONTEXT.md 35 术语（+非对称纯色断言）

## 真源与上下文（先读这些）

- 决策账本 docs/decision-ledger.md（D-055/D-056=本轮 spec）
- ADR docs/adr/0020-t14a-weakness-adjudication.md（裁决全录）
- T-15 审计 .scratch/facade/handoffs/audit-t15-passed.md（幻影簿记细节+返工验收表）
- tests/maya_stub/math3d.py:51（MVector 继承现场）、src/maya_mcp_server/visual_module.py:255-283（VP2 读回现场）、tests/maya_stub/signature-baseline.json+signature-allowlist.json+test_signature_baseline.py

## 工作约定（承袭）

- GitButler 专用（but；禁 git write）；幻影簿记下先 git ls-tree 对账再动手；禁 but discard
- 文件写 Node.js fs+字节校验；markdown/SVG 写入前自查 $/%/反斜杠字面量
- 每修复带回归测试；诚实档与代码档分 commit；五项裁决可分 commit 同 PR
- 人工门：tag/release/yank/social 上传/About/后端重启/issue 勾选/门面 PR 推送=用户执行
- atomcode 调研串行单发；ctx 缺席走 exec 直跑

## 任务链（按序）

### T-14a 实施（D-056 五项裁决）

1. **presence-baseline 更名**（①）：signature-baseline.json→presence-baseline.json；先全量 grep 消费方（test_signature_baseline.py/allowlist/docs/脚本）→git mv+引用更新+meta 补 content_type:"presence-callable"
2. **call-form 显性化**（②）：~10 API 形态断言点写进 docs/testing.md gui 档清单+test_human_verify.py 骨架条目；无视口依赖项归 mayapy 档挂账（env-blocked）
3. **visual_module 对照表**（③）：~10 cmds.* 调用×官方签名×verdict×URL×版本×日期工件（落位实现时定，建议 tests/fixture 旁或 docs/）；signature-allowlist 行改 verdict+锚链
4. **MVector 拆类**（④）：math3d.py MVector 独立成类（len==3/无 w/有叉积）；同步 MPoint↔MVector 互转构造（w 置 1.0）；翻红断言属预期逐个修
5. **VP2 flip/BGR 修复**（⑤）：visual_module.py:271-283——条件化翻转锚纯色断言实证；通道序=floatPixels()swizzle+setPixels+setRGBA(True)；gui-tier 新增非对称纯色断言 fixture（左上红块+容差带）；hasattr(MImage,convertPixelFormat) 真机实证；**核对 shot-hero/shot-alt 是否失真——是则修复后重捕**

### 打包卫生（审计新登记，轻量项）

6. **sdist 增肥**：.github/ 82 项约 2.5MB 进 sdist（wheel 干净）——裁决打包排除（tool.uv/hatch 配置或 MANIFEST 级）；R-2 语义重建免责在 spec 档补一行注脚

### 顺延队列（勿认领）

7. T-14b #7 残余：多客户端=用户环境项出 checklist；2025/2026 矩阵/mayapy env/headless fallback 挂账
8. T-14c 发布链核对：tag v0.1.2/release notes/yank 0.1.1/issue#7 评论+勾选/后端重启复测/门面 PR 推送/social 上传/About——全用户门，agent 备单核对状态
9. T-14d 登记债择题（下轮 grill 出题）

## DoD checkbox

- [ ] 五项裁决全实施且各带对应回归/工件（①引用全更新②清单落纸③表入库④拆类+互转⑤条件化+非对称断言）
- [ ] VP2 修复经非对称纯色断言实证（未实证不宣称修好）；shot-hero/shot-alt 核对结论入库
- [ ] pytest/ruff/mypy/build/pre-commit 五门复跑全绿
- [ ] sdist 排除裁决落地+uv build 复测体积
- [ ] 发布链逐项状态核对记录（已落核销/未落列出）

## 负向清单

- grill/spec 期不动源码；⑤修复未实证不宣称；不做 convertPixelFormat 等待分支/universal swizzle/满屏纯色 fixture/精确等值断言/版本号猜朝向
- ④翻红断言是目的非副作用，不许为求绿回退拆类；②追认必须落纸（testing.md+清单）
- 更名前必全量 grep 消费方；幻影簿记期间禁 but discard
- 顺延队列各项不提前实施；人工门不代执行不催促

## 登记债（碰到再修，勿认领）

- 本轮新挂：2025/2026 VP2 行为未逐版查（碰到再修口）；hasattr(convertPixelFormat) 实证待 Maya 开机；shot 重捕依赖修复完成+Maya 会话
- 沿用前轮：presence-baseline 若未来 Maya 提供真签名内省需二次升级；PyPI yank 无先例；多客户端 blocked；Maya 2025/2026 覆盖缺；mayapy env-blocked；MVector 拆解已立项（本债消）
- 沿用 rev19.1/rev17 长尾全录不变（runtime deps lock/mypy 2.x/T-06/T-07/Poly Haven/ctx 缺陷等）

## suggested skills

- $implement / $tdd — T-14a 五项实施驱动（④⑤ 走 tdd 回归钉）
- $but（GitButler）— 全部版本控制写操作（幻影簿记期先 git ls-tree 对账）
- $atomcode-research — 争议点调研（串行单发）
- $handoff — 下轮翻页；domain-modeling / neat-freak — CONTEXT/ADR 维护

[^r2-skill-names]: R-2 注脚（语义重建免责）：本档所列技能名/技能路径系复原——原始字面量在壳层被吞后不可考，返工方当时仅口头披露。名称语义保真，但路径字面量以 `~/.agents/skills/` 现状为准。（T-15 审计新发现#2，T-14a 落纸）
