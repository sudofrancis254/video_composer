#!/usr/bin/env python3
"""
Motion Graphics Typography Demo
Uses the full 3-phase animation system:
  - Entrance: kinetic-in, morph-scale, slide-up, zoom-in, typewriter, flip-in, counter-spin, blur-in
  - Emphasis: glow-breathe, pulse, shake, glitch, wave-float, color-shift
  - Exit: exit-dissolve, exit-fly-right, exit-shrink, fade-out
Also uses background patterns and animated shapes.
"""
import json, os, uuid, shutil

PID = "cd7824dc202a"
BASE = os.path.join("projects", PID)
WORK = os.path.join(os.path.expanduser("~"), "AppData", "Local", "VideoComposerWork", PID)

# Load words
words = json.load(open(os.path.join(BASE, "words.json"), encoding="utf-8"))
W, H = 1920, 1080

def uid():
    return uuid.uuid4().hex[:12]

def find_word(target, start_from=0):
    """Find a word (case-insensitive) starting from index start_from. Returns (index, word_obj)."""
    for i in range(start_from, len(words)):
        if words[i]["text"].lower().rstrip(".,!?;:") == target.lower():
            return i, words[i]
    return None, None

def find_phrase(phrase, start_from=0):
    """Find consecutive words matching a phrase. Returns (start_idx, end_idx, start_time, end_time)."""
    tokens = phrase.lower().split()
    idx = start_from
    while idx < len(words) - len(tokens):
        match = True
        for j, tok in enumerate(tokens):
            w = words[idx + j]["text"].lower().rstrip(".,!?;:")
            if w != tok:
                match = False
                break
        if match:
            return idx, idx + len(tokens) - 1, words[idx]["start"], words[idx + len(tokens) - 1]["end"]
        idx += 1
    return None, None, 0, 0

def caption_for_words(start_idx, end_idx):
    """Build word-level timestamps for a range of words."""
    return [{"text": words[i]["text"], "start": words[i]["start"], "end": words[i]["end"]} for i in range(start_idx, min(end_idx + 1, len(words)))]

def text_el(content, x, y, w, h, start, end, font="Bebas Neue", size=72, color="#FFFFFF", weight="normal",
            entrance="none", entrance_dur=0.6, emphasis="none", exit_type="none", exit_dur=0.5,
            bg_color=None, border_radius=0, glow_color=None, glow_radius=0, text_shadow=None):
    el = {
        "id": uid(), "type": "text", "content": content,
        "x": x, "y": y, "width": w, "height": h,
        "start": round(start, 3), "end": round(end, 3),
        "font": font, "size": size, "color": color, "weight": weight, "align": "center"
    }
    if bg_color:
        el["bg_color"] = bg_color
        el["border_radius"] = border_radius
    if glow_color:
        el["glow"] = {"color": glow_color, "radius": glow_radius}
    if text_shadow:
        el["text_shadow"] = text_shadow
    # 3-phase animations
    if entrance != "none":
        el["entrance"] = {"type": entrance, "duration": entrance_dur}
    if emphasis != "none":
        el["emphasis"] = {"type": emphasis, "duration": 0.4}
    if exit_type != "none":
        el["exit"] = {"type": exit_type, "duration": exit_dur}
    return el

def shape_el(shape, x, y, w, h, start, end, fill="#4a9eff", stroke=None, border_radius=0,
             entrance="none", emphasis="none", exit_type="none"):
    el = {
        "id": uid(), "type": "shape", "shape": shape,
        "x": x, "y": y, "width": w, "height": h,
        "start": round(start, 3), "end": round(end, 3),
        "fill": fill
    }
    if stroke:
        el["stroke"] = stroke
        el["stroke_width"] = 2
    if border_radius:
        el["border_radius"] = border_radius
    if entrance != "none":
        el["entrance"] = {"type": entrance, "duration": 0.6}
    if emphasis != "none":
        el["emphasis"] = {"type": emphasis, "duration": 0.4}
    if exit_type != "none":
        el["exit"] = {"type": exit_type, "duration": 0.5}
    return el

