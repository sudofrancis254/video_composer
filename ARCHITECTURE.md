---
name: video-composer-architecture
version: 1.0.0
created: 2026-08-18
status: PLANNING
---

# Video Composer — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     VIDEO COMPOSER                              │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    BROWSER (Frontend)                     │  │
│  │                                                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │  │
│  │  │  Canvas   │  │ Timeline │  │  Style   │  │  Media  │  │  │
│  │  │  Editor   │  │  Editor  │  │  Panel   │  │ Library │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘  │  │
│  │       │              │              │              │        │  │
│  │  ┌────┴──────────────┴──────────────┴──────────────┴────┐  │  │
│  │  │         Canvas IS the Preview (HTML/CSS/JS)          │  │  │
│  │  │  Browser renders the same code HyperFrames will use  │  │  │
│  │  │  No separate preview — what you see = what renders   │  │  │
│  │  └──────────────────────────┬───────────────────────────┘  │  │
│  └─────────────────────────────┼──────────────────────────────┘  │
│                                │                                 │
│  ┌─────────────────────────────┼──────────────────────────────┐  │
│  │                    PYTHON (Backend)                         │  │
│  │                                │                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌┴─────────┐  ┌───────────┐  │  │
│  │  │ Project  │  │  Scene   │  │  Render  │  │  Media    │  │  │
│  │  │ Store    │  │ Generator│  │  Engine  │  │  Service  │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └───────────┘  │  │
│  │                                                             │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │  │
│  │  │  Import  │  │  Export  │  │   HyperFrames CLI         │  │  │
│  │  │ Service  │  │ Service  │  │   (render time ONLY)      │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ Word Editor │   │ Caption Studio  │   │  Image Editor    │
│ (audio +    │   │ (styled         │   │  (graphics +     │
│  transcript)│   │  captions)      │   │   annotations)   │
└─────────────┘   └─────────────────┘   └──────────────────┘
```

**Key insight:** The canvas IS the preview. During editing, the browser
renders the same HTML/CSS/JS that HyperFrames will render at export time.
There is no separate "HyperFrames preview" — the canvas is both the
editor and the preview. HyperFrames only runs at render time to
generate frame-by-frame screenshots → ffmpeg → MP4.

## Directory Structure

```
video_composer/
├── VISION.md                  ← this file's parent
├── ARCHITECTURE.md
├── PLAN.md
├── COMMUNICATION.md
├── TOOLCHAIN.md
├── LESSONS.md
│
├── server.py                  ← Python backend (stdlib HTTP)
├── project_store.py           ← project CRUD, fast-dir migration
├── scene_service.py           ← scene HTML generation
├── render_service.py          ← HyperFrames CLI wrapper
├── import_service.py          ← import from Word Editor / Caption Studio
├── media_service.py           ← local file browser, stock media fetch
│
├── static/
│   ├── index.html             ← single-page app shell
│   ├── app.js                 ← main application logic
│   ├── ui.js                  ← reusable UI components (panels, modals)
│   ├── canvas.js              ← scene canvas (drag/drop/resize)
│   ├── timeline.js            ← timeline editor (keyframes, tracks)
│   ├── style.css              ← all styles
│   └── icons/                 ← SVG icon set (Feather or similar)
│
├── templates/                 ← reusable scene templates
│   ├── hook.json              ← "Hook" scene template
│   ├── code-demo.json         ← code typing animation template
│   ├── split-screen.json      ← side-by-side layout
│   ├── kinetic-title.json     ← animated text template
│   └── ...
│
├── compositions/              ← HyperFrames HTML output (generated)
│   ├── scene_001.html
│   ├── scene_002.html
│   └── ...
│
├── projects/                  ← user projects
│   └── <project_id>/
│       ├── meta.json          ← project metadata
│       ├── scenes.json        ← scene list + ordering
│       ├── timeline.json      ← element timing data
│       ├── media/             ← copied/referenced media files
│       └── output/            ← rendered MP4 files
│
└── packages/                  ← video-ready packages (from Word Editor)
    └── <project_name>/
        ├── audio.mp3
        ├── captions.srt
        ├── captions.vtt
        └── meta.json
