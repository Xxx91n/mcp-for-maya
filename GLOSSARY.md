# GLOSSARY — Maya MCP Server

术语表。每个词条写三件事：这个词、一句人话解释、`_Avoid_` 后面列出的旧词。
写文档、写注释、写报错时别再用 `_Avoid_` 里的说法。

## 工作流

**ICEV**: 先看场景、再算方案、再动手改、最后复查；四步按顺序走。
_Avoid_: 强制工作流、四步强制工作流、Inspect → Compute → Execute → Verify

**看图复查**: 把视口截图或渲染图发给 AI 看一眼，确认改得对不对；只有 GUI 会话能用。
_Avoid_: 视觉闭环、Visual Loop、回传图像、视觉验证

## 场景认知

**scene_snapshot**: 一次调用拿到场景里物体的名字、类型、位置、大小和父子关系；超大场景的默认列表会截断。
_Avoid_: 场景快照、场景心智模型、心智模型

**CoS**: 把场景数据写成很短的一行行文字，省下发给 AI 的字数。
_Avoid_: Chain-of-Symbol 记号化、token 压缩格式、CoS 格式

**Zone**: 按物体名字里的关键词分区域；`get_zone_map()` 实际认 7 组，`scene_plan` 另用 8 个名字。
_Avoid_: 九组、nine zones、9 zones、功能分区、分区

**模型推荐**: `scene_plan(recommend_assets=True)` 在规划结果里附上 Poly Haven 的模型推荐：先等 `auto_fix` 整理完成再读取各区最新尺寸，在后台线程里按 5 秒软超时、复用 300 秒模型索引缓存搜索入口、展示、家具、灯光这四个区（`shell`、`ip_core`、`path` 跳过不搜），做按词核对、去重排序，并在超时或断网时降级为 `partial`/`offline`（不断掉原本的规划）；只是参考，不下载、不导入。
_Avoid_: 智能推荐、AI 推荐、推荐引擎

**命名规则**: 物体名要用 GRP_/GEO_/MAT_/CAM_/LGT_/LOC_ 前缀，别用 pCube1、group1 这类 Maya 默认名。
_Avoid_: 命名约定、naming convention、生产命名规范

## 验证与事务

**scene_review**: 按 11 项固定规则检查整场景并给 0–100 分；内置项不能加也不能删。
_Avoid_: 确定性场景审计、deterministic audit、场景审计

**自定义检查项**: 用 `register_validator(...)` 在本次会话里加检查；分数单列在 `custom` 里，不动内置 0–100；重连后要重新加。
_Avoid_: 自定义 validator、custom validator、受信扩展机制、插件生态

**场景存档（checkpoint）**: 把当前场景导出成磁盘上的 `.ma` 文件，放在 `checkpoints/`，不含撤销历史。
_Avoid_: checkpoint（真快照）、内存快照、内存态快照、in-memory snapshot、真快照

**读档（rollback）**: 打开一个存档，并把场景重新绑回原来的文件路径。
_Avoid_: 回滚、显式重建场景身份、rebind、重绑

**临时存档**: 没保存过的新场景要先起个名字才能存；这种存档没有原文件路径，读档后仍停在存档里。
_Avoid_: ad-hoc 快照、ad-hoc snapshot、标记性快照

**未保存改动检查**: 读档前先看一眼有没有没保存的东西；结果跟着读档的返回一起给调用方，读档不会因此停下。
_Avoid_: 脏场景守卫、dirty-scene guard

## 连接与注入

**入口端口**: Maya 的 commandPort（默认 7001），只用来找会话和注入 helper，不跑正常工作。
_Avoid_: 引导通道、bootstrap channel

**工作端口**: 注入完成后专门收发命令的连接；默认是自带的 Qt TCP 服务，headless 时退回 Maya 原生 commandPort。
_Avoid_: 工作通道、working channel、专用通道

**临时文件注入**: 大段代码先写成临时文件，再让 Maya 去读；现在只有 headless 会话还走这个办法。
_Avoid_: temp-file 注入、temp-file、落盘、分帧协议

**asset_descriptor**: 下载素材和导入 Maya 之间的一张交接单：本地路径、来源网址、许可证、依赖清单。
_Avoid_: 受验证交接对象、handoff contract

**新模块的三条门槛**: 要新开一个 Maya 侧模块，得同时满足：有自己的注入时机、有自己的 API、坏了不影响别的模块。
_Avoid_: 注入模块准入判据、独立注入时机/独立 API 面/独立失败域、admission criteria

**同一个注入模块里的单独文件**: 功能仍归原来那个注入模块，代码可以放另一个文件，装配时一起注入；不能拿它绕开上面三条门槛。
_Avoid_: 同注入单元独立文件、SAME injection unit、fragment

## 安全姿态

**可信调用方**: 威胁模型假定 MCP 客户端和 agent 不会故意作恶。
_Avoid_: 受信方、trusted party

**防手滑措施**: 参数校验、限流、危险写法扫描这些防止手滑的措施；它们不是安全边界，挡不住故意作恶的人。
_Avoid_: 安全网、safety net、护栏、guardrail

**调用记录**: 每调用一次工具就写一行 JSON，单独存一个文件；写失败不影响工具执行。
_Avoid_: 审计日志、audit log、审计轨迹

**自动维护的代码块**: userSetup.py 里用 `# >>> mcp-for-maya >>>` 和 `# <<< mcp-for-maya <<<` 圈起来的一段；工具只改这一段，改前先备份。
_Avoid_: 标记块、marker block、幂等合并单元