def caption_el(start_idx, end_idx, font="Inter", size=48, color="#FFFFFF", highlight="#FFD700",
               bg_color="rgba(0,0,0,0.75)", box_style="rounded", position="bottom",
               word_animation="none", word_delay=0, unspoken="visible",
               entrance="none", exit_type="none"):
    ws = caption_for_words(start_idx, end_idx)
    if not ws:
        return None
    s0 = ws[0]["start"]
    s1 = ws[-1]["end"]
    el = {
        "id": uid(), "type": "caption", "words": ws,
        "x": 5, "y": 82, "width": 90, "height": 16,
        "start": round(s0, 3), "end": round(s1 + 0.2, 3),
        "style": {
            "font": font, "size": size, "color": color, "highlight": highlight,
            "bg_color": bg_color, "box_style": box_style, "border_radius": 16,
            "align": "center", "position": position,
            "word_animation": word_animation, "word_delay": word_delay,
            "unspoken": unspoken
        }
    }
    if entrance != "none":
        el["entrance"] = {"type": entrance, "duration": 0.5}
    if exit_type != "none":
        el["exit"] = {"type": exit_type, "duration": 0.4}
    return el

# ===== SCENE DEFINITIONS =====

scenes = []

# ─── SCENE 1: Hook — "IN MY LAST VIDEO" ───────────────────────
# Words 0-11: "In my last video I gave you a tour of the POSTemplate codebase"
s0 = find_phrase("In my last video I gave you a tour of the POSTemplate codebase")
scene1_dur = 5.0
scene1 = {
    "id": uid(), "name": "Hook — In My Last Video",
    "duration": round(scene1_dur, 2),
    "bg_color": "#0a0e14", "bg_pattern": "bg-grid",
    "elements": [
        # Big hero title — kinetic entrance, glow breathe emphasis, fly-right exit
        text_el("IN MY LAST VIDEO", 10, 10, 80, 20, 0.0, 4.5,
                font="Bebas Neue", size=96, color="#FFFFFF",
                entrance="kinetic-in", entrance_dur=0.8,
                emphasis="glow-breathe",
                exit_type="exit-fly-right", exit_dur=0.4,
                text_shadow="0 4px 20px rgba(74,158,255,0.5)"),
        # "POSTEmplate" zooms in at the exact word moment
        text_el("POSTEMPlATE", 20, 38, 60, 18, s0[2], s0[3] + 1.0,
                font="Orbitron", size=72, color="#4a9eff",
                entrance="morph-scale", entrance_dur=0.6,
                emphasis="pulse",
                exit_type="exit-dissolve", exit_dur=0.5),
        # "CODEBASE" at bottom
        text_el("CODEBASE", 30, 65, 40, 14, s0[3], s0[3] + 1.5,
                font="Anton", size=64, color="#FFD700",
                entrance="zoom-in", entrance_dur=0.5,
                emphasis="wave-float",
                exit_type="fade-out", exit_dur=0.3),
        # Decorative shapes
        shape_el("circle", 78, 5, 8, 8, 0.0, 4.5, fill="#4a9eff",
                 entrance="morph-scale", emphasis="glow-breathe", exit_type="exit-dissolve"),
        shape_el("rect", 2, 80, 12, 3, 0.5, 4.5, fill="#FFD700", border_radius=4,
                 entrance="slide-left", emphasis="pulse", exit_type="exit-shrink"),
    ]
}
scenes.append(scene1)

