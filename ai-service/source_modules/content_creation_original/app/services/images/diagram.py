"""Diagram + image services (spec #20).

Deterministic diagrams FIRST: the LLM produces a validated structured spec,
a pure-Python SVG renderer draws it (exact labels, no hallucinated pixels).
Generative images (Gemini) are for illustrations where exactness is not critical."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from ...core.exceptions import SchemaValidationError
from ...providers.llm.openrouter import llm


class DiagramSpec(BaseModel):
    kind: str = Field(pattern="^(flow|sequence)$")
    title: str = Field(max_length=120)
    nodes: list[dict] = Field(min_length=2, max_length=12)
    edges: list[dict] = Field(min_length=1, max_length=16)

    @field_validator("nodes")
    @classmethod
    def _nodes_ok(cls, values: list[dict]) -> list[dict]:
        ids = set()
        for node in values:
            if "id" not in node or "label" not in node:
                raise ValueError("node needs id + label")
            node["id"] = str(node["id"])[:12]
            node["label"] = str(node["label"])[:60]
            ids.add(node["id"])
        if len(ids) != len(values):
            raise ValueError("duplicate node ids")
        return values

    @field_validator("edges")
    @classmethod
    def _edges_ok(cls, values: list[dict]) -> list[dict]:
        for edge in values:
            edge["label"] = str(edge.get("label") or "")[:40]
        return values


def render_svg(spec: DiagramSpec) -> str:
    """Deterministic SVG — flow (vertical boxes+arrows) or sequence (lifelines)."""
    title = _esc(spec.title)
    if spec.kind == "sequence":
        return _sequence_svg(title, spec.nodes, spec.edges)
    return _flow_svg(title, spec.nodes, spec.edges)


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _wrap(label: str, width: int = 24) -> list[str]:
    words, lines, current = label.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width and current:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines[:3]


BOX_W, BOX_H, GAP = 300, 58, 46


def _flow_svg(title: str, nodes: list[dict], edges: list[dict]) -> str:
    total_h = 70 + len(nodes) * (BOX_H + GAP)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="{total_h}" '
           f'viewBox="0 0 720 {total_h}" font-family="Segoe UI, Arial, sans-serif">',
           f'<rect width="720" height="{total_h}" fill="#f8fafc"/>',
           f'<text x="360" y="34" text-anchor="middle" font-size="20" font-weight="700" '
           f'fill="#0f172a">{title}</text>']
    positions: dict[str, tuple[int, int]] = {}
    for i, node in enumerate(nodes):
        y = 60 + i * (BOX_H + GAP)
        x = (720 - BOX_W) // 2
        positions[node["id"]] = (x + BOX_W // 2, y)
        fill = "#2563eb" if i == 0 else ("#7c3aed" if i == len(nodes) - 1 else "#ffffff")
        text_fill = "#ffffff" if i in (0, len(nodes) - 1) else "#0f172a"
        svg.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="12" '
                   f'fill="{fill}" stroke="#94a3b8" stroke-width="1.5"/>')
        lines = _wrap(node["label"])
        start_y = y + BOX_H // 2 - (len(lines) - 1) * 9 + 5
        for li, line in enumerate(lines):
            svg.append(f'<text x="360" y="{start_y + li * 18}" text-anchor="middle" '
                       f'font-size="14" fill="{text_fill}">{_esc(line)}</text>')
    for edge in edges:
        src, dst = positions.get(edge["from"]), positions.get(edge["to"])
        if not src or not dst:
            continue
        y1, y2 = src[1] + BOX_H, dst[1]
        svg.append(f'<line x1="{src[0]}" y1="{y1}" x2="{dst[0]}" y2="{y2}" '
                   f'stroke="#475569" stroke-width="2" marker-end="url(#arrow)"/>')
        if edge.get("label"):
            mid = (y1 + y2) // 2
            svg.append(f'<rect x="{src[0] + 10}" y="{mid - 11}" width="{min(300, 9 * len(edge["label"]) + 14)}" '
                       f'height="20" rx="6" fill="#eef2ff" stroke="#c7d2fe"/>')
            svg.append(f'<text x="{src[0] + 17}" y="{mid + 3}" font-size="11.5" '
                       f'fill="#3730a3">{_esc(edge["label"])}</text>')
    svg.append('<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
               'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
               '<path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/></marker></defs></svg>')
    return "".join(svg)


def _sequence_svg(title: str, nodes: list[dict], edges: list[dict]) -> str:
    lanes = len(nodes[:6])
    lane_w = 170
    width = max(720, lanes * lane_w + 60)
    height = 120 + len(edges) * 56
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
           f'<text x="{width // 2}" y="34" text-anchor="middle" font-size="20" '
           f'font-weight="700" fill="#0f172a">{title}</text>']
    xs: dict[str, int] = {}
    for i, node in enumerate(nodes[:6]):
        x = 70 + i * lane_w + lane_w // 2
        xs[node["id"]] = x
        svg.append(f'<rect x="{x - 62}" y="56" width="124" height="40" rx="10" '
                   f'fill="#2563eb"/>')
        label_lines = _wrap(node["label"], 16)
        for li, line in enumerate(label_lines[:2]):
            svg.append(f'<text x="{x}" y="{72 + li * 14 + (0 if len(label_lines) > 1 else 6)}" '
                       f'text-anchor="middle" font-size="12" fill="#fff">{_esc(line)}</text>')
        svg.append(f'<line x1="{x}" y1="96" x2="{x}" y2="{height - 24}" '
                   f'stroke="#94a3b8" stroke-width="1.6" stroke-dasharray="5 4"/>')
    for i, edge in enumerate(edges):
        x1, x2 = xs.get(edge["from"]), xs.get(edge["to"])
        if x1 is None or x2 is None:
            continue
        y = 130 + i * 56
        svg.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#7c3aed" '
                   f'stroke-width="2" marker-end="url(#arrow2)"/>')
        if edge.get("label"):
            mid = (x1 + x2) // 2
            svg.append(f'<text x="{mid}" y="{y - 8}" text-anchor="middle" font-size="11.5" '
                       f'fill="#4c1d95">{_esc(edge["label"])}</text>')
    svg.append('<defs><marker id="arrow2" viewBox="0 0 10 10" refX="9" refY="5" '
               'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
               '<path d="M 0 0 L 10 5 L 0 10 z" fill="#7c3aed"/></marker></defs></svg>')
    return "".join(svg)


class DiagramService:
    async def create(self, *, topic: str, kind: str, learner: dict, level: str,
                     language: str, source_context: str,
                     style_hint: Optional[str]) -> tuple[str, DiagramSpec]:
        from ...prompts.templates import diagram_prompt
        wanted = kind if kind in {"flow", "sequence"} else "flow"
        system, task = diagram_prompt(topic, wanted, learner, level, language)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": (source_context + "\n\n" if source_context else "") + task}]
        spec = await llm.structured(messages, DiagramSpec, request_type="diagram_spec")
        node_ids = {n["id"] for n in spec.nodes}
        spec.edges = [e for e in spec.edges
                      if e.get("from") in node_ids and e.get("to") in node_ids]
        if not spec.edges:
            raise SchemaValidationError(detail_log="diagram edges reference unknown nodes")
        return render_svg(spec), spec


diagram_service = DiagramService()