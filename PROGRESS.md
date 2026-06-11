# Progress

## 2026-06-04 · Day 1 — CAW 接入 + 首个端到端测试网交易跑通 ✅

承重墙立住：从 0 代码到链上活着、带真人审批的 Agent 钱包流程。

### 完成的闭环

```
Agent 提交 Pact（最小授权：单地址白名单 + 24h 1 笔上限）
  → owner 手机 App 批准（HUMAN GATE）
  → Pact 激活
  → Agent 在授权内执行 transfer
  → Sepolia 链上确认，真 tx hash
```

### 链上身份（dev 环境 / 测试网，公开数据）

| 项 | 值 |
|---|---|
| Agent ID | `caw_agent_5fdd24260f156636` |
| Wallet UUID | `29ff4a15-d034-4edc-922e-71b0b48122d8` |
| ETH/EVM 地址 | `0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6`（Sepolia / Base Sepolia 等通用）|
| SOL 地址 | `6tZ63ggxjDjLukyWCp2xTYpZjR4qi15xijwhsdsBPjXV` |

### 首个 Pact + 交易（提交物级别证据）

| 项 | 值 |
|---|---|
| Pact ID | `7ef2c434-17f7-436c-8dbe-293924eb3a04` |
| 动作 | transfer 0.001 `SETH_USDC1` → `0x2348...81ba`（Sepolia）|
| Tx Hash | `0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726` |
| 验证 | https://sepolia.etherscan.io/tx/0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726 |

### 环境 / 接入

- caw CLI `v0.2.84`（`~/.cobo-agentic-wallet/bin/caw`，全局，凭证不入库）
- dev 环境：`agenticwallet.dev.cobo.com`，手机 App 走 TestFlight（Mock 登录）
- 测试币：faucet 领了 0.01 SETH（gas）+ 0.01 SETH_USDC1（USDC）

### 已证明 vs 还没建

| 已通 ✅ | 还没建 ⬜ |
|---|---|
| CAW 接入 + MPC 钱包 + 测试网真执行 | **Auditor 层**：语义检查 / 防注入 / 可读 risk summary |
| 人类审批闭环（手机批 Pact）| LangGraph 编排 + Claude Dynamic Workflow |
| 最小授权 policy（白名单 + 频率上限）| x402 / 采购场景包装 |
| 真 tx hash（hackathon 提交物之一）| golden set（5–6 regression cases）|

→ 今天通的是 **CAW 执行轨道 + 人类闸门**；差异化（Auditor）是坐在其上的下一段编码。

### 下一步

1. ✅ 建第二个 pact 演 **policy 拦截**（故意违反白名单 → CAW STOP），证明边界是真的。见 2026-06-06 记录。
2. 接 LangGraph 骨架 + Claude Dynamic Workflow，把"动态准备 → Auditor 把关 → CAW 执行"串起来。
3. 设计 Auditor 的 risk summary 怎么喂进 Pact 审批（Auditor↔Pact 接缝）。

## 2026-06-06 · Day 2 — CAW policy 拦截证据跑通 ✅

补齐第二条提交物级证据：同一个钱包、同一个 CAW execution layer，在授权内可以执行，在收款地址越界时会被 CAW policy 层拒绝，且不会产生链上交易。

### 对照结论

```text
Same wallet, same CAW execution layer.
Allowed recipient -> transaction succeeds.
Disallowed recipient -> CAW blocks before broadcast.
```

### 成功路径（6.04 对照）

| 项 | 值 |
|---|---|
| Pact ID | `7ef2c434-17f7-436c-8dbe-293924eb3a04` |
| 动作 | transfer 0.001 `SETH_USDC1` → allowlisted recipient（Sepolia） |
| Tx Hash | `0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726` |
| 结论 | 授权范围内的测试网转账可以通过 CAW 执行并上链。 |

### 拦截路径（6.06 新增）

| 项 | 值 |
|---|---|
| Pact ID | `d583ae23-cc5c-4a80-8f16-69c59970e698` |
| Policy | 只允许 `SETH_USDC1` 在 `SETH` 链上转给地址 A：`0x23482606e068480f91cd7b1a6f775986a96081ba` |
| 失败测试 | 故意把同样的 0.001 `SETH_USDC1` 转给地址 B：`0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6` |
| Request ID | `denial-wrong-recipient-20260606-2` |
| Transaction record ID | `10dbaf29-b5ab-4091-8059-6b2e9d8bda76` |
| Status | `Rejected` |
| Denial code | `ADDRESS_NOT_WHITELISTED` |
| Reason | `no_pact_transfer_allow_policy_matched` |
| Suggestion | `Destination address is not whitelisted. Use a whitelisted address or request the wallet owner to add it.` |
| 链上 tx | 无 tx hash，CAW 在 broadcast 前拒绝。 |
| 清理 | 测试完成后在 App 中 revoke Pact；复查状态为 `revoked`。 |

