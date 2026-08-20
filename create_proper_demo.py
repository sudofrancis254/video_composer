#!/usr/bin/env python3
"""
Create a proper multi-scene demo project for the Video Composer.
Uses word-level timestamps from words.json to create scenes with
timed visual elements (titles, shapes, accent lines) + captions.
"""
import os
import sys
import json
import shutil
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps

PID = "cd7824dc202a"
PROJECT_DIR = ps.project_dir(PID)
META_PATH = os.path.join(PROJECT_DIR, "meta.json")
WORDS_PATH = os.path.join(PROJECT_DIR, "words.json")
SCENES_PATH = os.path.join(PROJECT_DIR, "scenes.json")

def new_id():
    return uuid.uuid4().hex[:12]

def load_words():
    with open(WORDS_PATH, encoding="utf-8") as f:
        return json.load(f)

def get_audio_info():
    """Find audio source from the fast_dir or meta."""
    fast = ps.fast_dir(PID)
    for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a"]:
        import glob
        matches = glob.glob(os.path.join(fast, ext))
        if matches:
            return matches[0]
    return None

def build_captions(words, scene_start, scene_end):
    """Build caption elements from words within a scene time range."""
    captions = []
    # Filter words in this scene's time range
    scene_words = [w for w in words if w.get("start", 0) >= scene_start - 0.01 and w.get("end", 0) <= scene_end + 0.1]
    
    group = []
    group_start = None
    
    for w in scene_words:
        text = w.get("text", "").strip()
        if not text:
            continue
        start = w.get("start", 0)
        end = w.get("end", 0)
        
        if group_start is None:
            group_start = start
        group.append(w)
        
        # Check for break
        idx = scene_words.index(w)
        next_start = scene_words[idx + 1].get("start", 0) if idx + 1 < len(scene_words) else None
        gap = (next_start - end) if next_start else 999
        
        if gap > 0.4 or len(group) >= 5:
            text_content = " ".join(cw.get("text", "") for cw in group)
            local_start = round(group_start - scene_start, 3)
            local_end = round(end - scene_start + 0.1, 3)
            captions.append({
                "id": "el_" + new_id(),
                "type": "caption",
                "content": text_content,
                "x": 5, "y": 82, "width": 90, "height": 14,
                "start": local_start,
                "end": local_end,
                "words": [
                    {"text": cw.get("text", ""),
                     "start": round(cw.get("start", 0) - scene_start, 3),
                     "end": round(cw.get("end", 0) - scene_start, 3)}
                    for cw in group
                ],
                "style": {
                    "font": "Inter", "size": 42, "color": "#FFFFFF",
                    "highlight": "#FFD700",
                    "bg_color": "rgba(0,0,0,0.75)",
                    "border_radius": 12, "align": "center",
                },
            })
            group = []
            group_start = None
    
    # Flush remaining
    if group:
        text_content = " ".join(cw.get("text", "") for cw in group)
        captions.append({
            "id": "el_" + new_id(),
            "type": "caption",
            "content": text_content,
            "x": 5, "y": 82, "width": 90, "height": 14,
            "start": round((group_start or scene_start) - scene_start, 3),
            "end": round(group[-1].get("end", 0) - scene_start + 0.1, 3),
            "words": [
                {"text": cw.get("text", ""),
                 "start": round(cw.get("start", 0) - scene_start, 3),
                 "end": round(cw.get("end", 0) - scene_start, 3)}
                for cw in group
            ],
            "style": {
                "font": "Inter", "size": 42, "color": "#FFFFFF",
                "highlight": "#FFD700",
                "bg_color": "rgba(0,0,0,0.75)",
                "border_radius": 12, "align": "center",
            },
        })
    
    return captions

