"""Turn an uploaded roadmap (Markdown or JSON) into a tree of topics.

Markdown rules:
  * The first `# H1` (if it comes before any other heading) is the roadmap title.
  * Other headings nest by level (`##` > `###` > ...).
  * Bullet / numbered list items nest under the latest heading, by indentation.
  * Plain text lines become the description of the item above them
    (or of the roadmap, before the first item).

JSON: {"title": str, "description"?: str, "children": [{"title", "description"?, "children"?}]}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
LIST_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?(.+?)\s*$")


class RoadmapParseError(ValueError):
    pass


@dataclass
class ParsedNode:
    title: str
    description: str = ""
    children: list[ParsedNode] = field(default_factory=list)


@dataclass
class ParsedRoadmap:
    title: str
    description: str = ""
    children: list[ParsedNode] = field(default_factory=list)

    def count(self) -> int:
        def walk(nodes: list[ParsedNode]) -> int:
            return sum(1 + walk(n.children) for n in nodes)

        return walk(self.children)


def parse_roadmap(source: str, fallback_title: str = "Untitled roadmap") -> ParsedRoadmap:
    text = source.strip()
    if not text:
        raise RoadmapParseError("Roadmap is empty")
    if text[0] in "{[":
        return _parse_json(text, fallback_title)
    return _parse_markdown(text, fallback_title)


def _parse_json(text: str, fallback_title: str) -> ParsedRoadmap:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RoadmapParseError(f"Invalid JSON: {exc}") from exc

    def to_node(obj: object, path: str) -> ParsedNode:
        if isinstance(obj, str):
            return ParsedNode(title=obj)
        if not isinstance(obj, dict) or not str(obj.get("title", "")).strip():
            raise RoadmapParseError(f"Item at {path} needs a non-empty 'title'")
        kids = obj.get("children") or []
        if not isinstance(kids, list):
            raise RoadmapParseError(f"'children' at {path} must be a list")
        return ParsedNode(
            title=str(obj["title"]).strip(),
            description=str(obj.get("description") or "").strip(),
            children=[to_node(c, f"{path}.children[{i}]") for i, c in enumerate(kids)],
        )

    if isinstance(data, list):
        roadmap = ParsedRoadmap(title=fallback_title)
        roadmap.children = [to_node(c, f"[{i}]") for i, c in enumerate(data)]
    elif isinstance(data, dict):
        roadmap = ParsedRoadmap(
            title=str(data.get("title") or fallback_title).strip(),
            description=str(data.get("description") or "").strip(),
            children=[to_node(c, f"children[{i}]") for i, c in enumerate(data.get("children") or [])],
        )
    else:
        raise RoadmapParseError("JSON roadmap must be an object or a list")

    if not roadmap.children:
        raise RoadmapParseError("Roadmap has no topics")
    return roadmap


def _parse_markdown(text: str, fallback_title: str) -> ParsedRoadmap:
    lines = text.splitlines()
    roadmap = ParsedRoadmap(title=fallback_title)

    # Title: first H1 before any other heading/list.
    start = 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            roadmap.title = m.group(2).strip()
            start = i + 1
        break

    body = lines[start:]
    heading_levels = [len(m.group(1)) for l in body if (m := HEADING_RE.match(l))]
    base_level = min(heading_levels) if heading_levels else 1

    # Stack of (depth, node). Root depth is -1.
    stack: list[tuple[int, ParsedNode | ParsedRoadmap]] = [(-1, roadmap)]
    heading_depth = -1  # depth of the latest heading, list items go below it
    list_indents: list[int] = []  # indentation stack for current list block
    desc_target: ParsedNode | ParsedRoadmap = roadmap

    def attach(depth: int, node: ParsedNode) -> None:
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1]
        parent.children.append(node)
        stack.append((depth, node))

    for line in body:
        if not line.strip():
            continue

        if m := HEADING_RE.match(line):
            depth = len(m.group(1)) - base_level
            node = ParsedNode(title=m.group(2).strip())
            attach(depth, node)
            heading_depth = depth
            list_indents = []
            desc_target = node
            continue

        if m := LIST_RE.match(line):
            indent = len(m.group(1).expandtabs(4))
            while list_indents and list_indents[-1] > indent:
                list_indents.pop()
            if not list_indents or list_indents[-1] < indent:
                list_indents.append(indent)
            depth = heading_depth + len(list_indents)
            node = ParsedNode(title=m.group(2).strip())
            attach(depth, node)
            desc_target = node
            continue

        sep = "\n" if desc_target.description else ""
        desc_target.description += sep + line.strip()

    if not roadmap.children:
        raise RoadmapParseError(
            "No topics found. Use headings (## Topic) or bullet lists (- Topic)."
        )
    return roadmap
