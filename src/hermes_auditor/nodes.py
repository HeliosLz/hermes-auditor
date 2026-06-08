"""五个 stub 节点。

第一条 tracer bullet 只证明控制流，不证明智能：
- 不调用 Claude（PLAN 从 fixture 解包，模拟"Claude 已提出"）。
- 不调用 CAW（CAW_EXECUTE 返回 6.04 那笔成功 tx 的记录）。

唯一有真实逻辑的是 AUDIT：它从 risk_summary 的 checks / red_flags **推导**
audit_decision，而不是直接读 fixture 自带的 decision 标签。这一步把"风险判断"
变成"控制流"，是 Auditor 存在的理由。
"""

from __future__ import annotations

from typing import Any

from .state import AuditDecision, HermesState

# 6.04 测试网成功路径的真实证据，用于 CAW_EXECUTE stub。
_CAW_SUCCESS_TX = "0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726"
_CAW_SUCCESS_PACT = "7ef2c434-17f7-436c-8dbe-293924eb3a04"


def _log(node: str, detail: str) -> dict[str, Any]:
    """返回只含一条 audit_log 的 partial state；reducer 负责 append。"""
    return {"audit_log": [{"node": node, "detail": detail}]}


def plan_dynamic_workflow(state: HermesState) -> dict[str, Any]:
    """PLAN_DYNAMIC_WORKFLOW：可逆准备。

    本 bullet 里 fixture 已是 post-plan 的 risk_summary，所以这里只解包 vendor 和
    payment，模拟"Claude Dynamic Workflow 已经提出候选 vendor 和 payment draft"。
    规则：不调用 CAW，不把 payment 标记为已批准。
    """
    summary = state["risk_summary"]
    out: dict[str, Any] = {
        "user_intent": summary["user_intent"],
        "dynamic_workflow_trace": [
            f"propose vendor: {summary['vendor']['name']}",
            f"draft payment: {summary['payment']['amount']} {summary['payment']['token']}",
        ],
        "candidate_vendor": summary["vendor"],
        "payment_draft": summary["payment"],
        "error": None,
    }
    out.update(_log("PLAN_DYNAMIC_WORKFLOW", f"proposed vendor={summary['vendor']['name']}"))
    return out


def _derive_decision(summary: dict[str, Any]) -> tuple[AuditDecision, str]:
    """从 checks / red_flags 推导 audit_decision —— Auditor 的核心。"""
    checks = summary["checks"]
    has_high_flag = any(f["severity"] == "high" for f in summary.get("red_flags", []))

    # 不可逆资金路径的硬性拒绝条件：policy 不匹配、地址来源对不上、或高危红旗。
    if not checks["policy_matches_summary"] or has_high_flag:
        return "REJECT", "policy mismatch or high-severity red flag"
    if checks["prompt_injection_detected"]:
        return "REJECT", "prompt injection detected"

    # 地址来源可疑但 policy 仍匹配：不直接放行，交给 human。
    if not checks["address_matches_source"]:
        return "STOP_AND_REVIEW", "address does not match claimed source"

    return "ALLOW", "all binding checks passed"


def audit(state: HermesState) -> dict[str, Any]:
    """AUDIT：检查 + 生成 audit_decision。

    decision 由 checks 推导。fixture 自带的 decision 字段只当 oracle，用来验证
    推导逻辑是否和设计意图一致（记进 audit_log，不参与控制流）。
    """
    summary = state["risk_summary"]
    decision, reason = _derive_decision(summary)

    oracle = summary.get("decision")
    consistent = "ok" if oracle == decision else f"MISMATCH oracle={oracle}"

    out: dict[str, Any] = {"audit_decision": decision}
    out.update(_log("AUDIT", f"decision={decision} ({reason}); fixture-oracle={consistent}"))
    return out


def human_gate(state: HermesState) -> dict[str, Any]:
    """HUMAN_GATE：在 CAW 执行前暂停等待人类批准。

    stub：自动生成一个本地 approval object，绑定到精确的 summary_id。
    真实实现里这里会 interrupt 等待人类输入。
    """
    summary = state["risk_summary"]
    confirmation = {
        "approved": True,
        "summary_id": summary["summary_id"],
        "approved_decision": state["audit_decision"],
        "note": "stub auto-approval (tracer bullet)",
    }
    out: dict[str, Any] = {"human_confirmation": confirmation}
    out.update(_log("HUMAN_GATE", f"approved summary_id={summary['summary_id']}"))
    return out


def caw_execute(state: HermesState) -> dict[str, Any]:
    """CAW_EXECUTE：只在 human confirmation 之后执行。

    stub：返回 6.04 那笔测试网成功转账的记录。真实实现里这里 call CAW，
    必须区分成功 tx hash 和 CAW enforced STOP。
    """
    confirmation = state.get("human_confirmation", {})
    if not confirmation.get("approved"):
        result = {"status": "BLOCKED", "reason": "no human confirmation"}
        out: dict[str, Any] = {"caw_result": result}
        out.update(_log("CAW_EXECUTE", "blocked: missing confirmation"))
        return out

    result = {
        "status": "SUCCESS",
        "tx_hash": _CAW_SUCCESS_TX,
        "pact_id": _CAW_SUCCESS_PACT,
        "note": "stubbed from 2026-06-04 testnet evidence",
    }
    out = {"caw_result": result}
    out.update(_log("CAW_EXECUTE", f"success tx={_CAW_SUCCESS_TX[:14]}..."))
    return out


def stopped(state: HermesState) -> dict[str, Any]:
    """STOPPED：终态。记录为什么停。"""
    decision = state.get("audit_decision", "UNKNOWN")
    return _log("STOPPED", f"run stopped at decision={decision}")
