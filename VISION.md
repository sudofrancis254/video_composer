---
name: video-composer-vision
version: 1.0.0
created: 2026-08-18
status: PLANNING
---

# Video Composer — Vision

## The Problem

Creating videos today is either:
- **Manual** (CapCut, Premiere): drag clips, add captions, render. Repeat for every
  video. Hours of repetitive work. No reuse. No AI collaboration.
- **Code-first** (HyperFrames, Remotion): write HTML/CSS/JS scenes, render to MP4.
  Fast for AI, painful for humans — no drag-and-drop, no visual feedback until
  you preview in browser, no way to "just move that text up a bit."

Neither model supports **collaborative video creation between a human and an AI
agent**. The human sees things the AI can't (layout feels off, element too small,
animation too fast). The AI sees things the human can't (pacing math, timing
precision, code generation for complex animations). Today there's no tool that
lets both work together in the same interface.

## The Vision

Video Composer is a **local, browser-based video editor** that:

1. **Looks like a visual editor** — drag, drop, resize, position elements on a
   canvas. Timeline for timing. Style panel for properties. Everything a visual
   editor should have.

2. **Is powered by code behind the scenes** — every element, animation, and
   scene is an HTML/CSS/JS composition that HyperFrames renders to MP4. The
   visual editor is a GUI that writes HyperFrames-compatible code.

3. **Enables human-AI collaboration** — the AI agent (Buffy) can generate
   entire scenes, animations, and effects programmatically. The human refines
   them visually. Both see the same preview. Changes flow both ways.

4. **Reuses everything** — scenes, styles, animations, effects, and templates
   are saved as reusable components. The second video takes half the time of
   the first. The tenth video takes a quarter.

5. **Connects to the existing tool chain** — audio from Word Editor, captions
   from Caption Studio, images from Image Editor. No re-exporting, no
   copy-pasting. Import with one click.

## What "Success" Looks Like

**Today (without Video Composer):**
- Script → TTS → Edit audio → Transcribe → Style captions → Bake captions
  → Write HyperFrames scenes → Preview → Fix → Render → Repeat
- Time: 2-3 days per video
- Frustration: layout issues you can't see until render, animations that look
  wrong in the final output, no way to reuse previous work

**With Video Composer:**
- Script → TTS (Word Editor) → Import audio + transcript into Video Composer
  → AI generates scenes → You drag/resize/reposition → Preview live → Render
- Time: 2-4 hours per video
- Experience: you see exactly what you're building, changes are instant,
  everything is reusable

## Core Principles

### 1. Local-First
Everything runs on your machine. No cloud subscriptions. No uploads.
Your videos, your data, your tools. The only network call is edge-tts
for TTS generation and optional stock media fetching.

### 2. Visual by Default, Code When You Want It
The editor has a visual canvas, drag handles, property panels. But
every element also has a "View Source" that shows the HTML/CSS/JS.
Advanced users (or the AI agent) can edit the code directly. The
visual view updates to reflect code changes.

### 3. AI as Co-Pilot, Not Autopilot
The AI generates scenes, suggests animations, writes GSAP timelines,
and handles the parts that are tedious in code. But the human makes
the creative decisions: positioning, timing, style, feel. The AI
proposes, the human disposes.

### 4. Reusability is the Product
Every scene you build becomes a template. Every animation you create
becomes a preset. Every style you define becomes a theme. The tool
gets faster with use, not slower.

### 5. Compatible with HyperFrames
The output is standard HyperFrames HTML compositions. This means:
- You can render locally with `npx hyperframes render`
- You can use HyperFrames Studio for preview
- You can use the HyperFrames Catalog for ready-made components
- You can render on HeyGen's cloud if you want faster rendering
- You're not locked into our tool — the compositions are portable

## Scope

### In Scope (Phase 1)
- Scene editor canvas (drag/drop/resize elements)
- Element types: text, image, video clip, shape, code block
- Timeline editor (element timing, scene sequencing)
- Style panel (font, color, size, position, opacity, etc.)
- Caption import from Word Editor (word-level timestamps)
- Animation presets (fade, slide, typewriter, zoom, etc.)
- Scene templates (reusable scene types)
- Live preview in browser
- Render to MP4 via HyperFrames CLI
- Media library (local file browser)
- Project management (save/load/rename projects)

### In Scope (Phase 2)
- Multi-track audio (narrator + music + SFX)
- Audio-reactive visuals (text pulse with speech energy)
- Scene transitions (cross-fade, slide, wipe, shader effects)
- B-roll / stock media fetching (Pexels, Pixabay APIs)
- Per-word caption animation (words appear as spoken)
- Export presets (YouTube, TikTok, Instagram formats)
- Style/theme library (save and reuse visual styles)

### Out of Scope (Forever)
- Cloud rendering (local-first principle)
- Real-time collaboration (single-user tool)
- AI video generation (we compose, not generate)
- Subscription model (open-source, free forever)

## Users

**Primary user:** You (the course creator / video producer)
- Creates educational and explainer videos
- Values quality and production speed
- Comfortable with technology but prefers visual editing
- Works with an AI agent (Buffy) as a collaborator

**Secondary user:** The AI agent (Buffy)
- Generates scenes from scripts
- Writes complex animations (GSAP timelines)
- Handles timing math and pacing
- Suggests visual improvements based on content analysis

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to first video | < 4 hours (including setup) |
| Time for subsequent videos | < 2 hours |
| Reuse rate | 60%+ of scenes from templates |
| Render time | < 5 min for a 10-min video |
| Learning curve | productive within 30 minutes |
