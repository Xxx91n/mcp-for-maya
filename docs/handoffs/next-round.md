# next-round.md — rev41（R31 毕：收录面三态立法已立 D-144..D-147；执行窗=T-31 文档批 + T-30 人工门清账并行）

生成：2026-09-29 R31 整理环节｜Spec：docs/decision-ledger.md D-144..D-147｜前档：rev40（R30 锐评三发现+平台扩张裁决）

## 环境实况（本环节核验）

- main=eadbea6（PR #51=T-30 执行批已落地：附录断言脚本+PyPI 双源探针+CONTRIBUTING 注记+mcp-name+badge）；账本 147 行（132 current+15 revised）。
- 账本栈未推未合：grill/round30-critique-registry（opk→tlq→upx→rur）+ grill/round31-audience-surface（nmv→nwl，叠于其上）。
- T-30 审计 LOOP-2 PASS（.scratch/t30/handoffs/audit-t30-passed.md）；PyPI simple index 呈 CDN 分裂（pip 车道见 0.4.0、urllib 探针见陈旧）→T-30i 须双车道复核。
- Glama 审计实证**未**自动索引本仓；claim 价值预期修正=占位+元数据所有权，非分发流量（D-144 注记）。
- #7 十框 0/10 真机窗未开；mayapy env-broken→GUI 通道；叙事轨推迟 v1.0.0 不动（D-143γ）。

## 任务清单

### T-31a — 新建 docs/distribution-surfaces.md 收录面三态登记表 — 覆盖 D-144/D-145αγ

起草参照文档（本体=唯一查询面，账本/CONTEXT/任务书互锚指针已就位）。必含件：①**三态表**——可行动（官方 Registry 绑下次发版/Glama claim/awesome PR）；被动观察带触发条件（mcp.so/PulseMCP/VS Code gallery→D-146 核销窗）；结构性否决永续（Claude Connectors 停收本地 MCPB/Docker Catalog 须容器镜像/Cursor 只收代码编辑工作流/Windsurf+Zed 无第三方提交面/Smithery——同构判据）；②**逐渠道理由列**（R31-Q1 调研四维矩阵为源：结构匹配性/受众质量/进入成本凭据面/宣称约束）；③**兜底条款+叙事修边**（未列出默认=被动观察+结构匹配性一票否决闸；兜底不豁免叙事轨 D-143γ）；④**staleness 纪律行**（表头：权威载体=账本 D 行，改渠道处置先落账本再改表——upstream 对照表先例）；⑤Glama 行备注（claim 后改 repo 描述/logo 须重走 claim flow；无 Dockerfile 构建面=不分发常态）；⑥mcp.so 行（否决理由换锚=issue 人工提交面+受众质量低，非自动同步假设）；⑦atomcode R31-Q3 报告遗漏面 #1-#8（ctx 索引 atomcode-r31q3 批次可取；#8 收录后宣称面同步义务按调研建议并入兜底条款消化，不立常设义务）；⑧一切渠道描述文本过 D-132 句式（4-Beta 禁 stable 语气）。

suggested skills：domain-modeling（三态判置词条对齐）、neat-freak（staleness 纪律+指针互锚核验）

### T-31b — ADR-0023 增补「R31 增补（发布后段）」 — 覆盖 D-145β/D-146

增补块加独立小节「发布后段（一次性核销）」一行：Registry publish 动作完成后 30 天，一次性核销 mcp.so/PulseMCP/VS Code gallery 收录态（核验 Registry 同步已发生/未发生并按 distribution-surfaces.md 三态落账）；逾期未核销=债文标已触发未兑现；非 CI 项无探针步。**必带真源声明行**（「唯一真源=D-146 账本行，本块为抄写+格式化载体」——对齐 R28 块措辞纪律）；与 v1.0.0 硬项区隔（核对时点不同，gate 在 tag 前、本行在 publish 后）。

suggested skills：domain-modeling（发布门前清单词条对齐）

