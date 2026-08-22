/* ============================================================
   Multi-Audio Track System
   ============================================================
   Supports: narration (primary) + SFX + background music
   
   Track format:
   {
     "id": "track_narration",
     "type": "narration",     // narration | sfx | music
     "source": "/audio/pid/source.mp3",
     "volume": 1.0,           // 0.0 - 1.0
     "fadeIn": 0.5,           // seconds
     "fadeOut": 0.5,          // seconds
     "offset": 0,             // seconds into project timeline
     "loop": false,           // music loops
     "ducking": 0.3           // volume during narration (music only)
   }
   
   SFX trigger format (on element):
   {
     "type": "sfx",
     "sfx_ref": {
       "trackId": "sfx_click",
       "triggerAtWord": 42,    // word index that triggers this
       "triggerAtTime": null,  // or absolute time in seconds
       "volume": 0.8
     }
   }
   ============================================================ */

const MultiAudio = {
  tracks: [],          // all audio tracks
  _elements: {},       // audio elements by track id
  _sfxQueue: [],       // pending SFX to trigger
  _activeSfx: [],      // currently playing SFX

  /**
   * Load tracks from project data
   */
  loadTracks(project) {
    this.tracks = project.audioTracks || [];
    this._createElements();
    console.log(`[MultiAudio] Loaded ${this.tracks.length} tracks`);
  },

  /**
   * Create HTML Audio elements for each track
   */
  _createElements() {
    // Clean up old elements
    for (const [id, el] of Object.entries(this._elements)) {
      el.pause();
      el.src = '';
    }
    this._elements = {};

    for (const track of this.tracks) {
      if (!track.source) continue;
      const audio = new Audio();
      audio.src = track.source;
      audio.volume = track.volume || 1.0;
      audio.loop = track.loop || false;
      audio.preload = 'auto';
      this._elements[track.id] = audio;
    }
  },

  /**
   * Get the primary narration track
   */
  getNarrationTrack() {
    return this.tracks.find(t => t.type === 'narration') || this.tracks[0];
  },

  /**
   * Get all music tracks
   */
  getMusicTracks() {
    return this.tracks.filter(t => t.type === 'music');
  },

  /**
   * Get all SFX tracks
   */
  getSfxTracks() {
    return this.tracks.filter(t => t.type === 'sfx');
  },

  /**
   * Play all tracks from a given time
   */
  playFrom(time) {
    for (const track of this.tracks) {
      const audio = this._elements[track.id];
      if (!audio) continue;

      const trackOffset = track.offset || 0;
      const seekTo = time - trackOffset;

      if (seekTo < 0) {
        // Track hasn't started yet
        audio.pause();
        continue;
      }

      if (audio.readyState >= 2) {
        audio.currentTime = seekTo;
      }
      audio.play().catch(() => {});
    }
  },

  /**
   * Pause all tracks
   */
  pauseAll() {
    for (const track of this.tracks) {
      const audio = this._elements[track.id];
      if (audio) audio.pause();
    }
  },

  /**
   * Seek all tracks to a specific time
   */
  seekTo(time) {
    for (const track of this.tracks) {
      const audio = this._elements[track.id];
      if (!audio) continue;

      const trackOffset = track.offset || 0;
      const seekTo = time - trackOffset;

      if (seekTo < 0) {
        audio.pause();
        audio.currentTime = 0;
        continue;
      }

      if (audio.readyState >= 2) {
        audio.currentTime = Math.max(0, seekTo);
      }
    }
  },

  /**
   * Update volumes based on current time (for ducking)
   */
  updateVolumes(currentTime) {
    const narrationPlaying = this._isNarrationPlaying(currentTime);

    for (const track of this.tracks) {
      const audio = this._elements[track.id];
      if (!audio) continue;

      let targetVolume = track.volume || 1.0;

      // Apply ducking to music when narration is playing
      if (track.type === 'music' && track.ducking && narrationPlaying) {
        targetVolume *= track.ducking;
      }

      // Apply fade in/out
      const trackOffset = track.offset || 0;
      const trackTime = currentTime - trackOffset;
      if (trackTime < (track.fadeIn || 0)) {
        const progress = trackTime / (track.fadeIn || 0.5);
        targetVolume *= Math.max(0, Math.min(1, progress));
      }

      // Smooth volume transition
      if (Math.abs(audio.volume - targetVolume) > 0.01) {
        audio.volume = targetVolume;
      }
    }
  },

  /**
   * Check if narration is currently playing
   */
  _isNarrationPlaying(currentTime) {
    const narr = this.getNarrationTrack();
    if (!narr) return false;
    const audio = this._elements[narr.id];
    return audio && !audio.paused;
  },

  /**
   * Play an SFX at a specific time
   */
  playSfx(trackId, volume = 1.0) {
    const track = this.tracks.find(t => t.id === trackId && t.type === 'sfx');
    if (!track) return;

    // Clone the audio for overlapping SFX
    const audio = new Audio();
    audio.src = track.source;
    audio.volume = (track.volume || 1.0) * volume;
    audio.play().catch(() => {});

    this._activeSfx.push({ audio, trackId });
    audio.onended = () => {
      this._activeSfx = this._activeSfx.filter(s => s.audio !== audio);
    };
  },

  /**
   * Trigger SFX elements that match the current time
   */
  triggerSfxAtTime(currentTime, elements) {
    for (const el of elements) {
      if (el.type !== 'sfx' || !el.sfx_ref) continue;
      const ref = el.sfx_ref;

      // Check if already triggered
      const key = `${ref.trackId}-${el.id}`;
      if (this._sfxQueue.includes(key)) continue;

      // Check trigger condition
      let shouldTrigger = false;
      if (ref.triggerAtTime != null) {
        shouldTrigger = Math.abs(currentTime - ref.triggerAtTime) < 0.1;
      } else if (ref.triggerAtWord != null && WordAlignment.words.length > 0) {
        const word = WordAlignment.getWord(ref.triggerAtWord);
        if (word) {
          shouldTrigger = currentTime >= word.start && currentTime <= word.end;
        }
      }

      if (shouldTrigger) {
        this._sfxQueue.push(key);
        this.playSfx(ref.trackId, ref.volume || 1.0);
      }
    }
  },

  /**
   * Add a new track to the project
   */
  addTrack(trackData) {
    const track = {
      id: 'track_' + Date.now().toString(36),
      type: trackData.type || 'sfx',
      source: trackData.source,
      volume: trackData.volume ?? 1.0,
      fadeIn: trackData.fadeIn ?? 0,
      fadeOut: trackData.fadeOut ?? 0,
      offset: trackData.offset ?? 0,
      loop: trackData.loop ?? false,
      ducking: trackData.ducking ?? 0.3,
      ...trackData
    };
    this.tracks.push(track);
    return track;
  },

  /**
   * Remove a track
   */
  removeTrack(trackId) {
    const audio = this._elements[trackId];
    if (audio) {
      audio.pause();
      audio.src = '';
      delete this._elements[trackId];
    }
    this.tracks = this.tracks.filter(t => t.id !== trackId);
  },

  /**
   * Update track properties
   */
  updateTrack(trackId, props) {
    const track = this.tracks.find(t => t.id === trackId);
    if (!track) return;
    Object.assign(track, props);
    const audio = this._elements[trackId];
    if (audio) {
      if (props.volume != null) audio.volume = props.volume;
      if (props.loop != null) audio.loop = props.loop;
      if (props.source) audio.src = props.source;
    }
  },

  /**
   * Stop and reset all tracks
   */
  stopAll() {
    this.pauseAll();
    for (const audio of Object.values(this._elements)) {
      audio.currentTime = 0;
    }
    this._sfxQueue = [];
    // Stop active SFX
    for (const sfx of this._activeSfx) {
      sfx.audio.pause();
    }
    this._activeSfx = [];
  },

  /**
   * Get duration of the longest track
   */
  getMaxDuration() {
    let max = 0;
    for (const track of this.tracks) {
      const audio = this._elements[track.id];
      if (audio && audio.duration) {
        const total = (track.offset || 0) + audio.duration;
        if (total > max) max = total;
      }
    }
    return max;
  },

  /**
   * Render track list in the timeline UI
   */
  renderTrackList(container) {
    if (!container) return;
    container.innerHTML = '';

    for (const track of this.tracks) {
      const div = document.createElement('div');
      div.className = 'audio-track';
      div.dataset.trackId = track.id;

      const iconMap = { narration: '🎙', music: '🎵', sfx: '🔊' };
      div.innerHTML = `
        <span class="track-icon">${iconMap[track.type] || '🎵'}</span>
        <span class="track-name">${track.type}: ${track.id}</span>
        <input type="range" min="0" max="100" value="${(track.volume || 1) * 100}"
               class="track-volume" title="Volume">
        <button class="track-remove" title="Remove">✕</button>
      `;

      div.querySelector('.track-volume').oninput = (e) => {
        this.updateTrack(track.id, { volume: e.target.value / 100 });
      };

      div.querySelector('.track-remove').onclick = () => {
        this.removeTrack(track.id);
        this.renderTrackList(container);
      };

      container.appendChild(div);
    }
  }
};
