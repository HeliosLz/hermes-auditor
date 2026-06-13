# Demo 证据 / Backup 素材清单

> 服务 2026-06-14 现场 live demo。live demo 铁律:**手里永远有一条录好的真东西**。
> 这里汇总所有可放的真实证据 + 待录清单。
> 链上确认:下列 tx 均经 Sepolia RPC `eth_getTransactionByHash` 核过,真实存活(2026-06-11 复核)。

## ✅ 头条:真人闸 · **每笔手机批**(单闸 money shot · 2026-06-10 晚)

这是最强的一条:owner 不是批一次授权后任其自动跑,而是**亲手批准「这一笔」付款**——pact 带 `always_review`,每笔 transfer 都进 owner 手机审批,批了才上链。

| 项 | 值 |
|---|---|
| 日期 | 2026-06-10 晚 |
| Pact ID | `91860633-bc88-4b6c-8380-26844cb63c0b`(`always_review` · 锁死收款地址 + 0.001/笔)|
| 流程 | 整图 PLAN→AUDIT→HUMAN_GATE(interrupt 展示判断)→ CAW 提交 → **`PendingApproval` → owner 手机批这一笔** → 上链 |
| 路 | conflict(官方源+注入源同在 → Auditor 挑出合法地址 → ALLOW)|
| Tx Hash | `0x4832568957d87c7c9c7abd616aef2e1693dbc052809c589f66b5306fa0e83141` |
| Etherscan | https://sepolia.etherscan.io/tx/0x4832568957d87c7c9c7abd616aef2e1693dbc052809c589f66b5306fa0e83141 |
| 状态 | `Success` · **人闸 = owner 手机批「这一笔」**(非 pact 级一次性授权)|
| 时间线 | 提交 12:54:34 → 手机弹批 → owner 12:54:58 批准 → 上链 `Success` |
| 复跑 | `HERMES_CAW=real HERMES_GATE=real uv run hermes-auditor all`(owner 终端;allow+conflict 各弹一次手机批)|

> **叙事要点**:pact 级手机批(下方旧 pact)= 批一次授权、范围内自动执行;**单闸每笔手机批 = 每一笔不可逆付款都过 owner 的手**。后者才是 demo 该讲的故事——评委更买"每笔过人手"。

## ✅ 端到端:自然语言 → 升级 pact → 双闸 → DONE(2026-06-13)

一句中文驱动整图,超预算时**当场提案新 pact 让 owner 手机批**,再经终端确认 + 转账手机批两道闸真上链。这条把"意图来自对话 / 策略与资金授权来自带外手机"演全了。

| 项 | 值 |
|---|---|
| 日期 | 2026-06-13 |
| 入口 | `HERMES_BRAIN=gpt-5.5 HERMES_CAW=real HERMES_DISCOVERY=web uv run hermes-auditor` → 输入「我想采购一个链上数据 API,预算 10」|
| 升级 pact | `1b9c173f-b002-4ce5-9809-143ac7e454c8`(预算 10 超原上限 0.01 → 提案新 pact,**手机批①** 升预算;地址 allowlist 未放宽、单笔仍 `always_review`)|
| 三道闸 | 手机批①(升 pact)→ 终端 `y` 确认这笔 → **手机批②**(绑定这一笔转账)→ 上链 |
| 实付 | 0.001 `SETH_USDC1` → `0x23482606e068480f91cd7b1a6f775986a96081ba`(预算升到 10 但仍只付赢家报价 0.001 —— 唯一有权威地址的可信候选)|
| Tx Hash | `0x36ee84167a3400aa3ebb9aaeee6b9ac26a7cda63d9832d48cf7a81647eeeae32` |
| Etherscan | https://sepolia.etherscan.io/tx/0x36ee84167a3400aa3ebb9aaeee6b9ac26a7cda63d9832d48cf7a81647eeeae32 |
| 状态 | `Success/completed` · 终态 DONE(request_id `run_ask_001-e51d00f4`)|
| 时间线 | 提交 02:55:31 → 手机批 → 上链 `Success` 02:56:25 |

> **叙事要点**:① 预算只能由 owner 手机批准放宽,一句话(或注入)改不了策略;② 即便额度升到 10,agent 仍只把钱打给地址有权威背书的赢家(0.001),全网搜来的便宜货因无可信地址全部落选 —— "拿到更高额度也不乱花"。
>
> **可审计血统**:同一条路径早一轮(tx `0x615c4156bc41d6287f646bc6065c9f56d4bf5da2839c7e5b3d93fcc32dcbe0a5`)曾因 pending 状态走到文档未列的 `executed` 被误判超时 STOPPED——而钱已上链。修法:不可逆动作的成败只认链上 `caw tx get` 终态、不赌中间态机措辞。两笔 tx 都在 Sepolia 存活,可现场对比"误判 vs 修复"。

## ✅ 授权级手机批 + 整图一条龙(2026-06-10 · 旧自动 pact)

旧 pact `834f22c8…`:owner 手机批准 **pact 本身**(锁死收款地址 + 0.001/笔 + 6 天),之后范围内 transfer **自动执行**。仍是有效证据(演"最小授权"),但人闸在授权级、非每笔。

