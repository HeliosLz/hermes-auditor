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

呈现开关(不改控制流):
- HERMES_VERBOSE=1            demo 模式:浮出 PLAN 可逆区调查 + AUDIT 风险研判的「为什么」
"""

from __future__ import annotations

import os
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from .fixtures_io import load_plan_input
from .graph import build_graph
from .state import HermesState

VERBOSE = os.getenv("HERMES_VERBOSE", "") not in ("", "0", "false", "no")


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


def _print_plan_panel(final: HermesState) -> None:
    """PLAN · 可逆区调查:浮出 fan-out 每源 + synthesize + adversarial 每镜头的「为什么」。

    内容全来自 dynamic_workflow_trace(pipeline 写的),这里只是分组打印,不重算。
    """
    trace = final.get("dynamic_workflow_trace") or []
    ev = final.get("plan_evidence") or {}
    print("\n  ┌─ PLAN · 可逆区调查(fan-out + 对抗验证)" + "─" * 22)
    for line in trace:
        # trace 行形如 [fan-out] / [synthesize] / [adversarial:lens] / [assemble] / [brain]
        # ⚠ 只标真问题:被反驳的镜头,或 fan-out 上的 ⚠injection 标记(不是「injection 这个词」)
        marker = "✗" if "REFUTED" in line else ("⚠" if "⚠injection" in line else " ")
        print(f"  │ {marker} {line}")
    # 脑溯源:这次判断是谁做的(回退不静默 = 可审计底线)
    if ev.get("brain") and ev.get("brain") != "stub":
        fb, calls = ev.get("brain_fallbacks", 0), ev.get("brain_calls", 0)
        tag = f"⚠ {fb}/{calls} 次回退 stub(网关失败)" if fb else f"全真脑 {calls} 次"
        print(f"  │   [脑] brain={ev['brain']} · {tag}")
    print("  └" + "─" * 50)


def _print_audit_panel(final: HermesState) -> None:
    """AUDIT · 风险研判:浮出 risk_summary 的 checks / red_flags / 决策 —— 让评委看到「为什么放行/拦」。"""
    rs = final.get("risk_summary") or {}
    checks = rs.get("checks") or {}
    print("\n  ┌─ AUDIT · 风险研判(risk_summary)" + "─" * 27)
    for k, v in checks.items():
        print(f"  │ {'✓' if v else '✗'} {k}")
    for f in rs.get("red_flags") or []:
        sev = f.get("severity")
        if sev and sev != "none":
            print(f"  │ ⚠ [{sev}] {f.get('message')}")
    print(f"  │ → decision: {rs.get('decision')}")
    print("  └" + "─" * 50)


def _run_one(graph, run_id: str, scenario: str) -> HermesState:
    plan_input = load_plan_input(scenario)
    initial: HermesState = {"run_id": run_id, "plan_input": plan_input, "audit_log": []}
    config = {"configurable": {"thread_id": run_id}}

    print(f"\n=== RUN {run_id}  (plan-sources/{scenario}) ===")
    # 跑 → 遇 interrupt(HERMES_GATE=real)打印 Auditor 判断 → resume 续跑。
    final: HermesState = graph.invoke(initial, config)
    if VERBOSE:
        _print_plan_panel(final)  # PLAN 调查永远先打(每 run 必有)

    audit_panel_shown = False
    while "__interrupt__" in final:
        if VERBOSE and not audit_panel_shown:
            _print_audit_panel(final)  # 闸前让评委先看到「为什么放行」
            audit_panel_shown = True
        for intr in final["__interrupt__"]:
            _print_gate_payload(intr.value)
        final = graph.invoke(Command(resume={"ack": True}), config)

    # gate=stub(无 interrupt)/ reject 路(不到闸):AUDIT 面板在这里补打
    if VERBOSE and not audit_panel_shown:
        _print_audit_panel(final)

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
