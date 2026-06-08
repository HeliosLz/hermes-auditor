"""Hermes Auditor run state.

第一条 tracer bullet 的状态形状。字段对应 docs/langgraph-skeleton.md 的"状态形状"表。
目标只是证明流程可恢复、可审计 —— 不是智能。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

# AUDIT 节点产出的决策；直接映射成控制流。
AuditDecision = Literal["ALLOW", "STOP_AND_REVIEW", "REJECT"]


class AuditLogEntry(TypedDict):
    """audit_log 里的一条 append-only 记录：node 进出 + 决策。"""

    node: str
    detail: str


class HermesState(TypedDict, total=False):
    """一次 procurement/payment 尝试的全部可恢复状态。

    total=False：节点逐步填充字段，graph 入口只需要 run_id + risk_summary。
    """

    run_id: str
    user_intent: str

    # PLAN_DYNAMIC_WORKFLOW 产出（本 bullet 里从 fixture 解包，模拟"Claude 提出"）
    dynamic_workflow_trace: list[str]
    candidate_vendor: dict[str, Any]
    payment_draft: dict[str, Any]

    # AUDIT 产出
    risk_summary: dict[str, Any]
    audit_decision: AuditDecision

    # HUMAN_GATE 产出
    human_confirmation: dict[str, Any]

    # CAW_EXECUTE 产出
    caw_result: dict[str, Any]

    # 最近一次可恢复错误
    error: str | None

    # append-only：用 operator.add reducer，让每个节点 append 而不是覆盖
    audit_log: Annotated[list[AuditLogEntry], operator.add]
