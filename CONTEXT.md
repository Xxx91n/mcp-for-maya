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

**脏场景守卫 (dirty-scene guard)**:
对用户运行中会话执行场景变更类操作前的只读前置探针——先查 file modified 标志与场景名，命中未保存改动即停手并把处置权交回用户（存盘/授权丢弃/中止三选一），干净才放行新建场景。存在理由：脏场景上不带 force 会弹模态保存框挂死 UI 线程，带 force 则静默丢弃用户工作——两条路都致命，故唯一合宜姿势是"探针先行、人决脏场景"。
_Avoid_: 无条件 file(new,force)、在用户当前场景直跑会留残的 fixture、把场景状态当可信前提

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


**asset_descriptor**:
宿主侧资产下载与 Maya 侧导入之间的受验证交接契约——下载完成返回的结构化对象（本地首选文件路径+源 URL+CC0 license+依赖路径清单），参照 dcc-asset-polyhaven 形态；发现/下载（宿主、有网）与导入（Maya、本地文件）职责分界即以此对象为缝。
_Avoid_: 把 URL 直接递给 Maya 侧下载（Maya 零网络面）、下载与导入揉成单步无交接物

**注入模块准入判据**:
新 Maya 侧注入模块的立项门槛——三判据全满足才允许新建独立模块：①独立注入时机（D-095 语义读法：被需要的会话形态独立，非仅触发器机械独立）②独立 Maya 侧 API 面（cmds/omui 调用面与既有模块正交）③独立失败域（异常/降级语义不与他模块共享）；④目标模块健康度附则——判据不过须进既有模块时，若目标是挂号巨石则优先同注入单元独立文件而非追加本体（ADR-0027 含 D-095 修订）。域边界=注入边界=失败域粒度；文件粒度在同注入单元内可细分。
_Avoid_: 凭语义就近塞巨石（债上加债）、为表面相似拆模块（碎片化）

**同注入单元独立文件 (same-unit separate file)**:
B' 落位形态——能力归既有注入域（同一注入模块名/触发时机/失败域），但源码驻独立宿主侧文件经装配进入该注入单元；典型用于「准入判据不过但目标是挂号巨石」场景（ADR-0027 判据④，D-095 introspection 首案）。
_Avoid_: 独立文件≠独立注入模块（注入单元与失败域仍唯一）；不得借此绕开准入判据为新能力开小灶

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


**模块卸载协议 (module teardown protocol)**:
create_module 虚拟模块被 overwrite 替换前的生命周期钩子——替换 sys.modules 条目之前 getattr(旧模块,'_mcp_teardown',None) 判空调用，模块自带资源（listen socket/Qt server/线程）由归属方自释放；纪律=钩子幂等+逐项 try/except+Qt 对象 deleteLater+断信号连接非仅关 socket。importlib 语义实锤根因：sys.modules 替换不触发任何清理。
_Avoid_: 直接顶掉模块对象、调用方两步点修当长期方案、状态过继旧引用

**双语判别探针 (bilingual discriminating probe)**:
commandPort 端口类型探测的零副作用载荷形态——eval("1/2") 在 MEL（标准命令、int 除法→0）与 Python3（builtin→0.5）两侧皆合法且返回值可区分，替代会刷 syntax error 的裸 Python 探针 1+1；约束=eval 内保 int/int 操作数，MEL 侧回传形状须真机定型。commandPort 只回传返回值不回传 stdout（print 载荷无效），// 在 Python 非注释是 SyntaxError（死案留档）。
_Avoid_: print() 载荷、// 伪注释载荷、MEL python() 反向包裹（报错转嫁 Python 端口）

**端口豁免集 (port exemption set)**:
判别为非 Python 的 commandPort/第三方端口入会话级永久豁免集（端口从 LISTEN 消失才解禁）——probe minimization+指纹缓存范式，终结对同一已识别端口的周期重探；与失败冷却不同层：冷却管“疑似可成但失败”，豁免集管“已判明非我族类”。
_Avoid_: 对非 Python 端口周期重探、豁免集跨进程持久（端口复用语义不符）

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

**presence 基线 (presence baseline)**:
GUI 真机会话内 inspect.signature 尝试+dir() 采集项目实际 cmds.* 调用面产出的 JSON 清单+allowlist——cmds builtins 无 inspectable signature，契约实为 presence+方法名表，故名 presence-baseline.json（D-056①）；与 stub 声明自动 diff 作合约护栏，对齐 mypy stubtest 先例的 stub↔runtime 漂移检测，属冻结预算同构的 ratchet 资产——Maya 版本升级时重采集比对。presence 只覆盖存在性，时序/副作用/返回值语义归 call-form 清单补（证据层=docs/visual-callform-matrix.md）。
_Avoid_: 全人工逐条对文档、把 presence 等价当行为等价

