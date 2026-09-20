# issue #7 真机验证轮：修复先行 + 活会话权限 + 证据治理 + manual-tier 固化 + 0.1.2 patch

T-10b 落地后进入 D-043 排序的下一主线——issue #7 真机验证（D-040 v1.0.0 定义性门），本轮因用户 Maya 2024 本机开机而解锁。首探即中 ship-stopper：已发布 0.1.1 的 scene_* 工具面+视觉主路径在真实会话全灭（scene_tools.py/visual_tools.py 内部调用传裸 "JSON" str 撞 client.execute_code 的 result_type.value 枚举期望；execute_code 为 BaseMayaClient 共享实现故 Qt/native 双通道同炸；stub 层 mock 传输缝致 570 测试全绿漏检）。决策：修复先行+验证同轮交织、活会话全权限、证据归 agent/勾选归用户、真机项固化 manual-tier pytest、签名审计走 stubtest 式自动比对、修复面验证后即发 0.1.2+yank 0.1.1。

Status: accepted (2026-09-20)

## Considered Options

- **先扫后修 / 纯验证不修（D-046 B/C）**：否决——主工具面全死，无修复则无可验证之物；枚举缺陷的前提是 execute_code 可用。
- **保守只读边界 / 中档放行（D-047 B/C）**：否决——场景已实证空净 untitled（cmds.ls=[front,persp,side,top]），全部操作可逆；checkpoint 落盘限定 workspace/checkpoints/；扰动类（RST/FIN 杀连接）排序最后且用户可随时叫停；后端 pid 3168 跑旧码留作 0.1.1 原样证据面，修复验证靠直驱 harness 不阻塞等重启。
- **agent 直接勾选 / 全人工执行（D-048 B/C）**：否决——checkbox 是 v1.0.0 门的公开宣告，宣告权归用户复核后亲手勾（人工门精神延伸至验证层）；agent 产证据链（transcript/返回体/ImageContent 图像判定/exit code）落 .scratch 报告+issue #7 评论。
- **一次性探针脚本+报告（D-049a 备选）**：否决——issue #7 须在 0.1.2、未来 Maya 2025/2026 复跑；工业同构 SIL(stub)/PIL(mayapy)/HIL(活 GUI) 分层中 HIL 必须可重复（ESP-IDF target marker 先例）；按 RC 节奏跑不卡 CI。
- **GUI 项硬 assert 自动化（D-049a 反方）**：否决——视口态/焦点/DPI 使断言脆弱造假红假绿；人眼项版化为 human_verify 骨架测试（test 存在+打印人工步骤）保清单不散落。
- **全人工逐条签名审计（D-049b 备选）**：否决——cmds.* 数百命令+文档随版本漂移，不可扩展不可重复；mypy stubtest（stub↔runtime 漂移官方检测）/monkeytype（真机采集回填）为直接先例；采集限项目实际调用面。
- **等 #7 全绿再发 patch（D-049c 备选）**：否决——semver 明定已发布内容不可改、在售坏版每日扩损；0.1.2 的门=修复同类传输路径真机验证过，#7 全绿是 v1.0.0 的门不倒挂 patch；扰动项再爆 blocker 则 0.1.3 连发属知情接受。

## Consequences

- **修复先行**（D-046）：result_type 缺陷修复+回归测试（补 str 入参→真 execute_code 传输缝的契约测试——本轮失效根因是 stub mock 掉 execute_code 致真实方法从未被测）；修复后代码上跑全清单，每发现即修即验；__version__ 0.1.0/0.1.1 漂移并入本轮顺手修（诚实档同类）。
- **活会话权限**（D-047）：场景变更/文件落盘/视觉工具/连接扰动全放行；扰动类最后执行；Maya 2024 单版本可验（2025/2026→partial 如实标）。
- **证据治理**（D-048）：agent 执行+证据链→.scratch 报告+issue #7 评论；勾选权归用户；partial/blocked 不勾不粉饰；agent 直读 ImageContent 判 pixel sanity（占多客户端一席）。
- **manual-tier 固化**（D-049a）：新 marker（gui）机器可断项真断言+conftest 环境探测默认 skip；human_verify 骨架测试版化人眼清单；与 mayapy 档并列不卡 CI。
- **签名审计混合**（D-049b）：visual_module ~10 调用人工全量对官方文档；maya_scene_module 面走 mayapy inspect.signature 采集→与 stub 自动 diff→人工只裁 diff 命中项；产出 signature-baseline.json+allowlist 入库成 ratchet（冻结预算同构）；call-form smoke 补行为层（签名够不着时序/副作用）。
- **0.1.2+yank**（D-049c）：修复同类传输路径真机验证过→备 0.1.2 发布人工门清单；release notes 按 tier 如实披露+known-issues；0.1.1 执行 yank（标坏不下架可逆）；merge/tag/release/yank 全归人工门。
- **证据强度说明**：SIL/PIL/HIL 为嵌入式类比映射（Maya 非硬件，命名自定）；PyPI yank 惯例未深挖一手先例；stubtest 结构同构但需自研采集器（cmds 非 stub 文件形式）。
