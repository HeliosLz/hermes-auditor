"""整图入口:PLAN(可逆区 fan-out + adversarial)→ AUDIT → HUMAN_GATE → CAW_EXECUTE。

    uv run hermes-auditor

三条 PLAN-source 驱动的 run:
- allow    -> ALLOW  -> HUMAN_GATE -> CAW_EXECUTE -> DONE
- reject   -> REJECT -> STOPPED
- conflict -> ALLOW(挑出 legit、标记 attacker) -> ... -> DONE

PLAN 的 agent 仍是确定性 stub;不调真模型,不调真 CAW。
"""

from __future__ import annotations

from .fixtures_io import load_plan_input
from .graph import build_graph
from .state import HermesState


def _run_one(graph, run_id: str, scenario: str) -> HermesState:
    plan_input = load_plan_input(scenario)
    initial: HermesState = {"run_id": run_id, "plan_input": plan_input, "audit_log": []}
    final: HermesState = graph.invoke(initial)

    print(f"\n=== RUN {run_id}  (plan-sources/{scenario}) ===")
    for i, entry in enumerate(final["audit_log"], 1):
        print(f"  {i}. [{entry['node']}] {entry['detail']}")

    decision = final.get("audit_decision")
    caw = final.get("caw_result")
    if caw and caw.get("status") == "SUCCESS":
        terminal = f"DONE  (tx={caw['tx_hash'][:14]}...)"
    else:
        terminal = "STOPPED"
    print(f"  -> terminal: {terminal}  | audit_decision={decision}")
    return final


def main() -> None:
    graph = build_graph()
    _run_one(graph, "run_allow_001", "allow")
    _run_one(graph, "run_reject_001", "reject")
    _run_one(graph, "run_conflict_001", "conflict")


if __name__ == "__main__":
    main()
