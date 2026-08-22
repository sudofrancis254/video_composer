#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_alignment.py
===================
Verifies that visual elements in scenes.json are properly aligned
with word-level timestamps in words.json.

Usage:
    python verify_alignment.py <project_id>
    python verify_alignment.py cd7824dc202a

Exit codes:
    0 = all aligned
    1 = misalignments found
    2 = missing files
"""

import json
import os
import sys
import re
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")


def load_words(project_id):
    """Load words.json for a project."""
    path = os.path.join(PROJECTS_DIR, project_id, "words.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_scenes(project_id):
    """Load scenes.json for a project."""
    path = os.path.join(PROJECTS_DIR, project_id, "scenes.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def word_at_time(words, time):
    """Find the word index closest to a given time."""
    best_idx = 0
    best_dist = float("inf")
    for i, w in enumerate(words):
        dist = abs(w["start"] - time)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def get_words_in_range(words, start_idx, end_idx):
    """Get text of words in a range."""
    return " ".join(w["text"] for w in words[start_idx:end_idx + 1] if w["start"] is not None)


def verify_alignment(project_id):
    """Main verification function."""
    words = load_words(project_id)
    scenes = load_scenes(project_id)

    if not words:
        print(f"ERROR: words.json not found for project {project_id}")
        return 2
    if not scenes:
        print(f"ERROR: scenes.json not found for project {project_id}")
        return 2

    print(f"\n{'='*70}")
    print(f"  ALIGNMENT VERIFICATION: {project_id}")
    print(f"  Words: {len(words)}  |  Scenes: {len(scenes)}")
    print(f"{'='*70}\n")

    issues = []
    aligned = 0
    total_elements = 0
    words_covered = set()

    # Track scene time offsets
    scene_offset = 0

    for scene_idx, scene in enumerate(scenes):
        scene_name = scene.get("name", f"Scene {scene_idx + 1}")
        scene_dur = scene.get("duration", 10)
        elements = scene.get("elements", [])

        # Check scene word range if defined
        if scene.get("wordStart") is not None and scene.get("wordEnd") is not None:
            ws = scene["wordStart"]
            we = scene["wordEnd"]
            if ws >= len(words) or we >= len(words):
                issues.append({
                    "level": "ERROR",
                    "scene": scene_name,
                    "message": f"Scene word range [{ws}-{we}] exceeds words count ({len(words)})"
                })
            else:
                expected_dur = words[we]["end"] - words[ws]["start"]
                diff = abs(scene_dur - expected_dur)
                if diff > 0.5:
                    issues.append({
                        "level": "WARNING",
                        "scene": scene_name,
                        "message": f"Scene duration {scene_dur:.2f}s differs from word range {expected_dur:.2f}s (diff: {diff:.2f}s)"
                    })
                # Track words covered
                for i in range(ws, we + 1):
                    words_covered.add(i)

        for el in elements:
            total_elements += 1
            el_id = el.get("id", "?")[:8]
            el_type = el.get("type", "?")
            content = (el.get("content", "") or "")[:40]

            # Check wordRef-based elements
            if el.get("wordRef") and el["wordRef"].get("startWord") is not None:
                wr = el["wordRef"]
                sw, ew = wr["startWord"], wr["wordEnd"]

                if sw >= len(words) or ew >= len(words):
                    issues.append({
                        "level": "ERROR",
                        "scene": scene_name,
                        "element": el_id,
                        "message": f"wordRef [{sw}-{ew}] out of range (words: {len(words)})"
                    })
                    continue

                expected_start = words[sw]["start"] - scene_offset
                expected_end = words[ew]["end"] - scene_offset
                actual_start = el.get("start", 0)
                actual_end = el.get("end", 0)

                start_diff = abs(actual_start - expected_start)
                end_diff = abs(actual_end - expected_end)

                if start_diff < 0.1 and end_diff < 0.1:
                    aligned += 1
                else:
                    issues.append({
                        "level": "MISALIGNED",
                        "scene": scene_name,
                        "element": el_id,
                        "type": el_type,
                        "content": content,
                        "message": f"Timing off by {start_diff:.3f}s (start) / {end_diff:.3f}s (end)",
                        "expected": {"start": round(expected_start, 3), "end": round(expected_end, 3)},
                        "actual": {"start": actual_start, "end": actual_end},
                        "words": get_words_in_range(words, sw, ew)
                    })

                for i in range(sw, ew + 1):
                    words_covered.add(i)

            # Check time-based elements
            elif el.get("start") is not None and el.get("end") is not None:
                abs_start = el["start"] + scene_offset
                abs_end = el["end"] + scene_offset

                start_word = word_at_time(words, abs_start)
                end_word = word_at_time(words, abs_end)

                word_start_time = words[start_word]["start"]
                word_end_time = words[end_word]["end"]

                start_drift = abs(abs_start - word_start_time)
                end_drift = abs(abs_end - word_end_time)

                if start_drift < 0.2 and end_drift < 0.2:
                    aligned += 1
                else:
                    issues.append({
                        "level": "DRIFT",
                        "scene": scene_name,
                        "element": el_id,
                        "type": el_type,
                        "content": content,
                        "message": f"Drift: {start_drift:.3f}s (start) / {end_drift:.3f}s (end) from nearest word",
                        "nearest_word_range": f"{start_word}-{end_word}",
                        "nearest_words": get_words_in_range(words, start_word, end_word)
                    })

        scene_offset += scene_dur

    # Check for coverage gaps
    coverage = len(words_covered) / len(words) * 100 if words else 0
    uncovered_words = []
    for i in range(len(words)):
        if i not in words_covered:
            uncovered_words.append(i)

    # Find uncovered ranges
    gap_ranges = []
    if uncovered_words:
        gap_start = uncovered_words[0]
        gap_end = uncovered_words[0]
        for i in uncovered_words[1:]:
            if i == gap_end + 1:
                gap_end = i
            else:
                gap_ranges.append((gap_start, gap_end))
                gap_start = i
                gap_end = i
        gap_ranges.append((gap_start, gap_end))

    # Print results
    print(f"  {'ALIGNED':<12}: {aligned}/{total_elements} elements")
    print(f"  {'COVERAGE':<12}: {coverage:.1f}% ({len(words_covered)}/{len(words)} words)")
    print()

    if not issues and not gap_ranges:
        print("  ✅ ALL ELEMENTS PROPERLY ALIGNED")
        print()
        return 0

    # Print issues
    errors = [i for i in issues if i["level"] in ("ERROR", "MISALIGNED")]
    warnings = [i for i in issues if i["level"] in ("WARNING", "DRIFT")]

    if errors:
        print(f"  ❌ {len(errors)} alignment errors:")
        print(f"  {'-'*60}")
        for issue in errors:
            print(f"  [{issue['level']}] {issue['scene']} / {issue.get('element', '?')}")
            print(f"    {issue['message']}")
            if issue.get("expected"):
                print(f"    Expected: {issue['expected']}")
                print(f"    Actual:   {issue['actual']}")
            if issue.get("words"):
                print(f"    Words:    \"{issue['words']}\"")
            print()

    if warnings:
        print(f"  ⚠️  {len(warnings)} warnings:")
        print(f"  {'-'*60}")
        for issue in warnings:
            print(f"  [{issue['level']}] {issue['scene']} / {issue.get('element', '?')}")
            print(f"    {issue['message']}")
            if issue.get("nearest_words"):
                print(f"    Nearest:  \"{issue['nearest_words']}\"")
            print()

    if gap_ranges:
        print(f"  🔴 {len(gap_ranges)} uncovered word range(s):")
        print(f"  {'-'*60}")
        for gs, ge in gap_ranges:
            text = get_words_in_range(words, gs, ge)
            t_start = words[gs]["start"]
            t_end = words[ge]["end"]
            print(f"    [{gs}-{ge}] ({t_start:.2f}s - {t_end:.2f}s): \"{text}\"")
        print()

    return 1 if errors else 0


def fix_alignment(project_id):
    """Auto-fix alignment issues by reassigning wordRefs."""
    words = load_words(project_id)
    scenes = load_scenes(project_id)

    if not words or not scenes:
        print("Cannot fix: missing files")
        return

    fixed = 0
    scene_offset = 0

    for scene in scenes:
        scene_dur = scene.get("duration", 10)

        for el in scene.get("elements", []):
            if el.get("start") is not None and el.get("end") is not None:
                abs_start = el["start"] + scene_offset
                abs_end = el["end"] + scene_offset

                sw = word_at_time(words, abs_start)
                ew = word_at_time(words, abs_end)

                el["wordRef"] = {"startWord": sw, "wordEnd": ew}

                # Adjust timing to match words exactly
                el["start"] = words[sw]["start"] - scene_offset
                el["end"] = words[ew]["end"] - scene_offset

                fixed += 1

        scene_offset += scene_dur

    # Save fixed scenes
    path = os.path.join(PROJECTS_DIR, project_id, "scenes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)

    print(f"Fixed {fixed} elements in {project_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_alignment.py <project_id>")
        print("       python verify_alignment.py <project_id> --fix")
        sys.exit(1)

    project_id = sys.argv[1]
    fix_mode = "--fix" in sys.argv

    if fix_mode:
        fix_alignment(project_id)
    else:
        code = verify_alignment(project_id)
        sys.exit(code)
