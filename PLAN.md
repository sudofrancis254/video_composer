---
name: video-composer-plan
version: 1.0.0
created: 2026-08-18
status: PLANNING
---

# Video Composer — Implementation Plan

## Overview

8 phases, each building on the last. Each phase produces a working tool
you can use — no "big bang" delivery. The first phase gives you a
functional import-and-preview loop in a single session.

## Phase 1: Foundation (Session 1)
**Goal:** Import audio from Word Editor, display it on a canvas, preview
a basic scene with captions. End-to-end render to MP4.

**Key principle:** The canvas IS the preview. Browser renders HTML/CSS/JS
directly — same code HyperFrames will use at render time. No separate
"HyperFrames preview" step.

**Collaboration model:** I can create scenes programmatically via API.
User can immediately edit everything I create on the canvas (drag,
resize, delete, add). No locked state — one JSON, two editors.

### Deliverables
- `server.py` with project CRUD + import routes + scene element CRUD
- `static/index.html` — app shell with canvas area + toolbar + properties panel
- `static/app.js` — project management, import wiring, element interaction
- `static/canvas.js` — canvas rendering, drag/drop/resize (uses scene JSON)
- `static/style.css` — dark theme layout
- Basic canvas: shows a colored rectangle (the "stage") with correct
  dimensions (1080×1920 or 1920×1080)

### Tasks
1. [ ] Create `server.py` — stdlib HTTP server, static file serving,
   project CRUD endpoints, scene element CRUD endpoints
2. [ ] Create `project_store.py` — project folder structure, FAST_DIR
   for media
3. [ ] Create `import_service.py` — read Word Editor projects, extract
   audio + words.json + meta.json
4. [ ] Create `static/index.html` — app shell with sidebar, canvas area,
   toolbar (text/image/shape buttons), properties panel
5. [ ] Create `static/app.js` — boot, project list, import flow
6. [ ] Create `static/canvas.js` — canvas rendering engine:
   - Reads scene JSON → renders HTML elements on the canvas div
   - Handles click-to-select, drag-to-move, corner-resize
   - Updates scene JSON on every user action
   - This IS the preview — same HTML/CSS/JS HyperFrames will render
7. [ ] Create `static/style.css` — dark theme layout
8. [ ] Implement "Import from Word Editor" — select project → creates
   scene with audio track + auto-generated caption element
9. [ ] Implement basic canvas preview — colored stage, play/pause audio,
   show captions synced to playback
10. [ ] Implement `scene_service.py` — generate HyperFrames HTML from
    scene data (same format the canvas uses for preview)
11. [ ] Implement render pipeline — generate HTML → invoke HyperFrames
    CLI → produce MP4

### Acceptance Criteria
- [ ] Can start server, see app in browser
- [ ] Can import a Word Editor project (e.g., "hook")
- [ ] Audio plays on the canvas
- [ ] Captions appear synced to audio (word-level highlighting)
- [ ] Can drag/caption element to reposition on canvas
- [ ] Can add text/image elements via toolbar buttons
- [ ] Can render to MP4 and download the video
- [ ] Rendered video matches the canvas layout exactly

---

## Phase 2: Canvas Editing (Session 2)
**Goal:** Drag, drop, resize, and position elements on the canvas.
Visual editing that writes HyperFrames-compatible code.

### Deliverables
- `static/canvas.js` — canvas interaction engine
- Element selection, drag-move, corner-resize handles
- Property panel updates when elements are selected

### Tasks
1. [ ] Implement element rendering on canvas (positioned divs with
   correct CSS transforms)
2. [ ] Implement click-to-select on canvas elements
3. [ ] Implement drag-to-move (update element x/y in scene data)
4. [ ] Implement corner-resize handles (update element width/height)
5. [ ] Implement property panel — shows selected element's properties
   (position, size, font, color, opacity, etc.)
6. [ ] Implement property changes from panel → update canvas in real-time
7. [ ] Implement "Add Text" button → places a new text element on canvas
8. [ ] Implement "Add Image" button → file picker → places image on canvas
9. [ ] Implement "Add Shape" button → places a rectangle on canvas
10. [ ] Implement layer ordering (bring to front, send to back)
11. [ ] Implement delete element (select → Delete key)
12. [ ] Implement undo/redo (Ctrl+Z / Ctrl+Shift+Z)