### T-30a — v0.4.0 Release body 补挂披露附录（人工门，未变） — 覆盖 D-049/D-115/D-142α

备稿在 .scratch/t30/release-appendix-v040-draft.md（快照语义+去计数化+D-132 句式已按裁决起草）；序：用户过目批准→gh release edit v0.4.0 就地补挂→账本注记「D-138③ 所记 body 形态自此不再准确」→check_release_appendix.py 复核转绿（设计内反馈环，当前 exit 1=附录未挂的预期红）。

suggested skills：handoff、neat-freak（措辞校准核验）

### T-30f — Glama Add-Server+claim（人工门，未变） — 覆盖 D-143α/D-144③

实证未自动索引→Add MCP Server 提交 repo URL→GitHub OAuth claim（个人账号直连免 glama.json）。**禁启 Docker 构建面**；预期=占位+元数据所有权非分发流量（D-144 注记）；claim 后改 repo 描述/logo 须重走 claim flow（T-31a 登记表备注同源）。

suggested skills：—（用户 OAuth 人工门）

### T-30g — awesome-mcp-servers PR（人工门，未变） — 覆盖 D-143α

照抄格式+字母序+🤖🤖🤖 fast-track；行稿已在 .scratch/t30/；不押时点。若行内描述文本与收录页失真有更新义务——随 T-31a #8 兜底条款消化。

suggested skills：—（用户推 fork 或授权）

### T-30h — server.json+Registry publish（绑下次发版，未变） — 覆盖 D-143β/D-145

草稿在 .scratch/t30/server.json；发版窗动作序：version 改届时 PyPI 精确版本→mcp-publisher validate 离线→人工门 login github+publish→核验 curl+registry status 命令查 active；publish 完成即刻账本落 publish 日期=D-146 30 天核销窗起算点（非发版日）。

suggested skills：neat-freak（发布编排纪律嵌套）

### T-30i — D-139 销账复核（双车道，未变） — 覆盖 D-139/D-142γ

CDN 分裂实锤后须双车道复核：pip index versions mcp-for-maya（用户面）+check_pypi_index.py 探针车道（urllib/simple index）各带时间戳；两车道均稳定见 0.4.0→账本注记销账；仍分裂→原裁决（删版重传或 0.4.1 patch D-133②）回用户拍板。weekly 探针首跑若红=设计内真信号非脚本 bug（notify 归因车道命名失败步）。

suggested skills：neat-freak（带时间戳销账）

## 结转挂账（非本轮新增，时点驱动）

- **2026-10-05 双窗观测**（D-127/D-137）：native cron 37 6 * * 1 是否自愈+scheduler 14:40 +08 自触发；双双静默→incident 行+第三载体。
- **#7 十框+D-115 探针补采**（真机窗）：Maya 2024 在机，GUI 通道；v1.0.0 硬项。
- **D-146 核销窗**：Registry publish 后 30 天（事件锚，publish 日期落账即起算——勿用发版日）。
- **D-147 Cline 信号**：核验动作并入 D-146 同窗顺带执行（共用观测窗零成本）。
- **notify 红路径**：观测项挂起，无自然红不制造。
- **叙事传播**（D-143γ）：备稿不发，v1.0.0+#7 全绿后启用；兜底条款不豁免本门。
- **叙事轨备选面登记**（R31 调研副产品）：r/Maya、r/vfx、技术美术论坛=高密度目标用户叙事渠道，v1.0.0 叙事轮调研面。

## 措辞红线

- 收录轨价值=可发现性兜底非拉新主力（MCP 目录 Maya 密度低）——任务书/对外文本禁夸大目录流量。
- 渠道处置改动=先落账本再改表（staleness 纪律）；登记表外渠道默认被动观察。
- 附录=装船时点快照+声明性指针，禁计数型内容/tracker-dump。
- 一切对外宣称=4-Beta+能力+证据指针（D-132）；禁收录徽章堆砌、禁荣誉墙。
- 账本唯一真源 docs/decision-ledger.md。
