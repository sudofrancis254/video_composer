"""
Cognitive Pacing Engine for Video Composer
===========================================
Maps words to display modes based on content, timing, and human cognition.

Key principles:
1. Processing speed: 200-300ms minimum per word for recognition
2. Chunking: humans read in groups of 3-7 words
3. Visual hierarchy: key words larger, function words smaller
4. Pacing variety: mix single words, groups, phrases for engagement
5. Screen awareness: elements scale with canvas, never overlap
"""

import json
import re
import math
from typing import List, Dict, Tuple, Optional

# ─── Constants ───────────────────────────────────────────────────────
MIN_MS_PER_WORD = 200       # Minimum ms for brain to process a word
COMFORTABLE_MS_PER_WORD = 280  # Comfortable reading pace
MAX_GROUP_WORDS = 5         # Max words in a single display group
FUNCTION_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'out', 'off', 'over', 'under', 'again', 'further',
    'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
    'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 'just', 'because', 'but', 'and', 'or',
    'if', 'while', 'that', 'this', 'these', 'those', 'it', 'its',
    'i', 'me', 'my', 'myself', 'we', 'our', 'you', 'your', 'he',
    'him', 'his', 'she', 'her', 'they', 'them', 'their', 'what',
    'which', 'who', 'whom',
}

# Words that deserve emphasis (nouns, verbs, tech terms)
EMPHASIS_PATTERNS = [
    r'[A-Z][a-z]+',      # Capitalized words (proper nouns)
    r'[A-Z]{2,}',         # ALL CAPS words
    r'\d+',               # Numbers
    r'-',                 # Hyphenated compounds
    r'[A-Z][a-z]+[A-Z]', # CamelCase (tech terms)
]


def classify_word(word: str) -> str:
    """Classify a word as 'key', 'emphasis', or 'function'."""
    w = word.strip().lower().rstrip('.,!?;:')

    # Check emphasis patterns
    for pattern in EMPHASIS_PATTERNS:
        if re.search(pattern, word):
            return 'emphasis'

    # Check function words
    if w in FUNCTION_WORDS:
        return 'function'

    # Default: key word
    return 'key'


def compute_min_display_time(word_count: int, audio_duration: float) -> float:
    """Compute display time based on cognitive processing speed.

    The display time is the sum of:
    1. Audio duration (how long the words take to speak)
    2. Processing buffer (extra time for the brain to read and comprehend)

    The processing buffer is conservative — we allow the visual to extend
    slightly beyond what's strictly necessary, because the render engine
    handles cross-fade transitions between groups.
    """
    # Conservative processing buffers:
    # - Single word: 200ms extra (quick recognition)
    # - 2-3 words: 150ms per additional word (chunk reading)
    # - 4+ words: 120ms per additional word (diminishing returns)
    if word_count == 1:
        processing = 0.20
    elif word_count <= 3:
        processing = 0.20 + (word_count - 1) * 0.15
    else:
        processing = 0.35 + (word_count - 3) * 0.12

    return audio_duration + processing


def group_words(words: List[Dict], max_group: int = MAX_GROUP_WORDS) -> List[Dict]:
    """
    Group words into display units based on:
    - Natural pauses (gaps > 0.3s)
    - Punctuation
    - Cognitive chunking (3-7 words per group)
    - Content type (emphasis words get solo treatment)
    """
    if not words:
        return []

    groups = []
    current_group = []
    current_text = []

    for i, word in enumerate(words):
        text = word['text']
        w_class = classify_word(text)
        start = word['start']
        end = word['end']

        # Check if we should break the group
        should_break = False

        # 1. Natural pause before this word
        if i > 0:
            gap = start - words[i-1]['end']
            if gap > 0.35:
                should_break = True

        # 2. Punctuation at end of previous word
        if i > 0 and re.search(r'[.!?;:,$]$', words[i-1]['text']):
            should_break = True

        # 3. Group is full
        if len(current_group) >= max_group:
            should_break = True

        # 4. Emphasis word starts — solo or small group
        if w_class == 'emphasis' and len(current_group) > 1:
            should_break = True

        # 5. Long word (>10 chars) gets more space
        if len(text) > 10 and len(current_group) > 0:
            should_break = True

        if should_break and current_group:
            groups.append(_make_group(current_group, current_text))
            current_group = []
            current_text = []

        current_group.append(word)
        current_text.append(text)

    if current_group:
        groups.append(_make_group(current_group, current_text))

    return groups


