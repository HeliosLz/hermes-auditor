# LangGraph 骨架

> 2026-06-07 学习笔记。目标：在加入更复杂的规划逻辑前，先把 Hermes Auditor 的工作流变成一张显式、可回放的状态机。

## 核心原则

LangGraph 是确定性的流程骨架，不是智能层。

Claude Dynamic Workflow 可以帮助处理可逆规划：发现候选 vendor、比较选项、草拟 payment proposal，以及在检查失败后修正方案。

Claude Dynamic Workflow 不能直接执行 CAW 动作。任何不可逆的资金路径都必须经过：

```text
AUDIT -> HUMAN_GATE -> CAW_EXECUTE
```

因此，安全边界是结构性的：

```text
Claude Dynamic Workflow 提出方案。
Auditor 检查并生成摘要。
Human 批准。
CAW 强制执行。
LangGraph 记录流程走到哪一步，以及为什么走到这里。
```

## 最小图

```text
START
  -> PLAN_DYNAMIC_WORKFLOW
  -> AUDIT
  -> HUMAN_GATE
  -> CAW_EXECUTE
  -> DONE

AUDIT -> STOPPED
HUMAN_GATE -> STOPPED
CAW_EXECUTE -> STOPPED
```

## 状态形状

第一条 tracer bullet 只需要足够的状态来证明流程可恢复、可审计。

| 字段 | 作用 |
|---|---|
| `run_id` | 一次 procurement/payment 尝试的稳定身份。 |
| `user_intent` | 用户原始目标和预算。 |
| `dynamic_workflow_trace` | Claude 提出的可逆规划步骤。 |
| `candidate_vendor` | 选中的 vendor/API/service 候选项。 |
| `payment_draft` | chain、token、amount、recipient、budget 和来源证据。 |
| `risk_summary` | 符合 `schemas/risk-summary.schema.json` 的对象。 |
| `audit_decision` | `ALLOW`、`STOP_AND_REVIEW` 或 `REJECT`。 |
| `human_confirmation` | 用户对这份精确 summary/payment 对象的批准记录。 |
| `caw_result` | CAW 执行结果、tx hash，或 enforced STOP 细节。 |
| `error` | 最近一次可恢复错误，如果有。 |
| `audit_log` | node 输入、输出和决策的 append-only 记录。 |

## 节点契约

### `PLAN_DYNAMIC_WORKFLOW`

输入：

- `user_intent`
- 可选的上一轮 `error`
- 可选的上一轮 `audit_decision`

输出：

- `dynamic_workflow_trace`
- `candidate_vendor`
- `payment_draft`

规则：

- 可以调用 Claude 拆解和修正可逆准备步骤。
- 不可以调用 CAW。
- 不可以把 payment 标记为已批准。
- 必须输出结构化字段，供 Auditor 检查。

### `AUDIT`

输入：

- `user_intent`
- `candidate_vendor`
- `payment_draft`
- pact policy draft 或已知 CAW policy

输出：

- `risk_summary`
- `audit_decision`

规则：

- 必须校验 recipient、amount、token、chain、budget、policy match 和 source confidence。
- 如果任何绑定字段变化，本轮不能复用旧 confirmation。
- `REJECT` 直接进入 `STOPPED`。
- `STOP_AND_REVIEW` 仍可进入 `HUMAN_GATE`，但 summary 必须清楚展示风险。

### `HUMAN_GATE`

输入：

- `risk_summary`
- `audit_decision`

输出：

- `human_confirmation`

规则：

- 必须在 CAW 执行前暂停。
- confirmation 必须绑定到精确的 `summary_id`、payment fields、policy fields 和 summary hash。
- 任何字段变化，都需要重新生成 risk summary，并重新确认。

### `CAW_EXECUTE`

输入：

- `human_confirmation`
- `payment_draft`
- `pact_policy`

输出：

- `caw_result`

规则：

- 只能在 human confirmation 之后执行。
- 必须记录成功 tx hash 或 CAW enforced STOP。
- 必须区分参数错误和 policy denial。

## 第一条 Tracer Bullet

先使用已有 fixtures。不要先调用模型，也不要先调用 CAW。

1. 读取 `fixtures/risk-summary/allow-normal-payment.json`。
2. 路由经过 `AUDIT -> HUMAN_GATE -> CAW_EXECUTE`。
3. 把 `HUMAN_GATE` stub 成一个本地 approval object。
4. 把 `CAW_EXECUTE` stub 成 2026-06-04 tx hash 代表的成功记录。
5. 读取 `fixtures/risk-summary/reject-wrong-recipient.json`。
6. 路由经过 `AUDIT -> STOPPED`。

第一版可运行 graph 要证明的是控制流，不是智能。

## 非目标

- 不做 UI。
- 还不接 x402 integration。
- 不允许 Claude 执行 CAW tools。
- 不增加第二层框架。
- 状态机跑通前，不优化 prompt。

## 下一步编码

创建最小可行 graph 实现：

```text
state schema
  + five stub nodes
  + two fixture-driven runs
  + printed audit log
```

跑通之后，只替换 `PLAN_DYNAMIC_WORKFLOW` 为 Claude 调用。图里的其他节点不应该关心 payment draft 是哪个模型生成的。
