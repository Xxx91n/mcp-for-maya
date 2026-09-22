# next-round.md — rev25（T-17：T-16 落地收口 + 上游回应链）

生成：2026-09-22 grill 后整理环节｜Spec：ADR-0022 + docs/decision-ledger.md D-061~D-065｜前置：ADR-0021、.scratch/t16/handoffs/2026-09-22-handoff.md（审计 nits 清单原始件）

## 本轮裁决锚点

- D-062：立即落地 T-16+spec 分支；0.1.2 守 D-049 真机门（等 T-16f）；0.1.1 yank 随 0.1.2 同发
- D-063：上游回应=技术+署名型，一 issue 一评，发布归人工门
- D-064：分段回应（#2/#7 现在可发；#1/#3/#4/#5 等 0.1.2）+ docs/ upstream 对照表入库
- D-065：N1~N3 随落地同批修、N4 登记债、N5 归 T-16f、N6 删 2 孤儿文件

## 任务清单

### T-17a — T-16 落地 + N1~N3 同批修 + N6 孤儿删除（D-062, D-065）

1. `but land` 落 impl/t16-upstream-issues + grill/round16-upstream-issues-spec 进主干（栈序：spec 在下 impl 在上，land 一次收两支）
2. N1：client.py:590-592 _bootstrap 热更新点收 create_module 返回值，teardown warning 走 log 不静默吞（~4 行）
3. N2：ADR-0009 追加 superseded-by-0021 注记（≤2022 语义已被 floor 改变）
4. N3：AGENTS.md tests/ 清单补 2 个新测试文件（test_port_filter/test_teardown 类——以 impl 分支实际文件名为准）；adr 描述 0016→0022
5. N6：删 .github/assets-src/*.py 两个 untracked facade 孤儿（仅限此两件；zz 区 5 条 @2x R 幻影簿记严禁 discard）
6. 门禁复跑：pytest/ruff 预算/mypy 基线/pre-commit 全绿后收

### T-17b — upstream issue 对照表入库（D-064）

- docs/ 下新页（建议 docs/upstream-issue-status.md）：6 issue×我方处置×含修复版本×验证状态
- 数据源=账本+CHANGELOG 同源；#1/#4 验证状态列写「stub 审计绿，真机 T-16f 待定」不超前宣称
- README 双语加一行指针（可选，实现窗定落位）

### T-17c — #2/#7 上游回应备稿（D-063, D-064）

- 英文草稿两条（上游英文仓）：模板=根因→修法→「mcp-for-maya ≥0.1.0 已含」耐久陈述→fork 披露→回哺句
- #7 稿须注明「call-form 等传输路径加固随 0.1.2」诚实边界
- 备稿落 docs/ 或 .scratch 随实现窗定；**发布动作归用户**（或显式授权 gh）

### T-17d — #1/#3/#4/#5 回应备稿（D-063, D-064）

- 四条草稿现在可备，发布等 0.1.2 之后（届时 T-16f 已过有真机背书）
- #3 稿形态=边界声明（dual-runtime floor+显式能力错误），非修复公告
- #1 稿：若 T-16f 翻车则如实写豁免集方案，不宣称探针修好

### T-16f — 真机窗口批（顺延，Maya 开机即收）（D-056⑤, D-059, D-060, N5）

- VP2 非对称纯色断言钉 _VP2_READBACK_BOTTOM_UP+callform surface probe+currentTime 净零
- MEL commandPort `eval("1/2")` 回传形状定型（探针案生死前提；翻车→豁免集单走如实降级）
- #4 重连 teardown 活实证+hasattr(MImage,'convertPixelFormat') 复核
- 窗口一到一批全收，细节见 rev24 存档

## 顺延队列（原主不动）

- T-14c 发布链人工门：0.1.2 tag/release/0.1.1 yank/issue#7 勾选/social 上传/About——注意 0.1.0 是否同 yank 未裁决（0.1.0 同带病），发布时须呈报
- 登记债（不自动认领）：N4 五条 smell（D-065）+ T-06 dormant/T-07 注册表/依赖锁定/coverage patch 门/macOS 冒烟/mayapy env-blocked

## 铁律提醒

- 幻影簿记：zz 区 5 条 @2x R 残留严禁 discard，写操作前 git ls-tree 对账
- 对外文案纪律：#1/#4 在 T-16f 前必须带 pending-real-Maya-confirmation 措辞
- 上游回应发布=外部副作用=人工门

## suggested skills

- `$implement` / `$tdd` — T-17a 修复面
- `$but` — 落地与全部 VC 写操作
- `$handoff` — 再翻页
- `$atomcode-research` — 回应文案措辞争议时（串行单发）
- `$domain-modeling` / `$neat-freak` — 对照表与文档同步
- `$grill-with-docs` — 下轮裁决启动器