```

## Core Concepts

### 1. Scene

A **scene** is one shot in the video — a discrete visual unit with its own
layout, elements, and timing. A scene maps to one HyperFrames HTML file.

```json
{
  "id": "scene_001",
  "name": "Hook",
  "duration": 8.5,
  "width": 1080,
  "height": 1920,
  "bg_color": "#0e1116",
  "elements": [
    {
      "id": "el_001",
      "type": "text",
      "content": "Why Most Codebases Fail AI",
      "x": 50,
      "y": 30,
      "width": 90,
      "height": 15,
      "font": "Inter",
      "size": 48,
      "color": "#FFFFFF",
      "align": "center",
      "animation": {
        "type": "fade-slide-up",
        "start": 0.5,
        "duration": 0.8,
        "easing": "power2.out"
      }
    },
    {
      "id": "el_002",
      "type": "code",
      "content": "README.md",
      "x": 10,
      "y": 55,
      "width": 80,
      "height": 30,
      "animation": {
        "type": "typewriter",
        "start": 2.0,
        "duration": 3.0
      }
    }
  ],
  "audio_track": {
    "source": "packages/hook/hook.mp3",
    "captions": "packages/hook/hook.srt",
    "word_timestamps": "packages/hook/words.json"
  }
}
```

### 2. Element

An **element** is a visual object on the canvas. Types:

| Type | Description | Properties |
|------|-------------|------------|
| `text` | Styled text block | content, font, size, color, shadow, glow, outline |
| `image` | Static image | src, fit (cover/contain), border-radius |
| `video` | Video clip overlay | src, start, end, volume, fit |
| `shape` | Rectangle, circle, line | fill, stroke, border-radius, rotation |
| `code` | Code block with syntax highlight | language, theme, content, typing animation |
| `caption` | Word-level caption (auto-generated) | words, highlight style, group size |
| `svg` | Inline SVG element | path data, fill, stroke, animation |
| `component` | Reusable template instance | template_id, overrides |

### 3. Animation

Animations are GSAP timelines attached to elements. The visual editor
exposes common animations as presets, but any GSAP code is valid.

**Preset animations:**
- `fade-in` / `fade-out`
- `slide-up` / `slide-down` / `slide-left` / `slide-right`
- `zoom-in` / `zoom-out`
- `typewriter` (text types itself out)
- `word-by-word` (words appear one by one as spoken)
- `bounce` / `elastic` / `back`
- `morph` (shape morphing)
- `none` (no animation — static element)

**Custom animations** are written as GSAP timeline JSON:
```json
{
  "type": "custom",
  "gsap": {
    "timeline": [
      { "target": "#el_001", "from": { "opacity": 0, "y": 40 }, "duration": 0.8, "at": 0.5 },
      { "target": "#el_002", "from": { "scale": 0.8, "opacity": 0 }, "duration": 0.6, "at": 1.2 }
    ]
  }
}
```

### 4. Audio-Driven Visual System

**Audio is the DRIVER.** Every visual element is timed to exact word
timestamps from the audio transcript. The scene generator reads
`words.json`, splits into scenes at natural pauses, and creates
timed captions + visual elements.

```
words.json [{text: "In", start: 0.0, end: 0.187}, ...]
       │
       ▼
Scene Generator (server.py)
  ├── Split at gaps > 0.7s → scene boundaries
  ├── Group words into 4-6 word captions
  ├── Find emphasis points → visual elements
  └── Apply theme (bg color, pattern, accent)
       │
       ▼
Scene JSON
  ├── scene.duration = scene_end - scene_start
  ├── elements[].start/end = scene-LOCAL times
  └── audio_track.source = shared across all scenes
       │
       ▼
