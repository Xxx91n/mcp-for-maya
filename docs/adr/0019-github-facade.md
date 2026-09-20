# GitHub 门面轮：纯 SVG 工艺 + 眼睛×gizmo 品牌 + dogfood 证据素材 + 文本极轻双语

T-13 结案后进入 GitHub 门面完善轮（D-050：整页 README 视觉重构为主线，T-14 顺延）。环境约束：本机 1mcp 无 imagegen 工具——生图工艺不可用，反促成纯 SVG 全线裁定（几何排印派对工程工具反而更契合）。品牌核心叙事="AI 有了眼睛"，logo=几何眼睛×RGB 三轴 gizmo 融合、RGB-on-dark 配色（Maya 部落图腾级辨识度）；hero=品牌锁幅+产品自产真视口截图（dogfood 素材：用 scene_viewport_snapshot/orbit 捕获当 README 证据，blender-mcp 门面竞争的直击面）；双语走文本极轻共享资产零分叉；GIF 做 orbit 演示序列放次屏/social 位；资产标准套含 social preview（上传=人工门）。

Status: accepted (2026-09-20)

## Considered Options

- **asset-only 只做资产不动 README（D-050a-B）**：否决——门面目标=整页升级，资产与内容架构割裂收益折半。
- **门面+T-14a 裁决同轮 / T-14 优先（D-050b-B/C）**：否决——门面是自包含完整一轮；用户"额外"语义指新增主线非插队。
- **等 imagegen 环境再做 logo / 用户供 raster 混合（D-051 B/C）**：否决/未触发——生图缺席非损失：几何 SVG logo 对工程工具契合度更高、零随机可编辑；用户未提供 raster 素材。
- **M 字母×gizmo / 节点图×视口框 logo（D-052 B/C）**：否决——眼睛×三轴是"AI 有了眼睛"叙事的直接图形化，心智模型零脱节（repo-logo 黑名单红线）；B 备案为落地失败时的第二选。
- **单色工程调 / 高对比双色（D-052 b/c）**：否决——RGB gizmo 三色是 Maya 领域血统最纯的配色指纹。
- **工作流图/纯证明/三幕拼接 hero（D-053 B/C/D）**：否决——品牌锁幅+真截图一屏双收品牌位与证据位。
- **双语双变体资产（D-053 b-B）**：否决——文本极轻英文共享策略使双语零维护；SVG 内嵌中文在 GitHub 渲染链有缺字风险。
- **GIF 不做 / GIF 上首屏（D-054a-B/C 前半）**：折中采纳——orbit 序列有真动效价值（产品能力活证据）但体积/加载纪律决定放次屏或 social 位，翻车退静态。

## Consequences

- **工艺路线**（D-051）：全部视觉资产纯 SVG（logo/hero/section headers/badges/social preview）；dogfood 截图=产品自产（repo HEAD 新起服务实例采集，不动用户旧后端）；截图/GIF 属门面资产入 git（非 .scratch）。
- **品牌系统**（D-052/D-053）：logo=眼睛×gizmo+RGB-on-dark；hero=左锁幅+右视口框 mock 装裱真截图；字标英文（mcp-for-maya）；SVG 不内嵌中文。
- **资产矩阵**（D-054）：logo SVG 母本+favicon 派生+hero+真截图×2+section headers+social preview 1280×640（上传 repo settings=人工门）+orbit GIF（次屏位）+渲染源文件留档。
- **实施依赖**：Maya 活会话为 dogfood 采集前置（用户开机后执行）；repo About 元数据（description/topics）顺手刷新列 spec 项；README 双语结构重排走 readme-crafter 检查单+传播矩阵纪律。
- **证据强度说明**：logo 构图未落地前眼睛具象方案有失败风险（B 案备案）；GIF 制作链（render_motion_gif.py 依赖 ffmpeg/Pillow）可用性实现时验证；SVG 中文缺字风险为经验判断未逐字形实测。
