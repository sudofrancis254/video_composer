#!/usr/bin/env python3
"""Add motion graphics elements to the word-aligned scenes."""
import json, os, uuid

PID = 'cd7824dc202a'
BASE = os.path.join('projects', PID)
w = json.load(open(os.path.join(BASE, 'words.json'), 'r', encoding='utf-8'))
scenes = json.load(open(os.path.join(BASE, 'scenes.json'), 'r', encoding='utf-8'))
def uid(): return uuid.uuid4().hex[:12]

def add_text(scene_idx, content, x, y, wi, we, **kw):
    s = scenes[scene_idx]
    so = w[s['wordStart']]['start']
    el = {
        'id': uid(), 'type': 'text', 'content': content,
        'x': x, 'y': y, 'width': kw.get('w', 40), 'height': kw.get('h', 15),
        'start': round(w[wi]['start'] - so, 3),
        'end': round(w[we]['end'] - so + kw.get('extra', 0.5), 3),
        'wordRef': {'startWord': wi, 'wordEnd': we},
        'font': kw.get('font', 'Bebas Neue'), 'size': kw.get('sz', 72),
        'color': kw.get('col', '#FFFFFF'), 'align': 'center',
    }
    if kw.get('text_shadow'): el['text_shadow'] = kw['text_shadow']
    if kw.get('glow'): el['glow'] = kw['glow']
    if kw.get('ent'): el['entrance'] = {'type': kw['ent'], 'duration': kw.get('ent_dur', 0.6)}
    if kw.get('emph'): el['emphasis'] = {'type': kw['emph'], 'duration': 0.4}
    if kw.get('ext'): el['exit'] = {'type': kw['ext'], 'duration': 0.5}
    s['elements'].append(el)

# Scene 0: Hook (words 0-12)
add_text(0, 'IN MY LAST VIDEO', 10, 8, 0, 3, w=80, h=20, sz=96,
         text_shadow='0 4px 20px rgba(74,158,255,0.5)',
         ent='kinetic-in', ent_dur=0.8, emph='glow-breathe', ext='exit-fly-right')
add_text(0, 'POSTEMPlATE', 15, 38, 11, 11, w=70, h=18, sz=72, col='#4a9eff', font='Orbitron',
         ent='morph-scale', emph='pulse', ext='exit-dissolve')
add_text(0, 'CODEBASE', 25, 62, 12, 12, w=50, h=14, sz=64, col='#FFD700', font='Anton', extra=1.0,
         ent='zoom-in', emph='wave-float', ext='fade-out')

# Scene 1: POS (words 13-18)
add_text(1, 'REAL POINT-OF-SALE', 8, 15, 13, 14, w=84, h=20, sz=80, col='#00E5FF', font='Orbitron',
         ent='kinetic-in', emph='glow-breathe', ext='exit-dissolve')
add_text(1, 'APPS SCRIPT', 20, 55, 17, 18, w=60, h=16, sz=72, col='#E0E0E0', font='Montserrat',
         ent='typewriter', emph='wave-float', ext='exit-shrink')

# Scene 2: Layers (words 19-27)
add_text(2, 'EVERY LAYER', 10, 5, 19, 20, w=80, h=16, sz=88,
         ent='slide-down', emph='shake', ext='exit-fly-up')
add_text(2, 'DATABASE', 5, 28, 21, 21, w=42, h=20, sz=80, col='#00E5FF', font='Orbitron',
         ent='kinetic-in', emph='glow-breathe', ext='exit-dissolve')
add_text(2, 'BUSINESS LOGIC', 53, 28, 24, 25, w=42, h=20, sz=72, col='#FF9100', font='Anton',
         ent='counter-spin', emph='pulse', ext='exit-fly-right')
add_text(2, 'SECURITY', 25, 55, 27, 27, w=50, h=20, sz=76, col='#FF5252', font='Raleway',
         ent='flip-in', emph='shake', ext='exit-shrink')

# Scene 3: Promise (words 28-42)
add_text(3, 'I MADE A', 20, 15, 33, 34, w=60, h=18, sz=96,
         ent='typewriter', ent_dur=0.8, emph='glow-breathe', ext='exit-fly-up')
add_text(3, 'PROMISE', 15, 35, 35, 35, w=70, h=22, sz=108, col='#FFD700', font='Permanent Marker', extra=2.0,
         ent='morph-scale', ent_dur=0.9, emph='pulse', ext='exit-dissolve')
add_text(3, 'ONE MORE VIDEO', 10, 62, 38, 41, w=80, h=14, sz=64, col='#4a9eff', font='Anton',
         ent='slide-up', emph='wave-float', ext='fade-out')

# Scene 4: Plan (words 43-56)
add_text(4, 'HOW TO PLAN', 10, 10, 43, 46, w=80, h=20, sz=96,
         ent='kinetic-in', emph='glow-breathe', ext='exit-fly-right')
add_text(4, 'A CODEBASE', 15, 38, 47, 48, w=70, h=16, sz=72, col='#FFD700', font='Montserrat',
         ent='morph-scale', emph='pulse', ext='exit-dissolve')
add_text(4, 'A SINGLE LINE OF CODE', 10, 70, 54, 56, w=80, h=12, sz=48, col='#4a9eff', font='Orbitron',
         ent='typewriter', ext='exit-shrink')

# Scene 5: That Video (words 57-68)
add_text(5, 'THIS IS THAT VIDEO', 10, 10, 57, 60, w=80, h=20, sz=84,
         ent='slide-left', emph='glow-breathe', ext='exit-fly-right')
add_text(5, 'EXPLAIN', 25, 55, 66, 66, w=50, h=14, sz=72, col='#FF5252', font='Anton', extra=1.0,
         ent='shake', emph='shake', ext='exit-shrink')

# Scene 6: Built to Read (words 69-77)
add_text(6, 'THAT CODEBASE', 10, 8, 69, 70, w=80, h=16, sz=84,
         ent='kinetic-in', emph='glow-breathe', ext='exit-fly-right')
add_text(6, 'BUILT TO BE READ', 10, 60, 72, 77, w=80, h=16, sz=72, col='#4CAF50', font='Orbitron',
         ent='morph-scale', emph='pulse', ext='exit-dissolve')

# Scene 7: Two Readers (words 78-end)
add_text(7, 'BY TWO READERS', 10, 5, 78, 80, w=80, h=14, sz=72,
         ent='slide-down', emph='glow-breathe', ext='exit-fly-right')
if 81 < len(w):
    add_text(7, 'HUMANS', 10, 25, 81, 81, w=35, h=25, sz=96, col='#4CAF50',
             glow={'color': '#4CAF50', 'radius': 20},
             ent='kinetic-in', emph='glow-breathe', ext='exit-dissolve')
if 83 < len(w):
    add_text(7, 'AI ASSISTANTS', 55, 25, 83, min(85, len(w)-1), w=35, h=25, sz=96, col='#E040FB',
             glow={'color': '#E040FB', 'radius': 20},
             ent='counter-spin', emph='pulse', ext='exit-dissolve')

# Save
with open(os.path.join(BASE, 'scenes.json'), 'w', encoding='utf-8') as f:
    json.dump(scenes, f, indent=2, ensure_ascii=False)

total = sum(len(s['elements']) for s in scenes)
print(f'Done: {len(scenes)} scenes, {total} elements')
for i, s in enumerate(scenes):
    print(f'  {i+1}. {s["name"]}: {len(s["elements"])} elements, words {s["wordStart"]}-{s["wordEnd"]}')