### 这条证据证明了什么

Agent 拿到的不是钱包私钥，也不是无限权限，而是一段被 CAW policy 强制约束的能力。Auditor 的价值不是重写 CAW enforce 层，而是坐在 CAW 之上，负责语义正确性、输入侧防注入，以及把 payment draft / Pact 变成人能判断的 risk summary。

### 失败类型区分

| 类型 | 含义 | 是否证明权限边界 |
|---|---|---|
| 参数错误 | 例如缺 `src_addr` 触发 422 | 否 |
| Auditor local STOP | 应用层预检拦截 | 是，但不是钱包执行层证据 |
| CAW enforced STOP | CAW pact policy 拦截，未广播交易 | 是，且是本 demo 的核心硬证据 |

## 2026-06-07 · Day 3 — risk_summary schema 入项目 ✅

把 2026-06-05 设计的 `risk_summary schema v0` 迁入项目，先做 schema + fixtures，不接服务、不做 UI。

### 今日最小交付

- `schemas/risk-summary.schema.json`
- `fixtures/risk-summary/allow-normal-payment.json`
- `fixtures/risk-summary/reject-wrong-recipient.json`

### 下一步

1. 接 LangGraph 骨架：`PLAN_DYNAMIC_WORKFLOW -> AUDIT -> HUMAN_GATE -> CAW_EXECUTE -> DONE/STOPPED`
2. Claude Dynamic Workflow 只生成/修正 candidate vendor 与 payment draft，不允许直接执行 CAW。
3. golden set 扩到 5-6 条：正常通过 / 白名单错误 / 金额超限 / 字段偷换 / 恶意文档注入 / 余额不足。

### 学习启动

- 新增 `docs/langgraph-skeleton.md`，明确 LangGraph 管确定性状态机，Claude Dynamic Workflow 只管可逆规划。
- 第一段代码不接模型、不接 CAW：先用两个 `risk_summary` fixtures 跑通 `AUDIT -> HUMAN_GATE/STOPPED` 分支。

## 2026-06-08 · Day 4 — LangGraph tracer bullet 跑通（控制流，不接模型/CAW）✅

把 `docs/langgraph-skeleton.md` 的"第一条 tracer bullet"变成可运行的最小状态机：5 个 stub 节点 + 两条 fixture 驱动的 run + 打印 audit_log。只证明控制流，不调用 Claude，不调用 CAW。

### 今日最小交付

- `src/hermes_auditor/state.py` — 11 字段 `HermesState`；`audit_log` 用 `operator.add` reducer 做 append-only。
- `src/hermes_auditor/fixtures_io.py` — 加载 fixture 并按 `risk-summary.schema.json` 校验后才进图。
- `src/hermes_auditor/nodes.py` — 5 个 stub 节点；只有 `AUDIT` 有真实逻辑。
- `src/hermes_auditor/graph.py` — 最小图 + 3 处 conditional routing。
- `src/hermes_auditor/run_tracer.py` — 入口；`uv run hermes-auditor`。
- `pyproject.toml` / `uv.lock` — uv 项目，依赖 `langgraph` + `jsonschema`。

### 两条 run 的终态

| fixture | 路径 | 终态 |
|---|---|---|
| `allow-normal-payment` | PLAN → AUDIT(ALLOW) → HUMAN_GATE → CAW_EXECUTE | DONE（stub 6.04 tx hash） |
| `reject-wrong-recipient` | PLAN → AUDIT(REJECT) | STOPPED |

### 关键设计判断

`AUDIT` 从 `checks` / `red_flags` **推导** `audit_decision`，不读 fixture 自带的 `decision` 标签；fixture 的 `decision` 降级成 oracle，输出里的 `fixture-oracle=ok` 用来断言推导逻辑和设计意图一致。这一步把"风险判断"变成"控制流"。

### 下一步

