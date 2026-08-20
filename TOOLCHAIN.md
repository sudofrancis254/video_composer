---
name: video-composer-toolchain
version: 1.0.0
created: 2026-08-18
status: PLANNING
---

# Video Composer — Toolchain Integration

## The Complete Pipeline

This is how every tool connects, from raw idea to finished video.

```
┌─────────────────────────────────────────────────────────────┐
│                    THE VIDEO PIPELINE                        │
│                                                             │
│  ┌─────────────┐                                            │
│  │   SCRIPT    │  ← Script Workflow Skill                   │
│  │  (v3.2.md)  │     (research → draft → pacing → polish)  │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                            │
│  │ WORD EDITOR │  ← TTS / Transcribe                        │
│  │ (port 8765) │     (edge-tts → word-level timestamps)     │
│  │             │     (silence removal, effects, speed)       │
│  │  Audio +    │     (export: mp3 + srt + vtt + words.json) │
│  │  Transcript │                                            │
│  └──────┬──────┘                                            │
│         │                                                   │
│         ├──────────────────┐                                 │
│         ▼                  ▼                                 │
│  ┌─────────────┐  ┌────────────────┐                        │
│  │   CAPTION   │  │ VIDEO COMPOSER │  ← NEW                 │
│  │   STUDIO    │  │ (port 8770)    │                        │
│  │ (port 8766) │  │                │                        │
│  │             │  │ Scene editing, │                        │
│  │ Style       │  │ timeline,      │                        │
│  │ captions,   │──│ animations,    │                        │
│  │ bake to MP4 │  │ render to MP4  │                        │
│  └─────────────┘  └───────┬────────┘                        │
│                           │                                  │
│                           ▼                                  │
│                  ┌────────────────┐                           │
│                  │ FINAL VIDEO    │                           │
│                  │ (MP4, 1080p)   │                           │
│                  └────────────────┘                           │
│                                                              │
│  ┌─────────────┐                                             │
│  │   IMAGE     │  ← Annotations, thumbnails, overlays        │
│  │   EDITOR    │     (bg remove, contour, badges)            │
│  │ (port 8767) │     (generates assets for scenes)           │
│  └─────────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

## Tool Responsibilities

### Word Editor (port 8765)
**Input:** Raw text or audio file
**Output:** Audio + word-level transcript + SRT/VTT + metadata

Key exports that flow downstream:
| File | Format | Used By |
|------|--------|---------|
| `export.mp3` / `export.wav` | Audio | Video Composer (scene audio track) |
| `words.json` | Word-level timestamps | Video Composer (caption sync) |
| `*.srt` | Subtitle file | Caption Studio, Video Composer |
| `*.vtt` | WebVTT subtitle | Video Composer (HTML5 player format) |
| `*_transcript.txt` | Plain text | Script reference |
| `meta.json` | Project metadata | All tools (name, voice, duration) |

### Caption Studio (port 8766)
**Input:** Video + transcript from Word Editor
**Output:** Styled captions + baked MP4 + caption presets

Key exports:
| File | Format | Used By |
|------|--------|---------|
| `export.mp4` | Video with baked captions | Reference / final output |
| `*.srt` | Styled subtitle file | Video Composer |
| `meta.json` | Caption presets, styles | Video Composer (style import) |
| `state.json` | Full caption state | Video Composer (block data) |

### Image Editor (port 8767)
**Input:** Screenshots, photos
**Output:** Annotated images, removed backgrounds, contour paths

Key exports:
| File | Format | Used By |
|------|--------|---------|
| `export.png` | Processed image | Video Composer (scene assets) |
| `state.json` | Annotation data | Video Composer (re-import) |

### Video Composer (port 8770)
**Input:** Audio + transcript (from Word Editor) + styled captions
         (from Caption Studio) + assets (from Image Editor)
**Output:** Final MP4 video with scenes, animations, captions, music

## Import Protocol

When Video Composer imports from another tool, it reads these files:

### From Word Editor
```python
import_service.import_from_audio(project_id):
    # Read source files
    meta = read(f"projects/{project_id}/meta.json")
    words = read(f"projects/{project_id}/words.json")
    audio = f"projects/{project_id}/export.mp3"  # or source.mp3

    # Create scene
    scene = {
        "name": meta["name"],
        "duration": words[-1]["end"],
        "audio_track": {
            "source": audio,
            "word_timestamps": words,
            "voice": meta.get("voice", "en-GB-RyanNeural"),
        },
        "elements": [
            {
                "type": "caption",
                "words": words,
                "group_size": 3,  # default: 3 words per group
                "style": "classic",  # default preset
            }
        ],
    }
    return scene
```

### From Caption Studio
```python
import_service.import_from_caption(project_id):
    meta = read(f"projects/{project_id}/meta.json")
    state = read(f"projects/{project_id}/state.json")

    # Extract styled caption blocks
    blocks = state.get("blocks", [])
    preset = state.get("preset", {})

    # Merge into existing scene
    scene = get_current_scene()
    scene["elements"][0]["style"] = {
        "font": preset.get("font", "Segoe UI"),
        "size": preset.get("size", 46),
        "color": preset.get("text", "#FFFFFF"),
        "highlight": preset.get("hi", "#FFD700"),
        "outline": preset.get("oc", "#000000"),
        "animation": preset.get("anim", "pop"),
        "box": {
            "shape": preset.get("boxshape", "rounded"),
            "opacity": preset.get("bxop", 100),
            "radius": preset.get("bxrad", 12),
            "padding": preset.get("bxpad", 14),
        },
    }
    return scene