| 项 | 值 |
|---|---|
| Pact ID | `834f22c8-9f82-4811-9f7b-090c8ede0b0b` |
| 动作 | transfer 0.001 `SETH_USDC1` → `0x23482606e068480f91cd7b1a6f775986a96081ba`(Sepolia)|
| 首跑 Tx | `0xa5e38782885bd6680fedd33312ddaf5f1c8be03c41e739bd877f2e2dee241f24`(`Success`)|
| 复跑 | `bash scripts/demo-transfer.sh`(owner 终端;agent 被 auto-mode 挡,正好演"连 Claude 都不能自动动钱")|

### 整图一条龙真上链(全图驱动,同 `834f22c8` 内)

`HERMES_CAW=real uv run hermes-auditor all` —— 由 PLAN→AUDIT→HUMAN_GATE→CAW_EXECUTE **全图驱动**真转账(不再是独立 caw 脚本)。

| 路 | 终态 | Tx Hash |
|---|---|---|
| allow | DONE · `Success/completed` | `0xede4802102be51a4ea00bdfaabd6cb48f17c8ae20b8ddaa676582413791d8b43` |
| conflict | DONE · `Success/completed` | `0xb2a3958226595bd3db3eadb1522efdc6a73e072c4aa567904e6935a861556287` |
| reject | STOPPED · 无 tx | PLAN blocked → AUDIT REJECT,根本不到 CAW |

> **铁律实测**:同批次首轮 agent 钱包 gas 见底 → caw 终态 `Failed` → 节点如实 `FAILED→STOPPED`、**不假装成功 / 无假 tx hash**;补 gas 后才 `Success→DONE`。钱这条**没有 stub fallback**(脑可回退,钱不行)。
> gas 补给走 caw 自带水龙头:`caw faucet deposit --address <agent钱包> --token-id SETH`(每次 0.01,日上限 0.02)。

### 历史 CAW 证据(设计血统)

| 日期 | 证据 | Tx / 结果 |
|---|---|---|
| 2026-06-04 | 首笔测试网转账(带手机批)| Tx `0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726` |
| 2026-06-06 | CAW policy 拦截(错误地址)| `ADDRESS_NOT_WHITELISTED`,无 tx(broadcast 前拒)|

> 6.06 这条是攻击路的**最后一道硬边界**证据;Auditor 是上游第一道带原因的拦截 → 纵深防御。

## ✅ 对抗验证(攻击路 · Auditor 抓注入)

| 项 | 值 |
|---|---|
| 日期 | 2026-06-09 / 06-10 |
| 工具 | `eval_brain.py`(gpt-5.5)+ 06-09 Claude 9-subagent workflow |
| 结果 | 攻击地址 **3/3 REFUTED**、合法地址 control **0/3 误伤** |
| 整图 | `HERMES_BRAIN=gpt-5.5 uv run hermes-auditor all`:reject→STOPPED(带每镜头理由)|

## ⬜ 待录 backup(增量,别押 Day 13)

> 现场脑策略(2026-06-11 定):**hero=预录真脑,现场 live=stub**。攻击路 backup 不依赖网关,随时可录。
> 录制前全程开 `HERMES_VERBOSE=1`,让评委看到 PLAN 调查 + AUDIT 研判的「为什么」。

- [ ] **真脑 hero 片段**(正常路):`HERMES_VERBOSE=1 HERMES_BRAIN=gpt-5.5 HERMES_CAW=real HERMES_GATE=real uv run hermes-auditor all`
      → allow:真脑面板 → 手机弹批这一笔 → 真转账 → 打开 etherscan。**终端拉宽 ≥140 列**(真脑理由长,保 box 边框齐)。
- [ ] **攻击路片段**(stub,不依赖网关):`HERMES_VERBOSE=1 uv run hermes-auditor all`
      → reject:三镜头 REFUTED 带理由 + 三红旗 → STOPPED;conflict:挑出合法地址、标记 attacker → ALLOW。
- [ ] **完整 backup**:两条路一气呵成(Day 11 晚 / Day 12 晚,Day 13 不押)。
- [ ] 录屏里演**手机实时批「这一笔」**(单闸亮点,比批 pact 更强);现场 live 用 stub 求稳。

### 录制前提自检(2026-06-11 复核 · ✅ 已通)

| 项 | 状态 |
|---|---|
| always_review pact `91860633` | `active` |
| gas `SETH` | 0.0188(够多笔)|
| token `SETH_USDC1` | 0.005 ≈ **5 笔**;hero 一次吃 2 笔(allow+conflict)→ 反复重录 2-3 个 take 后补:`caw faucet deposit --address <agent钱包> --token-id SETH_USDC1` |
| 脑网关 | 不稳(连挂两天)→ hero 趁通时抢录;现场跑 stub 不依赖它 |

## 兜底切换

- 网关抽风 → 现场本就跑 `HERMES_BRAIN=stub`(控制流一样,理由变模板);误用真脑挂了 → 屏上 `⚠ 回退 stub` 是诚实叙事。
- 真转账翻车 / 手机批延迟 → 放预录 hero 录屏 + etherscan 链接;现场 live 只演攻击路(stub,纯本地,秒出)。