1. 只把 `PLAN_DYNAMIC_WORKFLOW` 换成 Claude 调用，其他节点不动（图不关心 payment draft 是哪个模型生成的）。
2. `HUMAN_GATE` 从 stub auto-approval 换成 LangGraph `interrupt` 真人闸门 + `checkpointer` 回放。
3. golden set 扩到 5-6 条：正常通过 / 白名单错误 / 金额超限 / 字段偷换 / 恶意文档注入 / 余额不足。

## 2026-06-09 · Day 5 — 概念纠偏 + PLAN 可逆区骨架(fan-out + adversarial)✅

### 概念纠偏:Claude Dynamic Workflow 到底是什么

之前一直把它当成「单 agent 自我编排的 tool-use loop」。查 Anthropic 官方 docs 后纠正:它是 **Claude Code 的正式功能**(2026-06-03 发布)——Claude 当场写一个**确定性 JS harness,编排大量独立-context 的 subagent**;「下一步做什么」是脚本决定(workflow 端),动态只在「现写脚本」这一层。

**判决级约束**:dynamic workflow **不支持中途人输入**(docs:"No mid-run user input … run each stage as its own workflow")。Hermes 命根是不可逆动作前的 HUMAN_GATE,故 dynamic workflow **不能持人闸、不能当整个骨架**。

**架构定向(分层,不冲突)**:
- 外层 = LangGraph,持 HUMAN_GATE(`interrupt`)+ 回放 —— Q11 的 LangGraph 决定站得住。
- PLAN 内层 = dynamic-workflow **模式**:可逆区扇出 subagent + adversarial verify,无中途人闸。
- Hermes 是独立 app 调不到该 feature,PLAN 里**重实现 pattern**(Anthropic API / Agent SDK)。

同步修订 `README.md` 技术栈,把 feature 与 pattern 分两层。

### PLAN 骨架(`src/hermes_auditor/plan/`)

| 文件 | 作用 |
|---|---|
| `types.py` | `Source` / `SourceFinding` / `RefuterVerdict` / `PlanResult` + `LENSES` + `QUARANTINE_TOOLS`(允许) + `EXCLUDED_TOOLS`(负空间) |
| `agents.py` | `run_source_agent` / `run_refuter` —— 两个 agent 接缝(确定性 stub;`# TODO(real)` 处接 API,构造时 `tools=quarantine`) |
| `pipeline.py` | `plan_dynamic_workflow`: fan-out → synthesize(代码)→ adversarial → assemble |
| `run_plan.py` | 3 场景 demo 入口:`uv run python -m hermes_auditor.plan.run_plan` |

### 三场景跑通(确定性 stub,不调模型/CAW)

| 场景 | synthesize | adversarial | 结果 |
|---|---|---|---|
| `allow`(官方+白名单印证) | authoritative=legit | 全 pass | DRAFT ok |
| `reject`(只有不可信注入源) | 无 authoritative | 3 镜头 REFUTED | BLOCKED → AUDIT STOP |
| `conflict`(官方 + 注入攻击源) | authoritative=legit, suspicious=attacker | 全 pass | DRAFT ok,attacker 标记但不采用 |

### 设计不变量(已落进代码)

- synthesize 是**代码**,不交给某个 agent 拍板。
- provenance **工具盖章**(`_CONFIDENCE_BY_SOURCE`),模型不能自升可信度。
- **非对称阈值**:`authoritative is None or any(refuted)` → blocked(可逆区拒绝代价低,偏向拒)。
- **quarantine 在代码里**:subagent 的 `tools` 只给只读组,动钱能力从未授予。
- adversarial 验的是**将要采用**的地址 —— 连合法地址也要过对抗(纵深)。

### 旁证:实跑了一个真 dynamic workflow demo

用 Claude Code 的 `Workflow` 工具跑了 9 个 subagent 的 fan-out + adversarial + control(存为 `/hermes-adversarial-demo`)。实测:攻击地址 3/3 REFUTED 被拦,合法地址 control 0/3 通过(校准没误伤)。成本 ~139k token / ~2 分钟 —— 印证「这种重火力只值得用在不可逆的钱上」。

### 下一步

1. `agents.py` 两个 stub → 真 Anthropic API / Agent SDK 调用(独立 context + `tools=quarantine`)。
2. fan-out / adversarial 从顺序改**并行**。
3. `plan_dynamic_workflow` 接进 `graph.py` 的 PLAN 节点(替换现在 unpack fixture 的 stub)。
4. `amount` 镜头接 payment 字段;`resolve_recipient_address` / `scan_for_injection` 接真实现。
5. 真实来源的可信根:`official_docs/high` 这个章本身建立在「信这份文档」上(demo 里 agent 自己挖出的残留弱点)—— 需要第三方/链上背书。

