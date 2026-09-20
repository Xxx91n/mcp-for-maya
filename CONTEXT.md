# Maya MCP Server — Domain Context

让 LLM Agent（Codex/Claude 类）通过 MCP 工具直接操控 Autodesk Maya 的项目；核心抽象是给 Agent 空间感知 + 工程级验证回路，而非通用遥控器。

## Language

### 工作流

**ICEV**:
Inspect → Compute → Execute → Verify 四步强制工作流：任何场景修改必须先快照感知、再计算、执行、然后验证。
_Avoid_: 盲改

**视觉闭环 (Visual Loop)**:
把视口/渲染图像回传给多模态 Agent 的验证手段；两个工具：scene_viewport_snapshot（高频便宜）与 scene_render_preview（低分辨按需）。headless 会话无视口，工具须返回显式能力错误。
_Avoid_: 截图工具（过泛）

### 场景认知

**场景快照 (scene_snapshot)**:
一次批量查询返回的全场景空间状态（名字/类型/位置/BBox/父子），是 Agent 场景心智模型的来源。
_Avoid_: 场景信息 dump

**CoS (Chain-of-Symbol)**:
场景数据的紧凑记号化输出格式，用于压缩 token。

**Zone**:
按命名规则映射的功能分区，内置九组：GRP_shell / GRP_entrance / GRP_display / GRP_ip_core / GRP_furniture / GRP_lighting / GRP_path / GRP_decor / GRP_service。
_Avoid_: 区域、层

**命名约定**:
生产命名前缀——GRP_ 组、GEO_ 几何、MAT_ 材质、CAM_ 相机、LGT_ 灯（带角色 key/fill/rim/accent）、LOC_ 定位器；禁用 Maya 默认名（pCube1、group1 等）。

### 验证与事务

**审核 (scene_review)**:
确定性场景审计；每个检查是自注册 validator（携带 name/severity/family/order 元数据），单条异常记 check_error 不中断整轮。
_Avoid_: 评分脚本

**自定义 validator**:
经注册 API（register(name, fn, severity, family)）注入的自定义检查；口径=受信 agent 的扩展机制，非插件生态。
_Avoid_: 插件、沙箱

**checkpoint（真快照）**:
对导出时刻内存态的自包含序列化快照（exportAll，references 默认展平），落 checkpoints/ 目录；不含 undo 历史。
_Avoid_: 文件备份、存档

**rollback**:
打开快照文件并显式重建场景身份；不变式——任何覆盖路径名操作之前，被覆盖内容必须已有内存态快照；返回值显式携带场景身份信息。
_Avoid_: 恢复

**ad-hoc 快照**:
untitled（未保存）场景经显式 name 参数产出的标记性快照；不参与 S2 回滚语义——rollback 打开后停留快照路径（S1），返回 scene_rebound_to=null、original_file_status="no_original_file"。untitled 场景不带 name 的 checkpoint 调用默认报错。 快照落 <Maya workspace>/checkpoints/。
_Avoid_: 无名场景快照

### 连接与注入

**引导通道 (bootstrap channel)**:
commandPort（默认 :7001），仅用于发现会话与注入 helper，不承载工作流量。
_Avoid_: 主通道

**工作通道 (working channel)**:
bootstrap 后创建的专用通道；默认=自研 Qt TCP server（多客户端、长度前缀分帧）；headless（mayapy 无 Qt 事件循环）回退到 native commandPort。

**temp-file 注入**:
大模块落盘临时文件再由 Maya 读取的注入方式；GUI 会话上随分帧协议移除，headless 回退保留。

**薄集成 (thin integration)**:
资产生态接入策略——只接低成本外部源（首片 Poly Haven，免费 CC0 API），挂到 scene_plan 做 zone 语义 + bbox 尺寸推荐；不做自建资产库/爬虫。
_Avoid_: 资产市场

### 安全姿态

**受信方**:
威胁模型中信任的对象 = MCP client/agent；防线不承诺遏制恶意 client。
_Avoid_: 沙箱内执行

**安全网 (safety net)**:
pattern 扫描/限流/校验等防误操作机制；与安全边界严格区分——文档禁用 sandbox/secure 字样描述它们。
_Avoid_: 沙箱、安全边界

**审计日志 (audit log)**:
每次工具调用一行结构化 JSON 的独立记录流（JSONL 文件），与应用日志分流；outcome 含 rejected——被管线拒绝的调用是探测攻击的第一信号。审计是观测面不是边界：审计写失败不阻断工具执行。
_Avoid_: 流水日志

**标记块 (marker block)**:
向共享的用户启动文件（userSetup.py）做幂等合并写入的单元——`# >>> mcp-for-maya >>>` … `# <<< mcp-for-maya <<<` 包裹；不存在则建、有块则原位替换、不可解析则拒绝；不提供整文件覆写参数，写入前留时间戳备份。
_Avoid_: 覆写安装

### 工程词汇

