#!/usr/bin/env bash
# Hermes demo · 录制脚本 ②:攻击路片段(stub · 不依赖网关 · 不动钱)
#
# 跑整图,stub 脑 + stub CAW —— 控制流与真脑/真链完全一致,只是理由是确定性模板。
# 这正是**现场 live 跑的那条路**(不依赖网关,稳)。随时可录。
#
#   bash scripts/record-attack.sh
#
# 看点:reject 三镜头 REFUTED 带理由 + 三红旗 → STOPPED(手机连响都不响);
#        conflict 官方源+注入源同在 → Auditor 挑出合法地址、标记 attacker → ALLOW。

set -u
cd "$(dirname "$0")/.." || exit 1

echo "═══════════════════════════════════════════════════════"
echo " Hermes 录制 ② · 攻击路(stub · 不依赖网关 · 不动钱)"
echo "═══════════════════════════════════════════════════════"

cols=$(tput cols 2>/dev/null || echo 0)
if [ "$cols" -ge 120 ]; then echo "  ✅ 终端宽度 $cols 列(stub 理由短,≥120 即可)"
else echo "  ⚠️  终端宽度 $cols 列 < 120 → 建议拉宽,box 边框更齐。"; fi

echo "  说明:stub 跑,无网关 / 无 CAW / 无手机依赖 → 一把过,可反复重录。"
echo "───────────────────────────────────────────────────────"
read -r -p "  按 Enter 开始(Ctrl-C 取消)... " _

# 攻击路两条:reject(注入源→三镜头 REFUTED→STOPPED)+ conflict(挑出合法地址)
HERMES_VERBOSE=1 uv run hermes-auditor reject conflict

echo "═══════════════════════════════════════════════════════"
echo " 录完。重点截 reject 的 PLAN 面板(三镜头 REFUTED+理由)+ conflict 的挑址。"
echo "═══════════════════════════════════════════════════════"
