#! /usr/bin/env python
import sys
import os
from pathlib import Path
import json
import time
import requests


if __name__ != "__main__":
    raise Exception("program is not a module; execute it directly")


try:
    API_TOKEN = os.environ.get("API_TOKEN") or Path('.API_TOKEN').read_text()
except FileNotFoundError as e:
    raise FileNotFoundError("provide the OpenRouter token through:\n- an environment variable `API_TOKEN`\n- a file `.API_TOKEN` containing it") from e
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
OUT_DIR = Path("out")
FORMATS = ('pdf',) # TODO: moar
MODELS = json.loads(Path('.models.json').read_text())['data']
MODEL_IDS = (model['id'] for model in MODELS)
PROMPT_STR =\
'''# Parse a body of text into nodes 
## Process
The document, in Markdown format, is used to create a directed acyclic graph, without reference to any outside material. The graph must be in raw text following the DOT graph description language.
### Nodes
The nodes must encapsulate chunks of text with a semantic coherence as best as they can. The node content is DIRECTLY FROM THE DOCUMENT and NOT CREATED or EXTRACTED FROM ELSEWHERE 
Examples:
- For non-fiction writing, split it into topic summaries or introductions, concepts, examples, etc.
- For fiction writing, split it into scenes, descriptions, notes, etc.
- For an exercise book, split it into questions and answers.
### Edges (Connections)
The nodes may be connected to one parent, or to no parent, making it a "root node". A node with no other node connecting to it makes it a "leaf node" The graph may have multiple roots, in the case that a node has no reasonable connection to a parent node.
Examples:
- for non-fiction writing, each node may connect to nodes progression from fundamental and narrow ideas, to advanced and/or broad ideas.

ALL the sections, sub-sections, etc. following the sub-section "The text:" are part of the document to be converted.
DON'T describe the document or the workings of acyclic directed graphs. Output in the DOT graph description language format.

## The text:

{}
'''
try:
    fpath = sys.argv[1]
    # TODO: bash completion or choose from index, will be easier with a TUI
    modelId = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e
fname = fpath[fpath.rfind('/')+1:]
fextension = fname[fname.rfind('.')+1:]
if fextension not in FORMATS:
    raise ValueError("unavailable file format; choose from " + str(FORMATS))
if modelId not in MODEL_IDS:
    raise ValueError("unavailable model; choose from https://openrouter.ai/models")
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
outsForFname = filter(lambda name: name.startswith(fpath), os.listdir("out"))
lastOutFname = next(iter(sorted(outsForFname, reverse=True)))
lastOutIdx = 

saveIdx = f'{int(lastIdx)+1:03d}'

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
Path(f"out/{fname}.{saveIdx}.parse").write_text(rendered_text)


tstart = time.time()
res = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": "Bearer "+API_TOKEN,
    },
    data=json.dumps({
        "model": model['id'],
        # "prompt": PROMPT.format(rendered_text),
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
        raise requests.exceptions.HTTPError(f'OpenRouter: {res_body['error']['message']} ({res.status_code})')
    res.raise_for_status()

graph = res_body['choices'][0]['message']['content']
Path(f"out/{fname}.{saveIdx}.graph").write_text(graph)