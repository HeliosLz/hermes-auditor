# Hermes Auditor

> 长程可审计 Agent：自主跑可逆的准备工作，在不可逆的资金操作前由 Auditor 把关，经 Cobo Agentic Wallet 在测试网真实执行。

AI × Web3 Agentic Builders Hackathon 参赛项目（主攻 Cobo 赛道）。

## 定位

- **Cobo CAW** = 无法被越权的合规部门（policy 执行 / 审计 / 撤销），直接用，不重写。
- **Hermes Auditor** = 坐在 CAW 之上的分析师：语义正确性 + 输入侧防注入 + 可读 risk summary。

## 技术栈

分两层编排，各归其层：

- **外层骨架 = LangGraph**：确定性 FSM，持有 HUMAN GATE（`interrupt`）+ 回放（`checkpointer`）。**人闸在这一层** —— 不可逆资金动作前必须中途真人签字。
- **PLAN 内层 = dynamic-workflow 模式**：在**可逆区**扇出 subagent 做发现 vendor / 起草 payment / adversarial 验证地址，只产出 `payment_draft`，**不碰 CAW、无中途人闸**。用 Anthropic API / Agent SDK 实现。
- **资金执行 = Cobo Agentic Wallet**（CAW，测试网 Sepolia / Base Sepolia / Solana Devnet）。

> 为什么人闸在 LangGraph、不在 dynamic workflow：Claude Code 的 [dynamic workflows](https://code.claude.com/docs/en/workflows) 明确**不支持中途人输入**（"No mid-run user input … run each stage as its own workflow"），而 Hermes 的命根正是不可逆动作前的真人签字。故 **人闸归 LangGraph，扇出规划归 PLAN 可逆区**。Hermes 作为独立 app 调不到 Claude Code 该 feature，PLAN 里重实现其 pattern（fan-out + adversarial verify），并用 quarantine —— 给读不可信内容的 subagent 一个不含动钱工具的 allowlist。

## 状态

- ✅ Day 1（2026-06-04）— CAW 接入 + 首笔测试网交易跑通（带真人审批）。
- ✅ Day 2（2026-06-06）— CAW policy 拦截跑通：错误收款地址被 `ADDRESS_NOT_WHITELISTED` 拒绝，未广播链上交易。
- ✅ Day 3（2026-06-07）— `risk_summary` schema + fixtures 入项目。
- ✅ Day 4（2026-06-08）— LangGraph tracer bullet 跑通：5 stub 节点 + 两条 fixture run 分别到 `DONE` / `STOPPED`，不接模型/CAW。
- ✅ Day 5（2026-06-09）— 概念纠偏（dynamic workflow 分层）+ PLAN 可逆区骨架（`plan/`：fan-out + adversarial，allow/reject/conflict 三场景跑通，stub）。

## 运行

```bash
uv run hermes-auditor
```

跑两条 fixture 驱动的 run，打印各自的 `audit_log` 和终态：

- `allow-normal-payment` → `PLAN_DYNAMIC_WORKFLOW → AUDIT(ALLOW) → HUMAN_GATE → CAW_EXECUTE → DONE`
- `reject-wrong-recipient` → `PLAN_DYNAMIC_WORKFLOW → AUDIT(REJECT) → STOPPED`

第一版只证明控制流：不调用 Claude，不调用 CAW。`CAW_EXECUTE` 用 2026-06-04 的测试网 tx hash 做 stub，`HUMAN_GATE` 用本地 auto-approval 做 stub。

进度见 [PROGRESS.md](./PROGRESS.md)。
LangGraph 骨架见 [docs/langgraph-skeleton.md](./docs/langgraph-skeleton.md)。
设计文档见学习仓库 `ai-web3-school-cohort-0/hackathon/ideation.md`。
