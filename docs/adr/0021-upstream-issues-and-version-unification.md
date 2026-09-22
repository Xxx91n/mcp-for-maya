# ADR-0021 — 上游 issue 裁决与版本统一（T-16 spec 簇）

状态：accepted（grill 定稿）
日期：2026-09-22
决策来源：D-057（本轮范围）、D-058（#4）、D-059（#1）、D-060（#3/#5/版本）

## 背景

本仓 fork 自 chadrik/maya-mcp-server（MIT 保留，GitHub 未登记 fork 关系）。上游 6 个 open issue、0 closed、最后提交 2026-07-15——本 fork 已是事实维护线。逐项代码实证后裁决：#2（fakeredis FakeConnection）与 #7（execute_code 吞 result.error）已由既有工作解决，只登记结论；其余四项+版本双轨进入本 ADR。

## D-058：上游 #4 — create_module(overwrite=True) 孤儿化 _qt_server（修）

缺陷链：`_bootstrap` 热更新路径（client.py:584-588）对已引导会话调 `create_module('maya_mcp', …, overwrite=True)`；create_module 新建 ModuleType 直接顶掉 sys.modules 条目，旧模块全局里 LISTEN 中的 QtCommandServer 被孤儿化——端口仍占用致新 server 同端口重绑失败。每次重连已引导会话必触发。

裁决：**模块卸载协议（teardown hook）**——create_module overwrite 分支替换 sys.modules 前 `getattr(old, '_mcp_teardown', None)` 判空调用；helper 实现幂等 `_mcp_teardown`：逐项独立 try/except（单项失败不中断）、Qt 对象走 deleteLater 语义、stop 须断 newConnection 等信号连接而非仅关 socket（防重载后双触发）。可选 `__build__` 构建标记供更新后断言重载生效。

依据：QGIS Plugin Reloader（最同构：GUI 宿主+Python 插件+资源句柄）的 unload() 分工纪律；Webpack HMR dispose/data 模式；importlib 官方语义实锤根因（替换 sys.modules 不触发清理，listen socket 被 Qt 事件循环/C 层持有引用不归 GC 管）。

回归测试（stub 层三例）：①持假 listen socket 的 helper→overwrite→断言 teardown 被调+资源 closed；②teardown 抛异常→替换仍完成+异常记录不传播；③旧模块无钩子→判空分支不崩。

否决项：(b) 客户端两步点修——保护钉死单一调用点，通用原语的洞仍在，降为止血备选不独立立项；(c) 状态过继独立方案——旧引用会被模块级重初始化再覆盖（延迟孤儿化非解决），仅可作 teardown 内纯数据过继；(d) 原地重 exec=importlib.reload 语义，官方陷阱清单长且不消除 (a) 必要性。

## D-059：上游 #1 — MEL 端口探测刷屏（修，真机验证前提）

本仓实证：后台扫描环 10s 周期+失败端口 60s 冷却→每个 MEL 端口每分钟吃一次 Python `1+1`→Script Editor 周期性报错（上游报告者实证 2022/2026 同病）。已有缓解：loopback-only 过滤、_detect_port_type 判 MEL 后拒 bootstrap、失败冷却降频。根因：psutil 看不到 commandPort sourceType，只能发包试探。

裁决：**A′+C 组合**——

1. 探针载荷改 `eval("1/2")`：eval 在 MEL（标准命令，表达式上下文 int 除法→0）与 Python3（builtin→0.5）双侧皆合法且返回值可区分、双侧零报错。约束：eval 内必须保 int/int 操作数（1.0/2 双侧同值失判别力）。
2. 判别为非 Python 的端口入**会话级永久豁免集**（端口从 LISTEN 消失才解禁）——工业界 probe minimization+指纹缓存范式，终结周期重探。
3. 附加 env/config 端口 include/exclude 过滤配置（上游用户 workaround 产品化，覆盖第三方 DCC TCP 服务误探残余面）。

双向纠错实录（诚实留档）：助手原案 `print(1/2)` 死证（commandPort 只回传返回值不回传 stdout，print 返回 None）；atomcode 旗舰案 `// 1/2` 死证（本机实测 SyntaxError——// 是 Python 二元中缀算子非注释，照做会让 Python 端口刷错且判别失效）。幸存载荷 `eval("1/2")` 的 MEL 侧回传字节形状与静默性为唯一关键未知项——**真机 GUI 验证为前提，翻车则退化为豁免集单走（每端口每会话一行错误）**。

否决项：MEL python() 反向包裹——判别方向相反且把报错负担转嫁到 Python 端口（我们要用的端口）；不修仅文档化——根因可消不留。

## D-060①：上游 #3 — ast.unparse Py3.7（双环境包 floor 声明）

dual-runtime 处置：requires-python>=3.10 只描述宿主依赖图；注入端（Maya 内嵌解释器）独立声明 floor。文档写支持矩阵：宿主 Py≥3.10 / 注入端 Maya≥2023（Py≥3.9，ast.unparse 可用边界）/ 实证面=Maya 2024。helper 双层守卫：`sys.version_info<(3,9)` 在前报友好可操作消息（点明 Maya 2023+），`hasattr(ast,'unparse')` 在后作 fork/patched 解释器事实兜底。

否决项：仅文档化不加运行时守卫（文档声明无边界执行≈没声明）；为 Maya 2022/Py3.7 写兼容 shim（已声明不支持的环境写兼容层=反模式，支持矩阵永远收不回来）。

## D-060②：上游 #5 — 多实例 commandPort 文档（分层补写）

README 双语+testing.md 增多实例章节：原理段（commandPort=绑死 host:port 的单监听 socket，同端口二实例 bind 失败）+per-instance 拓扑示例+自动扫描为主路径/add_session 手动兜底+症状化 troubleshooting+明示 commandPort 不跨会话持久（userSetup.py 为推荐持久化机制）。

## D-060③：版本统一 — serverInfo=产品版本

实测：FastMCP("Maya MCP Server") 未传 version→握手 serverInfo 泄漏框架版本 2.14.2。MCP 规范实锤 serverInfo.version=implementation 产品版本（协议版本走独立 protocolVersion）——非双轨，是遗漏缺陷。

裁决：`FastMCP(version=<产品版本>)`——运行时 `importlib.metadata.version("mcp-for-maya")` 为主（dist 名非 import 名），`__version__` 字面量为源码树 fallback，加一致性断言测试防再漂移。

## 证据强度说明

- #4/#1 缺陷链为本仓代码直读实证；#4 修复路线经 atomcode 三源独立证实（QGIS/Webpack HMR/importlib）
- #1 探针案经双向纠错后幸存 `eval("1/2")`，MEL 侧行为仍待真机定型（已在裁决内置退路）
- #3 版本映射（2022=3.7/2023=3.9/2024=3.10）与 serverInfo 语义经官方文档直读
- 调研缺口已录：Tavily 未参与；FastMCP version 参数行为经文档页+实测间接验证
