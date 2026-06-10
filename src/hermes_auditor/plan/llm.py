"""agent 脑的接缝:stub(确定性,免 token)| gpt-5.5(经 ai.input.im 网关)。

切换:环境变量 `HERMES_BRAIN`(默认 `stub`):
- `stub`     —— 确定性逻辑,不调任何模型(平时测试用,免 token)。
- `gpt-5.5`  —— 经 OpenAI 兼容 responses API 调 gpt-5.5。

为什么走网关:直连 api.openai.com 在本环境被区域封锁(403),网关 `ai.input.im` 用
`OPENAI_API_KEY`(env)鉴权。GLM-5.1 等其他 OpenAI 兼容脑只需改 base_url/model。
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Any

BRAIN = os.getenv("HERMES_BRAIN", "stub")
_MODEL = os.getenv("HERMES_MODEL", "gpt-5.5")
_BASE_URL = os.getenv("HERMES_BASE_URL", "https://ai.input.im/v1")


def use_model() -> bool:
    """非 stub 即接真脑。"""
    return BRAIN != "stub"


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI

    return OpenAI(base_url=_BASE_URL)


def complete_json(instructions: str, user: str) -> dict[str, Any]:
    """调真脑,返回解析后的 JSON dict。失败抛异常(由调用方决定 fallback)。"""
    r = _client().responses.create(
        model=_MODEL,
        instructions=instructions,
        input=user,
        reasoning={"effort": "low"},
        max_output_tokens=3000,
    )
    txt = (r.output_text or "").strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        raise ValueError(f"模型未返回 JSON: {txt[:120]}")
    return json.loads(m.group(0))
