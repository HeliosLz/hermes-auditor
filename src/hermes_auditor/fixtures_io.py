"""加载并校验 risk_summary fixtures。

Auditor 项目的第一道防线：在任何节点跑之前，先确认 fixture 真的符合
schemas/risk-summary.schema.json。fixture 不合规就直接报错，不进状态机。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# 项目根：src/hermes_auditor/fixtures_io.py -> 上三级
_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _ROOT / "schemas" / "risk-summary.schema.json"
_FIXTURE_DIR = _ROOT / "fixtures" / "risk-summary"
_PLAN_SOURCE_DIR = _ROOT / "fixtures" / "plan-sources"

_PLAN_INPUT_REQUIRED = ("user_intent", "pact_allowlist", "payment_template", "sources")
_SOURCE_REQUIRED = ("label", "source_type", "doc")
_PROCUREMENT_REQUIRED = ("user_intent", "pact_allowlist", "payment_template", "vendors")
_VENDOR_REQUIRED = ("name", "price", "sources")
_MARKETPLACE_REQUIRED = ("user_intent", "pact_allowlist", "payment_template", "facets")
_FACET_REQUIRED = ("facet", "source_type", "corpus")
# 与 plan/types.py 的 SourceType 对齐:source_type 是信任标签,坏值要等到审计阶段
# 查 _CONFIDENCE_BY_SOURCE 表时才炸,必须在 load 时挡住。
_SOURCE_TYPES = ("official_docs", "registry", "user_input", "web_untrusted", "unknown")


def _load_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def load_risk_summary(name: str) -> dict[str, Any]:
    """读取一个 fixture 并按 schema 校验。

    name 是 fixtures/risk-summary/ 下的文件名（带或不带 .json 均可）。
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    path = _FIXTURE_DIR / filename
    summary = json.loads(path.read_text(encoding="utf-8"))

    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(summary), key=lambda e: e.path)
    if errors:
        msgs = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"fixture {filename} 不符合 risk-summary schema -> {msgs}")

    return summary


def load_plan_input(name: str) -> dict[str, Any]:
    """读取一个 PLAN-输入 fixture(sources bundle)并做最小结构校验。

    name 是 fixtures/plan-sources/ 下的文件名(带或不带 .json 均可)。
    PLAN 输入 ≠ risk_summary:它是 PLAN 之前的「各路材料」,不走 risk-summary schema。
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    data = json.loads((_PLAN_SOURCE_DIR / filename).read_text(encoding="utf-8"))

    missing = [k for k in _PLAN_INPUT_REQUIRED if k not in data]
    if missing:
        raise ValueError(f"plan-source {filename} 缺字段: {missing}")
    for i, src in enumerate(data["sources"]):
        bad = [k for k in _SOURCE_REQUIRED if k not in src]
        if bad:
            raise ValueError(f"plan-source {filename} sources[{i}] 缺字段: {bad}")

    return data


def load_procurement_input(name: str) -> dict[str, Any]:
    """读取一个采购-输入 fixture(vendor 目录)并做最小结构校验。

    采购输入 = 多个候选 vendor,每个自报价格 + 各路材料;区别于单 vendor 的 sources bundle。
    """
    filename = name if name.endswith(".json") else f"{name}.json"
    data = json.loads((_PLAN_SOURCE_DIR / filename).read_text(encoding="utf-8"))

    missing = [k for k in _PROCUREMENT_REQUIRED if k not in data]
    if missing:
        raise ValueError(f"procurement {filename} 缺字段: {missing}")
    for i, v in enumerate(data["vendors"]):
        bad = [k for k in _VENDOR_REQUIRED if k not in v]
        if bad:
            raise ValueError(f"procurement {filename} vendors[{i}] 缺字段: {bad}")
        for j, src in enumerate(v["sources"]):
            sbad = [k for k in _SOURCE_REQUIRED if k not in src]
            if sbad:
                raise ValueError(f"procurement {filename} vendors[{i}].sources[{j}] 缺字段: {sbad}")

    return data


_BUDGET_RE = re.compile(r"(?:预算|budget)\D{0,8}?(\d+(?:\.\d+)?)", re.IGNORECASE)


def build_ask_input(intent: str, anchors: str = "marketplace") -> dict[str, Any]:
    """把一句自然语言变成 discovery 输入:intent/预算来自用户的话,信任锚来自配置。

    用户即时输入永远只能提供「想要什么」(user_intent / 预算);「钱能打给谁」
    (pact_allowlist)和权威语料(registry / official facets)从 curated fixture 加载,
    不接受运行时改写 —— 否则注入一段假 registry 就能给任意地址盖权威章。

    预算:从 intent 里抽(「预算 0.005」/「budget 0.005」),与 pact 配置的上限取
    **较小者** —— 用户能收紧预算,不能放宽(pact 的 budget_limit 是策略天花板)。
    web facet:staged 语料清空、query 置为 intent —— ask 的 web 候选只能来自实时搜索,
    不存在「排练过的网页」。
    """
    data = load_marketplace_input(anchors)
    data["user_intent"] = intent

    m = _BUDGET_RE.search(intent)
    if m:
        ceiling = float(data["payment_template"]["budget_limit"])
        asked = float(m.group(1))
        data["payment_template"]["budget_limit"] = str(min(asked, ceiling))
        if asked > ceiling:
            # 收紧不静默:用户要的预算被 pact 天花板压回,必须浮出(展示层打印)。
            data["_budget_clamped"] = {"asked": m.group(1), "ceiling": str(ceiling)}

    for facet in data["facets"]:
        if facet["source_type"] == "web_untrusted":
            facet["corpus"] = ""
            facet["query"] = intent
    return data


def load_marketplace_input(name: str) -> dict[str, Any]:
    """读取一个 discovery-输入 fixture(staged marketplace)并做最小结构校验。"""
    filename = name if name.endswith(".json") else f"{name}.json"
    data = json.loads((_PLAN_SOURCE_DIR / filename).read_text(encoding="utf-8"))

    missing = [k for k in _MARKETPLACE_REQUIRED if k not in data]
    if missing:
        raise ValueError(f"marketplace {filename} 缺字段: {missing}")
    for i, facet in enumerate(data["facets"]):
        bad = [k for k in _FACET_REQUIRED if k not in facet]
        if bad:
            raise ValueError(f"marketplace {filename} facets[{i}] 缺字段: {bad}")
        if facet["source_type"] not in _SOURCE_TYPES:
            raise ValueError(
                f"marketplace {filename} facets[{i}] source_type 非法: "
                f"{facet['source_type']!r},允许 {_SOURCE_TYPES}"
            )

    return data
