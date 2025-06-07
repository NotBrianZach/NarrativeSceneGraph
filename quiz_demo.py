#!/usr/bin/env python3
"""Demo of quiz generation functionality."""

from pdf2twine.quiz.generate import make_quiz_fallback, format_quiz_content

print("❓ QUIZ GENERATION DEMO")
print("=" * 40)

# Example scene from Moby Dick
scene_text = """Call me Ishmael. Some years ago—never mind how long precisely—having little
or no money in my purse, and nothing particular to interest me on shore, I thought
I would sail about a little and see the watery part of the world. It is a way I have
of driving off the spleen, and regulating the circulation."""

print("📖 Scene text:")
print(scene_text)

print("\n🧠 Generated quiz (fallback method):")
quiz_data = make_quiz_fallback(scene_text)
print(f"Question: {quiz_data['question']}")
for option in quiz_data['options']:
    print(f"  {option}")
print(f"Answer: {quiz_data['answer']}")
print(f"Explanation: {quiz_data['explanation']}")

print("\n📝 Formatted for Twine:")
quiz_content = format_quiz_content(quiz_data)
print(quiz_content)

print("\n✨ With LLM (requires API token), this would generate:")
print("   - Intelligent questions about plot, characters, themes")
print("   - Multiple plausible wrong answers")
print("   - Detailed explanations of correct answers")
print("   - Educational value for literature study!") 