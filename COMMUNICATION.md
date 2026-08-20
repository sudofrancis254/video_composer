---
name: video-composer-communication
version: 1.0.0
created: 2026-08-18
status: PLANNING
---

# Video Composer — Communication Protocol

This document defines how the human (you) and the AI agent (Buffy)
collaborate to create videos using Video Composer. Follow these
patterns to avoid the confusion and wasted time we experienced building
the other tools.

## The Golden Rules

### 1. One Phase at a Time
Never jump ahead. Complete the current phase, test it, confirm it works,
THEN move to the next. We broke this rule with the Caption Studio and
it cost us hours of backtracking.

### 2. Test Before You Build
Before building a new feature, verify the current state works:
- Can the server start?
- Can the page load in the browser?
- Can the last feature we built still function?
If any answer is no, fix that first.

### 3. Involve the User in Debugging
When something breaks, don't spin for an hour in isolation. Tell the
user what you suspect, what you've tried, and ask them to test specific
things. The user sees things in the browser that the AI cannot (layout
issues, rendering glitches, UX problems).

### 4. Document What We Learn
Every bug we fix, every workaround we discover, every constraint we
hit — write it down in LESSONS.md. This is not optional. We repeated
mistakes with the Caption Studio because we didn't document the
OneDrive throttling issue or the WAF trigger patterns.

### 5. Small Changes, Frequent Commits
After each meaningful change, verify it works and summarize what was
done. Don't make 20 edits and then try to figure out which one broke
something.

## Communication Flow — Building a Feature

```
┌──────────────────────────────────────────────────────────┐
│                    TYPICAL SESSION                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. USER says what they want:                            │
│     "Add a timeline editor where I can drag element bars" │
│                                                          │
│  2. AI reads the PLAN.md to see which phase this is      │
│     AI reads ARCHITECTURE.md for data structures         │
│     AI reads current code to understand the state         │
│                                                          │
│  3. AI creates a todo list (write_todos)                 │
│     Shows the user the plan:                             │
│     "Here's what I'll build in this session:             │
│      1. Timeline panel HTML                              │
│      2. Element bar rendering                            │
│      3. Drag-to-reposition                               │
│      4. Playhead sync                                    │
│      Please confirm or adjust."                          │
│                                                          │
│  4. USER confirms or adjusts                             │
│                                                          │
│  5. AI builds each item, tests after each:               │
│     - Build timeline panel → verify HTML loads            │
│     - Build bar rendering → verify bars appear            │
│     - Build drag logic → verify drag works                │
│     - Build playhead sync → verify seek works             │
│                                                          │
│  6. AI tells user to test:                               │
│     "Please open http://127.0.0.1:8770, go to the        │
│      Timeline tab, and try dragging a bar.               │
│      Tell me: does the bar move? Does the canvas         │
│      update? Does the audio seek?"                       │
│                                                          │
│  7. USER tests and reports back                          │
│                                                          │
│  8. If issues: AI fixes, user re-tests                   │
│     If works: AI documents in LESSONS.md, moves on       │
│                                                          │
│  9. End of session: AI summarizes                        │
│     "Today we built: [list]                               │
│      What works: [list]                                   │
│      What's next: [list]                                  │
│      Issues found: [list]"                                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Communication Flow — Video Creation

```
┌──────────────────────────────────────────────────────────┐
│              CREATING A VIDEO (once tool is built)        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. USER provides the script:                            │
│     "Here's the script for my next video"                │
│     (pastes the .md file or points to it)                │
│                                                          │
│  2. AI breaks it into sections:                          │
│     "I see 8 sections. Here's my plan:                   │
│      Scene 1 (Hook): kinetic title + code animation      │
│      Scene 2 (Problem): diagram + text overlay           │
│      Scene 3 (Solution): code demo with typewriter       │
│      ..."                                                │
│                                                          │
│  3. USER confirms or adjusts the visual plan             │
│                                                          │
│  4. AI generates scenes:                                 │
│     - Creates scene HTML from templates                  │
│     - Places elements on canvas with correct positions   │
│     - Adds animations (GSAP timelines)                   │
│     - Links audio tracks from Word Editor imports        │
│                                                          │
│  5. USER reviews in browser:                             │
│     "Scene 1 looks good. Scene 2: move the title up,    │
│      make the code block bigger, change the animation    │
│      to a slide instead of fade."                        │
│                                                          │
│  6. AI makes adjustments, user re-reviews                │
│     Repeat until all scenes look right                   │
│                                                          │
│  7. USER says "render"                                   │
│                                                          │
│  8. AI renders:                                          │
│     - Generates final HyperFrames HTML                   │
│     - Invokes HyperFrames CLI                            │
│     - Concatenates scenes                                │
│     - Reports progress                                   │
│                                                          │
│  9. USER watches the final video                         │
│     "Looks great! But the transition between scene 3     │
│      and 4 is too abrupt."                               │
│                                                          │
│  10. AI fixes, re-renders, repeat until done             │
│                                                          │
│  11. AI saves the scenes as templates for reuse          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## What the AI Generates vs. What the User Edits