### Acceptance Criteria
- [ ] Can add text, image, and shape elements to canvas
- [ ] Can drag elements to reposition them
- [ ] Can resize elements by dragging corners
- [ ] Property panel shows and edits selected element's properties
- [ ] Changes reflect immediately on canvas
- [ ] Can undo/redo changes
- [ ] Rendered MP4 matches the canvas layout
- [ ] Elements created by AI (via API) are fully editable on canvas
- [ ] User can delete any element (including AI-created ones)
- [ ] User can add elements on top of AI-created scenes

---

## Phase 3: Timeline Editor (Session 3)
**Goal:** A horizontal timeline where you can set when each element
appears and disappears, add keyframes for property changes, and
sequence multiple scenes.

### Deliverables
- `static/timeline.js` — timeline editor component
- Element tracks with draggable start/end handles
- Playhead scrubbing
- Scene thumbnails in a scene strip above the timeline

### Tasks
1. [ ] Implement timeline panel — horizontal scrollable track area
2. [ ] Render element bars on timeline (colored bars = element duration)
3. [ ] Drag element bars left/right to change start time
4. [ ] Resize bar edges to change duration
5. [ ] Playhead line that moves during playback
6. [ ] Click timeline to seek (jump playhead + audio position)
7. [ ] Scene strip above timeline — thumbnails for each scene, click to
   switch scenes, drag to reorder
8. [ ] "Add Scene" button → creates empty scene, adds to sequence
9. [ ] Keyframe dots on element bars — click to add keyframe, opens
   property editor for that moment
10. [ ] Playhead scrubbing (drag playhead to preview any frame)

### Acceptance Criteria
- [ ] Timeline shows all elements as bars
- [ ] Can drag bars to reposition elements in time
- [ ] Can resize bars to change element duration
- [ ] Playhead follows audio playback
- [ ] Can click timeline to seek
- [ ] Can switch between scenes via scene strip
- [ ] Can reorder scenes by dragging in the strip
- [ ] Keyframes visible on element bars

---

## Phase 4: Styling & Animations (Session 4)
**Goal:** Full style control for elements (font, color, shadow, glow,
outline, etc.) and animation presets. Caption styling from Caption
Studio integration.

### Deliverables
- Enhanced style panel with all visual properties
- Animation preset selector
- Caption style import from Caption Studio

### Tasks
1. [ ] Expand style panel: font family (Google Fonts dropdown),
   font size, font weight, italic, uppercase
2. [ ] Color picker for text, stroke, shadow, glow
3. [ ] Shadow controls (offset, blur, color)
4. [ ] Glow controls (radius, color)
5. [ ] Outline/stroke controls (width, color)
6. [ ] Box/background controls (color, opacity, border-radius, padding)
7. [ ] Alignment controls (left, center, right)
8. [ ] Animation preset dropdown: none, fade-in, slide-up, slide-down,
   zoom-in, typewriter, word-by-word, bounce
9. [ ] Animation timing: start delay, duration
10. [ ] "Import style from Caption Studio" — reads caption presets and
    applies to caption elements
11. [ ] Style library: save current element style as a named preset,
    apply preset to other elements
12. [ ] Per-caption override: select individual words in a caption
    element, apply different font/color/size

### Acceptance Criteria
- [ ] Can change font, size, color, weight of text elements
- [ ] Can add shadow and glow effects
- [ ] Can apply animation presets and see them in preview
- [ ] Can import caption styles from Caption Studio
- [ ] Can save and reuse style presets
- [ ] Can style individual words within captions

---

## Phase 5: Templates & Reusability (Session 5)
**Goal:** Save any scene as a template, instantiate scenes from
templates, build a template library.

### Deliverables
- Template system (create, list, instantiate)
- Pre-built templates for common scene types
- Template parameter system (placeholders)

### Tasks
1. [ ] "Save as Template" button on scene — extracts scene as template
   JSON with placeholder values
2. [ ] Template library panel — browse saved templates with previews
3. [ ] "New from Template" flow — select template → fill placeholders
   → scene created
4. [ ] Build starter templates:
   - "Hook" — dark bg, animated title, subtitle
   - "Code Demo" — code block with typewriter animation
   - "Split Screen" — left text, right image/video
   - "Kinetic Title" — large animated text, minimal
   - "Caption Scene" — full-screen captions with word-by-word highlight
   - "PiP" — picture-in-picture overlay on video
5. [ ] Template parameters: type (string, color, number, media),
   default values, validation
6. [ ] Template versioning — update template, existing scenes unaffected
   (opt-in to update)

### Acceptance Criteria
- [ ] Can save any scene as a template
- [ ] Can browse and preview templates
- [ ] Can create new scenes from templates
- [ ] Starter templates work out of the box
- [ ] Template parameters work (fill in values, scene generates correctly)
- [ ] Updating a template doesn't break existing scenes