# ─── SCENE 2: LAYERS — Database, Logic, Security ───────────────
# Words 12-30: "every layer the database the business logic the security"
idx_db, w_db, t_db_s, t_db_e = find_phrase("the database")
idx_bl, w_bl, t_bl_s, t_bl_e = find_phrase("business logic")
idx_sc, w_sc, t_sc_s, t_sc_e = find_phrase("security")
scene2_start = 4.8
scene2_dur = 7.0
scene2 = {
    "id": uid(), "name": "Layers — DB / Logic / Security",
    "duration": round(scene2_dur, 2),
    "bg_color": "#0d0221", "bg_pattern": "bg-vignette",
    "elements": [
        # Title
        text_el("EVERY LAYER", 10, 5, 80, 18, 0.0, 6.5,
                font="Bebas Neue", size=88, color="#FFFFFF",
                entrance="slide-down", entrance_dur=0.6,
                emphasis="shake", exit_type="exit-fly-up"),
        # DATABASE — kinetic entrance at word time
        text_el("DATABASE", 5, 30, 42, 20, t_db_s - scene2_start, t_db_s - scene2_start + 2.5,
                font="Orbitron", size=80, color="#00E5FF",
                entrance="kinetic-in", entrance_dur=0.7,
                emphasis="glow-breathe",
                exit_type="exit-dissolve"),
        # BUSINESS LOGIC
        text_el("BUSINESS LOGIC", 53, 30, 42, 20, t_bl_s - scene2_start, t_bl_s - scene2_start + 2.5,
                font="Anton", size=72, color="#FF9100",
                entrance="counter-spin", entrance_dur=0.8,
                emphasis="pulse",
                exit_type="exit-fly-right"),
        # SECURITY
        text_el("SECURITY", 25, 58, 50, 20, t_sc_s - scene2_start, t_sc_s - scene2_start + 2.5,
                font="Raleway", size=76, color="#FF5252",
                entrance="flip-in", entrance_dur=0.7,
                emphasis="shake",
                exit_type="exit-shrink"),
        # Decorative line
        shape_el("line", 20, 56, 60, 0.5, 0.5, 6.5, fill="#FFD700",
                 entrance="slide-left", emphasis="pulse", exit_type="exit-dissolve"),
        # Three small dots
        shape_el("circle", 35, 85, 4, 4, 0.5, 6.5, fill="#4a9eff",
                 entrance="morph-scale", emphasis="glow-breathe"),
        shape_el("circle", 48, 85, 4, 4, 0.8, 6.5, fill="#FFD700",
                 entrance="morph-scale", emphasis="glow-breathe"),
        shape_el("circle", 61, 85, 4, 4, 1.1, 6.5, fill="#FF5252",
                 entrance="morph-scale", emphasis="glow-breathe"),
    ]
}
scenes.append(scene2)

# ─── SCENE 3: PROMISE — "One more video first" ────────────────
# Words around index 30-50: "I made a promise one more video first How to plan a codebase"
idx_promise, _, t_promise_s, t_promise_e = find_phrase("I made a promise")
idx_plan, _, t_plan_s, t_plan_e = find_phrase("How to plan a codebase")
scene3_start = 13.0
scene3_dur = 6.0
scene3 = {
    "id": uid(), "name": "Promise — One More Video",
    "duration": round(scene3_dur, 2),
    "bg_color": "#1a1a2e", "bg_pattern": "bg-dots",
    "elements": [
        # "I MADE A PROMISE" — big dramatic text with typewriter entrance
        text_el("I MADE A", 20, 15, 60, 18, 0.0, 5.0,
                font="Bebas Neue", size=96, color="#FFFFFF",
                entrance="typewriter", entrance_dur=0.8,
                emphasis="glow-breathe",
                exit_type="exit-fly-up"),
        text_el("PROMISE", 15, 35, 70, 22, t_promise_e - scene3_start - 0.5, t_promise_e - scene3_start + 2.0,
                font="Permanent Marker", size=108, color="#FFD700",
                entrance="morph-scale", entrance_dur=0.9,
                emphasis="pulse",
                exit_type="exit-dissolve"),
        # "HOW TO PLAN A CODEBASE" at bottom
        text_el("HOW TO PLAN", 10, 62, 80, 15, t_plan_s - scene3_start, t_plan_s - scene3_start + 2.5,
                font="Anton", size=72, color="#4a9eff",
                entrance="slide-up", entrance_dur=0.6,
                emphasis="wave-float",
                exit_type="fade-out"),
        text_el("A CODEBASE", 15, 78, 70, 14, t_plan_e - scene3_start - 1.0, t_plan_e - scene3_start + 1.5,
                font="Montserrat", size=60, color="#E0E0E0",
                entrance="zoom-in", entrance_dur=0.5,
                exit_type="exit-shrink"),
        # Arrow shape
        shape_el("triangle", 42, 55, 16, 12, 1.0, 5.0, fill="#FFD700",
                 entrance="slide-up", emphasis="pulse", exit_type="exit-fly-right"),
    ]
}
scenes.append(scene3)