def _make_group(word_list: List[Dict], text_list: List[str]) -> Dict:
    """Create a group object from a list of words."""
    start_time = word_list[0]['start']
    end_time = word_list[-1]['end']
    audio_duration = end_time - start_time
    word_count = len(word_list)

    # Determine the dominant class
    classes = [classify_word(w['text']) for w in word_list]
    emphasis_count = classes.count('emphasis')
    key_count = classes.count('key')

    if emphasis_count > 0:
        dominant = 'emphasis'
    elif key_count > 0:
        dominant = 'key'
    else:
        dominant = 'function'

    # Compute display time with cognitive buffer
    min_display = compute_min_display_time(word_count, audio_duration)

    return {
        'words': word_list,
        'text': ' '.join(text_list),
        'start': start_time,
        'end': end_time,
        'audio_duration': audio_duration,
        'min_display_time': min_display,
        'word_count': word_count,
        'dominant_class': dominant,
        'classes': classes,
        'word_indices': [w.get('id', i) for i, w in enumerate(word_list)],
    }


def compute_display_timing(groups: List[Dict]) -> List[Dict]:
    """
    Compute display timing for each group.

    Key insight: in motion graphics, elements OVERLAP during transitions.
    Group A fades out while Group B fades in. This gives the brain time
    to process Group A's text even after the audio has moved to Group B.

    Timeline:
    Group A:  [====display====]
    Group B:              [====display====]
                       ^ overlap zone (fade transition)
    """
    if not groups:
        return []

    TRANSITION_OVERLAP = 0.20  # 200ms overlap during fade transitions

    for i, group in enumerate(groups):
        # Display starts when the first word is spoken
        display_start = group['start']

        # Display ends = start + minimum cognitive processing time
        display_end = display_start + group['min_display_time']

        # Allow overlap with next group's start for smooth transitions
        # Only cap if display would extend MORE than 500ms into next group
        if i < len(groups) - 1:
            next_start = groups[i+1]['start']
            max_overlap_end = next_start + 0.5  # allow up to 500ms past next group start
            if display_end > max_overlap_end:
                display_end = max_overlap_end

        group['display_start'] = display_start
        group['display_end'] = display_end
        group['display_duration'] = display_end - display_start

    return groups


def compute_visual_hierarchy(groups: List[Dict], canvas_w: int = 1920, canvas_h: int = 1080) -> List[Dict]:
    """
    Assign visual properties based on content importance:
    - Emphasis words: largest, brightest, centered
    - Key words: medium, standard weight
    - Function groups: small, dimmed, positioned lower
    """
    # Scale factors based on canvas height
    base_size = canvas_h * 0.065  # ~70px on 1080p

    for group in groups:
        word_count = group['word_count']
        dominant = group['dominant_class']

        # Font size: fewer words = bigger
        if word_count == 1:
            size_factor = 2.0
        elif word_count == 2:
            size_factor = 1.5
        elif word_count <= 3:
            size_factor = 1.2
        else:
            size_factor = 0.9

        # Emphasis boost
        if dominant == 'emphasis':
            size_factor *= 1.3

        font_size = int(base_size * size_factor)

        # ALL text centered — the eye focus point is the center of the screen.
        # Only vary Y slightly for visual rhythm. NEVER move X from center.
        # Emphasis words: slightly higher to draw the eye
        if dominant == 'emphasis':
            y = 42
            color = '#FFD700'  # Gold for emphasis
            weight = '900'
        elif word_count <= 2:
            y = 45
            color = '#FFFFFF'
            weight = '800'
        else:
            y = 45  # Same center line — not lower
            color = '#E8E8E8'
            weight = '700'
        x = 50  # ALWAYS center — this is where the eye focuses

        group['visual'] = {
            'x': x,
            'y': y,
            'font_size': font_size,
            'color': color,
            'weight': weight,
            'text_align': 'center',
            'max_width': 85,  # % of canvas width
        }

    return groups


def build_overlap_free_layout(groups: List[Dict], canvas_w: int = 1920, canvas_h: int = 1080) -> List[Dict]:
    """
    Ensure no two groups overlap on screen.
    Since groups are sequential in time (only one visible at a time),
    we use the same position but vary it slightly for visual interest.
    """
    # User-calibrated position: container at x=9.375%, y=40.74%,
    # width=80.208%, height=14.81% → text centered via CSS textAlign
    # Only vary Y slightly for visual rhythm (±2% from base)
    y_positions = [40.74, 42.74, 41.74, 42.74, 41.74]

    for i, group in enumerate(groups):
        if 'visual' in group:
            group['visual']['x'] = 9.375   # User's exact position
            group['visual']['y'] = y_positions[i % len(y_positions)]
            group['visual']['width'] = 80.208   # User's exact width
            group['visual']['height'] = 14.81    # User's exact height

    return groups


