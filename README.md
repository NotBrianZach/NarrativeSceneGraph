# NarrativeSceneGraph
## Setup
`$ make` should set everything up for you. These are the things it does. The last step is manual:
1. Create virtual environment and install dependencies from `requirements.txt`
2. Save OpenRouter API token (options are an `.API_TOKEN` file or `API_TOKEN` environment variable)
3. Cache available models into `.models.json` 
4. (MANUALLY) Install [graphviz](https://www.graphviz.org/) (example: Arch: `pacman -S graphviz`)

## Usage
`$ ./main.py <file> <model>`
- `<file>`: input file
- `<model>`: model ID. Must be a valid ID in `.models.json` (run `$ make .models.json` to generate it). A more human-friendly way to find them is in https://openrouter.ai/models

Final output will be `out/<file>.<iteration>.dot`. (example: [out/CrookedHouse.pdf.007.png](out/CrookedHouse.pdf.007.png))

## Roadmap
- [ ] use llm to cut story up into pieces, scenes
    - it's possible that llms are not necessary for this (but could be useful / are an option), if we use algorithms that are already used for chunking in RAG (https://stackoverflow.blog/2024/12/27/breaking-up-is-hard-to-do-chunking-in-rag-applications/)
    - use sumy to summarize (for the part that goes into the LLM)?
    - ask it to explain why two particular nodes were connected?
- [ ] just start with the first scene in the narrative as the first node, create graph
- [ ] at each step of graph construction use the graph + scenes you have to figure out where the next scene belongs in the graph

## Parametrize
- model
- body compression (i.e. chunking)

### Prompt
- type of output node (scene, logical connection/sequence), depends on context of document, for the future though

## 2 think about
- final file format (twine)
- intermediate storage in sqlite db for easier/faster processing?

## Useful (references, read later)
- https://openrouter.ai/docs/api-reference/overview

## Copyright notice
TODO: clarify that we don't own "And He Built A Crooked House" by Robert A. Heinlein, or any of the input PDFs