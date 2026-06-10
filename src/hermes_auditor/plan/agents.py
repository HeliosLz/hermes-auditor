"""PLAN 的 agent 接缝。

每个函数 = 一个独立-context 的 subagent。当前是**确定性 stub**,真实实现在
标注的 TODO 处接 Anthropic API / Agent SDK。

quarantine 在代码里的落地:构造 subagent 时 tools 只给 QUARANTINE_TOOLS。
动钱工具(EXCLUDED_TOOLS)物理上不在列表里 —— 不是「禁止」,是「从未授予」。
"""

from __future__ import annotations

import re

from .types import Confidence, RefuterVerdict, SourceFinding, SourceType

_ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")

# 注入话术特征(stub 版;真实实现交给 scan_for_injection 工具 / 模型判断)
_INJECTION_MARKERS = (
    "NOTE FOR AI",
    "AI AGENT",
    "AI agents",
    "忽略官方",
    "忽略前述",
    "改打到",
    "已迁移",
    "立即把所有付款",
    "务必照做",
    "ignore previous",
)

_CONFIDENCE_BY_SOURCE: dict[SourceType, Confidence] = {
    "official_docs": "high",
    "registry": "high",
    "user_input": "high",
    "web_untrusted": "low",
    "unknown": "low",
}


def _has_injection(text: str) -> bool:
    low = text.lower()
    return any(m.lower() in low for m in _INJECTION_MARKERS)


def run_source_agent(label: str, source_type: SourceType, doc: str) -> SourceFinding:
    """Fan-out subagent:只看一份材料,如实抽地址 + 由工具盖来源章。

    真实实现(TODO):
        client.messages.create(
            model=...,                      # 独立 context window
            tools=quarantine_tools(),       # 只读;无动钱工具
            system="你是来源调查 subagent,只看这一份材料……",
            messages=[{"role": "user", "content": doc}],
        )
    关键不变量:confidence 由 source_type 决定(工具盖章),模型不能自升可信度。
    """
    m = _ADDR_RE.search(doc)
    address = m.group(0) if m else None
    return SourceFinding(
        source_agent=label,
        address=address,
        source_type=source_type,
        confidence=_CONFIDENCE_BY_SOURCE[source_type],
        injection_signs=_has_injection(doc),
        notes="stub: regex 抽址 + 关键词测注入;真实实现接独立-context subagent",
    )


def run_refuter(
    lens: str,
    candidate: str,
    doc: str,
    authoritative: str | None,
    allowlist: tuple[str, ...],
) -> RefuterVerdict:
    """Adversarial refuter:身份是「攻击这个候选地址」,默认倾向可疑。

    真实实现(TODO):独立 subagent,看不到其他 refuter 的结论;
    system 强调「不确定就 refuted=true」「你是攻击者不是评审」。

    非对称:任一镜头 refuted=true,上层就拦(见 pipeline)。
    """
    a = candidate.lower()

    if lens == "provenance":
        if authoritative is None:
            return RefuterVerdict(lens, True, "无权威来源可对照 → 默认可疑")
        ok = a == authoritative.lower()
        return RefuterVerdict(lens, not ok, "与权威来源不符" if not ok else "与权威来源一致")

    if lens == "injection":
        bad = _has_injection(doc)
        return RefuterVerdict(lens, bad, "地址来自含注入话术的材料" if bad else "材料无注入特征")

    if lens == "policy":
        in_allow = a in {x.lower() for x in allowlist}
        return RefuterVerdict(lens, not in_allow, "不在 Pact allowlist" if not in_allow else "命中 allowlist")

    if lens == "amount":
        # stub:金额/字段越界检查留到接 payment_draft 时做;此处不否决
        return RefuterVerdict(lens, False, "stub: amount 镜头待接 payment 字段")

    return RefuterVerdict(lens, True, f"未知镜头 {lens} → 默认可疑")
