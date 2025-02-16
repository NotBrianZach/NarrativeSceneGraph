# NarrativeSceneGraph
## Roadmap
- [ ] use llm to cut story up into pieces, scenes
    - it's possible that llms are not necessary for this (but could be useful / are an option), if we use algorithms that are already used for chunking in RAG (https://stackoverflow.blog/2024/12/27/breaking-up-is-hard-to-do-chunking-in-rag-applications/)
- [ ] just start with the first scene in the narrative as the first node, create graph
- [ ] at each step of graph construction use the graph + scenes you have to figure out where the next scene belongs in the graph

## Parametrize
- model
- body compression (i.e. chunking)

### Prompt
- type of output node  (scene, logical connection/sequence), depends on context of document, for the future though

## 2 think about
- final file format (twine)
- intermediate storage in sqlite db for easier/faster processing?

## Useful (references, read later)
- https://openrouter.ai/docs/api-reference/overview
