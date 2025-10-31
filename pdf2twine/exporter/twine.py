"""Export helpers for generating Twee and Twine outputs."""
from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

logger = logging.getLogger(__name__)


def sanitize_passage_name(name: str) -> str:
    """Sanitize passage name for Twee format, preserving spaces."""

    cleaned = name.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    cleaned = cleaned.replace('"', "").replace("'", "")
    sanitized = re.sub(r"[^a-zA-Z0-9 \-_]", "_", cleaned)
    sanitized = re.sub(r" {2,}", " ", sanitized).strip()

    if len(sanitized) > 50:
        sanitized = sanitized[:47] + "..."

    return sanitized or "unnamed_passage"


def escape_twee_content(content: str) -> str:
    """Escape content for Twee format."""

    escaped = content.replace("[[", r"\[\[").replace("]]", r"\]\]")
    lines = [line.strip() for line in escaped.split("\n") if line.strip()]
    return "\n".join(lines)


def _build_outgoing_lookup(edges: Sequence[Mapping[str, str]]) -> Dict[str, List[Mapping[str, str]]]:
    lookup: Dict[str, List[Mapping[str, str]]] = {}
    for edge in edges:
        lookup.setdefault(edge["source"], []).append(edge)
    return lookup


def write_twee(graph: Dict, output_path: str, story_title: str = "Generated Story") -> None:
    """Write a narrative graph to Twee 3 format."""

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        raise ValueError("Graph contains no nodes")

    outgoing_edges = _build_outgoing_lookup(edges)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        for node in nodes:
            node_id = node["id"]
            passage_name = sanitize_passage_name(node["label"])
            content = escape_twee_content(node["text"])

            position_data = ""
            if "position" in node:
                pos = node["position"]
                position_data = f" <{pos['x']},{pos['y']}>"

            handle.write(f":: {passage_name}{position_data}\n\n")
            handle.write(content)
            handle.write("\n\n")

            connected_edges = outgoing_edges.get(node_id, [])
            if connected_edges:
                handle.write("---\n\n")
                for edge in connected_edges:
                    target_node = next((n for n in nodes if n["id"] == edge["target"]), None)
                    if not target_node:
                        continue
                    target_name = sanitize_passage_name(target_node["label"])
                    link_text = edge.get("label", "Continue")
                    handle.write(f"[[{link_text}|{target_name}]]\n")
                handle.write("\n")

            handle.write("\n")

    logger.info("Wrote Twee file with %s passages to %s", len(nodes), output_path)


def write_twine_story(graph: Dict, output_path: str, story_title: str = "Generated Story") -> None:
    """Write a narrative graph to Twine 2 HTML format."""

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        raise ValueError("Graph contains no nodes")

    outgoing_edges = _build_outgoing_lookup(edges)
    passages = []

    for index, node in enumerate(nodes):
        node_id = node["id"]
        passage_name = sanitize_passage_name(node["label"])
        content = escape_twee_content(node["text"])
        connected_edges = outgoing_edges.get(node_id, [])
        if connected_edges:
            content += "\n\n---\n\n"
            for edge in connected_edges:
                target_node = next((n for n in nodes if n["id"] == edge["target"]), None)
                if not target_node:
                    continue
                target_name = sanitize_passage_name(target_node["label"])
                link_text = edge.get("label", "Continue")
                content += f"[[{link_text}|{target_name}]]\n"

        position = node.get(
            "position",
            {"x": 100 + (index % 10) * 300, "y": 100 + (index // 10) * 200},
        )

        passages.append(
            {
                "text": content,
                "links": [],
                "name": passage_name,
                "pid": str(index + 1),
                "position": position,
                "tags": [],
            }
        )

    story_data = {
        "passages": passages,
        "name": story_title,
        "startnode": "1",
        "creator": "pdf2twine",
        "creator-version": "1.0.0",
        "ifid": str(uuid.uuid4()).upper(),
    }

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{story_title}</title>
    <meta charset="utf-8">
</head>
<body>
    <tw-storydata name="{story_title}"
                   startnode="1"
                   creator="pdf2twine"
                   creator-version="1.0.0"
                   ifid="{story_data['ifid']}"
                   zoom="1"
                   format="Harlowe"
                   format-version="3.3.0">

        <style role="stylesheet" id="twine-user-stylesheet" type="text/twine-css">
        </style>

        <script role="script" id="twine-user-script" type="text/twine-javascript">
        </script>
"""

    for passage in passages:
        position = passage["position"]
        html_content += f"""
        <tw-passagedata pid="{passage['pid']}"
                       name="{passage['name']}"
                       tags=""
                       position="{position['x']},{position['y']}"
                       size="100,100">{passage['text']}</tw-passagedata>"""

    html_content += """
    </tw-storydata>

    <script title="Twine engine code" data-main="harlowe">
    console.log("Story data loaded");
    </script>
</body>
</html>"""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")

    logger.info("Wrote Twine HTML file with %s passages to %s", len(nodes), output_path)


def convert_graph_to_twine(graph: Dict, output_dir: str, story_title: str = "Generated Story") -> Dict[str, str]:
    """Convert a narrative graph to both Twee and HTML formats."""

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    safe_title = sanitize_passage_name(story_title.replace(" ", "_"))
    twee_path = output_path / f"{safe_title}.twee"
    html_path = output_path / f"{safe_title}.html"

    write_twee(graph, str(twee_path), story_title)
    write_twine_story(graph, str(html_path), story_title)

    return {
        "twee": str(twee_path),
        "html": str(html_path),
        "title": story_title,
    }


__all__ = ["write_twee", "write_twine_story", "convert_graph_to_twine", "sanitize_passage_name", "escape_twee_content"]
