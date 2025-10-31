"""High-level orchestration for converting PDFs into Twine stories."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from pdf2twine.exporter import (
    assign_flow_coordinates,
    assign_random_coordinates,
    write_twee,
    write_twine_story,
)
from pdf2twine.graph import extract_narrative_graph, summarize_scenes
from pdf2twine.graph.serialize import to_dot
from pdf2twine.loader import extract
from pdf2twine.quiz import add_quizzes_to_graph
from pdf2twine.segmenter import split_auto

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration values for :class:`PdfToTwinePipeline`."""

    model_id: str = "openai/gpt-4o-mini"
    max_scenes: int = 200
    layout: str = "random"
    canvas_width: int = 4000
    canvas_height: int = 3000
    with_quiz: bool = False
    force_llm_segmentation: bool = False


class PdfToTwinePipeline:
    """Facade that coordinates the individual processing steps."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()

    def build_graph(self, input_path: Path) -> Dict:
        """Run extraction, segmentation, summarisation and graph building."""

        logger.info("Extracting text from %s", input_path)
        text = extract(str(input_path))
        logger.info("Extracted %s characters", len(text))

        logger.info("Segmenting text into scenes")
        scenes = split_auto(
            text,
            force_llm=self.config.force_llm_segmentation,
            max_scenes=self.config.max_scenes,
            model_id=self.config.model_id,
        )
        logger.info("Created %s scenes", len(scenes))
        if not scenes:
            raise ValueError("No scenes were extracted from the document")

        logger.info("Summarizing scenes with LLM")
        summarized_scenes = summarize_scenes(scenes, model_id=self.config.model_id)
        logger.info("Summarized %s scenes", len(summarized_scenes))

        logger.info("Extracting narrative relationships")
        graph = extract_narrative_graph(
            summarized_scenes,
            model_id=self.config.model_id,
        )
        logger.info(
            "Created graph with %s nodes and %s edges",
            len(graph["nodes"]),
            len(graph["edges"]),
        )

        if self.config.with_quiz:
            logger.info("Generating quizzes for scenes")
            graph = add_quizzes_to_graph(graph, model_id=self.config.model_id)
            logger.info("Added quiz nodes, total nodes now: %s", len(graph["nodes"]))

        logger.info("Assigning %s layout coordinates", self.config.layout)
        if self.config.layout == "flow":
            graph = assign_flow_coordinates(
                graph,
                self.config.canvas_width,
                self.config.canvas_height,
            )
        else:
            graph = assign_random_coordinates(
                graph,
                self.config.canvas_width,
                self.config.canvas_height,
            )

        return graph

    def export_outputs(
        self,
        graph: Dict,
        output_file: Path,
        story_title: str,
        *,
        dot_output: Optional[Path] = None,
        html_output: Optional[Path] = None,
    ) -> None:
        """Persist the generated graph to the requested output formats."""

        output_file.parent.mkdir(parents=True, exist_ok=True)
        write_twee(graph, str(output_file), story_title)

        if dot_output:
            dot_output.parent.mkdir(parents=True, exist_ok=True)
            dot_output.write_text(to_dot(graph, story_title.replace(" ", "_")), encoding="utf-8")

        if html_output:
            html_output.parent.mkdir(parents=True, exist_ok=True)
            write_twine_story(graph, str(html_output), story_title)


__all__ = ["PipelineConfig", "PdfToTwinePipeline"]