Canvas Rendering
  ├── Audio = PROJECT-level (one continuous track)
  ├── absStart = el.start + sceneOffset
  ├── renderCanvas() checks: t >= absStart - buffer && t <= absEnd + buffer
  ├── Captions: buffer = 0.05s (surgical precision)
  ├── Other elements: buffer = 0.5s (smooth animation)
  └── Scene transitions: crossfade overlay at boundaries
```

**Key rules:**
1. Audio is global — one continuous track, scenes are time segments
2. Element start/end are scene-local — canvas adds scene offset for absolute time
3. Caption timing must be surgical — no overlap between consecutive captions
4. Non-caption elements get animation buffer for smooth enter/exit
5. Background patterns use CSS classes (bg-grid, bg-dots) layered on backgroundColor

### 5. Timeline

The **timeline** is a horizontal representation of all elements across time.
Each element has a start time and duration. The timeline editor lets you:

- Drag element bars to reposition in time
- Resize bars to change duration
- Add keyframes for property changes (position, opacity, color, size)
- Preview the playhead position on the canvas
- Zoom in/out of the timeline

### 5. Collaboration Model (AI + Human)

The Video Composer supports **dual editing** — both programmatic (AI)
and visual (human) editing of the same scene data.

**How it works:**

1. **AI creates scenes** via API calls (POST /api/scenes) — writes
   scene JSON with elements, positions, styles, animations
2. **Canvas renders the same JSON** as HTML/CSS/JS — user sees the result
3. **User edits visually** — drag, resize, delete, add elements on canvas
4. **Canvas updates the JSON** — each user action modifies the scene data
5. **AI can read the updated JSON** — sees user changes, can suggest or
   make further programmatic edits
6. **User renders** — HyperFrames generates frames from the final JSON

**The key principle:** There is no "locked" state. Every element I
create is immediately editable by the user on the canvas. There's no
"AI-created vs user-created" distinction — they're all just elements
in the same scene. The scene JSON is the single source of truth.

```
User says: "Create a hook scene"
         │
         ▼
I call POST /api/scenes ──→ Scene JSON created
         │                    { elements: [text, image, caption] }
         │                              │
         ▼                              ▼
Canvas renders JSON ──→ User sees elements on screen
         │                              │
         ▼                              ▼
User drags title ──→ Canvas updates JSON ──→ Canvas re-renders
         │                              │
         ▼                              ▼