# ─── SCENE 4: BUILT TO BE READ — Two Readers ────────────────
# Words 50-80: "This is that video... it was built to be read by two different readers"
idx_built, _, t_built_s, t_built_e = find_phrase("built to be read")
idx_humans, _, t_humans_s, t_humans_e = find_phrase("Humans")
idx_ai, _, t_ai_s, t_ai_e = find_phrase("AI coding assistants")
scene4_start = t_built_s - 1.0
scene4_dur = 8.0
scene4 = {
    "id": uid(), "name": "Two Readers — Humans & AI",
    "duration": round(scene4_dur, 2),
    "bg_color": "#0e1116", "bg_pattern": "bg-grid",
    "elements": [
        # Title
        text_el("BUILT TO BE READ", 10, 8, 80, 16, 0.0, 7.0,
                font="Bebas Neue", size=84, color="#FFFFFF",
                entrance="slide-left", entrance_dur=0.6,
                emphasis="glow-breathe",
                exit_type="exit-fly-right"),
        # By line
        text_el("BY TWO READERS", 20, 28, 60, 12, 0.5, 7.0,
                font="Montserrat", size=48, color="#8B93A1",
                entrance="fade-in", emphasis="wave-float"),
        # HUMANS — left side with glow
        text_el("HUMANS", 10, 48, 35, 22, t_humans_s - scene4_start, t_humans_s - scene4_start + 3.0,
                font="Bebas Neue", size=96, color="#4CAF50",
                entrance="kinetic-in", entrance_dur=0.7,
                emphasis="glow-breathe",
                exit_type="exit-dissolve",
                glow_color="#4CAF50", glow_radius=20),
        # AI ASSISTANTS — right side
        text_el("AI ASSISTANTS", 55, 48, 35, 22, t_ai_s - scene4_start, t_ai_s - scene4_start + 3.0,
                font="Bebas Neue", size=96, color="#E040FB",
                entrance="counter-spin", entrance_dur=0.8,
                emphasis="pulse",
                exit_type="exit-dissolve",
                glow_color="#E040FB", glow_radius=20),
        # Divider line
        shape_el("line", 48, 45, 0.3, 30, 1.0, 7.0, fill="#FFD700",
                 entrance="slide-down", emphasis="glow-breathe"),
        # Decorative dots
        shape_el("circle", 8, 44, 3, 3, 2.0, 7.0, fill="#4CAF50",
                 entrance="morph-scale", emphasis="pulse"),
        shape_el("circle", 89, 44, 3, 3, 2.5, 7.0, fill="#E040FB",
                 entrance="morph-scale", emphasis="pulse"),
    ]
}
scenes.append(scene4)

