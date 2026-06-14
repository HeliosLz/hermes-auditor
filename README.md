# Hermes Auditor

> 长程可审计 Agent：自主跑可逆的准备工作，在不可逆的资金操作前由 Auditor 把关，经 Cobo Agentic Wallet 在测试网真实执行。

AI × Web3 Agentic Builders Hackathon 参赛项目（主攻 Cobo 赛道）。

## 定位

- **Cobo CAW** = 无法被越权的合规部门（policy 执行 / 审计 / 撤销），直接用，不重写。
- **Hermes Auditor** = 坐在 CAW 之上的分析师：语义正确性 + 输入侧防注入 + 可读 risk summary。

## 技术栈

分两层编排，各归其层：

- **外层骨架 = LangGraph**：确定性 FSM，持有 HUMAN GATE（`interrupt`）+ 回放（`checkpointer`）。**人闸在这一层** —— 不可逆资金动作前必须中途真人签字。
- **PLAN 内层 = dynamic-workflow 模式**：在**可逆区**扇出 subagent 做发现 vendor / 起草 payment / adversarial 验证地址，只产出 `payment_draft`，**不碰 CAW、无中途人闸**。脑 = **gpt-5.5（经网关，OpenAI 兼容 responses API）**；`HERMES_BRAIN=stub|gpt-5.5` 开关,失败回退 stub。
- **资金执行 = Cobo Agentic Wallet**（CAW，测试网 Sepolia / Base Sepolia / Solana Devnet）。

> 为什么人闸在 LangGraph、不在 dynamic workflow：Claude Code 的 [dynamic workflows](https://code.claude.com/docs/en/workflows) 明确**不支持中途人输入**（"No mid-run user input … run each stage as its own workflow"），而 Hermes 的命根正是不可逆动作前的真人签字。故 **人闸归 LangGraph，扇出规划归 PLAN 可逆区**。Hermes 作为独立 app 调不到 Claude Code 该 feature，PLAN 里重实现其 pattern（fan-out + adversarial verify），并用 quarantine —— 给读不可信内容的 subagent 一个不含动钱工具的 allowlist。

## 状态

- ✅ Day 1（2026-06-04）— CAW 接入 + 首笔测试网交易跑通（带真人审批）。
- ✅ Day 2（2026-06-06）— CAW policy 拦截跑通：错误收款地址被 `ADDRESS_NOT_WHITELISTED` 拒绝，未广播链上交易。
- ✅ Day 3（2026-06-07）— `risk_summary` schema + fixtures 入项目。
- ✅ Day 4（2026-06-08）— LangGraph tracer bullet 跑通：5 stub 节点 + 两条 fixture run 分别到 `DONE` / `STOPPED`，不接模型/CAW。
- ✅ Day 5（2026-06-09）— 概念纠偏（dynamic workflow 分层）+ PLAN 可逆区骨架（`plan/`：fan-out + adversarial，allow/reject/conflict 三场景跑通，stub）。
- ✅ Day 6（2026-06-10）— 接通 PLAN→AUDIT 接缝（PLAN 出事实+证据 / AUDIT 出 risk_summary+决策）+ 接 gpt-5.5 大模型（`stub|gpt-5.5` 开关 + 失败回退），整图三场景大模型跑通。

## 运行

```bash
uv run hermes-auditor                          # 交互模式：直接说想采购什么(有 OPENAI_API_KEY 时默认大模型+真全网搜索+面板)
uv run hermes-auditor all                      # 全量回归 5 场景（stub 脑，确定性，免 token）
HERMES_BRAIN=gpt-5.5 uv run hermes-auditor all # 大模型（gpt-5.5）
```

跑三条 PLAN-source 驱动的 run（整图 `PLAN → AUDIT → HUMAN_GATE → CAW_EXECUTE`），打印 `audit_log` 和终态：

- `allow`（官方+白名单印证）→ `AUDIT(ALLOW) → HUMAN_GATE → CAW_EXECUTE → DONE`
- `reject`（只有不可信注入源，无权威）→ `AUDIT(REJECT) → STOPPED`
- `conflict`（官方 + 注入攻击源）→ 挑出 legit、标记 attacker → `AUDIT(ALLOW) → DONE`

脑接缝 `plan/llm.py`：`HERMES_BRAIN=stub`（默认，免 token）| `gpt-5.5`（大模型，经 OpenAI 兼容网关）；大模型调用失败自动回退 stub（live demo 兜底）。

discovery 接缝 `plan/websearch.py`：`HERMES_DISCOVERY=staged`（默认，零网络）| `web`（真全网搜索：web facet 语料换成 gpt-5.5 服务端 `web_search` 拉回的实时报价，本地零出网；registry/official 仍走 staged —— 权威来源不上公网，收款地址永远不能只凭网页确立）。失败回退 staged 并留痕。

```bash
HERMES_DISCOVERY=web HERMES_BRAIN=gpt-5.5 HERMES_VERBOSE=1 uv run hermes-auditor discovery   # 真全网比价(staged 场景)
HERMES_DISCOVERY=web HERMES_BRAIN=gpt-5.5 HERMES_VERBOSE=1 \
  uv run hermes-auditor "我想采购一个链上数据 API,预算 0.005"                                  # 自然语言驱动整图
```

自然语言入口:参数命中场景名跑回归,否则整句当用户的话。用户的话只提供 intent + 预算(预算与 pact 上限取较小者 —— 能收紧不能放宽);信任锚(`pact_allowlist`、registry/official 语料)从 curated 配置加载,不接受运行时改写。「想要什么」是不可信输入,「钱能打给谁」是预先固化的策略,两者永远不在同一通道。

嫌前缀长可以装成全局命令或加 alias:

```bash
uv tool install --editable .        # 之后直接: hermes-auditor "采购一个数据 API"
# 或 alias hermes='uv run --project <仓库路径> hermes-auditor'
```

`CAW_EXECUTE` / `HUMAN_GATE` 默认仍 stub（`HERMES_CAW=real` / `HERMES_GATE=real` 由 owner 终端开）。

进度见 [PROGRESS.md](./PROGRESS.md)。
LangGraph 骨架见 [docs/langgraph-skeleton.md](./docs/langgraph-skeleton.md)。
设计文档见学习仓库 `ai-web3-school-cohort-0/hackathon/ideation.md`。
