"""五个图节点。

职责边界(今天接通的接缝):
- PLAN 出**事实 + 证据**:跑可逆区 fan-out + adversarial(plan/ 子包),产出
  candidate_vendor / payment_draft / plan_evidence。agent 仍是确定性 stub。
- AUDIT 出 **risk_summary + decision**:从 PLAN 的证据组装 risk_summary,并推导
  audit_decision —— 把"风险判断"变成"控制流"。
- HUMAN_GATE 接了 `HERMES_GATE=stub|real` 开关:stub 自动批准;real `interrupt` 真暂停、
  展示 risk_summary(单闸:绑定批准在 Cobo 手机 App,见 caw.py 的 PendingApproval 等待)。
- CAW_EXECUTE 接了 `HERMES_CAW=stub|real` 开关:stub 出 canned tx;real subprocess 调真
  caw 上 Sepolia(见 caw.py)。
"""

from __future__ import annotations

import os
from typing import Any

from langgraph.types import interrupt

from . import caw
from .plan import llm as plan_llm
from .plan import plan_dynamic_workflow as _run_plan_pipeline
from .plan.types import Source
from .state import AuditDecision, HermesState

# 人闸的接缝:stub(自动批准,回归免交互)| real(interrupt 真暂停,展示 Auditor 判断)。
# 单闸设计(2026-06-10 定):绑定的资金闸是 Cobo 手机批(caw.py 的 PendingApproval 等待),
# 这里的 interrupt 只负责「人在手机弹批之前先读到为什么」—— 展示后 resume 即续跑。
GATE = os.getenv("HERMES_GATE", "stub")

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
            # 决策者审计:这次 PLAN 的判断是谁做的(回退不能静默)。
            "brain": plan_llm.BRAIN,
            "brain_calls": result.brain_calls,
            "brain_fallbacks": result.brain_fallbacks,
        },
        "error": None,
    }
    detail = f"blocked={result.blocked} recipient={recipient}"
    if plan_llm.use_model():
        if result.brain_fallbacks:
            detail += f" brain={plan_llm.BRAIN} ⚠{result.brain_fallbacks}/{result.brain_calls} 回退 stub"
        else:
            detail += f" brain={plan_llm.BRAIN} 全真脑 {result.brain_calls} 次"
    out.update(_log("PLAN_DYNAMIC_WORKFLOW", detail))
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
    """HUMAN_GATE：CAW 执行前的人闸。

    - stub：自动生成本地 approval object,绑定精确 summary_id(回归免交互)。
    - real：`interrupt(risk_summary 摘要)` 真暂停(需 checkpointer);run_tracer 把
      Auditor 的判断打到终端再 resume。单闸:这里不收人决定,绑定的批/拒在 Cobo 手机
      App(caw.py 等 PendingApproval)。防御:resume 显式传 {"approved": False} 仍可中止。
    """
    summary = state["risk_summary"]

    if GATE != "stub":
        payment = summary.get("payment") or {}
        ack = interrupt(
            {
                "summary_id": summary["summary_id"],
                "decision": summary["decision"],
                "user_intent": summary.get("user_intent", ""),
                "payment": {
                    "recipient_address": payment.get("recipient_address"),
                    "amount": payment.get("amount"),
                    "token": payment.get("token"),
                    "chain_id": payment.get("chain_id"),
                },
                "checks": summary["checks"],
                "red_flags": summary["red_flags"],
            }
        )
        if isinstance(ack, dict) and ack.get("approved") is False:
            confirmation = {
                "approved": False,
                "summary_id": summary["summary_id"],
                "approved_decision": state["audit_decision"],
                "note": "operator aborted at interrupt (before CAW submit)",
            }
            out: dict[str, Any] = {"human_confirmation": confirmation}
            out.update(_log("HUMAN_GATE", f"operator abort summary_id={summary['summary_id']}"))
            return out
        note = "real gate: risk_summary shown at interrupt; binding approval = Cobo App (phone)"
    else:
        note = "stub auto-approval (tracer bullet)"

    confirmation = {
        "approved": True,
        "summary_id": summary["summary_id"],
        "approved_decision": state["audit_decision"],
        "note": note,
    }
    out = {"human_confirmation": confirmation}
    out.update(_log("HUMAN_GATE", f"approved summary_id={summary['summary_id']} (gate={GATE})"))
    return out


def caw_execute(state: HermesState) -> dict[str, Any]:
    """CAW_EXECUTE：只在 human confirmation 之后执行。

    按 `HERMES_CAW` 分派(见 caw.py):
    - stub：返回 6.04 那笔测试网成功转账的 canned 记录(免动钱)。
    - real：subprocess 调真 caw 上 Sepolia,拿真 tx_hash。

    铁律:real 任何失败 → status 非 SUCCESS、**绝不假 tx_hash** → 路由进 STOPPED。
    成功 tx hash 与 CAW enforced STOP 在这里被严格区分。
    """
    confirmation = state.get("human_confirmation", {})
    if not confirmation.get("approved"):
        result = {"status": "BLOCKED", "reason": "no human confirmation"}
        out: dict[str, Any] = {"caw_result": result}
        out.update(_log("CAW_EXECUTE", "blocked: missing confirmation"))
        return out

    if caw.use_real():
        payment = state.get("payment_draft") or {}
        try:
            result = caw.execute_transfer(payment, state.get("run_id", "run"))
        except Exception as e:  # 真转账:任何异常都不假装成功
            result = {"status": "BLOCKED", "reason": f"CAW real 异常: {type(e).__name__}: {e}"}
        if result.get("status") == "SUCCESS":
            detail = f"real success tx={str(result.get('tx_hash', ''))[:14]}..."
        else:
            detail = f"real {result.get('status')}: {result.get('reason', '')}"
        out: dict[str, Any] = {"caw_result": result}
        out.update(_log("CAW_EXECUTE", detail))
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
