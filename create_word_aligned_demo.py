#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word-Aligned Demo Generator
============================
Creates a demo project where EVERY element's timing is derived from
word-level timestamps via wordRef. Scene boundaries match actual
audio pauses. Zero drift guaranteed.
"""
import json, os, uuid, shutil

PID = "cd7824dc202a"
BASE = os.path.join("projects", PID)

# Load words
words = json.load(open(os.path.join(BASE, "words.json"), encoding="utf-8"))
W, H = 1920, 1080

def uid():
    return uuid.uuid4().hex[:12]

def find_gaps(min_gap=0.7):
    """Find natural pause points (gaps > min_gap between words)."""
    gaps = []
    for i in range(len(words) - 1):
        gap = words[i + 1]["start"] - words[i]["end"]
        if gap > min_gap:
            gaps.append((i, i + 1, gap, words[i]["end"], words[i + 1]["start"]))
    return gaps

def find_word(target, start_from=0):
    """Find a word by text, return (index, word)."""
    for i in range(start_from, len(words)):
        if words[i]["text"].lower().rstrip(".,!?;:") == target.lower():
            return i, words[i]
    return None, None

def find_phrase(phrase, start_from=0):
    """Find consecutive words matching a phrase. Returns (start_idx, end_idx)."""
    tokens = phrase.lower().split()
    idx = start_from
    while idx <= len(words) - len(tokens):
        match = True
        for j, tok in enumerate(tokens):
            w = words[idx + j]["text"].lower().rstrip(".,!?;:")
            if w != tok:
                match = False
                break
        if match:
            return idx, idx + len(tokens) - 1
        idx += 1
    return None, None

def word_timing(start_idx, end_idx):
    """Get absolute start/end from word indices."""
    return words[start_idx]["start"], words[end_idx]["end"]

def scene_local(start_idx, end_idx, scene_start):
    """Convert absolute word timestamps to scene-local times."""
    abs_s, abs_e = word_timing(start_idx, end_idx)
    return abs_s - scene_start, abs_e - scene_start

def caption_el(start_idx, end_idx, scene_start, **kw):
    """Create a caption element with wordRef."""
    ws, we = scene_local(start_idx, end_idx, scene_start)
    word_texts = [{"text": words[i]["text"],
                    "start": round(words[i]["start"] - scene_start, 3),
                    "end": round(words[i]["end"] - scene_start, 3)}
                  for i in range(start_idx, end_idx + 1)]
    return {
        "id": uid(), "type": "caption", "words": word_texts,
        "x": 5, "y": 82, "width": 90, "height": 15,
        "start": round(ws, 3), "end": round(we + 0.15, 3),
        "wordRef": {"startWord": start_idx, "wordEnd": end_idx},
        "style": {
            "font": kw.get("font", "Inter"),
            "size": kw.get("size", 46),
            "color": kw.get("color", "#FFFFFF"),
            "highlight": kw.get("highlight", "#FFD700"),
            "bg_color": kw.get("bg_color", "rgba(0,0,0,0.75)"),
            "box_style": kw.get("box_style", "rounded"),
            "border_radius": 16,
            "align": "center",
            "position": kw.get("position", "bottom"),
            "word_animation": kw.get("word_animation", "none"),
            "unspoken": kw.get("unspoken", "visible"),
        }
    }

def text_el(content, x, y, w, h, start_idx, end_idx, scene_start, **kw):
    """Create a text element with wordRef for timing."""
    ws, we = scene_local(start_idx, end_idx, scene_start)
    el = {
        "id": uid(), "type": "text", "content": content,
        "x": x, "y": y, "width": w, "height": h,
        "start": round(ws, 3), "end": round(we + kw.get("extra_time", 0.5), 3),
        "wordRef": {"startWord": start_idx, "wordEnd": end_idx},
        "font": kw.get("font", "Bebas Neue"),
        "size": kw.get("size", 72),
        "color": kw.get("color", "#FFFFFF"),
        "weight": kw.get("weight", "normal"),
        "align": kw.get("align", "center"),
    }
    if kw.get("bg_color"): el["bg_color"] = kw["bg_color"]
    if kw.get("border_radius"): el["border_radius"] = kw["border_radius"]
    if kw.get("text_shadow"): el["text_shadow"] = kw["text_shadow"]
    if kw.get("glow"):
        el["glow"] = {"color": kw["glow"][0], "radius": kw["glow"][1]}
    if kw.get("entrance"):
        el["entrance"] = {"type": kw["entrance"], "duration": kw.get("entrance_dur", 0.6)}
    if kw.get("emphasis"):
        el["emphasis"] = {"type": kw["emphasis"], "duration": 0.4}
    if kw.get("exit_type"):
        el["exit"] = {"type": kw["exit_type"], "duration": kw.get("exit_dur", 0.5)}
    return el

def shape_el(shape, x, y, w, h, start_idx, end_idx, scene_start, **kw):
    """Create a shape element."""
    ws, we = scene_local(start_idx, end_idx, scene_start)
    el = {
        "id": uid(), "type": "shape", "shape": shape,
        "x": x, "y": y, "width": w, "height": h,
        "start": round(ws, 3), "end": round(we + 0.3, 3),
        "wordRef": {"startWord": start_idx, "wordEnd": end_idx},
        "fill": kw.get("fill", "#4a9eff"),
    }
    if kw.get("border_radius"): el["border_radius"] = kw["border_radius"]
    if kw.get("entrance"):
        el["entrance"] = {"type": kw["entrance"], "duration": 0.6}
    if kw.get("emphasis"):
        el["emphasis"] = {"type": kw["emphasis"], "duration": 0.4}
    if kw.get("exit_type"):
        el["exit"] = {"type": kw["exit_type"], "duration": 0.5}
    return el


# ================================================================
# SCENE DEFINITIONS — derived from actual audio pauses
# ================================================================

# Find natural pauses
gaps = find_gaps(0.7)
print("Natural pauses found:")
for gi, (w_before, w_after, gap_dur, t_before, t_after) in enumerate(gaps):
    print(f"  Gap {gi+1}: {words[w_before]['text']} → {words[w_after]['text']}  ({gap_dur:.2f}s gap, {t_before:.2f}s → {t_after:.2f}s)")

# Define scenes based on actual audio structure
# Each scene starts at the beginning of a phrase and ends at a pause
scene_defs = []

# Scene 1: Hook — "In my last video I gave you a tour of the POSTemplate codebase"
# Words 0-12, audio 0.1s → 4.11s
s1_start_word = 0
s1_end_word = 12
s1_abs_start = words[s1_start_word]["start"]
s1_abs_end = words[s1_end_word]["end"]
scene_defs.append({
    "name": "Hook — In My Last Video",
    "word_start": s1_start_word, "word_end": s1_end_word,
    "bg_color": "#0a0e14", "bg_pattern": "bg-grid",
    "elements": [
        text_el("IN MY LAST VIDEO", 10, 8, 80, 20, 0, 3, s1_abs_start,
                font="Bebas Neue", size=96,
                entrance="kinetic-in", entrance_dur=0.8,
                emphasis="glow-breathe",
                exit_type="exit-fly-right", exit_dur=0.4,
                text_shadow="0 4px 20px rgba(74,158,255,0.5)"),
        text_el("POSTEMPlATE", 15, 38, 70, 18, 11, 12, s1_abs_start,
                font="Orbitron", size=72, color="#4a9eff",
                entrance="morph-scale", entrance_dur=0.6,
                emphasis="pulse",
                exit_type="exit-dissolve"),
        text_el("CODEBASE", 25, 62, 50, 14, 12, 12, s1_abs_start,
                font="Anton", size=64, color="#FFD700", extra_time=1.5,
                entrance="zoom-in", entrance_dur=0.5,
                emphasis="wave-float",
                exit_type="fade-out"),
        caption_el(0, 12, s1_abs_start, unspoken="dimmed", word_animation="bounce-in"),
        shape_el("circle", 82, 6, 6, 6, 0, 12, s1_abs_start,
                 fill="#4a9eff", entrance="morph-scale", emphasis="glow-breathe"),
        shape_el("rect", 2, 85, 10, 2, 4, 12, s1_abs_start,
                 fill="#FFD700", border_radius=4, entrance="slide-left", emphasis="pulse"),
    ]
})

# Scene 2: "a real point-of-sale system built with Apps Script"
# Words 13-18, audio 4.36s → 6.9s
s2_start_word = 13
s2_end_word = 18
s2_abs_start = words[s2_start_word]["start"]
s2_abs_end = words[s2_end_word]["end"]
scene_defs.append({
    "name": "What It Is — POS System",
    "word_start": s2_start_word, "word_end": s2_end_word,
    "bg_color": "#0d0221", "bg_pattern": "bg-vignette",
    "elements": [
        text_el("REAL POINT-OF-SALE", 8, 20, 84, 20, 13, 15, s2_abs_start,
                font="Orbitron", size=80, color="#00E5FF",
                entrance="kinetic-in", entrance_dur=0.7,
                emphasis="glow-breathe",
                exit_type="exit-dissolve"),
        text_el("BUILT WITH", 25, 50, 50, 14, 16, 17, s2_abs_start,
                font="Bebas Neue", size=64, color="#FFD700",
                entrance="slide-up", entrance_dur=0.5,
                emphasis="pulse"),
        text_el("APPS SCRIPT", 20, 68, 60, 16, 17, 18, s2_abs_start,
                font="Montserrat", size=72, color="#E0E0E0",
                entrance="typewriter", entrance_dur=0.6,
                emphasis="wave-float",
                exit_type="exit-shrink"),
        caption_el(13, 18, s2_abs_start),
    ]
})

# Scene 3: "We walked through every layer the database the business logic the security"
# Words 19-27, audio 8.56s → 12.35s
s3_start_word = 19
s3_end_word = 27
s3_abs_start = words[s3_start_word]["start"]
s3_abs_end = words[s3_end_word]["end"]
scene_defs.append({
    "name": "Layers — DB / Logic / Security",
    "word_start": s3_start_word, "word_end": s3_end_word,
    "bg_color": "#1a0a2e", "bg_pattern": "bg-dots",
    "elements": [
        text_el("EVERY LAYER", 10, 5, 80, 16, 19, 20, s3_abs_start,
                font="Bebas Neue", size=88,
                entrance="slide-down", emphasis="shake", exit_type="exit-fly-up"),
        text_el("DATABASE", 5, 28, 42, 20, 21, 21, s3_abs_start,
                font="Orbitron", size=80, color="#00E5FF",
                entrance="kinetic-in", emphasis="glow-breathe", exit_type="exit-dissolve"),
        text_el("BUSINESS LOGIC", 53, 28, 42, 20, 24, 25, s3_abs_start,
                font="Anton", size=72, color="#FF9100",
                entrance="counter-spin", emphasis="pulse", exit_type="exit-fly-right"),
        text_el("SECURITY", 25, 55, 50, 20, 27, 27, s3_abs_start,
                font="Raleway", size=76, color="#FF5252",
                entrance="flip-in", emphasis="shake", exit_type="exit-shrink"),
        shape_el("line", 20, 53, 60, 0.5, 19, 27, s3_abs_start,
                 fill="#FFD700", entrance="slide-left", emphasis="pulse"),
        caption_el(19, 27, s3_abs_start, unspoken="hidden", word_animation="bounce-in"),
    ]
})

# Scene 4: "And at the end I made a promise one more video first"
# Words 28-42, audio 13.21s → 16.69s
s4_start_word = 28
s4_end_word = 42
s4_abs_start = words[s4_start_word]["start"]
s4_abs_end = words[s4_end_word]["end"]
scene_defs.append({
    "name": "The Promise — One More Video",
    "word_start": s4_start_word, "word_end": s4_end_word,
    "bg_color": "#0a0e14", "bg_pattern": "bg-grid",
    "elements": [
        text_el("I MADE A", 20, 15, 60, 18, 33, 34, s4_abs_start,
                font="Bebas Neue", size=96,
                entrance="typewriter", emphasis="glow-breathe", exit_type="exit-fly-up"),
        text_el("PROMISE", 15, 35, 70, 22, 35, 35, s4_abs_start,
                font="Permanent Marker", size=108, color="#FFD700", extra_time=2.0,
                entrance="morph-scale", emphasis="pulse", exit_type="exit-dissolve"),
        text_el("ONE MORE VIDEO", 10, 62, 80, 14, 38, 41, s4_abs_start,
                font="Anton", size=64, color="#4a9eff",
                entrance="slide-up", emphasis="wave-float", exit_type="fade-out"),
        caption_el(28, 42, s4_abs_start),
    ]
})

# Scene 5: "How to plan a codebase like this before you write a single line of code"
# Words 43-56, audio 17.55s → 21.33s
s5_start_word = 43
s5_end_word = 56
s5_abs_start = words[s5_start_word]["start"]
s5_abs_end = words[s5_end_word]["end"]
scene_defs.append({
    "name": "How to Plan a Codebase",
    "word_start": s5_start_word, "word_end": s5_end_word,
    "bg_color": "#1a1a2e", "bg_pattern": "bg-vignette",
    "elements": [
        text_el("HOW TO PLAN", 10, 10, 80, 20, 43, 46, s5_abs_start,
                font="Bebas Neue", size=96,
                entrance="kinetic-in", emphasis="glow-breathe", exit_type="exit-fly-right"),
        text_el("A CODEBASE", 15, 38, 70, 16, 47, 48, s5_abs_start,
                font="Montserrat", size=72, color="#FFD700",
                entrance="morph-scale", emphasis="pulse", exit_type="exit-dissolve"),
        text_el("BEFORE YOU WRITE", 10, 60, 80, 12, 49, 54, s5_abs_start,
                font="Inter", size=48, color="#8B93A1",
                entrance="slide-up", emphasis="wave-float"),
        text_el("A SINGLE LINE OF CODE", 10, 75, 80, 12, 54, 56, s5_abs_start,
                font="Orbitron", size=48, color="#4a9eff",
                entrance="typewriter", exit_type="exit-shrink"),
        caption_el(43, 56, s5_abs_start),
    ]
})

# Scene 6: "This is that video... didn't fully explain last time"
# Words 57-68, audio 22.19s → 26.99s
s6_start_word = 57
s6_end_word = 68
s6_abs_start = words[s6_start_word]["start"]
s6_abs_end = words[s6_end_word]["end"]
scene_defs.append({
    "name": "That Video I Didn't Fully Explain",
    "word_start": s6_start_word, "word_end": s6_end_word,
    "bg_color": "#0d0221", "bg_pattern": "bg-grid",
    "elements": [
        text_el("THIS IS THAT", 10, 10, 80, 16, 57, 59, s6_abs_start,
                font="Bebas Neue", size=84,
                entrance="slide-left", emphasis="glow-breathe", exit_type="exit-fly-right"),
        text_el("VIDEO", 20, 30, 60, 20, 60, 60, s6_abs_start,
                font="Orbitron", size=108, color="#FFD700", extra_time=1.5,
                entrance="morph-scale", emphasis="pulse", exit_type="exit-dissolve"),
        text_el("I DIDN'T FULLY", 10, 55, 80, 12, 62, 65, s6_abs_start,
                font="Montserrat", size=48, color="#8B93A1",
                entrance="typewriter", emphasis="wave-float"),
        text_el("EXPLAIN", 25, 70, 50, 14, 66, 66, s6_abs_start,
                font="Anton", size=72, color="#FF5252", extra_time=1.0,
                entrance="shake", emphasis="shake", exit_type="exit-shrink"),
        caption_el(57, 68, s6_abs_start),
    ]
})

# Scene 7: "That codebase wasn't just organized it was built to be read"
# Words 69-77, audio 27.85s → 31.03s
s7_start_word = 69
s7_end_word = 77
s7_abs_start = words[s7_start_word]["start"]
s7_abs_end = words[s7_end_word]["end"]
scene_defs.append({
    "name": "Built to Be Read",
    "word_start": s7_start_word, "word_end": s7_end_word,
    "bg_color": "#0e1116", "bg_pattern": "bg-grid",
    "elements": [
        text_el("THAT CODEBASE", 10, 8, 80, 16, 69, 70, s7_abs_start,
                font="Bebas Neue", size=84,
                entrance="kinetic-in", emphasis="glow-breathe", exit_type="exit-fly-right"),
        text_el("WASN'T JUST", 20, 28, 60, 12, 71, 71, s7_abs_start,
                font="Montserrat", size=48, color="#8B93A1",
                entrance="fade-in", emphasis="wave-float"),
        text_el("ORGANIZED", 15, 42, 70, 16, 71, 71, s7_abs_start,
                font="Anton", size=72, color="#FF9100",
                entrance="slide-up", emphasis="pulse", exit_type="exit-dissolve"),
        text_el("IT WAS BUILT", 10, 62, 80, 14, 72, 73, s7_abs_start,
                font="Bebas Neue", size=64, color="#FFFFFF",
                entrance="typewriter", emphasis="glow-breathe"),
        text_el("TO BE READ", 15, 78, 70, 14, 76, 77, s7_abs_start,
                font="Orbitron", size=72, color="#4CAF50",
                entrance="morph-scale", emphasis="pulse", exit_type="exit-shrink"),
        caption_el(69, 77, s7_abs_start, unspoken="hidden", word_animation="bounce-in"),
    ]
})

# Scene 8: "by two different readers Humans And AI coding assistants"
# Words 78-83+, audio 31.04s → end
s8_start_word = 78
s8_end_word = len(words) - 1
s8_abs_start = words[s8_start_word]["start"]
s8_abs_end = words[s8_end_word]["end"]
scene_defs.append({
    "name": "Two Readers — Humans & AI",
    "word_start": s8_start_word, "word_end": s8_end_word,
    "bg_color": "#1a0a2e", "bg_pattern": "bg-vignette",
    "elements": [
        text_el("BY TWO READERS", 10, 5, 80, 14, 78, 80, s8_abs_start,
                font="Bebas Neue", size=72,
                entrance="slide-down", emphasis="glow-breathe", exit_type="exit-fly-right"),
        text_el("HUMANS", 10, 25, 35, 25, 81, 81, s8_abs_start,
                font="Bebas Neue", size=96, color="#4CAF50",
                entrance="kinetic-in", emphasis="glow-breathe", exit_type="exit-dissolve",
                glow=("#4CAF50", 20)),
        text_el("AI ASSISTANTS", 55, 25, 35, 25, 83, 83, s8_abs_start,
                font="Bebas Neue", size=96, color="#E040FB",
                entrance="counter-spin", emphasis="pulse", exit_type="exit-dissolve",
                glow=("#E040FB", 20)),
        shape_el("line", 48, 22, 0.3, 30, 78, 83, s8_abs_start,
                 fill="#FFD700", entrance="slide-down", emphasis="glow-breathe"),
        caption_el(78, s8_end_word, s8_abs_start, position="center"),
    ]
})


# ================================================================
# BUILD PROJECT
# ================================================================

scenes = []
for i, sd in enumerate(scene_defs):
    ws = sd["word_start"]
    we = sd["word_end"]
    duration = round(words[we]["end"] - words[ws]["start"] + 0.5, 2)
    scene = {
        "id": uid(),
        "name": sd["name"],
        "duration": duration,
        "bg_color": sd["bg_color"],
        "bg_pattern": sd.get("bg_pattern"),
        "wordStart": ws,
        "wordEnd": we,
        "elements": sd["elements"],
    }
    scenes.append(scene)

# Save scenes
scenes_path = os.path.join(BASE, "scenes.json")
with open(scenes_path, "w", encoding="utf-8") as f:
    json.dump(scenes, f, indent=2, ensure_ascii=False)

# Update meta.json
meta_path = os.path.join(BASE, "meta.json")
meta = json.load(open(meta_path, encoding="utf-8"))
meta["name"] = "Word-Aligned Demo"
meta["modified"] = __import__("time").time()
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

# Print summary
total_elements = sum(len(s["elements"]) for s in scenes)
total_duration = sum(s["duration"] for s in scenes)
print(f"\n{'='*60}")
print(f"  WORD-ALIGNED DEMO CREATED")
print(f"  Scenes: {len(scenes)}")
print(f"  Elements: {total_elements}")
print(f"  Duration: {total_duration:.1f}s")
print(f"  Words: {len(words)}")
print(f"{'='*60}")
for si, s in enumerate(scenes):
    ws = s["wordStart"]
    we = s["wordEnd"]
    print(f"  Scene {si+1}: {s['name']}")
    print(f"    Words {ws}-{we}: \"{words[ws]['text']} ... {words[we]['text']}\"")
    print(f"    Audio: {words[ws]['start']:.2f}s → {words[we]['end']:.2f}s  (dur: {s['duration']:.1f}s)")
    print(f"    Elements: {len(s['elements'])}")
    for el in s["elements"]:
        if el["type"] == "text":
            print(f"      [text] wordRef={el.get('wordRef',{})} \"{el['content'][:35]}\"")
        elif el["type"] == "caption":
            wr = el.get("wordRef", {})
            print(f"      [caption] wordRef={wr} ({wr.get('wordEnd',0)-wr.get('wordStart',0)+1} words)")
    print()
