#! /usr/bin/env python
import sys
import os
from pathlib import Path
import json
import time
import subprocess
import requests

if __name__ != "__main__":
    sys.exit("program is not a module; execute it directly")

# Retrieve the API token.
try:
    API_TOKEN = (os.environ.get("API_TOKEN") or
                 os.environ.get("OPENROUTER_API_KEY") or
                 Path('.API_TOKEN').read_text())
except FileNotFoundError:
    sys.exit(
        "provide the OpenRouter token through:\n"
        "- an environment variable `API_TOKEN`\n"
        "- a file `.API_TOKEN` containing it"
    )

# Setup configuration and constants.
OUT_DIR = Path("out")
FORMATS = ('pdf',)  # TODO: add more formats
MODELS = json.loads(Path('.models.json').read_text())['data']
MODEL_IDS = (model['id'] for model in MODELS)
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"

# Define prompts.
INITIAL_PROMPT = r'''# Narrative Scene Graph
Describe the following narrative as a directed acyclic graph in the DOT graph description language format. Start with a single root node, that may branch out, especially when there are scenes or sub-narratives occurring in parallel. These branches MUST converge to a final end node, corresponding to the end of the narrative.
DON'T describe the document or the workings of directed acyclic graphs.
DON'T fill the nodes with anything outside of the document. Don't refer to general knowledge, historical events, or facts, if they're not in the text. Quote EXCLUSIVELY the text contained in the document. On top of that, DON'T adjust the labels or quotes, even if to make them more concise. Again, they must quote the text directly.
Don't repeat the same node or scene. If they happen to repeat in the narrative itself, merge them into the same node.

## Example graph for fiction writing
```dot
digraph HeinleinCrookedHouse {{
    rankdir=TB;

    // Root node: Beginning of the story
    Start [label="Quintus Teal proposes a tesseract house", shape=ellipse];

    // Initial branching paths
    Design [label="Teal explains 4D geometry to Homer and Matson", shape=box];
    Build [label="House is built as a 3D projection of a tesseract", shape=box];

    // Merging paths into the key event
    EnterHouse [label="Homer and Matson enter the house", shape=ellipse];

    // The surreal experience inside
    Collapse [label="Earthquake causes the house to 'unfold' into 4D", shape=diamond];
    Lost [label="They find themselves trapped in a looping, non-Euclidean space", shape=diamond];

    // Strange interior exploration
    GravityShift [label="Gravity shifts unpredictably", shape=parallelogram];
    Recursion [label="Rooms repeat in paradoxical ways", shape=parallelogram];
    WindowView [label="They see landscapes from impossible locations", shape=parallelogram];

    // The struggle to escape
    ExitSearch [label="Desperate search for an exit", shape=ellipse];

    // The climax and resolution
    FinalJump [label="They attempt to exit through a door, re-emerging outside", shape=diamond];
    HouseGone [label="The house disappears completely", shape=box];

    // Conclusion
    End [label="Teal realizes the house collapsed into another dimension", shape=ellipse];

    // Connecting edges
    Start -> {{Design Build}};
    Design -> EnterHouse;
    Build -> EnterHouse;
    EnterHouse -> Collapse;
    Collapse -> {{Lost WindowView}};
    Lost -> {{GravityShift Recursion ExitSearch}};
    GravityShift -> ExitSearch;
    Recursion -> ExitSearch;
    WindowView -> ExitSearch;
    ExitSearch -> FinalJump;
    FinalJump -> HouseGone;
    HouseGone -> End;
}}
```

## The narrative:
```md
{}
```
'''

UPDATE_PROMPT = r'''# Narrative Scene Graph Update
Given the following existing narrative graph in DOT format:
```dot
{previous_graph}
```
And given the additional narrative text:
```md
{new_narrative}
```
Update the graph by incorporating the new narrative content, while preserving all existing nodes, labels, and quotes exactly as they appear. The updated graph must remain a directed acyclic graph starting with a single root node and ending with a final end node. If nodes repeat in the narrative, merge them.
DON'T modify the existing labels or quotes—only add new nodes or edges for the additional narrative.
Return only the updated graph in DOT format.
'''

# Process command-line arguments.
try:
    fpath = sys.argv[1]
    modelId = sys.argv[2]
except IndexError:
    sys.exit(USAGE_STR)

file = Path(fpath)
if not file.exists():
    sys.exit(f"input file {fpath} doesn't exist")

fname = fpath[fpath.rfind('/')+1:]
fextension = fname[fname.rfind('.')+1:]
if fextension not in FORMATS:
    sys.exit("unavailable file format; choose from " + str(FORMATS))

if modelId not in MODEL_IDS:
    sys.exit("unavailable model; choose from https://openrouter.ai/models")
model = next(filter(lambda model: model['id'] == modelId, MODELS), '')

# Verify API token limits.
res = requests.get(
    url="https://openrouter.ai/api/v1/auth/key",
    headers={"Authorization": "Bearer " + API_TOKEN},
    timeout=10,
)
res.raise_for_status()
print(f"OpenRouter tokens: {res.json()['data']['limit_remaining']}")

