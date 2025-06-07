#!/usr/bin/env python3
"""Demo of DOT graph generation from PDF content."""

from pdf2twine.graph.serialize import to_dot

# Create a small example graph
graph = {
    'nodes': [
        {'id': 'scene_1', 'label': 'Call me Ishmael'},
        {'id': 'scene_2', 'label': 'The artist desires to paint'},
        {'id': 'scene_3', 'label': 'Going to sea when hazy'},
        {'id': 'scene_4', 'label': 'The spout of the whale'}
    ],
    'edges': [
        {'source': 'scene_1', 'target': 'scene_2', 'label': 'leads_to'},
        {'source': 'scene_2', 'target': 'scene_3', 'label': 'continues'},
        {'source': 'scene_3', 'target': 'scene_4', 'label': 'flows_to'}
    ]
}

print("📊 DIRECTED GRAPH DEMO")
print("=" * 40)
dot_content = to_dot(graph, 'MobyDickDemo')
print("Generated DOT graph:")
print(dot_content)

# Save to file
with open('demo_graph.dot', 'w') as f:
    f.write(dot_content)

print(f"\n✅ Saved to demo_graph.dot")
print("🔍 You can visualize this with Graphviz:")
print("   dot -Tpng demo_graph.dot -o demo_graph.png") 