User clicks Render ──→ HyperFrames reads JSON ──→ MP4 output
```

### 5. Template

A **template** is a saved scene with placeholder values. Templates are
the key to reusability. Example:

```json
{
  "id": "code-demo",
  "name": "Code Demo",
  "description": "Code block typing itself out with narration",
  "placeholders": {
    "code_content": { "type": "string", "default": "// your code here" },
    "language": { "type": "string", "default": "javascript" },
    "title": { "type": "string", "default": "Code Demo" },
    "bg_color": { "type": "color", "default": "#0e1116" }
  },
  "scene": {
    "elements": [
      { "type": "text", "content": "{{title}}", "animation": "fade-slide-up" },
      { "type": "code", "content": "{{code_content}}", "language": "{{language}}", "animation": "typewriter" }
    ]
  }
}
```

When you create a new scene from a template, you fill in the placeholders
and the scene is generated. Edit the template once, and all future scenes
of that type benefit.

## Data Flow

### Import Flow (Word Editor → Video Composer)

```
1. User clicks "Import from Word Editor" in Video Composer
2. Video Composer lists Word Editor projects via API
   (reads projects/*/meta.json)
3. User selects a project (e.g., "hook")
4. Video Composer reads:
   - meta.json → project name, voice, duration
   - words.json → word-level timestamps
   - export.mp3 or source.mp3 → audio file
5. Video Composer creates a new scene with:
   - Audio track linked to the mp3
   - Caption element auto-generated from word timestamps
   - Default duration matching the audio length
6. Scene appears on canvas with captions ready to style
```

### Import Flow (Caption Studio → Video Composer)

```
1. User clicks "Import styled captions" in Video Composer
2. Video Composer lists Caption Studio projects via API
3. User selects a project
4. Video Composer reads:
   - meta.json → caption style presets, block data
   - state.json → styled caption blocks with timing
5. Video Composer merges caption styles into the scene
   (preserves font, color, animation, box style from Caption Studio)
```

### Render Flow

```
1. User clicks "Render" in Video Composer
2. Backend generates HyperFrames HTML for each scene:
   - canvas.js state → scene JSON → scene_service generates HTML
   - Each element becomes a <div> with data-* timing attributes
   - GSAP animations are wired via <script> blocks
   - Audio tracks are <audio> elements with data-start/duration
3. Backend invokes HyperFrames CLI:
   npx hyperframes render --composition scene_001.html --output output/scene_001.mp4
4. Backend concatenates rendered scenes:
   ffmpeg -f concat -i scenes.txt -c copy final_video.mp4
5. Frontend shows progress and provides download link
```

## Server API

All routes are under `/api/`:

```
GET    /api/projects                     → list all projects
POST   /api/projects                     → create new project
GET    /api/projects/:id                 → get project data
PUT    /api/projects/:id                 → update project
DELETE /api/projects/:id                 → delete project

POST   /api/projects/:id/scenes          → add scene
PUT    /api/projects/:id/scenes/:sid     → update scene
DELETE /api/projects/:id/scenes/:sid     → delete scene
PUT    /api/projects/:id/scenes/reorder  → reorder scenes

GET    /api/projects/:id/timeline        → get timeline state
PUT    /api/projects/:id/timeline        → update timeline

GET    /api/templates                    → list templates
POST   /api/templates                    → create template from scene
POST   /api/templates/:id/instantiate    → create scene from template

GET    /api/import/audio-projects        → list Word Editor projects
POST   /api/import/from-audio/:pid       → import from Word Editor
GET    /api/import/caption-projects      → list Caption Studio projects
POST   /api/import/from-caption/:pid     → import from Caption Studio

GET    /api/media                        → list local media files
POST   /api/media/upload                 → upload media file

POST   /api/render/:id                   → start render job
GET    /api/render/:id/status            → poll render progress
GET    /api/render/:id/download          → download rendered video

GET    /api/preview/:id/scene/:sid       → get HyperFrames HTML for preview
```

## Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Backend | Python 3.10+ stdlib HTTP server | Same pattern as Word Editor & Caption Studio — proven, no dependencies |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework overhead, fast iteration |
| Rendering | HyperFrames CLI | Open-source, Apache 2.0, deterministic HTML→MP4 — runs at render time ONLY |
| Animation | GSAP (GreenSock) | HyperFrames' primary animation runtime, seekable, frame-accurate |
| Audio | ffmpeg (system) | Already installed, handles all audio operations |
| Fonts | Google Fonts (CDN) | Free, vast selection, loads on demand |
| Icons | Feather Icons (SVG) | Clean, lightweight, MIT license |
| Preview | Canvas IS the preview | Browser renders the same HTML/CSS/JS as HyperFrames — no separate preview needed |

## Security & Constraints

1. **These are standalone videos, not Moodle content.** The WAF lessons
   from the Moodle saga only apply if we later create Moodle pages that
   embed these videos. Video creation itself has no WAF concerns.

2. **OneDrive throttling** — audio/video files should live in a fast
   local directory (not OneDrive-synced). The Word Editor's FAST_DIR
   pattern handles this. Video Composer should use the same approach.

3. **Local-only server** — bind to 127.0.0.1 only. No external access.
   No cloud services. The only outbound network calls are:
   - edge-tts (TTS generation via Microsoft Edge)
   - Google Fonts CDN
   - Optional: Pexels/Pixabay API for stock media

4. **File size awareness** — video files are large. The project store
   should use symlinks or direct references to avoid duplicating media
   files across projects.
