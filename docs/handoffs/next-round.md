# next-round.md — rev28（T-20：README 门面返工——高难度素材 + 展示栏收拢 + PyPI 裂图修复）

生成：2026-09-24 grill 后整理环节｜Spec：ADR-0025 + docs/decision-ledger.md D-078~D-081｜前置：ADR-0024、.scratch/t19/handoffs/2026-09-23-audit-handoff.md（T-19 闭环实录+复审签字）

## 环境实况（本轮核验）

- `main`=8b546ee：v0.2.0 已发 PyPI（22 工具/asset_search+asset_import 已交付）；PR #23/#24 已合
- **PyPI 0.2.0 页面实证硬伤**：14 个 img 全相对路径=全裂图（无回改通道，只能随下版修）
- **Maya 2024 活着**：PID 13028，:7001 在听，HUD 已英文（采集窗现成，无需重启）；开着 .scratch/t19/t19-showroom.ma
- 旧 hero.png（设计横幅模板）已挖出备查：.scratch/t20/hero-old.png（2400×720 渐变底+logo 字标+tagline+视口槽）
- 素材清单现状：.github/assets/ 9 件实拍（hero/shot×2/orbit/row×5/social）+品牌层 SVG 不动
- assets-src 管线在：.github/assets-src/scene_build.py+capture.py+probe_shaders.py（上轮产物，可增量）

## 任务清单

### T-20a — 高难度场景构建（D-079；前置=脏场景守卫通过）

agent 经本 MCP 工具实况迭代建造（execute_code 驱动，看截图调构图），各题材独立小场景、同一 Maya session 内切换：

1. **钟表机芯剖面**（主打）：真渐开线齿轮系（参数化齿形公式，禁假齿——啮合须成立）+层叠夹板+螺旋游丝（螺旋曲线）+螺丝阵列+日内瓦纹；微距构图+DoF
2. **L-system 树/盆景**：参数化递归分枝+叶片实例；**明示 low-poly 为风格选择**
3. **PH 导入+装配组合景**：asset_search→asset_import 挑重型资产（雕塑/载具类，数万面 PBR）+execute_code 布光/摆放/布景——「资产给质感、装配给叙事」
4. **low-poly 城市块**：模块建筑+自发光窗阵（VP2 无 GI 故走低密度风格化不走写实夜景）
5. **Utah 茶壶**：留任——随新 session 重拍（沿用 t19-showroom 内已有茶壶或独立小景重摆）
6. **audit 布景**：搭违规场景→scene_review 检出→修复 的 before/after 双帧素材

铁律：禁原始体堆叠观感（D-071⑦ 延续为本轮验收门槛）；GRP_/GEO_/MAT_/CAM_/LGT_ 命名与 ≤4 层级纪律不破；zone 分区用材质/色温暗示禁线框描边。

### T-20b — 冻结采集 session 出片（D-078/D-080；前置=T-20a 场景定稿）

- 一个冻结环境一个 session 一次出齐（同 VP2 设置/同灯光/同 HUD 状态/英文 UI 已在）：
  - **hero 槽素材**=带 HUD 的视口实拍（scene_viewport_snapshot；视口框装真视口）
  - **6 行例表图**：机芯微距 / 盆景 / PH 装配 / 街区 / 茶壶 / audit before+after 双帧
  - **orbit.gif**：通栏收尾用，5-15s，**<10MB**；环绕对象=最有信息量场景（建议机芯或 PH 装配景）
  - **social-preview.png**：随 hero 重合成（1280×640/<1MB/实底）
- 密度红线：单图 <500KB；视觉模块 ≤4
- 补拍仅作缺陷返工路径；跨 session 素材禁混
- **验收门**：全套贴图呈报用户过目签字才入库（人工门，沿用 D-077④）

### T-20c — README 版面手术（D-078/D-080；可与 T-20a/b 部分并行——结构先行、嵌图等素材）

1. 顶部恢复设计横幅：hero.svg 模板重合成 hero.png——视口槽嵌新 HUD 实拍；social-preview 同步
2. 单一展示栏=`| Prompt | Result |` 表 6 行（左文右图）+orbit.gif 通栏居中收尾；正文其余位置零实拍图
3. **资产引用全改绝对 URL**：`https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/...`（main 钉，禁 tag 钉禁相对路径）
4. 旧素材退役：row1-showroom/row3-camera/shot-alt 删；shot-hero 退役或留 docs/（hero 槽用新拍）；row2-teapot 文件随重拍替换
5. SVG 品牌层清欠：「20 tools」→22 文案刷新
6. README.zh-CN.md 镜像同步（头注 commit hash 锚更新）+CI 标题骨架校验须过
7. 能力矩阵/对比表若因展示栏重构受影响则同步（传播矩阵纪律）

### T-20d — 门禁+收口+家务（D-080⑤/D-081）

- 门禁：pytest/ruff 预算/mypy 基线/pre-commit/README 骨架校验全绿；**发版前 twine check**（若有发版）
- 版本归置：**不发专版**——PyPI 裂图随下一次真实发版顺带修；仅当用户判紧急才授权 0.2.0.post1
- 家务落地：issue #2（自家 tracker）更新「0.2.0 已交付 models 切片，HDRI/贴图留 roadmap」；CHANGELOG 记门面返工+PyPI 修复（[Unreleased] 段或随下版）
- assets-src 结晶：新场景构建脚本+采集脚本更新入 .github/assets-src/（复现 README 同步记题材/参数）

### 人工门（用户执行，agent 备单）

素材过目签字（入库前置）→0.2.0.post1 紧急度裁决（默认不发）→（若发）tag/release 动作

## 顺延队列（原主不动）

N4 smell 债 / T-06 dormant 引擎 / T-07 注册表 / 依赖锁定 / coverage patch 门 / macOS 冒烟 / Arnold 可选项 / T-19 顺延批（async 阻塞下载/双次哈希/_ensure 三份复制/首 SG 位移线/_ASSET_TYPE_RE 收紧/zh 历史地址注/2 码入清单/新 callform 入账/assets-src 上轮残留）——排序裁归下一轮

## 铁律

- dogfood 不破：全部素材产品工具链实拍，禁 mock/生成图/手工摆拍；脏场景守卫探针先行
- 精确性替代艺术性：纯脚本只做几何逻辑清晰题材；E 类（角色/生物）禁纯脚本
- 素材未过目不入库；一次 session 出齐；单图 <500KB、orbit <10MB、视觉模块 ≤4
- PyPI 资产引用一律绝对 URL（main 钉）；禁 video/js/iframe
- VC 全走 but；grill/实现分离

## suggested skills

- `$implement` — T-20a 场景构建（MCP 驱动）/T-20c README 手术
- `$but` — 全部 VC 写操作
- `$handoff` — 翻页
- `$atomcode-research` — 争议调研（串行单发）
- `$domain-modeling` — 术语增量入 CONTEXT.md 时
