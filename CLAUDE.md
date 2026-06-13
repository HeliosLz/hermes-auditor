# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目

Hermes Auditor — 长程可审计 Agent（AI × Web3 Hackathon，Cobo 赛道）：自主跑可逆的准备工作（PLAN），在不可逆资金操作前由 Auditor + 真人闸把关，经 Cobo Agentic Wallet (CAW) 在测试网真实执行。Python ≥3.12，uv 管理依赖。注释/文档以中文为主，保持一致。

## 常用命令

```bash
uv run hermes-auditor all                   # 跑全部 5 场景（全 stub：免 token / 免动钱 / 免交互）。管道/CI 里无参数同义
uv run hermes-auditor                       # 终端无参数 = REPL 交互模式（每句话一条独立 run；场景名照样跑回归）
uv run hermes-auditor discovery             # 只跑指定场景（discovery|procurement|allow|reject|conflict）
uv run hermes-auditor "采购…预算 0.005"      # 自然语言驱动：非场景名参数整句当 intent，信任锚来自配置（build_ask_input）
HERMES_VERBOSE=1 uv run hermes-auditor      # demo 模式：浮出 PLAN/DISCOVERY/AUDIT 面板（不改控制流）
HERMES_BRAIN=gpt-5.5 uv run hermes-auditor  # 真脑（经 ai.input.im 网关，需 OPENAI_API_KEY）
uv run python eval_brain.py                 # 评估 gpt-5.5 当 agent 脑（注入识别/对抗否决）
```

没有测试套件——回归方式就是跑全部 5 场景，核对每条 run 的 `audit_log` 和终态（allow/procurement/discovery → DONE；reject → STOPPED；conflict → 标记 attacker 后 DONE）。

## 三个接缝开关（环境变量，默认全 stub）

| 变量 | 值 | 含义 |
|---|---|---|
| `HERMES_BRAIN` | `stub` \| `gpt-5.5` | agent 脑（`plan/llm.py`）。真脑失败**自动回退 stub**，并打 `FALLBACK_MARK` 进证据（回退不静默） |
| `HERMES_CAW` | `stub` \| `real` | 上链执行（`caw.py`）。**钱不能假装成功**：real 任何失败/超时 → BLOCKED/FAILED，绝不返回假 tx_hash |
| `HERMES_GATE` | `stub` \| `real` | 人闸（`nodes.py`）。real 用 LangGraph `interrupt` 真暂停 |
| `HERMES_DISCOVERY` | `staged` \| `web` | discovery 语料（`plan/websearch.py`）。web 模式只换 `web_untrusted` facet 为实时全网搜索（gpt-5.5 服务端 `web_search`，本地零出网）；registry/official 永远走 staged（权威来源不上公网）。失败回退 staged 并留痕 |

约束：`HERMES_CAW=real`（`caw tx transfer` 动真钱 + Cobo 手机批）只由 owner 在自己终端跑；agent 开发/测试一律用 stub。

## 架构

两层编排，人闸归属是核心设计决策：

- **外层 = LangGraph 确定性 FSM**（`graph.py`）：`START → PLAN_DYNAMIC_WORKFLOW → AUDIT → HUMAN_GATE → CAW_EXECUTE → DONE`，各节点失败路由到 `STOPPED`。控制流由节点写入 state 字段驱动（"风险判断变成控制流"）。HUMAN_GATE 的 `interrupt` 需要 checkpointer（`run_tracer.py` 传 MemorySaver + thread_id）。
- **内层 = PLAN 可逆区**（`plan/`）：dynamic-workflow 模式——确定性脚本编排（`pipeline.py`），模型只在接缝干活（`agents.py`）。流程：fan-out（每源一个独立 subagent）→ synthesize（**代码层**比对权威地址，不让 agent 拍板）→ adversarial refuter（多镜头反驳候选地址）→ assemble `payment_draft`。`discovery.py` 在 pipeline 前面加"发现候选 vendor"层（facets 输入自动分流）。PLAN 只产出 draft + evidence + trace，**不碰 CAW、无中途人闸**。

关键不变量（改代码时不要破坏）：

- **Quarantine**：读不可信内容的 subagent 不给任何工具（纯文本推理），动钱能力从未授予。
- **Provenance 由代码盖章**：confidence 来自 source_type，模型不能自升权威性；权威来源 = `official_docs | registry | user_input`（`pipeline.py`）。
- **可审计**：所有判断写进 `dynamic_workflow_trace` / `plan_evidence` / `audit_log`；脑回退、注入标记都要浮出，不能静默。

数据流接缝：`fixtures/plan-sources/*.json`（场景输入，`fixtures_io.py` 加载）→ PLAN 出事实+证据 → AUDIT 出 `risk_summary`（schema 见 `schemas/risk-summary.schema.json`，示例 fixtures 在 `fixtures/risk-summary/`）→ 决策驱动路由。场景登记表在 `run_tracer.py` 的 `_SCENARIOS`（场景名与 fixture 文件名解耦）。

## 文档

- `PROGRESS.md` — 逐日进度（改完功能记得更新）
- `docs/langgraph-skeleton.md` — 图结构设计
- `docs/demo-script.md` / `docs/recording-runbook.md` — demo 录制脚本（与 `scripts/record-*.sh` 对齐，改 run_tracer 输出时需同步）
