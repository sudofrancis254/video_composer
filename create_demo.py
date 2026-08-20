#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_demo.py
==============
Creates a demo Video Composer project using the hook audio,
split into 3 scenes with title text and shape elements added by AI.
"""

import os
import sys
import json
import time
import uuid
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

# Source project with hook audio
SRC_PID = "d0e217336789"

def new_id():
    return uuid.uuid4().hex[:12]

def main():
    # Read source scenes
    src_scenes = ps.list_scenes(SRC_PID)
    if not src_scenes:
        print("ERROR: Source project has no scenes")
        return
    src_captions = src_scenes[0].get("elements", [])
    audio_track = src_scenes[0].get("audio_track")
    duration = src_scenes[0].get("duration", 93)

    print(f"Source: {len(src_captions)} captions, duration={duration}s")

    # Create new project
    proj = ps.create_project("Agent-Ready Codebase - Demo", 1920, 1080)
    pid = proj["id"]

    # Copy audio file from source project
    src_meta = ps._read_json(os.path.join(ps.project_dir(SRC_PID), "meta.json")) or {}
    audio_source = src_meta.get("audio_source")
    if audio_source:
        # Update audio track source to point to the source project's audio
        # (we'll reference it directly from the source project's fast dir)
        src_audio_path = os.path.join(ps.fast_dir(SRC_PID), "audio.mp3")
        if os.path.isfile(src_audio_path):
            dst_audio_path = os.path.join(ps.fast_dir(pid), "audio.mp3")
            shutil.copy2(src_audio_path, dst_audio_path)
            print(f"Copied audio: {src_audio_path} -> {dst_audio_path}")
        else:
            print(f"WARNING: Source audio not found at {src_audio_path}")

    # ---- SCENE 1: Hook (0-22s) ----
    # Filter captions for 0-22s
    scene1_caps = [c for c in src_captions if c.get("start", 0) < 22]
    # Normalize start times relative to scene start (0)
    for c in scene1_caps:
        c["type"] = "caption"

    scene1 = {
        "id": "scene_" + new_id(),
        "name": "Hook — Intro",
        "duration": 23,
        "bg_color": "#0e1116",
        "audio_track": {"source": f"/audio/{pid}/audio.mp3", "offset": 0},
        "elements": scene1_caps + [
            # Title text: appears at 1s, stays until 10s
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "AGENT-READY\nCODEBASE",
                "x": 15,
                "y": 15,
                "width": 70,
                "height": 30,
                "font": "Inter",
                "size": 72,
                "color": "#4a9eff",
                "weight": "bold",
                "align": "center",
                "start": 0.5,
                "end": 10,
                "bg_color": "rgba(14,17,22,0.8)",
                "border_radius": 16,
            },
            # Subtitle text
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "How to Plan Before You Code",
                "x": 20,
                "y": 48,
                "width": 60,
                "height": 10,
                "font": "Inter",
                "size": 36,
                "color": "#FFD700",
                "weight": "normal",
                "align": "center",
                "start": 1,
                "end": 10,
            },
            # Decorative accent bar at top
            {
                "id": "el_" + new_id(),
                "type": "shape",
                "shape": "rect",
                "x": 0,
                "y": 0,
                "width": 100,
                "height": 2,
                "fill": "#4a9eff",
                "start": 0,
                "end": 93,
            },
            # Circle accent
            {
                "id": "el_" + new_id(),
                "type": "shape",
                "shape": "circle",
                "x": 85,
                "y": 5,
                "width": 8,
                "height": 8,
                "fill": "#FFD700",
                "start": 0.5,
                "end": 10,
            },
        ]
    }

    # ---- SCENE 2: Why Docs Matter (22-63s) ----
    scene2_caps = [c for c in src_captions if 22 <= c.get("start", 0) < 63]
    for c in scene2_caps:
        c["type"] = "caption"

    scene2 = {
        "id": "scene_" + new_id(),
        "name": "Why Docs Matter",
        "duration": 42,
        "bg_color": "#0e1116",
        "audio_track": {"source": f"/audio/{pid}/audio.mp3", "offset": 22},
        "elements": scene2_caps + [
            # Section title
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "WHY DOCUMENTATION MATTERS",
                "x": 10,
                "y": 5,
                "width": 80,
                "height": 10,
                "font": "Inter",
                "size": 42,
                "color": "#4a9eff",
                "weight": "bold",
                "align": "center",
                "start": 23,
                "end": 30,
            },
            # Key point 1
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "1. Humans & AI Both Read Codebases",
                "x": 10,
                "y": 20,
                "width": 80,
                "height": 8,
                "font": "Inter",
                "size": 32,
                "color": "#FFFFFF",
                "weight": "normal",
                "align": "left",
                "start": 33,
                "end": 42,
                "bg_color": "rgba(74,158,255,0.15)",
                "border_radius": 8,
            },
            # Key point 2
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "2. AI Guesses Less With Better Docs",
                "x": 10,
                "y": 32,
                "width": 80,
                "height": 8,
                "font": "Inter",
                "size": 32,
                "color": "#FFFFFF",
                "weight": "normal",
                "align": "left",
                "start": 43,
                "end": 55,
                "bg_color": "rgba(255,215,0,0.15)",
                "border_radius": 8,
            },
            # Key point 3
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "3. Agent-Ready = AI + Human Friendly",
                "x": 10,
                "y": 44,
                "width": 80,
                "height": 8,
                "font": "Inter",
                "size": 32,
                "color": "#FFFFFF",
                "weight": "normal",
                "align": "left",
                "start": 46,
                "end": 60,
                "bg_color": "rgba(76,175,80,0.15)",
                "border_radius": 8,
            },
            # Accent line
            {
                "id": "el_" + new_id(),
                "type": "shape",
                "shape": "line",
                "x": 10,
                "y": 17,
                "width": 80,
                "height": 1,
                "fill": "#4a9eff",
                "start": 23,
                "end": 63,
                "stroke_width": 3,
            },
        ]
    }

    # ---- SCENE 3: What to Create (63-93s) ----
    scene3_caps = [c for c in src_captions if c.get("start", 0) >= 63]
    for c in scene3_caps:
        c["type"] = "caption"

    scene3 = {
        "id": "scene_" + new_id(),
        "name": "What to Create",
        "duration": 32,
        "bg_color": "#0e1116",
        "audio_track": {"source": f"/audio/{pid}/audio.mp3", "offset": 63},
        "elements": scene3_caps + [
            # Section title
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "4 THINGS TO CREATE",
                "x": 15,
                "y": 5,
                "width": 70,
                "height": 10,
                "font": "Inter",
                "size": 48,
                "color": "#FFD700",
                "weight": "bold",
                "align": "center",
                "start": 64,
                "end": 70,
            },
            # Checklist items
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "1. README.md",
                "x": 15,
                "y": 22,
                "width": 70,
                "height": 7,
                "font": "Inter",
                "size": 30,
                "color": "#4caf50",
                "weight": "bold",
                "align": "left",
                "start": 70,
                "end": 77,
            },
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "2. ARCHITECTURE.md",
                "x": 15,
                "y": 31,
                "width": 70,
                "height": 7,
                "font": "Inter",
                "size": 30,
                "color": "#4caf50",
                "weight": "bold",
                "align": "left",
                "start": 70,
                "end": 80,
            },
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "3. RULES.md",
                "x": 15,
                "y": 40,
                "width": 70,
                "height": 7,
                "font": "Inter",
                "size": 30,
                "color": "#4caf50",
                "weight": "bold",
                "align": "left",
                "start": 70,
                "end": 83,
            },
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "4. PLAN.md",
                "x": 15,
                "y": 49,
                "width": 70,
                "height": 7,
                "font": "Inter",
                "size": 30,
                "color": "#4caf50",
                "weight": "bold",
                "align": "left",
                "start": 70,
                "end": 86,
            },
            # Closing CTA
            {
                "id": "el_" + new_id(),
                "type": "text",
                "content": "Start Planning. Start Building.",
                "x": 15,
                "y": 65,
                "width": 70,
                "height": 10,
                "font": "Inter",
                "size": 40,
                "color": "#4a9eff",
                "weight": "bold",
                "align": "center",
                "start": 85,
                "end": 93,
                "bg_color": "rgba(74,158,255,0.1)",
                "border_radius": 12,
            },
            # Bottom accent bar
            {
                "id": "el_" + new_id(),
                "type": "shape",
                "shape": "rect",
                "x": 0,
                "y": 98,
                "width": 100,
                "height": 2,
                "fill": "#4a9eff",
                "start": 0,
                "end": 93,
            },
        ]
    }

    # Add scenes in order
    ps.add_scene(pid, scene1)
    ps.add_scene(pid, scene2)
    ps.add_scene(pid, scene3)

    # Verify
    scenes = ps.list_scenes(pid)
    total_elements = sum(len(s.get("elements", [])) for s in scenes)
    print(f"\nDemo project created: {pid}")
    print(f"Name: Agent-Ready Codebase - Demo")
    print(f"Scenes: {len(scenes)}")
    for s in scenes:
        print(f"  {s['name']}: {len(s.get('elements', []))} elements, duration={s['duration']}s")
    print(f"Total elements: {total_elements}")
    print(f"Audio source: {audio_track}")
    print(f"\nOpen http://127.0.0.1:8768 and load project '{pid}' to see it.")


if __name__ == "__main__":
    main()
