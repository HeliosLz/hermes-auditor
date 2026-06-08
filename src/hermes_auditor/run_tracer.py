"""第一条 tracer bullet 的入口。

跑两条 fixture 驱动的 run，打印每一条的 audit_log 和终态：
- allow-normal-payment   -> AUDIT -> HUMAN_GATE -> CAW_EXECUTE -> DONE
- reject-wrong-recipient -> AUDIT -> STOPPED

只证明控制流，不调用模型，不调用 CAW。
"""

from __future__ import annotations

from .fixtures_io import load_risk_summary
from .graph import build_graph
from .state import HermesState


def _run_one(graph, run_id: str, fixture_name: str) -> HermesState:
    summary = load_risk_summary(fixture_name)
    initial: HermesState = {"run_id": run_id, "risk_summary": summary, "audit_log": []}
    final: HermesState = graph.invoke(initial)

    print(f"\n=== RUN {run_id}  ({fixture_name}) ===")
    print(f"summary_id : {summary['summary_id']}")
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
    _run_one(graph, "run_allow_001", "allow-normal-payment")
    _run_one(graph, "run_reject_001", "reject-wrong-recipient")


if __name__ == "__main__":
    main()
