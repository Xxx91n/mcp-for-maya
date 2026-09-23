# ADR-0024 — README 门面升级与 Poly Haven 资产导入（T-19 spec 簇）

状态：accepted（grill 定稿）
日期：2026-09-23
决策来源：D-071（范围+素材路径+建模硬约束）、D-072（英文默认化）、D-073（场景设计+复刻需求）、D-074（双轨复刻+导入功能）、D-075（导入设计边界）、D-076（例表+重拍清单）、D-077（执行序列+采集窗）

## 背景

T-18 全闭环：v0.1.2 已发 PyPI、0.1.0/0.1.1 已 yank、上游 6 条评论全发、主干顶 0d0f242。用户提出 README 两痛点：默认语言应为英文；演示素材（torus/cube/cone 原始体+平光+灰底+中文 HUD）简陋，须达 blender-mcp 式作品级。四轮 atomcode 调研修正了关键认知：blender-mcp README 本体无作品级图阵——"牛逼感"来自场景内容丰富度+外部生态（gallery/视频），其爆款场景大量依赖 AI 生成资产与 Poly Haven 拉取而非纯脚本。

## D-071：范围与素材路径

本轮=README 双题（语言换位+素材升级）。素材=**VP2 艺术化重拍**主线——不换渲染器换内容：主题化场景+三点光/阴影/AO+考究机位；新增 prompt→结果例表叙事单元；hero 无 HUD 重拍、shot 保留 HUD（海报/证据分层）；orbit.gif 形态保留；**Arnold 静帧降级为后续可选项（届时走账本裁决）**。**用户增补硬约束：禁"原始几何体堆叠"观感——模型须含复杂多边形造型与曲线元素。**

## D-072：英文默认化（调研高置信惯例）

README.md=英文=唯一 source-of-truth；中文退居 README.zh-CN.md（BCP 47）；README_en.md 删除不留 stub；顶部语言选择器置于一切内容前（当前语言加粗不链接）；英文权威/中文=便利性镜像（zh 文件头 HTML 注释锚英文版 commit hash）；CI 挂标题骨架校验（EN↔zh 标题序列一一对应）入 lint job；pyproject readme 字段不动（构建时快照→PyPI 页下次发版自动转英）；AGENTS.md 联动表 6 处引用更新。

## D-073：场景设计（C 混合）+ 复刻需求

机械虹膜雕塑（revolve 机壳+光圈叶片阵列+透镜玻璃+曲线线缆——logo"眼睛+RGB 三轴"实体化）为主展品置于展厅环境（地台/射灯阵/围栏/zone 分区以材质与灯光色温暗示，**禁线框彩色描边**）；双构图=hero 中景雕塑特写+orbit 环绕展现空间层次；工艺=VP2 全开 SSAO/MSAA/DoF/depth-map 软阴影/暗色自定义背景+相机父级约束 rim 光（治 orbit 显空）+前中后三层+对比度集中 focal point。**用户新增：找到既有 3D 资产/作品由本 MCP 在 Maya 内复刻——"AI 经 MCP 复刻知名 3D 资产"为爆款叙事单元。**

## D-074：双轨复刻制

①脚本复刻轨：Utah 茶壶（CG 圣物、公版、bezier patch 公开数据可得）作展厅第二展品；②资产导入轨：实现真实资产导入能力（Poly Haven CC0，issue #2 roadmap 提前），prompt 例表获"Find a CC0 asset and import it"爆款行。**范围扩张知情记录**：本轮由纯文档轮升级为"门面+新功能"合并轮——用户明示爆款优先级高于轻量轮。

## D-075：资产导入设计边界（调研修正版）

