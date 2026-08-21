#!/usr/bin/env python3
"""Print word indices around key transcript moments to verify scene boundaries."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

DEMO_PID = "cd7824dc202a"
words = json.load(open(os.path.join(ps.project_dir(DEMO_PID), "words.json"), encoding="utf-8"))
words = [w for w in words if w.get("text","").strip()]

# Print key moments
key_phrases = ["walked", "How to plan", "That codebase", "Humans", "Every file", "I know agent",
               "AI", "plan", "So here", "By the end", "We're covering", "Let's build"]

for phrase in key_phrases:
    for i, w in enumerate(words):
        if w["text"].lower().startswith(phrase.lower().split()[0]):
            # Check if full phrase matches
            match = True
            for j, pword in enumerate(phrase.split()):
                if i+j < len(words) and words[i+j]["text"].lower().startswith(pword.lower()):
                    continue
                match = False
                break
            if match:
                print(f"  Word {i:3d}: '{w['text']}' at {w['start']:.2f}s — phrase '{phrase}'")
                break

print(f"\nTotal words: {len(words)}")
print(f"\nFirst 5 words: {[(i, w['text']) for i, w in enumerate(words[:5])]}")
print(f"Words 20-25: {[(i, w['text']) for i, w in enumerate(words[20:25], 20)]}")
print(f"Words 48-55: {[(i, w['text']) for i, w in enumerate(words[48:55], 48)]}")
print(f"Words 68-75: {[(i, w['text']) for i, w in enumerate(words[68:75], 68)]}")
print(f"Words 96-105: {[(i, w['text']) for i, w in enumerate(words[96:105], 96)]}")
print(f"Words 128-135: {[(i, w['text']) for i, w in enumerate(words[128:135], 128)]}")
print(f"Words 165-180: {[(i, w['text']) for i, w in enumerate(words[165:180], 165)]}")
print(f"Words 210-220: {[(i, w['text']) for i, w in enumerate(words[210:220], 210)]}")
print(f"Words 248-254: {[(i, w['text']) for i, w in enumerate(words[248:254], 248)]}")
