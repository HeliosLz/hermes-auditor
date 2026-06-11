"""加载并校验 risk_summary fixtures。

Auditor 项目的第一道防线：在任何节点跑之前，先确认 fixture 真的符合
schemas/risk-summary.schema.json。fixture 不合规就直接报错，不进状态机。
"""

from __future__ import annotations

import json
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
