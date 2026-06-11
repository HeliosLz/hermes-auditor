#!/usr/bin/env bash
# Hermes demo · 录制脚本 ①:真脑 hero 片段(正常路 money shot)
#
# 跑整图 PLAN→AUDIT→HUMAN_GATE→CAW_EXECUTE,真脑 + 真上链 + 单闸每笔手机批。
# 必须在 owner 自己的终端跑(agent 被 auto-mode 挡;手机批也得真人)。
#
#   bash scripts/record-hero.sh
#
# hero = 采购场景(procurement):发现 3 候选 → 比价 → 审计拦下最便宜的注入骗子 →
#        选官方 vendor → 手机批**一次** → 真上链。一笔交易,一次手机批。

set -u
CAW=/Users/gffive/.local/bin/caw
PACT=91860633-bc88-4b6c-8380-26844cb63c0b   # always_review:每笔进 owner 手机审批
cd "$(dirname "$0")/.." || exit 1

echo "═══════════════════════════════════════════════════════"
echo " Hermes 录制 ① · 真脑 hero(正常路 · 真上链 · 单闸手机批)"
echo "═══════════════════════════════════════════════════════"

warn=0

# 1) 终端宽度(真脑理由长,<140 列 box 边框会断)
cols=$(tput cols 2>/dev/null || echo 0)
if [ "$cols" -ge 140 ]; then echo "  ✅ 终端宽度 $cols 列(≥140)"
else echo "  ⚠️  终端宽度 $cols 列 < 140 → 真脑长理由会换行、box 边框断。拉宽窗口再录。"; warn=1; fi

# 2) 脑网关(hero 要真脑;挂了会静默回退 stub,hero 就不是真脑了)
if uv run python -c "from hermes_auditor.plan import llm; llm.complete_json('只输出 JSON: {\"ok\":true}','ping')" >/dev/null 2>&1; then
  echo "  ✅ 脑网关 gpt-5.5 可用"
else
  echo "  ⚠️  脑网关不可用 → 会回退 stub(屏上会显示 ⚠ 回退,但 hero 就不是真脑了)。等网关恢复再录。"; warn=1
fi

# 3) pact active + 钱包余额(token 够 2 笔:allow+conflict)
$CAW status >/dev/null 2>&1 && $CAW pact show --pact-id "$PACT" 2>/dev/null | python3 -c "
import sys,json
d=json.load(sys.stdin)
print('  ✅ pact active' if d.get('status')=='active' else '  ⚠️  pact 非 active: '+str(d.get('status')))
" || echo "  ⚠️  caw 状态/pact 读取失败,检查登录态"

$CAW wallet balance 2>/dev/null | python3 -c "
import sys,json
def walk(x):
    o=[]
    if isinstance(x,dict):
        if ('token_id' in x or 'token' in x) and any(k in x for k in('balance','amount','value')): o.append(x)
        for v in x.values(): o+=walk(v)
    elif isinstance(x,list):
        for v in x: o+=walk(v)
    return o
bals={ (b.get('token_id') or b.get('token')): float(b.get('balance') or b.get('amount') or b.get('value') or 0) for b in walk(json.load(sys.stdin)) }
usdc=bals.get('SETH_USDC1',0); seth=bals.get('SETH',0)
print(f'  {\"✅\" if usdc>=0.001 else \"⚠️ \"} token SETH_USDC1 = {usdc} (hero 吃 1 笔=0.001;不足补:caw faucet deposit --token-id SETH_USDC1)')
print(f'  {\"✅\" if seth>=0.001 else \"⚠️ \"} gas   SETH       = {seth}')
" 2>/dev/null || echo "  ⚠️  余额读取失败"

echo "───────────────────────────────────────────────────────"
echo "  开录提示:① 开屏录  ② 浏览器留一个 sepolia.etherscan.io 标签"
echo "           ③ 手机解锁、Cobo App 待命 —— **会弹一次批准**(选中的官方 vendor)"
[ "$warn" -eq 1 ] && echo "  ⚠️  上面有警告,确认可接受再继续。"
echo "───────────────────────────────────────────────────────"
read -r -p "  按 Enter 开始(Ctrl-C 取消)... " _

# hero = procurement 一条:发现→比价→审计当闸→选官方 vendor→手机批一次→真上链
HERMES_VERBOSE=1 HERMES_BRAIN=gpt-5.5 HERMES_CAW=real HERMES_GATE=real uv run hermes-auditor procurement

echo "═══════════════════════════════════════════════════════"
echo " 录完。把上面整段 + etherscan 截图存进 backup;tx hash 回填 demo-evidence.md。"
echo "═══════════════════════════════════════════════════════"