def generate_display_elements(groups: List[Dict]) -> List[Dict]:
    """
    Convert groups into video composer elements with wordRef,
    screen-aware sizing, and cognitive timing.
    """
    elements = []

    for gi, group in enumerate(groups):
        vis = group.get('visual', {})
        font_size = vis.get('font_size', 72)
        x = vis.get('x', 9.375)       # User's exact X
        y = vis.get('y', 40.74)       # User's exact Y (varies for rhythm)
        width = vis.get('width', 80.208)   # User's exact width
        height = vis.get('height', 14.81)  # User's exact height
        color = vis.get('color', '#FFFFFF')
        weight = vis.get('weight', '700')

        text = group['text']
        word_list = group['words']

        # Create the element with user-calibrated coordinates
        el = {
            'id': f'el_cog_{gi:04d}',
            'type': 'text',
            'content': text,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'style': {
                'fontSize': font_size,
                'fontWeight': weight,
                'color': color,
                'textAlign': 'center',
                'textShadow': '0 2px 20px rgba(0,0,0,0.8)',
                'letterSpacing': '0.05em',
                'lineHeight': '1.3',
            },
            'wordRef': {
                'startWord': _find_word_index(word_list[0]),
                'endWord': _find_word_index(word_list[-1]),
                # NO padding — display exactly during word audio
                # The canvas 0.05s buffer handles smooth transitions
            },
            'animation': {'type': 'none'},
            'entrance': _pick_entrance(group),
            'emphasis': _pick_emphasis(group),
            'exit': _pick_exit(group),
        }

        elements.append(el)

    return elements


def _find_word_index(word: Dict) -> int:
    """Find the index of a word in the original words list by matching start time."""
    # This will be set by the caller using the actual words.json indices
    return word.get('_index', 0)


def _pick_entrance(group: Dict) -> Dict:
    """Pick an entrance animation — must complete within 100ms to avoid flicker."""
    if group['dominant_class'] == 'emphasis':
        return {'type': 'kinetic-in', 'duration': 0.10}
    elif group['word_count'] == 1:
        return {'type': 'morph-scale', 'duration': 0.08}
    elif group['word_count'] <= 3:
        return {'type': 'zoom-in', 'duration': 0.10}
    else:
        return {'type': 'fade-in', 'duration': 0.10}


def _pick_emphasis(group: Dict) -> Dict:
    """Pick an emphasis animation — subtle glow, no duration constraint."""
    if group['dominant_class'] == 'emphasis':
        return {'type': 'glow-breathe', 'duration': 0.3}
    return {'type': 'none', 'duration': 0}


def _pick_exit(group: Dict) -> Dict:
    """Pick an exit animation — must complete within 80ms to avoid flicker."""
    return {'type': 'fade-out', 'duration': 0.08}


# ─── Main Pipeline ───────────────────────────────────────────────────

def process_words_to_elements(words: List[Dict], canvas_w: int = 1920, canvas_h: int = 1080) -> Tuple[List[Dict], List[Dict]]:
    """
    Full pipeline: words → groups → elements with cognitive pacing.

    Returns:
        (groups, elements) — groups for debugging, elements for the video
    """
    # Add indices to words
    for i, w in enumerate(words):
        w['_index'] = i

    # Step 1: Group words into display units
    groups = group_words(words)

    # Step 2: Compute display timing with cognitive buffers
    groups = compute_display_timing(groups)

    # Step 3: Assign visual hierarchy
    groups = compute_visual_hierarchy(groups, canvas_w, canvas_h)

    # Step 4: Layout (overlap-free since groups are sequential)
    groups = build_overlap_free_layout(groups, canvas_w, canvas_h)

    # Step 5: Generate elements
    elements = generate_display_elements(groups)

    return groups, elements


def create_scenes_from_groups(groups: List[Dict], elements: List[Dict], bg_color: str = '#0a0e14') -> List[Dict]:
    """
    Create video composer scenes from cognitive pacing groups.
    Each scene covers a natural pause boundary.
    """
    if not groups:
        return []

    scenes = []
    scene_elements = []
    scene_start = groups[0]['start']
    scene_words = []

    for i, group in enumerate(groups):
        scene_words.extend(group['words'])
        scene_elements.append(elements[i])

        # Check if we should start a new scene
        is_last = i == len(groups) - 1
        should_break = False

        if not is_last:
            next_group = groups[i+1]
            gap = next_group['start'] - group['end']
            if gap > 0.5:  # Natural pause → new scene
                should_break = True
            if len(scene_elements) >= 8:  # Max elements per scene
                should_break = True

        if should_break or is_last:
            # Compute scene timing
            first_word = scene_words[0]
            last_word = scene_words[-1]
            duration = last_word['end'] - first_word['start']

            # Add processing buffer at end
            duration += max(0.5, len(scene_elements) * 0.1)

            # Build phrase text
            phrase_text = ' '.join(w['text'] for w in scene_words)

            scene = {
                'id': f'scene_cog_{len(scenes):03d}',
                'name': f'Phrase {len(scenes)+1}: {phrase_text[:50]}...',
                'duration': round(duration, 3),
                'bg_color': bg_color,
                'wordStart': first_word.get('_index', 0),
                'wordEnd': last_word.get('_index', 0),
                'elements': scene_elements,
            }
            scenes.append(scene)

            # Reset for next scene
            scene_elements = []
            scene_words = []
            scene_start = None

    return scenes
