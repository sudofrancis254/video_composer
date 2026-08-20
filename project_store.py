#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_store.py
================
Project management for Video Composer.
Handles project CRUD, scene CRUD, FAST_DIR for heavy media,
and project metadata.
"""

import os
import json
import shutil
import time
import uuid
import re
import sys

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
COMPOSITIONS_DIR = os.path.join(BASE_DIR, "compositions")
PACKAGES_DIR = os.path.join(BASE_DIR, "packages")

# FAST_DIR: heavy media (audio, rendered frames) lives here — off OneDrive
_default_fast = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "VideoComposerWork",
)
FAST_DIR = os.environ.get("VIDEO_COMPOSER_FAST_DIR", _default_fast)

# Word Editor fast dir (for importing audio)
_wd_default_fast = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "WordEditorWork",
)
WORD_EDITOR_FAST_DIR = os.environ.get("WORD_EDITOR_FAST_DIR", _wd_default_fast)


def _ensure_dirs():
    for d in [PROJECTS_DIR, TEMPLATES_DIR, COMPOSITIONS_DIR, PACKAGES_DIR, FAST_DIR]:
        os.makedirs(d, exist_ok=True)


def _new_id():
    return uuid.uuid4().hex[:12]


def _sanitize_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("_. ")
    return name[:80] or "Untitled"


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def list_projects() -> list[dict]:
    _ensure_dirs()
    projects = []
    for pid in sorted(os.listdir(PROJECTS_DIR)):
        pdir = os.path.join(PROJECTS_DIR, pid)
        if not os.path.isdir(pdir):
            continue
        meta = _read_json(os.path.join(pdir, "meta.json"))
        if meta:
            meta["id"] = pid
            projects.append(meta)
    return projects


def get_project(pid: str) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    meta = _read_json(os.path.join(pdir, "meta.json"))
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    timeline = _read_json(os.path.join(pdir, "timeline.json")) or {}
    if meta:
        meta["id"] = pid
        meta["scenes"] = scenes
        meta["timeline"] = timeline
    return meta


def create_project(name: str, width: int = 1920, height: int = 1080) -> dict:
    _ensure_dirs()
    pid = _new_id()
    pdir = os.path.join(PROJECTS_DIR, pid)
    os.makedirs(pdir, exist_ok=True)

    # Create fast-dir for this project's heavy media
    fast_pdir = os.path.join(FAST_DIR, pid)
    os.makedirs(fast_pdir, exist_ok=True)

    meta = {
        "name": _sanitize_name(name),
        "width": width,
        "height": height,
        "created": time.time(),
        "modified": time.time(),
        "fast_dir": fast_pdir,
        "audio_source": None,  # set when importing from Word Editor
        "scenes": [],
    }
    _write_json(os.path.join(pdir, "meta.json"), meta)
    _write_json(os.path.join(pdir, "scenes.json"), [])
    _write_json(os.path.join(pdir, "timeline.json"), {})

    meta["id"] = pid
    return meta


def update_project(pid: str, updates: dict) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    meta = _read_json(os.path.join(pdir, "meta.json")) or {}
    meta.update(updates)
    meta["modified"] = time.time()
    _write_json(os.path.join(pdir, "meta.json"), meta)
    meta["id"] = pid
    return meta


def rename_project(pid: str, new_name: str) -> dict | None:
    return update_project(pid, {"name": _sanitize_name(new_name)})


def delete_project(pid: str) -> bool:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return False
    shutil.rmtree(pdir, ignore_errors=True)
    # Also clean fast-dir
    fast_pdir = os.path.join(FAST_DIR, pid)
    if os.path.isdir(fast_pdir):
        shutil.rmtree(fast_pdir, ignore_errors=True)
    return True


# ---------------------------------------------------------------------------
# Scene CRUD
# ---------------------------------------------------------------------------

def list_scenes(pid: str) -> list[dict]:
    pdir = os.path.join(PROJECTS_DIR, pid)
    return _read_json(os.path.join(pdir, "scenes.json")) or []


def get_scene(pid: str, sid: str) -> dict | None:
    scenes = list_scenes(pid)
    for s in scenes:
        if s.get("id") == sid:
            return s
    return None


def add_scene(pid: str, scene: dict) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    if not scene.get("id"):
        scene["id"] = "scene_" + _new_id()
    if not scene.get("name"):
        scene["name"] = f"Scene {len(scenes) + 1}"
    if not scene.get("duration"):
        scene["duration"] = 10.0
    if not scene.get("elements"):
        scene["elements"] = []
    scenes.append(scene)
    _write_json(os.path.join(pdir, "scenes.json"), scenes)
    return scene


def update_scene(pid: str, sid: str, updates: dict) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    for i, s in enumerate(scenes):
        if s.get("id") == sid:
            scenes[i].update(updates)
            scenes[i]["id"] = sid  # protect id
            _write_json(os.path.join(pdir, "scenes.json"), scenes)
            return scenes[i]
    return None


def delete_scene(pid: str, sid: str) -> bool:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return False
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    scenes = [s for s in scenes if s.get("id") != sid]
    _write_json(os.path.join(pdir, "scenes.json"), scenes)
    return True


def reorder_scenes(pid: str, scene_ids: list[str]) -> bool:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return False
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    id_map = {s["id"]: s for s in scenes}
    reordered = [id_map[sid] for sid in scene_ids if sid in id_map]
    # Add any scenes not in the new order at the end
    seen = set(scene_ids)
    for s in scenes:
        if s["id"] not in seen:
            reordered.append(s)
    _write_json(os.path.join(pdir, "scenes.json"), reordered)
    return True


# ---------------------------------------------------------------------------
# Element CRUD (within a scene)
# ---------------------------------------------------------------------------

def add_element(pid: str, sid: str, element: dict) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    for s in scenes:
        if s.get("id") == sid:
            if not element.get("id"):
                element["id"] = "el_" + _new_id()
            s.setdefault("elements", []).append(element)
            _write_json(os.path.join(pdir, "scenes.json"), scenes)
            return element
    return None


def update_element(pid: str, sid: str, eid: str, updates: dict) -> dict | None:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return None
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    for s in scenes:
        if s.get("id") == sid:
            for el in s.get("elements", []):
                if el.get("id") == eid:
                    el.update(updates)
                    el["id"] = eid
                    _write_json(os.path.join(pdir, "scenes.json"), scenes)
                    return el
    return None


def delete_element(pid: str, sid: str, eid: str) -> bool:
    pdir = os.path.join(PROJECTS_DIR, pid)
    if not os.path.isdir(pdir):
        return False
    scenes = _read_json(os.path.join(pdir, "scenes.json")) or []
    for s in scenes:
        if s.get("id") == sid:
            before = len(s.get("elements", []))
            s["elements"] = [e for e in s.get("elements", []) if e.get("id") != eid]
            if len(s["elements"]) < before:
                _write_json(os.path.join(pdir, "scenes.json"), scenes)
                return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def project_dir(pid: str) -> str:
    return os.path.join(PROJECTS_DIR, pid)


def fast_dir(pid: str) -> str:
    d = os.path.join(FAST_DIR, pid)
    os.makedirs(d, exist_ok=True)
    return d


def media_dir(pid: str) -> str:
    d = os.path.join(PROJECTS_DIR, pid, "media")
    os.makedirs(d, exist_ok=True)
    return d


def output_dir(pid: str) -> str:
    d = os.path.join(PROJECTS_DIR, pid, "output")
    os.makedirs(d, exist_ok=True)
    return d


def composition_dir(pid: str) -> str:
    d = os.path.join(COMPOSITIONS_DIR, pid)
    os.makedirs(d, exist_ok=True)
    return d


def _read_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
