#!/usr/bin/env python3
"""
Word-by-Word Motion Graphics Demo — Karaoke Style
===================================================
Each word appears CENTERED on screen at its EXACT spoken timestamp.
Only the currently-spoken word is visible — big, bold, animated.
A small running caption at bottom shows the full phrase.
Timing comes 100% from words.json — zero drift.
"""
import json, os, hashlib, random

random.seed(42)
PROJECT_ID = "cd7824dc202a"
BASE = os.path.join("projects", PROJECT_ID)

with open(os.path.join(BASE, "words.json"), encoding="utf-8") as f:
    WORDS = json.load(f)

print(f"Loaded {len(WORDS)} words")

# ── Group words into scenes by natural pauses ──────────────────
PAUSE_THRESHOLD = 0.55
scene_breaks = [0]
for i in range(len(WORDS) - 1):
    gap = WORDS[i + 1]["start"] - WORDS[i]["end"]
    if gap >= PAUSE_THRESHOLD:
        scene_breaks.append(i + 1)
scene_breaks.append(len(WORDS))

scenes_word_ranges = []
for j in range(len(scene_breaks) - 1):
    scenes_word_ranges.append((scene_breaks[j], scene_breaks[j + 1]))

print(f"Split into {len(scenes_word_ranges)} scenes")

# ── Emphasis words (appear bigger & colored) ───────────────────
EMPHASIS = {
    "postemPlate", "POSTemplate", "codebase", "database", "security",
    "promise", "agent-ready", "buzzword", "humans", "ai", "blueprint",
    "readers", "organized", "built", "code", "docs", "plan",
    "incredible", "guess", "guesses", "want", "deal", "files",
    "create", "project", "knows", "rules", "markdown", "forever",
    "every", "single", "line", "one", "idea", "four", "things",
    "five", "fix", "together"
}

ACCENT_COLORS = [
    "#FFD700", "#4a9eff", "#ff6b6b", "#50fa7b",
    "#ff79c6", "#bd93f9", "#f1fa8c", "#8be9fd"
]

BG_PALETTE = [
    "#0a0e14", "#0d0221", "#1a1a2e", "#0f3460",
    "#16213e", "#0a1628", "#1b0a2e", "#0d0221",
    "#0a0e14", "#1a1a2e"
]

ENTRANCE_ANIMS = ["kinetic-in", "morph-scale", "zoom-in", "slide-up", "slide-left", "fade-in", "counter-spin", "flip-in"]
EXIT_ANIMS = ["exit-dissolve", "exit-fly-right", "exit-fly-up", "fade-out"]

def uid():
    return hashlib.md5(str(random.random()).encode()).hexdigest()[:12]

def is_emphasis(word):
    return word.lower().rstrip(".,!?;:'\"") in {e.lower() for e in EMPHASIS}

# ── Build scenes ───────────────────────────────────────────────
scene_objects = []

