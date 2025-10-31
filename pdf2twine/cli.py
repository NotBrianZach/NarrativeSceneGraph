#!/usr/bin/env python3
"""PDF2Twine command-line interface."""
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional

from pdf2twine.pipeline import PipelineConfig, PdfToTwinePipeline


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def main():
    """Main entry point for pdf2twine CLI."""
    parser = argparse.ArgumentParser(
        description="Convert PDF documents to Twine interactive stories",
        epilog="Example: pdf2twine story.pdf output.twee --with-quiz --layout flow"
    )

    # Required arguments
    parser.add_argument('input_file', type=Path, help='Input PDF file path')
    parser.add_argument('output_file', type=Path, help='Output Twee file path')

    # Segmentation options
    parser.add_argument('--llm', action='store_true',
                       help='Force use of LLM for text segmentation')
    parser.add_argument('--force-llm', action='store_true',
                       help='Alias for --llm (backward compatibility)')
    parser.add_argument('--max-scenes', type=int, default=200,
                       help='Maximum number of scenes (default: 200)')

    # Graph generation options
    parser.add_argument('--model', type=str, default='openai/gpt-4o-mini',
                       help='LLM model to use (default: openai/gpt-4o-mini)')
    parser.add_argument('--title', type=str, default=None,
                       help='Story title (default: based on filename)')

    # Layout options
    parser.add_argument('--layout', choices=['random', 'flow'], default='random',
                       help='Node layout algorithm (default: random)')
    parser.add_argument('--canvas-width', type=int, default=4000,
                       help='Canvas width for node positioning (default: 4000)')
    parser.add_argument('--canvas-height', type=int, default=3000,
                       help='Canvas height for node positioning (default: 3000)')

    # Output options
    parser.add_argument('--with-quiz', action='store_true',
                       help='Generate quiz questions for each scene')
    parser.add_argument('--dot-output', type=Path, default=None,
                       help='Also output DOT graph file')
    parser.add_argument('--html-output', type=Path, default=None,
                       help='Also output Twine HTML file')

    # Debugging options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Validate arguments
    if not args.input_file.exists():
        print(f"Error: Input file {args.input_file} does not exist", file=sys.stderr)
        return 1

    if not args.input_file.suffix.lower() == '.pdf':
        print(f"Error: Input file must be a PDF", file=sys.stderr)
        return 1

    # Set story title
    story_title = args.title or args.input_file.stem.replace('_', ' ').title()

    # Show plan if dry run
    if args.dry_run:
        print("PDF2Twine Execution Plan:")
        print(f"  Input: {args.input_file}")
        print(f"  Output: {args.output_file}")
        print(f"  Title: {story_title}")
        print(f"  Segmentation: {'LLM' if (args.llm or args.force_llm) else 'Heuristic'}")
        print(f"  Max scenes: {args.max_scenes}")
        print(f"  Model: {args.model}")
        print(f"  Layout: {args.layout}")
        print(f"  With quiz: {args.with_quiz}")
        if args.dot_output:
            print(f"  DOT output: {args.dot_output}")
        if args.html_output:
            print(f"  HTML output: {args.html_output}")
        return 0

    try:
        config = PipelineConfig(
            model_id=args.model,
            max_scenes=args.max_scenes,
            layout=args.layout,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            with_quiz=args.with_quiz,
            force_llm_segmentation=args.llm or args.force_llm,
        )
        pipeline = PdfToTwinePipeline(config)

        graph = pipeline.build_graph(args.input_file)
        pipeline.export_outputs(
            graph,
            args.output_file,
            story_title,
            dot_output=args.dot_output,
            html_output=args.html_output,
        )

        # Success summary
        print(f"✅ Successfully generated Twine story:")
        print(f"   📖 Title: {story_title}")
        print(f"   📄 Scenes: {len([n for n in graph['nodes'] if 'quiz' not in n.get('tags', [])])}")
        if args.with_quiz:
            quiz_count = len([n for n in graph['nodes'] if 'quiz' in n.get('tags', [])])
            print(f"   ❓ Quizzes: {quiz_count}")
        print(f"   🔗 Connections: {len(graph['edges'])}")
        print(f"   📁 Output: {args.output_file}")

        if args.dot_output:
            print(f"   📊 DOT graph: {args.dot_output}")
        if args.html_output:
            print(f"   🌐 HTML story: {args.html_output}")

        return 0

    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=args.verbose)
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
