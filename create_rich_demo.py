#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_rich_demo.py
====================
Create a cinematic demo project with visuals synced to exact word timestamps.
Every element appears and disappears at precise audio moments.
"""

import os, sys, json, time, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

# ── Config ──
DEMO_PID = "cd7824dc202a"  # reuse existing project with audio
WORDS_PATH = os.path.join(ps.project_dir(DEMO_PID), "words.json")
AUDIO_SRC = "C:/Users/AITREC/AppData/Local/VideoComposerWork/cd7824dc202a/source.mp3"

# ── Load words ──
words = json.load(open(WORDS_PATH, encoding="utf-8"))
# Filter valid words
words = [w for w in words if w.get("text", "").strip()]
total_duration = words[-1]["end"] if words else 60

print(f"Total words: {len(words)}, duration: {total_duration:.1f}s")

# ── Scene definitions ──
# Each scene: (name, start_word_idx, end_word_idx, theme)
# Themes: tech (dark+grid), minimal (light), bold (dark+dots), neon (dark+vibrant)
scene_defs = [
    # Title: (name, start_word_idx, end_word_idx, theme)
    # Narration: "In my last video I gave you a tour of the POSTemplate codebase...
    ("Hook — In My Last Video", 0, 28, "tech"),
    ("A Real Point-of-Sale System", 28, 60, "bold"),
    ("Database, Logic, Security", 60, 95, "tech"),
    ("At The End I Made A Request", 95, 130, "neon"),
    ("The Problem — It's Not Agent Ready", 130, 170, "bold"),
    ("Here's What We're Covering", 170, 210, "tech"),
    ("Let's Build The Blueprint", 210, 254, "neon"),
]

# ── Theme palettes ──
themes = {
    "tech": {
        "bg": "#0a0e14",
        "accent": "#4a9eff",
        "highlight": "#FFD700",
        "secondary": "#00ff88",
        "pattern": "bg-grid",
        "title_color": "#4a9eff",
    },
    "bold": {
        "bg": "#1a1a2e",
        "accent": "#e94560",
        "highlight": "#FFD700",
        "secondary": "#ff6b35",
        "pattern": "bg-dots",
        "title_color": "#e94560",
    },
    "minimal": {
        "bg": "#f5f5f5",
        "accent": "#333333",
        "highlight": "#e74c3c",
        "secondary": "#2ecc71",
        "pattern": None,
        "title_color": "#333333",
    },
    "neon": {
        "bg": "#0d0221",
        "accent": "#00ffff",
        "highlight": "#ff00ff",
        "secondary": "#ffff00",
        "pattern": "bg-vignette",
        "title_color": "#00ffff",
    },
}

# ── Helper ──
_id_counter = 0
def new_id():
    global _id_counter
    _id_counter += 1
    return f"el_{int(time.time()*1000) % 1000000:06d}_{_id_counter:04d}"

def scene_id():
    global _id_counter
    _id_counter += 1
    return f"scene_{int(time.time()*1000) % 1000000:06d}_{_id_counter:04d}"

# ── Build scenes ──
all_scenes = []

# Delete existing scenes
for s in ps.list_scenes(DEMO_PID):
    ps.delete_scene(DEMO_PID, s["id"])
print("Cleared existing scenes")

for si, (name, w_start, w_end, theme_name) in enumerate(scene_defs):
    w_start = min(w_start, len(words) - 1)
    w_end = min(w_end, len(words))
    scene_words = words[w_start:w_end]
    if not scene_words:
        continue

    t = themes[theme_name]
    scene_start = scene_words[0]["start"]
    scene_end = scene_words[-1]["end"]
    scene_dur = round(scene_end - scene_start + 0.3, 2)

    elements = []

    # ── 1. CAPTIONS — every 5-6 words, timed to exact timestamps ──
    caption_group = []
    caption_start = None
    for wi, w in enumerate(scene_words):
        text = w["text"].strip()
        if not text:
            continue
        if caption_start is None:
            caption_start = w["start"]
        caption_group.append(w)

        # Break conditions
        next_gap = 999
        if wi + 1 < len(scene_words):
            next_gap = scene_words[wi + 1]["start"] - w["end"]
        is_pause = next_gap > 0.5
        is_full = len(caption_group) >= 6

        if (is_pause and len(caption_group) >= 3) or is_full:
            caption_text = " ".join(cw["text"] for cw in caption_group)
            # Position captions at bottom — vary by scene for visual interest
            cap_y = 82 if si % 2 == 0 else 78
            elements.append({
                "id": new_id(),
                "type": "caption",
                "content": caption_text,
                "x": 5, "y": cap_y, "width": 90, "height": 14,
                "start": round(caption_start - scene_start, 3),
                "end": round(caption_group[-1]["end"] - scene_start + 0.05, 3),
                "words": [
                    {"text": cw["text"],
                     "start": round(cw["start"] - scene_start, 3),
                     "end": round(cw["end"] - scene_start, 3)}
                    for cw in caption_group
                ],
                "style": {
                    "font": "Inter", "size": 44, "color": "#FFFFFF",
                    "highlight": t["highlight"],
                    "bg_color": "rgba(0,0,0,0.75)",
                    "border_radius": 14, "align": "center",
                },
            })
            caption_group = []
            caption_start = None

    # Flush remaining
    if caption_group:
        caption_text = " ".join(cw["text"] for cw in caption_group)
        cap_y = 82 if si % 2 == 0 else 78
        elements.append({
            "id": new_id(),
            "type": "caption",
            "content": caption_text,
            "x": 5, "y": cap_y, "width": 90, "height": 14,
            "start": round((caption_start or scene_start) - scene_start, 3),
            "end": round(caption_group[-1]["end"] - scene_start + 0.05, 3),
            "words": [
                {"text": cw["text"],
                 "start": round(cw["start"] - scene_start, 3),
                 "end": round(cw["end"] - scene_start, 3)}
                for cw in caption_group
            ],
            "style": {
                "font": "Inter", "size": 44, "color": "#FFFFFF",
                "highlight": t["highlight"],
                "bg_color": "rgba(0,0,0,0.75)",
                "border_radius": 14, "align": "center",
            },
        })

    # ── 2. SCENE TITLE — first 3 words, appears at scene start ──
    title_words = " ".join(w["text"] for w in scene_words[:3]).upper()
    # Make titles BIG and impactful
    title_y = 6
    elements.append({
        "id": new_id(),
        "type": "text",
        "content": title_words,
        "x": 5, "y": title_y, "width": 90, "height": 12,
        "font": "Inter", "size": 68, "color": t["title_color"],
        "weight": "bold", "align": "center",
        "start": 0,
        "end": round(min(scene_dur, 5), 3),
        "animation": {"type": "slide-down", "duration": 0.6},
    })

    # ── 3. ACCENT LINE — appears under title, stays for the scene ──
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "line",
        "x": 15, "y": 19, "width": 70, "height": 0.5,
        "fill": t["accent"],
        "start": 0.3,
        "end": round(scene_dur, 3),
        "animation": {"type": "fade-in", "duration": 0.4},
    })

    # ── 4. KEY PHRASE HIGHLIGHTS — large centered text at emphasis moments ──
    # Find 2-3 key moments per scene (longer words = key concepts)
    emphasis_indices = []
    for wi, w in enumerate(scene_words):
        text = w["text"].strip()
        # Key term: long word at a sentence boundary
        is_long = len(text) > 7
        is_sentence_start = wi > 0 and (w["start"] - scene_words[wi-1]["end"]) > 0.6
        if is_long and is_sentence_start and len(emphasis_indices) < 3:
            emphasis_indices.append(wi)
        elif len(text) > 8 and wi % 15 == 0 and len(emphasis_indices) < 3:
            emphasis_indices.append(wi)

    # If we didn't find enough, add one at the midpoint
    if len(emphasis_indices) < 2:
        mid = len(scene_words) // 2
        emphasis_indices.append(mid)

    for ei, word_idx in enumerate(emphasis_indices[:3]):
        if word_idx >= len(scene_words):
            continue
        kw = scene_words[word_idx]
        kw_text = kw["text"].upper()
        kw_start = kw["start"] - scene_start
        kw_end = kw["end"] - scene_start

        # Position varies: center, upper-right, lower-left
        positions = [
            {"x": 25, "y": 35, "w": 50, "h": 15, "size": 56},
            {"x": 55, "y": 22, "w": 38, "h": 12, "size": 42},
            {"x": 5, "y": 55, "w": 40, "h": 12, "size": 42},
        ]
        pos = positions[ei % 3]

        # Show the key term for 2 seconds around its spoken time
        show_start = max(0, kw_start - 0.2)
        show_end = kw_end + 2.0
        if show_end > scene_dur:
            show_end = scene_dur

        elements.append({
            "id": new_id(),
            "type": "text",
            "content": kw_text,
            "x": pos["x"], "y": pos["y"], "width": pos["w"], "height": pos["h"],
            "font": "Inter", "size": pos["size"], "color": t["secondary"],
            "weight": "bold", "align": "center",
            "start": round(show_start, 3),
            "end": round(show_end, 3),
            "bg_color": f"{t['accent']}18",
            "border_radius": 16,
            "animation": {"type": "zoom-in", "duration": 0.5},
        })

    # ── 5. DECORATIVE SHAPES — circles, lines for visual texture ──
    # Top-left corner decoration
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "circle",
        "x": 3, "y": 3, "width": 6, "height": 6,
        "fill": f"{t['accent']}15",
        "start": 0, "end": round(scene_dur, 3),
        "animation": {"type": "fade-in", "duration": 0.8},
    })

    # Bottom-right corner decoration
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "circle",
        "x": 90, "y": 88, "width": 4, "height": 4,
        "fill": f"{t['highlight']}20",
        "start": 0.5, "end": round(scene_dur, 3),
        "animation": {"type": "fade-in", "duration": 0.6},
    })

    # Left vertical accent line
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "line",
        "x": 2, "y": 22, "width": 0.5, "height": 55,
        "fill": f"{t['accent']}30",
        "start": 0.2, "end": round(scene_dur, 3),
        "animation": {"type": "fade-in", "duration": 0.5},
    })

    # ── 6. SCENE NUMBER / SECTION INDICATOR ──
    if si > 0:
        section_label = f"SECTION {si}"
        elements.append({
            "id": new_id(),
            "type": "text",
            "content": section_label,
            "x": 3, "y": 2, "width": 20, "height": 4,
            "font": "JetBrains Mono", "size": 14, "color": t["accent"],
            "weight": "500", "align": "left",
            "start": 0, "end": round(min(scene_dur, 4), 3),
            "animation": {"type": "fade-in", "duration": 0.3},
        })

    # ── 7. BOTTOM ACCENT BAR ──
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "rect",
        "x": 0, "y": 98.5, "width": 100, "height": 1.5,
        "fill": t["accent"],
        "start": 0, "end": round(scene_dur, 3),
    })

    # ── 8. PROGRESS INDICATOR — thin bar that grows across the scene ──
    elements.append({
        "id": new_id(),
        "type": "shape", "shape": "rect",
        "x": 0, "y": 97, "width": 100, "height": 0.3,
        "fill": f"{t['highlight']}40",
        "start": 0, "end": round(scene_dur, 3),
    })

    # ── Create scene ──
    scene = {
        "id": scene_id(),
        "name": name,
        "duration": scene_dur,
        "bg_color": t["bg"],
        "bg_pattern": t["pattern"],
        "audio_track": {
            "source": AUDIO_SRC,
            "duration": total_duration,
        },
        "elements": elements,
    }

    ps.add_scene(DEMO_PID, scene)
    all_scenes.append(scene)
    print(f"  Scene {si+1}: {name} ({scene_dur:.1f}s, {len(elements)} elements)")

# ── Summary ──
total_elements = sum(len(s["elements"]) for s in all_scenes)
total_scenes = len(all_scenes)
print(f"\n✅ Created {total_scenes} scenes with {total_elements} total elements")
print(f"   Total duration: {total_duration:.1f}s")
print(f"   Audio track: {AUDIO_SRC}")

# Verify audio file exists
if os.path.isfile(AUDIO_SRC):
    print(f"   ✅ Audio file exists: {os.path.getsize(AUDIO_SRC) / 1024 / 1024:.1f} MB")
else:
    print(f"   ❌ Audio file NOT found: {AUDIO_SRC}")