**模块清理约定**: 覆盖一个已加载模块前，先调用它的 `_mcp_teardown`，让它关掉自己的 socket、Qt 服务和线程；这个清理可以重复调用。
_Avoid_: 模块卸载协议、teardown protocol、钩子须幂等

**端口类型探测**: 往端口发 `eval("1/2")`：回 0 是 MEL，回 0.5 是 Python；不改对方状态。
_Avoid_: 双语判别探针、bilingual probe、零副作用载荷

**免探测端口名单**: 确认过不是 Python 的端口，本次会话不再反复探测；等它不再监听时移出名单。
_Avoid_: 端口豁免集、exemption set、permanent exemption

**safe_mode**: 可选的收紧开关（`MAYA_MCP_SAFE_MODE`，默认关）；打开后 `execute_code` 和 `write_module` 的代码要先过允许清单，不通过就报 `safe_mode_rejected`。
_Avoid_: 收紧模式、opt-in gate、AST 门

**影响范围**: 一次误操作最多能弄坏多大一片。
_Avoid_: blast radius、爆炸半径

**被带偏的代理**: agent 被外部内容骗着去干用户没让它干的事。
_Avoid_: confused-deputy、confused deputy

## 工程词汇

**边修边拆**: 哪里出问题就在哪里加测试、顺手把那一块拆小，不搞一次性大重构。
_Avoid_: 绞杀者、strangler、增量拆分

**假 Maya 测试层（stub）**: CI 里用来代替 Maya 的假实现；数学要对，画面对不对不归它管。
_Avoid_: stub 层、stub tier、契约测试层、contract layer

**真机 Maya 测试（mayapy）**: 装了 Maya 的机器上手动跑的可选测试；不在 CI 里跑，别和假 Maya 层混在一起。
_Avoid_: mayapy 档、mayapy tier、Tier-2、真机层

**改完复原**: 工具可以临时改 Maya 状态，但结束时必须用 try/finally 恢复原样；`readOnlyHint:true` 靠这个才成立。
_Avoid_: 净零副作用、net-zero side effect、净零纪律

**两种出错返回**: 宿主这边出错走 MCP 的 `isError`；Maya 那边的错误放在 `{error:{code,message,suggestion?}}` 里。
_Avoid_: 双层错误契约、two-layer error contract、error contract

**三个名字**: 分发名 `mcp-for-maya`、导入名 `maya_mcp_server`、命令名 `mcp-for-maya`；分发名和导入名不同是 Python 打包惯例。
_Avoid_: 三层命名、three-layer naming

**需要人确认的事**: 改仓库名、推 main、打 tag/发版、发 PyPI、改 secret，要用户自己做或逐条点头；低风险且能撤销的 agent 可以自己来。
_Avoid_: 人工确认门、human gate、人工门

**只降不升的预算**: 把 lint 和类型错误的条数记进仓库，只许减不许加。
_Avoid_: 冻结预算、frozen budget

**只减不增的检查**: 除了固定预算，还要防止抑制标记只增不减，比如没用到的 ignore 和 noqa 必须马上删。
_Avoid_: 棘爪、ratchet pawl、ratchet

**暂时没接上的代码**: 已经排好要用、但现在还没有生产调用的代码；要标出来，它的测试不算生产覆盖率。
_Avoid_: 休眠代码、dormant code、dormant

**人工验收清单**: 人眼才能确认的测试项：标 `human_verify`，只打印步骤、不写断言，永远跳过。
_Avoid_: human_verify 骨架测试、skeleton test、骨架测试

**真机 cmds 清单**: 在真 Maya 会话里记下实际有哪些 `cmds.*`，存成 JSON 加白名单，用来检查假 Maya 层少了或多了什么。
_Avoid_: presence 基线、presence baseline、漂移检测、调用面

**两套 Python 环境**: 宿主 Python 和 Maya 内置 Python 的支持版本分开写；注入的代码要同时检查版本和能力。
_Avoid_: 双环境包、dual-runtime package、双层守卫

**中文译本**: 英文 README 是唯一准稿，中文版可以晚一点更新，但不能各写各的。
_Avoid_: 便利性镜像、convenience mirror、source-of-truth、镜像

**TDQS**: Glama 给工具说明打的第三方质量分；本仓库看字母档 A、每个工具至少 3.0、没有矛盾旗标，不为分数改坏 API。
_Avoid_: Glama 评分、tool description score

**Boundary: 一句**: 每个工具说明里加一句 `Boundary:`，点名 1–3 个相近工具，告诉调用方该用哪个。
_Avoid_: Boundary: 行、boundary line、单向消歧

**资产目录只增不删**: `.github/assets/` 里的图片被旧版 PyPI 页面用固定网址引用，所以只加新文件，不删不改名。
_Avoid_: 只加不删资产目录、append-only、只增不删

**单文件大模块**: `maya_scene_module.py` 这个很大的单文件，行数有上限；新功能另开文件，和它一起注入。
_Avoid_: monolith、巨石、主模块

**统一入口**: 所有工具调用都必须经过的同一个地方。
_Avoid_: choke point、唯一入口

## 已删除的说法

薄集成这条旧词条删掉了，只是词表自己造的说法，不是词条、也不用再解释一遍。
素材来源这件事，README 的素材那行和 `polyhaven.py` 都只提 Poly Haven。
下面这行只是不许再用的说法，检查脚本照样会拦：

_Avoid_: 薄集成、thin integration
