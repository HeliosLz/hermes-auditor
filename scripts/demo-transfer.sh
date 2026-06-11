#!/usr/bin/env bash
# ⚠️ 裸 caw 兜底脚本 —— **不是录制脚本**。录 demo 用 record-hero.sh / record-attack.sh。
#    三个原因不适合录制:① 用旧自动 pact 834f22c8(手机不弹批)② 固定 request-id 撞幂等
#    (重跑拿同一笔旧 tx)③ 绕过整图(评委看不到 Auditor 的「为什么」)。
#    仅留作「原始 caw 转账能力」的最后兜底证据。
#
# Hermes demo · allow 路转账:0.001 SETH_USDC1 → 0x2348..81ba(在已批准 pact 内执行)
# 用法(在你自己的终端里跑):
#   bash /Users/gffive/hermes-auditor/scripts/demo-transfer.sh
CAW=/Users/gffive/.local/bin/caw
cd /Users/gffive/hermes-auditor    # caw 配置在项目目录

echo "=== 执行转账:0.001 SETH_USDC1 -> 0x2348..81ba ==="
"$CAW" tx transfer \
  --pact-id 834f22c8-9f82-4811-9f7b-090c8ede0b0b \
  --chain-id SETH \
  --token-id SETH_USDC1 \
  --src-address 0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6 \
  --dst-address 0x23482606e068480f91cd7b1a6f775986a96081ba \
  --amount 0.001 \
  --request-id hermes-demo-tx-001
echo "=== 完成,把上面整段输出贴给 Claude ==="