**dogfood 素材**:
门面/文档证据素材由产品自身产出的纪律——README 截图与演示 GIF 用本项目视觉工具（scene_viewport_snapshot/camera_orbit 序列）真实捕获，而非生成图或手工 mock；是 show-don't-tell 的最强形态，素材即能力证明。采集走 repo HEAD 服务实例，属门面资产入 git（非 .scratch 过程件）。
_Avoid_: 生成图冒充实拍、手工摆拍截屏

**文本极轻共享资产 (text-light shared assets)**:
双语 README（zh/en）共用同一套视觉资产的纪律——logo 字标用英文名、hero 等资产文字压到最少且统一英文，两版 README 零资产分叉；动因=SVG 内嵌中文在 GitHub 渲染链有缺字风险+维护成本翻倍。
_Avoid_: 双语双变体资产、SVG 内嵌中文文案

**非对称纯色断言 (asymmetric pure-color assertion)**:
视口读回正确性的地面真值锁定法——渲染已知非对称纯色布局（如左上红块其余黑）截屏断言，同时锁定垂直朝向与 RGB/BGR 通道序；非对称是硬约束（满屏纯色锁不了"翻没翻"），色管用容差带非精确等值（OCIO 可偏移纯色）。与 stub 自验证同构：先验证测量仪器，再用仪器测东西。
_Avoid_: 版本号分支猜朝向、universal swizzle、满屏纯色 fixture、精确等值断言

**双环境包 (dual-runtime package)**:
宿主进程与注入目标解释器是两个独立运行时的包形态——requires-python 只声明宿主依赖图（Py>=3.10），注入端（Maya 内嵌 Python）须独立声明支持 floor（Maya>=2023 即 Py>=3.9）并在注入代码内做双层守卫：版本检测在前报可操作消息、能力检测（hasattr）在后防 fork/patched 解释器。声明即契约：不为已声明不支持的环境写兼容 shim。
_Avoid_: 宿主 requires-python 当注入端契约、守卫缺位让用户吃 traceback、为 EOL 运行时写兼容层

**技术+署名回应 (technical response with attribution)**:
休眠上游 issue 区的合宜发言形态——根因分析+修复路径+fork 实现指针+血缘披露+回哺意愿句，第一功能是给卡住的用户留路标、引流仅为副产品；区别于引流型（promotion-first，spam 邻域）与纯技术型（对 stranded 用户无导航价值）。纪律：一 issue 一评不追评、事实陈述非广告、发布归人工门。
_Avoid_: 宣传置顶措辞、连环追评、把回应当广告位

**耐久陈述 (durable claim)**:
对外文案中不随 yank/后续发布而失效的版本陈述写法——以「≥X.Y.Z 已含」锚定引入版本而非「最新版已修」锚定当前位；前者在旧版被 yank、新版接续后依然为真，后者随发布节奏变质为误导。回应/对照表/release notes 的版本指针一律走耐久形态。
_Avoid_: 「最新版修复」式瞬态措辞、指向即将 yank 版本的硬推

**upstream issue 对照表 (upstream issue tracking table)**:
docs/ 下公开登记上游 open issue 与本仓处置映射的表（issue×处置×版本号×验证状态）——对外回应的固定锚点+透明度叙事资产；须与决策账本/CHANGELOG 同源，任何一格失真即破坏其存在理由。
_Avoid_: 与账本漂移的二手表、缺验证状态列的过度宣称

**fix-forward（同窗修复）**:
发布冻结窗口（tag/RC 签发前）内新发现低风险高收益缺陷的处置姿势——修进待发版本而非带病发布记 known-issue；判据=修复量小、可与待发版本同过一次验证窗（机会成本为零）、且"修复版遗留同族缺陷"的披露负担大于修复成本。tag 一旦签发则切换为"只加不减"的事后语义。
_Avoid_: 无 RC 锚点却按 post-RC 严苛门槛拒修、为赶发布把已知同族缺陷带病上架

**逐版核实 (per-release verification)**:
发布面决策（yank/安全公告/弃用声明）的判定单位是单个 release 而非缺陷家族——同一缺陷在不同版本间可能被其间修复改变存在性，须对每个候选版本做实物核验（如 git show 对应 tag）再定处置，reason 写该版的具体故障模式。
_Avoid_: 凭"同族"推定批量处置、在未确认后继版本可用前先行 yank

**便利性镜像 (convenience mirror)**:
第二语言 README 的权威定位——英文 README.md 为唯一 source-of-truth，README.zh-CN.md 为镜像：zh 文件头 HTML 注释锚定英文版 commit hash 作新鲜度审计，CI 挂标题骨架校验防漂移；镜像可滞后、不许分叉。
_Avoid_: 双文件对等维护（对等必漂移）、留 README_en.md stub（双英文文件=混乱源）

