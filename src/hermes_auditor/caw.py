"""CAW 执行接缝:stub(canned tx)| real(真调 caw CLI 上 Sepolia)。

切换:环境变量 `HERMES_CAW`(默认 `stub`),仿 `plan/llm.py` 的 `HERMES_BRAIN`:
- `stub` —— 返回 6.04 测试网那笔成功转账的 canned 记录(免动钱,平时测试 / 回归)。
- `real` —— subprocess 调 `caw tx transfer` 提交,轮询 `caw tx get` 拿真 tx_hash。

**和脑的 fallback 决然不同——钱不能假装成功**:real 转账任何失败 / 超时 → 返回
status=BLOCKED|FAILED、**绝不返回假 tx_hash** → 由图路由进 STOPPED。脑可回退 stub,钱不行。

真人闸(Cobo 手机批,2026-06-10 接):pact 策略带 `always_review` 时,transfer 提交后
返回 `pending_operation_id` → owner 在 Cobo App 批准这一笔 → 才上链。本模块的对应分支:
- 提交响应里有 pending_operation_id → 轮询 `caw pending get` 到 approved / rejected;
- approved → 转轮 `caw tx get` 拿真 tx_hash;rejected → FAILED(无 tx_hash)→ STOPPED;
- 等待人批的超时比 tx 轮询宽(默认 ~5 分钟,HERMES_PENDING_POLL_* 可调)。
- 钱包未 paired / 旧自动 pact(无 pending)→ 走原路直接轮 tx,行为不变。

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
# 默认 = always_review 的 demo pact(每笔 owner 手机批;2026-06-17 过期)。
# 旧自动放行 pact 834f22c8-…(2026-06-16 过期)可经 env 切回,用于免手机的排练快路。
_PACT_ID = os.getenv("HERMES_PACT_ID", "91860633-bc88-4b6c-8380-26844cb63c0b")
_SRC_ADDRESS = os.getenv("HERMES_CAW_SRC", "0xf8b6ee2cd773d8c1dd7109ff70cb9f7f9ed026a6")
_CHAIN_ID = os.getenv("HERMES_CAW_CHAIN", "SETH")  # payment_draft 是 11155111,caw 要 SETH
# caw 配置在项目目录;cwd 默认仓库根(此文件 src/hermes_auditor/caw.py 上溯两级)。
_CWD = os.getenv("HERMES_CAW_CWD", str(Path(__file__).resolve().parents[2]))

_POLL_INTERVAL_S = float(os.getenv("HERMES_CAW_POLL_INTERVAL", "3"))
_POLL_MAX_TRIES = int(os.getenv("HERMES_CAW_POLL_TRIES", "30"))  # ~90s;6.10 实测 ~24s 到 Success
_SUBMIT_TIMEOUT_S = 60
_GET_TIMEOUT_S = 30

# 等 owner 手机批准:人比链慢,超时单独放宽(默认 5s × 60 = ~5 分钟)。
_PENDING_POLL_INTERVAL_S = float(os.getenv("HERMES_PENDING_POLL_INTERVAL", "5"))
_PENDING_POLL_MAX_TRIES = int(os.getenv("HERMES_PENDING_POLL_TRIES", "60"))

# caw tx get 的 .status:终态(实测 API 用 "Success";防御性兼容 SKILL 文档的 "Completed")。
_TERMINAL_OK = {"Success", "Completed"}
_TERMINAL_FAIL = {"Failed", "Rejected"}

# caw pending get 的 .status:owner 在 Cobo App 的决定。
_PENDING_APPROVED = {"approved", "Approved"}
_PENDING_REJECTED = {"rejected", "Rejected"}


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


def _extract_pending_operation_id(stdout: str) -> str | None:
    """从 caw tx transfer 的提交响应里挖 pending_operation_id(没有 = 自动放行)。"""
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    result = data.get("result") if isinstance(data, dict) else None
    for record in (result, data):
        if isinstance(record, dict) and record.get("pending_operation_id"):
            return str(record["pending_operation_id"])
    return None


def _wait_for_owner_approval(operation_id: str, request_id: str) -> dict[str, Any]:
    """轮询 `caw pending get` 等 owner 在 Cobo App 里批/拒这一笔。

    返回 {status: approved} 或 BLOCKED/FAILED 错误 dict(可直接当 execute_transfer 结果)。
    """
    print(f"  [CAW] PendingApproval — 等 owner 在 Cobo App 批准这一笔 (operation_id={operation_id})")
    last_status = "pending"
    for _ in range(_PENDING_POLL_MAX_TRIES):
        try:
            got = _run(["pending", "get", "--operation-id", operation_id], _GET_TIMEOUT_S)
        except Exception:
            time.sleep(_PENDING_POLL_INTERVAL_S)
            continue
        if got.returncode == 0 and got.stdout.strip():
            try:
                record = json.loads(got.stdout)
                inner = record.get("result") if isinstance(record.get("result"), dict) else record
                last_status = inner.get("status", last_status)
            except json.JSONDecodeError:
                pass
        if last_status in _PENDING_APPROVED:
            print("  [CAW] owner 已批准 — 等上链")
            return {"status": "approved"}
        if last_status in _PENDING_REJECTED:
            print("  [CAW] owner 已拒绝")
            return {
                "status": "FAILED",
                "reason": "owner 在 Cobo App 拒绝了这一笔(human gate)",
                "request_id": request_id,
                "pending_operation_id": operation_id,
            }
        time.sleep(_PENDING_POLL_INTERVAL_S)

    return {
        "status": "BLOCKED",
        "reason": (
            f"等 owner 批准超时({_PENDING_POLL_MAX_TRIES}×{_PENDING_POLL_INTERVAL_S}s),"
            f"最后 status={last_status};未批准,未上链"
        ),
        "request_id": request_id,
        "pending_operation_id": operation_id,
    }


def _poll_tx(request_id: str, extra: dict[str, Any]) -> dict[str, Any]:
    """轮询 `caw tx get --request-id` 到终态,拿真 transaction_hash。"""
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
                **extra,
            }
        if last_status in _TERMINAL_FAIL:
            return {
                "status": "FAILED",
                "reason": f"caw 终态 status={last_status} sub_status={last_record.get('sub_status', '')}",
                "request_id": request_id,
                **extra,
            }
        time.sleep(_POLL_INTERVAL_S)

    return {
        "status": "BLOCKED",
        "reason": f"轮询超时({_POLL_MAX_TRIES}×{_POLL_INTERVAL_S}s),最后 status={last_status}",
        "request_id": request_id,
        **extra,
    }


def execute_transfer(payment_draft: dict[str, Any], run_id: str) -> dict[str, Any]:
    """real:提交 `caw tx transfer`,(若需人批)等 owner 手机批准,再轮询到终态。

    成功 → {status: SUCCESS, tx_hash, pact_id, request_id, sub_status[, human_approval]}。
    任何失败 / 拒绝 / 超时 → {status: BLOCKED|FAILED, reason, ...}(**无 tx_hash**)。
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

    # 2) 真人闸:pact always_review → 提交响应带 pending_operation_id,等 owner 手机批。
    extra: dict[str, Any] = {}
    operation_id = _extract_pending_operation_id(sub.stdout)
    if operation_id:
        gate = _wait_for_owner_approval(operation_id, request_id)
        if gate["status"] != "approved":
            return gate  # FAILED(owner 拒)或 BLOCKED(超时)——无 tx_hash,图路由进 STOPPED
        extra = {"human_approval": "approved", "pending_operation_id": operation_id}

    # 3) 轮询 caw tx get 到终态。
    return _poll_tx(request_id, extra)
