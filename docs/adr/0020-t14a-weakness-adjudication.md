# T-14a 弱点裁决：presence 更名 + call-form 显性兼任 + 对照表工件 + MVector 拆类 + VP2 读回修复

T-15 门面轮审计 PASS 后，对审计遗留弱点逐项裁决（D-055：本轮=裁决轮，VP2 flip/BGR 作第 5 项——门面 dogfood 截图即出自该工具，不修则证据图诚实性存灰区）。atomcode 调研（官方文档直读+社区一手记录交叉）修正后定稿：①signature-baseline 更名 presence-baseline（cmds builtins 永远无 inspect.signature，等重采案死证）；②call-form 由 gui 档显式兼任不新增档；③visual_module 补独立对照表（证据/结论分层）；④MVector(MPoint) 继承是语义错误必拆；⑤VP2 修复=条件化翻转锚纯色断言+floatPixels swizzle 官方在列路径。

Status: accepted (2026-09-21)

## Considered Options

- **①保名+meta 注记 / 等健康环境重采真签名**：否决——调研实锤 cmds builtins 永无 inspect.signature（help() 方为官方内省通道），"健康环境"不存在；golden-file 惯例：文件名是载重信息，名实不符=每次 PR 重复缴税。
- **②call-form 独立成档**：否决——Fowler 窄集成测试归层：形态断言的自然宿主是既有真机档（gui/mayapy）；为 10 个 API 单开第三档=制造既非 CI 也非纯手动的怪胎，维护成本与 cmds 面十年不动的演进速度不匹配。
- **②仅口头追认不落纸**：否决——"实质承担"与"契约承担"之差会被时间磨平；显性化动作=~10 API 形态断言点写进 testing.md+human_verify 清单，"恰好路过"升级"必须路过"。
- **③并入 allowlist 理由**：否决——证据层（对照表）与结论层（allowlist）分离同构 audit JSONL/pipeline 架构；表带官方文档 URL+版本+日期戳，allowlist 行只留 verdict+锚链；10 行规模虽小，表是未来新调用的接收结构。
- **④留 allowlist 挂账**：否决——官方文档直读实锤兄弟类（MPoint len==4 有 w/cartesianize，MVector len==3 无 w 有叉积）；继承使 isinstance/w/len 全反=stub 绿真机炸的虚假信心；allowlist 只配收"行为对但表面不符"的账，行为本身错不许挂账（违 D-005 立层原则）。
- **⑤只记不修 / 版本号分支 / universal swizzle / 满屏纯色 fixture**：全否决——版本分支脆（同版本不同 GPU 有方向性差异前科）；convertPixelFormat 十年缺席 Autodesk 无意补不做等待分支；翻转方向只有实证能定，非对称布局（左上红块其余黑）才锁得住"翻没翻"，满屏纯色锁不了方向；色管用容差带（OCIO 可偏移纯色）。

## Consequences

- **①更名**（D-056①）：signature-baseline.json→presence-baseline.json（git mv+全量 grep 消费方+meta content_type:"presence-callable" 机器可读解释）；signature-allowlist/test_signature_baseline.py 同步。
- **②显性兼任**（D-056②）：call-form 职责落纸 gui 档契约文档（testing.md+human_verify 清单列 ~10 API 形态断言点）；无视口依赖项归 mayapy 档（本机 env-blocked 挂账待健康机）。
- **③对照表**（D-056③）：visual_module ~10 调用独立对照表工件（call×官方签名×verdict×URL×版本×日期）；allowlist 行=verdict+锚链指表，表为唯一事实源。
- **④拆类**（D-056④）：MVector 独立成类与 MPoint 兄弟；同步实现 MPoint↔MVector 互转构造（真实 API 允许且 w 置 1.0）；翻红既有断言属预期（暴露错误断言=拆分目的非副作用）。
- **⑤VP2 修复**（D-056⑤）：条件化翻转锚纯色断言实证朝向；通道序=floatPixels()手动 swizzle+setPixels+setRGBA(True)；gui-tier 新增非对称纯色断言 fixture（左上红块+容差带）；顺带 hasattr(MImage,convertPixelFormat) 真机实证；核对 shot-hero/shot-alt 是否经此路径——失真则修复后重捕（门面证据图诚实性闭环）。
- **证据强度说明**：2024 无 convertPixelFormat 为文档缺席推断（gui 验证时 hasattr 实证收口）；Meszaros 转述双源；2025/2026 行为未逐版查留"碰到再修"口。