---

## Phase 6: Render Pipeline (Session 6)
**Goal:** Robust render pipeline with progress tracking, scene
concatenation, and output options.

### Deliverables
- Full render pipeline (scene HTML → HyperFrames → MP4 → concat)
- Progress UI with percentage and status
- Output format options

### Tasks
1. [ ] Generate HyperFrames HTML for each scene (scene_service)
2. [ ] Render each scene to MP4 via HyperFrames CLI (parallel possible)
3. [ ] Concatenate scene MP4s + audio into final video
4. [ ] Progress tracking: per-scene status, overall percentage
5. [ ] Cancel render button
6. [ ] Render queue: render scenes in order, show which is rendering
7. [ ] Output options: resolution (1080p, 720p), format (MP4, WebM),
   quality (high, medium, low)
8. [ ] Post-render: show final video in preview, download button
9. [ ] Render cache: don't re-render unchanged scenes
10. [ ] Export options: full video, individual scenes, just audio + captions

### Acceptance Criteria
- [ ] Can render a multi-scene video end-to-end
- [ ] Progress bar shows accurate render status
- [ ] Can cancel a render in progress
- [ ] Rendered video plays correctly with all elements and animations
- [ ] Can choose output resolution and format
- [ ] Render cache works (unchanged scenes skip re-render)

---

## Phase 7: Media Library & Polish (Session 7)
**Goal:** Local media browser, drag-and-drop media import, stock
media fetching, and overall polish.

### Deliverables
- Media library panel with local file browsing
- Drag-and-drop import
- Optional stock media (Pexels/Pixabay)
- UI polish and keyboard shortcuts

### Tasks
1. [ ] Media library panel — shows folders and files from a configured
   media directory
2. [ ] Drag-and-drop from file explorer onto canvas → creates image/video
   element
3. [ ] Upload zone in media library — upload files to project media folder
4. [ ] Optional: Pexels/Pixabay API integration for stock photos/videos
5. [ ] Keyboard shortcuts: Space=play/pause, Delete=remove element,
   Ctrl+S=save, Ctrl+Z=undo, Ctrl+C/V=copy/paste element
6. [ ] Canvas zoom in/out (scroll wheel)
7. [ ] Canvas pan (middle-click drag or space+drag)
8. [ ] Snap-to-grid and alignment guides
9. [ ] Rulers on canvas edges
10. [ ] Properties panel: precise numeric inputs for position/size
    (not just drag)

### Acceptance Criteria
- [ ] Can browse local media files in the library
- [ ] Can drag media from file explorer onto canvas
- [ ] Can upload media to project
- [ ] Keyboard shortcuts work
- [ ] Canvas zoom and pan work
- [ ] Snap-to-grid works

---

## Phase 8: Multi-Audio & Audio-Reactive (Session 8)
**Goal:** Multi-track audio (narrator + music + SFX), audio-reactive
visuals, and final polish for daily use.

### Deliverables
- Multi-track audio mixer
- Audio-reactive element binding
- Final UI polish and documentation

### Tasks
1. [ ] Audio track manager — add/remove/reorder tracks
2. [ ] Track types: narrator (primary), music (background), SFX (one-shot)
3. [ ] Volume controls per track
4. [ ] Music track: auto-ducking when narrator speaks (from Word Editor
   energy data)
5. [ ] Audio-reactive binding: link element properties to audio energy
   - Text glow intensity follows speech volume
   - Shape scale pulses with beat
   - Color shifts with frequency bands
6. [ ] SFX placement on timeline — click to add SFX at playhead position
7. [ ] Final documentation update — USAGE_GUIDE.md for Video Composer
8. [ ] End-to-end test: import 10 agent-ready sections → build scenes
   from templates → add music → render full video

### Acceptance Criteria
- [ ] Can add multiple audio tracks
- [ ] Volume controls work per track
- [ ] Music ducks under narration
- [ ] Audio-reactive effects work (text glows with speech)
- [ ] Can place SFX on timeline
- [ ] Full agent-ready video renders successfully
- [ ] USAGE_GUIDE.md is complete

---

## Audio-Driven Feature (Added 2026-08-19)

### Concept
Audio is the DRIVER of all visuals. Every element's start/end time
maps to exact word timestamps from the audio transcript. The AI
(reads word-level timestamps → decides what visuals to show → places
them at precise audio moments).

