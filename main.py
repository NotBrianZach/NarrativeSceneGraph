#! /usr/bin/env python
if __name__ != "__main__":
    raise Exception("program is not a module; execute it directly")

import sys
import os
import time
import logging
from pathlib import Path

try:
    API_TOKEN = os.environ['OPENROUTER_API_KEY']
except EnvironmentError as e:
    raise EnvironmentError(f"Error: {e}")

USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
FORMATS = ('pdf',)
MODELS = ('openai/gpt-4o',)
OUT_FOLDER = Path("out")

import networkx as nx

try:
    fname: str = sys.argv[1]
    model: str = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e

fextension = fname[fname.rfind('.') + 1:]
if fextension not in FORMATS:
    raise ValueError("unavailable file format; choose from " + str(FORMATS))

# Delayed imports to respect the check above
from marker.converters.pdf import PdfConverter
from marker.modelws import create_model_dict
from marker.output import text_from_rendered

logging.getLogger().setLevel(level=3)

FORMAT_CONVERTERS = {'pdf': PdfConverter}

import spacy
nlp = spacy.load("en_core_web_sm")


def context_aware_chunker(full_text: str, max_chunk_size: int = 4000):
    """
    Context-aware chunker that attempts to detect scene boundaries based on:
      - Paragraph structure
      - Named Entity changes (particularly GPE, LOC, DATE, TIME)
      - A maximum chunk size to avoid too-large scenes

    :param full_text: The entire novel’s text.
    :param max_chunk_size: The upper bound for chunk size (in characters).
    :return: A list of scene text segments.
    """

    # Split by paragraphs (very rough approach)
    paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]

    scenes = []
    current_scene = []
    current_scene_text = ""

    # Track the "current location/time" based on the last paragraph
    prev_location_time = None

    for p in paragraphs:
        # Add paragraph to a doc for NER analysis
        doc = nlp(p)
        # Extract any location/time mention in this paragraph
        location_time_entities = [
            ent.text for ent in doc.ents 
            if ent.label_ in ("GPE", "LOC", "FAC", "DATE", "TIME")
        ]

        # Decide whether to start a new scene if there's a strong shift
        # in location/time from one paragraph to the next
        # (You can make this more or less strict.)
        # If we detect new location/time info that isn't just a repeat of the old,
        # we consider that a potential boundary.
        has_new_location = False
        for loc_time in location_time_entities:
            if not prev_location_time or loc_time not in prev_location_time:
                has_new_location = True
                break

        # Also check length constraints
        projected_length = len(current_scene_text) + len(p)

        # If there's a big shift or the chunk is about to exceed max_chunk_size,
        # finalize the current scene and start a new one.
        if (has_new_location and current_scene_text) or (projected_length >= max_chunk_size):
            # Finalize the current scene
            scene_text = "\n".join(current_scene).strip()
            if scene_text:
                scenes.append(scene_text)
            
            # Reset for the new scene
            current_scene = []
            current_scene_text = ""

        # Accumulate paragraph
        current_scene.append(p)
        current_scene_text += p + "\n"

        # Update prev_location_time info
        if location_time_entities:
            # Keep a small set of relevant location/time tokens
            prev_location_time = set(location_time_entities)

    # Catch any trailing paragraphs as the final scene
    if current_scene:
        scenes.append("\n".join(current_scene).strip())

    return scenes


def build_scene_graph(scenes):
    """
    Build a directed graph of scenes:
      - Each index is a node (Scene #).
      - Directed edge from scene i to scene i+1.
    """
    G = nx.DiGraph()
    for i, scene_text in enumerate(scenes):
        # Add a node with the scene text as data
        G.add_node(i, text=scene_text)

    # Link scene i -> i+1 in a linear chain
    for i in range(len(scenes) - 1):
        G.add_edge(i, i + 1)

    return G


def export_graph_to_dot(G, output_path: Path):
    """
    Exports the directed graph to Graphviz DOT format.
    """
    nx.drawing.nx_pydot.write_dot(G, output_path)


def main():
    tstart = time.time()
    # 1. Convert PDF -> text
    converter = FORMAT_CONVERTERS[fextension](artifact_dict=create_model_dict())
    rendered = converter(fname)
    text, _, images = text_from_rendered(rendered)
    print(f"Parsing complete. Extracted {len(text)} characters.")
    print(f"Took:\t{round(time.time() - tstart, 2)}s (imports + parsing)")

    # 2. Chunk the text into "scenes" with context-aware logic
    print("Performing context-aware chunking...")
    scenes = context_aware_chunker(text, max_chunk_size=4000)
    print(f"Identified {len(scenes)} scene(s).")

    # 3. Build the directed graph
    print("Building directed graph of scenes...")
    G = build_scene_graph(scenes)

    # 4. Export the graph as .dot
    OUT_FOLDER.mkdir(exist_ok=True, parents=True)
    dot_path = OUT_FOLDER / "scenes.dot"
    export_graph_to_dot(G, dot_path)
    print(f"Scene graph exported to {dot_path.resolve()}.")


if __name__ == "__main__":
    main()

