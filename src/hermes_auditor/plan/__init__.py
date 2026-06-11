"""PLAN_DYNAMIC_WORKFLOW 节点内部:可逆区的扇出规划 + 对抗验证。

这是 LangGraph 图里 PLAN 节点的内部实现骨架,对应 dynamic-workflow 模式
(fan-out-and-synthesize + adversarial-verification),全程 quarantine:
subagent 只读、不含动钱工具。

注:Hermes 是独立 app,调不到 Claude Code 的 dynamic workflows feature,所以这里
**重实现该 pattern**(用 Anthropic API / Agent SDK)。当前为确定性 stub,接缝见
agents.py 的 TODO。
"""

from .pipeline import plan_dynamic_workflow, procure_dynamic_workflow

__all__ = ["plan_dynamic_workflow", "procure_dynamic_workflow"]
