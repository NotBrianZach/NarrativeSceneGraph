#! /usr/bin/env python
import time
import sys
import os
from pathlib import Path
import json
import requests

if __name__ != "__main__":
    raise Exception("program is not a module; execute it directly")


try:
    API_TOKEN =  os.environ.get(".API_TOKEN", Path('.API_TOKEN').read_text())
except FileNotFoundError as e:
    raise FileNotFoundError("provide the OpenRouter token through:\n- an environment variable `.API_TOKEN`\n- a file `.API_TOKEN` containing it") from e
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
OUT_DIR = Path("out")
FORMATS = ('pdf',) # TODO: moar
MODELS = json.loads(Path('.models.json').read_text())['data']
MODEL_IDS = (model['id'] for model in MODELS)
PROMPT = '''
# Parse a body of text into nodes 
## Process
The text, in Markdown format, must be split into nodes that encapsulate as best as it can.
Examples:
- For non-fiction writing, split it into topics, concepts,
- For fiction writing, 
- For an exercise book, split it into questions and answers.
The nodes must have a connection.
Examples:
- for non-fiction writing, each node may connect to nodes  progression from fundamental and narrow ideas, to advanced and/or broad ideas.
- For fiction writing, 
'''
try:
    fname: str = sys.argv[1]
    # TODO: bash completion or choose from index, will be easier with a TUI
    modelId: str = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e
fextension = fname[fname.rfind('.')+1:]
if fextension not in FORMATS:
    raise ValueError("unavailable file format; choose from " + str(FORMATS))
if modelId not in MODEL_IDS:
    raise ValueError("unavailable model; choose from https://openrouter.ai/models")
model = next(model for model in MODELS if model['id'] == modelId)


# these imports take long so I placed them after initial checks
# even if it disrespects pylint C0413
# pylint: disable=wrong-import-position
# some example usage in marker/scripts/convert_single.py
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
# pylint: enable=wrong-import-position

FORMAT_CONVERTERS = {'pdf': PdfConverter}
assert tuple(FORMAT_CONVERTERS.keys()) == FORMATS

tstart = time.time()
converter = FORMAT_CONVERTERS[fextension](
    artifact_dict=create_model_dict(),
)
rendered = converter(fname)
text, _, images = text_from_rendered(rendered)
print(f"took:\t{round(time.time() - tstart, 2)}s (imports + parsing)")

# get info about limits: https://openrouter.ai/docs/api-reference/limits#rate-limits-and-credits-remaining
res = requests.get(
    url="https://openrouter.ai/api/v1/auth/key",
    headers={
        "Authorization": "Bearer "+API_TOKEN,
    },
    timeout=10,
)
res.raise_for_status()
print(f"OpenRouter tokens remaining: {res.json()['data']['limit_remaining']}")

res = requests.post(
  url="https://openrouter.ai/api/v1/completions",
  headers={
    "Authorization": "Bearer "+API_TOKEN,
  },
  data=json.dumps({
    "model": model,
    "prompt": PROMPT+" "+text}),
  timeout=30,
).json()

if not res.ok:
    # https://openrouter.ai/docs/api-reference/errors
    print(res.error.message, file=sys.stderr)
    res.raise_for_status()
