"""CAW 执行接缝:stub(canned tx)| real(真调 caw CLI 上 Sepolia)。

切换:环境变量 `HERMES_CAW`(默认 `stub`),仿 `plan/llm.py` 的 `HERMES_BRAIN`:
- `stub` —— 返回 6.04 测试网那笔成功转账的 canned 记录(免动钱,平时测试 / 回归)。
- `real` —— subprocess 调 `caw tx transfer` 提交,轮询 `caw tx get` 拿真 tx_hash。

**和脑的 fallback 决然不同——钱不能假装成功**:real 转账任何失败 / 超时 → 返回
status=BLOCKED|FAILED、**绝不返回假 tx_hash** → 由图路由进 STOPPED。脑可回退 stub,钱不行。

约束:Claude Code auto-mode 安全分类器挡 agent 自动跑 `caw tx transfer`(动钱守卫),
所以 real 模式由 **owner** 在自己终端跑整图,agent 只用 `HERMES_CAW=stub` 测代码。

参数映射(payment_draft → caw flags):
- payment_draft.chain_id=11155111  → caw `--chain-id SETH`(env HERMES_CAW_CHAIN)
- payment_draft.token=SETH_USDC1   → caw `--token-id`
- payment_draft.recipient_address  → caw `--dst-address`(pact 只放行已批准的那个)
- payment_draft.amount             → caw `--amount`
- src/pact/request-id 由 env / run_id 提供。
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

CAW = os.getenv("HERMES_CAW", "stub")

_CAW_BIN = os.getenv("HERMES_CAW_BIN", "/Users/gffive/.local/bin/caw")
_PACT_ID = os.getenv("HERMES_PACT_ID", "834f22c8-9f82-4811-9f7b-090c8ede0b0b")
_SRC_ADDRESS = os.getenv("HERMES_CAW_SRC", "0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6")
_CHAIN_ID = os.getenv("HERMES_CAW_CHAIN", "SETH")  # payment_draft 是 11155111,caw 要 SETH
# caw 配置在项目目录;cwd 默认仓库根(此文件 src/hermes_auditor/caw.py 上溯两级)。
_CWD = os.getenv("HERMES_CAW_CWD", str(Path(__file__).resolve().parents[2]))

_POLL_INTERVAL_S = float(os.getenv("HERMES_CAW_POLL_INTERVAL", "3"))
_POLL_MAX_TRIES = int(os.getenv("HERMES_CAW_POLL_TRIES", "30"))  # ~90s;6.10 实测 ~24s 到 Success
_SUBMIT_TIMEOUT_S = 60
_GET_TIMEOUT_S = 30

# caw tx get 的 .status:终态(实测 API 用 "Success";防御性兼容 SKILL 文档的 "Completed")。
_TERMINAL_OK = {"Success", "Completed"}
_TERMINAL_FAIL = {"Failed", "Rejected"}


def use_real() -> bool:
    """非 stub 即真调 caw。"""
    return CAW != "stub"


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_CAW_BIN, *args],
        cwd=_CWD,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _request_id(run_id: str) -> str:
    """每次跑唯一(caw 用它做幂等键);run_id 便于在 caw tx list 里对回。"""
    return f"{run_id}-{uuid4().hex[:8]}"


def execute_transfer(payment_draft: dict[str, Any], run_id: str) -> dict[str, Any]:
    """real:提交 `caw tx transfer` + 轮询 `caw tx get` 到终态。

    成功 → {status: SUCCESS, tx_hash, pact_id, request_id, sub_status}。
    任何失败 / 超时 → {status: BLOCKED|FAILED, reason, ...}(**无 tx_hash**)。
    """
    recipient = payment_draft.get("recipient_address")
    amount = payment_draft.get("amount")
    token_id = payment_draft.get("token", "SETH_USDC1")
    if not recipient or not amount:
        return {"status": "BLOCKED", "reason": "payment_draft 缺 recipient/amount"}

    request_id = _request_id(run_id)
    transfer_args = [
        "tx", "transfer",
        "--pact-id", _PACT_ID,
        "--chain-id", _CHAIN_ID,
        "--token-id", token_id,
        "--src-address", _SRC_ADDRESS,
        "--dst-address", recipient,
        "--amount", str(amount),
        "--request-id", request_id,
    ]

    # 1) 提交。非零退出 = 政策拒绝(5)/ 余额不足(6)/ 网络错(7)/ 认证(4)→ BLOCKED,不轮询。
    try:
        sub = _run(transfer_args, _SUBMIT_TIMEOUT_S)
    except Exception as e:
        return {"status": "BLOCKED", "reason": f"transfer 子进程异常: {type(e).__name__}: {e}",
                "request_id": request_id}
    if sub.returncode != 0:
        return {
            "status": "BLOCKED",
            "reason": f"caw tx transfer exit={sub.returncode}",
            "stderr": (sub.stderr or "").strip()[:300],
            "request_id": request_id,
        }

    # 2) 轮询 caw tx get --request-id 到终态,拿真 transaction_hash。
    last_status = "Pending"
    last_record: dict[str, Any] = {}
    for _ in range(_POLL_MAX_TRIES):
        try:
            got = _run(["tx", "get", "--request-id", request_id], _GET_TIMEOUT_S)
        except Exception:
            time.sleep(_POLL_INTERVAL_S)
            continue
        if got.returncode == 0 and got.stdout.strip():
            try:
                last_record = json.loads(got.stdout)
                last_status = last_record.get("status", last_status)
            except json.JSONDecodeError:
                pass
        if last_status in _TERMINAL_OK:
            return {
                "status": "SUCCESS",
                "tx_hash": last_record.get("transaction_hash", ""),
                "pact_id": last_record.get("pact_id", _PACT_ID),
                "request_id": request_id,
                "sub_status": last_record.get("sub_status", ""),
            }
        if last_status in _TERMINAL_FAIL:
            return {
                "status": "FAILED",
                "reason": f"caw 终态 status={last_status} sub_status={last_record.get('sub_status', '')}",
                "request_id": request_id,
            }
        time.sleep(_POLL_INTERVAL_S)

    return {
        "status": "BLOCKED",
        "reason": f"轮询超时({_POLL_MAX_TRIES}×{_POLL_INTERVAL_S}s),最后 status={last_status}",
        "request_id": request_id,
    }
