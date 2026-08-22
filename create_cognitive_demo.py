"""
Cognitive Pacing Demo Generator
===============================
Uses the cognitive pacing engine to create a motion graphics demo
where words appear at a pace that's comfortable for human processing.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from cognitive_pacing import (
    process_words_to_elements, create_scenes_from_groups,
    classify_word, compute_min_display_time
)

PROJECT_ID = 'cd7824dc202a'
PROJECT_DIR = os.path.join(os.path.dirname(__file__), 'projects', PROJECT_ID)

def main():
    # Load words
    words_path = os.path.join(PROJECT_DIR, 'words.json')
    with open(words_path, 'r', encoding='utf-8') as f:
        words = json.load(f)

    print(f'Loaded {len(words)} words')

    # Classify all words for debugging
    classes = {}
    for w in words:
        c = classify_word(w['text'])
        classes.setdefault(c, []).append(w['text'])

    print(f'\nWord classification:')
    for c, ws in classes.items():
        print(f'  {c}: {len(ws)} words — e.g. {", ".join(ws[:5])}')

    # Run cognitive pacing pipeline
    t0 = time.time()
    groups, elements = process_words_to_elements(words, canvas_w=1920, canvas_h=1080)
    elapsed = time.time() - t0

    print(f'\nCognitive pacing pipeline: {elapsed:.3f}s')
    print(f'  Groups: {len(groups)}')
    print(f'  Elements: {len(elements)}')

    # Show group breakdown
    print(f'\nGroup breakdown:')
    for i, g in enumerate(groups[:15]):
        vis = g.get('visual', {})
        print(f'  [{i:3d}] "{g["text"][:45]:45s}" '
              f'words={g["word_count"]} class={g["dominant_class"]:<10s} '
              f'time={g["start"]:.2f}-{g["end"]:.2f}s '
              f'display={g.get("display_duration",0):.2f}s '
              f'size={vis.get("font_size","?")}px '
              f'entrance={elements[i]["entrance"]["type"]}')
    if len(groups) > 15:
        print(f'  ... and {len(groups)-15} more groups')

    # Create scenes
    scenes = create_scenes_from_groups(groups, elements, bg_color='#0a0e14')
    print(f'\nScenes: {len(scenes)}')
    for i, s in enumerate(scenes):
        print(f'  [{i:2d}] {s["name"][:55]:55s} dur={s["duration"]:.2f}s els={len(s["elements"])}')

    # Compute total timeline
    total = sum(s['duration'] for s in scenes)
    audio_total = words[-1]['end'] - words[0]['start']
    print(f'\nTimeline: {total:.1f}s visual vs {audio_total:.1f}s audio')

    # Verify: no overlapping elements in any scene
    overlap_count = 0
    for s in scenes:
        els = s['elements']
        for i in range(len(els)):
            for j in range(i+1, len(els)):
                ei, ej = els[i], els[j]
                wi_start = ei['wordRef']['startWord']
                wi_end = ei['wordRef'].get('endWord', wi_start)
                wj_start = ej['wordRef']['startWord']
                wj_end = ej['wordRef'].get('endWord', wj_start)
                if wi_start <= wj_end and wj_start <= wi_end:
                    overlap_count += 1
    print(f'Word index overlaps: {overlap_count} (should be 0)')

    # Verify: display timing respects cognitive minimums
    timing_issues = 0
    for g in groups:
        if g.get('display_duration', 0) < g.get('min_display_time', 0) - 0.05:
            timing_issues += 1
            print(f'  ⚠ Timing issue: "{g["text"][:30]}" display={g["display_duration"]:.2f}s < min={g["min_display_time"]:.2f}s')
    print(f'Timing issues: {timing_issues} (should be 0)')

    # Write scenes
    scenes_path = os.path.join(PROJECT_DIR, 'scenes.json')
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    print(f'\n✅ Written {scenes_path}')

    # Update meta
    meta_path = os.path.join(PROJECT_DIR, 'meta.json')
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta = json.load(f)
    meta['name'] = 'Cognitive Pacing Demo'
    meta['modified'] = time.time()
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f'✅ Updated {meta_path}')

    # Summary stats
    total_elements = sum(len(s['elements']) for s in scenes)
    avg_group_size = sum(g['word_count'] for g in groups) / len(groups)
    avg_display_time = sum(g.get('display_duration', 0) for g in groups) / len(groups)
    emphasis_groups = sum(1 for g in groups if g['dominant_class'] == 'emphasis')

    print(f'\n📊 Summary:')
    print(f'  Words: {len(words)}')
    print(f'  Groups: {len(groups)} (avg {avg_group_size:.1f} words/group)')
    print(f'  Scenes: {len(scenes)}')
    print(f'  Elements: {total_elements}')
    print(f'  Emphasis groups: {emphasis_groups}')
    print(f'  Avg display time: {avg_display_time:.2f}s')
    print(f'  Total visual duration: {total:.1f}s')


if __name__ == '__main__':
    main()