- **两工具拆分**：asset_search={readOnly+idempotent+openWorld:true, destructive:false}；asset_import={readOnly:false, destructive:false, openWorld:true}；idempotentHint 仅当同名去重实现才可标；scene_plan 推荐位保留为子集（D-003 原形态扩面非改向）
- **首片仅 models**（FBX+纹理包，默认 1k 档）；textures/HDRI 延后（VP2 不吃 IBL，HDRI=Arnold 域）
- **宿主侧下载+Maya 导本地**（Maya 零网络面）；下载返回 validated asset_descriptor（本地路径+源 URL+CC0 license+依赖路径，参 dcc-asset-polyhaven）
- **安全骨架**：域名白名单 api.polyhaven.com+dl.polyhaven.com 仅 https+必填 User-Agent+尺寸/超时/polycount>100k 默认拒（可覆盖+审计披露）+缓存目录 platformdirs+文件名 sanitize+fbxmaya.mll 幂等检查+审计记 URL/size/files_hash/source:cache+CC0 透出
- **主工程量=纹理接线**：PH FBX 不内嵌纹理，按命名约定（diffuse/rough/nor_gl）自动建 file 节点、normal 过 normalMap；unit=meters 显式（防 scale×100）+dimensions sanity check+坏 FBX 容错（PH 部分 FBX 本身有损）+搜索限 20 条保 total_count
- **降级**：无网显式报 network_unavailable 域错（非 isError），禁静默喂陈旧缓存；cache 命中审计标 source:cache
- **版本**：合并产出 0.2.0（feature→minor bump）

## D-076：例表与重拍清单

prompt→结果例表 4 行定稿（| Prompt | Result | 每行内嵌实拍）：①Build a showroom displaying a mechanical iris sculpture ②Rebuild the Utah teapot and place it on a pedestal ③Find a CC0 vintage camera on Poly Haven and import it（Camera_01=光学之眼与虹膜呼应）④Audit this scene and fix violations（before/after 双帧，读作证据非作品）。**4/4 配图密度即对 blender-mcp（9 行仅 4 图全外链）的压制点**。资产全量重拍一次 session 出齐：hero.png（嵌新无 HUD）+shot-hero/shot-alt（带 HUD）+orbit.gif（5-15s）+social-preview.png（1280×640/<1MB/实底）+例表 4 图；品牌层（logo/icon/favicon/section SVG）不动。场景构建+采集脚本入 .github/assets-src/+复现 README——dogfood 宣称升级为可验证命题。

## D-077：执行序列与采集窗

①序列=功能先行（asset 工具+测试+注解+threat-model+AGENTS 联动）∥ README 结构层可并行（换位+CI 骨架校验不依赖素材）→ 素材采集等真机窗 → README 嵌图收口 → 门禁+0.2.0 备料（门面先行=截图撒谎否决，Fission「截图=发布资产须采自目标版本真实环境」）。②采集窗=Maya 以 MAYA_UI_LANGUAGE=en_US 英文 UI 启动（**系统环境变量/启动脚本，官方明确禁写 Maya.env**）+HUD 保留+一个冻结 session 一次出齐+脏场景守卫沿用。③构建=agent 经本 MCP 工具实况迭代→定稿结晶为 assets-src 可复现脚本+采集 transcript 留档。④**素材过目=发布 checklist 显式 gate，用户签字才入库**（Fission：自动采集不替代人工判断）。

## 负向清单（本簇汇总）

禁 mock/生成图（dogfood）；Arnold 本轮不做；工程债不搭车；禁版权角色与商标形象复刻；禁 Maya 侧网络；禁 action 制单工具；禁静默陈旧缓存；禁半旧半新素材混用；禁门面先行（截图须反映发布版本）；禁 Maya.env 设 UI 语言；禁 zone 线框彩色描边；素材未过目不入库；PyPI 不单独发版刷页。

## 证据薄弱处（诚实标注）

- "纯脚本零外部资产公认作品级"无直接先例——C 方案=人工设计构图补短板，须预期迭代打磨
- polycount>100k 阈值=工程判断非业界标准；scale×100 坑=中置信须真资产实测
- README 改默认语言的深链损失无量化数据（定性可接受代价）
- 品牌 logo 实体化无开源先例（类比推理）；agent 实操叙事=中置信社区归纳
