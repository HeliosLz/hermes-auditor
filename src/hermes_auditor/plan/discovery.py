"""PLAN discovery: fan-out 搜索 marketplace 语料 -> 代码层合并 -> 产出 vendors。

这个层只负责「发现候选」,不碰 pipeline 的比价 / 审计结构。
stub 路径完全确定性、零网络;真脑接缝仿 agents.py,失败回退后打 FALLBACK_MARK。

语料来源由 websearch.py 的 `HERMES_DISCOVERY=staged|web` 决定:web 模式下
`web_untrusted` facet 换成实时搜索拉回的语料,其余 facet 仍走 staged(权威来源不上公网)。
vendor 记录允许 pay-to 缺失(`n/a`)—— 真实网页报价多数没有链上地址;无地址候选
进比价表但被判「无可用地址 → 不可信」,永远选不中,只提供价格参照。
"""

from __future__ import annotations

import os
import re
from typing import Any

from . import agents, llm, websearch
from .types import Source, SourceType, Vendor

# 第 2 轮地址解析每轮最多对几家「有价无址」候选深挖(避免无限循环 / 控制延迟)。
_RESOLVE_CAP = int(os.getenv("HERMES_RESOLVE_CAP", "2"))

_ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
_VENDOR_LINE_RE = re.compile(
    r"^vendor:\s*(?P<name>[^|]+?)\s*\|\s*price:\s*(?P<price>[^|]+?)\s*\|\s*pay-to:\s*(?P<address>0x[a-fA-F0-9]{40}|n/a)\b.*$",
    re.IGNORECASE,
)


class _SearchBatch(list[Vendor]):
    """内部批次容器:保持 list 语义,顺手带一个 fallback 标记。"""

    fallback_mark: str | None

    def __init__(self, vendors: list[Vendor], fallback_mark: str | None = None):
        super().__init__(vendors)
        self.fallback_mark = fallback_mark


def _has_addr(text: str) -> bool:
    return bool(_ADDR_RE.search(text))


def _context_doc(lines: list[str], index: int) -> str:
    """保留 vendor 那一行 + 上下文,原文不改写。"""
    start = max(0, index - 1)
    end = min(len(lines), index + 2)
    return "\n".join(lines[start:end])


def _vendor_hits_from_corpus(corpus: str, facet: str, source_type: SourceType) -> list[Vendor]:
    lines = corpus.splitlines()
    vendors: list[Vendor] = []
    for idx, line in enumerate(lines):
        m = _VENDOR_LINE_RE.match(line)
        if not m:
            continue
        name = m.group("name").strip()
        price = m.group("price").strip()
        doc = _context_doc(lines, idx)
        vendors.append(
            Vendor(
                name=name,
                price=price,
                sources=[
                    Source(
                        label=f"{facet}·search",
                        source_type=source_type,
                        doc=doc,
                    )
                ],
            )
        )
    return vendors


def _doc_for_model_hit(corpus: str, name: str, price: str, address: str) -> str:
    """按模型抽到的字段回到语料里找原始上下文。"""
    lines = corpus.splitlines()
    name_low = name.casefold().strip()
    price_low = price.strip()
    address_low = address.casefold().strip()

    def _matches(line: str) -> bool:
        low = line.casefold()
        return (
            name_low
            and name_low in low
            and price_low in line
            and address_low in low
        )

    for idx, line in enumerate(lines):
        if _matches(line):
            return _context_doc(lines, idx)
    for idx, line in enumerate(lines):
        low = line.casefold()
        if address_low and address_low in low:
            return _context_doc(lines, idx)
    for idx, line in enumerate(lines):
        low = line.casefold()
        if name_low and name_low in low:
            return _context_doc(lines, idx)
    # 语料里找不到出处 = 模型编造了 vendor。fail-closed:判定本次输出失败,
    # 走 run_search_agent 的回退路径(stub + FALLBACK 标记),不给幻觉 vendor 配证据。
    raise ValueError(f"模型抽取的 vendor 在语料中找不到出处: {name}")