# ─── SCENE 5: AGENT-READY — Not a Buzzword ──────────────────
idx_agent, _, t_agent_s, t_agent_e = find_phrase("agent-ready")
idx_buzz, _, t_buzz_s, t_buzz_e = find_phrase("buzzword")
idx_guess, _, t_guess_s, t_guess_e = find_phrase("guesses")
scene5_start = t_agent_s - 1.0
scene5_dur = 8.0
scene5 = {
    "id": uid(), "name": "Agent-Ready — Not a Buzzword",
    "duration": round(scene5_dur, 2),
    "bg_color": "#1a0a2e", "bg_pattern": "bg-vignette",
    "elements": [
        # AGENT-READY — big, glowing, morph entrance
        text_el("AGENT-READY", 10, 12, 80, 24, 0.5, 7.0,
                font="Orbitron", size=108, color="#00E5FF",
                entrance="morph-scale", entrance_dur=1.0,
                emphasis="glow-breathe",
                exit_type="exit-dissolve",
                glow_color="#00E5FF", glow_radius=30,
                text_shadow="0 0 40px rgba(0,229,255,0.4)"),
        # "sounds like a buzzword" — strikethrough style
        text_el("SOUNDS LIKE A", 20, 45, 60, 12, t_buzz_s - scene5_start - 0.5, t_buzz_s - scene5_start + 1.5,
                font="Montserrat", size=40, color="#8B93A1",
                entrance="slide-up", emphasis="wave-float", exit_type="fade-out"),
        text_el("BUZZWORD", 25, 58, 50, 16, t_buzz_s - scene5_start, t_buzz_s - scene5_start + 2.0,
                font="Anton", size=72, color="#FF5252",
                entrance="shake", entrance_dur=0.5,
                emphasis="shake",
                exit_type="exit-shrink"),
        # "UNTIL I SAW HOW IT CHANGES EVERYTHING"
        text_el("UNTIL I SAW", 10, 75, 35, 10, t_guess_s - scene5_start - 2.0, t_guess_s - scene5_start + 0.5,
                font="Montserrat", size=36, color="#FFFFFF",
                entrance="typewriter", exit_type="fade-out"),
        text_el("HOW IT CHANGES", 48, 75, 45, 10, t_guess_s - scene5_start - 1.5, t_guess_s - scene5_start + 1.0,
                font="Montserrat", size=36, color="#FFD700",
                entrance="slide-right", emphasis="glow-breathe"),
        # Decorative shapes
        shape_el("rect", 5, 40, 2, 35, 0.0, 7.0, fill="#00E5FF",
                 entrance="slide-down", emphasis="glow-breathe", exit_type="exit-dissolve"),
        shape_el("circle", 90, 10, 6, 6, 1.0, 7.0, fill="#E040FB",
                 entrance="morph-scale", emphasis="pulse", exit_type="exit-shrink"),
    ]
}
scenes.append(scene5)

# ─── SCENE 6: THE DEAL — Four Things ────────────────────────
idx_which, _, t_which_s, t_which_e = find_phrase("which files")
idx_inside, _, t_inside_s, t_inside_e = find_phrase("what goes inside")
idx_lay, _, t_lay_s, t_lay_e = find_phrase("how to lay out")
idx_markdown, _, t_md_s, t_md_e = find_phrase("markdown files")
scene6_start = t_which_s - 1.5
scene6_dur = 10.0
scene6 = {
    "id": uid(), "name": "The Deal — Four Things",
    "duration": round(scene6_dur, 2),
    "bg_color": "#0a0e14", "bg_pattern": "bg-grid",
    "elements": [
        text_el("HERE'S THE DEAL", 10, 5, 80, 16, 0.0, 9.0,
                font="Bebas Neue", size=84, color="#FFD700",
                entrance="kinetic-in", entrance_dur=0.8,
                emphasis="glow-breathe",
                exit_type="exit-fly-right"),
        # Numbered list items appear one by one
        text_el("01  WHICH FILES EXIST", 12, 26, 75, 12,
                t_which_s - scene6_start, t_inside_s - scene6_start,
                font="Inter", size=48, color="#FFFFFF",
                entrance="slide-left", entrance_dur=0.5,
                emphasis="pulse",
                exit_type="exit-fly-right"),
        text_el("02  WHAT GOES INSIDE", 12, 42, 75, 12,
                t_inside_s - scene6_start, t_lay_s - scene6_start,
                font="Inter", size=48, color="#FFFFFF",
                entrance="slide-left", entrance_dur=0.5,
                emphasis="pulse",
                exit_type="exit-fly-right"),
        text_el("03  HOW TO LAY OUT", 12, 58, 75, 12,
                t_lay_s - scene6_start, t_md_s - scene6_start,
                font="Inter", size=48, color="#FFFFFF",
                entrance="slide-left", entrance_dur=0.5,
                emphasis="pulse",
                exit_type="exit-fly-right"),
        text_el("04  MARKDOWN FILES", 12, 74, 75, 12,
                t_md_s - scene6_start, t_md_s - scene6_start + 2.5,
                font="Inter", size=48, color="#4a9eff",
                entrance="slide-left", entrance_dur=0.5,
                emphasis="glow-breathe",
                exit_type="exit-dissolve"),
        # Side accent
        shape_el("rect", 5, 24, 3, 65, 0.5, 9.0, fill="#FFD700",
                 entrance="slide-down", emphasis="glow-breathe"),
    ]
}
scenes.append(scene6)

