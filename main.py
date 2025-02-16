#! /usr/bin/env python
if __name__ != "__main__":
    raise Exception("program is not a module; execute it directly")


import json.tool
import sys
import os
from pathlib import Path
import json
import requests

try:
    API_TOKEN =  os.environ.get(".API_TOKEN", Path('.API_TOKEN').read_text())
except FileNotFoundError as e:
    raise FileNotFoundError("provide the OpenRouter token through:\n- an environment variable `.API_TOKEN`\n- a file `.API_TOKEN` containing it") from e
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
OUT_DIR = Path("out")
FORMATS = ('pdf',) # TODO: moar
MODELS = Path('.models')

try:
    fname: str = sys.argv[1]
    # TODO: bash completion or choose from index, will be easier with a TUI
    model: str = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e
fextension = fname[fname.rfind('.')+1:]
if fextension not in FORMATS:
    raise ValueError("unavailable file format; choose from " + str(FORMATS))
if model not in MODELS:
    raise ValueError("unavailable model; choose from " + str(MODELS))

# pylint: disable=wrong-import-position
import time
# these imports take long so I placed them after initial checks
# even if it disrespects pylint C0413
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
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": "Bearer"+API_TOKEN,
  },
  data=json.dumps({
    "model": model,
    "messages": [text]
  }),
  timeout=30,
).json()

if not res.ok:
    # https://openrouter.ai/docs/api-reference/errors
    print(res.error.message, file=sys.stderr)
    res.raise_for_status()
