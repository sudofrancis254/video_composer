/* ============================================================
   Word Alignment Engine
   ============================================================
   Every visual element can reference words by INDEX (not timestamp).
   Timing is computed from words.json at render time.
   
   Element wordRef format:
   {
     "startWord": 5,     // index into words.json array
     "endWord": 12,       // index into words.json array (inclusive)
     "padBefore": 0.1,   // optional seconds before first word
     "padAfter": 0.1     // optional seconds after last word
   }
   
   Scene wordRef format (on scene object):
   {
     "wordStart": 0,     // first word index in this scene
     "wordEnd": 79       // last word index in this scene (inclusive)
   }
   ============================================================ */

const WordAlignment = {
  words: [],           // loaded from words.json
  _cache: {},          // memoization cache

  /**
   * Load words.json for a project
   */
  async loadWords(projectId) {
    try {
      const res = await fetch(`/api/projects/${projectId}/words`);
      if (!res.ok) { this.words = []; return false; }
      this.words = await res.json();
      this._cache = {};
      console.log(`[WordAlignment] Loaded ${this.words.length} words`);
      return true;
    } catch (e) {
      console.warn('[WordAlignment] Failed to load words:', e);
      this.words = [];
      return false;
    }
  },

  /**
   * Get word by index
   */
  getWord(idx) {
    if (idx < 0 || idx >= this.words.length) return null;
    return this.words[idx];
  },

  /**
   * Get the absolute start time of a word by index
   */
  wordStartTime(idx) {
    const w = this.getWord(idx);
    return w ? w.start : 0;
  },

  /**
   * Get the absolute end time of a word by index
   */
  wordEndTime(idx) {
    const w = this.getWord(idx);
    return w ? w.end : 0;
  },

  /**
   * Resolve a wordRef to { start, end } timestamps
   * wordRef: { startWord, endWord, padBefore, padAfter }
   * offset: scene-local time offset to subtract (for scenes with absolute word indices)
   */
  resolveTiming(wordRef, offset = 0) {
    if (!wordRef || wordRef.startWord == null || wordRef.endWord == null) {
      return null;
    }
    const key = `${wordRef.startWord}-${wordRef.endWord}-${offset}`;
    if (this._cache[key]) return this._cache[key];

    const start = this.wordStartTime(wordRef.startWord) - offset;
    const end = this.wordEndTime(wordRef.endWord) - offset;
    const padBefore = wordRef.padBefore || 0;
    const padAfter = wordRef.padAfter || 0;

    const result = {
      start: Math.max(0, start - padBefore),
      end: end + padAfter,
      duration: (end + padAfter) - Math.max(0, start - padBefore)
    };

    this._cache[key] = result;
    return result;
  },

  /**
   * Resolve scene word range to { start, end } absolute times
   * Scene must have wordStart and wordEnd fields
   */
  resolveSceneTiming(scene) {
    if (scene.wordStart == null || scene.wordEnd == null) return null;
    const start = this.wordStartTime(scene.wordStart);
    const end = this.wordEndTime(scene.wordEnd);
    return { start, end, duration: end - start };
  },

  /**
   * Get all words in a range as a formatted string
   */
  getWordsText(startIdx, endIdx) {
    const words = [];
    for (let i = startIdx; i <= endIdx && i < this.words.length; i++) {
      words.push(this.words[i].text);
    }
    return words.join(' ');
  },

  /**
   * Find which word index corresponds to a given time
   */
  wordAtTime(time) {
    for (let i = 0; i < this.words.length; i++) {
      if (this.words[i].start <= time && this.words[i].end >= time) {
        return i;
      }
    }
    // Find nearest word
    let nearest = 0;
    let minDist = Infinity;
    for (let i = 0; i < this.words.length; i++) {
      const dist = Math.abs(this.words[i].start - time);
      if (dist < minDist) { minDist = dist; nearest = i; }
    }
    return nearest;
  },

  /**
   * Get the phrase (group of words) that covers a time range
   * Returns { startIdx, endIdx, text, start, end }
   */
  phraseAtTime(time) {
    const idx = this.wordAtTime(time);
    // Walk backwards to find phrase start (stop at punctuation or gap > 0.3s)
    let startIdx = idx;
    for (let i = idx; i > 0; i--) {
      const gap = this.words[i].start - this.words[i - 1].end;
      if (gap > 0.3 || /[.!?;:]$/.test(this.words[i - 1].text)) break;
      startIdx = i - 1;
    }
    // Walk forwards to find phrase end
    let endIdx = idx;
    for (let i = idx; i < this.words.length - 1; i++) {
      const gap = this.words[i + 1].start - this.words[i].end;
      if (gap > 0.3 || /[.!?;:]$/.test(this.words[i].text)) { endIdx = i; break; }
      endIdx = i + 1;
    }

    return {
      startIdx,
      endIdx,
      text: this.getWordsText(startIdx, endIdx),
      start: this.words[startIdx].start,
      end: this.words[endIdx].end
    };
  },

  /**
   * Verify alignment of all elements against word timestamps
   * Returns { aligned, misaligned: [], gaps: [] }
   */
  verifyAlignment(scenes) {
    const results = { aligned: 0, misaligned: [], gaps: [], stats: {} };
    if (!this.words.length) {
      results.error = 'No words loaded';
      return results;
    }

    let lastEnd = 0;
    let totalWordsCovered = new Set();

    for (const scene of scenes) {
      const elements = scene.elements || [];
      for (const el of elements) {
        // If element has wordRef, verify it
        if (el.wordRef && el.wordRef.startWord != null) {
          const resolved = this.resolveTiming(el.wordRef);
          if (!resolved) {
            results.misaligned.push({
              element: el.id,
              type: el.type,
              content: (el.content || '').substring(0, 30),
              issue: 'Invalid wordRef'
            });
            continue;
          }

          // Check if element timing matches word timestamps
          const wordStart = this.wordStartTime(el.wordRef.startWord);
          const wordEnd = this.wordEndTime(el.wordRef.endWord);
          const timeDiff = Math.abs(resolved.start - wordStart);
          const endDiff = Math.abs(resolved.end - wordEnd);

          if (timeDiff < 0.05 && endDiff < 0.05) {
            results.aligned++;
          } else {
            results.misaligned.push({
              element: el.id,
              type: el.type,
              content: (el.content || '').substring(0, 30),
              wordRef: el.wordRef,
              expected: { start: wordStart, end: wordEnd },
              actual: resolved,
              diff: { start: timeDiff, end: endDiff }
            });
          }

          // Track words covered
          for (let i = el.wordRef.startWord; i <= el.wordRef.endWord; i++) {
            totalWordsCovered.add(i);
          }
        }
        // If element has raw start/end, check alignment to nearest words
        else if (el.start != null && el.end != null) {
          const startWord = this.wordAtTime(el.start);
          const endWord = this.wordAtTime(el.end);
          const wordStart = this.wordStartTime(startWord);
          const wordEnd = this.wordEndTime(endWord);
          const startDiff = Math.abs(el.start - wordStart);
          const endDiff = Math.abs(el.end - wordEnd);

          if (startDiff > 0.15 || endDiff > 0.15) {
            results.misaligned.push({
              element: el.id,
              type: el.type,
              content: (el.content || '').substring(0, 30),
              issue: `Timing drift: start ${startDiff.toFixed(3)}s, end ${endDiff.toFixed(3)}s from nearest word`,
              nearestWords: { start: startWord, end: endWord }
            });
          } else {
            results.aligned++;
          }
        }
      }

      // Check for gaps between scenes
      if (scene.wordEnd != null) {
        const sceneEnd = this.wordEndTime(scene.wordEnd);
        if (sceneEnd > lastEnd + 0.5) {
          results.gaps.push({
            after: scene.name,
            from: lastEnd,
            to: sceneEnd,
            duration: sceneEnd - lastEnd
          });
        }
        lastEnd = sceneEnd;
      }
    }

    // Stats
    results.stats = {
      totalWords: this.words.length,
      wordsCovered: totalWordsCovered.size,
      coveragePercent: this.words.length > 0
        ? ((totalWordsCovered.size / this.words.length) * 100).toFixed(1)
        : 0,
      totalScenes: scenes.length,
      totalElements: scenes.reduce((sum, s) => sum + (s.elements || []).length, 0)
    };

    return results;
  },

  /**
   * Auto-assign wordRef to elements that don't have one
   * Based on their current start/end times and nearest word timestamps
   */
  autoAssignWordRefs(scenes) {
    let assigned = 0;
    for (const scene of scenes) {
      for (const el of (scene.elements || [])) {
        if (el.wordRef && el.wordRef.startWord != null) continue;
        if (el.start == null || el.end == null) continue;

        const startIdx = this.wordAtTime(el.start);
        const endIdx = this.wordAtTime(el.end);
        el.wordRef = { startWord: startIdx, endWord: endIdx };
        assigned++;
      }
    }
    return assigned;
  },

  /**
   * Convert scene from time-based to word-based boundaries
   * scene.duration = wordEndTime(wordEnd) - wordStartTime(wordStart)
   */
  convertSceneToWordBased(scene) {
    if (scene.wordStart == null || scene.wordEnd == null) return false;
    const timing = this.resolveSceneTiming(scene);
    if (!timing) return false;
    scene.duration = timing.duration;
    // Adjust all elements to be relative to scene start
    for (const el of (scene.elements || [])) {
      if (el.start != null) el.start -= timing.start;
      if (el.end != null) el.end -= timing.start;
      // Auto-assign wordRef if not present
      if (!el.wordRef || el.wordRef.startWord == null) {
        const startIdx = this.wordAtTime(el.start + timing.start);
        const endIdx = this.wordAtTime(el.end + timing.start);
        el.wordRef = { startWord: startIdx, endWord: endIdx };
      }
    }
    return true;
  }
};
