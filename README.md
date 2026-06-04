# Hermes Auditor

> 长程可审计 Agent：自主跑可逆的准备工作，在不可逆的资金操作前由 Auditor 把关，经 Cobo Agentic Wallet 在测试网真实执行。

AI × Web3 Agentic Builders Hackathon 参赛项目（主攻 Cobo 赛道）。

## 定位

- **Cobo CAW** = 无法被越权的合规部门（policy 执行 / 审计 / 撤销），直接用，不重写。
- **Hermes Auditor** = 坐在 CAW 之上的分析师：语义正确性 + 输入侧防注入 + 可读 risk summary。

## 技术栈

- 编排：LangGraph（FSM + HUMAN GATE via `interrupt` + 回放 via `checkpointer`）
- Agent 脑：GLM-5.1（Z.AI General API）
- 资金执行：Cobo Agentic Wallet（CAW，测试网 Sepolia / Base Sepolia / Solana Devnet）

## 状态

🚧 Day 1 — 搭建中。设计文档见学习仓库 `ai-web3-school-cohort-0/hackathon/ideation.md`。
