#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scene_service.py
================
Generates HyperFrames-compatible HTML from scene JSON data.
Each scene becomes one HTML file with GSAP animations,
audio sync, and word-level caption highlighting.
"""

import os
import json
import sys
import html as html_mod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps


def generate_scene_html(pid: str, scene: dict) -> str:
    """
    Generate a complete HTML document for a scene.
    This HTML is what HyperFrames renders to frames at export time,
    and what the browser canvas renders for live preview.
    """
    width = 1920
    height = 1080
    meta = ps._read_json(os.path.join(ps.project_dir(pid), "meta.json")) or {}
    width = meta.get("width", width)
    height = meta.get("height", height)

    scene_id = scene.get("id", "unknown")
    duration = scene.get("duration", 10)
    bg_color = scene.get("bg_color", "#0e1116")
    elements = scene.get("elements", [])
    audio_track = scene.get("audio_track", {})

    # Build element HTML
    elements_html = []
    elements_css = []
    elements_js = []

    for el in elements:
        el_html, el_css, el_js = _render_element(el, width, height)
        elements_html.append(el_html)
        elements_css.append(el_css)
        elements_js.append(el_js)

    # Build GSAP timeline
    gsap_timeline = _build_gsap_timeline(elements, duration)

    # Audio element
    audio_html = ""
    if audio_track.get("source"):
        audio_src = audio_track["source"]
        # Use relative path for HyperFrames, absolute for local preview
        if os.path.isabs(audio_src):
            audio_src = "file:///" + audio_src.replace("\\", "/")
        audio_html = f'<audio id="audio" src="{audio_src}" preload="auto"></audio>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width}, initial-scale=1.0">
<title>Scene: {html_mod.escape(scene.get("name", scene_id))}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {width}px;
    height: {height}px;
    background: {bg_color};
    overflow: hidden;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    position: relative;
  }}
  .scene-container {{
    width: 100%;
    height: 100%;
    position: relative;
  }}
  .element {{
    position: absolute;
    overflow: hidden;
  }}
  .element[data-type="text"] {{
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  .element[data-type="caption"] {{
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 12px 20px;
  }}
  .element[data-type="image"] {{
    background-size: cover;
    background-position: center;
  }}
  .element[data-type="shape"] {{
    border-radius: 0;
  }}
  .word-highlight {{
    color: #FFD700;
    font-weight: bold;
  }}
  .word-dim {{
    opacity: 0.4;
  }}
  .word-spoken {{
    opacity: 1;
  }}
  .word-unspoken {{
    opacity: 0;
  }}
  /* Caption box styles */
  .caption-box {{
    display: inline-block;
    padding: 8px 16px;
    border-radius: 12px;
  }}
  .caption-box.pill {{ border-radius: 999px; }}
  .caption-box.rounded {{ border-radius: 12px; }}
  .caption-box.sharp {{ border-radius: 0; }}
  /* Element styles */
  {"".join(elements_css)}
</style>
</head>
<body>
<div class="scene-container" id="scene">
  {audio_html}
  {"".join(elements_html)}
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
// Scene data
const SCENE = {json.dumps(scene, ensure_ascii=False)};
const DURATION = {duration};
const WIDTH = {width};
const HEIGHT = {height};

// Audio sync
const audio = document.getElementById('audio');
let currentTime = 0;

if (audio) {{
  audio.addEventListener('timeupdate', () => {{
    currentTime = audio.currentTime;
    updateCaptions(currentTime);
  }});
}}

// Caption word highlighting
function updateCaptions(t) {{
  document.querySelectorAll('.element[data-type="caption"]').forEach(el => {{
    const words = JSON.parse(el.dataset.words || '[]');
    const wordEls = el.querySelectorAll('.word');
    wordEls.forEach((wordEl, i) => {{
      if (!words[i]) return;
      const w = words[i];
      if (t >= w.start && t <= w.end) {{
        wordEl.className = 'word word-highlight';
      }} else if (t > w.end) {{
        wordEl.className = 'word word-spoken';
      }} else {{
        wordEl.className = 'word word-unspoken';
      }}
    }});
  }});
}}

// GSAP Timeline
{gsap_timeline}

// Play control (used by HyperFrames renderer)
function play() {{
  if (audio) audio.play();
  gsap.globalTimeline.play();
}}
function pause() {{
  if (audio) audio.pause();
  gsap.globalTimeline.pause();
}}
function seek(time) {{
  gsap.globalTimeline.seek(time);
  if (audio) audio.currentTime = time;
  updateCaptions(time);
}}

// Auto-play on load
document.addEventListener('DOMContentLoaded', () => {{
  gsap.globalTimeline.pause();
  if (audio) {{
    audio.addEventListener('canplaythrough', () => {{
      play();
    }}, {{ once: true }});
  }}
}});

{"".join(elements_js)}
</script>
</body>
</html>"""

    return html_content


