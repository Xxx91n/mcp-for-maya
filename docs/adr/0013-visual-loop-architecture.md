# 视觉闭环架构：双工具捕获机制、注入边界与无副作用契约

scene_viewport_snapshot=M3dView.readColorBuffer 内存路径（高频 WYSIWYG），scene_render_preview=playblast 单帧（干净可选相机）；GUI-only 代码隔离在 lazy 注入的 _mcp_visual 模块；返回混合 [ImageContent, TextContent] 冻结于 v1.0；headless 双闸能力错误；save/restore 净零副作用纪律；stateful-fake 契约测试层。

Status: accepted (2026-09-17)

## Considered Options

- **统一 playblast 两工具**：否决——snapshot 失去"高频便宜"定位（playblast ~秒级+磁盘 IO），readColorBuffer 内存路径才匹配高频调用。
- **统一 readColorBuffer 两工具**：否决——preview 无法脱离当前视口指定相机/去 HUD，"render"名不副实。
- **Qt QWidget.grab()**：否决——VP2 GL surface 上 grab 可能黑图，生产实现（maya-capture/blender-mcp）无一采用；仅可作文 MImage→QImage fallback 编码器。
- **VP2/MHWRender offscreen render target**：否决——官方"正规"路径但需 MRenderOverride/C++ 插件、报告 1fps 阻塞，对 MCP 工具过度工程。
- **ogsRender+renderWindowEditor**：否决——需 Render View 更重，登记为备选不入实现面。
- **捕获代码并入 _mcp_scene 单体**：否决——绞杀者逆向生长；omui/Qt 故障爆炸半径污染全部场景工具；if-batch 散落是坏味道（tech-artists 共识：拆 batch-safe/GUI-only/common 三段）。
- **并入 maya_mcp_helper**：否决——helper 常驻=传输层污染最致命（崩即全工具失联）。
- **工具并入 scene_tools.py**：修正为独立 visual_tools.py——scene↔scene/visual↔visual 边界两侧对齐，capability 声明与错误映射正交，未来 capability（如渲染）照抄模式；注册机制已实证可组合（register_scene_tools 函数先例）。
- **裸 ImageContent 返回**：否决——blender-mcp 实证信息损失（addon 产出的 width/height/method 元数据被 handler 丢弃）；v1.0 冻结点直接定混合形状，不赌后加 block 的客户端兼容。
- **headless 静默渲染器回退（cmds.render/mayaHardware2）**：否决——输出与视口语义不同（无 HUD/光照路径不同）不加标注即误导（模型拿渲染器图当视口状态分析）；dcc-mcp-maya 生态模式=声明能力+运行时结构化错误；未来回退必须 opt-in+method 字段显式标注（blender-mcp PR #266 模式）。
- **lookThru 不还原（标 mutating）**：否决——restore 仅两行代码无理由不做；不还原伤艺术家信任且 agent 连续调用反复劫持视口。
- **独立面板（maya-capture 式）**：暂缓——为"需改一堆 viewport 选项"场景设计，v1.0 单帧预览不值（焦点抢占/泄漏/sequence-time 复杂度）；未来暴露 viewport 选项时直接换 maya-capture 库（MIT+pip，接口兼容）。
- **精确调用序列 pin**：否决——脆性固化实现细节，无害重构即红。
- **fake 层像素断言/golden-image**：否决——图像比较本质脆弱（pyddg syrupy 阈值/Playwright 连拍稳定），须真渲染才有意义。

## Consequences