def build_visuals(words, scene_start, scene_end, scene_idx, total_scenes):
    """Build visual elements for a scene — text titles, accent shapes, decorative elements."""
    visuals = []
    dur = round(scene_end - scene_start + 0.3, 1)
    scene_words = [w for w in words if w.get("start", 0) >= scene_start - 0.01 and w.get("end", 0) <= scene_end + 0.1]
    
    if not scene_words:
        return visuals
    
    # === Big title text — appears in first 5 seconds ===
    # Use first 3-4 words as a title
    title_words = [w.get("text", "") for w in scene_words[:4] if w.get("text", "").strip()]
    title_text = " ".join(title_words).upper()
    first_w_start = scene_words[0].get("start", scene_start) - scene_start
    title_end = min(dur, 6)
    
    if scene_idx == 0:
        # Hook scene: big animated title
        visuals.append({
            "id": "el_" + new_id(),
            "type": "text",
            "content": "AGENT-READY CODEBASE",
            "x": 10, "y": 25, "width": 80, "height": 15,
            "font": "Inter", "size": 80, "color": "#4a9eff",
            "weight": "bold", "align": "center",
            "start": round(first_w_start + 0.2, 3),
            "end": round(min(dur, 8), 3),
            "animation": {"type": "slide-right", "duration": 0.8},
        })
        # Subtitle
        visuals.append({
            "id": "el_" + new_id(),
            "type": "text",
            "content": "A Deep Dive into System Architecture",
            "x": 15, "y": 42, "width": 70, "height": 8,
            "font": "Inter", "size": 36, "color": "#8b93a1",
            "weight": "normal", "align": "center",
            "start": round(first_w_start + 1.0, 3),
            "end": round(min(dur, 7), 3),
            "animation": {"type": "fade-in", "duration": 0.6},
        })
    else:
        # Content scenes: section title
        visuals.append({
            "id": "el_" + new_id(),
            "type": "text",
            "content": title_text,
            "x": 8, "y": 6, "width": 84, "height": 10,
            "font": "Inter", "size": 52, "color": "#4a9eff",
            "weight": "bold", "align": "left",
            "start": round(first_w_start, 3),
            "end": round(min(dur, 5), 3),
            "bg_color": "rgba(74,158,255,0.08)",
            "border_radius": 8,
            "animation": {"type": "slide-down", "duration": 0.5},
        })
    
    # === Accent line under title ===
    visuals.append({
        "id": "el_" + new_id(),
        "type": "shape", "shape": "line",
        "x": 8, "y": 18, "width": 84, "height": 1,
        "fill": "#4a9eff55", "stroke_width": 3,
        "start": round(first_w_start + 0.3, 3),
        "end": round(dur, 3),
        "animation": {"type": "fade-in", "duration": 0.3},
    })
    
    # === Key number/icon for middle scenes ===
    if 0 < scene_idx < total_scenes - 1:
        # Big scene number in background
        scene_num = str(scene_idx)
        visuals.append({
            "id": "el_" + new_id(),
            "type": "text",
            "content": scene_num,
            "x": 75, "y": 10, "width": 20, "height": 25,
            "font": "Inter", "size": 160, "color": "rgba(74,158,255,0.08)",
            "weight": "bold", "align": "center",
            "start": 0, "end": round(dur, 3),
        })
    
    # === Decorative circles — appear at emphasis points ===
    emphasis_indices = []
    for i, w in enumerate(scene_words):
        if i > 0:
            gap = w.get("start", 0) - scene_words[i-1].get("end", 0)
            if gap > 0.6:
                emphasis_indices.append(i)
        if len(w.get("text", "")) > 6 and len(emphasis_indices) < 3:
            if i % 6 == 0:
                emphasis_indices.append(i)
    
    positions = [(82, 8, 6), (5, 70, 4), (88, 65, 5)]
    for idx, word_idx in enumerate(emphasis_indices[:3]):
        if word_idx >= len(scene_words):
            continue
        w = scene_words[word_idx]
        el_start = w.get("start", 0) - scene_start
        px, py, ps_size = positions[idx % 3]
        visuals.append({
            "id": "el_" + new_id(),
            "type": "shape", "shape": "circle",
            "x": px, "y": py, "width": ps_size, "height": ps_size,
            "fill": "#4a9eff18",
            "start": round(el_start, 3),
            "end": round(dur, 3),
            "animation": {"type": "zoom-in", "duration": 0.5},
        })
    
    # === Bottom accent bar ===
    visuals.append({
        "id": "el_" + new_id(),
        "type": "shape", "shape": "rect",
        "x": 0, "y": 97, "width": 100, "height": 3,
        "fill": "#4a9eff",
        "start": 0, "end": round(dur, 3),
    })
    
    return visuals