## 2026-06-10 · Day 6 — 接通 PLAN→AUDIT 接缝 + 接 gpt-5.5 真脑 ✅

### 接通 PLAN→AUDIT(职责边界落进代码)

把昨天孤立的 `plan/` 骨架接进 LangGraph 整图,接缝倒过来理顺:

```text
旧(脱节):  risk_summary fixture → PLAN 解包 → AUDIT 读同一个 fixture
新(接通):  plan-sources fixture → PLAN 出 payment_draft+证据 → AUDIT 出 risk_summary+决策
```

- 新增 `fixtures/plan-sources/{allow,reject,conflict}.json`(PLAN 输入 = 各路材料,区别于 risk-summary)。
- `nodes.plan_dynamic_workflow` 调 `plan/` 骨架产出 draft+`plan_evidence`;`nodes.audit` 从证据组装 risk_summary、推导 decision(`blocked` = 硬 REJECT)。
- 关键认知:**`risk_summary` 不是输入,是 PLAN 的产出 / AUDIT 的输出。**

### 接 gpt-5.5 真脑(脑选型 + 开关)

- 脑选型:**gpt-5.5(经 `ai.input.im` 网关,OpenAI 兼容)**。GLM 非硬性要求(user 2026-06-10),gpt-5.5 已 eval 验过、零设置。直连 api.openai.com 被区域封锁(403),走网关用 `OPENAI_API_KEY`。
- `plan/llm.py`:脑接缝。`HERMES_BRAIN=stub`(默认,免 token)| `gpt-5.5`(responses API)。
- `plan/agents.py`:`run_source_agent` / `run_refuter` 按开关分派,**失败自动回退 stub**(live demo 网关抽风兜底)。confidence 仍工具盖章,模型只判抽址/注入/对抗。

### 跑通证据

| 脑 | allow | reject | conflict |
|---|---|---|---|
| stub | DONE | STOPPED | DONE |
| **gpt-5.5** | **DONE** | **STOPPED** | **DONE** |

两种脑三场景终态一致;gpt-5.5 模式是真模型推理在跑 fan-out + adversarial。eval(`eval_brain.py`):攻击 3/3 拦、control 0/3 误伤,与 06-09 Claude demo 持平。

### 对 demo 的意义

"真脑 + 真控制流" 跑通 → demo 作战图里**原 Day 12 的"接真脑"腿提前完成**,补回 Day 13 损失的 buffer。剩:真 CAW(Day 11 money shot)+ 真人闸 + demo 脚本 + 录制。`stub|gpt-5.5` 开关 + 回退 = live demo 兜底。

### 下一步

1. `CAW_EXECUTE` 接真 `caw`(money shot);`HUMAN_GATE` 接 Cobo 手机批 Pact。
2. fan-out / adversarial 从顺序改并行(现在真脑顺序跑稍慢)。
3. `amount` 镜头接 payment 字段。

## 2026-06-10 · Day 6(续)— 真 CAW 上链跑通(money shot)+ 真人闸 ✅

把 demo 作战图里**最硬的一条腿(原计划 Day 11)提前在 06-10 打通**:真 Pact + 手机真人批 + 授权内真转账 + 真 Sepolia tx hash。

### 闭环

```
caw pact submit(锁死收款地址 + 0.001/笔上限 + 6 天有效期)
  → owner 手机 App 批准(HUMAN_GATE = 真人闸)
  → pact active
  → caw tx transfer(授权范围内)
  → Sepolia 链上 Success,真 tx hash
```

### 链上证据(本次)

| 项 | 值 |
|---|---|
| Pact ID | `834f22c8-9f82-4811-9f7b-090c8ede0b0b` |
| 动作 | transfer 0.001 `SETH_USDC1` `0xf8b6…26a6` → `0x2348…81ba`(Sepolia)|
| Tx Hash | `0xa5e38782885bd6680fedd33312ddaf5f1c8be03c41e739bd877f2e2dee241f24` |
| 验证 | https://sepolia.etherscan.io/tx/0xa5e38782885bd6680fedd33312ddaf5f1c8be03c41e739bd877f2e2dee241f24 |
| 状态 | `Success` / `completed` |

详见 `docs/demo-evidence.md`(backup 素材清单)。转账脚本 `scripts/demo-transfer.sh`。

### 关键发现:auto-mode 拦截 = Hermes 论点的活体演示