for si, (w_start, w_end) in enumerate(scenes_word_ranges):
    first_w = WORDS[w_start]
    last_w = WORDS[w_end - 1]

    scene_start = first_w["start"] - 0.15
    scene_end = last_w["end"] + 0.6
    scene_dur = scene_end - scene_start

    bg = BG_PALETTE[si % len(BG_PALETTE)]
    elements = []

    # ── 1. One BIG word element per word (karaoke style) ──────
    for wi in range(w_start, w_end):
        w = WORDS[wi]
        emph = is_emphasis(w["text"])

        accent = ACCENT_COLORS[hash(w["text"]) % len(ACCENT_COLORS)]

        if emph:
            size = 96
            color = accent
            weight = "900"
            glow_r = 16
        else:
            size = 72
            color = "#FFFFFF"
            weight = "700"
            glow_r = 0

        entrance = random.choice(ENTRANCE_ANIMS)
        exit_anim = random.choice(EXIT_ANIMS)

        el = {
            "id": uid(),
            "type": "text",
            "x": 50, "y": 45,
            "width": 80, "height": 20,
            "content": w["text"],
            "font": "Inter",
            "size": size,
            "color": color,
            "weight": weight,
            "align": "center",
            "bg_color": "transparent",
            "entrance": {"type": entrance, "duration": 0.25},
            "emphasis": {"type": "none", "duration": 0},
            "exit": {"type": exit_anim, "duration": 0.2},
            "wordRef": {
                "startWord": wi,
                "endWord": wi,
                "padBefore": 0.02,
                "padAfter": 0.02
            },
            "visible": True
        }

        if glow_r > 0:
            el["text_shadow"] = f"0 0 {glow_r}px {color}, 0 0 {glow_r * 2}px {color}"

        elements.append(el)

    # ── 2. Running phrase caption at bottom ───────────────────
    phrase = " ".join(WORDS[i]["text"] for i in range(w_start, w_end))
    elements.append({
        "id": uid(),
        "type": "text",
        "x": 50, "y": 92,
        "width": 90, "height": 6,
        "content": phrase,
        "font": "Inter",
        "size": 24,
        "color": "rgba(255,255,255,0.45)",
        "weight": "400",
        "align": "center",
        "bg_color": "transparent",
        "entrance": {"type": "fade-in", "duration": 0.4},
        "exit": {"type": "fade-out", "duration": 0.4},
        "wordRef": {
            "startWord": w_start,
            "endWord": w_end - 1,
            "padBefore": 0.1,
            "padAfter": 0.1
        },
        "visible": True
    })

    # ── 3. Decorative line under main word ────────────────────
    elements.append({
        "id": uid(),
        "type": "shape",
        "x": 30, "y": 55,
        "width": 40, "height": 0.3,
        "shape": "line",
        "fill": ACCENT_COLORS[si % len(ACCENT_COLORS)],
        "stroke_width": 3,
        "stroke": "none",
        "border_radius": 0,
        "entrance": {"type": "fade-in", "duration": 0.3},
        "exit": {"type": "fade-out", "duration": 0.3},
        "wordRef": {
            "startWord": w_start,
            "endWord": w_end - 1,
            "padBefore": 0.05,
            "padAfter": 0.05
        },
        "visible": True
    })

    scene_obj = {
        "id": uid(),
        "name": f"Phrase {si + 1}: {phrase[:40]}...",
        "duration": round(scene_dur, 3),
        "bg_color": bg,
        "bg_pattern": None,
        "wordStart": w_start,
        "wordEnd": w_end - 1,
        "elements": elements
    }
    scene_objects.append(scene_obj)

    print(f"  Scene {si+1:2d}: words {w_start:3d}-{w_end-1:3d} "
          f"({scene_start:.2f}s → {scene_end:.2f}s, {scene_dur:.2f}s) "
          f"{len(elements):3d} elements")

# ── Write output ───────────────────────────────────────────────
scenes_path = os.path.join(BASE, "scenes.json")
with open(scenes_path, "w", encoding="utf-8") as f:
    json.dump(scene_objects, f, indent=2, ensure_ascii=False)

total_dur = sum(s["duration"] for s in scene_objects)
total_el = sum(len(s["elements"]) for s in scene_objects)

print(f"\n{'='*60}")
print(f"WORD-BY-WORD DEMO GENERATED")
print(f"{'='*60}")
print(f"Scenes:    {len(scene_objects)}")
print(f"Elements:  {total_el}")
print(f"Duration:  {total_dur:.1f}s (audio: {WORDS[-1]['end']:.1f}s)")
print(f"Output:    {scenes_path}")
print(f"{'='*60}")
print(f"\nEach word element has wordRef pointing to its EXACT word index.")
print(f"Only ONE word is visible at a time — big, centered, animated.")
print(f"Previous words vanish, next word appears at the spoken moment.")
print(f"\nTo test: Ctrl+Shift+R → play → watch word-by-word karaoke.")
