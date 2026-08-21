# LESSONS LEARNED
> Building Word Editor, Caption Studio, Image Editor, and Video Composer — what worked, what broke, and what to never forget.

---

## 1. Architecture Lessons

### ✅ What Worked

| Pattern | Why It Works |
|---------|-------------|
| **Shared `project_store.py`** — single source of truth for paths | Every tool uses the same project structure; Caption Studio can import from Word Editor without fragile path assumptions |
| **Fast-dir migration** — heavy audio off OneDrive, JSON stays synced | ffmpeg writes 40× faster; sync still covers metadata; `WORD_EDITOR_FAST_DIR` env var for override |
| **Event log (`server-events.jsonl`)** — every API call logged | Every action is diagnosable after the fact; the frequency probe, transcription debugging, and silence investigations all relied on it |
| **`word_id`-based transcript linkage** — not time-based | Word Editor and Caption Studio share word IDs; no fragile timestamp interpolation needed when importing |
| **`audio_source` provenance** — Caption Studio remembers which Word project captions came from | Survives autosaves; renames in Word Editor update live in Caption Studio |

### ❌ What Broke (and the Fix)

| Problem | Root Cause | Fix |
|---------|------------|-----|
| Renders took 10+ minutes | OneDrive throttled ffmpeg writes to 0.04× speed | `FAST_DIR` at `AppData\Local\WordEditorWork` |
| `normalize-silences` / `speed` endpoints returned 404 | Server started before new routes were added | Documented: restart server after code changes; consider auto-reload |
| Bulk silence UI disappeared after UI adjustments | Feature was on separate "Bulk" sidebar page, not on "Silent spots" page | Moved bulk controls to the page where users actually scan gaps |
| Stale browser cache served old JS/HTML | `?v=3` never changed across edits | Bump cache-busting version on every significant frontend change |
| Browser history intercepting shortcuts | `<` and `>` triggered `history.back()` | `stopPropagation()` on all `<`/`>` keydown events |
| Caption box disappeared during editing | Selection handler removed it from DOM during edit mode | `isEditing` flag to suppress selection clearing while editing |
| Some captions unselectable after word-grouping | `.word-chip` click handlers consumed pointerdown before selection handler | Separate `pointerdown` on `.cap-box` vs `.word-chip` with proper delegation |

---

## 2. UI/UX Lessons

### Design Principles That Stuck

1. **Pages, not scrolling sections** — each sidebar button opens a discrete page, not a section you scroll to. Users should never scroll through unrelated controls.
2. **Progressive disclosure** — basic controls visible by default; advanced options behind a "more" toggle or gear icon.
3. **Inline editing** — double-click to rename, not a modal. Feels faster and less disruptive.
4. **Visual feedback for every action** — progress bars for long operations, toasts for completed actions, green borders for active panels.
5. **Sticky toolbar, scrollable content** — the top bar with play/export stays put; the transcript/content area scrolls independently.

### What Users Actually Want (vs What We Built)

| We built | They wanted |
|----------|-------------|
| Separate "Bulk" page for silence removal | Bulk controls on the same page as "Scan gaps" |
| Modal dialogs for project creation | Inline inputs in the creation form |
| Fixed caption box position | Draggable + resizable + auto-constrained to canvas |
| Predefined word grouping (3 words) | User-chosen grouping count |
| Separate "Effects" panel | Effects visible when you select the thing you're styling |

---

## 3. Content & WAF Lessons (Moodle)

### Rules That Never Change

1. **No SQL keywords in visible text** — `SELECT`, `INSERT`, `VALUES`, `UNION`, `DELETE` etc. in table-like structures (chips with `=` signs and parenthesized lists) trigger the WAF.
2. **SVGs need `viewBox` + `preserveAspectRatio="xMidYMid meet"`** to display correctly in Moodle's narrow content column (≈420px). Without these, content overflows or gets clipped.
3. **Fixed widths > relative widths** — `max-width:100%` on `.card` and `.note` classes prevents horizontal overflow. Use `width:calc(100% - 20px)` on hero headers.
4. **SVG fill colors must not contain SQL keywords** — `#select = green` triggers the WAF because `select` appears as a word near `=` signs.
5. **Label SVGs with CSS classes or data attributes** — never with inline text blocks that read like SQL.
6. **Moodle 4.5 handles `@@PLUGINFILE@@`** for images, but **only for single uploads via the WYSIWYG** — zip files don't auto-extract. Use drag-and-drop for bulk image upload.

### Bisect Protocol (for 403 Debugging)

1. Remove content from the bottom up in sections
2. When save succeeds, the last-removed section contains the trigger
3. Split that section into halves and repeat
4. The trigger is almost always: SQL keywords + table-like visible text + `=` signs + parenthesized lists

---

## 4. Audio Processing Lessons

### Whisper Transcription