```

### From Image Editor
```python
import_service.import_from_image(project_path):
    meta = read(f"{project_path}/meta.json")
    state = read(f"{project_path}/state.json")

    # Extract processed images
    images = []
    for item in state.get("layers", []):
        if item["type"] == "image":
            images.append({
                "path": item["src"],
                "width": item["width"],
                "height": item["height"],
                "annotations": item.get("annotations", []),
            })
    return images
```

## HyperFrames Integration

Video Composer generates HyperFrames-compatible HTML. Here's how
the translation works:

### Scene JSON → HyperFrames HTML

```python
def scene_to_hyperframes(scene):
    """Convert a scene JSON to HyperFrames HTML."""

    html = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    #stage {{
      width: {scene["width"]}px;
      height: {scene["height"]}px;
      background: {scene.get("bg_color", "#0e1116")};
      position: relative;
      overflow: hidden;
    }}
    .element {{
      position: absolute;
      /* ... styles from element properties ... */
    }}
  </style>
</head>
<body>
  <div id="stage"
       data-composition-id="{scene['id']}"
       data-width="{scene['width']}"
       data-height="{scene['height']}"
       data-duration="{scene['duration']}">'''

    # Add elements
    for el in scene["elements"]:
        html += render_element(el)

    # Add audio track
    if "audio_track" in scene:
        audio = scene["audio_track"]
        html += f'''
    <audio class="clip"
           data-track-index="0"
           src="{audio['source']}"></audio>'''

    # Add GSAP animations
    html += render_gsap_timeline(scene["elements"])

    html += '''
  </div>
</body>
</html>'''
    return html
```

### The Render Pipeline

```
1. Video Composer generates scene HTML files
   (compositions/scene_001.html, scene_002.html, ...)

2. For each scene, invoke HyperFrames CLI:
   npx hyperframes render compositions/scene_001.html \
     --output output/scene_001.mp4 \
     --width 1080 --height 1920

3. Concatenate rendered scenes with ffmpeg:
   ffmpeg -f concat -safe 0 -i scenes.txt \
     -c copy output/final_video.mp4

4. scenes.txt:
   file 'scene_001.mp4'
   file 'scene_002.mp4'
   ...
```

## Data Format Standards

### Word Timestamps (words.json)
```json
[
  {"word": "In", "start": 0.0, "end": 0.18},
  {"word": "my", "start": 0.18, "end": 0.34},
  {"word": "previous", "start": 0.34, "end": 0.78},
  {"word": "video", "start": 0.78, "end": 1.12}
]
```

### Scene Definition (scenes.json)
```json
{
  "version": 1,
  "canvas": {"width": 1080, "height": 1920},
  "scenes": [
    {"id": "scene_001", "name": "Hook", "duration": 8.5},
    {"id": "scene_002", "name": "Problem", "duration": 12.3}
  ]
}
```

### Element Definition (within scene)
```json
{
  "id": "el_001",
  "type": "text",
  "content": "Hello World",
  "x": 50, "y": 30,
  "width": 90, "height": 10,
  "font": "Inter",
  "size": 48,
  "color": "#FFFFFF",
  "align": "center",
  "animation": {"type": "fade-slide-up", "start": 0.5, "duration": 0.8}
}
```

### Template Definition
```json
{
  "id": "code-demo",
  "name": "Code Demo",
  "version": 1,
  "placeholders": {
    "title": {"type": "string", "default": "Code Demo"},
    "code": {"type": "string", "default": "// code here"},
    "language": {"type": "string", "default": "javascript"}
  },
  "scene": {
    "bg_color": "#0e1116",
    "elements": [
      {"type": "text", "content": "{{title}}", "animation": "fade-slide-up"},
      {"type": "code", "content": "{{code}}", "language": "{{language}}", "animation": "typewriter"}
    ]
  }
}
```

## Quick Reference — Port Numbers

| Tool | Port | URL | Start Command |
|------|------|-----|---------------|
| Word Editor | 8765 | http://127.0.0.1:8765 | `start_editor.bat` or `python server.py` |
| Caption Studio | 8766 | http://127.0.0.1:8766 | `python server.py` |
| Image Editor | 8767 | http://127.0.0.1:8767 | `python server.py` |
| Video Composer | 8770 | http://127.0.0.1:8770 | `python server.py` |

## Quick Reference — File Locations

```
AITREC/Videos/
├── word_editor/          ← Audio + transcripts
│   ├── projects/         ← Audio projects (fast-dir for media)
│   ├── packages/         ← Video-ready packages (audio + captions + meta)
│   └── exports/          ← Exported files
│
├── caption_editor/       ← Styled captions
│   └── projects/         ← Caption projects
│
├── image_editor/         ← Graphics + annotations
│   └── projects/         ← Image projects
│
├── video_composer/       ← Video scenes + rendering (NEW)
│   ├── projects/         ← Video projects
│   ├── templates/        ← Reusable scene templates
│   ├── compositions/     ← Generated HyperFrames HTML
│   └── output/           ← Rendered MP4s
│
└── .agents/skills/       ← AI skills
    └── script-workflow/  ← Script creation skill
```