# Create output directory and determine output file index.
Path("out").mkdir(exist_ok=True)
outFiles = set(filter(lambda name: name.startswith(fname), os.listdir("out")))
numberedOutFiles = filter(lambda name: not name.endswith('.md'), outFiles)
lastOutFile = next(iter(sorted(numberedOutFiles, reverse=True)), None)
lastOutIdx = lastOutFile and lastOutFile[len(fname)+1:len(fname)+4] or -1
saveOutIdx = f'{int(lastOutIdx)+1:03d}'

# Retrieve or generate rendered text.
mdFile = next(filter(lambda name: name.endswith('.md'), outFiles), None)
if mdFile:
    rendered_text = (Path("out") / mdFile).read_text()
else:
    # Delay imports until necessary.
    tstart = time.time()
    from marker.config.parser import ConfigParser
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.renderers.markdown import MarkdownOutput
    print(f"took: {round(time.time() - tstart, 2)}s (imports)")

    MARKER_CONFIG = {"output_format": "md"}
    MARKER_CONFIG_PARSER = ConfigParser(MARKER_CONFIG)
    FORMAT_CONVERTERS = {'pdf': PdfConverter}
    assert tuple(FORMAT_CONVERTERS.keys()) == FORMATS

    tstart = time.time()
    converter = FORMAT_CONVERTERS[fextension](
        config=MARKER_CONFIG_PARSER.generate_config_dict(),
        artifact_dict=create_model_dict(),
    )
    rendered: MarkdownOutput = converter(fpath)
    rendered_text = rendered.markdown
    print(f"took: {round(time.time() - tstart, 2)}s (parsing)")
    Path(f"out/{fname}.{saveOutIdx}.md").write_text(rendered_text)

# =============================================================================
# BATCH PROCESSING: Split the rendered text into manageable chunks.
# =============================================================================
CHUNK_SIZE = 2000  # Adjust as needed based on token limits.

def split_into_chunks(text, chunk_size):
    """Splits text into chunks, attempting to break at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for p in paragraphs:
        if current_chunk and len(current_chunk) + len(p) + 2 > chunk_size:
            chunks.append(current_chunk)
            current_chunk = p
        else:
            current_chunk = p if not current_chunk else current_chunk + "\n\n" + p
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

chunks = split_into_chunks(rendered_text, CHUNK_SIZE)
print(f"Text split into {len(chunks)} chunk(s).")

# =============================================================================
# Incremental processing of each text chunk.
# =============================================================================
graph = None
for i, chunk in enumerate(chunks):
    if i == 0:
        prompt_text = INITIAL_PROMPT.format(chunk)
    else:
        prompt_text = UPDATE_PROMPT.format(previous_graph=graph, new_narrative=chunk)

    tstart = time.time()
    res = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + API_TOKEN},
        data=json.dumps({
            "model": model['id'],
            "messages": [{"role": "user", "content": prompt_text}],
        }),
        timeout=30,
    )
    print(f"took: {round(time.time() - tstart, 2)}s (generation for batch {i+1})")
    res.raise_for_status()
    res_body = res.json()
    if not res.ok:
        error_message = res_body.get('error', {}).get('message', 'Unknown error')
        sys.exit(f'OpenRouter: {error_message} ({res.status_code})')

    llm_out: str = res_body['choices'][0]['message']['content']
    dotStart = llm_out.find("```dot")
    dotEnd = llm_out.rfind("```")
    if dotStart == -1 or dotEnd == -1 or dotEnd <= dotStart:
        sys.exit("No DOT code block found in LLM response")
    # Update the cumulative graph with the latest output.
    graph = llm_out[dotStart + len("```dot"):dotEnd].strip()
    print(f"Batch {i+1} processed. Graph length: {len(graph)} characters.")

# =============================================================================
# Output: Save the final DOT graph and render it to PNG.
# =============================================================================
graphFpath = f"out/{fname}.{saveOutIdx}.dot"
Path(graphFpath).write_text(graph)
print(f"Final DOT graph written to {graphFpath}")

png = subprocess.run(["dot", "-Tpng", graphFpath], capture_output=True, check=False)
if png.returncode != 0:
    sys.exit(png.stderr)
Path(f"out/{fname}.{saveOutIdx}.png").write_bytes(png.stdout)
print(f"PNG graph rendered successfully to out/{fname}.{saveOutIdx}.png")

### Overview

# 1. **Initial Setup:**  
#    - The script verifies the API token, file format, and model.  
#    - It then either retrieves pre-rendered text or converts the input PDF to markdown.

# 2. **Batch Processing:**  
#    - The rendered text is split into chunks (by paragraphs) to avoid exceeding token limits.
#    - The first chunk is processed with `INITIAL_PROMPT`.
#    - Subsequent chunks are processed using `UPDATE_PROMPT`, merging new narrative content into the previously generated DOT graph.

# 3. **Output Generation:**  
#    - The final graph is saved to a DOT file.
#    - The Graphviz `dot` command is used to render the DOT file to a PNG image.

# You can adjust parameters like `CHUNK_SIZE` or modify the prompts to suit your needs. This revised version should handle longer PDFs more gracefully by processing them incrementally.
