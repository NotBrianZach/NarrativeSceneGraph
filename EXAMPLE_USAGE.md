# PDF2Twine Usage Examples

This document demonstrates how to use the PDF2Twine tool to convert PDF documents into interactive Twine stories.

## Prerequisites

1. Ensure you have the project set up with dependencies installed
2. For LLM features, you'll need an OpenRouter API token:
   - Set environment variable: `export API_TOKEN=your_token_here`
   - Or create a file: `.API_TOKEN` containing your token

## Basic Usage

### Simple PDF to Twee Conversion
```bash
python -m pdf2twine.cli input.pdf output.twee
```

This will:
- Extract text from the PDF
- Segment it into scenes using heuristic rules
- Create a basic narrative graph
- Export to Twee format

### With LLM Enhancement
```bash
python -m pdf2twine.cli input.pdf output.twee --llm
```

This uses LLM for more intelligent scene segmentation.

## Advanced Features

### Generate Interactive Quizzes
```bash
python -m pdf2twine.cli story.pdf interactive_story.twee --with-quiz
```

This adds quiz questions after each scene to test comprehension.

### Multiple Output Formats
```bash
python -m pdf2twine.cli story.pdf story.twee \
  --dot-output story.dot \
  --html-output story.html
```

Generates:
- `story.twee` - Twee format for Twine
- `story.dot` - Graphviz DOT file for visualization
- `story.html` - Standalone HTML story

### Flow-Based Layout
```bash
python -m pdf2twine.cli story.pdf story.twee --layout flow
```

Arranges scenes in a top-to-bottom narrative flow instead of random positioning.

### Custom Configuration
```bash
python -m pdf2twine.cli story.pdf story.twee \
  --title "My Interactive Adventure" \
  --max-scenes 50 \
  --model "openai/gpt-4" \
  --canvas-width 6000 \
  --canvas-height 4000 \
  --with-quiz \
  --layout flow \
  --verbose
```

## Planning and Debugging

### Dry Run
```bash
python -m pdf2twine.cli story.pdf output.twee --dry-run
```

Shows what the tool would do without actually processing the file.

### Verbose Output
```bash
python -m pdf2twine.cli story.pdf output.twee --verbose
```

Provides detailed logging of each processing step.

## Example Workflow

1. **Plan your conversion:**
   ```bash
   python -m pdf2twine.cli mobydick.pdf mobydick_story.twee --dry-run --with-quiz
   ```

2. **Run the conversion:**
   ```bash
   python -m pdf2twine.cli mobydick.pdf mobydick_story.twee \
     --with-quiz \
     --layout flow \
     --title "Moby Dick Interactive" \
     --dot-output mobydick.dot
   ```

3. **Open in Twine:**
   - Import the `.twee` file into Twine 2
   - Or compile with tweego: `tweego mobydick_story.twee -o mobydick_story.html`

## Output Structure

### Twee File Format
The generated `.twee` file contains:
- Story metadata (title, creator, etc.)
- Scene passages with original text
- Navigation links between scenes
- Quiz passages (if `--with-quiz` used)
- Position coordinates for Twine editor

### Example Twee Output
```twee
:: Story [Twine2]

{
  "name": "My Story",
  "startnode": "scene_1",
  "creator": "pdf2twine",
  "creator-version": "1.0.0"
}

:: Opening_Scene <100,200>

Call me Ishmael. Some years ago—never mind how long precisely—having little or no money in my purse...

---

[[Continue|The_Voyage]]

:: The_Voyage <300,400>

The ship was ready to sail...

---

[[Take Quiz|Opening_Scene_quiz]]
[[Continue to Next Chapter|Next_Scene]]
```

## Tips and Best Practices

1. **Start with dry run** to understand what will be generated
2. **Use flow layout** for better narrative organization
3. **Add quizzes** for educational content
4. **Set appropriate max-scenes** based on document length
5. **Use verbose mode** when debugging issues
6. **Test with small documents** first

## Troubleshooting

### Common Issues

1. **No API token error:**
   - Set `API_TOKEN` environment variable
   - Or create `.API_TOKEN` file

2. **Too many scenes:**
   - Use `--max-scenes` to limit output
   - Consider using heuristic segmentation instead of LLM

3. **Poor scene segmentation:**
   - Try `--llm` flag for better segmentation
   - Adjust document formatting before conversion

4. **Memory issues with large PDFs:**
   - Process in smaller chunks
   - Use heuristic segmentation to reduce LLM calls

### Getting Help

```bash
python -m pdf2twine.cli --help
```

Shows all available options and their descriptions. 