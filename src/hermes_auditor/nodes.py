"""五个图节点。

职责边界(今天接通的接缝):
- PLAN 出**事实 + 证据**:跑可逆区 fan-out + adversarial(plan/ 子包),产出
  candidate_vendor / payment_draft / plan_evidence。agent 仍是确定性 stub。
- AUDIT 出 **risk_summary + decision**:从 PLAN 的证据组装 risk_summary,并推导
  audit_decision —— 把"风险判断"变成"控制流"。
- HUMAN_GATE / CAW_EXECUTE 仍 stub(不接 interrupt、不接真 CAW)。
"""

from __future__ import annotations

from typing import Any

from .plan import plan_dynamic_workflow as _run_plan_pipeline
from .plan.types import Source
from .state import AuditDecision, HermesState

# 6.04 测试网成功路径的真实证据，用于 CAW_EXECUTE stub。
_CAW_SUCCESS_TX = "0xf65f2d90826fe948c9fa12ec1d605f6b092a22c802795d4d5740463062ed9726"
_CAW_SUCCESS_PACT = "7ef2c434-17f7-436c-8dbe-293924eb3a04"


def _log(node: str, detail: str) -> dict[str, Any]:
    """返回只含一条 audit_log 的 partial state；reducer 负责 append。"""
    return {"audit_log": [{"node": node, "detail": detail}]}


def plan_dynamic_workflow(state: HermesState) -> dict[str, Any]:
    """PLAN_DYNAMIC_WORKFLOW：可逆区 fan-out + adversarial。

    调 plan/ 子包:多源查地址 → synthesize(代码)→ adversarial 反驳 → assemble。
    产出 candidate_vendor / payment_draft / plan_evidence,交给 AUDIT。
    规则:全程 quarantine(subagent 无动钱工具),不调用 CAW,不标记已批准。
    """
    pin = state["plan_input"]
    sources = [Source(s["label"], s["source_type"], s["doc"]) for s in pin["sources"]]
    result = _run_plan_pipeline(
        user_intent=pin["user_intent"],
        sources=sources,
        pact_allowlist=tuple(pin["pact_allowlist"]),
        payment_template=pin["payment_template"],
        vendor_name=pin.get("vendor_name", "Demo Data API"),
    )

    recipient = result.payment_draft["recipient_address"] if result.payment_draft else "none"
    out: dict[str, Any] = {
        "user_intent": result.user_intent,
        "dynamic_workflow_trace": result.trace,
        "candidate_vendor": result.candidate_vendor,
        "payment_draft": result.payment_draft,
        "plan_evidence": {
            "authoritative_address": result.authoritative_address,
            "suspicious_candidate": result.suspicious_candidate,
            "verdicts": [{"lens": v.lens, "refuted": v.refuted, "reason": v.reason} for v in result.verdicts],
            "blocked": result.blocked,
        },
        "error": None,
    }
    out.update(_log("PLAN_DYNAMIC_WORKFLOW", f"blocked={result.blocked} recipient={recipient}"))
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


def _checks_from_verdicts(verdicts: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """把 PLAN 的 refuter verdicts 映射成 risk_summary 的 checks。

    PLAN 的信号是 advisory;AUDIT 在这里组装成自己的 checks(真模型接通后,这一步
    会改成 AUDIT 独立重核,而非直接采信 PLAN)。
    """

    def refuted(lens: str) -> bool:
        return verdicts.get(lens, {}).get("refuted", False)

    return {
        "address_matches_source": not refuted("provenance"),
        "amount_within_budget": not refuted("amount"),
        "recipient_first_seen": True,  # stub: CAW 链上状态未接
        "policy_matches_summary": not refuted("policy"),
        "prompt_injection_detected": refuted("injection"),
    }


def audit(state: HermesState) -> dict[str, Any]:
    """AUDIT：从 PLAN 证据组装 risk_summary，并推导 audit_decision。

    PLAN 出事实+证据,AUDIT 出 checks+决策。blocked(无权威来源/证据不足)是硬 REJECT。
    """
    evidence = state["plan_evidence"]
    verdicts = {v["lens"]: v for v in evidence["verdicts"]}
    checks = _checks_from_verdicts(verdicts)
    red_flags = [
        {"severity": "high", "message": v["reason"]}
        for v in evidence["verdicts"]
        if v["refuted"]
    ]

    if evidence["blocked"]:
        decision: AuditDecision = "REJECT"
        reason = "PLAN blocked: 无权威来源 / 证据不足"
    else:
        decision, reason = _derive_decision({"checks": checks, "red_flags": red_flags})

    risk_summary = {
        "summary_id": f"rs_{state.get('run_id', 'run')}",
        "user_intent": state.get("user_intent", ""),
        "vendor": state.get("candidate_vendor", {}),
        "payment": state.get("payment_draft") or {},
        "checks": checks,
        "red_flags": red_flags or [{"severity": "none", "message": "no material red flags"}],
        "decision": decision,
        "plan_evidence": evidence,
    }

    out: dict[str, Any] = {"risk_summary": risk_summary, "audit_decision": decision}
    out.update(_log("AUDIT", f"decision={decision} ({reason})"))
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