# ─── SCENE 7: FOUR THINGS — Grid ───────────────────────────
idx_four, _, t_four_s, t_four_e = find_phrase("four things")
idx_idea, _, t_idea_s, t_idea_e = find_phrase("one idea")
idx_docs, _, t_docs_s, t_docs_e = find_phrase("markdown files")  # re-use
idx_other, _, t_other_s, t_other_e = find_phrase("everybody else")
scene7_start = t_four_s - 1.0
scene7_dur = 10.0
# Grid of 4 items
items = [
    ("ONE IDEA", t_idea_s - scene7_start, t_idea_s - scene7_start + 2.5, "#4a9eff"),
    ("THE STRUCTURE", t_idea_e + 0.5 - scene7_start, t_idea_e + 3.0 - scene7_start, "#FFD700"),
    ("THE DOCS", t_docs_s - scene7_start, t_docs_s - scene7_start + 2.5, "#FF9100"),
    ("EVERYBODY ELSE", t_other_s - scene7_start, t_other_s - scene7_start + 2.5, "#E040FB"),
]
grid_positions = [(5, 15), (52, 15), (5, 55), (52, 55)]
scene7 = {
    "id": uid(), "name": "Four Things Grid",
    "duration": round(scene7_dur, 2),
    "bg_color": "#0d1117", "bg_pattern": "bg-dots",
    "elements": [
        text_el("WE'RE COVERING", 10, 3, 80, 10, 0.0, 9.0,
                font="Bebas Neue", size=64, color="#FFFFFF",
                entrance="slide-down", emphasis="wave-float"),
        text_el("FOUR THINGS", 20, 10, 60, 12, 0.5, 9.0,
                font="Orbitron", size=56, color="#FFD700",
                entrance="morph-scale", emphasis="pulse"),
    ]
}
for i, (label, t_s, t_e, color) in enumerate(items):
    gx, gy = grid_positions[i]
    # Number box
    scene7["elements"].append(
        shape_el("rect", gx, gy, 42, 35, t_s, t_e + 1.0, fill="#1a1e24", border_radius=12,
                 entrance="morph-scale", emphasis="glow-breathe", exit_type="exit-shrink"))
    scene7["elements"].append(
        text_el(str(i+1), gx + 15, gy + 3, 12, 10, t_s, t_e + 1.0,
                font="Bebas Neue", size=64, color=color,
                entrance="zoom-in", emphasis="pulse", exit_type="fade-out"))
    scene7["elements"].append(
        text_el(label, gx + 2, gy + 22, 38, 10, t_s + 0.3, t_e + 1.0,
                font="Montserrat", size=36, color="#FFFFFF",
                entrance="slide-up", emphasis="wave-float", exit_type="exit-dissolve"))
