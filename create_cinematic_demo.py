#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_cinematic_demo.py
========================
CINEMATIC demo: rich visuals tightly synced to exact word timestamps.
Every scene has a unique layout, dramatic text, key phrase highlights,
decorative elements, and visual storytelling that matches the narration.

FIXED: Key phrases now use scene-relative timestamps (not absolute).
FIXED: Key phrases found by word text search (not hardcoded indices).
"""

import os, sys, json, time, shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

# ── Config ──
DEMO_PID = "cd7824dc202a"
WORDS_PATH = os.path.join(ps.project_dir(DEMO_PID), "words.json")
AUDIO_SRC = "C:/Users/AITREC/AppData/Local/VideoComposerWork/cd7824dc202a/source.mp3"

# ── Load words ──
words = json.load(open(WORDS_PATH, encoding="utf-8"))
words = [w for w in words if w.get("text", "").strip()]
total_duration = words[-1]["end"] if words else 60
print(f"Total words: {len(words)}, duration: {total_duration:.1f}s")

# ── ID generators ──
_idc = 0
def eid():
    global _idc; _idc += 1
    return f"el_{int(time.time()*1000)%1000000:06d}_{_idc:04d}"

def sid():
    global _idc; _idc += 1
    return f"sc_{int(time.time()*1000)%1000000:06d}_{_idc:04d}"

# ── Scene definitions ──
SCENE_DEFS = [
    ("Hook — In My Last Video",           0,   22,  "hero-title",    "tech"),
    ("Layers — Database, Logic, Security", 22,  49,  "split-layout",  "neon"),
    ("How To Plan A Codebase",             49,  69,  "center-focus",  "bold"),
    ("Built To Be Read By Two Readers",    69,  100, "split-layout",  "dark"),
    ("AI Is Incredible But...",            100, 130, "center-focus",  "neon"),
    ("Here's The Deal",                   130, 175, "numbered-list", "tech"),
    ("We're Covering Four Things",        175, 215, "grid-4",        "bold"),
    ("Let's Build The Blueprint",         215, 254, "closing",       "neon"),
]

# ── Themes ──
THEMES = {
    "tech": {
        "bg": "#0a0e14", "accent": "#4a9eff", "highlight": "#FFD700",
        "secondary": "#00ff88", "dim": "#1a2332", "pattern": "bg-grid",
        "title_color": "#4a9eff", "key_color": "#00ff88",
    },
    "neon": {
        "bg": "#0d0221", "accent": "#00ffff", "highlight": "#ff00ff",
        "secondary": "#ffff00", "dim": "#1a0a3e", "pattern": "bg-vignette",
        "title_color": "#00ffff", "key_color": "#ff00ff",
    },
    "bold": {
        "bg": "#1a1a2e", "accent": "#e94560", "highlight": "#FFD700",
        "secondary": "#ff6b35", "dim": "#2a2a3e", "pattern": "bg-dots",
        "title_color": "#e94560", "key_color": "#ff6b35",
    },
    "dark": {
        "bg": "#0e1116", "accent": "#7c3aed", "highlight": "#fbbf24",
        "secondary": "#34d399", "dim": "#1e2028", "pattern": "bg-grid",
        "title_color": "#7c3aed", "key_color": "#34d399",
    },
}

def words_to_rel(ws, scene_start):
    """Convert absolute word timestamps to scene-relative."""
    return [
        {"text": w["text"],
         "start": round(w["start"] - scene_start, 3),
         "end": round(w["end"] - scene_start, 3)}
        for w in ws
    ]

def make_caption(ws, scene_start, scene_dur, theme, idx=0, y_pct=82):
    """Build a caption element from a list of words (absolute timestamps)."""
    if not ws: return None
    content = " ".join(w["text"] for w in ws)
    y_offset = (idx % 3) * 2
    return {
        "id": eid(), "type": "caption",
        "content": content,
        "x": 5, "y": y_pct + y_offset, "width": 90, "height": 12,
        "start": round(ws[0]["start"] - scene_start, 3),
        "end": round(ws[-1]["end"] - scene_start + 0.05, 3),
        "words": words_to_rel(ws, scene_start),
        "style": {
            "font": "Inter", "size": 40, "color": "#FFFFFF",
            "highlight": theme["highlight"],
            "bg_color": "rgba(0,0,0,0.80)",
            "border_radius": 12, "align": "center",
        },
    }

def make_text(content, x, y, w, h, size, color, theme, weight="bold",
              align="center", bg=None, radius=0, start=0, end=5, anim=None):
    el = {
        "id": eid(), "type": "text", "content": content,
        "x": x, "y": y, "width": w, "height": h,
        "font": "Inter", "size": size, "color": color,
        "weight": weight, "align": align,
        "start": round(start, 3), "end": round(end, 3),
    }
    if bg: el["bg_color"] = bg
    if radius: el["border_radius"] = radius
    if anim: el["animation"] = anim
    return el

def make_shape(shape_type, x, y, w, h, fill, start=0, end=5, anim=None, stroke=None):
    el = {
        "id": eid(), "type": "shape", "shape": shape_type,
        "x": x, "y": y, "width": w, "height": h,
        "fill": fill,
        "start": round(start, 3), "end": round(end, 3),
    }
    if anim: el["animation"] = anim
    if stroke: el["stroke"] = stroke
    return el

def make_key_phrase(text, x, y, w, h, size, color, bg_color, show_start, show_end, anim_type="zoom-in"):
    """All start/end MUST be scene-relative (0-based within the scene)."""
    return {
        "id": eid(), "type": "text", "content": text.upper(),
        "x": x, "y": y, "width": w, "height": h,
        "font": "Inter", "size": size, "color": color,
        "weight": "bold", "align": "center",
        "bg_color": bg_color, "border_radius": 16,
        "start": round(show_start, 3), "end": round(show_end, 3),
        "animation": {"type": anim_type, "duration": 0.4},
    }

# ── Delete old scenes ──
for s in ps.list_scenes(DEMO_PID):
    ps.delete_scene(DEMO_PID, s["id"])
print("Cleared old scenes")

# ══════════════════════════════════════════════════════════════════
# BUILD EACH SCENE
# ══════════════════════════════════════════════════════════════════
all_scenes = []

for si, (name, w_start, w_end, layout, theme_name) in enumerate(SCENE_DEFS):
    w_start = min(w_start, len(words) - 1)
    w_end = min(w_end, len(words))
    sw = words[w_start:w_end]
    if not sw: continue

    t = THEMES[theme_name]
    s0 = sw[0]["start"]   # absolute start time of scene
    s1 = sw[-1]["end"]    # absolute end time of scene
    dur = round(s1 - s0 + 0.4, 2)

    els = []

    # ─── HELPER: find word in scene by text (case-insensitive partial match) ───
    def find_word(search_text, start_from=0):
        """Find a word in sw by text, starting from start_from index.
        Returns (word_dict, scene_relative_start_time) or (None, None)."""
        search_lower = search_text.lower()
        for i in range(start_from, len(sw)):
            if search_lower in sw[i]["text"].lower():
                return sw[i], sw[i]["start"] - s0  # SCENE-RELATIVE!
        return None, None

    # ─── CAPTIONS (every 5-6 words, timed to exact timestamps) ───
    cap_group = []
    cap_start_w = None
    for wi, w in enumerate(sw):
        if not w["text"].strip(): continue
        if cap_start_w is None:
            cap_start_w = w
        cap_group.append(w)

        gap = 999
        if wi + 1 < len(sw):
            gap = sw[wi+1]["start"] - w["end"]
        full = len(cap_group) >= 6
        pause = gap > 0.5 and len(cap_group) >= 3

        if full or pause:
            c = make_caption(cap_group, s0, dur, t, idx=wi)
            if c: els.append(c)
            cap_group = []
            cap_start_w = None
    if cap_group:
        c = make_caption(cap_group, s0, dur, t, idx=w_end - w_start)
        if c: els.append(c)

    # ─── LAYOUT-SPECIFIC VISUAL ELEMENTS ───
    # ALL show_start/show_end values MUST be scene-relative (0 to dur)
    if layout == "hero-title":
        # Scene 1 (words 0-21): "In my last video...Apps Script"
        els.append(make_text(
            "IN MY LAST", 5, 8, 90, 14, 80, t["title_color"], t,
            start=0, end=6, anim={"type": "slide-down", "duration": 0.8}))
        els.append(make_text(
            "VIDEO", 5, 20, 90, 10, 56, "#FFFFFF", t,
            weight="normal", start=1.0, end=5.0,
            anim={"type": "fade-in", "duration": 0.6}))
        els.append(make_shape("line", 20, 31, 60, 0.5, t["accent"],
                              start=0.5, end=dur,
                              anim={"type": "fade-in", "duration": 0.4}))
        # "POSTEMPlATE" — search for it
        kw, kw_s = find_word("POSTemplate")
        if kw:
            els.append(make_key_phrase(
                "POSTEMPlATE", 15, 36, 70, 18, 72, t["key_color"],
                f"{t['accent']}15", kw_s, kw_s + 3.0, "elastic"))
        # "codebase"
        kw, kw_s = find_word("codebase")
        if kw:
            els.append(make_key_phrase(
                "CODEBASE", 20, 56, 60, 14, 56, t["highlight"],
                f"{t['accent']}15", kw_s, kw_s + 2.5, "zoom-in"))
        els.append(make_shape("circle", 3, 3, 5, 5, f"{t['accent']}20",
                              start=0, end=dur, anim={"type": "fade-in", "duration": 0.8}))
        els.append(make_shape("circle", 91, 85, 4, 4, f"{t['highlight']}20",
                              start=0.5, end=dur, anim={"type": "fade-in", "duration": 0.6}))
        els.append(make_shape("line", 2, 24, 0.4, 50, f"{t['accent']}30",
                              start=0.3, end=dur))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))

    elif layout == "split-layout":
        # Scene 2: Left title + Right key terms
        # Scene 4: Left title + Right key terms
        if si == 1:  # Scene 2
            els.append(make_text(
                "EVERY LAYER", 3, 5, 45, 10, 72, t["title_color"], t,
                start=0, end=6, anim={"type": "slide-left", "duration": 0.6}))
            els.append(make_text(
                "DATABASE", 3, 16, 45, 10, 56, t["key_color"], t,
                start=0.5, end=6.5, anim={"type": "slide-left", "duration": 0.6}))
            els.append(make_text(
                "LOGIC  SECURITY", 3, 26, 45, 8, 42, "#FFFFFF", t,
                weight="normal", start=1, end=7, anim={"type": "fade-in", "duration": 0.5}))
            # Right side: search for key words
            kw, kw_s = find_word("database")
            if kw: els.append(make_key_phrase(
                "DATABASE", 52, 28, 40, 12, 48, t["key_color"],
                f"{t['accent']}20", kw_s, kw_s + 3.0, "zoom-in"))
            kw, kw_s = find_word("business")
            if kw: els.append(make_key_phrase(
                "BUSINESS LOGIC", 52, 44, 42, 10, 40, t["highlight"],
                f"{t['accent']}15", kw_s, kw_s + 3.0, "slide-up"))
            kw, kw_s = find_word("security")
            if kw: els.append(make_key_phrase(
                "SECURITY", 52, 58, 38, 10, 44, "#ff4444",
                f"{t['accent']}15", kw_s, kw_s + 3.0, "elastic"))
            kw, kw_s = find_word("promise")
            if kw: els.append(make_key_phrase(
                "PROMISE", 52, 72, 36, 8, 40, t["highlight"],
                f"{t['accent']}20", kw_s, kw_s + 2.5, "bounce"))
        else:  # Scene 4
            els.append(make_text(
                "BUILT TO BE", 3, 5, 45, 10, 72, t["title_color"], t,
                start=0, end=6, anim={"type": "slide-left", "duration": 0.6}))
            els.append(make_text(
                "READ", 3, 16, 45, 10, 64, t["key_color"], t,
                start=0.5, end=6.5, anim={"type": "slide-left", "duration": 0.6}))
            els.append(make_text(
                "BY TWO READERS", 3, 26, 45, 8, 42, "#FFFFFF", t,
                weight="normal", start=1, end=7, anim={"type": "fade-in", "duration": 0.5}))
            kw, kw_s = find_word("organized")
            if kw: els.append(make_key_phrase(
                "ORGANIZED", 52, 28, 40, 12, 48, t["key_color"],
                f"{t['accent']}20", kw_s, kw_s + 3.0, "zoom-in"))
            kw, kw_s = find_word("humans")
            if kw: els.append(make_key_phrase(
                "HUMANS", 52, 44, 38, 10, 44, t["highlight"],
                f"{t['accent']}15", kw_s, kw_s + 2.5, "slide-up"))
            kw, kw_s = find_word("AI")
            if kw: els.append(make_key_phrase(
                "AI ASSISTANTS", 52, 58, 42, 10, 40, t["secondary"],
                f"{t['accent']}15", kw_s, kw_s + 3.0, "elastic"))
        els.append(make_shape("line", 50, 5, 0.4, 85, f"{t['accent']}30",
                              start=0.2, end=dur))
        els.append(make_text(
            f"SECTION {si}", 2, 2, 15, 3, 14, f"{t['accent']}80", t,
            weight="500", align="left", start=0, end=4,
            anim={"type": "fade-in", "duration": 0.3}))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))

    elif layout == "center-focus":
        # Scene 3: "How to plan a codebase..."
        # Scene 5: "I know agent-ready..."
        if si == 2:  # Scene 3
            els.append(make_text(
                "HOW TO PLAN", 5, 5, 90, 12, 76, t["title_color"], t,
                start=0, end=6, anim={"type": "zoom-in", "duration": 0.7}))
            els.append(make_shape("line", 25, 18, 50, 0.5, t["accent"],
                                  start=0.5, end=dur, anim={"type": "fade-in", "duration": 0.4}))
            kw, kw_s = find_word("codebase")
            if kw: els.append(make_key_phrase(
                "CODEBASE", 15, 25, 70, 20, 80, t["key_color"],
                f"{t['accent']}15", kw_s, kw_s + 3.5, "elastic"))
            kw, kw_s = find_word("single")
            if kw: els.append(make_key_phrase(
                "SINGLE LINE", 20, 52, 60, 14, 56, t["highlight"],
                f"{t['accent']}15", kw_s, kw_s + 2.5, "zoom-in"))
        else:  # Scene 5
            els.append(make_text(
                "AGENT-READY", 5, 5, 90, 12, 76, t["title_color"], t,
                start=0, end=6, anim={"type": "zoom-in", "duration": 0.7}))
            els.append(make_shape("line", 25, 18, 50, 0.5, t["accent"],
                                  start=0.5, end=dur, anim={"type": "fade-in", "duration": 0.4}))
            kw, kw_s = find_word("buzzword")
            if kw: els.append(make_key_phrase(
                "BUZZWORD", 15, 25, 70, 18, 68, t["key_color"],
                f"{t['accent']}15", kw_s, kw_s + 3.0, "elastic"))
            kw, kw_s = find_word("without")
            if kw: els.append(make_key_phrase(
                "WITHOUT A PLAN", 15, 50, 70, 14, 56, "#ff4444",
                f"{t['accent']}15", kw_s, kw_s + 3.0, "zoom-in"))
            kw, kw_s = find_word("guesses")
            if kw: els.append(make_key_phrase(
                "GUESSES", 25, 68, 50, 10, 44, t["highlight"],
                f"{t['accent']}15", kw_s, kw_s + 2.0, "bounce"))
        els.append(make_shape("circle", 90, 3, 4, 4, f"{t['highlight']}20",
                              start=0.3, end=dur))
        els.append(make_shape("circle", 3, 90, 3, 3, f"{t['accent']}20",
                              start=0.6, end=dur))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))
        els.append(make_text(
            f"SECTION {si}", 2, 2, 15, 3, 14, f"{t['accent']}80", t,
            weight="500", align="left", start=0, end=4,
            anim={"type": "fade-in", "duration": 0.3}))

    elif layout == "numbered-list":
        # Scene 6 (words 130-174): "So here's the deal...markdown files forever"
        els.append(make_text(
            "HERE'S THE DEAL", 5, 4, 90, 10, 72, t["title_color"], t,
            start=0, end=6, anim={"type": "slide-down", "duration": 0.7}))
        els.append(make_shape("line", 20, 15, 60, 0.5, t["accent"],
                              start=0.5, end=dur))
        kw, kw_s = find_word("end", start_from=3)  # skip "end" in "by the end"
        if kw: els.append(make_key_phrase(
            "BY THE END", 10, 22, 80, 10, 48, t["highlight"],
            f"{t['accent']}15", kw_s, kw_s + 3.0, "fade-in"))
        kw, kw_s = find_word("which")
        if kw: els.append(make_key_phrase(
            "WHICH FILES", 10, 34, 80, 10, 44, t["key_color"],
            f"{t['accent']}15", kw_s, kw_s + 4.0, "slide-left"))
        kw, kw_s = find_word("what")
        if kw: els.append(make_key_phrase(
            "WHAT GOES INSIDE", 10, 46, 80, 10, 44, t["highlight"],
            f"{t['accent']}15", kw_s, kw_s + 4.0, "slide-up"))
        kw, kw_s = find_word("lay")
        if kw: els.append(make_key_phrase(
            "HOW TO LAY OUT", 10, 58, 80, 10, 44, t["secondary"],
            f"{t['accent']}15", kw_s, kw_s + 4.0, "zoom-in"))
        kw, kw_s = find_word("markdown")
        if kw: els.append(make_key_phrase(
            "MARKDOWN FILES", 10, 70, 80, 10, 40, t["highlight"],
            f"{t['accent']}20", kw_s, kw_s + 3.0, "elastic"))
        els.append(make_text(
            "THE PROMISE", 2, 2, 15, 3, 14, f"{t['accent']}80", t,
            weight="500", align="left", start=0, end=4,
            anim={"type": "fade-in", "duration": 0.3}))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))

    elif layout == "grid-4":
        # Scene 7 (words 175-214): "We're covering four things..."
        els.append(make_text(
            "WE'RE COVERING", 5, 3, 90, 10, 68, t["title_color"], t,
            start=0, end=5, anim={"type": "slide-down", "duration": 0.6}))
        els.append(make_text(
            "FOUR THINGS", 5, 13, 90, 8, 48, "#FFFFFF", t,
            weight="normal", start=0.5, end=5.5,
            anim={"type": "fade-in", "duration": 0.5}))
        grid_items = [
            ("WHY CODEBASES", "FALL APART", "why", 25, t["accent"]),
            ("5 FILES THAT", "FIX IT", "five", 41, t["key_color"]),
            ("SMALL RULES", "HOLD IT TOGETHER", "small", 57, t["highlight"]),
            ("ONE IDEA", "CHANGES EVERYTHING", "one", 73, t["secondary"]),
        ]
        for i, (line1, line2, search, y_pct, color) in enumerate(grid_items):
            kw, kw_s = find_word(search)
            if kw:
                els.append(make_shape("rect", 8, y_pct - 1, 84, 14,
                                      f"{t['accent']}08", start=kw_s, end=kw_s + 8.0,
                                      anim={"type": "fade-in", "duration": 0.3}))
                els.append(make_text(
                    str(i+1), 10, y_pct, 6, 10, 42, color, t,
                    start=kw_s, end=kw_s + 8.0,
                    anim={"type": "zoom-in", "duration": 0.4}))
                els.append(make_text(
                    f"{line1}  {line2}", 18, y_pct, 72, 10, 36, "#FFFFFF", t,
                    weight="600", start=kw_s, end=kw_s + 8.0,
                    anim={"type": "slide-left", "duration": 0.4}))
        els.append(make_text(
            "THE BLUEPRINT", 2, 2, 15, 3, 14, f"{t['accent']}80", t,
            weight="500", align="left", start=0, end=4,
            anim={"type": "fade-in", "duration": 0.3}))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))

    elif layout == "closing":
        # Scene 8 (words 215-253): "Let's build the blueprint"
        els.append(make_text(
            "LET'S BUILD", 5, 15, 90, 14, 88, t["title_color"], t,
            start=0, end=8, anim={"type": "zoom-in", "duration": 0.8}))
        els.append(make_text(
            "THE BLUEPRINT", 5, 32, 90, 12, 72, t["key_color"], t,
            start=0.5, end=8.5, anim={"type": "zoom-in", "duration": 0.8}))
        els.append(make_shape("line", 15, 46, 70, 0.6, t["accent"],
                              start=1, end=dur, anim={"type": "fade-in", "duration": 0.5}))
        els.append(make_shape("line", 25, 48, 50, 0.4, t["highlight"],
                              start=1.5, end=dur, anim={"type": "fade-in", "duration": 0.4}))
        els.append(make_shape("circle", 4, 4, 8, 8, f"{t['accent']}12",
                              start=0, end=dur, anim={"type": "fade-in", "duration": 1.0}))
        els.append(make_shape("circle", 88, 80, 6, 6, f"{t['highlight']}15",
                              start=0.5, end=dur, anim={"type": "fade-in", "duration": 0.8}))
        els.append(make_text(
            "FINALE", 2, 2, 12, 3, 14, f"{t['accent']}80", t,
            weight="500", align="left", start=0, end=4,
            anim={"type": "fade-in", "duration": 0.3}))
        els.append(make_shape("rect", 0, 98.5, 100, 1.5, t["accent"],
                              start=0, end=dur))

    # ─── Create the scene ───
    scene = {
        "id": sid(),
        "name": name,
        "duration": dur,
        "bg_color": t["bg"],
        "bg_pattern": t["pattern"],
        "audio_track": {
            "source": AUDIO_SRC,
            "duration": total_duration,
        },
        "elements": els,
    }
    ps.add_scene(DEMO_PID, scene)
    all_scenes.append(scene)
    print(f"  Scene {si+1}: {name} ({dur:.1f}s, {len(els)} elements, {layout})")

# ── Summary ──
total_els = sum(len(s["elements"]) for s in all_scenes)
print(f"\n🎬 Created {len(all_scenes)} scenes with {total_els} total elements")
print(f"   Total duration: {total_duration:.1f}s")
if os.path.isfile(AUDIO_SRC):
    sz = os.path.getsize(AUDIO_SRC) / 1024 / 1024
    print(f"   ✅ Audio exists: {sz:.1f} MB")

for si, s in enumerate(all_scenes):
    types = {}
    for e in s["elements"]:
        types[e["type"]] = types.get(e["type"], 0) + 1
    print(f"   [{si+1}] {s['name']}: {dict(types)}")
