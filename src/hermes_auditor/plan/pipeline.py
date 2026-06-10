"""PLAN 编排:fan-out → synthesize(代码)→ adversarial → assemble。

确定性的 glue 是脚本(不是某个 agent 说了算);模型驱动的部分在 agents.py 的接缝。
这正是 dynamic-workflow 的形状:脚本编排,subagent 干活,中间结果存在变量里。
"""

from __future__ import annotations

from . import agents
from .types import LENSES, PlanResult, RefuterVerdict, Source, SourceFinding

# 哪些来源算「权威」(可作为收款依据)
_AUTHORITATIVE = ("official_docs", "registry", "user_input")


def _count_fallbacks(findings: list[SourceFinding], verdicts: list[RefuterVerdict]) -> tuple[int, int]:
    """数「这次 PLAN 的判断是谁做的」:(总调用数, 其中回退 stub 的次数)。"""
    calls = len(findings) + len(verdicts)
    fallbacks = sum(agents.FALLBACK_MARK in f.notes for f in findings) + sum(
        agents.FALLBACK_MARK in v.reason for v in verdicts
    )
    return calls, fallbacks


def _synthesize(findings: list[SourceFinding]) -> tuple[str | None, str | None]:
    """代码层比对:选权威地址 + 检出冲突候选。不交给某个 agent 自己拍板。"""
    authoritative = next(
        (f.address for f in findings if f.source_type in _AUTHORITATIVE and f.address),
        None,
    )
    if authoritative is None:
        # 没有权威来源:唯一候选(若有)本身就是可疑的
        suspicious = next((f.address for f in findings if f.address), None)
        return None, suspicious

    suspicious = next(
        (f.address for f in findings if f.address and f.address.lower() != authoritative.lower()),
        None,
    )
    return authoritative, suspicious


def _adversarial_verify(
    candidate: str,
    doc: str,
    authoritative: str | None,
    allowlist: tuple[str, ...],
) -> list[RefuterVerdict]:
    """对**将要采用的**地址跑 perspective-diverse refuter。

    真实实现:并行(各自独立 context)。stub:顺序跑,逻辑等价。
    """
    return [agents.run_refuter(lens, candidate, doc, authoritative, allowlist) for lens in LENSES]


def plan_dynamic_workflow(
    user_intent: str,
    sources: list[Source],
    pact_allowlist: tuple[str, ...],
    payment_template: dict,
    vendor_name: str = "Demo Data API",
) -> PlanResult:
    """PLAN 节点内部主线。

    sources           : 各路材料(每份喂一个独立 fan-out subagent)
    pact_allowlist    : CAW Pact 白名单(policy 镜头用)
    payment_template  : chain_id / network / token / amount / budget_limit(recipient 由 PLAN 填)
    """
    trace: list[str] = []

    # Stage 1 · fan-out(真实实现:并行;每个 subagent 独立 context + quarantine 工具集)
    findings = [agents.run_source_agent(s.label, s.source_type, s.doc) for s in sources]
    for f in findings:
        flag = " ⚠injection" if f.injection_signs else ""
        trace.append(f"[fan-out] {f.source_agent}: {f.address} ({f.source_type}/{f.confidence}){flag}")

    # synthesize(代码)
    authoritative, suspicious = _synthesize(findings)
    trace.append(f"[synthesize] authoritative={authoritative} suspicious={suspicious}")

    # 要采用的地址:有权威用权威;否则退到唯一候选(必然低可信)
    chosen = authoritative or suspicious
    if chosen is None:
        trace.append("[assemble] 无任何地址 → 证据不足")
        calls, fallbacks = _count_fallbacks(findings, [])
        return PlanResult(
            user_intent=user_intent,
            candidate_vendor={"name": vendor_name},
            payment_draft=None,
            authoritative_address=None,
            suspicious_candidate=None,
            blocked=True,
            trace=trace,
            brain_calls=calls,
            brain_fallbacks=fallbacks,
        )

    # chosen 对应的材料(给 injection 镜头看)
    chosen_doc = next((s.doc for s, f in zip(sources, findings) if f.address == chosen), "")

    # Stage 2 · adversarial(对将要采用的地址)
    verdicts = _adversarial_verify(chosen, chosen_doc, authoritative, pact_allowlist)
    for v in verdicts:
        trace.append(f"[adversarial:{v.lens}] {'REFUTED' if v.refuted else 'pass'} — {v.reason}")

    # 非对称阈值:无权威来源 OR 任一镜头反驳 → 拦
    blocked = authoritative is None or any(v.refuted for v in verdicts)

    # assemble
    payment_draft: dict | None
    if blocked:
        trace.append("[assemble] blocked → payment_draft=None(交 AUDIT,大概率 STOP)")
        payment_draft = None
    else:
        payment_draft = {**payment_template, "recipient_address": chosen}
        trace.append(f"[assemble] payment_draft 就绪 → recipient={chosen}")

    calls, fallbacks = _count_fallbacks(findings, verdicts)
    if fallbacks:
        trace.append(f"[brain] ⚠ {fallbacks}/{calls} 次调用回退 stub(网关失败)")

    return PlanResult(
        user_intent=user_intent,
        candidate_vendor={"name": vendor_name, "address_source": _source_of(findings, chosen)},
        payment_draft=payment_draft,
        authoritative_address=authoritative,
        suspicious_candidate=suspicious,
        verdicts=verdicts,
        blocked=blocked,
        trace=trace,
        brain_calls=calls,
        brain_fallbacks=fallbacks,
    )


def _source_of(findings: list[SourceFinding], address: str) -> str:
    f = next((f for f in findings if f.address == address), None)
    return f.source_type if f else "unknown"
