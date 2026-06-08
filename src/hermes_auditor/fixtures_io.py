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
