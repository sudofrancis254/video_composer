#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_demo_v2.py
==================
Rich demo project with animated text, custom backgrounds,
grid patterns, and themed elements.
"""

import os
import sys
import json
import time
import uuid
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

SRC_PID = "d0e217336789"

def new_id():
    return uuid.uuid4().hex[:12]

def el_id():
    return "el_" + new_id()

def main():
    # Read source captions
    src_scenes = ps.list_scenes(SRC_PID)
    src_captions = src_scenes[0].get("elements", [])
    duration = src_scenes[0].get("duration", 93)
    src_meta = ps._read_json(os.path.join(ps.project_dir(SRC_PID), "meta.json")) or {}
    audio_src = src_meta.get("audio_source", "")

    print(f"Source: {len(src_captions)} captions, duration={duration}s, audio={audio_src[:40]}")

    # Create project
    proj = ps.create_project("Agent-Ready Codebase — Rich Demo", 1920, 1080)
    pid = proj["id"]

    # Copy audio
    src_audio = os.path.join(ps.fast_dir(SRC_PID), "source.mp3")
    dst_audio = os.path.join(ps.fast_dir(pid), "audio.mp3")
    if os.path.isfile(src_audio):
        shutil.copy2(src_audio, dst_audio)
        print(f"Copied audio -> {dst_audio}")

    # ==============================
    # SCENE 1: Hook (0-22s)
    # Grid background, big animated title, captions
    # ==============================
    caps1 = [dict(c, type="caption") for c in src_captions if c.get("start", 0) < 22]

    scene1 = {
        "id": "scene_" + new_id(),
        "name": "Hook — Opening",
        "duration": 23,
        "bg_color": "#0a0e14",
        "bg_pattern": "bg-grid",
        "audio_track": {"source": dst_audio, "duration": duration},
        "elements": caps1 + [
            # === Decorative accent bar at top ===
            {"id": el_id(), "type": "shape", "shape": "rect",
             "x": 0, "y": 0, "width": 100, "height": 1.5,
             "fill": "#4a9eff", "start": 0, "end": 93},

            # === Floating dot top-right ===
            {"id": el_id(), "type": "shape", "shape": "circle",
             "x": 88, "y": 4, "width": 6, "height": 6,
             "fill": "rgba(74,158,255,0.3)", "start": 0.5, "end": 10,
             "animation": {"type": "fade-in", "duration": 0.6}},

            # === Title: "AGENT-READY" — slides in from left ===
            {"id": el_id(), "type": "text",
             "content": "AGENT-READY",
             "x": 10, "y": 12, "width": 80, "height": 12,
             "font": "Inter", "size": 80, "color": "#4a9eff",
             "weight": "bold", "align": "center",
             "start": 0.8, "end": 11,
             "bg_color": "rgba(10,14,20,0.85)",
             "border_radius": 16,
             "animation": {"type": "slide-left", "duration": 0.7}},

            # === Title: "CODEBASE" — slides in from right ===
            {"id": el_id(), "type": "text",
             "content": "CODEBASE",
             "x": 10, "y": 26, "width": 80, "height": 12,
             "font": "Inter", "size": 80, "color": "#FFFFFF",
             "weight": "bold", "align": "center",
             "start": 1.2, "end": 11,
             "bg_color": "rgba(10,14,20,0.85)",
             "border_radius": 16,
             "animation": {"type": "slide-right", "duration": 0.7}},

            # === Subtitle — zoom in ===
            {"id": el_id(), "type": "text",
             "content": "How to Plan Before You Write a Single Line",
             "x": 15, "y": 42, "width": 70, "height": 8,
             "font": "Inter", "size": 32, "color": "#FFD700",
             "weight": "normal", "align": "center",
             "start": 2, "end": 11,
             "animation": {"type": "zoom-in", "duration": 0.5}},

            # === Accent line under subtitle ===
            {"id": el_id(), "type": "shape", "shape": "line",
             "x": 25, "y": 52, "width": 50, "height": 1,
             "fill": "#4a9eff", "stroke_width": 3,
             "start": 2.5, "end": 11,
             "animation": {"type": "fade-in", "duration": 0.4}},

            # === Decorative bottom bar ===
            {"id": el_id(), "type": "shape", "shape": "rect",
             "x": 0, "y": 98, "width": 100, "height": 2,
             "fill": "#4a9eff", "start": 0, "end": 93},
        ]
    }

    # ==============================
    # SCENE 2: Why Docs Matter (22-63s)
    # Dots background, key points appear one by one
    # ==============================
    caps2 = [dict(c, type="caption") for c in src_captions if 22 <= c.get("start", 0) < 63]

    scene2 = {
        "id": "scene_" + new_id(),
        "name": "Why Docs Matter",
        "duration": 42,
        "bg_color": "#0e1116",
        "bg_pattern": "bg-dots",
        "audio_track": {"source": dst_audio, "duration": duration},
        "elements": caps2 + [
            # === Section header — bounce in ===
            {"id": el_id(), "type": "text",
             "content": "WHY DOCUMENTATION MATTERS",
             "x": 8, "y": 4, "width": 84, "height": 10,
             "font": "Inter", "size": 44, "color": "#4a9eff",
             "weight": "bold", "align": "center",
             "start": 23, "end": 32,
             "bg_color": "rgba(74,158,255,0.08)",
             "border_radius": 12,
             "animation": {"type": "bounce", "duration": 0.8}},

            # === Horizontal divider ===
            {"id": el_id(), "type": "shape", "shape": "line",
             "x": 8, "y": 16, "width": 84, "height": 1,
             "fill": "rgba(74,158,255,0.4)", "stroke_width": 2,
             "start": 23.5, "end": 63},

            # === Point 1: Humans & AI ===
            {"id": el_id(), "type": "text",
             "content": "1",
             "x": 8, "y": 20, "width": 8, "height": 8,
             "font": "Inter", "size": 48, "color": "#4a9eff",
             "weight": "bold", "align": "center",
             "start": 33, "end": 42,
             "bg_color": "rgba(74,158,255,0.15)",
             "border_radius": 50,
             "animation": {"type": "zoom-in", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "Humans & AI\nBoth Read Codebases",
             "x": 18, "y": 20, "width": 74, "height": 8,
             "font": "Inter", "size": 30, "color": "#FFFFFF",
             "weight": "600", "align": "left",
             "start": 33.3, "end": 42,
             "bg_color": "rgba(74,158,255,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-left", "duration": 0.5}},

            # === Point 2: AI Guesses Less ===
            {"id": el_id(), "type": "text",
             "content": "2",
             "x": 8, "y": 33, "width": 8, "height": 8,
             "font": "Inter", "size": 48, "color": "#FFD700",
             "weight": "bold", "align": "center",
             "start": 43, "end": 55,
             "bg_color": "rgba(255,215,0,0.15)",
             "border_radius": 50,
             "animation": {"type": "zoom-in", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "AI Guesses Less\nWith Better Docs",
             "x": 18, "y": 33, "width": 74, "height": 8,
             "font": "Inter", "size": 30, "color": "#FFFFFF",
             "weight": "600", "align": "left",
             "start": 43.3, "end": 55,
             "bg_color": "rgba(255,215,0,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-left", "duration": 0.5}},

            # === Point 3: Agent-Ready ===
            {"id": el_id(), "type": "text",
             "content": "3",
             "x": 8, "y": 46, "width": 8, "height": 8,
             "font": "Inter", "size": 48, "color": "#4caf50",
             "weight": "bold", "align": "center",
             "start": 46, "end": 60,
             "bg_color": "rgba(76,175,80,0.15)",
             "border_radius": 50,
             "animation": {"type": "zoom-in", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "Agent-Ready =\nAI + Human Friendly",
             "x": 18, "y": 46, "width": 74, "height": 8,
             "font": "Inter", "size": 30, "color": "#FFFFFF",
             "weight": "600", "align": "left",
             "start": 46.3, "end": 60,
             "bg_color": "rgba(76,175,80,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-left", "duration": 0.5}},

            # === Decorative accent shapes ===
            {"id": el_id(), "type": "shape", "shape": "circle",
             "x": 90, "y": 10, "width": 4, "height": 4,
             "fill": "rgba(255,215,0,0.2)",
             "start": 23, "end": 63},
            {"id": el_id(), "type": "shape", "shape": "circle",
             "x": 2, "y": 60, "width": 3, "height": 3,
             "fill": "rgba(74,158,255,0.2)",
             "start": 25, "end": 63},
        ]
    }

    # ==============================
    # SCENE 3: What to Create (63-93s)
    # Math-book background, checklist items appear sequentially
    # ==============================
    caps3 = [dict(c, type="caption") for c in src_captions if c.get("start", 0) >= 63]

    scene3 = {
        "id": "scene_" + new_id(),
        "name": "What to Create",
        "duration": 32,
        "bg_color": "#0e1116",
        "bg_pattern": "bg-math",
        "audio_track": {"source": dst_audio, "duration": duration},
        "elements": caps3 + [
            # === Big number "4" in background ===
            {"id": el_id(), "type": "text",
             "content": "4",
             "x": 35, "y": -5, "width": 30, "height": 50,
             "font": "Inter", "size": 200, "color": "rgba(74,158,255,0.06)",
             "weight": "bold", "align": "center",
             "start": 63, "end": 93},

            # === Section header — elastic ===
            {"id": el_id(), "type": "text",
             "content": "4 FILES TO CREATE",
             "x": 10, "y": 5, "width": 80, "height": 10,
             "font": "Inter", "size": 48, "color": "#FFD700",
             "weight": "bold", "align": "center",
             "start": 64, "end": 72,
             "bg_color": "rgba(255,215,0,0.1)",
             "border_radius": 12,
             "animation": {"type": "elastic", "duration": 0.8}},

            # === Checkmark + README.md ===
            {"id": el_id(), "type": "text",
             "content": "README.md",
             "x": 18, "y": 22, "width": 65, "height": 7,
             "font": "JetBrains Mono", "size": 28, "color": "#4caf50",
             "weight": "600", "align": "left",
             "start": 70, "end": 78,
             "bg_color": "rgba(76,175,80,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-right", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "✓",
             "x": 10, "y": 22, "width": 7, "height": 7,
             "font": "Inter", "size": 36, "color": "#4caf50",
             "weight": "bold", "align": "center",
             "start": 70, "end": 78,
             "animation": {"type": "zoom-in", "duration": 0.3}},

            # === Checkmark + ARCHITECTURE.md ===
            {"id": el_id(), "type": "text",
             "content": "ARCHITECTURE.md",
             "x": 18, "y": 31, "width": 65, "height": 7,
             "font": "JetBrains Mono", "size": 28, "color": "#4a9eff",
             "weight": "600", "align": "left",
             "start": 72, "end": 81,
             "bg_color": "rgba(74,158,255,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-right", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "✓",
             "x": 10, "y": 31, "width": 7, "height": 7,
             "font": "Inter", "size": 36, "color": "#4a9eff",
             "weight": "bold", "align": "center",
             "start": 72, "end": 81,
             "animation": {"type": "zoom-in", "duration": 0.3}},

            # === Checkmark + RULES.md ===
            {"id": el_id(), "type": "text",
             "content": "RULES.md",
             "x": 18, "y": 40, "width": 65, "height": 7,
             "font": "JetBrains Mono", "size": 28, "color": "#ff9800",
             "weight": "600", "align": "left",
             "start": 74, "end": 84,
             "bg_color": "rgba(255,152,0,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-right", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "✓",
             "x": 10, "y": 40, "width": 7, "height": 7,
             "font": "Inter", "size": 36, "color": "#ff9800",
             "weight": "bold", "align": "center",
             "start": 74, "end": 84,
             "animation": {"type": "zoom-in", "duration": 0.3}},

            # === Checkmark + PLAN.md ===
            {"id": el_id(), "type": "text",
             "content": "PLAN.md",
             "x": 18, "y": 49, "width": 65, "height": 7,
             "font": "JetBrains Mono", "size": 28, "color": "#9c27b0",
             "weight": "600", "align": "left",
             "start": 76, "end": 87,
             "bg_color": "rgba(156,39,176,0.08)",
             "border_radius": 8,
             "animation": {"type": "slide-right", "duration": 0.4}},
            {"id": el_id(), "type": "text",
             "content": "✓",
             "x": 10, "y": 49, "width": 7, "height": 7,
             "font": "Inter", "size": 36, "color": "#9c27b0",
             "weight": "bold", "align": "center",
             "start": 76, "end": 87,
             "animation": {"type": "zoom-in", "duration": 0.3}},

            # === CTA at end ===
            {"id": el_id(), "type": "text",
             "content": "Start Planning.\nStart Building.",
             "x": 15, "y": 62, "width": 70, "height": 12,
             "font": "Inter", "size": 42, "color": "#4a9eff",
             "weight": "bold", "align": "center",
             "start": 85, "end": 93,
             "bg_color": "rgba(74,158,255,0.1)",
             "border_radius": 16,
             "animation": {"type": "elastic", "duration": 0.8}},

            # === Bottom accent bar ===
            {"id": el_id(), "type": "shape", "shape": "rect",
             "x": 0, "y": 98, "width": 100, "height": 2,
             "fill": "#4a9eff", "start": 0, "end": 93},
        ]
    }

    # Add all scenes
    ps.add_scene(pid, scene1)
    ps.add_scene(pid, scene2)
    ps.add_scene(pid, scene3)

    # Verify
    scenes = ps.list_scenes(pid)
    total_elements = sum(len(s.get("elements", [])) for s in scenes)
    print(f"\nRich demo project created: {pid}")
    print(f"Name: Agent-Ready Codebase — Rich Demo")
    print(f"Scenes: {len(scenes)}")
    for s in scenes:
        anims = sum(1 for e in s.get("elements", []) if e.get("animation"))
        print(f"  {s['name']}: {len(s.get('elements', []))} elements ({anims} animated), bg={s.get('bg_pattern','solid')}, duration={s['duration']}s")
    print(f"Total elements: {total_elements}")
    print(f"\nOpen http://127.0.0.1:8768 and load project '{pid}'")


if __name__ == "__main__":
    main()