def _stub_search_agent(facet: str, source_type: SourceType, corpus: str) -> list[Vendor]:
    return _vendor_hits_from_corpus(corpus, facet, source_type)


def _model_search_agent(facet: str, source_type: SourceType, intent: str, corpus: str) -> list[Vendor]:
    instructions = (
        "你是 Hermes PLAN 的搜索 subagent。只看给你的这一份语料,抽取 vendor 列表。"
        "你没有任何动钱工具。只输出 JSON:{\"vendors\":[{\"name\":\"...\",\"price\":\"...\",\"address\":\"0x... 或空串\"}]}"
        "address 只在语料原文出现 0x 地址时才填,绝不编造;没有就填空串。"
    )
    user = f"facet: {facet}\nuser_intent: {intent}\ncorpus:\n{corpus}"
    out = llm.complete_json(instructions, user)
    rows = out.get("vendors", [])
    if not isinstance(rows, list):
        raise ValueError("模型未返回 vendors 数组")

    vendors: list[Vendor] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("vendors 数组元素不是对象")
        name = str(row.get("name", "")).strip()
        price = str(row.get("price", "")).strip()
        address = str(row.get("address", "")).strip()
        if not name or not price:
            raise ValueError("vendor 字段不完整")
        if address and not _has_addr(address):
            raise ValueError(f"vendor address 非法(既不是 0x 地址也不是空): {address}")
        vendors.append(
            Vendor(
                name=name,
                price=price,
                sources=[
                    Source(
                        label=f"{facet}·search",
                        source_type=source_type,
                        doc=_doc_for_model_hit(corpus, name, price, address),
                    )
                ],
            )
        )
    return vendors


def run_search_agent(facet: str, source_type: SourceType, intent: str, corpus: str) -> list[Vendor]:
    """Fan-out subagent:单 facet 搜索 staged 语料,抽 vendor 候选。"""
    if llm.use_model():
        try:
            return _SearchBatch(_model_search_agent(facet, source_type, intent, corpus))
        except Exception as e:  # 真脑失败 -> 回退 stub,并保留 fallback 标记
            batch = _SearchBatch(_stub_search_agent(facet, source_type, corpus))
            batch.fallback_mark = f"[{agents.FALLBACK_MARK}: {type(e).__name__}]"
            return batch
    return _SearchBatch(_stub_search_agent(facet, source_type, corpus))


