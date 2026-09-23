# ADR-0025 — README 门面返工与 PyPI 图片硬伤修复（R20 spec 簇）

状态：accepted（grill 定稿）
日期：2026-09-24
决策来源：D-078（本轮范围）、D-079（高难度题材组）、D-080（展示栏+旧素材+PyPI 硬伤）、D-081（版本归置+URL 钉法+家务）
被修订：D-073（虹膜展厅题材组→新题材组）、D-075（dl.polyhaven.com→.org 域名追认）、D-076（例表行组/hero-HUD 子项）

## 背景

T-19 全栈落地、0.2.0 已发 PyPI 后，用户复审 README 判不合格：①顶部 100% 宽裸场景截图丑（原设计横幅被替换）②实拍素材散落正文五处无统一展示栏③题材不够「高难度」（虹膜=平面环、展厅=黑地板+栏杆，D-071⑦ 复杂多边形+曲线约束在观感上未兑现）④视觉区不简洁。同期实证发现硬伤：PyPI 0.2.0 页面 14 个 img 全相对路径=全裂图（PyPI 无仓库上下文）。三轮 atomcode 调研（题材矩阵/版面惯例/发版语义）修正了关键认知：纯代码建模只在「几何逻辑清晰」题材上可达作品级（精确性替代艺术性）；角色/生物题材被四源一致判翻车；docs-only 变更不该消耗 patch 号（semver #609），PEP 440 post-release 才是勘误正形。

## D-078：本轮范围

README 门面返工：①顶部恢复 T-19 前设计横幅形态（渐变底+logo 字标+tagline+视口槽内嵌新实拍，非 100% 宽裸截图——旧 hero.png 2400×720 已从 git 基线挖出作模板）②全部实拍素材收拢进单一展示栏、左右分栏排布、不散落正文③新做数个高难度题材演示资产④README 视觉区收简洁。负向：禁 mock/生成图/手工摆拍（dogfood）；素材冻结 session 一次出齐；未过目不入库。

## D-079：高难度题材组（调研修正版）

用户原倾向含 E（角色/生物），调研四源一致判翻车（拉伸球拼装是工具约束非 prompt 问题）后采纳修正：

- **主图 A=钟表机芯剖面**（execute_code 纯脚本）：真渐开线齿轮系（lkesteloot/clock gear.py、varkenvarken gears20.py 参数化先例）+层叠夹板+螺旋游丝，微距+DoF；翻车点=假齿轮不自啮合被圈内识破→须真数学
- **副图 C=L-system 树/盆景**（gpfault 教科书先例）：明示 low-poly 为风格选择回避写实落差
- **组合图 D+C**：Poly Haven 重型资产（雕塑/载具类）导入+execute_code 布光摆放布景——同构移植 blender-mcp beach demo 公式「资产给质感、装配给叙事」，兼证 asset 双工具协同
- **可选 B′=low-poly 城市块**（降密度保风格化；VP2 无 GI 夜景霓虹先天弱化故不走高密度写实）
- **E 排除**：角色/生物纯脚本必翻车；若未来要此题材仅可走 D 导入路径（归 D 类非建模展示）

## D-080：展示栏结构+旧素材处置+PyPI 硬伤

- **布局**：单一展示栏=`| Prompt | Result |` 表 6 行（左文右图即「左右分开」，每格=dogfood 证明）+orbit.gif 通栏居中收尾（GIF=整页最重资产锁窄列不减速又浪费展示面；<10MB 压缩线）；正文其余位置零截图
- **6 行**：钟表机芯微距 | L-system 盆景 | PH 导入+装配 | low-poly 街区 | Utah 茶壶（用户裁留） | audit before/after 双帧
- **hero**：设计横幅重合成，视口槽**嵌带 HUD 实拍**（视口框装真视口=最强实拍凭证；对 D-076②「hero 嵌无 HUD」的修订）；social-preview 随 hero 重合成
- **旧素材**：row1 虹膜/row3 相机/shot-alt 退役；shot-hero 形态入 hero 槽（新 session 重拍）；row2 茶壶题材留任重拍
- **密度红线**：视觉模块 ≤4（横幅+表+orbit+可选架构图）、单图 <500KB、orbit <10MB（Utrecht「don not overdo it」+巨型 GIF 拖页双源翻车实证）
- **PyPI 硬伤**：资产引用全改绝对 URL（readme_renderer 白名单=img/table 存活、video/js/iframe 全剥）；发版前 twine check

## D-081：版本归置+URL 钉法+家务

- **发版=C 为主+条件 B**：GitHub 端立即修（渲染 HEAD 零成本）；PyPI 裂图随下一次真实发版顺带修；仅当用户判紧急才发 0.2.0.post1（PEP 440 明文支持的非代码勘误形态）；**0.2.1 patch 纯 docs 变更被否**（docs-only 不消耗 patch 号）；0.2.0 已裂无回改通道（版本槽位永久占用 4+源一致）
- **URL 钉法=main 分支钉**：raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/...——GitHub 首页即时生效+PyPI 门面随 main 更新；tag 钉（spec-kit fb6df4c 先例）因 tag 存在前自裂被否；已知代价=PyPI 旧版页图随 main 漂移（对门面属特性）
- **追认**：D-075 白名单域 dl.polyhaven.com→实测 .org（T-19a 实现已按 .org 落地）
- **顺延债**：排序本轮不裁，原样挂账
- **issue #2**：实证=自家仓 roadmap tracker（Xxx91n/mcp-for-maya#2），非上游——无礼仪问题，落地时顺手更新为低风险动作

## 负向清单（本簇汇总）

禁 mock/生成图/手工摆拍；禁假齿不自啮合（须真渐开线数学）；C/B′ 类须明示 low-poly 风格声明；E 题材禁纯脚本；D 不单列成图；HUD 截图仅 hero 槽 1 张其余退役；禁 B 纯图网格（div align PyPI 剥离+窄屏错位）；禁 video/js/iframe；禁相对路径资产引用；禁为门面单独发 patch 版；禁 tag 钉 URL；素材未过目不入库；半旧半新禁混用；Maya.env 禁设 UI 语言（沿用）。

## 证据薄弱处（诚实标注）

- 无 Maya+MCP+VP2 同域先例——题材选型系 Blender 生态外推+Maya 工具链事实的类比推理，须预期迭代打磨
- VP2 金属反射 DX11/OpenGL 模式差异未核验——实机采集前先打小样
- post-release 在 uv/poetry/pdm resolver 边角行为未逐一验证（0.x 低用户基数风险极低）
- Tavily 全程超额=实际双引擎交叉（关键结论均 ≥2 独立信源兜底）
