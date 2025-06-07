#!/usr/bin/env python3
"""
Simple demo of PDF2Twine functionality without LLM features.
This shows the core pipeline: PDF → scenes → basic graph → Twine export
"""

from pdf2twine.loader import extract
from pdf2twine.segmenter import split_heuristic
from pdf2twine.exporter.twine import write_twee
from pdf2twine.exporter.coordinates import assign_random_coordinates

def simple_demo():
    print("🎯 PDF2TWINE SIMPLE DEMO")
    print("=" * 50)
    
    # Step 1: Extract text from PDF
    print("\n📄 Step 1: Extracting text from PDF...")
    try:
        text = extract('mobydick.pdf')
        print(f"✅ Extracted {len(text):,} characters")
        print(f"📖 First line: {text.split('CONTENTS')[0].strip()}")
    except Exception as e:
        print(f"❌ Error extracting PDF: {e}")
        return
    
    # Step 2: Split into scenes (limit to manageable number)
    print("\n🔤 Step 2: Splitting into scenes...")
    try:
        # Use larger min_length to get fewer, more substantial scenes
        scenes = split_heuristic(text, min_length=800)
        print(f"✅ Created {len(scenes)} scenes")
        
        # Show first few scenes
        for i, scene in enumerate(scenes[:3]):
            print(f"Scene {i+1}: {scene[:100]}...")
            
    except Exception as e:
        print(f"❌ Error splitting scenes: {e}")
        return
    
    # Step 3: Create basic graph structure (without LLM)
    print("\n🕸️  Step 3: Creating basic narrative graph...")
    try:
        # Create a simple sequential graph
        nodes = []
        edges = []
        
        for i, scene in enumerate(scenes):
            node_id = f"scene_{i+1}"
            # Create a simple summary from first sentence
            first_sentence = scene.split('.')[0][:50]
            summary = first_sentence + "..." if len(first_sentence) == 50 else first_sentence
            
            nodes.append({
                'id': node_id,
                'label': summary,
                'text': scene
            })
            
            # Create sequential edges
            if i < len(scenes) - 1:
                edges.append({
                    'source': node_id,
                    'target': f"scene_{i+2}",
                    'label': 'Continue'
                })
        
        graph = {
            'nodes': nodes,
            'edges': edges,
            'metadata': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'demo_mode': True
            }
        }
        
        print(f"✅ Created graph with {len(nodes)} nodes and {len(edges)} edges")
        
    except Exception as e:
        print(f"❌ Error creating graph: {e}")
        return
    
    # Step 4: Add coordinates
    print("\n📍 Step 4: Adding coordinates...")
    try:
        graph = assign_random_coordinates(graph, seed=42)  # Reproducible
        print("✅ Added random coordinates to all nodes")
    except Exception as e:
        print(f"❌ Error adding coordinates: {e}")
        return
    
    # Step 5: Export to Twee
    print("\n📝 Step 5: Exporting to Twine format...")
    try:
        output_file = "demo_output.twee"
        write_twee(graph, output_file, "Moby Dick Demo")
        print(f"✅ Exported to {output_file}")
        
        # Show file size and first few lines
        with open(output_file, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            print(f"📊 Generated {len(content):,} characters, {len(lines)} lines")
            print(f"🔍 First few lines:")
            for line in lines[:10]:
                if line.strip():
                    print(f"   {line}")
                    
    except Exception as e:
        print(f"❌ Error exporting: {e}")
        return
    
    print("\n🎉 DEMO COMPLETE!")
    print(f"📁 Check out '{output_file}' - you can import this into Twine 2!")
    print("🎮 This creates a 'choose your own adventure' style story")
    print("🔗 Each scene connects to the next with clickable links")

if __name__ == "__main__":
    simple_demo() 