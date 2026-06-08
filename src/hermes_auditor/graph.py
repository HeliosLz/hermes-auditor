"""把五个节点接成 docs/langgraph-skeleton.md 里的最小图。

    START
      -> PLAN_DYNAMIC_WORKFLOW
      -> AUDIT
      -> HUMAN_GATE
      -> CAW_EXECUTE
      -> DONE        (= LangGraph END)

    AUDIT       -> STOPPED
    HUMAN_GATE  -> STOPPED
    CAW_EXECUTE -> STOPPED

控制流由各节点写入 state 的字段驱动 —— 这正是"风险判断变成控制流"。
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from . import nodes
from .state import HermesState


def _route_after_audit(state: HermesState) -> str:
    # REJECT 直接进 STOPPED；ALLOW / STOP_AND_REVIEW 进 HUMAN_GATE。
    return "STOPPED" if state["audit_decision"] == "REJECT" else "HUMAN_GATE"


def _route_after_human_gate(state: HermesState) -> str:
    return "CAW_EXECUTE" if state["human_confirmation"].get("approved") else "STOPPED"


def _route_after_caw(state: HermesState) -> str:
    return "DONE" if state["caw_result"].get("status") == "SUCCESS" else "STOPPED"


def build_graph():
    g = StateGraph(HermesState)

    g.add_node("PLAN_DYNAMIC_WORKFLOW", nodes.plan_dynamic_workflow)
    g.add_node("AUDIT", nodes.audit)
    g.add_node("HUMAN_GATE", nodes.human_gate)
    g.add_node("CAW_EXECUTE", nodes.caw_execute)
    g.add_node("STOPPED", nodes.stopped)

    g.add_edge(START, "PLAN_DYNAMIC_WORKFLOW")
    g.add_edge("PLAN_DYNAMIC_WORKFLOW", "AUDIT")

    g.add_conditional_edges(
        "AUDIT", _route_after_audit, {"HUMAN_GATE": "HUMAN_GATE", "STOPPED": "STOPPED"}
    )
    g.add_conditional_edges(
        "HUMAN_GATE", _route_after_human_gate, {"CAW_EXECUTE": "CAW_EXECUTE", "STOPPED": "STOPPED"}
    )
    g.add_conditional_edges(
        "CAW_EXECUTE", _route_after_caw, {"DONE": END, "STOPPED": "STOPPED"}
    )
    g.add_edge("STOPPED", END)

    return g.compile()