**prompt→结果例表**:
README 叙事单元——| Prompt | Result | 表把用户指令与真实实拍结果配对（4-6 行甜区，每行内嵌图）；每行天然是 dogfood 证明；构图分工：建模/导入行单图、审计行 before/after 双帧读作"证据"非"作品"；门面资产保持纯美感，差异化叙事由例表承担。
_Avoid_: 无图凑数行、外链视频当主图（PyPI 不渲染）、把审计行也做成纯美图丢失差异化

**冻结采集会话 (frozen capture session)**:
门面素材的采集纪律——一个冻结环境（同 Maya 会话/同 VP2 设置/同灯光/同 HUD 状态）一个 session 一次出齐全部素材（hero/shots/orbit/social/例表图）；跨 session 补拍会产生视口风格漂移（SSAO/阴影/背景不一致），补拍仅作缺陷返工路径非常规分批；Maya 采集窗以 MAYA_UI_LANGUAGE=en_US 英文 UI 启动（系统环境变量，禁写 Maya.env）。
_Avoid_: 分批零散补拍、中文 UI 配英文默认门面、会话间设置漂移

**精确性替代艺术性 (precision-over-artistry)**:
脚本驱动 DCC 演示题材的选型准则——纯代码建模（execute_code）只在几何逻辑清晰的题材上可达作品级：钟表机芯/渐开线齿轮/模块建筑/阵列装配，精度本身就是卖点；有机角色/雕塑类必翻车（拉伸球拼装是工具约束非 prompt 问题，HN/3daistudio/BigGo/Reddit 四源收敛）。有机题材的诚实出路=Poly Haven 导入（归管线展示非建模展示）。
_Avoid_: 用脚本硬做角色生物、把密度当难度、假齿轮不自啮合

**视觉模块预算 (visual module budget)**:
README 可视区的图片密度红线——≤4 个视觉模块（合成横幅+例表实拍+orbit 通栏+可选架构图）、单图 <500KB、orbit GIF <10MB（GitHub 限制线）；依据=Utrecht「don not overdo it」官方教程+巨型 GIF 拖垮整页双源翻车实证（import-http#7/GitLab 论坛）+awesome-readme 收录案例零多图堆砌正面案例。与冻结采集会话互补：一个管拍、一个管放。
_Avoid_: 截图散落正文各处、GIF 锁进表格窄列、图片堆砌显自信


**实证反审计 (evidence-based counter-audit)**:
对外部审计指控的回应姿势——每条指控先对当前树/真机取证再表态：成立则修、证伪则驳回并留探针证据（.scratch/<slug>/probe-*.json）；对称纪律=对方驳对的指控要认（D-042 撤回先例），我方驳倒的要有机器证据不许只有口头。
_Avoid_: 凭记忆反驳、把对方指控照单全收（辩证=逐条实证）

**证据指针 (evidence pointer)**:
CHANGELOG/发布说明每条 Added/Fixed bullet 必须挂的可机检锚点——file:line 或测试 ID（D-xxx 引用已有，补齐指向可执行物证即完全体）；lint 可查形态，防「决策→文案」管线跑在「代码→对账」前面（CHANGELOG:33、manifest-based 两例病灶）。
_Avoid_: 无锚点承诺文案、先写机制名后补实现

**只加不删资产目录 (append-only asset dir)**:
.github/assets/ 等被绝对 URL（main 钉）引用的发布资产目录纪律——条目只可新增不可删除/改名；旧 PyPI 页面 description 永久指向 main 路径且不可回改，退役删除=全部历史页面永久裂图。
_Avoid_: 素材换代顺手删旧文件、改名复用槽位

**触发条件债**:
顺延债的强化形态——登记时必须附显式重开触发条件（如「下个 minor 窗口探 fastmcp 3.x 兼容面」）；ignore/defer 不带触发条件=永久失明而非债管理。
_Avoid_: ignore 规则裸挂不记债、债条目无触发条件成永久搁置

**证据型上界 (evidence-based cap)**:
依赖版本 cap 的合法形态——仅当存在已知不兼容证据或上游官方要求时才设上界（PyPA/iscinumpy 立场：cap 是例外非默认）；cap 必须挂证据指针（CI 红记录/上游迁移指南），探通收窄时在同文件注释引证据。
_Avoid_: 无证据预防性 cap、cap 悬空不引证据、上游已明令兼容范围仍放任

**探索窗 (exploration window / spike)**:
触发条件债的执行体——time-boxed 探测单元：探针清单→可弃分支→结构化报告→裁决点，产出=信息非代码（分支可弃不合并、不写迁移 PR 进主线）；成熟先例=XP spike/Renovate 按序探针。姊妹件关系：债=排程（何时探），窗=执行（探什么怎么判）。
_Avoid_: 探测分支夹带修复、报告落 docs/ 越过程件归处、无验收判据的开放式探测