scenes.append(scene7)

# ─── SCENE 8: CLOSING — Let's Build The Blueprint ───────────
idx_build, _, t_build_s, t_build_e = find_phrase("let's build")
idx_bp, _, t_bp_s, t_bp_e = find_phrase("the blueprint")
scene8_start = t_build_s - 1.0
scene8_dur = 5.0
scene8 = {
    "id": uid(), "name": "Closing — Build The Blueprint",
    "duration": round(scene8_dur, 2),
    "bg_color": "#0d0221", "bg_pattern": "bg-gradient-radial",
    "elements": [
        # Big dramatic closing text
        text_el("LET'S BUILD", 10, 15, 80, 20, 0.5, 4.5,
                font="Bebas Neue", size=108, color="#FFFFFF",
                entrance="kinetic-in", entrance_dur=0.9,
                emphasis="glow-breathe",
                exit_type="exit-dissolve",
                glow_color="#4a9eff", glow_radius=25),
        text_el("THE BLUEPRINT", 5, 40, 90, 28, 1.0, 4.5,
                font="Orbitron", size=120, color="#FFD700",
                entrance="morph-scale", entrance_dur=1.0,
                emphasis="glow-breathe",
                exit_type="exit-fly-right",
                glow_color="#FFD700", glow_radius=35,
                text_shadow="0 0 60px rgba(255,215,0,0.4)"),
        # Decorative lines
        shape_el("line", 15, 72, 70, 0.4, 0.0, 4.5, fill="#FFD700",
                 entrance="slide-left", emphasis="glow-breathe", exit_type="exit-dissolve"),
        shape_el("line", 15, 80, 70, 0.4, 0.3, 4.5, fill="#4a9eff",
                 entrance="slide-right", emphasis="pulse", exit_type="exit-dissolve"),
        # Corner accents
        shape_el("circle", 2, 2, 4, 4, 0.0, 4.5, fill="#4a9eff",
                 entrance="morph-scale", emphasis="pulse"),
        shape_el("circle", 93, 2, 4, 4, 0.0, 4.5, fill="#FFD700",
                 entrance="morph-scale", emphasis="pulse"),
    ]
}
scenes.append(scene8)

# ===== SAVE PROJECT =====
# Read existing scenes.json to preserve audio reference
scenes_file = os.path.join(BASE, "scenes.json")
existing = {}
if os.path.exists(scenes_file):
    existing = json.load(open(scenes_file, encoding="utf-8"))

# Copy audio from existing project if available
work_audio = os.path.join(WORK, "source.mp3")
if not os.path.exists(WORK):
    os.makedirs(WORK, exist_ok=True)

# Save scenes.json
with open(scenes_file, "w", encoding="utf-8") as f:
    json.dump(scenes, f, indent=2, ensure_ascii=False)

# Also save to work dir
work_scenes = os.path.join(WORK, "scenes.json")
with open(work_scenes, "w", encoding="utf-8") as f:
    json.dump(scenes, f, indent=2, ensure_ascii=False)

total_elements = sum(len(s["elements"]) for s in scenes)
print(f"✅ Motion Graphics Demo created!")
print(f"   {len(scenes)} scenes, {total_elements} elements")
print(f"   Total duration: {sum(s['duration'] for s in scenes):.1f}s")
print(f"   Scenes:")
for i, s in enumerate(scenes):
    anims = set()
    for el in s["elements"]:
        for phase in ["entrance", "emphasis", "exit"]:
            a = el.get(phase)
            if a and a.get("type") and a["type"] != "none":
                anims.add(f"{phase[:3]}:{a['type']}")
    print(f"   {i+1}. {s['name']} ({s['duration']}s) — {len(s['elements'])} els — {', '.join(sorted(anims)[:5])}...")
