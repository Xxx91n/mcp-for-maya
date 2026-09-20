# Handoff — maya-mcp-grill 下一轮任务书（rev22）

> 规范路径（T-11a/D-041④）：docs/handoffs/next-round.md；账本=docs/decision-ledger.md；.scratch 仅存本地过程件。

## 本轮验收事实（非计划）

- **门面轮 spec 已立案**（D-050..D-054→ADR-0019）：整页 README 视觉重构为主线；纯 SVG 全线（本环境无 imagegen）；logo=眼睛×gizmo+RGB-on-dark；hero=品牌锁幅+真截图；双语=文本极轻英文共享资产；GIF=orbit 序列放次屏；资产标准套含 social preview
- **T-13 已结案**：PR #19/#20 合并 main（f79811b），审计返工落地，0.1.2 备单就绪（CHANGELOG/pyproject/__init__ 已 bump）；**tag/release/yank/后端重启/issue#7 评论+勾选=用户门未动**
- **基线实测（main 口径）**：pytest 590/10、gui 5/5 真机、ruff 83/83+29/29、mypy new=0、pre-commit 8/8、uv build 0.1.2
- **README 现状**：纯文本零视觉资产（无 logo/hero/截图/GIF；badge=CI+PyPI）；README_en.md 双语并存
- **真机环境**：Maya 进程本报告生成时未在跑（用户称已开，或为启动中）；dogfood 采集以 GUI 会话为前置；旧后端 pid 3168 仍 0.1.1；mayapy 本机 env-blocked
- 账本 54 条（D-001..D-054）；ADR 0001..0019；CONTEXT.md 34 术语（+dogfood 素材/文本极轻共享资产）

## 真源与上下文（先读这些）

- 决策账本 docs/decision-ledger.md（D-050..D-054=本轮 spec）
- ADR docs/adr/0019-github-facade.md（门面决策簇全录）
- 门面 skill 族 C:\Users\Administrator\.agents\skills\git\readme\（beautify-github-readme/readme-crafter/repo-logo/create-readme）
- README.md+README_en.md 现状；CONTEXT.md；docs/threat-model.md 诚实边界
- T-13 审计/实施报告 .scratch/maya-mcp-grill/reports/2026-09-20-*

## 工作约定（承袭）

- GitButler 专用（but；禁 git write）；文件写 Node.js fs+字节校验；每轮独立分支
- 诚实档与代码档分 commit；门面资产与文档变更同 PR 可但分 commit
- 写入 markdown/SVG 前自查 $/%/反斜杠字面量不被壳层吞食（rev20 教训）
- 人工门：tag/release/yank/social 上传/repo About/后端重启/issue 勾选=用户执行
- atomcode 调研串行单发；ctx 缺席走 exec 直跑

## 任务链（按序）

### T-15a 品牌资产生产（D-051/D-052）

1. **logo SVG 母本**：几何眼睛×RGB 三轴 gizmo 融合（瞳孔=三轴箭头）+RGB-on-dark；产出 1024² 母本+favicon/小尺寸派生；落地失败退回备案 B（M 字母×gizmo）
2. **hero SVG**：左=logo 锁幅+英文 tagline、右=视口框 mock（截图槽位，先占位后填真图）
3. **section headers + badge 审查**：能力矩阵分区小标；现有 CI/PyPI badge 保留+评估补充（license/python version）

### T-15b dogfood 素材采集（D-051/D-054；前置=用户 Maya 开机）

4. repo HEAD 新起服务实例（不动 pid 3168 旧后端）→ 搭演示场景 → scene_viewport_snapshot 真截图×2 + camera_orbit 多帧序列
5. orbit 序列 → GIF（render_motion_gif.py 管线，SVG 源留档；翻车退静态截图）；截图/GIF 入 .github/assets/

### T-15c README 重构（D-053）

6. README.md+README_en.md 内容架构重排（readme-crafter 检查单：一屏讲清/证据前置/最短上手路径）；hero 嵌入+截图/GIF 落位+文本极轻英文资产双语共用
7. **social preview 1280×640** 产出（上传 repo settings=人工门）
8. **repo About 元数据**刷新建议（description/topics：mcp/maya/model-context-protocol/3d 等，gh repo edit 备单=人工门）

### T-14 顺延队列（下轮，勿认领）

9. T-14a 弱点裁决 4 项（presence-baseline 名实/call-form 独立层/visual_module 对照表/MVector stub 拆解）——先 grill 后动
10. T-14b #7 残余（多客户端=用户/2025-2026 矩阵/mayapy env-blocked/headless fallback）
11. T-14c 0.1.2 发布链核对（tag/release/yank/issue#7 评论+勾选 全用户门）

## DoD checkbox

- [ ] logo SVG 母本+派生入库（构图经核验，心智模型零脱节）
- [ ] hero+截图/GIF 全资产入 .github/assets/ 且 README 双语正确引用
- [ ] README 双语重排后质量检查单过线（readme-crafter quality-checklist）
- [ ] dogfood 素材为真机实捕（非 mock）；GIF 放次屏位
- [ ] social preview+About 备单就绪（执行归用户）
- [ ] 门面变更不夹带源码/测试改动（文档传播矩阵纪律）

## 负向清单

- grill/spec 期不动源码；门面资产全纯 SVG（无 imagegen 硬约束）
- SVG 不内嵌中文；GIF 翻车退静态不硬撑；social/About 上传归用户
- dogfood 素材禁 mock/生成图冒充；采集不动用户旧后端
- T-14 各项不提前实施；0.1.2/#7 残余各归其主
- README 改动守传播矩阵（只修本变更致 stale 的行+新增视觉面）

## 登记债（碰到再修，勿认领）

- 本轮新挂：Maya 进程开机状态不稳定（dogfood 采集前置）；render_motion_gif.py 依赖（ffmpeg/Pillow）可用性未验；logo 具象眼睛方案落地风险（B 案备案）
- 沿用 rev21：presence-baseline 名实不符；PyPI yank 无先例（若已执行则消）；多客户端 blocked 待用户；Maya 2025/2026 覆盖缺；MVector(MPoint) 拆解；mayapy env-blocked
- 沿用 rev19.1/rev17 长尾全录不变（runtime deps lock/mypy 2.x 格式/T-06/T-07/Poly Haven/ctx 缺陷等）

## suggested skills

- beautify-github-readme / readme-crafter / repo-logo（.agents/skills/git/readme/）— T-15 门面实施驱动
- create-readme — README 文案纪律沿用（D-030）
- $implement / $tdd — 实施驱动
- $but（GitButler）— 全部版本控制写操作
- $atomcode-research — 争议点调研（串行单发）
- $handoff — 下轮翻页；domain-modeling / neat-freak — CONTEXT/ADR 维护
