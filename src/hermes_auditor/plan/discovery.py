"""PLAN discovery: fan-out 搜索 staged marketplace 语料 -> 代码层合并 -> 产出 vendors。

这个层只负责「发现候选」,不碰 pipeline 的比价 / 审计结构。
stub 路径完全确定性、零网络;真脑接缝仿 agents.py,失败回退后打 FALLBACK_MARK。
"""

from __future__ import annotations

import re
from typing import Any

from . import agents, llm
from .types import Source, SourceType, Vendor

_ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")
_VENDOR_LINE_RE = re.compile(
    r"^vendor:\s*(?P<name>[^|]+?)\s*\|\s*price:\s*(?P<price>[^|]+?)\s*\|\s*pay-to:\s*(?P<address>0x[a-fA-F0-9]{40})\b.*$",
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
        address = m.group("address").strip()
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
        "你没有任何动钱工具。只输出 JSON:{\"vendors\":[{\"name\":\"...\",\"price\":\"...\",\"address\":\"0x...\"}]}"
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
        if not name or not price or not _has_addr(address):
            raise ValueError("vendor 字段不完整")
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
    return merged, trace_lines


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
