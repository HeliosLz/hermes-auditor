# Demo 证据 / Backup 素材清单

> 服务 2026-06-14 现场 live demo。live demo 铁律:**手里永远有一条录好的真东西**。
> 这里汇总所有可放的真实证据 + 待录清单。

## ✅ 真 CAW 上链(money shot · 正常路)

| 项 | 值 |
|---|---|
| 日期 | 2026-06-10 |
| Pact ID | `834f22c8-9f82-4811-9f7b-090c8ede0b0b`(锁死收款地址 + 0.001/笔 + 6 天)|
| 动作 | transfer 0.001 `SETH_USDC1` → `0x23482606e068480f91cd7b1a6f775986a96081ba`(Sepolia)|
| Tx Hash | `0xa5e38782885bd6680fedd33312ddaf5f1c8be03c41e739bd877f2e2dee241f24` |
| Etherscan | https://sepolia.etherscan.io/tx/0xa5e38782885bd6680fedd33312ddaf5f1c8be03c41e739bd877f2e2dee241f24 |
| 状态 | `Success` · 人闸 = owner 手机批 pact |
| 复跑 | `bash scripts/demo-transfer.sh`(owner 终端执行;agent 被 auto-mode 挡,正好演"连 Claude 都不能自动动钱")|

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
| 整图 | `HERMES_BRAIN=gpt-5.5 uv run hermes-auditor`:reject→STOPPED(带每镜头理由)|

## ⬜ 待录 backup(增量,别押 Day 13)

- [ ] **正常路片段**:跑 allow 流程 → 手机批 → 真转账 → 打开 etherscan。屏录。
- [ ] **攻击路片段**:跑 reject/conflict → Auditor 三镜头 REFUTED 带理由 → STOPPED。屏录。
- [ ] **完整 backup**:两条路一气呵成(Day 11 晚 / Day 12 晚)。
- [ ] 录屏里演**手机实时批 pact**(亮点);现场 live 用预批 pact 求稳。

## 兜底切换

- 网关抽风 → `HERMES_BRAIN=stub`(控制流一样,理由变模板)。
- 真转账翻车 → 放上面录好的 backup 录屏 + etherscan 链接。