def main():
    words = load_words()
    if not words:
        print("ERROR: No words.json found")
        sys.exit(1)
    
    audio_path = get_audio_info()
    total_audio_dur = words[-1].get("end", 0) if words else 60
    
    print(f"Words: {len(words)}, Audio: {total_audio_dur:.1f}s")
    print(f"Audio path: {audio_path}")
    
    # Audio track shared by all scenes
    audio_track = None
    if audio_path:
        audio_track = {
            "source": audio_path,
            "duration": total_audio_dur,
        }
    
    # === Split into scenes at natural pauses ===
    # Find good split points (gaps > 0.7s)
    split_points = [0.0]
    for i in range(len(words) - 1):
        gap = words[i + 1].get("start", 0) - words[i].get("end", 0)
        if gap > 0.7:
            # Only split if we haven't split in the last 5 seconds
            last_split = split_points[-1]
            if words[i].get("end", 0) - last_split > 5:
                split_points.append(words[i].get("end", 0) + 0.1)
    
    # Ensure we don't have too many or too few scenes
    # Target: 8-12 scenes for a 90-second video
    if len(split_points) < 6:
        # Force more splits based on word count
        words_per_scene = len(words) // 10
        split_points = [0.0]
        for i in range(words_per_scene, len(words), words_per_scene):
            if i < len(words):
                split_points.append(words[i].get("start", 0))
    
    split_points.append(total_audio_dur + 1)  # sentinel
    # Remove duplicates and sort
    split_points = sorted(set(split_points))
    
    print(f"Scenes to create: {len(split_points) - 1}")
    
    # === Delete existing scenes ===
    for s in ps.list_scenes(PID):
        ps.delete_scene(PID, s["id"])
    
    # === Build scenes ===
    all_scenes = []
    for i in range(len(split_points) - 1):
        scene_start = split_points[i]
        scene_end = split_points[i + 1]
        if scene_end > total_audio_dur + 1:
            scene_end = total_audio_dur + 0.5
        dur = round(scene_end - scene_start, 1)
        
        if dur < 2:
            continue  # skip very short scenes
        
        # Get scene name from first words
        scene_words = [w for w in words if w.get("start", 0) >= scene_start - 0.01 and w.get("start", 0) <= scene_end + 0.1]
        name_words = [w.get("text", "") for w in scene_words[:3] if w.get("text", "").strip()]
        if i == 0:
            name = f"Opening — {' '.join(name_words)}..."
        elif i == len(split_points) - 2:
            name = f"Closing — {' '.join(name_words)}..."
        else:
            name = f"Scene {i} — {' '.join(name_words)}..."
        
        bg_color = "#0a0e14"
        bg_pattern = "bg-grid" if i % 2 == 0 else "bg-dots"
        
        captions = build_captions(words, scene_start, scene_end)
        visuals = build_visuals(words, scene_start, scene_end, i, len(split_points) - 1)
        
        scene = {
            "id": "scene_" + new_id(),
            "name": name,
            "duration": dur,
            "bg_color": bg_color,
            "bg_pattern": bg_pattern,
            "audio_track": audio_track,
            "elements": captions + visuals,
        }
        
        ps.add_scene(PID, scene)
        all_scenes.append(scene)
        print(f"  {name}: {dur}s, {len(captions)} captions, {len(visuals)} visuals")
    
    print(f"\nTotal: {len(all_scenes)} scenes, {sum(len(s['elements']) for s in all_scenes)} elements")
    print("Done! Restart the server and reload.")

if __name__ == "__main__":
    main()