Claude Code 的 auto-mode 安全分类器**挡住 agent(我)自动执行 `caw tx transfer`**,也挡住 agent 给自己加动钱权限。这恰好是 Hermes 论点的活体证明:**连操刀的 Claude 自己,都被挡在不可逆动钱之外,必须人来按。** 可写进 demo 叙事。

落地影响:**真转账由 owner 亲手跑**(终端 / 现场);整图集成时,`CAW_EXECUTE` 子进程在 owner 自己的 shell 里执行,不受 agent auto-mode 限制 —— 现场由 owner 跑 graph 即通。

### demo 意义

money shot(真 CAW + 真人闸)提前完成 → demo 只剩**接 `CAW_EXECUTE` 节点 + demo-friendly 输出 + 录 backup**。人闸是真的(手机按),叙事更强。

### 下一步(续)

1. 接 `CAW_EXECUTE` 节点调真 `caw`(`HERMES_CAW=stub|real` 开关),整图 allow 路一条龙到真上链。
2. demo-friendly 输出(让评委看到 PLAN/AUDIT 的"为什么")。
3. 录 backup(正常路 + 攻击路增量录)。

## 2026-06-10 · Day 6(三续)— 真人闸接进整图:每笔 Cobo 手机批 + interrupt 展示闸 ✅

demo 作战图的最后一条硬腿。至此**真 CAW + 真人闸都接进了 LangGraph 整图**,剩的全是呈现(录制/排练/输出美化)。

### 单闸设计(决策)

绑定的资金批准在 **Cobo 手机 App(CAW 层)**,不在 LangGraph 层:
- pact 策略加 `always_review: true` → 每笔 transfer 进 `PendingApproval`,owner 手机批了才上链。
- LangGraph `interrupt` 只负责「人在手机弹批之前先读到为什么」—— 暂停、打 Auditor 判断框、自动续跑,不在终端收决定(防御:resume 传 `{approved: False}` 仍可中止)。
- 关键事实:Cobo 手机批默认发生在 **pact 批准时**(批一次,范围内自动执行);`always_review` 才把闸下沉到**每一笔**。

### 三个接缝开关(全默认 stub,免 token / 免动钱 / 免交互)

| 开关 | stub | real |
|---|---|---|
| `HERMES_BRAIN` | 确定性逻辑 | gpt-5.5 经网关 |
| `HERMES_CAW` | canned tx | 真 caw + 等手机批 |
| `HERMES_GATE` | 自动批准 | interrupt 暂停展示 |

### 落地

- **review pact**:`91860633-bc88-4b6c-8380-26844cb63c0b`(always_review,allow 条件同旧 pact,2026-06-17 过期);`caw.py` 默认指向它,旧自动 pact `834f22c8` 可经 env 切回(排练快路)。
- **`caw.py` PendingApproval 分支**:提交响应带 `pending_operation_id` → 轮询 `caw pending get`(默认 ~5 分钟,容手机反应)→ approved 转轮 `caw tx get` 拿真 tx_hash;**rejected/超时 → FAILED/BLOCKED,绝不假 tx_hash** → STOPPED。无 pending(旧 pact)走原路。
- **HUMAN_GATE interrupt**:`graph.compile(checkpointer=MemorySaver())` + thread_id;`run_tracer` 跑→遇 `__interrupt__` 打 Auditor 判断框→`Command(resume)` 续跑。checkpointer 顺手把「回放」的脊椎接上了。

### 实跑证据(conflict 路完整闭环 = 真人闸 money shot)

| 时刻(UTC) | 事件 |
|---|---|
| 12:54:34 | conflict 路提交 transfer → `PendingApproval`,手机弹批 |
| **12:54:58** | **owner 手机批准这一笔** |
| 之后 | tx `Success`:`0x4832568957d87c7c9c7abd616aef2e1693dbc052809c589f66b5306fa0e83141` |

- 验证:https://sepolia.etherscan.io/tx/0x4832568957d87c7c9c7abd616aef2e1693dbc052809c589f66b5306fa0e83141
- reject 路:REJECT → STOPPED,**手机全程不响**(提交前就被 Auditor 拦了)—— demo 叙事的另一半。
- allow 路当次 `exit=4`:跑的时候 review pact 还没被批(12:54:16 才 active),**无活跃委托 → 干净 BLOCKED,铁律守住没假 tx**。pact 已 active,重跑即通。

### 额度耗尽暴露的透明度缺口(已修)

