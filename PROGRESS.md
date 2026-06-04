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
| 人类审批闭环（手机批 Pact）| LangGraph 编排 + GLM-5.1 当脑 |
| 最小授权 policy（白名单 + 频率上限）| x402 / 采购场景包装 |
| 真 tx hash（hackathon 提交物之一）| golden set（5–6 regression cases）|

→ 今天通的是 **CAW 执行轨道 + 人类闸门**；差异化（Auditor）是坐在其上的下一段编码。

### 下一步

1. 建第二个 pact 演 **policy 拦截**（故意违反白名单 → CAW STOP），证明边界是真的。
2. 接 LangGraph 骨架 + GLM-5.1，把"Agent 自主准备 → Auditor 把关 → CAW 执行"串起来。
3. 设计 Auditor 的 risk summary 怎么喂进 Pact 审批（Auditor↔Pact 接缝）。
