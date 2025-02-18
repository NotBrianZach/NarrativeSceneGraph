#! /usr/bin/env python
import sys
import os
from pathlib import Path
import json
import time
import subprocess
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
DON'T describe the document or the workings of acyclic directed graphs. 
Output in the DOT graph description language format.
DON'T fill in the nodes with anything outside of the document. Don't refer to general knowledge, historical events, or facts, if they're not in the text. Use EXCLUSIVELY the text contained in the document.

### Example graph
```dot
digraph ComputerScienceMindMap {{
    node [shape=ellipse, style=filled, fillcolor=lightblue];
    
    "Computer Science" [label="Computer Science\nThe study of computation and information"];
    "Programming" [label="Programming\nWriting and maintaining code"];
    "Algorithms & Data Structures" [label="Algorithms & Data Structures\nTechniques for solving problems efficiently"];
    "Databases" [label="Databases\nStorage and retrieval of structured data"];
    "Networking" [label="Networking\nCommunication between computers"];
    "Operating Systems" [label="Operating Systems\nSoftware that manages hardware and applications"];
    "Artificial Intelligence" [label="Artificial Intelligence\nCreating systems that simulate human intelligence"];
    "Cybersecurity" [label="Cybersecurity\nProtecting systems and data from threats"];
    "Software Engineering" [label="Software Engineering\nDesigning, developing, and maintaining software"];
    "Theory of Computation" [label="Theory of Computation\nMathematical study of computation"];
    "Computer Graphics" [label="Computer Graphics\nCreating visual content using computers"];
    
    "Programming" -> "Python" [label="A high-level programming language"];
    "Programming" -> "C++" [label="A powerful systems programming language"];
    "Programming" -> "Java" [label="A versatile object-oriented language"];
    "Programming" -> "JavaScript" [label="A language for web development"];
    "Programming" -> "Functional Programming" [label="A paradigm focusing on immutability and functions"];
    "Programming" -> "Object-Oriented Programming" [label="A paradigm based on objects and classes"];
    
    "Algorithms & Data Structures" -> "Sorting" [label="Techniques for arranging data"];
    "Algorithms & Data Structures" -> "Graphs" [label="Data structures for networked relationships"];
    "Algorithms & Data Structures" -> "Trees" [label="Hierarchical data structures"];
    "Algorithms & Data Structures" -> "Dynamic Programming" [label="Optimization technique for recursive problems"];
    
    "Databases" -> "SQL" [label="Structured Query Language for databases"];
    "Databases" -> "NoSQL" [label="Non-relational database solutions"];
    "Databases" -> "Normalization" [label="Organizing data to reduce redundancy"];
    "Databases" -> "Indexing" [label="Optimizing database queries"];
    
    "Networking" -> "TCP/IP" [label="Protocols for internet communication"];
    "Networking" -> "HTTP" [label="Protocol for web communication"];
    "Networking" -> "DNS" [label="System that translates domain names to IP addresses"];
    "Networking" -> "Routing" [label="Directing data between networks"];
    
    "Operating Systems" -> "Memory Management" [label="Handling system memory allocation"];
    "Operating Systems" -> "Process Scheduling" [label="Managing CPU time for tasks"];
    "Operating Systems" -> "File Systems" [label="Organizing and storing files"];
    "Operating Systems" -> "Concurrency" [label="Managing multiple executing tasks"];
    
    "Artificial Intelligence" -> "Machine Learning" [label="Training algorithms to learn from data"];
    "Artificial Intelligence" -> "Deep Learning" [label="Neural networks for complex tasks"];
    "Artificial Intelligence" -> "Neural Networks" [label="Models inspired by the human brain"];
    "Artificial Intelligence" -> "Natural Language Processing" [label="Computational understanding of human language"];
    
    "Cybersecurity" -> "Cryptography" [label="Securing data through encryption"];
    "Cybersecurity" -> "Ethical Hacking" [label="Testing security through controlled attacks"];
    "Cybersecurity" -> "Firewalls" [label="Protecting networks from unauthorized access"];
    "Cybersecurity" -> "Secure Coding" [label="Writing software with security in mind"];
    
    "Software Engineering" -> "Agile Development" [label="Iterative software development approach"];
    "Software Engineering" -> "Version Control" [label="Tracking changes in source code"];
    "Software Engineering" -> "Design Patterns" [label="Reusable solutions to common design problems"];
    
    "Theory of Computation" -> "Automata Theory" [label="Study of abstract machines"];
    "Theory of Computation" -> "Turing Machines" [label="Theoretical model of computation"];
    "Theory of Computation" -> "Computational Complexity" [label="Classifying problems based on difficulty"];
    
    "Computer Graphics" -> "Rendering" [label="Generating images from models"];
    "Computer Graphics" -> "Ray Tracing" [label="Simulating light for realistic graphics"];
    "Computer Graphics" -> "3D Modeling" [label="Creating three-dimensional representations"];
}}
```

## The text:

{}
'''

try:
    fpath = sys.argv[1]
    # TODO: bash completion or choose from index, will be easier with a TUI
    modelId = sys.argv[2]
except IndexError as e:
    raise IndexError(USAGE_STR) from e
file = Path(fpath)
if not file.exists():
    raise FileNotFoundError(f"input file {fpath} doesn't exist")
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
outsForFname = filter(lambda name: name.startswith(fname), os.listdir("out"))
lastOutFile = next(iter(sorted(outsForFname, reverse=True)), None)
if lastOutFile:
    lastOutIdx = lastOutFile[len(fname)+1:len(fname)+4]
else:
    lastOutIdx = -1
saveOutIdx = f'{int(lastOutIdx)+1:03d}'


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

llm_out: str = res_body['choices'][0]['message']['content']
Path(f"out/{fname}.{saveOutIdx}.txt").write_text(llm_out)

# until we can get it to output raw .dot
dotStart = llm_out.find("```dot")
dotEnd = llm_out.rfind("```")

graph = llm_out[dotStart+6:dotEnd]
graphFpath = f"out/{fname}.{saveOutIdx}.dot"
Path(graphFpath).write_text(graph)

try:
    png = subprocess.run(["dot", "-Tpng", graphFpath], capture_output=True, check=True)
except subprocess.CalledProcessError as e:
    raise e(png.stderr)

Path(f"out/{fname}.{saveOutIdx}.png").write_bytes(png.stdout)
