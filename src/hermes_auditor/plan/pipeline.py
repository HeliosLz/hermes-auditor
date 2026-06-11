"""PLAN 编排:fan-out → synthesize(代码)→ adversarial → assemble。

确定性的 glue 是脚本(不是某个 agent 说了算);模型驱动的部分在 agents.py 的接缝。
这正是 dynamic-workflow 的形状:脚本编排,subagent 干活,中间结果存在变量里。
"""

from __future__ import annotations

from . import agents
from .types import LENSES, PlanResult, RefuterVerdict, Source, SourceFinding, Vendor

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


# ===== 采购比价(procurement)=========================================
# 在单 vendor 审计之上加一层「发现候选 → 比价 → 审计当闸」:
# 便宜优先,但审计(来源可信度)是胜负手——最便宜的若是注入骗子,落到次便宜且可信的。

def _price(v: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("inf")


def _evaluate_vendor(vendor: Vendor, allowlist: tuple[str, ...]) -> dict:
    """对一个候选 vendor 跑 fan-out + 来源可信预筛(provenance + injection)。

    "可信"只看来源(地址有权威背书、无注入),**不含 allowlist**——allowlist 是最终 CAW 闸,
    不是「选哪个 vendor」的依据。这样多个 vendor 能在不同价位都可信,比价才是真的价格决策。
    返回结构含 findings(供赢家复用做完整对抗)+ chosen 地址 + trusted 判定。
    """
    findings = [agents.run_source_agent(s.label, s.source_type, s.doc) for s in vendor.sources]
    authoritative, suspicious = _synthesize(findings)
    chosen = authoritative or suspicious
    chosen_doc = next((s.doc for s, f in zip(vendor.sources, findings) if f.address == chosen), "")

    screen: list[RefuterVerdict] = []
    if chosen is not None:
        for lens in ("provenance", "injection"):
            screen.append(agents.run_refuter(lens, chosen, chosen_doc, authoritative, allowlist))
    trusted = (authoritative is not None) and not any(v.refuted for v in screen)

    if chosen is None:
        reason = "无可用地址"
    elif authoritative is None:
        reason = "无权威来源 → 不可信"
    elif not trusted:
        reason = "; ".join(v.reason for v in screen if v.refuted) or "预筛未过"
    else:
        reason = "来源可信(权威背书 + 无注入)"

    return {
        "vendor": vendor,
        "findings": findings,
        "authoritative": authoritative,
        "suspicious": suspicious,
        "chosen": chosen,
        "chosen_doc": chosen_doc,
        "screen": screen,
        "trusted": trusted,
        "reason": reason,
    }


def procure_dynamic_workflow(
    user_intent: str,
    vendors: list[Vendor],
    pact_allowlist: tuple[str, ...],
    payment_template: dict,
    budget_limit: str,
) -> PlanResult:
    """采购主线:发现候选 → 逐个查证(fan-out)→ 比价(便宜优先,审计当闸)→ 赢家完整对抗 → assemble。

    胜负手是审计:最便宜的 vendor 若收款地址来自注入源,被预筛拦下,落到次便宜且可信的。
    """
    trace: list[str] = []
    budget = _price(budget_limit)

    # Stage 1 · 逐 vendor 查证(每个 vendor 一组 fan-out + 来源可信预筛)
    evals = [_evaluate_vendor(v, pact_allowlist) for v in vendors]
    for e in evals:
        v = e["vendor"]
        flag = "可信" if e["trusted"] else "✗ " + e["reason"]
        trace.append(f"[discover] {v.name}  价 {v.price}  地址 {e['chosen']}  → {flag}")

    # Stage 2 · 比价:可信 且 预算内,按价格选最便宜
    eligible = [
        e for e in evals
        if e["trusted"] and _price(e["vendor"].price) <= budget
    ]
    eligible.sort(key=lambda e: _price(e["vendor"].price))
    # 比价表(含落选原因:不可信 / 超预算 / 价更高)
    comparison: list[dict] = []
    winner_eval = eligible[0] if eligible else None
    for e in sorted(evals, key=lambda e: _price(e["vendor"].price)):
        v = e["vendor"]
        within = _price(v.price) <= budget
        if not within:
            note = "超预算"
        elif not e["trusted"]:
            note = e["reason"]
        elif winner_eval is not None and e is winner_eval:
            note = "最便宜且可信 → 选中"
        else:
            note = "可信但价更高"
        comparison.append({
            "name": v.name, "price": v.price, "address": e["chosen"],
            "trusted": e["trusted"], "within_budget": within, "reason": note,
        })

    all_findings = [f for e in evals for f in e["findings"]]
    all_screen = [v for e in evals for v in e["screen"]]

    if winner_eval is None:
        trace.append("[比价] 无可信且预算内的候选 → 证据不足,拦")
        calls, fallbacks = _count_fallbacks(all_findings, all_screen)
        return PlanResult(
            user_intent=user_intent,
            candidate_vendor={"name": "(none)"},
            payment_draft=None,
            authoritative_address=None,
            suspicious_candidate=None,
            blocked=True,
            trace=trace,
            brain_calls=calls,
            brain_fallbacks=fallbacks,
            comparison=comparison,
            selected_vendor=None,
        )

    winner = winner_eval["vendor"]
    chosen = winner_eval["chosen"]
    trace.append(f"[比价] 选中 {winner.name}(价 {winner.price})—— 最便宜且通过审计")

    # Stage 3 · 赢家跑完整 4 镜头对抗(与单 vendor 路一致;allowlist/amount 镜头在此把关)
    verdicts = _adversarial_verify(chosen, winner_eval["chosen_doc"], winner_eval["authoritative"], pact_allowlist)
    for v in verdicts:
        trace.append(f"[adversarial:{v.lens}] {'REFUTED' if v.refuted else 'pass'} — {v.reason}")
    blocked = winner_eval["authoritative"] is None or any(v.refuted for v in verdicts)

    if blocked:
        trace.append("[assemble] 赢家完整对抗未过 → payment_draft=None")
        payment_draft = None
    else:
        payment_draft = {**payment_template, "amount": winner.price, "recipient_address": chosen}
        trace.append(f"[assemble] payment_draft 就绪 → {winner.price} → {chosen}")

    # 回退计数:含所有 vendor 的 fan-out + 预筛 + 赢家完整对抗
    calls, fallbacks = _count_fallbacks(all_findings, all_screen + verdicts)
    if fallbacks:
        trace.append(f"[brain] ⚠ {fallbacks}/{calls} 次调用回退 stub(网关失败)")

    return PlanResult(
        user_intent=user_intent,
        candidate_vendor={"name": winner.name, "address_source": _source_of(winner_eval["findings"], chosen)},
        payment_draft=payment_draft,
        authoritative_address=winner_eval["authoritative"],
        suspicious_candidate=winner_eval["suspicious"],
        verdicts=verdicts,
        blocked=blocked,
        trace=trace,
        brain_calls=calls,
        brain_fallbacks=fallbacks,
        comparison=comparison,
        selected_vendor=winner.name,
    )