| Task | Who Does It | Why |
|------|-------------|-----|
| Write HyperFrames HTML for scenes | AI | Code generation is what AI does best |
| Create GSAP animation timelines | AI | Complex animation code is tedious to write |
| Position elements roughly on canvas | AI | Based on script content and layout rules |
| Fine-tune element positions | User | Visual judgment — "that feels 10px too low" |
| Choose colors and fonts | User | Creative decision |
| Set animation timing | Both | AI suggests, user adjusts by feel |
| Sequence scenes | Both | AI suggests order, user confirms flow |
| Write captions style | User | Visual preference |
| Render the video | AI | Automated pipeline |
| Review the output | User | Final quality check |
| Save templates for reuse | AI | After user approves a scene |

## File Naming Convention

All files follow this pattern:
```
<project_name>_<scene_number>_<type>.<ext>
```

Examples:
```
agent_ready_01_hook.html          ← scene HTML
agent_ready_01_hook.mp4           ← rendered scene
agent_ready_full.mp4              ← final concatenated video
agent_ready_01_hook_preview.html  ← browser preview
```

## Server Ports

| Tool | Port | URL |
|------|------|-----|
| Word Editor | 8765 | http://127.0.0.1:8765 |
| Caption Studio | 8766 | http://127.0.0.1:8766 |
| Image Editor | 8767 | http://127.0.0.1:8767 |
| **Video Composer** | **8770** | **http://127.0.0.1:8770** |

## Session Start Checklist

At the beginning of every session, the AI should:

1. [ ] Read `VISION.md` — remind ourselves what we're building
2. [ ] Read `PLAN.md` — see which phase we're on
3. [ ] Read `LESSONS.md` — remember what went wrong before
4. [ ] Read the current state of the code — what works, what's broken
5. [ ] Create a todo list for this session
6. [ ] Summarize the plan to the user before starting

## Session End Checklist

At the end of every session, the AI should:

1. [ ] Summarize what was built and what works
2. [ ] List any known issues or bugs
3. [ ] Note what's next (which phase/task)
4. [ ] Update `LESSONS.md` with anything new we learned
5. [ ] Update `PLAN.md` if priorities changed
6. [ ] Verify the server can start cleanly

## Escalation Protocol

When something isn't working and the AI has been trying for more than
20 minutes:

1. **Stop coding.** Tell the user what's happening.
2. **Present the evidence:** "I've tried X, Y, Z. The error is W."
3. **Ask the user to test:** "Can you open the page and tell me what
   you see in the console (F12)?"
4. **Consider alternatives:** "Should we try a different approach?"
5. **If stuck on a specific library/tool:** Research it (web_search),
   read the docs, try the fix. If still stuck after 10 more minutes,
   move on and come back later.

**Never:** spin for an hour, make 50 edits without testing, or
abandon a session without summarizing what happened.