- **捕获机制**（D-023，D-056⑤ 修订，T-18a 真机再修订）：snapshot=M3dView.active3dView().readColorBuffer()（VP2 必须 img.create(kFloat)→readColorBuffer(img, readRGBA=True)，否则全黑）→**RGBA 在源头经 readRGBA 旗标取得（isRGBA()=True），writeToFile 内建 float→byte 转换出 PNG——floatPixels 指针读路径整体退役（MScriptUtil 于 Maya 2024 移除，floatPixels() 实测返回裸 int 地址；2026-09-22 真机实证）**→条件化 verticalFlip（`_VP2_READBACK_BOTTOM_UP` 常量由 gui 档非对称纯色断言锚定，非版本分支）→writeToFile 临时 PNG→QImage 降采样→JPEG base64→删文件，含 HUD/选区即"agent 所见"特性，调用前 cmds.refresh(force=True)；preview=cmds.playblast(format=image/compression=png/offScreen=True/viewer=False/showOrnaments=False/widthHeight/percent=100/forceOverwrite=True/editorPanelName 显式钉面板)，相机经 modelPanel 命名参数 API 指定（T-11/D-039 起；lookThru 歧义 API 退场）。
- **修正**（2026-09-20 T-13 审计 R-1，2026-09-22 T-14a 再修正）：上条"必须 convertPixelFormat(kByte) 否则全黑"经真机证伪；"convertPixelFormat 为 2025+ API"表述亦错——atomcode 单发调研逐字核对证实其为 **C++ 专有方法，Python API 2.0 各版本（2023/2024 已逐字核验，2025-2027 成员表交叉）均无此项**，死分支已从 module 与 stub 一并删除（证据：docs/visual-callform-matrix.md #29）；MImage 自 2025 起由 maya.api.OpenMaya 移至 maya.api.OpenMayaUI，visual_module 双模块解析保留（ADR-0018/D-046 轮）。
- **注入边界**（D-024）：Maya 端 visual_module.py 注入名 _mcp_visual，lazy 注入于首次视觉调用、headless 永不注入（结构性隔离 omui/PySide import），模块内仍防御 omui import 失败；宿主侧 visual_tools.py+register_visual_tools(mcp) 与 register_scene_tools 并排；pipeline.TOOL_ANNOTATIONS 补两行（read 类）；并发首调注入竞态复用 _mcp_scene 幂等保护；工具 docstring 声明 GUI-only。
- **headless 双闸**（D-024/D-025）：宿主侧 client.framed_channel 短路预检→D-019 第一层 isError+code 前缀；Maya 侧 about(batch) OR 无 modelPanel→第二层 {error:{code:gui_session_required,message,suggestion}}；服务端必须校验产物非空（headless playblast 实证静默产空文件）。
- **返回契约**（D-025）：[ImageContent(annotations.audience=[assistant,user]), TextContent(JSON 元数据)]——snapshot 元数据={session,camera(回传面板相机名),width,height,format,bytes,panel}，preview 额外 source:"playblast"；参数 max_size=800 最长边/format jpeg|png 默认 jpeg（偏离声明：docstring 写 png recommended for wireframe/line-art review）/quality=80；preview 参数 camera=None(默认当前面板相机)/width=640/height=360，服务端向上取整 ÷4（playblast Windows 硬约束）+clamp 声明"实际尺寸以返回元数据为准"；瓶颈是 Claude Code ~25k token 图像上限非传输；structuredContent 为未来增量升级路径。
- **副作用纪律**（D-026）：_camera_switch_restored context manager（modelPanel -q -camera 读原→modelPanel -e -camera 切换→try/finally 恢复，finally 内 modelPanel -ex 存活防御，restore 失败吞掉记日志不掩盖业务错误）；_active_model_panel() 两级探测（withFocus→modelEditor 校验→activeView 兜底）；currentTime save/restore 防 playblast undo bug #21；objExists(camera) 预检；readOnly:true 以净零副作用为成立前提+docstring 六条披露（瞬时跳变不可 undo/净零副作用/时间跳变/不弹 viewer/失败语义/强杀除外）；.rnd 分支不做（GUI-only）。
- **测试分层**（D-027）：stub 扩 stateful-fake GUI 面（panel 注册表 edit 真改状态/query 读回同值、确定性 PNG playblast、新 openmayaui stub）=契约测试层，禁像素断言；钉法=终态往返断言（含异常路径）+单条宽松 restore 存在性断言；mock 仅用于难触发错误分支；真像素归 mayapy 手动层（垂直翻转方向/kFloat@2025+/真实视口内容三枚 checklist）；stub 层与手动层不同 pytest 调用。
- **文档传播矩阵**（D-027）：本 commit 修 feature 致 stale 的行（tool count→20/tool list/server.py instructions/AGENTS 结构+联动表/threat-model §5 矩阵逐行对齐 TOOL_ANNOTATIONS）；其余既有错数落 PR 描述清单交 T-09（Chromium flag-discrepancy 义务）；Diataxis：reference 允许缺失不允许失真。
- **证据强度说明**：readColorBuffer 已标 Deprecated（未移除）→捕获路径隔离为可替换单元；kFloat 路径在 2025/2026 仅 API 签名佐证无回归实测；VP2 翻转/通道序经 stub 档非对称断言钉住（红块左上容差带），真机锚定测试 `test_vp2_pure_color_orientation_and_channels` 已备、待 gui 会话实证（本机无会话——诚实挂账，未宣称通过）；dcc-mcp-maya 内部截图实现未读出（可选 pip download 审源码）；多 block 逐客户端渲染行为无官方文档→DoD 含 MCP Inspector+Claude Code+Codex 实测。
