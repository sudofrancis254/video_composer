# Video Composer

A browser-based video composition tool that creates timed visual scenes synced to audio with word-level precision.

## Features

- **Audio-driven composition** — scenes and elements timed to exact word timestamps
- **Timeline editor** — drag, resize, and reorder elements with keyframe support
- **Rich animations** — 10+ animation types (slide, zoom, bounce, elastic, etc.)
- **Scene transitions** — crossfade between scenes with background patterns
- **Element types** — text, shapes, images, captions with per-word highlighting
- **Canvas interaction** — drag, resize with 8-point handles, align, layer order
- **Undo/Redo** — full undo/redo stack
- **Export** — render to video or export HTML composition
- **Import** — import audio from Word Editor projects with word-level timestamps

## Architecture

```
video_composer/
├── server.py              # HTTP server (stdlib)
├── project_store.py       # Project storage management
├── import_service.py      # Import from Word Editor projects
├── scene_service.py       # Scene generation from audio transcripts
├── create_rich_demo.py    # Demo project builder
├── static/
│   ├── index.html         # Main UI
│   ├── app.js             # Canvas, timeline, properties panel
│   └── style.css          # Theme and layout
├── ARCHITECTURE.md        # Detailed architecture docs
├── PLAN.md                # Development roadmap
└── LESSONS.md             # Lessons learned
```

## Quick Start

```bash
cd AITREC/Videos/video_composer
python server.py
# Open http://127.0.0.1:8768
```

## How It Works

1. **Import** audio from a Word Editor project (with word-level timestamps)
2. **Generate Scenes** — AI splits transcript into scenes at natural pauses
3. **Edit** — drag elements, adjust timing, add animations
4. **Render** — export to video or HTML

## Audio-Driven Visual System

Every element's `start`/`end` maps to absolute project time. The audio plays continuously across all scenes. Elements appear and disappear based on their time range, with animation transitions at scene boundaries.

```
Scene 1: 0s — 23s     (elements start at 0, end at 23)
Scene 2: 23s — 65s    (elements start at 0 relative, +23 offset = absolute)
Scene 3: 65s — 93s    (elements start at 0 relative, +65 offset = absolute)
```

## Dependencies

- Python 3.10+ (stdlib only for server)
- ffmpeg (for rendering)
- Node.js (optional, for linting)