### Architecture
```
words.json (word-level timestamps)
        │
        ▼
Scene Generator (server.py)
  ├── Split words into scenes at natural pauses
  ├── Create captions grouped 4-6 words, timed to exact timestamps
  ├── Create visual elements (titles, shapes) at emphasis points
  └── Theme presets: tech, minimal, bold
        │
        ▼
Scene JSON (scenes.json)
  ├── scene[].elements[].start/end = scene-local times
  └── Canvas renders ALL scenes based on absolute time
        │
        ▼
Canvas Rendering
  ├── Audio is PROJECT-level (one continuous track)
  ├── Scenes are time segments within the audio
  ├── Elements appear/disappear at exact word timestamps
  └── Scene transitions: crossfade at boundaries
```

### Key Design Decisions
1. **Audio is global** — one continuous track, scenes are time segments
2. **Captions need surgical timing** — no overlap buffer, appear/disappear precisely
3. **Visual elements (non-captions) get a 0.5s buffer** for smooth enter/exit
4. **Scene transitions** — crossfade overlay at scene boundaries (0.8s)
5. **Background patterns** — CSS background-image (grid, dots, math lines)
   layered on backgroundColor for visibility

### Known Issues (Fixed 2026-08-19)
| Issue | Root Cause | Fix |
|-------|------------|-----|
| Captions overlap/pile up | 0.5s buffer on both sides of caption time range | Remove buffer for captions (use 0.05s) |
| Background patterns invisible | CSS background-image overridden by inline shorthand | Use backgroundColor (not shorthand) when pattern class present |
| Welcome screen too small | 48px SVG, 16px heading | 80px SVG, 22px heading, better layout |
| Elements lost on drag | handleDrag/handleResize didn't call saveScene() | Added finishInteraction() that calls saveScene() |
| Images lost on reload | URL.createObjectURL blob URLs die on reload | Server upload endpoint with persistent /images/{pid}/{file} URLs |

---

## Session Estimation

| Phase | Sessions | Dependencies | Status |
|-------|----------|--------------|--------|
| 1. Foundation | 1 | None | ✅ Done |
| 2. Canvas Editing | 1-2 | Phase 1 | ✅ Done |
| 3. Timeline Editor | 1-2 | Phase 2 | ✅ Done |
| 4. Styling & Animations | 1-2 | Phase 2 | 🔄 Partial (10 animations, basic style) |
| 5. Templates | 1 | Phase 4 | ⬜ Not started |
| 6. Render Pipeline | 1 | Phase 3 | 🔄 Basic (HTML export) |
| 7. Media Library | 1 | Phase 2 | ⬜ Not started |
| 8. Multi-Audio | 1 | Phase 6 | ⬜ Not started |
| **Total** | **8-12 sessions** | | **Phases 1-3 done, 4-6 partial** |

**Fast-track option:** Phases 1-3 + 6 can produce a working video
tool in ~5 sessions. Phases 4-5 + 7-8 add polish and reusability.

## Collaboration Protocol: AI + Human

### How Scene Creation Works

| Step | Who | What Happens |
|------|-----|---------------|
| 1 | You | Say "create a hook scene" or "add a title here" |
| 2 | Me | Call API → scene JSON → canvas renders it |
| 3 | You | See my elements on canvas — review |
| 4 | You | Edit anything I created (drag, resize, delete, replace) |
| 5 | Me | Or I can make further programmatic changes if you ask |
| 6 | You | Click Render → HyperFrames produces MP4 |

### Key Rules

1. **No locked state** — every element I create is immediately editable
2. **One JSON model** — my API calls and your canvas edits write to the
   same scene JSON. No "AI layer" vs "user layer".
3. **I create starting points, not final products** — you always have
   full visual control over everything.
4. **You can jump in at any step** — skip my creation and start from
   scratch, or render exactly what I built.
5. **Mix freely** — I create some elements, you create others in the
   same scene. They coexist naturally.

## Milestones

| Milestone | Phases | What you can do |
|-----------|--------|-----------------|
| **M1: First Render** | 1 | Import audio → preview captions → render MP4 |
| **M2: Visual Editing** | 2 | Drag/drop/resize elements on canvas |
| **M3: Timeline Control** | 3 | Set element timing, sequence scenes |
| **M4: Styled & Animated** | 4 | Full visual control, animations, caption styles |
| **M5: Reusable** | 5 | Templates, style library, fast scene creation |
| **M6: Production Ready** | 6 | Robust rendering with progress and options |
| **M7: Media Rich** | 7 | Stock media, drag-drop import, keyboard shortcuts |
| **M8: Full Studio** | 8 | Multi-track audio, audio-reactive, daily use |
