# Demo 录制 Runbook(backup 素材)

> 服务 2026-06-14 现场 live demo。目标:**今晚(Day 11)手里至少有一条录好的真东西**,Day 12 补完整,不押 Day 13。
> 策略(2026-06-11 定):**hero=预录真脑,现场 live=stub**。详见 `demo-script.md`、证据见 `demo-evidence.md`。

## 两条要录的片段

| # | 脚本 | 跑的场景 | 脑 | 依赖 | 看点 |
|---|---|---|---|---|---|
| ① 真脑 hero(自主采购)| `bash scripts/record-hero.sh` | `procurement` | gpt-5.5 | 网关 + 真 CAW + 手机 | 发现3候选→比价→审计拦下注入骗子→选官方→手机批1次→真 tx→etherscan |
| ② 攻击路 | `bash scripts/record-attack.sh` | `reject conflict` | stub | 无(纯本地)| 三镜头 REFUTED+理由→STOPPED;conflict 挑出合法地址 |

> ② 不依赖网关,**随时可录、可反复重录**——今晚先把它录了,安全网到手。
> ① 要网关通 + 手机在手,趁网关恢复时抢录。

## 录 ① 真脑 hero 前的自检(脚本会自动跑,这里是清单)

- [ ] 终端拉宽 **≥140 列**(真脑理由长,窄了 box 边框断)。
- [ ] 脑网关通(`uv run python eval_brain.py` 或脚本内 ping;连挂两天,务必现验)。
- [ ] always_review pact `91860633` = `active`。
- [ ] token `SETH_USDC1` ≥ 0.001(procurement 吃 1 笔);gas `SETH` ≥ 0.001。
      不足补:`caw faucet deposit --address 0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6 --token-id SETH_USDC1`(日上限留意)。
- [ ] 浏览器留一个 `sepolia.etherscan.io` 标签;手机解锁、Cobo App 待命。
- [ ] **手机会弹一次批准**(选中的官方 vendor)——别以为卡住了。

## 分镜旁白(① hero 自主采购 · 对应 5 分钟脚本的路 A)

1. **起跑** → 屏上**比价表**:"Agent 发现 3 个候选数据 API,自报价不同。最便宜的 CheapData 0.0008。"
2. **审计当闸** → "但 CheapData 的收款地址来自一个注入论坛帖——Auditor 来源预筛判它不可信,拦下。Agent 落到次便宜、且官方+白名单印证的 Demo Data API(0.001)。**审计是这笔采购的胜负手。**"
3. **AUDIT 面板** → "赢家跑完整对抗,5 项 check 全过,决策 ALLOW。"
4. **HUMAN_GATE 暂停** → "图停在这里,把判断推到我面前——我先看懂为什么,再批。"
5. **手机弹批** → "绑定的资金批准在 Cobo 手机上,我亲手批**这一笔**。"(批准)
6. **真 tx** → 切 etherscan,"链上确认,真钱真转给了对的 vendor。"

## 分镜旁白(② 攻击路 · stub · 对应路 B)

- **reject 的 PLAN 面板**是主角:三镜头 `REFUTED` 各带理由(无权威来源/注入话术/不在 allowlist)+ 三条 high 红旗 → REJECT → STOPPED。
- **conflict** 收尾:证明不是"有可疑就全拒"——官方源在时,Auditor 挑出合法地址放行、把 attacker 标记不采用。
- 旁白点透:"现场这条跑的是 stub 脑,控制流和真脑**一模一样**,不依赖网关。真脑版在 hero 片段里。"

## 重录 / 翻车

- **②(stub)**:随便重录,无成本。
- **①(真脑)**:每个完整 take 吃 1 笔 token(procurement 赢家)→ 录 4-5 个 take 后补币(见自检)。
- **网关录到一半挂**:屏上会显示 `⚠ N/M 回退 stub`——这条 take 作废(不是真脑了),网关恢复重录;但这个画面本身可留作"透明度"素材。
- **手机没收到推送**:`caw pending list` 看挂起的操作;CAW 轮询默认等 ~5 分钟,从容批。

## 录完

- tx hash 回填 `demo-evidence.md`(链上复核:`eth_getTransactionByHash`)。
- 片段存档;Day 12 把两条接成一条完整 backup。

---

> `scripts/demo-transfer.sh` 是**裸 caw 兜底**,不是录制脚本(旧 pact 不弹手机批 / 固定 request-id 撞幂等 / 绕过整图无 Auditor)。
