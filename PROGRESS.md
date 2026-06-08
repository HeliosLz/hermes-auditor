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