**绞杀者 (strangler)**:
大模块改造方式——先建 stub 测试脚手架，修复带回归测试落地，拆分随修复触及区域增量进行。
_Avoid_: 大爆炸重构

**stub 层**:
CI 上替代 maya.cmds/OpenMaya 的自建假实现；数学语义必须正确（尤其 8 角点世界 bbox），否则假绿。定位=契约测试层——验证代码与 maya.cmds 契约的往返逻辑（edit 真改状态、query 读回同值），像素/行为正确性归 mayapy 档；GUI 面（panel/modelPanel/playblast/OpenMayaUI）以 stateful-fake 扩展，禁像素断言；lookThru 仅作 stub 保真保留（生产已于 T-11/D-039 退场）。

**mayapy 档**:
可选的真机 Maya 测试层，本地手动跑，文档化，不卡 CI。与 stub 层不同 pytest 调用（禁混跑）。

**净零副作用 (net-zero side effect)**:
工具执行中可瞬时改变宿主状态（视口相机/时间线），但必须 try/finally 恢复，使成功与失败路径的终态==入前快照；readOnlyHint:true 的声称以此为成立前提，瞬时改变须在工具描述中披露。
_Avoid_: 就地改动

**文档传播矩阵 (propagation matrix)**:
文档同步边界规则——commit 只修"本次变更使其失真"的文档行（触碰的工具数/清单/instructions/架构表）；与变更无关的既有错误不顺手修（sweep 反模式），但须在 PR 描述中列出交文档任务。

**双层错误契约**:
工具错误的两个正交通道——宿主侧失败（校验/限流/连接/管线拒绝）经 MCP isError 上报；Maya 侧域结果经统一 `{error:{code,message,suggestion?}}` 对象返回。区分“调用失败”与“调用成功但域内未过”。
_Avoid_: 全量信封

**三层命名**:
Python 包的三个独立命名面——dist 名（PyPI 货架标签，本项目=mcp-for-maya）、import 名（代码地名，=maya_mcp_server 不动）、script 名（uvx 命令入口，=mcp-for-maya，旧名仅作兼容 alias）。dist 与 import 分叉是 PyPA 认可的惯例，fork 是其常见成因。
_Avoid_: 包名（歧义）

**人工确认门**:
一次性高副作用公开动作的人工批准边界——repo 改名、push main、建 tag、建 Release、PyPI 发布、改 secret 须经用户执行或逐条批准；agent 仅备命令清单与影响面列表。低风险可逆动作（文件/分支/issues/PR）agent 自主。
_Avoid_: 自动发布

**冻结预算 (frozen budget)**:

存量 lint/类型错误以计数预算文件入库冻结、只降不升的 ratchet 纪律——CI 计数>预算即 fail；预算下调须经 PR 同 commit 改文件并写明理由，CI 内禁止自动写预算；粒度按目录分段（src/tests），per-rule 为完整质量门升级项。
_Avoid_: 全绿门槛、noqa 打标基线

**休眠代码 (dormant code)**:
有明确排期复用决策（如 T-06）而保留、但当前零生产引用的代码；必须机器可见标注（AGENTS.md 联动表+预算/配置说明），docstring 装饰不算数。区别于死代码（无复用计划应删除，git 历史即期权）与负债代码（在被引用的生产路径上）。休眠代码的测试计为 dormant 覆盖，不得虚增“已验证”叙事。
_Avoid_: 仅口头休眠、无锚点标注、把 dormant 测试算进生产覆盖率叙事

**棘爪 (ratchet pawl)**:
冻结预算之外的防侵蚀单向机制——预算只降不升之外还须堵“抑制项只增不减”的侧门：mypy 落地为 warn_unused_ignores+warn_unused_configs（不再必要的 ignore/override 立即显形）、lint 落地为 noqa 审计与预算下调须同 commit 说明；无棘爪的 ratchet 会因抑制面静默膨胀而失效。
_Avoid_: 只设预算不设棘爪

**human_verify 骨架测试**:
人眼验收项的版本化形态——pytest 中 test 函数存在、标 human_verify marker、body 只打印待人工确认步骤而不写 assert；使 GUI 真机清单（截图方向/渲染正确性等脆弱断言面）进版本库可复跑，又不制造假红假绿。与 gui marker（机器可断项真断言）同属 manual-tier 层，按 RC 节奏跑不卡 CI。
_Avoid_: 把脆弱 GUI 断言硬写成 assert、清单散落仓库外

**签名基线 (signature baseline)**:
mayapy 真机内 inspect.signature 采集项目实际 cmds.* 调用面产出的 JSON 清单+allowlist，与 stub 声明自动 diff 作合约护栏；对齐 mypy stubtest 先例的 stub↔runtime 漂移检测，属冻结预算同构的 ratchet 资产——Maya 版本升级时重采集比对。签名只覆盖参数形状，时序/副作用/返回值语义归 call-form smoke 补。
_Avoid_: 全人工逐条对文档、把签名等价当行为等价