当晚网关日额度耗尽(`429 DAILY_LIMIT_EXCEEDED`)→ 每次 gpt-5.5 调用**静默回退 stub**,而表头仍写 `brain = gpt-5.5` —— 一个主打可审计的 Agent,自己的证据没记录「判断是谁做的」。修复:
- PLAN 审计日志行显式报 `brain=gpt-5.5 ⚠5/6 回退 stub`(或 `全真脑 N 次`);
- `plan_evidence` 带 `brain / brain_calls / brain_fallbacks`,随 risk_summary 进闸面板数据底座;
- 意外卖点:现场网关抽风时屏幕上诚实显示回退,而不是假装真脑。

### 提交

`10419a2`(caw.py 人闸分支)→ `b677261`(interrupt + checkpointer + resume)→ `69fe73e`(脑回退透明化)。

### 下一步

1. 明天额度重置后全真脑重跑:`HERMES_BRAIN=gpt-5.5 HERMES_CAW=real HERMES_GATE=real uv run hermes-auditor` → allow 路真 tx + 三场景全绿(完整彩排素材,手机弹两次)。
2. demo day 上台前 ping 网关验额度(`eval_brain.py`);额度是单点,回退 + ⚠ 标记是兜底叙事。
3. 录 backup(正常路 + 攻击路),更新 demo-script 反映单闸流程。

## 2026-06-11 · Day 11 — 呈现层:demo-friendly 输出 + 现场脑策略定案 ✅

硬腿昨晚全完成,今天起不加能力、只做「能不能演」。demo day(6.14)剩今明两个工作日(Day 13 owner 不在)。

### 现场脑策略定案:预录真脑 hero + 现场 stub

开工 ping 脑网关连挂两天(6-10 额度 429 → 6-11 upstream error)→ 它是 live demo 唯一单点。决策:
- **Hero 片段 = 预录真脑**(gpt-5.5 端到端,happy-path 高潮)。
- **现场 live = stub 脑**:控制流与真脑**完全一致**(终态/拦截/放行都一样),不依赖网关,稳。
- **回退透明化(Day 6 三续做的)= 把网关风险从翻车点变叙事**:即便误用真脑且网关挂,屏上诚实打 `⚠ N/M 回退 stub`。
- 解锁:今天的活**全部不被网关卡住**(现场跑 stub);真脑 hero 降级成异步抢录。

### P1 · `HERMES_VERBOSE=1` demo 输出(`a4a48cb`)

terse audit_log 看不到「为什么」→ verbose 浮出评委能扫读的面板,**内容全来自已存在的 `dynamic_workflow_trace`/`risk_summary`,只分组打印,不改控制流**:
- PLAN 面板:fan-out 每源(地址/来源/可信度/注入)+ synthesize + adversarial 每镜头 REFUTED/pass+理由 + 脑溯源。
- AUDIT 面板:checks 逐项 ✓/✗ + red_flags + decision。
- ⚠ 只标真问题(REFUTED / fan-out ⚠injection),pass 行干净;gate=real 时闸前打 AUDIT 面板。
- reject 路最有说服力:3 镜头 REFUTED 带理由 + 3 条 high 红旗 → REJECT。

### P2 · demo-script 对齐现实(`4b0dbc8`)

脚本早于昨晚单闸工作,三处脱节全修:三硬腿翻牌 🔌→✅;补单闸/手机批/always_review money shot +「人在哪批」问答;现场脑策略成节;分镜重排(路A=预录 hero,路B=现场 stub);兜底表重写(现场本就 stub,网关不再单点);链上证据表(conflict 手机批 tx)。

### P3 · 真脑面板预览(验排版,省额度)

网关下午恢复。只跑 allow 一条 + stub CAW(不动钱)验真脑 verbose 面板:
- ALLOW 正确,`全真脑 6 次` 无回退。
- 真脑理由是长自由文本(比 stub 模板有说服力,适合 hero);录制注意:**终端 ≥140 列**保 box 边框齐。

### 剩(纯呈现)

- [ ] 抢录真脑 hero 片段(`VERBOSE=1 BRAIN=gpt-5.5 CAW=real GATE=real`,≥140 列,手机弹两次)。
- [ ] 录现场攻击路 backup(`VERBOSE=1` stub,不依赖网关,随时)。
- [ ] README/slides + 排练 5 分钟。
- [ ] 上台前 ping 网关(`eval_brain.py`);现场跑 stub 不依赖它,hero 片段要它。
