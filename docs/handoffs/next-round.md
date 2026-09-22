# next-round.md — rev24 常驻任务书（T-16 上游 issue 修复轮 + 顺延队列）

生成：2026-09-22 grill round16（上游 issue+版本双轨合并裁决）定稿后
数据源：docs/decision-ledger.md D-057~D-060；ADR-0021
前置事实：T-14a 已审计 PASS 并落地主干（tip d07b056）；五门绿 pytest 598/24、ruff 83/83+28/28、mypy new:0、sdist 313KB/wheel 134KB、pre-commit 8/8

## 上手 30 秒

- 仓库：D:\Aworker\maya\maya-mcp-server；dist 名 mcp-for-maya / import 名 maya_mcp_server
- VC 一律用 GitButler（but）；**幻影簿记仍在**：5 条 .github/assets @2x→裸名 R 残留属索引假象（HEAD==磁盘已证），严禁 but discard；一切写操作前 git ls-tree 对账
- 测试分层：stub=默认 CI；gui/human_verify/mayapy=manual-tier 真机档（-m 标志，默认 skip）
- 真机窗口依赖用户 Maya 2024 GUI 开机；T-16b/T-16f 卡在窗口上

## 任务链

### T-16a — create_module teardown 协议（上游 #4 修复）[D-058]

- maya_bootstrap.create_module：overwrite 分支替换 sys.modules 前 getattr(old,'_mcp_teardown',None) 判空调用；teardown 异常捕获不阻塞替换、警告进返回 JSON
- maya_mcp_helper 实现幂等 _mcp_teardown：逐项独立 try/except、Qt 对象 deleteLater 语义、stop_qt_server 须断 newConnection 信号连接非仅关 socket；可选 __build__ 构建标记
- stub 回归三例：teardown 被调+资源 closed / teardown 抛异常替换仍完成 / 无钩子判空不崩
- 同步面：maya_bootstrap 消费方全 grep；联动规范查 AGENTS.md（client.py bootstrap 路径）

### T-16b — 探测双语化+豁免集+端口过滤（上游 #1 修复）[D-059]

- _detect_port_type 探针载荷 1+1 → eval("1/2")（判别：回传含 0.5=Python / 0 或静默=MEL）；eval 内必须 int/int
- session_manager 增非 Python 端口会话级永久豁免集（端口从 LISTEN 消失才解禁）；与 _failed_ports 冷却分层共存
- env/config 端口 include/exclude 过滤（上游 workaround 产品化）
- **真机验证前提**：MEL commandPort 对 eval("1/2") 的回传形状与静默性未定型——T-16f 窗口内 nc/探活定型；翻车退化为豁免集单走
- 回归：stub/单元层覆盖判别分支与豁免集生命周期

### T-16c — 双环境包 floor 声明（上游 #3 处置）[D-060①]

- 文档支持矩阵：宿主 Py>=3.10 / 注入端 Maya>=2023（Py>=3.9）/ 实证面=2024（README 双语+testing.md）
- helper 注入前置双层守卫：sys.version_info<(3,9) 报友好消息（点明 Maya 2023+）→ hasattr(ast,'unparse') 兜底
- 不为 2022/Py3.7 写兼容码

### T-16d — 多实例文档（上游 #5 处置）[D-060②]

- README 双语+testing.md：原理段（commandPort=绑死 host:port 单监听 socket）+per-instance 拓扑示例+自动扫描主路径/add_session 兜底+症状化 troubleshooting+commandPort 不跨会话持久→userSetup.py 持久化明示

### T-16e — serverInfo 版本统一 [D-060③]

- server.py：FastMCP(version=)——importlib.metadata.version("mcp-for-maya") 为主、PackageNotFoundError fallback __version__
- 一致性断言测试：__version__==importlib.metadata 版本（防 T-13 前漂移复发）

### T-16f — 真机 GUI 验证窗口批（一次开机全收）[依赖用户 Maya 开机]

- VP2 非对称纯色断言钉 _VP2_READBACK_BOTTOM_UP（T-14a 遗留）
- callform surface probe（currentTime 净零自证）
- **新增**：MEL commandPort 的 eval("1/2") 回传形状定型（T-16b 前提）
- #4 活实证：重连已引导会话→断言旧 _qt_server 被 teardown 而非孤儿化
- hasattr(MImage,'convertPixelFormat') 顺带实证（T-14a 遗留已证 C++-only，复核即可）

## 顺延队列（非本轮，保持原主）

- **T-14c 发布链**：tag v0.1.2/release/yank 0.1.1/issue#7 评论+勾选/social preview 上传/repo About=全人工门
- **T-14b #7 残余**：多客户端矩阵（用户环境）/Maya 2025-2026/mayapy env-blocked 修复/headless fallback
- **登记债**（不自动认领）：T-06 dormant aesthetic_engine 归置、Poly Haven issue#2、validator issue/T-07、依赖锁定、mypy 2.x 输出、coverage patch 门、macOS 冒烟、ctx preload、Maya 2022+ commandPort 文档（部分被 T-16c/d 覆盖）

## DoD（本轮收口标准）

- [ ] T-16a~e 全落地：teardown 协议+双语探针+豁免集+端口过滤+floor 守卫+多实例文档+版本统一
- [ ] stub/单元回归全绿；pytest/ruff/mypy/build/pre-commit 五门复跑
- [ ] T-16f 真机窗口实证（Maya 开机后）：eval 探针定型+VP2 断言+重连 teardown 活证
- [ ] #1 探针案翻车则如实退化豁免集单走，不虚报双侧零副作用
- [ ] CHANGELOG pending-release 同步（上游 issue 修复叙事）

## 负向清单

- grill/spec 期不动源码（本轮已出 spec，实施归实现阶段）
- 不做状态过继独立方案/原地重 exec/客户端两步当长期解（D-058 否决项）
- 不为 Maya 2022 写兼容 shim（声明即契约）
- 不把 serverInfo 双轨文档化当解（是缺陷非设计）
- 不趁轮次顺手消费登记债
- 发布/推送/勾选类人工门一律留给用户

## suggested skills

- $implement / $tdd — T-16a~e 实施（teardown/探针/守卫/文档/版本各成小 commit）
- $handoff — 翻页与交接
- $but — 全部 VC 写操作（先 git ls-tree 对账幻影）
- $atomcode-research — 争议点调研（串行单发）
- grill-with-docs — 下轮裁决启动器
