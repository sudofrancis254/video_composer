#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py
=========
Local HTTP server for Video Composer.
Serves the frontend and provides API routes for project management,
scene editing, element manipulation, import, and rendering.

Port: 8768 (avoids 8765 Word Editor, 8766 Image Editor, 8767 Caption Studio)
"""

import os
import sys
import json
import time
import re
import subprocess
import shutil
import io
import urllib.parse
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project_store as ps
import import_service as ims
import scene_service as scs

PORT = 8768
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ---------------------------------------------------------------------------
# Event log
# ---------------------------------------------------------------------------

EVENT_LOG = os.path.join(BASE_DIR, "server-events.jsonl")


def _log_event(event: str, data: dict = None):
    entry = {"ts": time.time(), "event": event}
    if data:
        entry["data"] = data
    try:
        with open(EVENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class ComposerHandler(SimpleHTTPRequestHandler):
    """Handle API requests and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        path = self.path.split("?")[0]

        # API routes
        if path.startswith("/api/"):
            self._handle_api_get(path)
            return

        # Serve scene HTML preview
        if path.startswith("/preview/"):
            self._handle_preview(path)
            return

        # Serve audio files from project dirs
        if path.startswith("/audio/"):
            self._handle_audio(path)
            return

        # Serve uploaded images from project dirs
        if path.startswith("/images/"):
            self._handle_image(path)
            return

        # Default: serve static files
        super().do_GET()

    def do_POST(self):
        path = self.path.split("?")[0]
        # Event log endpoint (no /api/ prefix needed, but allow both)
        if path == "/api/log" or path == "/log":
            return self._handle_log()
        if not path.startswith("/api/"):
            self._json_response({"error": "POST only on /api/"}, 405)
            return
        self._handle_api_post(path)

    def do_PUT(self):
        path = self.path.split("?")[0]
        if not path.startswith("/api/"):
            self._json_response({"error": "PUT only on /api/"}, 405)
            return
        self._handle_api_put(path)

    def do_DELETE(self):
        path = self.path.split("?")[0]
        if not path.startswith("/api/"):
            self._json_response({"error": "DELETE only on /api/"}, 405)
            return
        self._handle_api_delete(path)

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    # -----------------------------------------------------------------------
    # GET handlers
    # -----------------------------------------------------------------------

    def _handle_api_get(self, path: str):
        _log_event("api_get", {"path": path})

        # Projects
        if path == "/api/projects":
            return self._json_response(ps.list_projects())

        # Import sources
        if path == "/api/import/audio-projects":
            return self._json_response(ims.list_word_editor_projects())
        if path == "/api/import/caption-projects":
            return self._json_response(ims.list_caption_editor_projects())

        # Project detail
        m = re.match(r"^/api/projects/([^/]+)$", path)
        if m:
            proj = ps.get_project(m.group(1))
            if proj:
                return self._json_response(proj)
            return self._json_response({"error": "not found"}, 404)

        # Scene list
        m = re.match(r"^/api/projects/([^/]+)/scenes$", path)
        if m:
            return self._json_response(ps.list_scenes(m.group(1)))

        # Scene detail
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)$", path)
        if m:
            scene = ps.get_scene(m.group(1), m.group(2))
            if scene:
                return self._json_response(scene)
            return self._json_response({"error": "not found"}, 404)

        # Word-level timestamps for a project
        m = re.match(r"^/api/projects/([^/]+)/words$", path)
        if m:
            return self._handle_words(m.group(1))

        # Alignment verification
        m = re.match(r"^/api/projects/([^/]+)/verify-alignment$", path)
        if m:
            return self._handle_verify_alignment(m.group(1))

        # Audio tracks
        m = re.match(r"^/api/projects/([^/]+)/audio-tracks$", path)
        if m:
            return self._handle_get_audio_tracks(m.group(1))

        # Render status
        m = re.match(r"^/api/render/([^/]+)/status$", path)
        if m:
            return self._json_response({"status": "idle"})

        self._json_response({"error": "not found"}, 404)

    # -----------------------------------------------------------------------
    # POST handlers
    # -----------------------------------------------------------------------

    def _handle_api_post(self, path: str):
        body = self._read_body()
        _log_event("api_post", {"path": path, "body_keys": list(body.keys()) if isinstance(body, dict) else []})

        # Event log endpoint
        if path == "/api/log":
            return self._handle_log()

        # Create project
        if path == "/api/projects":
            name = body.get("name", "Untitled")
            width = body.get("width", 1920)
            height = body.get("height", 1080)
            proj = ps.create_project(name, width, height)
            return self._json_response(proj, 201)

        # Import from Word Editor
        m = re.match(r"^/api/import/from-audio/([^/]+)$", path)
        if m:
            we_pid = m.group(1)
            vc_name = body.get("name", "")
            # Create a new project for this import
            proj = ps.create_project(vc_name or "Imported")
            vc_pid = proj["id"]
            scene = ims.import_from_word_editor(we_pid, vc_pid, vc_name)
            if "error" in scene:
                ps.delete_project(vc_pid)
                return self._json_response(scene, 400)
            # Add the scene
            ps.add_scene(vc_pid, scene)
            # Return the project with scenes
            full = ps.get_project(vc_pid)
            return self._json_response(full, 201)

        # Import captions from Caption Studio
        m = re.match(r"^/api/import/from-caption/([^/]+)$", path)
        if m:
            cs_pid = m.group(1)
            vc_pid = body.get("project_id", "")
            scene_id = body.get("scene_id")
            result = ims.import_captions_from_caption_editor(cs_pid, vc_pid, scene_id)
            if "error" in result:
                return self._json_response(result, 400)
            return self._json_response(result)

        # Add scene
        m = re.match(r"^/api/projects/([^/]+)/scenes$", path)
        if m:
            pid = m.group(1)
            scene = body
            result = ps.add_scene(pid, scene)
            if result:
                return self._json_response(result, 201)
            return self._json_response({"error": "project not found"}, 404)

        # Add element to scene
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)/elements$", path)
        if m:
            pid, sid = m.group(1), m.group(2)
            result = ps.add_element(pid, sid, body)
            if result:
                return self._json_response(result, 201)
            return self._json_response({"error": "scene not found"}, 404)

        # Upload image for a project
        m = re.match(r"^/api/projects/([^/]+)/upload-image$", path)
        if m:
            return self._handle_upload_image(m.group(1), body)

        # AI scene generation from word timestamps
        m = re.match(r"^/api/projects/([^/]+)/generate-scenes$", path)
        if m:
            return self._handle_generate_scenes(m.group(1), body)

        # Render
        m = re.match(r"^/api/render/([^/]+)$", path)
        if m:
            return self._handle_render(m.group(1), body)

        # Template create
        if path == "/api/templates":
            return self._json_response({"error": "templates not implemented yet"}, 501)

        self._json_response({"error": "not found"}, 404)

    # -----------------------------------------------------------------------
    # PUT handlers
    # -----------------------------------------------------------------------

    def _handle_api_put(self, path: str):
        body = self._read_body()
        _log_event("api_put", {"path": path})

        # Rename project
        if path.startswith("/api/projects/") and path.endswith("/rename"):
            m = re.match(r"^/api/projects/([^/]+)/rename$", path)
            if m:
                new_name = body.get("name", "")
                result = ps.rename_project(m.group(1), new_name)
                if result:
                    return self._json_response(result)
                return self._json_response({"error": "not found"}, 404)

        # Update project
        m = re.match(r"^/api/projects/([^/]+)$", path)
        if m:
            result = ps.update_project(m.group(1), body)
            if result:
                return self._json_response(result)
            return self._json_response({"error": "not found"}, 404)

        # Update scene
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)$", path)
        if m:
            result = ps.update_scene(m.group(1), m.group(2), body)
            if result:
                return self._json_response(result)
            return self._json_response({"error": "not found"}, 404)

        # Update element
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)/elements/([^/]+)$", path)
        if m:
            result = ps.update_element(m.group(1), m.group(2), m.group(3), body)
            if result:
                return self._json_response(result)
            return self._json_response({"error": "not found"}, 404)

        self._json_response({"error": "not found"}, 404)

    # -----------------------------------------------------------------------
    # DELETE handlers
    # -----------------------------------------------------------------------

    def _handle_api_delete(self, path: str):
        _log_event("api_delete", {"path": path})

        # Delete project
        m = re.match(r"^/api/projects/([^/]+)$", path)
        if m:
            if ps.delete_project(m.group(1)):
                return self._json_response({"ok": True})
            return self._json_response({"error": "not found"}, 404)

        # Delete scene
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)$", path)
        if m:
            if ps.delete_scene(m.group(1), m.group(2)):
                return self._json_response({"ok": True})
            return self._json_response({"error": "not found"}, 404)

        # Delete element
        m = re.match(r"^/api/projects/([^/]+)/scenes/([^/]+)/elements/([^/]+)$", path)
        if m:
            if ps.delete_element(m.group(1), m.group(2), m.group(3)):
                return self._json_response({"ok": True})
            return self._json_response({"error": "not found"}, 404)

        self._json_response({"error": "not found"}, 404)

    # -----------------------------------------------------------------------
    # Preview / Audio serving
    # -----------------------------------------------------------------------

    def _handle_preview(self, path: str):
        """Serve generated scene HTML for preview."""
        m = re.match(r"^/preview/([^/]+)/([^/]+)$", path)
        if not m:
            self._json_response({"error": "bad preview path"}, 400)
            return
        pid, sid = m.group(1), m.group(2)
        scene = ps.get_scene(pid, sid)
        if not scene:
            self._json_response({"error": "scene not found"}, 404)
            return
        html = scs.generate_scene_html(pid, scene)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._set_cors()
        data = html.encode("utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_audio(self, path: str):
        """Serve audio files with Range request support (required for seeking)."""
        m = re.match(r"^/audio/([^/]+)/(.+)$", path)
        if not m:
            self._json_response({"error": "bad audio path"}, 400)
            return
        pid, filename = m.group(1), m.group(2)
        search_dirs = [
            ps.fast_dir(pid),
            ps.WORD_EDITOR_FAST_DIR + '/' + pid,
            os.path.join(ps.WORD_EDITOR_FAST_DIR, pid),
            ps.project_dir(pid),
        ]
        fpath = None
        for d in search_dirs:
            candidate = os.path.join(d, filename)
            if os.path.isfile(candidate):
                fpath = candidate
                break
        if not fpath:
            self._json_response({"error": "audio not found"}, 404)
            return
        ct = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
        file_size = os.path.getsize(fpath)
        range_header = self.headers.get("Range")
        if range_header:
            # Parse Range: bytes=START-END
            rm = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if rm:
                start = int(rm.group(1))
                end = int(rm.group(2)) if rm.group(2) else file_size - 1
                end = min(end, file_size - 1)
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self._set_cors()
                self.end_headers()
                with open(fpath, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return
        # Full file (no Range header)
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self._set_cors()
        self.end_headers()
        with open(fpath, "rb") as f:
            self.wfile.write(f.read())

    def _handle_image(self, path: str):
        """Serve uploaded images from project directories."""
        m = re.match(r"^/images/([^/]+)/(.+)$", path)
        if not m:
            self._json_response({"error": "bad image path"}, 400)
            return
        pid, filename = m.group(1), m.group(2)
        # Security: prevent path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            self._json_response({"error": "invalid filename"}, 400)
            return
        images_dir = os.path.join(ps.project_dir(pid), "images")
        fpath = os.path.join(images_dir, filename)
        if not os.path.isfile(fpath):
            self._json_response({"error": "image not found"}, 404)
            return
        # Guess content type
        ext = os.path.splitext(filename)[1].lower()
        ct_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                  '.gif': 'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml'}
        ct = ct_map.get(ext, 'application/octet-stream')
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self._set_cors()
        with open(fpath, "rb") as f:
            data = f.read()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_upload_image(self, pid: str, body: dict):
        """Accept base64-encoded image data and save to project images dir."""
        import base64 as b64mod
        data_url = body.get("data", "")  # data:image/png;base64,...
        filename = body.get("filename", "upload.png")
        if not data_url:
            return self._json_response({"error": "no image data"}, 400)
        # Parse data URL
        if "," in data_url:
            header, encoded = data_url.split(",", 1)
        else:
            encoded = data_url
        # Sanitize filename
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        if not safe_name:
            safe_name = f"img_{int(time.time())}.png"
        images_dir = os.path.join(ps.project_dir(pid), "images")
        os.makedirs(images_dir, exist_ok=True)
        fpath = os.path.join(images_dir, safe_name)
        try:
            raw = b64mod.b64decode(encoded)
            with open(fpath, "wb") as f:
                f.write(raw)
        except Exception as e:
            return self._json_response({"error": f"decode failed: {e}"}, 400)
        url = f"/images/{pid}/{safe_name}"
        _log_event("image_uploaded", {"pid": pid, "filename": safe_name, "size": len(raw)})
        return self._json_response({"ok": True, "url": url, "filename": safe_name, "size": len(raw)})

    # -----------------------------------------------------------------------
    # AI Scene Generation from word timestamps
    # -----------------------------------------------------------------------

    def _handle_generate_scenes(self, pid: str, body: dict):
        """
        Generate scenes from word-level timestamps.
        Reads the words.json for this project, splits into scenes
        based on natural pause points, and creates timed visual elements.

        Body params:
          - words_per_scene: target words per scene (default: 80)
          - theme: 'tech', 'minimal', 'bold' (default: 'tech')
          - keep_existing: if true, keep existing scenes (default: false)
        """
        import import_service as ims_local

        project_dir = ps.project_dir(pid)
        meta = ps._read_json(os.path.join(project_dir, "meta.json")) or {}

        # Find words.json
        words_path = os.path.join(project_dir, "words.json")
        words = []
        if os.path.isfile(words_path):
            words = json.loads(open(words_path, encoding="utf-8").read())
        else:
            # Try to find from source project
            src_pid = meta.get("audio_source", "")
            if src_pid:
                src_words = os.path.join(ps.project_dir(src_pid), "words.json")
                if os.path.isfile(src_words):
                    words = json.loads(open(src_words, encoding="utf-8").read())
                    # Copy to this project
                    import shutil
                    shutil.copy2(src_words, words_path)

        if not words:
            return self._json_response({"error": "No word-level timestamps found. Import audio first."}, 400)

        words_per_scene = body.get("words_per_scene", 80)
        theme = body.get("theme", "tech")
        keep_existing = body.get("keep_existing", False)

        # Find the audio source BEFORE deleting scenes
        audio_track = None
        # Check existing scenes for audio
        for s in ps.list_scenes(pid):
            if s.get("audio_track", {}).get("source"):
                audio_track = s["audio_track"]
                break
        # If no audio in scenes, find it from the source project
        if not audio_track:
            src_pid = meta.get("audio_source", "")
            if src_pid:
                import import_service as ims_find
                we_projects = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "word_editor", "projects"
                )
                audio_path = ims_find._find_audio(
                    os.path.join(we_projects, src_pid), src_pid
                )
                if audio_path:
                    # Copy audio to this project's fast_dir
                    import shutil
                    vc_fast = ps.fast_dir(pid)
                    os.makedirs(vc_fast, exist_ok=True)
                    audio_dest = os.path.join(vc_fast, "source.mp3")
                    if not os.path.isfile(audio_dest):
                        shutil.copy2(audio_path, audio_dest)
                    audio_track = {
                        "source": audio_dest,
                        "duration": words[-1].get("end", 0) if words else 60,
                    }
        # If still no audio, try finding audio in this project's fast_dir
        if not audio_track:
            import glob as globmod
            for ext in ["*.mp3", "*.wav", "*.ogg", "*.m4a"]:
                matches = globmod.glob(os.path.join(ps.fast_dir(pid), ext))
                if matches:
                    audio_track = {
                        "source": matches[0],
                        "duration": words[-1].get("end", 0) if words else 60,
                    }
                    break

        # Delete existing scenes if not keeping
        if not keep_existing:
            for s in ps.list_scenes(pid):
                ps.delete_scene(pid, s["id"])

        # Split words into scenes at natural pause points
        scenes_data = _split_words_into_scenes(words, words_per_scene)

        # Theme palettes
        themes = {
            "tech": {
                "bg": "#0a0e14",
                "accent": "#4a9eff",
                "highlight": "#FFD700",
                "pattern": "bg-grid",
                "font": "Inter",
                "title_size": 72,
                "subtitle_size": 32,
            },
            "minimal": {
                "bg": "#f5f5f5",
                "accent": "#333333",
                "highlight": "#e74c3c",
                "pattern": None,
                "font": "Inter",
                "title_size": 64,
                "subtitle_size": 28,
            },
            "bold": {
                "bg": "#1a1a2e",
                "accent": "#e94560",
                "highlight": "#0f3460",
                "pattern": "bg-dots",
                "font": "Inter",
                "title_size": 80,
                "subtitle_size": 36,
            },
        }
        t = themes.get(theme, themes["tech"])

        total_duration = words[-1].get("end", 0) if words else 60
        scenes_created = []

        for i, scene_words in enumerate(scenes_data):
            if not scene_words:
                continue

            scene_start = scene_words[0].get("start", 0)
            scene_end = scene_words[-1].get("end", scene_start + 5)
            scene_duration = round(scene_end - scene_start + 0.5, 1)

            # Build caption elements from word groups (3-6 words each)
            captions = _build_captions_from_words(scene_words, scene_start)

            # Build visual elements based on content analysis
            visuals = _generate_visuals_for_scene(
                scene_words, i, len(scenes_data),
                scene_start, scene_end, t
            )

            scene = {
                "id": "scene_" + ps._new_id(),
                "name": _generate_scene_name(scene_words, i, len(scenes_data)),
                "duration": scene_duration,
                "bg_color": t["bg"],
                "bg_pattern": t["pattern"],
                "audio_track": audio_track,
                "elements": captions + visuals,
            }

            ps.add_scene(pid, scene)
            scenes_created.append({
                "name": scene["name"],
                "duration": scene_duration,
                "element_count": len(scene["elements"]),
                "word_range": f"{scene_words[0].get('text', '')} ... {scene_words[-1].get('text', '')}"
            })

        _log_event("scenes_generated", {
            "pid": pid, "count": len(scenes_created), "theme": theme
        })

        return self._json_response({
            "ok": True,
            "scenes": scenes_created,
            "total_duration": round(total_duration, 1),
            "total_elements": sum(s["element_count"] for s in scenes_created),
        })

    # -----------------------------------------------------------------------
    # Render
    # -----------------------------------------------------------------------

    def _handle_render(self, pid: str, body: dict):
        """Render a project to MP4."""
        scenes = ps.list_scenes(pid)
        if not scenes:
            return self._json_response({"error": "no scenes"}, 400)

        meta = ps._read_json(os.path.join(ps.project_dir(pid), "meta.json")) or {}
        width = meta.get("width", 1920)
        height = meta.get("height", 1080)

        # Generate composition HTML
        comp_dir = ps.composition_dir(pid)
        comp_html = scs.generate_composition_html(pid, scenes)
        comp_path = os.path.join(comp_dir, "composition.html")
        with open(comp_path, "w", encoding="utf-8") as f:
            f.write(comp_html)

        # Try HyperFrames if available, else ffmpeg
        output_dir = ps.output_dir(pid)
        output_path = os.path.join(output_dir, "output.mp4")

        try:
            result = subprocess.run(
                ["npx", "hyperframes", "render",
                 "--composition", comp_path,
                 "--output", output_path,
                 "--width", str(width),
                 "--height", str(height)],
                capture_output=True, text=True, timeout=600,
                cwd=BASE_DIR
            )
            if result.returncode == 0:
                return self._json_response({
                    "ok": True,
                    "output": output_path,
                    "message": "Rendered via HyperFrames"
                })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Fallback: just save the HTML
        return self._json_response({
            "ok": True,
            "composition": comp_path,
            "message": "HTML composition generated. Install HyperFrames for MP4 rendering.",
            "note": "Open composition.html in a browser to preview."
        })

    # -----------------------------------------------------------------------
    # Word-level timestamps + alignment verification
    # -----------------------------------------------------------------------

    def _handle_words(self, pid: str):
        """Return word-level timestamps for a project."""
        project_dir = ps.project_dir(pid)
        words_path = os.path.join(project_dir, "words.json")
        if not os.path.isfile(words_path):
            # Try to copy from source project
            meta = ps._read_json(os.path.join(project_dir, "meta.json")) or {}
            src = meta.get("audio_source", "")
            if src:
                # Handle both Windows paths and project IDs
                if os.sep in src or ':' in src:
                    src_pid = src.split(os.sep)[-2] if os.sep in src else src
                    src_dir = ps.project_dir(src_pid) if not os.path.isdir(src) else src
                else:
                    src_pid = src
                    src_dir = ps.project_dir(src_pid)
                src_words = os.path.join(src_dir, "words.json") if os.path.isdir(src_dir) else None
                if src_words and os.path.isfile(src_words):
                    import shutil
                    shutil.copy2(src_words, words_path)
        if os.path.isfile(words_path):
            words = json.loads(open(words_path, encoding="utf-8").read())
            return self._json_response(words)
        return self._json_response([])

    def _handle_verify_alignment(self, pid: str):
        """Verify element timing against word timestamps."""
        project_dir = ps.project_dir(pid)
        words_path = os.path.join(project_dir, "words.json")
        if not os.path.isfile(words_path):
            return self._json_response({"error": "No words.json found"}, 400)
        words = json.loads(open(words_path, encoding="utf-8").read())
        scenes = ps.list_scenes(pid)
        if not scenes:
            return self._json_response({"error": "No scenes found"}, 400)

        # Inline verification logic
        issues = []
        aligned = 0
        total = 0
        covered = set()
        offset = 0
        for scene in scenes:
            for el in scene.get("elements", []):
                total += 1
                if el.get("wordRef") and el["wordRef"].get("startWord") is not None:
                    sw, ew = el["wordRef"]["startWord"], el["wordRef"]["wordEnd"]
                    if 0 <= sw < len(words) and 0 <= ew < len(words):
                        expected_s = words[sw]["start"] - offset
                        expected_e = words[ew]["end"] - offset
                        if abs((el.get("start", 0)) - expected_s) < 0.1 and abs((el.get("end", 0)) - expected_e) < 0.1:
                            aligned += 1
                        else:
                            issues.append({"el": el.get("id", "?")[:8], "content": (el.get("content", "") or "")[:30]})
                        for i in range(sw, ew + 1):
                            covered.add(i)
            offset += scene.get("duration", 10)

        return self._json_response({
            "totalElements": total,
            "aligned": aligned,
            "misaligned": len(issues),
            "issues": issues[:20],
            "coveragePercent": round(len(covered) / len(words) * 100, 1) if words else 0,
            "wordsTotal": len(words),
            "wordsCovered": len(covered)
        })

    def _handle_get_audio_tracks(self, pid: str):
        """Get audio tracks for a project."""
        meta = ps._read_json(os.path.join(ps.project_dir(pid), "meta.json")) or {}
        tracks = meta.get("audioTracks", [])
        return self._json_response(tracks)

    # -----------------------------------------------------------------------
    # Event log handler
    # -----------------------------------------------------------------------

    def _handle_log(self):
        """Accept batched UI event logs from the frontend."""
        body = self._read_body()
        events = body.get("events", [])
        if events:
            _log_event("ui_batch", {"count": len(events)})
            # Write each event to the log file
            try:
                log_path = os.path.join(BASE_DIR, "ui-events.jsonl")
                with open(log_path, "a", encoding="utf-8") as f:
                    for ev in events:
                        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            except Exception:
                pass
        self._json_response({"ok": True})

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def guess_type(self, path):
        """Override to add no-cache headers for all static files."""
        return super().guess_type(path)

    def send_head(self):
        """Override to add Cache-Control: no-cache for static files."""
        response = super().send_head()
        if response and hasattr(response, 'headers'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Scene generation helpers
# ---------------------------------------------------------------------------


def _split_words_into_scenes(words: list, target_per_scene: int) -> list[list]:
    """Split word list into scenes at natural pause points.
    
    Groups words into scenes of roughly `target_per_scene` words,
    breaking at natural pauses (gaps > 0.8s between words).
    """
    if not words:
        return []

    scenes = []
    current = []

    for i, w in enumerate(words):
        text = w.get("text", "").strip()
        if not text:
            continue
        current.append(w)

        # Check for natural break
        is_break = False
        if i + 1 < len(words):
            gap = words[i + 1].get("start", 0) - w.get("end", 0)
            if gap > 0.8:
                is_break = True

        is_full = len(current) >= target_per_scene

        if (is_break and len(current) >= 20) or (is_full and is_break):
            scenes.append(current)
            current = []
        elif is_full and not is_break:
            # Force split at target
            scenes.append(current)
            current = []

    if current:
        scenes.append(current)

    return scenes


def _build_captions_from_words(words: list, scene_start: float) -> list:
    """Build caption elements from words, grouped into 4-8 word chunks."""
    captions = []
    group = []
    group_start = None

    for w in words:
        text = w.get("text", "").strip()
        if not text:
            continue
        start = w.get("start", 0)
        end = w.get("end", 0)

        if group_start is None:
            group_start = start
        group.append(w)

        # Check for break: gap > 0.4s or 6 words
        next_start = None
        idx = words.index(w)
        if idx + 1 < len(words):
            next_start = words[idx + 1].get("start", 0)
        gap = (next_start - end) if next_start else 999

        if gap > 0.4 or len(group) >= 6:
            text_content = " ".join(cw.get("text", "") for cw in group)
            # Find word indices for this group in the full words list
            group_word_start = None
            group_word_end = None
            for wi, ww in enumerate(words):
                if ww is group[0]:
                    group_word_start = wi
                if ww is group[-1]:
                    group_word_end = wi
            captions.append({
                "id": "el_" + ps._new_id(),
                "type": "caption",
                "content": text_content,
                "x": 5, "y": 80, "width": 90, "height": 15,
                "start": round(group_start - scene_start, 3),
                "end": round(end - scene_start + 0.1, 3),
                "wordRef": {"startWord": group_word_start, "wordEnd": group_word_end},
                "words": [
                    {"text": cw.get("text", ""),
                     "start": round(cw.get("start", 0) - scene_start, 3),
                     "end": round(cw.get("end", 0) - scene_start, 3)}
                    for cw in group
                ],
                "style": {
                    "font": "Inter", "size": 46, "color": "#FFFFFF",
                    "highlight": "#FFD700",
                    "bg_color": "rgba(0,0,0,0.7)",
                    "border_radius": 12, "align": "center",
                },
            })
            group = []
            group_start = None

    # Flush remaining
    if group:
        text_content = " ".join(cw.get("text", "") for cw in group)
        group_word_start = None
        group_word_end = None
        for wi, ww in enumerate(words):
            if ww is group[0]:
                group_word_start = wi
            if ww is group[-1]:
                group_word_end = wi
        captions.append({
            "id": "el_" + ps._new_id(),
            "type": "caption",
            "content": text_content,
            "x": 5, "y": 80, "width": 90, "height": 15,
            "start": round((group_start or 0) - scene_start, 3),
            "end": round(group[-1].get("end", 0) - scene_start + 0.1, 3),
            "wordRef": {"startWord": group_word_start, "wordEnd": group_word_end},
            "words": [
                {"text": cw.get("text", ""),
                 "start": round(cw.get("start", 0) - scene_start, 3),
                 "end": round(cw.get("end", 0) - scene_start, 3)}
                for cw in group
            ],
            "style": {
                "font": "Inter", "size": 46, "color": "#FFFFFF",
                "highlight": "#FFD700",
                "bg_color": "rgba(0,0,0,0.7)",
                "border_radius": 12, "align": "center",
            },
        })

    return captions


def _generate_visuals_for_scene(
    words: list, scene_idx: int, total_scenes: int,
    scene_start: float, scene_end: float, theme: dict
) -> list:
    """Generate timed visual elements (text, shapes) for a scene.
    
    Key principle: ALL visuals are timed to exact word timestamps.
    The AI reads the words being spoken and places elements at the
    precise moments they should appear.
    """
    visuals = []
    scene_duration = scene_end - scene_start
    accent = theme["accent"]
    highlight = theme["highlight"]

    # === Scene title — appears with first 2-3 words ===
    title_words = " ".join(w.get("text", "") for w in words[:3]).upper()
    first_word_start = words[0].get("start", scene_start) - scene_start if words else 0
    title_end = min(scene_duration, 5)  # title shows for up to 5s

    # Don't add title for first scene (it's the hook)
    if scene_idx > 0 and len(words) >= 2:
        # Find absolute word indices for first 3 words
        title_word_end_idx = min(2, len(words) - 1)
        title_abs_end = words[title_word_end_idx].get("end", scene_end) - scene_start
        visuals.append({
            "id": "el_" + ps._new_id(),
            "type": "text",
            "content": title_words,
            "x": 8, "y": 4, "width": 84, "height": 10,
            "font": theme["font"], "size": theme["title_size"],
            "color": accent, "weight": "bold", "align": "center",
            "start": round(first_word_start, 3),
            "end": round(min(title_end, title_abs_end + 1.0), 3),
            "wordRef": {"startWord": 0, "wordEnd": title_word_end_idx},
            "bg_color": f"{accent}11",
            "border_radius": 12,
            "animation": {"type": "bounce", "duration": 0.7},
        })

    # === Accent line — timed to first sentence ===
    # Find where first sentence ends (gap > 1s)
    first_sentence_end = scene_duration * 0.4  # default 40% of scene
    for i, w in enumerate(words):
        if i + 1 < len(words):
            gap = words[i + 1].get("start", 0) - w.get("end", 0)
            if gap > 1.0:
                first_sentence_end = w.get("end", 0) - scene_start + 0.5
                break

    visuals.append({
        "id": "el_" + ps._new_id(),
        "type": "shape", "shape": "line",
        "x": 8, "y": 16, "width": 84, "height": 1,
        "fill": f"{accent}66", "stroke_width": 2,
        "start": round(first_word_start + 0.3, 3),
        "end": round(scene_duration, 3),
        "animation": {"type": "fade-in", "duration": 0.4},
    })

    # === Key phrase highlights — find important moments ===
    # Look for natural emphasis points: long words, capitalized, or at sentence starts
    emphasis_points = []
    for i, w in enumerate(words):
        text = w.get("text", "")
        # Sentence start (after a long gap)
        if i > 0:
            gap = w.get("start", 0) - words[i - 1].get("end", 0)
            if gap > 0.6:
                emphasis_points.append((i, "sentence_start"))
        # Long words (> 6 chars) are often key terms
        if len(text) > 6 and i % 8 == 0:
            emphasis_points.append((i, "key_term"))

    # Add decorative elements at emphasis points (max 3 per scene)
    for idx, (word_idx, reason) in enumerate(emphasis_points[:3]):
        if word_idx >= len(words):
            continue
        w = words[word_idx]
        el_start = w.get("start", 0) - scene_start

        # Position varies based on index
        positions = [
            (85, 8, 4),   # top-right circle
            (2, 70, 3),   # bottom-left circle
            (88, 65, 5),  # bottom-right circle
        ]
        px, py, ps_size = positions[idx % 3]

        visuals.append({
            "id": "el_" + ps._new_id(),
            "type": "shape", "shape": "circle",
            "x": px, "y": py, "width": ps_size, "height": ps_size,
            "fill": f"{accent}20",
            "start": round(el_start, 3),
            "end": round(scene_duration, 3),
            "animation": {"type": "fade-in", "duration": 0.5},
        })

    # === Bottom accent bar — entire scene ===
    visuals.append({
        "id": "el_" + ps._new_id(),
        "type": "shape", "shape": "rect",
        "x": 0, "y": 98, "width": 100, "height": 2,
        "fill": accent,
        "start": 0, "end": round(scene_duration, 3),
    })

    return visuals


def _generate_scene_name(words: list, idx: int, total: int) -> str:
    """Generate a descriptive scene name from the words spoken."""
    if not words:
        return f"Scene {idx + 1}"
    # Use first 3 words
    first_words = " ".join(w.get("text", "") for w in words[:3])
    if idx == 0:
        return f"Opening — {first_words}..."
    if idx == total - 1:
        return f"Closing — {first_words}..."
    return f"Scene {idx + 1} — {first_words}..."


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ps._ensure_dirs()
    _log_event("server_start", {"port": PORT})
    server = HTTPServer(("127.0.0.1", PORT), ComposerHandler)
    print(f"Video Composer running at http://127.0.0.1:{PORT}")
    print(f"Projects dir: {ps.PROJECTS_DIR}")
    print(f"Fast dir: {ps.FAST_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log_event("server_stop")
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
