#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_demo_v3.py
==================
Clean demo showcasing audio-driven scene generation.
Creates a project with properly wired audio, word-timed captions,
and visual elements placed at exact audio timestamps.
"""

import os
import sys
import json
import time
import uuid
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

SRC_PID = "d0e217336789"  # Hook project with audio


def new_id():
    return uuid.uuid4().hex[:12]


def el_id():
    return "el_" + new_id()


def main():
    # Read source data
    src_meta = ps._read_json(os.path.join(ps.project_dir(SRC_PID), "meta.json")) or {}
    src_words_path = os.path.join(ps.project_dir(SRC_PID), "words.json")
    src_words = []
    if os.path.isfile(src_words_path):
        src_words = json.load(open(src_words_path, encoding="utf-8"))

    if not src_words:
        print("ERROR: No words.json found in source project!")
        return

    total_duration = max(w.get("end", 0) for w in src_words) if src_words else 60
    print(f"Source: {len(src_words)} words, {total_duration:.1f}s total")

    # Find audio source
    audio_path = os.path.join(ps.fast_dir(SRC_PID), "source.mp3")
    if not os.path.isfile(audio_path):
        print(f"ERROR: Audio not found at {audio_path}")
        return
    print(f"Audio: {audio_path}")

    # Delete old demo projects (clean slate)
    for p in ps.list_projects():
        pid_check = p.get("id", "")
        meta = ps._read_json(os.path.join(ps.project_dir(pid_check), "meta.json")) or {}
        pname = meta.get("name", "")
        if "Demo" in pname and pid_check != SRC_PID:
            ps.delete_project(pid_check)
            print(f"Deleted old demo: {pid_check}")

    # Create new project
    proj = ps.create_project("Audio-Driven Demo", 1920, 1080)
    pid = proj["id"]

    # Copy audio to this project's fast_dir
    vc_fast = ps.fast_dir(pid)
    os.makedirs(vc_fast, exist_ok=True)
    audio_dest = os.path.join(vc_fast, "source.mp3")
    shutil.copy2(audio_path, audio_dest)
    print(f"Copied audio -> {audio_dest}")

    # Copy words.json
    words_dest = os.path.join(ps.project_dir(pid), "words.json")
    shutil.copy2(src_words_path, words_dest)

    # Store audio track (same for all scenes)
    audio_track = {
        "source": audio_dest,
        "duration": total_duration,
        "words_json": words_dest,
    }

    # Theme
    accent = "#4a9eff"
    highlight = "#FFD700"
    bg = "#0a0e14"
    pattern = "bg-grid"

    # Split words into scenes at natural pauses
    scenes_data = split_words(src_words, target=80)

    scenes_created = []

    for scene_idx, scene_words in enumerate(scenes_data):
        if not scene_words:
            continue

        scene_start = scene_words[0].get("start", 0)
        scene_end = scene_words[-1].get("end", scene_start + 5)
        scene_duration = round(scene_end - scene_start + 0.5, 1)

        # Build captions (4-6 word groups, timed to exact word timestamps)
        captions = build_captions(scene_words, scene_start)

        # Build visual elements at precise audio moments
        visuals = build_visuals(
            scene_words, scene_idx, len(scenes_data),
            scene_start, scene_end, scene_duration,
            accent, highlight, bg
        )

        scene = {
            "id": "scene_" + new_id(),
            "name": scene_name(scene_words, scene_idx, len(scenes_data)),
            "duration": scene_duration,
            "bg_color": bg,
            "bg_pattern": pattern if scene_idx % 2 == 0 else "bg-dots",
            "audio_track": audio_track,
            "elements": captions + visuals,
        }

        ps.add_scene(pid, scene)
        scenes_created.append(scene)

    # Verify
    scenes = ps.list_scenes(pid)
    total_elements = sum(len(s.get("elements", [])) for s in scenes)
    total_anims = sum(
        sum(1 for e in s.get("elements", []) if e.get("animation"))
        for s in scenes
    )

    print(f"\n{'='*60}")
    print(f"Demo project created: {pid}")
    print(f"Name: Audio-Driven Demo")
    print(f"Scenes: {len(scenes)}")
    print(f"Total elements: {total_elements}")
    print(f"Animated elements: {total_anims}")
    print(f"Total duration: {total_duration:.1f}s")
    print(f"Audio track: {audio_track['source'][:60]}...")
    print(f"\nScene breakdown:")
    offset = 0
    for i, s in enumerate(scenes):
        dur = s.get("duration", 0)
        elems = len(s.get("elements", []))
        anims = sum(1 for e in s.get("elements", []) if e.get("animation"))
        pattern_name = s.get("bg_pattern", "solid")
        print(f"  Scene {i+1}: {s.get('name', '?')}")
        print(f"    Time: {offset:.1f}s - {offset+dur:.1f}s ({dur:.1f}s)")
        print(f"    Elements: {elems} ({anims} animated)")
        print(f"    Background: {pattern_name}")
        offset += dur

    print(f"\nOpen http://127.0.0.1:8768 -> Projects -> '{pid}'")
    print(f"All elements are timed to EXACT word timestamps!")
    print(f"{'='*60}")


def split_words(words, target=80):
    """Split words into scenes at natural pauses."""
    if not words:
        return []

    scenes = []
    current = []

    for i, w in enumerate(words):
        text = w.get("text", "").strip()
        if not text:
            continue
        current.append(w)

        is_break = False
        if i + 1 < len(words):
            gap = words[i + 1].get("start", 0) - w.get("end", 0)
            if gap > 0.8:
                is_break = True

        is_full = len(current) >= target

        if (is_break and len(current) >= 20) or (is_full and is_break):
            scenes.append(current)
            current = []
        elif is_full and not is_break:
            scenes.append(current)
            current = []

    if current:
        scenes.append(current)

    return scenes


def build_captions(words, scene_start):
    """Build caption elements from words, 4-6 words per caption."""
    captions = []
    group = []
    group_start = None

    for i, w in enumerate(words):
        text = w.get("text", "").strip()
        if not text:
            continue
        start = w.get("start", 0)
        end = w.get("end", 0)

        if group_start is None:
            group_start = start
        group.append(w)

        next_start = words[i + 1].get("start", 0) if i + 1 < len(words) else None
        gap = (next_start - end) if next_start else 999

        if gap > 0.4 or len(group) >= 6:
            text_content = " ".join(cw.get("text", "") for cw in group)
            captions.append({
                "id": el_id(),
                "type": "caption",
                "content": text_content,
                "x": 5, "y": 80, "width": 90, "height": 15,
                "start": round(group_start - scene_start, 3),
                "end": round(end - scene_start + 0.1, 3),
                "words": [
                    {
                        "text": cw.get("text", ""),
                        "start": round(cw.get("start", 0) - scene_start, 3),
                        "end": round(cw.get("end", 0) - scene_start, 3),
                    }
                    for cw in group
                ],
                "style": {
                    "font": "Inter", "size": 46, "color": "#FFFFFF",
                    "highlight": "#FFD700",
                    "bg_color": "rgba(0,0,0,0.7)",
                    "border_radius": 12, "align": "center",
                },
            })
            group = []
            group_start = None

    # Flush remaining
    if group:
        text_content = " ".join(cw.get("text", "") for cw in group)
        captions.append({
            "id": el_id(),
            "type": "caption",
            "content": text_content,
            "x": 5, "y": 80, "width": 90, "height": 15,
            "start": round((group_start or 0) - scene_start, 3),
            "end": round(group[-1].get("end", 0) - scene_start + 0.1, 3),
            "words": [
                {
                    "text": cw.get("text", ""),
                    "start": round(cw.get("start", 0) - scene_start, 3),
                    "end": round(cw.get("end", 0) - scene_start, 3),
                }
                for cw in group
            ],
            "style": {
                "font": "Inter", "size": 46, "color": "#FFFFFF",
                "highlight": "#FFD700",
                "bg_color": "rgba(0,0,0,0.7)",
                "border_radius": 12, "align": "center",
            },
        })

    return captions


def build_visuals(words, scene_idx, total, scene_start, scene_end, scene_dur, accent, highlight, bg):
    """Build visual elements timed to exact audio moments."""
    visuals = []
    first_word_start = words[0].get("start", 0) - scene_start if words else 0

    # === Scene title — first 3 words, timed to when they're spoken ===
    if scene_idx > 0:
        title_words = " ".join(w.get("text", "") for w in words[:3]).upper()
        title_end = min(scene_dur, 6)

        visuals.append({
            "id": el_id(), "type": "text",
            "content": title_words,
            "x": 8, "y": 4, "width": 84, "height": 10,
            "font": "Inter", "size": 68, "color": accent,
            "weight": "bold", "align": "center",
            "start": round(max(0, first_word_start), 3),
            "end": round(title_end, 3),
            "bg_color": f"{accent}11",
            "border_radius": 16,
            "animation": {"type": "bounce", "duration": 0.7},
        })

    # === Accent line — appears with first word, stays until scene end ===
    visuals.append({
        "id": el_id(), "type": "shape", "shape": "line",
        "x": 8, "y": 16, "width": 84, "height": 1,
        "fill": f"{accent}66", "stroke_width": 2,
        "start": round(max(0, first_word_start + 0.2), 3),
        "end": round(scene_dur, 3),
        "animation": {"type": "fade-in", "duration": 0.4},
    })

    # === Decorative circles at sentence boundaries ===
    circle_positions = [(86, 6, 5), (3, 72, 4), (88, 68, 6)]
    circle_idx = 0
    for i, w in enumerate(words):
        if i > 0 and circle_idx < 3:
            gap = w.get("start", 0) - words[i - 1].get("end", 0)
            if gap > 0.6:
                cx, cy, cs = circle_positions[circle_idx]
                visuals.append({
                    "id": el_id(), "type": "shape", "shape": "circle",
                    "x": cx, "y": cy, "width": cs, "height": cs,
                    "fill": f"{accent}18",
                    "start": round(w.get("start", 0) - scene_start, 3),
                    "end": round(scene_dur, 3),
                    "animation": {"type": "fade-in", "duration": 0.5},
                })
                circle_idx += 1

    # === Bottom accent bar ===
    visuals.append({
        "id": el_id(), "type": "shape", "shape": "rect",
        "x": 0, "y": 98, "width": 100, "height": 2,
        "fill": accent,
        "start": 0, "end": round(scene_dur, 3),
    })

    return visuals


def scene_name(words, idx, total):
    """Generate scene name from first 3 words."""
    if not words:
        return f"Scene {idx + 1}"
    first = " ".join(w.get("text", "") for w in words[:3])
    if idx == 0:
        return f"Opening - {first}..."
    if idx == total - 1:
        return f"Closing - {first}..."
    return f"Scene {idx + 1} - {first}..."


if __name__ == "__main__":
    main()
