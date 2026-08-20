#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_service.py
=================
Import audio, transcripts, and captions from Word Editor and Caption Studio
into Video Composer projects.
"""

import os
import json
import shutil
import time
import sys

# Add parent dir so we can import project_store
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

# Word Editor paths
WE_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WE_PROJECTS = os.path.join(WE_BASE, "word_editor", "projects")

# Caption Studio paths
CS_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CS_PROJECTS = os.path.join(CS_BASE, "caption_editor", "projects")


def list_word_editor_projects() -> list[dict]:
    """List all Word Editor projects with metadata."""
    projects = []
    if not os.path.isdir(WE_PROJECTS):
        return projects
    for pid in sorted(os.listdir(WE_PROJECTS)):
        pdir = os.path.join(WE_PROJECTS, pid)
        if not os.path.isdir(pdir):
            continue
        meta = _read_json(os.path.join(pdir, "meta.json"))
        if not meta:
            continue
        # Check for audio files
        audio_path = _find_audio(pdir, pid)
        words_path = os.path.join(pdir, "words.json")
        has_words = os.path.isfile(words_path)
        has_audio = audio_path is not None

        # Get duration from meta or words
        duration = meta.get("duration", 0)
        if not duration and has_words:
            words = _read_json(words_path) or []
            if words:
                duration = max(w.get("end", 0) for w in words)

        projects.append({
            "id": pid,
            "name": meta.get("name", pid),
            "source": meta.get("source", "unknown"),
            "voice": meta.get("voice", ""),
            "duration": round(duration, 1),
            "word_count": meta.get("word_count", 0),
            "has_audio": has_audio,
            "has_words": has_words,
            "audio_path": audio_path,
        })
    return projects


def list_caption_editor_projects() -> list[dict]:
    """List Caption Studio projects."""
    projects = []
    if not os.path.isdir(CS_PROJECTS):
        return projects
    for pid in sorted(os.listdir(CS_PROJECTS)):
        pdir = os.path.join(CS_PROJECTS, pid)
        if not os.path.isdir(pdir):
            continue
        meta = _read_json(os.path.join(pdir, "meta.json")) or {}
        state = _read_json(os.path.join(pdir, "state.json")) or {}
        blocks = state.get("blocks", [])
        projects.append({
            "id": pid,
            "name": meta.get("name", pid),
            "audio_source": meta.get("audio_source", ""),
            "block_count": len(blocks),
        })
    return projects


def import_from_word_editor(
    we_pid: str, vc_pid: str, project_name: str = ""
) -> dict:
    """
    Import audio + word timestamps from a Word Editor project
    into a Video Composer project. Creates the first scene with
    an auto-generated caption element.

    Returns the created scene dict.
    """
    we_pdir = os.path.join(WE_PROJECTS, we_pid)
    if not os.path.isdir(we_pdir):
        return {"error": f"Word Editor project not found: {we_pid}"}

    # Read source data
    meta = _read_json(os.path.join(we_pdir, "meta.json")) or {}
    words = _read_json(os.path.join(we_pdir, "words.json")) or []

    # Find audio
    audio_path = _find_audio(we_pdir, we_pid)
    if not audio_path:
        return {"error": "No audio file found in Word Editor project"}

    # Copy audio to Video Composer fast-dir
    vc_fast = ps.fast_dir(vc_pid)
    audio_dest = os.path.join(vc_fast, "source.mp3")
    if not os.path.isfile(audio_dest):
        shutil.copy2(audio_path, audio_dest)

    # Copy words.json
    words_dest = os.path.join(ps.project_dir(vc_pid), "words.json")
    if words and not os.path.isfile(words_dest):
        ps._write_json(words_dest, words)

    # Get duration
    duration = meta.get("duration", 0)
    if not duration and words:
        duration = max(w.get("end", 0) for w in words)
    duration = round(duration, 1)

    # Build caption elements from word groups
    captions = _build_caption_elements(words, duration)

    # Create scene
    scene = {
        "name": project_name or meta.get("name", "Imported"),
        "duration": duration,
        "bg_color": "#0e1116",
        "elements": captions,
        "audio_track": {
            "source": audio_dest,
            "words_json": words_dest if os.path.isfile(words_dest) else None,
            "duration": duration,
        },
        "source_project": we_pid,
        "source_name": meta.get("name", we_pid),
    }

    # Update project metadata
    ps.update_project(vc_pid, {
        "audio_source": we_pid,
        "source_name": meta.get("name", we_pid),
        "voice": meta.get("voice", ""),
    })

    return scene


def import_captions_from_caption_editor(
    cs_pid: str, vc_pid: str, scene_id: str = None
) -> dict:
    """
    Import styled captions from Caption Studio into an existing scene.
    Merges caption styles (font, color, animation) from the Caption Studio
    project into the Video Composer scene's caption elements.
    """
    cs_pdir = os.path.join(CS_PROJECTS, cs_pid)
    if not os.path.isdir(cs_pdir):
        return {"error": f"Caption Studio project not found: {cs_pid}"}

    state = _read_json(os.path.join(cs_pdir, "state.json")) or {}
    blocks = state.get("blocks", [])
    preset = state.get("preset", {})

    if not blocks:
        return {"error": "No caption blocks found in Caption Studio project"}

    # Get or find the scene
    scenes = ps.list_scenes(vc_pid)
    if scene_id:
        scene = ps.get_scene(vc_pid, scene_id)
    else:
        scene = scenes[0] if scenes else None

    if not scene:
        return {"error": "No scene found in Video Composer project"}

    # Merge caption styles into scene
    style = {
        "font": preset.get("font", "Inter"),
        "size": preset.get("size", 46),
        "color": preset.get("text", "#FFFFFF"),
        "highlight": preset.get("highlight", "#FFD700"),
        "bg_color": preset.get("bg", "rgba(0,0,0,0.7)"),
        "border_radius": preset.get("radius", 12),
        "animation": preset.get("word_effect", "none"),
        "box_style": preset.get("box_style", "pill"),
    }

    # Update scene's caption elements with the imported styles
    elements = scene.get("elements", [])
    for el in elements:
        if el.get("type") == "caption":
            el["style"] = style
            el["source_blocks"] = blocks  # keep original block data

    ps.update_scene(vc_pid, scene["id"], {"elements": elements})

    return {"scene_id": scene["id"], "style": style, "block_count": len(blocks)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_audio(project_dir: str, pid: str) -> str | None:
    """Find the best audio file in a Word Editor project."""
    # Check FAST_DIR first
    fast_audio = os.path.join(ps.WORD_EDITOR_FAST_DIR, pid, "audio.wav")
    if os.path.isfile(fast_audio):
        return fast_audio

    # Check export files
    for ext in [".mp3", ".wav", ".ogg", ".m4a"]:
        export = os.path.join(project_dir, f"export{ext}")
        if os.path.isfile(export):
            return export

    # Check source
    for ext in [".mp3", ".wav", ".ogg", ".m4a"]:
        source = os.path.join(project_dir, f"source{ext}")
        if os.path.isfile(source):
            return source

    # Check FAST_DIR for source
    fast_source = os.path.join(ps.WORD_EDITOR_FAST_DIR, pid, "source.mp3")
    if os.path.isfile(fast_source):
        return fast_source

    return None


def _build_caption_elements(words: list[dict], duration: float) -> list[dict]:
    """
    Build caption elements from word-level timestamps.
    Groups words into lines of ~5-8 words each, split at natural
    pause points (gaps > 0.5s between words).
    """
    if not words:
        return []

    elements = []
    current_group = []
    group_start = None

    for w in words:
        text = w.get("text", "").strip()
        if not text:
            continue
        start = w.get("start", 0)
        end = w.get("end", 0)

        if group_start is None:
            group_start = start

        current_group.append(w)

        # Check for natural break: gap > 0.5s or ~6 words accumulated
        next_start = None
        idx = words.index(w)
        if idx + 1 < len(words):
            next_start = words[idx + 1].get("start", 0)

        gap = (next_start - end) if next_start else 999
        is_natural_break = gap > 0.5
        is_full = len(current_group) >= 6

        if is_natural_break or is_full:
            text_content = " ".join(cw.get("text", "") for cw in current_group)
            elements.append({
                "id": "el_" + ps._new_id(),
                "type": "caption",
                "content": text_content,
                "x": 5,  # percent
                "y": 80,  # percent — near bottom
                "width": 90,
                "height": 15,
                "start": round(group_start, 3),
                "end": round(end + 0.1, 3),
                "words": [
                    {
                        "text": cw.get("text", ""),
                        "start": round(cw.get("start", 0), 3),
                        "end": round(cw.get("end", 0), 3),
                    }
                    for cw in current_group
                ],
                "style": {
                    "font": "Inter",
                    "size": 46,
                    "color": "#FFFFFF",
                    "highlight": "#FFD700",
                    "bg_color": "rgba(0,0,0,0.7)",
                    "border_radius": 12,
                    "align": "center",
                },
            })
            current_group = []
            group_start = None

    # Flush remaining words
    if current_group:
        text_content = " ".join(cw.get("text", "") for cw in current_group)
        elements.append({
            "id": "el_" + ps._new_id(),
            "type": "caption",
            "content": text_content,
            "x": 5,
            "y": 80,
            "width": 90,
            "height": 15,
            "start": round(group_start or 0, 3),
            "end": round(current_group[-1].get("end", 0) + 0.1, 3),
            "words": [
                {
                    "text": cw.get("text", ""),
                    "start": round(cw.get("start", 0), 3),
                    "end": round(cw.get("end", 0), 3),
                }
                for cw in current_group
            ],
            "style": {
                "font": "Inter",
                "size": 46,
                "color": "#FFFFFF",
                "highlight": "#FFD700",
                "bg_color": "rgba(0,0,0,0.7)",
                "border_radius": 12,
                "align": "center",
            },
        })

    return elements


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