def discover_vendors(intent: str, facets: list[dict[str, Any]]) -> tuple[list[Vendor], list[str]]:
    """fan-out 搜索所有 facet,再由代码层按 vendor name 去重合并 sources。"""
    trace_lines: list[str] = []
    merged: list[Vendor] = []
    seen: dict[str, Vendor] = {}

    # 真实实现这里应并行 fan-out;stub 路径顺序跑,形状先摆正。
    for facet in facets:
        facet_name = str(facet["facet"])
        source_type = facet["source_type"]
        corpus = str(facet["corpus"])
        # live web 接缝:只换 web_untrusted facet 的语料;registry/official 仍走 staged
        # (权威来源不上公网 —— provenance 分级)。失败回退 staged,留痕不静默。
        if websearch.use_web() and source_type == "web_untrusted":
            query = str(facet.get("query") or intent)
            try:
                corpus = websearch.fetch_web_corpus(query)
                trace_lines.append(
                    f"[search:{facet_name}] live web 语料就绪({len(corpus)} 字,query={query!r})"
                )
            except Exception as e:
                trace_lines.append(
                    f"[search:{facet_name}] ⚠ [{websearch.WEB_FALLBACK_MARK}: {type(e).__name__}]"
                )
        batch = run_search_agent(facet_name, source_type, intent, corpus)
        summary = ", ".join(f"{v.name}({v.price})" for v in batch) if batch else "(none)"
        trace_lines.append(f"[search:{facet_name}] 命中 {len(batch)} 家: {summary}")
        if getattr(batch, "fallback_mark", None):
            trace_lines.append(f"[search:{facet_name}] {batch.fallback_mark}")
        for vendor in batch:
            key = vendor.name.strip().casefold()
            existing = seen.get(key)
            if existing is None:
                seen[key] = vendor
                merged.append(vendor)
            else:
                if vendor.price.strip() != existing.price.strip():
                    # 价格冲突是审计信号:合并保留先到的报价,但冲突必须留痕。
                    trace_lines.append(
                        f"[merge] 价格冲突: {existing.name} 已记 {existing.price},"
                        f"{facet_name} 报 {vendor.price}(保留前者,冲突留痕)"
                    )
                existing.sources.extend(vendor.sources)

    trace_lines.append(f"[merge] 共 {len(merged)} 家候选(去重后)")

    # 第 2 轮:对「有价无址」的候选做专项地址解析(只 web 模式)。
    # 这是「继续找」—— 但只加深搜索,不降信任门槛:找到的地址一律 web_untrusted,
    # 公网出处永不自动获得权威背书(provenance 由工具盖章),所以仍选不中,只是
    # 从「无可用地址」变成「有址但无权威背书」—— agent 真的多找了一轮,闸照样守住。
    if websearch.use_web():
        addressless = [v for v in merged if not _vendor_has_address(v)]
        for v in addressless[:_RESOLVE_CAP]:
            addr, note = resolve_vendor_address(v.name, intent)
            if addr:
                v.sources.append(
                    Source(
                        label=f"{v.name}·resolve",
                        source_type="web_untrusted",
                        doc=f"专项搜索命中 pay-to {addr}(来源:公网搜索,未经权威背书)",
                    )
                )
                trace_lines.append(
                    f"[resolve:{v.name}] 第2轮专项找地址 → 命中 {addr}(web_untrusted,无权威背书,仍不可选)"
                )
            else:
                trace_lines.append(f"[resolve:{v.name}] 第2轮专项找地址 → {note}")
        if len(addressless) > _RESOLVE_CAP:
            trace_lines.append(
                f"[resolve] 还有 {len(addressless) - _RESOLVE_CAP} 家未做二轮"
                f"(本轮上限 {_RESOLVE_CAP},避免无限循环;HERMES_RESOLVE_CAP 可调)"
            )

    return merged, trace_lines


def _vendor_has_address(vendor: Vendor) -> bool:
    return any(_ADDR_RE.search(s.doc) for s in vendor.sources)


def resolve_vendor_address(vendor_name: str, intent: str) -> tuple[str | None, str]:
    """第 2 轮专项地址解析:深挖搜索,不降信任门槛 —— 命中也只算 web_untrusted。

    返回 (地址 | None, 留痕说明)。地址抽取用正则(不靠模型自报),出处由调用方盖 web_untrusted。
    """
    try:
        corpus = websearch.fetch_targeted_address(vendor_name, intent)
    except Exception as e:
        return None, f"[{websearch.WEB_FALLBACK_MARK}: {type(e).__name__}]"
    m = _ADDR_RE.search(corpus)
    if m:
        return m.group(0), ""
    return None, "未找到官方链上收款地址(拒绝用论坛/第三方猜测凑数)"


def _print_vendor(vendor: Vendor) -> None:
    print(f"- {vendor.name} | price={vendor.price}")
    for src in vendor.sources:
        print(f"  source={src.label} / {src.source_type}")
        print(f"  doc={src.doc}")


def main() -> None:
    from hermes_auditor.fixtures_io import load_marketplace_input

    data = load_marketplace_input("marketplace")
    vendors, trace_lines = discover_vendors(data["user_intent"], data["facets"])
    print(f"vendors={len(vendors)}")
    for line in trace_lines:
        print(line)
    for vendor in vendors:
        _print_vendor(vendor)
    cheap = next((v for v in vendors if v.name == "CheapData"), None)
    has_note = bool(cheap and any("NOTE FOR AI AGENTS" in s.doc for s in cheap.sources))
    print(f"[check] CheapData doc contains NOTE FOR AI AGENTS: {has_note}")


if __name__ == "__main__":
    main()
