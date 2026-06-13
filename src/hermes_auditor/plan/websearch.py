"""PLAN discovery 的 live web 接缝:staged(默认)| web(真全网搜索)。

切换:环境变量 `HERMES_DISCOVERY`(默认 `staged`),仿 `HERMES_BRAIN` 的接缝风格:
- `staged` —— 用 fixture 里的 staged 语料(确定性、零网络,平时测试 / 回归)。
- `web`    —— `web_untrusted` 类型的 facet 把语料换成 gpt-5.5 服务端 `web_search`
              拉回的实时摘录;registry / official_docs 仍走本地 —— 权威来源本来就
              不该从公网取,这是 provenance 分级的一部分。

不变量(不要破坏):
- 拉回的内容一律以 `web_untrusted` 进管线,confidence 由代码盖章,模型不能自升;
  收款地址永远不能只凭网页内容确立(_synthesize 要求权威印证)。
- fetch 调用只带 web_search 一个工具 —— 动钱能力物理不存在(quarantine 同款)。
- 失败回退 staged 语料,必须留痕(FALLBACK 标记进 trace),回退不静默。
"""

from __future__ import annotations

import os

from . import llm

DISCOVERY = os.getenv("HERMES_DISCOVERY", "staged")

# 回退标记:live 搜索失败、回退 staged 语料时打进 trace。
WEB_FALLBACK_MARK = "live web 搜索失败回退 staged"

_FETCH_INSTRUCTIONS = (
    "你是 Hermes PLAN 的 web 搜索取材 subagent。用 web_search 查给定主题的真实供应商报价,"
    "把搜到的内容整理成纯文本语料,供下游 agent 抽取。规则:\n"
    "1. 每条结果一个块:先 `url: <来源链接>`,再 `excerpt: <页面上的原文摘录>`(忠实摘录,不改写)。\n"
    "2. 摘录后追加一行归一化记录:`vendor: <名称> | price: <页面原话的价格> | pay-to: <0x地址或 n/a>`。\n"
    "3. pay-to 只在页面原文里真的出现 0x 地址时才填;绝不编造、绝不推断地址,没有就写 n/a。\n"
    "4. 价格照页面原话写(含币种/周期),不换算、不编造。找不到报价的结果直接略过。\n"
    "5. 最多 5 条结果,只输出语料本身,不要评论。"
)


def use_web() -> bool:
    return DISCOVERY == "web"


def fetch_web_corpus(query: str) -> str:
    """经网关 web_search 拉回实时语料。失败抛异常(由调用方回退 staged 并留痕)。"""
    print(f"  … live web 搜索中: {query!r}(gpt-5.5 服务端 web_search,约 20-40s)")
    return llm.complete_with_web_search(_FETCH_INSTRUCTIONS, f"搜索主题: {query}")