- **model="small" + task="transcribe" + language="sw"** handles Swahili+English mixed content
- Processing time ≈ 0.2–0.5× real-time (9 min audio → 30–60 min on CPU)
- Adobe-enhanced audio produces better Whisper results than raw audio (less noise, clearer speech)
- **Always validate confidence scores** — words below 0.4 confidence are often wrong
- VAD data can fill gaps that Whisper missed (low-energy segments = likely speech that Whisper couldn't decode)

### Audio Enhancement

- **demucs** (stem separation) works but is slow on CPU; on GPU it's fast
- **DeepFilterNet** is the best local denoiser for speech
- **ffmpeg filters** (highpass, afftdn, equalizer, dynaudnorm, loudnorm) give 80% of Adobe-quality results
- **Adobe Podcast** still beats local enhancement for voice quality — consider it as a "premium" option
- Silence normalization: `afade=t=in` + `afade=t=out` on edges prevents clicks when trimming

### Export

- Always render to a fast local directory first, then copy to the project folder (OneDrive throttles writes)
- SRT/VTT naming: use project name, not internal ID
- Package folders should contain: audio + SRT + VTT + transcript + meta.json

---

## 5. Caption & Video Lessons

### Caption Rendering

- **ASS subtitles** support karaoke fill (`{\kf50}`), word highlighting, per-word styling
- **Rich renderer** (HTML→screenshot→frame) supports gradient text, 3D tilt, text-on-a-path — but is 5–10× slower
- **Neon glow** is the most reliable visual effect in ASS — works across all players
- Per-word effects (typewriter, wave, bounce) need word-level timestamps, not just cue-level

### Caption Interaction (Drag/Resize)

- Use `pointerdown` on the caption box, `pointermove` on document, `pointerup` on document
- Constrain position to canvas bounds
- Pause video when editing (prevents the caption from disappearing mid-drag)
- `isEditing` flag prevents selection handler from clearing the active caption during text edits

### The Unspoken Words Problem

- Words not yet spoken should be invisible (`opacity: 0` or `color: transparent`) and become visible as the playhead passes
- This requires per-word timestamps AND a rendering engine that updates per frame (ASS `\kf` or JS-based)
- The approach: render each word as a span with `opacity:0` + CSS transition triggered by karaoke timing

---

## 6. Collaboration Patterns (AI + Human)

### What Works

| Pattern | Why |
|---------|-----|
| **User tests, I fix** — user tries the tool, reports issues, I diagnose and patch | Fast iteration; user finds real UX problems I'd miss |
| **Document every decision** — LESSONS.md, USAGE_GUIDE.md, traceability notes | Prevents re-solving the same problem |
| **Event logging** — every API call logged with timestamp + params | Debugging is 10× faster when you can see what actually happened |
| **Bisect methodology** — split problems in halves | Found the WAF trigger ("chips" section) and the OneDrive throttle in under an hour |
| **Build the simplest thing that works, then iterate** | Caption Studio started as "style captions" → now has drag/resize/per-word effects |

### Communication Protocol

1. **User says what they see** → I investigate the code
2. **I propose a fix** → User tests it
3. **User reports results** → We document in LESSONS.md
4. **Every tool has a USAGE_GUIDE.md** → So the user never has to remember how it works

---

## 7. Tech Stack Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Backend | Python stdlib `http.server` | Zero dependencies, works everywhere, easy to debug |
| Audio processing | ffmpeg (CLI) | Fastest, most reliable, already installed |
| Speech recognition | openai-whisper (local) | No API costs, handles mixed languages |
| TTS | edge-tts (network) | Best free quality, natural-sounding voices |
| Subtitles | ASS format | Rich styling support, ffmpeg renders them perfectly |
| Rendering engine | HyperFrames (planned) | Open-source, HTML/CSS/JS → MP4, supports complex animations |
| Frontend | Vanilla JS + CSS | No build step, instant reload, user can edit directly |
| Data format | JSON (state, meta, words) | Human-readable, debuggable, easy to serialize |

---

## 8. Things to Never Forget

1. **Restart the server after editing Python files** — routes are loaded once at startup
2. **Bump `?v=N` on every frontend change** — browsers cache aggressively
3. **Test on actual Moodle** — local HTML rendering ≠ Moodle rendering (WAF, narrow column, plugin system)
4. **OneDrive kills performance** — always use the fast-dir for heavy I/O
5. **Log everything** — the event log has saved us multiple times
6. **Bisect, don't guess** — when something breaks, split the problem in half
7. **User's eyes > my assumptions** — if it looks broken to them, it IS broken
8. **Package audio with its metadata** — word-level timestamps, SRT, VTT, meta.json in one folder
9. **Consistency in naming** — project name flows through all exports and cross-tool references
10. **Make the tool work for the user's workflow, not the other way around**

---

## 9. Video Composer Lessons (August 2026)

### Audio-Driven Visuals — What We Learned

| Issue | Root Cause | Fix |
|-------|------------|-----|
| **Captions pile up on each other** | 0.5s buffer on both sides of caption time range caused all overlapping captions to render simultaneously | Remove buffer for captions — use 0.05s buffer only for non-caption elements to allow smooth enter/exit |
| **Background patterns invisible** | `stage.style.background = '#0a0e14'` (shorthand) overrode CSS class `background-image` patterns | Use `stage.style.backgroundColor` when a pattern class is present; never use shorthand when CSS class patterns are layered |
| **Welcome screen too small** | 48px SVG icon, 16px heading — looked like noise on a large canvas | 80px SVG, 22px heading, descriptive subtitle, better button styling |
| **Element positions lost on refresh** | `handleDrag()` and `handleResize()` updated DOM but never called `saveScene()` | Added `finishInteraction()` method that calls `saveScene()` after every drag/resize |
| **Images lost on reload** | `URL.createObjectURL()` blob URLs die when page reloads | Server-side upload endpoint: POST base64 → save to `{project_dir}/images/{filename}` → persistent URL `/images/{pid}/{filename}` |
| **Demo project showed nothing** | All captions in one scene (duration=93s), only tiny accent shapes (1-2% height) as visuals | Rebuild demo with multiple scenes, bigger visual elements (text titles, decorative circles, accent lines), and proper timing |
| **Audio not loading after scene generation** | Scene generator set `audio_track: None` because it looked for `meta.audio_source_track` (doesn't exist) | Fixed to search all scenes → source project → fast_dir with proper fallback chain |
| **No transitions between scenes** | Demo had only 1 scene spanning entire audio; crossfade needs ≥2 scenes | Split audio into 8-12 scenes at natural pauses; crossfade at boundaries |
| **Playback logging missing** | No way to diagnose what happens during play | Added `canvas_frame` logger: logs visible elements, types, scene name every 5th frame during playback |

### Key Architecture Insights

1. **Audio must be project-level, not scene-level** — one continuous track, scenes are time segments
2. **Captions need surgical precision** — word-level timestamps, no overlap buffer
3. **Visual elements need buffer** — 0.5s for smooth CSS transition enter/exit
4. **Scene generation reads word timestamps** — not hardcoded positions
5. **CSS background patterns need backgroundColor, not background shorthand** — shorthand overrides background-image
6. **Blob URLs die on reload** — always persist images to server
7. **Every drag/resize must call saveScene()** — DOM changes aren't persisted automatically
8. **Playback needs frame-level logging** — essential for diagnosing timing issues
9. **NEVER modify scene durations from audio metadata** — the loadedmetadata handler must NOT change scene durations; only extend the LAST scene if audio exceeds total scene time; corrupting a scene's duration destroys the entire timeline (all subsequent scenes shift, rendering 0 elements)
10. **Use requestAnimationFrame for playback rendering** — timeupdate fires only ~4 times/sec, far too slow for smooth animations; RAF gives 60fps rendering

### The loadedmetadata Disaster (August 2026)

**What happened:** At playback time, scenes after Scene 0 showed 0 rendered elements. Console logs showed `rendered=0` for all timestamps past Scene 0.

**Root cause:** The `loadedmetadata` event handler contained:
```javascript
if (this.currentScene && this.currentScene.duration < this.duration) {
  this.currentScene.duration = Math.ceil(this.duration);
}
```
This set Scene 0's duration from 8.28s → 92s (full audio length). Since `_getActiveScene()` iterates scenes by cumulative duration, ALL other scenes were pushed beyond the audio duration, so no elements from Scene 1-8 ever matched.

**Fix:** Only extend the LAST scene if total scene time < audio duration. Never touch other scene durations.

**Lesson:** Audio metadata is about the AUDIO, not the SCENES. Scene durations define the visual timeline. The audio may be longer or shorter — that's fine, but the scene structure must remain intact.

### Timeline & Scrubbing Lessons (August 2026)

| Issue | Root Cause | Fix |
|-------|------------|-----|
| **Playhead scrolls away with tracks** | Playhead was inside `timeline-tracks` (overflow-y: auto) | Moved playhead outside scrollable area to be a direct child of `.timeline` |
| **Clicking scene chip doesn't jump** | Scene chip only selected the scene, didn't seek audio to scene start | `selectScene()` already seeks to scene offset; ensured it works with RAF render loop |
| **Timeline segment click doesn't seek** | Segment click only selected element, didn't move playhead to element's start | Added `seekTo()` call in segment click handler |
| **Ruler not clickable for seeking** | Ruler rendered but had no click handler | Added pointerdown handler on `.timeline-ruler` that seeks to clicked position |
| **Playhead handle too small** | 10px triangle was hard to grab | Increased to 14px with rounded triangle shape |

---

*Last updated: August 2026 — after completing Word Editor, Caption Studio, Image Editor, and building Video Composer Phases 1-4.*