def generate_composition_html(pid: str, scenes: list[dict]) -> str:
    """
    Generate a multi-scene composition HTML.
    Scenes are sequenced with gaps based on timeline data.
    """
    meta = ps._read_json(os.path.join(ps.project_dir(pid), "meta.json")) or {}
    width = meta.get("width", 1920)
    height = meta.get("height", 1080)

    # Build scene elements
    scenes_html = []
    scenes_css = []
    scenes_js = []
    total_offset = 0.0

    for scene in scenes:
        duration = scene.get("duration", 10)
        bg_color = scene.get("bg_color", "#0e1116")
        elements = scene.get("elements", [])

        scene_divs = []
        scene_styles = []
        for el in elements:
            el_html, el_css, el_js = _render_element(el, width, height, time_offset=total_offset)
            scene_divs.append(el_html)
            scene_styles.append(el_css)
            scene_styles.append(el_js)

        scenes_html.append(
            f'<div class="scene" data-scene="{scene.get("id", "")}" '
            f'data-start="{total_offset}" data-duration="{duration}" '
            f'style="position:absolute;top:0;left:0;width:100%;height:100%;'
            f'background:{bg_color};display:none;">'
            f'{"".join(scene_divs)}</div>'
        )
        scenes_css.extend(scene_styles)
        total_offset += duration

    # Audio tracks
    audio_elements = []
    for scene in scenes:
        at = scene.get("audio_track", {})
        if at.get("source"):
            src = at["source"]
            if os.path.isabs(src):
                src = "file:///" + src.replace("\\", "/")
            offset = scenes.index(scene)
            audio_offset = sum(s.get("duration", 10) for s in scenes[:offset])
            audio_elements.append(
                f'<audio class="scene-audio" data-offset="{audio_offset}" '
                f'src="{src}" preload="auto"></audio>'
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Composition</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    width: {width}px; height: {height}px;
    background: #0e1116; overflow: hidden;
    font-family: 'Inter', 'Segoe UI', sans-serif;
  }}
  .scene {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
  .element {{ position: absolute; overflow: hidden; }}
  .element[data-type="caption"] {{ display: flex; align-items: center; justify-content: center; text-align: center; padding: 12px 20px; }}
  .element[data-type="image"] {{ background-size: cover; background-position: center; }}
  .word-highlight {{ color: #FFD700; font-weight: bold; }}
  .word-spoken {{ opacity: 1; }}
  .word-unspoken {{ opacity: 0; }}
  {"".join(scenes_css)}
</style>
</head>
<body>
{"".join(scenes_html)}
{"".join(audio_elements)}

<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
const TOTAL_DURATION = {total_offset};
const SCENES = {json.dumps([{"id": s.get("id"), "start": sum(sc.get("duration", 10) for sc in scenes[:i]), "duration": s.get("duration", 10)} for i, s in enumerate(scenes)], ensure_ascii=False)};

let playing = false;
let startTime = 0;

function showScene(t) {{
  document.querySelectorAll('.scene').forEach(el => {{
    const start = parseFloat(el.dataset.start);
    const dur = parseFloat(el.dataset.duration);
    el.style.display = (t >= start && t < start + dur) ? 'block' : 'none';
  }});
  document.querySelectorAll('.scene-audio').forEach(a => {{
    const offset = parseFloat(a.dataset.offset);
    const t2 = t - offset;
    if (t2 >= 0 && t2 < 1) {{ a.currentTime = t2; a.play(); }}
  }});
}}

function play() {{ playing = true; startTime = performance.now() / 1000; tick(); }}
function pause() {{ playing = false; }}
function seek(t) {{ startTime = performance.now() / 1000 - t; showScene(t); }}

function tick() {{
  if (!playing) return;
  const t = performance.now() / 1000 - startTime;
  if (t >= TOTAL_DURATION) {{ pause(); return; }}
  showScene(t);
  requestAnimationFrame(tick);
}}

document.addEventListener('DOMContentLoaded', () => {{ play(); }});
{"".join(scenes_js)}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Element rendering
# ---------------------------------------------------------------------------

def _render_element(el: dict, canvas_w: int, canvas_h: int, time_offset: float = 0):
    """Render a single element to (html, css, js)."""
    el_id = el.get("id", "el_unknown")
    el_type = el.get("type", "text")
    eid = f"el-{el_id}"

    # Convert percent-based positions to pixels
    x = _to_px(el.get("x", 0), canvas_w)
    y = _to_px(el.get("y", 0), canvas_h)
    w = _to_px(el.get("width", 50), canvas_w)
    h = _to_px(el.get("height", 10), canvas_h)

    start = el.get("start", 0) + time_offset
    end = el.get("end", start + 5)

    # Base styles
    style = f"left:{x}px;top:{y}px;width:{w}px;height:{h}px;"

    html_el = ""
    css = ""
    js = ""

    if el_type == "text":
        content = html_mod.escape(el.get("content", "Text"))
        font = el.get("font", "Inter")
        size = el.get("size", 48)
        color = el.get("color", "#FFFFFF")
        weight = el.get("weight", "normal")
        align = el.get("align", "center")
        style += f"font-family:'{font}';font-size:{size}px;color:{color};font-weight:{weight};text-align:{align};"

        # Box background
        if el.get("bg_color"):
            style += f"background:{el['bg_color']};padding:12px 24px;"
        if el.get("border_radius"):
            style += f"border-radius:{el['border_radius']}px;"
        if el.get("glow"):
            style += f"text-shadow:0 0 {el['glow'].get('radius', 10)}px {el['glow'].get('color', '#FFD700')};"

        html_el = f'<div class="element" id="{eid}" data-type="text" style="{style}">{content}</div>'

        # Animation
        anim = el.get("animation", {})
        anim_type = anim.get("type", "none") if isinstance(anim, dict) else anim
        if anim_type and anim_type != "none":
            css, js = _make_animation(eid, anim_type, start, end, anim if isinstance(anim, dict) else {})
        else:
            js = f"gsap.set('#{eid}', {{opacity: 1, display: 'flex'}});"

    elif el_type == "caption":
        content = html_mod.escape(el.get("content", ""))
        style_data = el.get("style", {})
        font = style_data.get("font", "Inter")
        size = style_data.get("size", 46)
        color = style_data.get("color", "#FFFFFF")
        align = style_data.get("align", "center")
        bg_color = style_data.get("bg_color", "rgba(0,0,0,0.7)")
        border_radius = style_data.get("border_radius", 12)
        box_style = style_data.get("box_style", "rounded")

        style += (f"font-family:'{font}';font-size:{size}px;color:{color};"
                  f"text-align:{align};background:{bg_color};"
                  f"border-radius:{border_radius}px;padding:12px 20px;")

        # Build word spans for highlighting
        words = el.get("words", [])
        if words:
            word_spans = " ".join(
                f'<span class="word" data-idx="{i}">{html_mod.escape(w.get("text", ""))}</span>'
                for i, w in enumerate(words)
            )
            html_el = (
                f'<div class="element" id="{eid}" data-type="caption" '
                f'data-words=\'{json.dumps(words, ensure_ascii=False)}\' '
                f'style="{style}">'
                f'<span class="caption-box {box_style}">{word_spans}</span>'
                f'</div>'
            )
        else:
            html_el = (
                f'<div class="element" id="{eid}" data-type="caption" '
                f'style="{style}">'
                f'<span class="caption-box {box_style}">{content}</span>'
                f'</div>'
            )

        # Caption fade-in
        css = f"#{eid} {{ opacity: 0; display: flex; }}"
        js = (
            f"gsap.fromTo('#{eid}', {{opacity: 0, y: 20}}, "
            f"{{opacity: 1, y: 0, duration: 0.3, ease: 'power2.out', "
            f"scrollTrigger: false}});\n"
            f"// Show during [{start}s - {end}s]\n"
            f"gsap.set('#{eid}', {{display: 'none'}});\n"
        )

    elif el_type == "image":
        src = el.get("src", "")
        if src and not src.startswith(("http://", "https://", "file:///")):
            src = "file:///" + os.path.abspath(src).replace("\\", "/")
        fit = el.get("fit", "cover")
        style += f"background-image:url('{src}');background-size:{fit};background-position:center;"
        if el.get("border_radius"):
            style += f"border-radius:{el['border_radius']}px;"
        html_el = f'<div class="element" id="{eid}" data-type="image" style="{style}"></div>'
        css = f"#{eid} {{ opacity: 0; }}"
        js = f"gsap.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: 0.5, ease: 'power2.out'}});"

    elif el_type == "shape":
        fill = el.get("fill", "#FFFFFF")
        stroke = el.get("stroke", "none")
        stroke_width = el.get("stroke_width", 0)
        border_radius = el.get("border_radius", 0)
        style += f"background:{fill};border:{stroke_width}px solid {stroke};border-radius:{border_radius}px;"
        html_el = f'<div class="element" id="{eid}" data-type="shape" style="{style}"></div>'
        css = f"#{eid} {{ opacity: 0; }}"
        js = f"gsap.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: 0.5}});"

    elif el_type == "svg":
        path_data = el.get("path", "")
        fill = el.get("fill", "#FFFFFF")
        style += f"background:transparent;"
        html_el = (
            f'<div class="element" id="{eid}" data-type="svg" style="{style}">'
            f'<svg viewBox="0 0 100 100" width="100%" height="100%">'
            f'<path d="{html_mod.escape(path_data)}" fill="{fill}"/></svg></div>'
        )
        css = f"#{eid} {{ opacity: 0; }}"
        js = f"gsap.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: 0.5}});"

    else:
        html_el = f'<div class="element" id="{eid}" data-type="{el_type}" style="{style}"></div>'

    return html_el, css, js


def _make_animation(eid: str, anim_type: str, start: float, end: float, anim_data: dict) -> tuple[str, str]:
    """Generate CSS + JS for a GSAP animation."""
    duration = anim_data.get("duration", 0.8) if isinstance(anim_data, dict) else 0.8
    delay = start
    css = f"#{eid} {{ opacity: 0; display: none; }}"

    animations = {
        "fade-in": f"gsap.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "fade-out": f"gsap.to('#{eid}', {{opacity: 0, duration: {duration}, delay: {delay}, ease: 'power2.in'}});",
        "slide-up": f"gsap.fromTo('#{eid}', {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "slide-down": f"gsap.fromTo('#{eid}', {{opacity: 0, y: -40}}, {{opacity: 1, y: 0, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "slide-left": f"gsap.fromTo('#{eid}', {{opacity: 0, x: 40}}, {{opacity: 1, x: 0, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "slide-right": f"gsap.fromTo('#{eid}', {{opacity: 0, x: -40}}, {{opacity: 1, x: 0, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "zoom-in": f"gsap.fromTo('#{eid}', {{opacity: 0, scale: 0.5}}, {{opacity: 1, scale: 1, duration: {duration}, delay: {delay}, ease: 'back.out(1.7)'}});",
        "zoom-out": f"gsap.fromTo('#{eid}', {{opacity: 0, scale: 1.5}}, {{opacity: 1, scale: 1, duration: {duration}, delay: {delay}, ease: 'power2.out'}});",
        "bounce": f"gsap.fromTo('#{eid}', {{opacity: 0, y: -30}}, {{opacity: 1, y: 0, duration: {duration}, delay: {delay}, ease: 'bounce.out'}});",
        "elastic": f"gsap.fromTo('#{eid}', {{opacity: 0, scaleX: 0}}, {{opacity: 1, scaleX: 1, duration: {duration}, delay: {delay}, ease: 'elastic.out(1, 0.3)'}});",
    }

    js = animations.get(anim_type, f"gsap.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: {duration}, delay: {delay}}});")
    return css, js


def _build_gsap_timeline(elements: list[dict], total_duration: float) -> str:
    """Build a GSAP timeline that sequences all elements."""
    lines = ["const tl = gsap.timeline({ paused: true });"]

    for el in elements:
        eid = f"el-{el.get('id', 'unknown')}"
        start = el.get("start", 0)
        end = el.get("end", start + 5)
        anim = el.get("animation", {})
        anim_type = anim.get("type", "none") if isinstance(anim, dict) else anim

        # Show/hide based on time
        lines.append(f"tl.set('#{eid}', {{display: 'flex'}}, {start});")
        lines.append(f"tl.set('#{eid}', {{display: 'none'}}, {end});")

        # Animation
        if anim_type and anim_type != "none":
            duration = anim.get("duration", 0.8) if isinstance(anim, dict) else 0.8
            if anim_type == "fade-in":
                lines.append(f"tl.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: {duration}}}, {start});")
            elif anim_type == "slide-up":
                lines.append(f"tl.fromTo('#{eid}', {{opacity: 0, y: 40}}, {{opacity: 1, y: 0, duration: {duration}}}, {start});")
            elif anim_type == "zoom-in":
                lines.append(f"tl.fromTo('#{eid}', {{opacity: 0, scale: 0.5}}, {{opacity: 1, scale: 1, duration: {duration}}}, {start});")
            else:
                lines.append(f"tl.fromTo('#{eid}', {{opacity: 0}}, {{opacity: 1, duration: {duration}}}, {start});")
        else:
            lines.append(f"tl.set('#{eid}', {{opacity: 1}}, {start});")

    return "\n".join(lines)


def _to_px(value, total: int) -> int:
    """Convert a value to pixels. Values > 100 are treated as pixels."""
    if isinstance(value, str):
        if value.endswith("%"):
            return int(float(value.rstrip("%")) / 100 * total)
        return int(float(value))
    if value > 100:
        return int(value)
    return int(value / 100 * total)
