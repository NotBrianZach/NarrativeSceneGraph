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


try:
    API_TOKEN = os.environ.get("API_TOKEN") or Path('.API_TOKEN').read_text()
except FileNotFoundError as e:
    sys.exit("provide the OpenRouter token through:\n- an environment variable `API_TOKEN`\n- a file `.API_TOKEN` containing it")
OUT_DIR = Path("out")
FORMATS = ('pdf',) # TODO: moar
MODELS = json.loads(Path('.models.json').read_text())['data']
MODEL_IDS = (model['id'] for model in MODELS)
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
PROMPT_STR =\
'''# Narrative Scene Graph
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

try:
    fpath = sys.argv[1]
    # TODO: bash completion or choose from index, will be easier with a TUI
    modelId = sys.argv[2]
except IndexError as e:
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

# get info about limits: https://openrouter.ai/docs/api-reference/limits#rate-limits-and-credits-remaining
res = requests.get(
    url="https://openrouter.ai/api/v1/auth/key",
    headers={
        "Authorization": "Bearer "+API_TOKEN,
    },
    timeout=10,
)
res.raise_for_status()
print(f"OpenRouter tokens: {res.json()['data']['limit_remaining']}")

Path("out").mkdir(exist_ok=True)
# must wrap it in `set` because `filter` is a generator and reading its items consumes them
outFiles = set(filter(lambda name: name.startswith(fname), os.listdir("out")))

numberedOutFiles = filter(lambda name: not name.endswith('.md'), outFiles)
lastOutFile = next(iter(sorted(numberedOutFiles, reverse=True)), None)
lastOutIdx = lastOutFile and lastOutFile[len(fname)+1:len(fname)+4] or -1
saveOutIdx = f'{int(lastOutIdx)+1:03d}'

mdFile = next(filter(lambda name: name.endswith('.md'), outFiles), None)
if mdFile:
    rendered_text = (Path("out")/mdFile).read_text()
else:
    # these imports take crazy long so I placed them after initial checks
    # even if it disrespects pylint C0413
    # pylint: disable=wrong-import-position
    tstart = time.time()
    from marker.config.parser import ConfigParser
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.renderers.markdown import MarkdownOutput
    # some example usage in marker/scripts/convert_single.py
    # pylint: enable=wrong-import-position
    print(f"took: {round(time.time() - tstart, 2)}s (imports)")

    MARKER_CONFIG = {
        "output_format": "md"
    }
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


tstart = time.time()
res = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": "Bearer "+API_TOKEN,
    },
    data=json.dumps({
        "model": model['id'],
        # "prompt": PROMPT_STR.format(rendered_text),
        "messages": [{
            "role": "user",
            "content": PROMPT_STR.format(rendered_text),
        }],
    }),
    # NOTE: too little?
    timeout=30,
)
print(f"took: {round(time.time() - tstart, 2)}s (generation)")
res_body = res.json()

if not res.ok:
    if res_body:
    # https://openrouter.ai/docs/api-reference/errors
        sys.exit(f'OpenRouter: {res_body['error']['message']} ({res.status_code})')
    res.raise_for_status()

llm_out: str = res_body['choices'][0]['message']['content']
Path(f"out/{fname}.{saveOutIdx}.txt").write_text(llm_out)

# until we can get it to output raw .dot
dotStart = llm_out.find("```dot")
dotEnd = llm_out.rfind("```")

graph = llm_out[dotStart+len('```dot'):dotEnd]
graphFpath = f"out/{fname}.{saveOutIdx}.dot"
Path(graphFpath).write_text(graph)

png = subprocess.run(["dot", "-Tpng", graphFpath], capture_output=True, check=False)
if png.returncode != 0:
    sys.exit(png.stderr)

Path(f"out/{fname}.{saveOutIdx}.png").write_bytes(png.stdout)
