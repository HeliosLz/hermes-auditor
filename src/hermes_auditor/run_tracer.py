"""整图入口:PLAN(可逆区 fan-out + adversarial)→ AUDIT → HUMAN_GATE → CAW_EXECUTE。

    uv run hermes-auditor

三条 PLAN-source 驱动的 run:
- allow    -> ALLOW  -> HUMAN_GATE -> CAW_EXECUTE -> DONE
- reject   -> REJECT -> STOPPED   (HUMAN_GATE 根本不到,手机不会响)
- conflict -> ALLOW(挑出 legit、标记 attacker) -> ... -> DONE

三个接缝开关(默认全 stub,免 token / 免动钱 / 免交互):
- HERMES_BRAIN=stub|gpt-5.5   agent 脑
- HERMES_CAW=stub|real        上链执行(real 含 Cobo 手机批等待,owner 终端跑)
- HERMES_GATE=stub|real       人闸展示(real: interrupt 暂停,打印 Auditor 判断后续跑)
"""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .fixtures_io import load_plan_input
from .graph import build_graph
from .state import HermesState


def _print_gate_payload(payload: dict[str, Any]) -> None:
    """interrupt 暂停时,把 Auditor 的判断打到终端 —— 人在手机弹批之前先读到「为什么」。"""
    pay = payload.get("payment") or {}
    print("\n  ┌─ HUMAN_GATE · Auditor 判断(图已暂停)" + "─" * 24)
    print(f"  │ summary_id : {payload.get('summary_id')}")
    print(f"  │ decision   : {payload.get('decision')}")
    print(f"  │ intent     : {payload.get('user_intent', '')[:60]}")
    print(
        f"  │ payment    : {pay.get('amount')} {pay.get('token')}"
        f" -> {pay.get('recipient_address')} (chain {pay.get('chain_id')})"
    )
    checks = payload.get("checks", {})
    print(f"  │ checks     : " + ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in checks.items()))
    for f in payload.get("red_flags", []):
        print(f"  │ red_flag   : [{f.get('severity')}] {f.get('message')}")
    print("  └─ 单闸:绑定批准在 Cobo 手机 App —— 续跑提交,等手机弹批 " + "─" * 8)


def _run_one(graph, run_id: str, scenario: str) -> HermesState:
    plan_input = load_plan_input(scenario)
    initial: HermesState = {"run_id": run_id, "plan_input": plan_input, "audit_log": []}
    config = {"configurable": {"thread_id": run_id}}

    print(f"\n=== RUN {run_id}  (plan-sources/{scenario}) ===")
    # 跑 → 遇 interrupt(HERMES_GATE=real)打印 Auditor 判断 → resume 续跑。
    final: HermesState = graph.invoke(initial, config)
    while "__interrupt__" in final:
        for intr in final["__interrupt__"]:
            _print_gate_payload(intr.value)
        final = graph.invoke(Command(resume={"ack": True}), config)

    for i, entry in enumerate(final["audit_log"], 1):
        print(f"  {i}. [{entry['node']}] {entry['detail']}")

    decision = final.get("audit_decision")
    caw = final.get("caw_result")
    if caw and caw.get("status") == "SUCCESS":
        gate = "·手机已批" if caw.get("human_approval") == "approved" else ""
        terminal = f"DONE  (tx={caw['tx_hash'][:14]}...{gate})"
    else:
        terminal = "STOPPED"
    print(f"  -> terminal: {terminal}  | audit_decision={decision}")
    return final


def main() -> None:
    from . import caw, nodes
    from .plan import llm

    print(f"brain = {llm.BRAIN}" + ("" if llm.use_model() else "  (确定性 stub,免 token)"))
    print(f"caw   = {caw.CAW}" + ("  (真上链+手机批 · owner 终端跑)" if caw.use_real() else "  (canned tx,免动钱)"))
    print(f"gate  = {nodes.GATE}" + ("  (interrupt 暂停,展示 Auditor 判断)" if nodes.GATE != "stub" else "  (自动批准,免交互)"))
    graph = build_graph(checkpointer=MemorySaver())
    _run_one(graph, "run_allow_001", "allow")
    _run_one(graph, "run_reject_001", "reject")
    _run_one(graph, "run_conflict_001", "conflict")


if __name__ == "__main__":
    main()
