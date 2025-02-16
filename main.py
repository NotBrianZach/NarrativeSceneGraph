#! /usr/bin/env python
if __name__ != "__main__":
    raise Exception("program is not a module; execute it directly")


import sys
import os
from pathlib import Path

try:
    API_TOKEN = Path('.API_TOKEN').read_text()
except FileNotFoundError as e:
    raise FileNotFoundError("paste your OpenRouter token into `.API_TOKEN`") from e
USAGE_STR = f"usage: {sys.argv[0]} <filename> <model>"
FORMATS = ('pdf',) # TODO: moar
MODELS = ('openai/gpt-4o',) # TODO: moar; these will be the model strings
OUT_FOLDER = Path("out")

try:
    fname: str = sys.argv[1]
    model: str = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e
fextension = fname[fname.rfind('.')+1:]
if fextension not in FORMATS:
    raise ValueError("unavailable file format; choose from " + str(FORMATS))

# pylint: disable=wrong-import-position
import time
import logging
# these imports take so long so I placed them after initial checks
# even if it disrespects pylint C0413
from marker.converters.pdf import PdfConverter
from marker.modelws import create_model_dict
from marker.output import text_from_rendered
# pylint: enableq=wrong-import-position
logging.getLogger().setLevel(level=3)

FORMAT_CONVERTERS = {'pdf': PdfConverter}
assert tuple(FORMAT_CONVERTERS.keys()) == FORMATS

tstart = time.time()
converter = FORMAT_CONVERTERS[fextension](
    artifact_dict=create_model_dict(),
)
rendered = converter(fname)
text, _, images = text_from_rendered(rendered)
print(f"took:\t{round(time.time() - tstart, 2)}s (imports + parsing)")

# TODO: split into nodes