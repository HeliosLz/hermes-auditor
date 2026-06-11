"""PLAN 内部的数据形状 + 常量。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["official_docs", "registry", "user_input", "web_untrusted", "unknown"]
Confidence = Literal["high", "medium", "low"]


@dataclass
class Source:
    """喂给一个 fan-out subagent 的「一份材料」。"""

    label: str
    source_type: SourceType
    doc: str


@dataclass
class Vendor:
    """采购比价里的一个候选供应商:自报价格 + 各路材料(收款地址藏在材料里,待查证)。"""

    name: str
    price: str  # 字符串保精度(与 payment amount 同款)
    sources: list[Source]


@dataclass
class SourceFinding:
    """一个 fan-out subagent 的产出。provenance 由工具盖章,不由模型自称。"""

    source_agent: str
    address: str | None
    source_type: SourceType
    confidence: Confidence
    injection_signs: bool
    notes: str = ""


@dataclass
class RefuterVerdict:
    """一个 adversarial refuter 的产出。"""

    lens: str
    refuted: bool
    reason: str = ""


@dataclass
class PlanResult:
    """PLAN 出口:交回 LangGraph 的结构化结果。

    payment_draft 为 None 表示「证据不足 / 可疑」—— AUDIT 大概率 STOP。
    """

    user_intent: str
    candidate_vendor: dict
    payment_draft: dict | None
    authoritative_address: str | None
    suspicious_candidate: str | None
    verdicts: list[RefuterVerdict] = field(default_factory=list)
    blocked: bool = False
    trace: list[str] = field(default_factory=list)
    # 决策者审计:真脑模式下共发起几次 agent 调用、其中几次回退了 stub(0=全真脑)。
    brain_calls: int = 0
    brain_fallbacks: int = 0
    # 采购比价:逐 vendor 的 {name, price, address, trusted, within_budget, reason};单 vendor 路为空。
    comparison: list[dict] = field(default_factory=list)
    selected_vendor: str | None = None


# 对抗验证的镜头:perspective-diverse,各抓一类失败模式。
LENSES = ("provenance", "injection", "policy", "amount")

# quarantine allowlist:PLAN 的 subagent 只能用这些(全只读 / 可逆)。
QUARANTINE_TOOLS = (
    "search_vendor",
    "fetch_vendor_doc",
    "resolve_recipient_address",
    "scan_for_injection",
    "compute_budget_fit",
)

# 故意排除(负空间即论点):动钱能力从未授予 PLAN 的任何 subagent。
# transfer / create_pact / sign / broadcast → 归 CAW_EXECUTE
# approve / confirm                          → 归 HUMAN_GATE
EXCLUDED_TOOLS = ("transfer", "create_pact", "sign", "broadcast", "approve", "confirm")
