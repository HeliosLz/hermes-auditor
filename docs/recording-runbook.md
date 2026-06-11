# Demo 录制 Runbook(backup 素材)

> 服务 2026-06-14 现场 live demo。目标:**今晚(Day 11)手里至少有一条录好的真东西**,Day 12 补完整,不押 Day 13。
> 策略(2026-06-11 定):**hero=预录真脑,现场 live=stub**。详见 `demo-script.md`、证据见 `demo-evidence.md`。

## 两条要录的片段

| # | 脚本 | 脑 | 依赖 | 看点 |
|---|---|---|---|---|
| ① 真脑 hero(正常路)| `bash scripts/record-hero.sh` | gpt-5.5 | 网关 + 真 CAW + 手机 | 真脑判断 → 手机批这一笔 → 真 tx → etherscan |
| ② 攻击路 | `bash scripts/record-attack.sh` | stub | 无(纯本地)| 三镜头 REFUTED+理由→STOPPED;conflict 挑出合法地址 |

> ② 不依赖网关,**随时可录、可反复重录**——今晚先把它录了,安全网到手。
> ① 要网关通 + 手机在手,趁网关恢复时抢录。

## 录 ① 真脑 hero 前的自检(脚本会自动跑,这里是清单)

- [ ] 终端拉宽 **≥140 列**(真脑理由长,窄了 box 边框断)。
- [ ] 脑网关通(`uv run python eval_brain.py` 或脚本内 ping;连挂两天,务必现验)。
- [ ] always_review pact `91860633` = `active`。
- [ ] token `SETH_USDC1` ≥ 0.002(allow+conflict 吃 2 笔);gas `SETH` ≥ 0.002。
      不足补:`caw faucet deposit --address 0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6 --token-id SETH_USDC1`(日上限留意)。
- [ ] 浏览器留一个 `sepolia.etherscan.io` 标签;手机解锁、Cobo App 待命。
- [ ] **手机会弹两次批准**(allow 一次、conflict 一次)——别以为卡住了,各批一次。

## 分镜旁白(① hero · 对应 5 分钟脚本的路 A)

1. **allow 起跑** → 屏上 PLAN 面板:"两个独立来源(官方 docs + 白名单)各自查证,都指向同一个地址,真脑读出无注入。"
2. **AUDIT 面板** → "Auditor 把证据组装成 risk_summary,5 项 check 全过,决策 ALLOW。"
3. **HUMAN_GATE 暂停** → "图停在这里,把判断推到我面前——我先看懂为什么,再批。"
4. **手机弹批** → "绑定的资金批准在 Cobo 手机上,我亲手批**这一笔**。"(批准)
5. **真 tx** → 切 etherscan,"链上确认,真钱真转。"
6. (conflict 同理,强调"官方源和注入源同时在,Auditor 挑出合法的、把攻击地址标记但不采用"——再批一次手机。)
7. **reject** → "这条没有权威来源、只有注入源,三镜头全 REFUTED,STOPPED,手机连响都不响——坏付款到不了我手上。"

## 分镜旁白(② 攻击路 · stub · 对应路 B)

- **reject 的 PLAN 面板**是主角:三镜头 `REFUTED` 各带理由(无权威来源/注入话术/不在 allowlist)+ 三条 high 红旗 → REJECT → STOPPED。
- **conflict** 收尾:证明不是"有可疑就全拒"——官方源在时,Auditor 挑出合法地址放行、把 attacker 标记不采用。
- 旁白点透:"现场这条跑的是 stub 脑,控制流和真脑**一模一样**,不依赖网关。真脑版在 hero 片段里。"

## 重录 / 翻车

- **②(stub)**:随便重录,无成本。
- **①(真脑)**:每个完整 take 吃 2 笔 token(allow+conflict)→ 录 2-3 个 take 后补币(见自检)。
- **网关录到一半挂**:屏上会显示 `⚠ N/M 回退 stub`——这条 take 作废(不是真脑了),网关恢复重录;但这个画面本身可留作"透明度"素材。
- **手机没收到推送**:`caw pending list` 看挂起的操作;CAW 轮询默认等 ~5 分钟,从容批。

## 录完

- tx hash 回填 `demo-evidence.md`(链上复核:`eth_getTransactionByHash`)。
- 片段存档;Day 12 把两条接成一条完整 backup。

---

> `scripts/demo-transfer.sh` 是**裸 caw 兜底**,不是录制脚本(旧 pact 不弹手机批 / 固定 request-id 撞幂等 / 绕过整图无 Auditor)。
