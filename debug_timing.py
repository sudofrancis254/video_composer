#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug scene timing and element visibility during playback."""
import json, sys

import os
base = os.path.dirname(os.path.abspath(__file__))
scenes = json.load(open(os.path.join(base, "projects/cd7824dc202a/scenes.json"), encoding="utf-8"))
words = json.load(open(os.path.join(base, "projects/cd7824dc202a/words.json"), encoding="utf-8"))
words = [w for w in words if w.get("text","").strip()]

print("=== SCENE TIMING ===")
offset = 0
for i, s in enumerate(scenes):
    dur = s.get("duration", 10)
    print(f"\nScene {i}: '{s['name']}'")
    print(f"  Duration: {dur:.2f}s")
    print(f"  Absolute window: {offset:.2f}s - {offset+dur:.2f}s")
    print(f"  Elements: {len(s.get('elements',[]))}")
    
    # Show element types and absolute timing
    for e in s.get("elements", []):
        el_start = e.get("start", 0) + offset
        el_end = e.get("end", 5) + offset
        etype = e.get("type", "?")
        content = (e.get("content","") or e.get("shape","") or "")[:30]
        print(f"    [{etype:8s}] abs={el_start:6.2f}-{el_end:6.2f}  '{content}'")
    
    offset += dur

print(f"\n\nTotal project duration: {offset:.2f}s")
print(f"Audio duration from words: {words[-1]['end']:.2f}s")

# Check what _getActiveScene would return at key moments
print("\n=== _getActiveScene SIMULATION ===")
test_times = [0, 4, 8, 8.3, 8.5, 10, 15, 19, 19.1, 25, 40, 60, 80, 91]
for t in test_times:
    sim_offset = 0
    active = None
    for i, s in enumerate(scenes):
        dur = s.get("duration", 10)
        if t >= sim_offset and t < sim_offset + dur:
            active = i
            break
        sim_offset += dur
    if active is None and t >= offset:
        active = len(scenes) - 1
    name = scenes[active]["name"][:30] if active is not None else "NONE"
    print(f"  t={t:6.2f}s => scene {active}: {name}")

# Check how many elements would render at each test time
print("\n=== ELEMENT VISIBILITY SIMULATION ===")
for t in test_times:
    sim_offset = 0
    visible = []
    for s in scenes:
        dur = s.get("duration", 10)
        for e in s.get("elements", []):
            el_abs_start = e.get("start", 0) + sim_offset
            el_abs_end = e.get("end", 5) + sim_offset
            is_cap = e.get("type") == "caption"
            buf = 0.05 if is_cap else 0.5
            if t >= el_abs_start - buf and t <= el_abs_end + buf:
                ct = (e.get("content") or e.get("shape",""))[:20]
                visible.append(f"{e['type']}:{ct}")
        sim_offset += dur
    print(f"  t={t:6.2f}s => {len(visible)} elements visible: {visible[:5]}{'...' if len(visible)>5 else ''}")
