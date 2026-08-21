/* ============================================================
   Video Composer — Main Application
   ============================================================ */

const API = '';  // same origin

/* ------------------------------------------------------------------
   Auto-event logger — sends every user action to the server log
   ------------------------------------------------------------------ */
const Logger = {
  _buf: [],
  _flushTimer: null,

  log(action, detail = {}) {
    const entry = { ts: Date.now(), action, ...detail };
    this._buf.push(entry);
    // Flush every 500ms or when buffer hits 10
    if (this._buf.length >= 10) this.flush();
    else if (!this._flushTimer) {
      this._flushTimer = setTimeout(() => this.flush(), 500);
    }
  },

  flush() {
    if (this._flushTimer) { clearTimeout(this._flushTimer); this._flushTimer = null; }
    if (!this._buf.length) return;
    const batch = this._buf.splice(0);
    try {
      navigator.sendBeacon(`${API}/api/log`, JSON.stringify({ events: batch }));
    } catch (_) {
      // fallback: fire-and-forget fetch
      fetch(`${API}/api/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ events: batch }),
        keepalive: true
      }).catch(() => {});
    }
  }
};

/* ------------------------------------------------------------------
   Main App
   ------------------------------------------------------------------ */
const App = {
  // State
  project: null,
  scenes: [],
  currentScene: null,
  currentElement: null,
  tool: 'select',
  playing: false,
  currentTime: 0,
  duration: 0,
  audio: null,
  animFrame: null,
  dragState: null,
  resizeState: null,
  _playheadDrag: false,       // user is dragging the playhead
  _seeking: false,            // true while seekTo is executing — blocks RAF/timeupdate from overwriting
  _selectedImportPid: null,
  _propCallbacks: {},         // property panel change callbacks

  // Phase 2: Undo/redo
  _undoStack: [],
  _redoStack: [],
  _maxUndo: 50,

  // Phase 2: Copy/paste
  _clipboard: null,

  // Phase 2: Snap-to-grid
  _snapEnabled: true,
  _snapSize: 20,  // px at canvas resolution

  // ---- Init ----
  init() {
    this.bindKeyboard();
    this.bindCanvasEvents();
    this.bindTimelineInteractions();
    this.bindTimelineResize();
    this.scaleCanvas();
    window.addEventListener('resize', () => this.scaleCanvas());
    Logger.log('app_init');
  },

  // ---- Undo/Redo ----
  pushUndo() {
    if (!this.currentScene) return;
    const snapshot = JSON.parse(JSON.stringify(this.currentScene.elements || []));
    this._undoStack.push(snapshot);
    if (this._undoStack.length > this._maxUndo) this._undoStack.shift();
    this._redoStack = []; // clear redo on new action
  },

  undo() {
    if (!this.currentScene || !this._undoStack.length) {
      this.toast('Nothing to undo');
      return;
    }
    const current = JSON.parse(JSON.stringify(this.currentScene.elements || []));
    this._redoStack.push(current);
    this.currentScene.elements = this._undoStack.pop();
    this.currentElement = null;
    this.renderCanvas();
    this.renderTimeline();
    this.renderProperties();
    this.saveScene();
    Logger.log('undo');
    this.toast('Undo');
  },

  redo() {
    if (!this.currentScene || !this._redoStack.length) {
      this.toast('Nothing to redo');
      return;
    }
    const current = JSON.parse(JSON.stringify(this.currentScene.elements || []));
    this._undoStack.push(current);
    this.currentScene.elements = this._redoStack.pop();
    this.currentElement = null;
    this.renderCanvas();
    this.renderTimeline();
    this.renderProperties();
    this.saveScene();
    Logger.log('redo');
    this.toast('Redo');
  },

  // ---- Copy/Paste ----
  copyElement() {
    if (!this.currentElement) return;
    this._clipboard = JSON.parse(JSON.stringify(this.currentElement));
    Logger.log('copy_element', { eid: this.currentElement.id });
    this.toast('Copied');
  },

  pasteElement() {
    if (!this._clipboard || !this.currentScene) return;
    this.pushUndo();
    const clone = JSON.parse(JSON.stringify(this._clipboard));
    clone.id = 'el_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    // Offset slightly so pasted element doesn't overlap
    clone.x = Math.min(95, (clone.x || 35) + 3);
    clone.y = Math.min(95, (clone.y || 35) + 3);
    Logger.log('paste_element', { type: clone.type });
    this.addElement(clone);
  },

  // ---- Snap-to-grid ----
  snap(val) {
    if (!this._snapEnabled) return val;
    return Math.round(val / this._snapSize) * this._snapSize;
  },

  toggleSnap() {
    this._snapEnabled = !this._snapEnabled;
    this.toast(this._snapEnabled ? 'Snap: ON' : 'Snap: OFF');
    Logger.log('toggle_snap', { enabled: this._snapEnabled });
  },

  // ---- Layer ordering ----
  bringToFront() {
    if (!this.currentElement || !this.currentScene) return;
    this.pushUndo();
    const els = this.currentScene.elements;
    const idx = els.findIndex(e => e.id === this.currentElement.id);
    if (idx < 0 || idx === els.length - 1) return;
    const [el] = els.splice(idx, 1);
    els.push(el);
    this.renderCanvas();
    this.renderTimeline();
    this.saveScene();
    Logger.log('bring_to_front', { eid: el.id });
    this.toast('Brought to front');
  },

  sendToBack() {
    if (!this.currentElement || !this.currentScene) return;
    this.pushUndo();
    const els = this.currentScene.elements;
    const idx = els.findIndex(e => e.id === this.currentElement.id);
    if (idx <= 0) return;
    const [el] = els.splice(idx, 1);
    els.unshift(el);
    this.renderCanvas();
    this.renderTimeline();
    this.saveScene();
    Logger.log('send_to_back', { eid: el.id });
    this.toast('Sent to back');
  },

  moveUp() {
    if (!this.currentElement || !this.currentScene) return;
    this.pushUndo();
    const els = this.currentScene.elements;
    const idx = els.findIndex(e => e.id === this.currentElement.id);
    if (idx < 0 || idx >= els.length - 1) return;
    [els[idx], els[idx + 1]] = [els[idx + 1], els[idx]];
    this.renderCanvas();
    this.saveScene();
    Logger.log('move_up', { eid: this.currentElement.id });
  },

  moveDown() {
    if (!this.currentElement || !this.currentScene) return;
    this.pushUndo();
    const els = this.currentScene.elements;
    const idx = els.findIndex(e => e.id === this.currentElement.id);
    if (idx <= 0) return;
    [els[idx], els[idx - 1]] = [els[idx - 1], els[idx]];
    this.renderCanvas();
    this.saveScene();
    Logger.log('move_down', { eid: this.currentElement.id });
  },

  // ---- Alignment ----
  alignElement(alignment) {
    if (!this.currentElement || !this.currentScene) return;
    this.pushUndo();
    const el = this.currentElement;
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    const ew = this.toPx(el.width, cw);
    const eh = this.toPx(el.height, ch);

    switch (alignment) {
      case 'left': el.x = 0; break;
      case 'center-h': el.x = this.pxToPercent((cw - ew) / 2, cw); break;
      case 'right': el.x = this.pxToPercent(cw - ew, cw); break;
      case 'top': el.y = 0; break;
      case 'center-v': el.y = this.pxToPercent((ch - eh) / 2, ch); break;
      case 'bottom': el.y = this.pxToPercent(ch - eh, ch); break;
    }

    this.renderCanvas();
    this.renderTimeline();
    this.renderProperties();
    this.saveScene();
    Logger.log('align_element', { alignment, eid: el.id });
    this.toast(`Aligned ${alignment}`);
  },

  // ---- Tool selection ----
  setTool(tool) {
    this.tool = tool;
    document.querySelectorAll('.sidebar-btn[data-tool]').forEach(b => {
      b.classList.toggle('active', b.dataset.tool === tool);
    });
    const stage = document.getElementById('canvas-stage');
    if (stage) stage.style.cursor = tool === 'select' ? 'default' : 'crosshair';
    Logger.log('set_tool', { tool });
  },

  // ---- Keyboard shortcuts ----
  bindKeyboard() {
    document.addEventListener('keydown', e => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.contentEditable === 'true') return;

      switch(e.key.toLowerCase()) {
        case 'v': this.setTool('select'); break;
        case 't': this.setTool('text'); break;
        case 'i': this.setTool('image'); break;
        case 's': if (!e.ctrlKey && !e.metaKey) this.setTool('shape'); break;
        case 'c': if (!e.ctrlKey && !e.metaKey) this.setTool('caption'); break;
        case ' ': e.preventDefault(); this.togglePlay(); break;
        case 'delete':
        case 'backspace':
          if (this.currentElement) this.deleteElement(this.currentElement.id);
          break;
        case 'escape':
          this.deselectAll();
          break;
        case 'z':
          if ((e.ctrlKey || e.metaKey) && e.shiftKey) { e.preventDefault(); this.redo(); }
          else if (e.ctrlKey || e.metaKey) { e.preventDefault(); this.undo(); }
          break;
        case 'y':
          if (e.ctrlKey || e.metaKey) { e.preventDefault(); this.redo(); }
          break;
        case 'c':
          if (e.ctrlKey || e.metaKey) { e.preventDefault(); this.copyElement(); }
          break;
        case 'v':
          if (e.ctrlKey || e.metaKey) { e.preventDefault(); this.pasteElement(); }
          break;
      }
    });
  },

  // ---- Canvas events ----
  bindCanvasEvents() {
    const stage = document.getElementById('canvas-stage');
    if (!stage) return;

    // Drag-to-create state
    this._dragCreate = null;

    stage.addEventListener('pointerdown', e => {
      Logger.log('canvas_pointerdown', { target: e.target.id || e.target.className });
      if (e.target === stage || e.target.id === 'empty-state' || e.target.closest('.empty-state')) {
        if (this.tool !== 'select') {
          // Start drag-to-create for text/shape/caption
          if (this.tool === 'text' || this.tool === 'shape' || this.tool === 'caption') {
            this.startDragCreate(e);
          } else {
            this.createElementAtPointer(e);
          }
        } else {
          this.deselectAll();
        }
      }
    });

    document.addEventListener('pointermove', e => {
      this._lastPointerX = e.clientX;
      this._lastPointerY = e.clientY;
      if (this.dragState) this.handleDrag(e);
      if (this.resizeState) this.handleResize(e);
      if (this._playheadDrag) this.handlePlayheadDrag(e);
      if (this._dragCreate) this.handleDragCreate(e);
    });

    document.addEventListener('pointerup', () => {
      if (this.dragState) Logger.log('drag_end', { eid: this.dragState.el?.id });
      if (this.resizeState) Logger.log('resize_end', { eid: this.resizeState.el?.id });
      if (this._dragCreate) this.finishDragCreate();
      this.finishInteraction();  // saves scene after drag/resize
      this._playheadDrag = false;
    });
  },

  // ---- Drag-to-create ----
  startDragCreate(e) {
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    const scale = rect.width / cw;

    const x = ((e.clientX - rect.left) / scale) / cw * 100;
    const y = ((e.clientY - rect.top) / scale) / ch * 100;

    this._dragCreate = {
      startX: e.clientX,
      startY: e.clientY,
      x, y,
      tool: this.tool
    };

    // Create a selection rectangle
    const selRect = document.createElement('div');
    selRect.className = 'selection-rect';
    selRect.id = 'sel-rect';
    stage.appendChild(selRect);
  },

  handleDragCreate(e) {
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    const scale = rect.width / cw;
    const dc = this._dragCreate;
    if (!dc) return;

    const x2 = ((e.clientX - rect.left) / scale) / cw * 100;
    const y2 = ((e.clientY - rect.top) / scale) / ch * 100;

    const left = Math.min(dc.x, x2);
    const top = Math.min(dc.y, y2);
    const width = Math.abs(x2 - dc.x);
    const height = Math.abs(y2 - dc.y);

    const selRect = document.getElementById('sel-rect');
    if (selRect) {
      selRect.style.left = (left / 100 * cw) + 'px';
      selRect.style.top = (top / 100 * ch) + 'px';
      selRect.style.width = (width / 100 * cw) + 'px';
      selRect.style.height = (height / 100 * ch) + 'px';
    }
  },

  finishDragCreate() {
    const dc = this._dragCreate;
    if (!dc) return;
    const selRect = document.getElementById('sel-rect');

    // Calculate final dimensions
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    const scale = rect.width / cw;

    const endX = ((dc.startX - rect.left) / scale) / cw * 100;
    const endY = ((dc.startY - rect.top) / scale) / ch * 100;
    const endX2 = ((this._lastPointerX - rect.left) / scale) / cw * 100;
    const endY2 = ((this._lastPointerY - rect.top) / scale) / ch * 100;

    const x = Math.min(endX, endX2);
    const y = Math.min(endY, endY2);
    let w = Math.abs(endX2 - endX);
    let h = Math.abs(endY2 - endY);

    // Minimum size
    if (w < 5) w = 20;
    if (h < 3) h = 5;

    // Remove selection rectangle
    if (selRect) selRect.remove();
    this._dragCreate = null;
    this.setTool('select');

    // Create the element
    if (dc.tool === 'text') {
      this.addElement({ type: 'text', content: 'New Text', x, y, width: w, height: h, font: 'Inter', size: 48, color: '#FFFFFF' });
    } else if (dc.tool === 'shape') {
      this.addElement({ type: 'shape', shape: this._currentShape || 'rect', x, y, width: w, height: h, fill: '#4a9eff', border_radius: 0 });
    } else if (dc.tool === 'caption') {
      this.addElement({ type: 'caption', content: 'Caption', x, y, width: w, height: h, words: [{ text: 'Caption', start: 0, end: 1 }], style: { font: 'Inter', size: 46, color: '#FFFFFF', bg_color: 'rgba(0,0,0,0.7)', border_radius: 12 } });
    }
  },

  // ---- Timeline interactions (scrubbing, click-to-seek) ----
  bindTimelineInteractions() {
    const tracks = document.getElementById('timeline-tracks');
    const playhead = document.getElementById('playhead');
    if (!tracks || !playhead) return;

    // Click on tracks area to seek
    tracks.addEventListener('pointerdown', e => {
      if (e.target.closest('.timeline-segment')) return; // don't interfere with segment clicks
      const rect = tracks.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.max(0, Math.min(1, x / rect.width));
      this.seekTo(pct * this.duration);
      Logger.log('timeline_seek', { pct: pct.toFixed(3), time: this.currentTime.toFixed(2) });
    });

    // Drag the playhead
    playhead.style.pointerEvents = 'auto';
    playhead.style.cursor = 'col-resize';
    playhead.addEventListener('pointerdown', e => {
      e.stopPropagation();
      this._playheadDrag = true;
      Logger.log('playhead_drag_start');
    });
  },

  handlePlayheadDrag(e) {
    const tracks = document.getElementById('timeline-tracks');
    if (!tracks) return;
    const rect = tracks.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, x / rect.width));
    this.seekTo(pct * this.duration);
  },

  // ---- Timeline resize (drag top edge) ----
  bindTimelineResize() {
    const handle = document.getElementById('timeline-resize-handle');
    const timeline = document.getElementById('timeline');
    if (!handle || !timeline) return;

    let startY = null, startH = null;

    handle.addEventListener('pointerdown', e => {
      e.preventDefault();
      startY = e.clientY;
      startH = timeline.offsetHeight;
      handle.setPointerCapture(e.pointerId);
      Logger.log('timeline_resize_start', { startH });
    });

    handle.addEventListener('pointermove', e => {
      if (startY === null) return;
      const dy = startY - e.clientY; // drag UP = bigger timeline
      const newH = Math.max(80, Math.min(startH + dy, window.innerHeight * 0.7));
      // Update the CSS grid row
      const app = document.getElementById('app');
      if (app) {
        app.style.gridTemplateRows = `48px 1fr ${newH}px`;
      }
      this.scaleCanvas();
    });

    handle.addEventListener('pointerup', () => {
      startY = null;
      Logger.log('timeline_resize_end');
    });
  },

  seekTo(time) {
    const prev = this.currentTime;
    this.currentTime = Math.max(0, Math.min(time, this.duration));
    console.log(`[SEEK] prev=${prev.toFixed(2)} → target=${this.currentTime.toFixed(2)} audioReady=${this.audio?.readyState} audioTime=${this.audio?.currentTime?.toFixed(2)} playing=${this.playing}`);
    this._seeking = true;
    if (this.audio) {
      this.audio.currentTime = this.currentTime;
      console.log(`[SEEK] after set audio.currentTime=${this.audio.currentTime.toFixed(2)}`);
    }
    this.updateTimeDisplay();
    this.updatePlayhead();
    this.highlightWords();
    this.renderCanvas();
    setTimeout(() => { this._seeking = false; }, 100);
  },

  // ---- Canvas scaling ----
  scaleCanvas() {
    const area = document.getElementById('canvas-area');
    const scaler = document.getElementById('canvas-scaler');
    const wrapper = document.getElementById('canvas-wrapper');
    const stage = document.getElementById('canvas-stage');
    if (!area || !wrapper || !stage) return;

    const w = this.project?.width || 1920;
    const h = this.project?.height || 1080;
    const pad = 40;
    const areaW = area.clientWidth - pad;
    const areaH = area.clientHeight - pad;
    const scale = Math.min(areaW / w, areaH / h, 1);

    // Stage: actual canvas resolution
    stage.style.width = w + 'px';
    stage.style.height = h + 'px';
    stage.style.background = this.currentScene?.bg_color || '#ffffff';

    // Wrapper: full resolution, scaled via CSS transform
    wrapper.style.width = w + 'px';
    wrapper.style.height = h + 'px';
    wrapper.style.transform = `scale(${scale})`;

    // Scaler: sized to the VISUAL (post-transform) dimensions
    // This is what flex centers — matches the visual size
    if (scaler) {
      scaler.style.width = Math.ceil(w * scale) + 'px';
      scaler.style.height = Math.ceil(h * scale) + 'px';
    }

    // Canvas scaled
  },

  // ---- Project management ----
  async loadProjects() {
    const res = await fetch(`${API}/api/projects`);
    return await res.json();
  },

  async openProjects() {
    Logger.log('open_projects');
    const projects = await this.loadProjects();
    let html = '<div class="modal-overlay" onclick="if(event.target===this)App.closeModal()">';
    html += '<div class="modal">';
    html += '<div class="modal-title">My Projects</div>';
    if (projects.length === 0) {
      html += '<p style="color:var(--text-dim)">No projects yet. Create one or import from Word Editor.</p>';
    } else {
      html += '<div class="project-list">';
      for (const p of projects) {
        html += `<div class="project-card" onclick="App.loadProject('${p.id}')">
          <div class="project-card-name">${this.esc(p.name)}</div>
          <div class="project-card-meta">${p.width}×${p.height}</div>
          <button class="btn sm danger" onclick="event.stopPropagation();App.deleteProject('${p.id}')">🗑</button>
        </div>`;
      }
      html += '</div>';
    }
    html += '<div class="modal-actions">';
    html += '<button class="btn" onclick="App.closeModal()">Cancel</button>';
    html += '<button class="btn primary" onclick="App.closeModal();App.createNew()">New Project</button>';
    html += '</div></div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
  },

  // Stop playback + save state before switching
  stopPlayback() {
    if (this.audio) {
      this.audio.pause();
      this.audio = null;
    }
    this.playing = false;
    if (this._renderRAF) { cancelAnimationFrame(this._renderRAF); this._renderRAF = null; }
    if (this._sceneHighlightRAF) { cancelAnimationFrame(this._sceneHighlightRAF); this._sceneHighlightRAF = null; }
    this.currentTime = 0;
    this.duration = 0;
    this.currentElement = null;
    this.updatePlayButton();
    this.updateTimeDisplay();
    this.updatePlayhead();
    this.updateAudioInfo();
  },

  async loadProject(pid) {
    this.closeModal();
    // Stop everything from the previous project
    this.stopPlayback();

    Logger.log('load_project', { pid });
    const res = await fetch(`${API}/api/projects/${pid}`);
    this.project = await res.json();
    this.scenes = this.project.scenes || [];
    this.currentScene = this.scenes[0] || null;
    this.duration = this._getProjectDuration();

    document.getElementById('project-name').textContent = this.project.name;
    document.getElementById('empty-state').style.display = 'none';

    this.renderSceneStrip();
    this.renderCanvas();
    this.renderTimeline();
    this.scaleCanvas();
    this.toast(`Loaded "${this.project.name}"`);
  },

  async createNew() {
    const name = prompt('Project name:', 'Untitled');
    if (!name) return;
    Logger.log('create_project', { name });
    const res = await fetch(`${API}/api/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, width: 1920, height: 1080 })
    });
    const proj = await res.json();
    await this.loadProject(proj.id);
  },

  async deleteProject(pid) {
    if (!confirm('Delete this project?')) return;
    Logger.log('delete_project', { pid });
    await fetch(`${API}/api/projects/${pid}`, { method: 'DELETE' });
    this.toast('Project deleted');
    this.closeModal();
    this.openProjects();
  },

  // ---- AI Scene Generation ----
  async generateScenes() {
    if (!this.project) { this.toast('Open a project first', 'error'); return; }
    Logger.log('generate_scenes', { pid: this.project.id });
    this.toast('Generating scenes from audio timestamps...');
    try {
      const res = await fetch(`${API}/api/projects/${this.project.id}/generate-scenes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ words_per_scene: 80, theme: 'tech' })
      });
      const data = await res.json();
      if (data.error) {
        this.toast(data.error, 'error');
        return;
      }
      // Reload project to get new scenes
      await this.loadProject(this.project.id);
      this.toast(`Generated ${data.scenes.length} scenes with ${data.total_elements} elements!`);
      Logger.log('scenes_generated', { count: data.scenes.length, elements: data.total_elements });
    } catch (err) {
      this.toast('Scene generation failed: ' + err.message, 'error');
      Logger.log('scenes_gen_error', { error: err.message });
    }
  },

  // ---- Import from Word Editor ----
  async openImportModal() {
    Logger.log('open_import_modal');
    const res = await fetch(`${API}/api/import/audio-projects`);
    const projects = await res.json();

    let html = '<div class="modal-overlay" onclick="if(event.target===this)App.closeModal()">';
    html += '<div class="modal">';
    html += '<div class="modal-title">Import from Word Editor</div>';
    html += '<p style="color:var(--text-dim);margin-bottom:12px">Select an audio project to import:</p>';
    if (projects.length === 0) {
      html += '<p style="color:var(--text-dim)">No Word Editor projects found.</p>';
    } else {
      html += '<div class="import-list">';
      for (const p of projects) {
        if (!p.has_audio) continue;
        html += `<div class="import-item" data-pid="${p.id}" onclick="App.selectImport(this, '${p.id}')">
          <div class="import-item-name">${this.esc(p.name)}</div>
          <div class="import-item-meta">${p.source} · ${this.fmtDuration(p.duration)} · ${p.word_count || 0} words</div>
        </div>`;
      }
      html += '</div>';
    }
    html += '<div class="modal-actions">';
    html += '<button class="btn" onclick="App.closeModal()">Cancel</button>';
    html += '<button class="btn primary" id="import-btn" disabled onclick="App.doImport()">Import</button>';
    html += '</div></div></div>';
    document.body.insertAdjacentHTML('beforeend', html);
    this._selectedImportPid = null;
  },

  selectImport(el, pid) {
    document.querySelectorAll('.import-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    this._selectedImportPid = pid;
    document.getElementById('import-btn').disabled = false;
    Logger.log('select_import', { pid });
  },

  async doImport() {
    if (!this._selectedImportPid) return;
    this.closeModal();
    Logger.log('do_import', { we_pid: this._selectedImportPid });

    // Stop previous project first
    this.stopPlayback();

    const res = await fetch(`${API}/api/import/from-audio/${this._selectedImportPid}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();
    if (data.error) {
      this.toast(data.error, 'error');
      return;
    }
    await this.loadProject(data.id);
    this.toast('Imported successfully!');
  },

  // ---- Audio management ----
  removeAudio() {
    if (!this.currentScene) return;
    Logger.log('remove_audio', { scene_id: this.currentScene.id });
    this.stopPlayback();
    this.currentScene.audio_track = null;
    this.saveScene();
    this.updateAudioInfo();
    this.toast('Audio removed');
  },

  updateAudioInfo() {
    const info = document.getElementById('audio-info');
    if (!info) return;
    // Check global audio source
    let src = this.project?.audio?.source;
    if (!src) {
      for (const s of this.scenes) {
        if (s.audio_track?.source) { src = s.audio_track.source; break; }
      }
    }
    if (!src && this.project?.audio_source) {
      src = this.project.audio_source;
    }
    if (src && this.duration > 0) {
      const filename = src.split(/[/\\]/).pop() || 'audio';
      info.innerHTML = `
        <span class="audio-info-name">${this.esc(filename)}</span>
        <span class="audio-info-sep">·</span>
        <span class="audio-info-duration">${this.fmtDuration(this.duration)}</span>
      `;
      info.style.display = 'flex';
    } else {
      info.innerHTML = '';
      info.style.display = 'none';
    }
  },

  // ---- Scene management ----
  renderSceneStrip() {
    const strip = document.getElementById('scene-strip');
    strip.innerHTML = '';
    this.scenes.forEach((s, i) => {
      const chip = document.createElement('div');
      chip.className = 'scene-chip' + (s.id === this.currentScene?.id ? ' active' : '');
      chip.dataset.sid = s.id;
      chip.dataset.idx = i;
      chip.draggable = true;

      const elemCount = (s.elements || []).length;
      const dur = s.duration || 10;
      chip.innerHTML = `<div class="scene-chip-name">${this.esc(s.name || `Scene ${i + 1}`)}</div>`
        + `<div class="scene-chip-meta">${elemCount} el · ${this.fmtDuration(dur)}</div>`;

      chip.onclick = () => { Logger.log('select_scene', { sid: s.id }); this.selectScene(s.id); };

      // Drag-to-reorder
      chip.addEventListener('dragstart', e => {
        e.dataTransfer.setData('text/plain', i);
        chip.classList.add('dragging');
      });
      chip.addEventListener('dragend', () => chip.classList.remove('dragging'));
      chip.addEventListener('dragover', e => { e.preventDefault(); chip.classList.add('drag-over'); });
      chip.addEventListener('dragleave', () => chip.classList.remove('drag-over'));
      chip.addEventListener('drop', e => {
        e.preventDefault();
        chip.classList.remove('drag-over');
        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
        const toIdx = i;
        if (fromIdx !== toIdx) {
          const [moved] = this.scenes.splice(fromIdx, 1);
          this.scenes.splice(toIdx, 0, moved);
          this.saveScene();
          this.renderSceneStrip();
          Logger.log('reorder_scene', { from: fromIdx, to: toIdx });
        }
      });

      strip.appendChild(chip);
    });
    document.getElementById('scene-info').textContent =
      this.scenes.length ? `${this.scenes.length} scene(s) · ${this.fmtDuration(this.duration)}` : 'No scenes';
  },

  selectScene(sid) {
    const targetScene = this.scenes.find(s => s.id === sid) || this.scenes[0];
    if (!targetScene) return;

    console.log(`[SCENE] selectScene called: sid=${sid} currentScene=${this.currentScene?.id} playing=${this.playing} audioTime=${this.audio?.currentTime?.toFixed(2)}`);

    // If clicking the already-active scene, just deselect current element
    if (this.currentScene && this.currentScene.id === targetScene.id) {
      console.log('[SCENE] same scene — deselecting only');
      this.currentElement = null;
      this.renderCanvas();
      this.renderProperties();
      return;
    }

    this.currentScene = targetScene;
    this.currentElement = null;
    const sceneOffset = this._getSceneTimeOffset(this.currentScene);
    console.log(`[SCENE] seeking to sceneOffset=${sceneOffset.toFixed(2)} scene=${targetScene.name}`);
    this.currentTime = sceneOffset;
    if (this.audio) {
      this.audio.currentTime = this.currentTime;
      console.log(`[SCENE] audio.currentTime set to ${this.audio.currentTime.toFixed(2)}`);
    }
    this.updateTimeDisplay();
    this.updatePlayhead();
    this.renderSceneStrip();
    this.renderCanvas();
    this.renderTimeline();
    this.renderProperties();
    this.scaleCanvas();
  },

  async addScene() {
    if (!this.project) return;
    Logger.log('add_scene');
    const res = await fetch(`${API}/api/projects/${this.project.id}/scenes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: `Scene ${this.scenes.length + 1}`, duration: 10 })
    });
    const scene = await res.json();
    this.scenes.push(scene);
    this.currentScene = scene;
    this.renderSceneStrip();
    this.renderCanvas();
    this.renderTimeline();
    this.toast('Scene added');
  },

  async deleteScene() {
    if (!this.project || !this.currentScene) return;
    if (!confirm('Delete this scene?')) return;
    Logger.log('delete_scene', { sid: this.currentScene.id });
    await fetch(`${API}/api/projects/${this.project.id}/scenes/${this.currentScene.id}`, { method: 'DELETE' });
    this.scenes = this.scenes.filter(s => s.id !== this.currentScene.id);
    this.currentScene = this.scenes[0] || null;
    this.renderSceneStrip();
    this.renderCanvas();
    this.renderTimeline();
    this.toast('Scene deleted');
  },  // ---- Canvas rendering ----
  renderCanvas() {
    const stage = document.getElementById('canvas-stage');
    if (!stage) { console.error('[Canvas] stage element NOT FOUND'); return; }

    // Remove all canvas elements (keep empty-state if present)
    stage.querySelectorAll('.canvas-el').forEach(el => el.remove());
    stage.querySelectorAll('.selection-rect').forEach(el => el.remove());
    const empty = document.getElementById('empty-state');
    if (empty) empty.style.display = 'none';

    // Global audio: load once from project if available
    this._loadGlobalAudio();

    // Determine which scene(s) are active based on currentTime
    const activeScene = this._getActiveScene();
    const scene = activeScene || this.currentScene;
    if (!scene) {
      // Show empty state — don't destroy it with innerHTML
      stage.style.background = '#0e1116';
      if (empty) { empty.style.display = ''; }
      return;
    }

    // Apply background — use backgroundColor (not shorthand) so CSS class patterns work
    stage.className = 'canvas-stage'; // reset classes first
    if (scene.bg_pattern) {
      stage.classList.add(scene.bg_pattern);
      stage.style.background = '';
      stage.style.backgroundColor = scene.bg_color || '#ffffff';
    } else {
      stage.style.background = scene.bg_color || '#ffffff';
    }

    // Render crossfade overlay for scene transitions
    this._renderSceneTransitions(stage);

    const w = this.project?.width || 1920;
    const h = this.project?.height || 1080;
    const t = this.currentTime;
    let renderedCount = 0;
    const transitionDur = 1.0;

    // Compute scene transition fade for each scene
    // _sceneFade[sceneId] = { fadeIn: 0-1, fadeOut: 0-1 }
    this._sceneFade = {};
    let _sOff = 0;
    for (let si = 0; si < this.scenes.length; si++) {
      const sDur = this.scenes[si].duration || 10;
      const sEnd = _sOff + sDur;
      let fadeIn = 1, fadeOut = 1;
      // Fade in at the start (except first scene)
      if (si > 0) {
        const fadeInProgress = (t - _sOff) / transitionDur;
        if (t < _sOff) fadeIn = 0;
        else if (fadeInProgress < 1) fadeIn = fadeInProgress;
        else fadeIn = 1;
      }
      // Fade out at the end (except last scene)
      if (si < this.scenes.length - 1) {
        const fadeOutProgress = (sEnd - t) / transitionDur;
        if (t > sEnd) fadeOut = 0;
        else if (fadeOutProgress < 1) fadeOut = fadeOutProgress;
        else fadeOut = 1;
      }
      this._sceneFade[this.scenes[si].id] = { fadeIn, fadeOut };
      _sOff += sDur;
    }

    // Render elements from ALL scenes based on absolute time
    for (const s of this.scenes) {
      const sceneOffset = this._getSceneTimeOffset(s);
      const elements = s.elements || [];
      const fadeInfo = this._sceneFade[s.id] || { fadeIn: 1, fadeOut: 1 };
      const sceneOpacity = Math.min(fadeInfo.fadeIn, fadeInfo.fadeOut);
      for (const el of elements) {
        // Convert scene-local times to absolute project times
        const absStart = (el.start ?? 0) + sceneOffset;
        const absEnd = (el.end ?? 5) + sceneOffset;
        // Captions need precise timing — no buffer to prevent overlap
        // Other elements get a small buffer for smooth enter/exit animations
        const isCaption = el.type === 'caption';
        const buffer = isCaption ? 0.05 : 0.5;
        if (t < absStart - buffer || t > absEnd + buffer) continue;
        this.renderElement(el, stage, w, h, absStart, absEnd, sceneOpacity);
        renderedCount++;
      }
    }

    // Log render stats (non-playing: always; playing: every 10th frame)
    if (!this.playing || (this._frameLogCount = (this._frameLogCount || 0) + 1) % 10 === 0) {
      console.log(`[Canvas] t=${t.toFixed(2)} rendered=${renderedCount} scenes=${this.scenes.length} bg=${scene.bg_color || scene.bg_pattern || 'none'}`);
    }

    // Highlight the active scene in the strip
    this._highlightActiveScene();

    this.duration = this._getProjectDuration();
    this.updateTimeDisplay();
    this.updateAudioInfo();

    // Log what's visible on canvas during playback (every 5th frame)
    if (this.playing) {
      if (this._frameLogCount % 5 === 0) {
        const visibleEls = stage.querySelectorAll('.canvas-el');
        Logger.log('canvas_frame', {
          time: t.toFixed(2),
          visible: visibleEls.length,
          types: Array.from(visibleEls).map(e => e.dataset.type).join(',') || 'none',
          scene: scene?.name || 'none'
        });
      }
    }
  },

  // ---- Global audio: one continuous track across all scenes ----
  _loadGlobalAudio() {
    // Priority: project-level audio > any scene's audio_track > audio_source
    let src = this.project?.audio?.source;
    if (!src) {
      // Search all scenes for an audio_track
      for (const s of this.scenes) {
        if (s.audio_track?.source) { src = s.audio_track.source; break; }
      }
    }
    // Also check the project's audio_source (Word Editor source path)
    if (!src && this.project?.audio_source) {
      // audio_source could be a WE project ID — try standard naming
      const we_pid = this.project.audio_source;
      src = `/audio/${we_pid}/source.mp3`;
    }
    if (!src) return;
    if (this.audio && this._lastAudioSrc === src) {
      console.log('[AUDIO] _loadGlobalAudio: guard OK, skipping');
      return;
    }
    console.log('[AUDIO] _loadGlobalAudio: LOADING! src=' + src + ' audioExists=' + !!this.audio + ' lastSrc=' + this._lastAudioSrc);
    this.loadAudio(src);
  },

  // ---- Scene time math ----
  _getSceneTimeOffset(targetScene) {
    // Calculate absolute start time of a scene based on cumulative durations
    let offset = 0;
    for (const s of this.scenes) {
      if (s.id === targetScene.id) return offset;
      offset += s.duration || 10;
    }
    return offset;
  },

  _getProjectDuration() {
    return this.scenes.reduce((sum, s) => sum + (s.duration || 10), 0);
  },

  _getActiveScene() {
    // Find which scene contains the current playback time
    let offset = 0;
    for (const s of this.scenes) {
      const dur = s.duration || 10;
      if (this.currentTime >= offset && this.currentTime < offset + dur) {
        return s;
      }
      offset += dur;
    }
    // Past all scenes — return last scene
    return this.scenes[this.scenes.length - 1] || null;
  },

  _highlightActiveScene() {
    const t = this.currentTime;
    let offset = 0;
    let activeId = null;
    for (const s of this.scenes) {
      const dur = s.duration || 10;
      if (t >= offset && t < offset + dur) {
        activeId = s.id;
        break;
      }
      offset += dur;
    }
    if (!activeId && this.scenes.length) activeId = this.scenes[this.scenes.length - 1].id;
    document.querySelectorAll('.scene-chip').forEach(chip => {
      chip.classList.toggle('active', chip.dataset.sid === activeId);
    });
  },

  // ---- Scene transition crossfade ----
  // Returns { fadeOut: 0-1, fadeIn: 0-1, transitionDur } for the current time
  _getSceneTransitionInfo() {
    const transitionDur = 1.0; // 1 second crossfade
    const t = this.currentTime;
    let offset = 0;
    for (let i = 0; i < this.scenes.length; i++) {
      const dur = this.scenes[i].duration || 10;
      const sceneEnd = offset + dur;

      // At the END of scene i (transitioning to i+1)
      if (i < this.scenes.length - 1) {
        if (t >= sceneEnd - transitionDur && t < sceneEnd) {
          // Outgoing scene fading out
          const progress = (t - (sceneEnd - transitionDur)) / transitionDur;
          return { fadeOut: 1 - progress, fadeIn: 0, transitionDur };
        }
        if (t >= sceneEnd && t < sceneEnd + transitionDur) {
          // Incoming scene fading in
          const progress = (t - sceneEnd) / transitionDur;
          return { fadeOut: 0, fadeIn: Math.min(1, progress), transitionDur };
        }
      }

      offset += dur;
    }
    return { fadeOut: 0, fadeIn: 0, transitionDur };
  },

  _renderSceneTransitions(stage) {
    // Remove old transition overlays
    stage.querySelectorAll('.scene-transition').forEach(el => el.remove());
    if (this.scenes.length < 2) return;

    const t = this.currentTime;
    const transitionDur = 1.0;
    let offset = 0;

    for (let i = 0; i < this.scenes.length; i++) {
      const dur = this.scenes[i].duration || 10;
      const sceneEnd = offset + dur;

      // Show next scene background fading in during transition
      if (i < this.scenes.length - 1 && t >= sceneEnd - transitionDur && t <= sceneEnd + transitionDur) {
        const nextScene = this.scenes[i + 1];
        const overlay = document.createElement('div');
        overlay.className = 'scene-transition';
        overlay.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;z-index:998;pointer-events:none;';

        // Calculate blend
        let opacity;
        if (t < sceneEnd) {
          opacity = (t - (sceneEnd - transitionDur)) / (2 * transitionDur);
        } else {
          opacity = 0.5 + (t - sceneEnd) / (2 * transitionDur);
        }
        opacity = Math.max(0, Math.min(1, opacity));
        overlay.style.opacity = opacity;
        overlay.style.background = nextScene.bg_color || '#0e1116';
        if (nextScene.bg_pattern) overlay.classList.add(nextScene.bg_pattern);
        stage.appendChild(overlay);
      }

      offset += dur;
    }
  },

  renderElement(el, stage, canvasW, canvasH, elStart, elEnd, sceneOpacity) {
    if (sceneOpacity === undefined) sceneOpacity = 1;
    const div = document.createElement('div');
    div.className = 'canvas-el';
    div.dataset.eid = el.id;
    div.dataset.type = el.type;

    let x = this.toPx(el.x, canvasW);
    let y = this.toPx(el.y, canvasH);
    const w = this.toPx(el.width, canvasW);
    let hh = this.toPx(el.height, canvasH);

    // Caption position presets override x/y
    if (el.type === 'caption' && el.style?.position && el.style.position !== 'custom') {
      const pos = el.style.position;
      const xOff = (el.style.x_offset || 50) / 100;
      const yOff = (el.style.y_offset || 85) / 100;
      if (pos === 'top') { y = canvasH * 0.05; x = canvasW * xOff - w / 2; }
      else if (pos === 'center') { y = canvasH * 0.45; x = canvasW * xOff - w / 2; }
      else if (pos === 'bottom') { y = canvasH * 0.82; x = canvasW * xOff - w / 2; }
      div.style.left = x + 'px';
      div.style.top = y + 'px';
      div.style.width = Math.min(w, canvasW * 0.9) + 'px';
      div.style.height = hh + 'px';
    } else {
      div.style.left = x + 'px';
      div.style.top = y + 'px';
      div.style.width = w + 'px';
      div.style.height = hh + 'px';
    }

    // --- 3-Phase Animation system (Entrance + Emphasis + Exit) ---
    const t = this.currentTime;
    const elapsed = t - (elStart ?? 0);
    const remaining = (elEnd ?? t) - t;
    const elDur = (elEnd ?? 0) - (elStart ?? 0);

    // Backward compat: old { type, duration } → entrance
    const raw = el.animation;
    const entrance = el.entrance || (typeof raw === 'object' && raw?.type ? raw : (raw && raw !== 'none' ? { type: raw } : { type: 'none' }));
    const emphasis = el.emphasis || { type: 'none' };
    const exit = el.exit || { type: 'none' };

    const enType = entrance?.type || 'none';
    const enDur = entrance?.duration || 0.6;
    const emType = emphasis?.type || 'none';
    const emDur = emphasis?.duration || 0.4;
    const exType = exit?.type || 'none';
    const exDur = exit?.duration || 0.5;

    // Determine which phase we're in
    const inEntrance = elapsed >= 0 && elapsed < enDur + 0.05;
    const inExit = remaining >= 0 && remaining < exDur && !inEntrance;
    const inEmphasis = !inEntrance && !inExit && elDur > enDur + exDur + 0.1;

    // -- ENTRANCE --
    if (inEntrance && enType !== 'none') {
      const p = Math.min(1, elapsed / enDur);
      const e = 1 - Math.pow(1 - p, 3);
      this._applyAnimType(div, enType, e, elapsed, 'enter');
    }
    // -- EXIT --
    else if (inExit && exType !== 'none') {
      const p = 1 - (remaining / exDur);
      const e = Math.min(1, p);
      this._applyExitType(div, exType, e, remaining);
    }
    // -- EMPHASIS (mid-life effects) --
    else if (inEmphasis && emType !== 'none') {
      this._applyEmphasisType(div, emType, elapsed - enDur, elDur - enDur - exDur);
    }
    // -- STABLE STATE --
    else if (elapsed >= enDur || !inEntrance) {
      div.style.opacity = '1';
      div.style.transform = 'none';
      div.style.filter = 'none';
      div.style.clipPath = 'none';
    }

    // Visibility toggle
    if (el.visible === false) {
      div.dataset.visible = 'false';
    }

    if (el.type === 'text') {
      div.style.fontFamily = `'${el.font || 'Inter'}'`;
      div.style.fontSize = (el.size || 48) + 'px';
      div.style.color = el.color || '#FFFFFF';
      div.style.fontWeight = el.weight || 'normal';
      div.style.textAlign = el.align || 'center';
      div.style.display = 'flex';
      div.style.alignItems = 'center';
      div.style.justifyContent = 'center';
      if (el.bg_color) { div.style.background = el.bg_color; div.style.padding = '12px 24px'; }
      if (el.border_radius) div.style.borderRadius = el.border_radius + 'px';
      if (el.glow) div.style.textShadow = `0 0 ${el.glow.radius || 10}px ${el.glow.color || '#FFD700'}`;
      if (el.text_shadow) div.style.textShadow = el.text_shadow;
      div.textContent = el.content || 'Text';
    }
    else if (el.type === 'caption') {
      const s = el.style || {};
      div.style.fontFamily = `'${s.font || 'Inter'}'`;
      div.style.fontSize = (s.size || 46) + 'px';
      div.style.color = s.color || '#FFFFFF';
      div.style.textAlign = s.align || 'center';
      div.style.display = 'flex';
      div.style.alignItems = 'center';
      div.style.justifyContent = 'center';
      div.style.padding = '12px 20px';

      const words = el.words || [];
      if (words.length > 0) {
        const boxClass = s.box_style || 'rounded';
        const wordAnim = s.word_animation || 'none';
        const wordDelay = s.word_delay || 0;
        const unspoken = s.unspoken || 'visible';
        let boxStyle = `background:${s.bg_color || 'rgba(0,0,0,0.7)'};border-radius:${s.border_radius || 12}px;padding:8px 16px`;
        if (boxClass === 'pill') boxStyle += ';border-radius:999px';
        else if (boxClass === 'circle') boxStyle += ';border-radius:50%;width:60px;height:60px;display:flex;align-items:center;justify-content:center';
        else if (boxClass === 'sharp') boxStyle += ';border-radius:0';
        else if (boxClass === 'none') boxStyle = 'background:transparent;padding:8px 16px';
        let wordHtml = words.map((w, i) =>
          `<span class="word" data-idx="${i}" data-word-anim="${wordAnim}" data-word-delay="${wordDelay * i}" data-unspoken="${unspoken}" style="display:inline-block;transition:all 0.3s ease">${this.esc(w.text)}</span>`
        ).join(' ');
        div.innerHTML = `<span class="caption-box ${boxClass}" style="${boxStyle}">${wordHtml}</span>`;
      } else {
        div.textContent = el.content || '';
      }
      // Apply text glow/shadow if set
      if (s.text_shadow) div.style.textShadow = s.text_shadow;
      // Caption hidden
      if (s.hidden) { div.dataset.visible = 'false'; }
    }
    else if (el.type === 'image') {
      const img = document.createElement('img');
      img.src = el.src || '';
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.objectFit = el.fit || 'cover';
      img.style.borderRadius = (el.border_radius || 0) + 'px';
      img.style.pointerEvents = 'none';
      img.draggable = false;
      div.appendChild(img);
      div.style.overflow = 'hidden';
    }
    else if (el.type === 'shape') {
      const shapeType = el.shape || 'rect';
      if (shapeType === 'circle') {
        div.style.borderRadius = '50%';
        div.style.background = el.fill || '#4a9eff';
      } else if (shapeType === 'triangle') {
        div.style.background = 'transparent';
        div.style.width = '0';
        div.style.height = '0';
        div.style.borderLeft = (w / 2) + 'px solid transparent';
        div.style.borderRight = (w / 2) + 'px solid transparent';
        div.style.borderBottom = hh + 'px solid ' + (el.fill || '#4a9eff');
      } else if (shapeType === 'line') {
        div.style.background = el.fill || '#FFFFFF';
        div.style.height = (el.stroke_width || 4) + 'px';
        div.style.borderRadius = '2px';
      } else {
        // Default: rectangle
        div.style.background = el.fill || '#4a9eff';
        div.style.borderRadius = (el.border_radius || 0) + 'px';
      }
      if (el.stroke && el.stroke !== 'none' && shapeType !== 'line') {
        div.style.border = `${el.stroke_width || 2}px solid ${el.stroke}`;
      }
    }

    // 8-point resize handles
    ['tl', 't', 'tr', 'r', 'br', 'b', 'bl', 'l'].forEach(pos => {
      const handle = document.createElement('div');
      handle.className = `resize-handle ${pos}`;
      handle.onpointerdown = e => {
        e.stopPropagation();
        this.startResize(el, pos, e);
      };
      div.appendChild(handle);
    });

    // Delete button
    const del = document.createElement('div');
    del.className = 'delete-btn';
    del.textContent = '×';
    del.onclick = e => { e.stopPropagation(); this.deleteElement(el.id); };
    div.appendChild(del);

    // Click to select
    div.onpointerdown = e => {
      e.stopPropagation();
      this.selectElement(el.id);
      if (this.tool === 'select') {
        this.startDrag(el, e);
      }
    };

    // Apply scene transition opacity — multiply with existing opacity
    if (sceneOpacity < 1) {
      const existingOpacity = parseFloat(div.style.opacity) || 1;
      div.style.opacity = Math.min(existingOpacity, sceneOpacity);
    }

    stage.appendChild(div);
  },

  // ---- Element interaction ----
  selectElement(eid) {
    this.currentElement = this.currentScene?.elements?.find(e => e.id === eid);
    document.querySelectorAll('.canvas-el').forEach(el => {
      el.classList.toggle('selected', el.dataset.eid === eid);
    });
    Logger.log('select_element', { eid });
    this.renderProperties();
  },

  // ---- 3-Phase Animation Engine ----
  _applyAnimType(div, type, p, elapsed, phase) {
    const e = 1 - Math.pow(1 - Math.min(1, p), 3); // ease-out cubic
    switch (type) {
      case 'fade-in': div.style.opacity = e; break;
      case 'slide-up': div.style.opacity = e; div.style.transform = `translateY(${(1 - e) * 60}px)`; break;
      case 'slide-down': div.style.opacity = e; div.style.transform = `translateY(${(e - 1) * 60}px)`; break;
      case 'slide-left': div.style.opacity = e; div.style.transform = `translateX(${(1 - e) * 80}px)`; break;
      case 'slide-right': div.style.opacity = e; div.style.transform = `translateX(${(e - 1) * 80}px)`; break;
      case 'zoom-in': div.style.opacity = e; div.style.transform = `scale(${0.3 + e * 0.7})`; break;
      case 'zoom-out': div.style.opacity = e; div.style.transform = `scale(${1.7 - e * 0.7})`; break;
      case 'bounce': {
        const b = e < 0.6 ? (e / 0.6) : 1 + Math.sin((e - 0.6) * Math.PI * 2.5) * 0.15 * (1 - e);
        div.style.opacity = Math.min(1, e * 2);
        div.style.transform = `translateY(${(1 - b) * 50}px) scale(${0.8 + b * 0.2})`;
        break;
      }
      case 'elastic': {
        const el = 1 + Math.sin(elapsed * 8) * Math.exp(-elapsed * 3) * 0.3;
        div.style.opacity = e; div.style.transform = `scale(${el})`; break;
      }
      case 'kinetic-in': {
        div.style.animation = `vc-kinetic-in ${0.6}s cubic-bezier(0.23,1,0.32,1) both`; break;
      }
      case 'morph-scale': {
        div.style.animation = `vc-morph-scale ${0.7}s cubic-bezier(0.23,1,0.32,1) both`; break;
      }
      case 'typewriter': div.style.opacity = e; div.style.clipPath = `inset(0 ${(1 - e) * 100}% 0 0)`; break;
      case 'spin-in': div.style.opacity = e; div.style.transform = `rotate(${(1 - e) * 180}deg) scale(${0.3 + e * 0.7})`; break;
      case 'counter-spin': {
        div.style.animation = `vc-counter-spin ${0.8}s cubic-bezier(0.23,1,0.32,1) both`; break;
      }
      case 'flip-in': {
        div.style.animation = `vc-flip-y ${0.7}s cubic-bezier(0.23,1,0.32,1) both`; break;
      }
      case 'blur-in': div.style.opacity = e; div.style.filter = `blur(${(1 - e) * 10}px)`; break;
      case 'glow-pulse': {
        div.style.opacity = e;
        const glow = Math.sin(elapsed * 4) * 0.5 + 0.5;
        div.style.textShadow = `0 0 ${10 + glow * 20}px ${div.style.color || '#FFD700'}`;
        break;
      }
    }
  },

  _applyExitType(div, type, p, remaining) {
    const e = Math.min(1, p);
    switch (type) {
      case 'fade-out': div.style.opacity = 1 - e; break;
      case 'exit-shrink': {
        div.style.animation = `vc-exit-shrink ${0.5}s ease-in both`; break;
      }
      case 'exit-fly-right': {
        div.style.animation = `vc-exit-fly-right ${0.5}s ease-in both`; break;
      }
      case 'exit-fly-up': {
        div.style.animation = `vc-exit-fly-up ${0.5}s ease-in both`; break;
      }
      case 'exit-dissolve': {
        div.style.animation = `vc-exit-dissolve ${0.6}s ease-in both`; break;
      }
      case 'slide-down': div.style.opacity = 1 - e; div.style.transform = `translateY(${e * 60}px)`; break;
      case 'zoom-out': div.style.opacity = 1 - e; div.style.transform = `scale(${1 - e * 0.7})`; break;
      case 'blur-in': div.style.opacity = 1 - e; div.style.filter = `blur(${e * 10}px)`; break;
      default: div.style.opacity = 1 - e;
    }
  },

  _applyEmphasisType(div, type, elapsedInPhase, phaseDur) {
    const cycle = elapsedInPhase * 3; // cycles per second
    switch (type) {
      case 'shake':
        div.style.animation = `vc-shake 0.5s ease-in-out infinite`;
        break;
      case 'glitch':
        div.style.animation = `vc-glitch 2s steps(1) infinite`;
        break;
      case 'glow-breathe':
        div.style.animation = `vc-glow-breathe 2s ease-in-out infinite`;
        div.style.setProperty('--glow-color', div.style.color || '#4a9eff');
        break;
      case 'elastic-wave':
        div.style.animation = `vc-elastic-wave 1.2s ease-in-out infinite`;
        break;
      case 'pulse': {
        const pulse = 1 + Math.sin(cycle * Math.PI) * 0.06;
        div.style.transform = `scale(${pulse})`;
        break;
      }
      case 'wave-float': {
        const yOff = Math.sin(cycle * Math.PI) * 4;
        const rot = Math.sin(cycle * Math.PI * 0.5) * 2;
        div.style.transform = `translateY(${yOff}px) rotate(${rot}deg)`;
        break;
      }
      case 'rotate-subtle': {
        const angle = Math.sin(cycle * Math.PI) * 3;
        div.style.transform = `rotate(${angle}deg)`;
        break;
      }
      case 'color-shift': {
        const hue = (elapsedInPhase * 30) % 360;
        div.style.filter = `hue-rotate(${hue}deg)`;
        break;
      }
    }
  },

  deselectAll() {
    this.currentElement = null;
    document.querySelectorAll('.canvas-el').forEach(el => el.classList.remove('selected'));
    this.renderProperties();
  },

  startDrag(el, e) {
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const scale = rect.width / (this.project?.width || 1920);
    this.pushUndo();
    this.dragState = {
      el,
      startX: e.clientX,
      startY: e.clientY,
      origX: this.toPx(el.x, this.project?.width || 1920),
      origY: this.toPx(el.y, this.project?.height || 1080),
      scale
    };
    Logger.log('drag_start', { eid: el.id });
  },

  handleDrag(e) {
    const { el, startX, startY, origX, origY, scale } = this.dragState;
    const dx = (e.clientX - startX) / scale;
    const dy = (e.clientY - startY) / scale;
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    let newX = Math.max(0, Math.min(origX + dx, cw - 10));
    let newY = Math.max(0, Math.min(origY + dy, ch - 10));
    // Snap-to-grid
    newX = this.snap(newX);
    newY = this.snap(newY);
    el.x = this.pxToPercent(newX, cw);
    el.y = this.pxToPercent(newY, ch);
    this.updateElementDOM(el);
    this.renderProperties();
  },

  // Called on pointerup after drag/resize
  finishInteraction() {
    if (this.dragState || this.resizeState) {
      this.saveScene();
    }
    this.dragState = null;
    this.resizeState = null;
  },

  startResize(el, corner, e) {
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const scale = rect.width / (this.project?.width || 1920);
    this.pushUndo();
    this.resizeState = {
      el, corner,
      startX: e.clientX,
      startY: e.clientY,
      origX: this.toPx(el.x, this.project?.width || 1920),
      origY: this.toPx(el.y, this.project?.height || 1080),
      origW: this.toPx(el.width, this.project?.width || 1920),
      origH: this.toPx(el.height, this.project?.height || 1080),
      scale
    };
    Logger.log('resize_start', { eid: el.id, corner });
  },

  handleResize(e) {
    const { el, corner, startX, startY, origX, origY, origW, origH, scale } = this.resizeState;
    const dx = (e.clientX - startX) / scale;
    const dy = (e.clientY - startY) / scale;
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;

    let newX = origX, newY = origY, newW = origW, newH = origH;

    // Corners
    if (corner === 'tl') { newW = Math.max(20, origW - dx); newH = Math.max(20, origH - dy); newX = origX + dx; newY = origY + dy; }
    else if (corner === 'tr') { newW = Math.max(20, origW + dx); newH = Math.max(20, origH - dy); newY = origY + dy; }
    else if (corner === 'bl') { newW = Math.max(20, origW - dx); newH = Math.max(20, origH + dy); newX = origX + dx; }
    else if (corner === 'br') { newW = Math.max(20, origW + dx); newH = Math.max(20, origH + dy); }
    // Edge midpoints
    else if (corner === 't') { newH = Math.max(20, origH - dy); newY = origY + dy; }
    else if (corner === 'b') { newH = Math.max(20, origH + dy); }
    else if (corner === 'l') { newW = Math.max(20, origW - dx); newX = origX + dx; }
    else if (corner === 'r') { newW = Math.max(20, origW + dx); }

    // Snap-to-grid
    newW = this.snap(newW);
    newH = this.snap(newH);
    newX = this.snap(newX);
    newY = this.snap(newY);

    el.x = this.pxToPercent(Math.max(0, newX), cw);
    el.y = this.pxToPercent(Math.max(0, newY), ch);
    el.width = this.pxToPercent(newW, cw);
    el.height = this.pxToPercent(newH, ch);
    this.updateElementDOM(el);
    this.renderProperties();
  },

  updateElementDOM(el) {
    const stage = document.getElementById('canvas-stage');
    const div = stage.querySelector(`[data-eid="${el.id}"]`);
    if (!div) return;
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    div.style.left = this.toPx(el.x, cw) + 'px';
    div.style.top = this.toPx(el.y, ch) + 'px';
    div.style.width = this.toPx(el.width, cw) + 'px';
    div.style.height = this.toPx(el.height, ch) + 'px';
  },

  // ---- Element creation ----
  createElementAtPointer(e) {
    if (!this.currentScene) return;
    const stage = document.getElementById('canvas-stage');
    const rect = stage.getBoundingClientRect();
    const cw = this.project?.width || 1920;
    const ch = this.project?.height || 1080;
    const scale = rect.width / cw;

    const x = ((e.clientX - rect.left) / scale) / cw * 100;
    const y = ((e.clientY - rect.top) / scale) / ch * 100;

    // Image tool uses click-to-place (file picker)
    if (this.tool === 'image') {
      this._pendingImagePos = { x, y };
      document.getElementById('file-input').click();
      this.setTool('select');
      return;
    }

    // Default: create at click position with default size
    this.addElement({ type: this.tool === 'caption' ? 'caption' : 'text', content: this.tool === 'caption' ? 'Caption' : 'New Text', x, y, width: 25, height: 8, font: 'Inter', size: 48, color: '#FFFFFF' });
    this.setTool('select');
  },

  addTextElement() {
    if (!this.currentScene) return;
    Logger.log('add_text_element');
    this.addElement({ type: 'text', content: 'New Text', x: 35, y: 40, width: 30, height: 8, font: 'Inter', size: 48, color: '#FFFFFF' });
  },

  addImageElement() {
    this._pendingImagePos = { x: 20, y: 20 };
    document.getElementById('file-input').click();
  },

  addShapeElement() {
    if (!this.currentScene) return;
    Logger.log('add_shape_element', { shape: this._currentShape || 'rect' });
    this.addElement({ type: 'shape', shape: this._currentShape || 'rect', x: 35, y: 35, width: 20, height: 20, fill: '#4a9eff', border_radius: 0 });
  },

  _shapeTypes: ['rect', 'circle', 'triangle', 'line'],
  _shapeIdx: 0,
  _currentShape: 'rect',

  cycleShapeTool() {
    this._shapeIdx = (this._shapeIdx + 1) % this._shapeTypes.length;
    this._currentShape = this._shapeTypes[this._shapeIdx];
    this.setTool('shape');
    this.toast(`Shape: ${this._currentShape}`);
    // Update tooltip
    const btn = document.querySelector('[data-tool="shape"] .tooltip');
    if (btn) btn.textContent = `Shape: ${this._currentShape} (S — click to cycle)`;
  },

  async handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file || !this.currentScene) return;
    Logger.log('image_upload', { filename: file.name });
    const pos = this._pendingImagePos || { x: 10, y: 10 };

    // Read file as data URL and upload to server for persistence
    try {
      const dataUrl = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const uploadRes = await fetch(`${API}/api/projects/${this.project.id}/upload-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: dataUrl, filename: file.name })
      });
      const uploadData = await uploadRes.json();

      if (uploadData.url) {
        this.addElement({ type: 'image', src: uploadData.url, x: pos.x, y: pos.y, width: 40, height: 30, fit: 'cover' });
        this.toast(`Image saved: ${uploadData.filename}`);
      } else {
        // Fallback to blob URL if upload fails
        this.addElement({ type: 'image', src: URL.createObjectURL(file), x: pos.x, y: pos.y, width: 40, height: 30, fit: 'cover' });
      }
    } catch (err) {
      // Fallback to blob URL on error
      this.addElement({ type: 'image', src: URL.createObjectURL(file), x: pos.x, y: pos.y, width: 40, height: 30, fit: 'cover' });
    }
    e.target.value = '';
  },

  async addElement(elData) {
    if (!this.project || !this.currentScene) return;
    Logger.log('add_element', { type: elData.type });
    const res = await fetch(`${API}/api/projects/${this.project.id}/scenes/${this.currentScene.id}/elements`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(elData)
    });
    const el = await res.json();
    this.currentScene.elements = this.currentScene.elements || [];
    this.currentScene.elements.push(el);
    this.renderCanvas();
    this.renderTimeline();
    this.selectElement(el.id);
  },

  async deleteElement(eid) {
    if (!this.project || !this.currentScene) return;
    this.pushUndo();
    Logger.log('delete_element', { eid });
    await fetch(`${API}/api/projects/${this.project.id}/scenes/${this.currentScene.id}/elements/${eid}`, { method: 'DELETE' });
    this.currentScene.elements = this.currentScene.elements.filter(e => e.id !== eid);
    if (this.currentElement?.id === eid) this.currentElement = null;
    this.renderCanvas();
    this.renderTimeline();
    this.renderProperties();
  },

  // ---- Properties panel ----
  renderProperties() {
    const panel = document.getElementById('props-content');
    if (!panel) return;
    const el = this.currentElement;
    if (!el) {
      // Show scene properties when nothing is selected
      let html = '<div class="prop-section">';
      html += '<div class="prop-title">Scene</div>';
      html += this.propRow('BG Color', 'color', this.currentScene?.bg_color || '#ffffff', v => {
        if (!this.currentScene) return;
        this.currentScene.bg_color = v;
        this.saveScene();
        this.renderCanvas();
      });
      const patterns = ['none', 'bg-grid', 'bg-dots', 'bg-math', 'bg-gradient-radial', 'bg-gradient-top', 'bg-vignette'];
      html += this.propRow('Pattern', 'select', this.currentScene?.bg_pattern || 'none', patterns, v => {
        if (!this.currentScene) return;
        this.currentScene.bg_pattern = v === 'none' ? null : v;
        this.saveScene();
        this.renderCanvas();
      });
      html += '</div>';
      html += '<div class="empty-state" style="padding:12px"><p style="font-size:12px;color:var(--text-dim)">Select an element to edit properties</p></div>';
      panel.innerHTML = html;
      return;
    }

    let html = '';

    // Position & Size
    html += '<div class="prop-section">';
    html += '<div class="prop-title">Position & Size</div>';
    html += this.propRow('X', 'number', el.x, v => this.updateProp(el, 'x', parseFloat(v)));
    html += this.propRow('Y', 'number', el.y, v => this.updateProp(el, 'y', parseFloat(v)));
    html += this.propRow('Width', 'number', el.width, v => this.updateProp(el, 'width', parseFloat(v)));
    html += this.propRow('Height', 'number', el.height, v => this.updateProp(el, 'height', parseFloat(v)));
    html += '</div>';

    // Timing
    html += '<div class="prop-section">';
    html += '<div class="prop-title">Timing</div>';
    html += this.propRow('Start (s)', 'number', el.start ?? 0, v => this.updateProp(el, 'start', parseFloat(v)));
    html += this.propRow('End (s)', 'number', el.end ?? 5, v => this.updateProp(el, 'end', parseFloat(v)));
    html += '</div>';

    // Text properties
    if (el.type === 'text') {
      html += '<div class="prop-section">';
      html += '<div class="prop-title">Text</div>';
      html += this.propRow('Content', 'text', el.content, v => this.updateProp(el, 'content', v));
      html += this._fontPicker('Font', el.font || 'Inter', v => this.updateProp(el, 'font', v));
      html += this.propRow('Size', 'number', el.size || 48, v => this.updateProp(el, 'size', parseInt(v)));
      html += this.propRow('Color', 'color', el.color || '#FFFFFF', v => this.updateProp(el, 'color', v));
      html += this.propRow('Weight', 'select', el.weight || 'normal', ['normal', 'bold', '600', '700'], v => this.updateProp(el, 'weight', v));
      html += this.propRow('Align', 'select', el.align || 'center', ['left', 'center', 'right'], v => this.updateProp(el, 'align', v));
      html += this.propRow('BG Color', 'color', el.bg_color || '', v => this.updateProp(el, 'bg_color', v || undefined));
      html += this.propRow('Radius', 'number', el.border_radius || 0, v => this.updateProp(el, 'border_radius', parseInt(v)));
      // Glow / Shadow
      html += '<div class="prop-title" style="margin-top:8px">Effects</div>';
      const glow = el.glow || {};
      html += this.propRow('Glow Color', 'color', glow.color || '', v => {
        if (!el.glow) el.glow = {};
        el.glow.color = v || undefined;
        if (!v) delete el.glow.color;
        if (!el.glow.color && !el.glow.radius) delete el.glow;
        this.updateProp(el, 'glow', el.glow || undefined);
      });
      html += this.propRow('Glow Radius', 'number', glow.radius || 0, v => {
        if (!el.glow) el.glow = {};
        el.glow.radius = parseInt(v);
        if (!el.glow.radius) delete el.glow.radius;
        if (!el.glow.color && !el.glow.radius) delete el.glow;
        this.updateProp(el, 'glow', el.glow || undefined);
      });
      html += this.propRow('Shadow', 'text', el.text_shadow || '', v => this.updateProp(el, 'text_shadow', v || undefined));
      html += '</div>';
    }

    // Caption properties
    if (el.type === 'caption') {
      const s = el.style || {};
      html += '<div class="prop-section">';
      html += '<div class="prop-title">Caption Style</div>';
      html += this._fontPicker('Font', s.font || 'Inter', v => this.updateNestedProp(el, 'style', 'font', v));
      html += this.propRow('Size', 'number', s.size || 46, v => this.updateNestedProp(el, 'style', 'size', parseInt(v)));
      html += this.propRow('Color', 'color', s.color || '#FFFFFF', v => this.updateNestedProp(el, 'style', 'color', v));
      html += this.propRow('Highlight', 'color', s.highlight || '#FFD700', v => this.updateNestedProp(el, 'style', 'highlight', v));
      html += this.propRow('BG Color', 'color', s.bg_color || '#000000', v => this.updateNestedProp(el, 'style', 'bg_color', v));
      html += this.propRow('Box Shape', 'select', s.box_style || 'rounded', ['rounded', 'sharp', 'pill', 'circle', 'none'], v => this.updateNestedProp(el, 'style', 'box_style', v));
      html += this.propRow('Radius', 'number', s.border_radius || 12, v => this.updateNestedProp(el, 'style', 'border_radius', parseInt(v)));
      html += this.propRow('Align', 'select', s.align || 'center', ['left', 'center', 'right'], v => this.updateNestedProp(el, 'style', 'align', v));
      // Caption positioning
      html += '<div class="prop-title" style="margin-top:8px">Caption Position</div>';
      html += this.propRow('Position', 'select', s.position || 'bottom', ['top', 'center', 'bottom', 'custom'], v => this.updateNestedProp(el, 'style', 'position', v));
      html += this.propRow('X Offset %', 'number', s.x_offset || 50, v => this.updateNestedProp(el, 'style', 'x_offset', parseInt(v)));
      html += this.propRow('Y Offset %', 'number', s.y_offset || 85, v => this.updateNestedProp(el, 'style', 'y_offset', parseInt(v)));
      html += this.propRow('Hide Captions', 'select', s.hidden ? 'yes' : 'no', ['no', 'yes'], v => this.updateNestedProp(el, 'style', 'hidden', v === 'yes'));
      html += '</div>';
      // Per-word effects
      html += '<div class="prop-title" style="margin-top:8px">Word Effects</div>';
      html += this.propRow('Word Animation', 'select', s.word_animation || 'none', ['none', 'typewriter', 'wave', 'bounce-in', 'scale-up', 'glow-pulse'], v => this.updateNestedProp(el, 'style', 'word_animation', v));
      html += this.propRow('Word Delay (ms)', 'number', s.word_delay || 0, v => this.updateNestedProp(el, 'style', 'word_delay', parseInt(v)));
      html += this.propRow('Unspoken', 'select', s.unspoken || 'visible', ['visible', 'dimmed', 'hidden'], v => this.updateNestedProp(el, 'style', 'unspoken', v));
      html += '</div>';
    }

    // Shape properties
    if (el.type === 'shape') {
      html += '<div class="prop-section">';
      html += '<div class="prop-title">Shape</div>';
      html += this.propRow('Type', 'select', el.shape || 'rect', ['rect', 'circle', 'triangle', 'line'], v => this.updateProp(el, 'shape', v));
      html += this.propRow('Fill', 'color', el.fill || '#FFFFFF', v => this.updateProp(el, 'fill', v));
      html += this.propRow('Stroke', 'color', el.stroke || '#000000', v => this.updateProp(el, 'stroke', v));
      html += this.propRow('Stroke W', 'number', el.stroke_width || 0, v => this.updateProp(el, 'stroke_width', parseInt(v)));
      html += this.propRow('Radius', 'number', el.border_radius || 0, v => this.updateProp(el, 'border_radius', parseInt(v)));
      html += '</div>';
    }

    // 3-Phase Animation System
    const _entranceTypes = ['none', 'fade-in', 'slide-up', 'slide-down', 'slide-left', 'slide-right', 'zoom-in', 'zoom-out', 'bounce', 'elastic', 'kinetic-in', 'morph-scale', 'typewriter', 'spin-in', 'flip-in', 'blur-in', 'counter-spin', 'glow-pulse'];
    const _emphasisTypes = ['none', 'shake', 'glitch', 'glow-breathe', 'elastic-wave', 'pulse', 'wave-float', 'rotate-subtle', 'color-shift'];
    const _exitTypes = ['none', 'fade-out', 'exit-shrink', 'exit-fly-right', 'exit-fly-up', 'exit-dissolve', 'slide-down', 'zoom-out', 'blur-in'];

    html += '<div class="prop-section">';
    html += '<div class="prop-title">Entrance Animation</div>';
    const enVal = (el.entrance?.type) || ((typeof el.animation === 'object' ? el.animation?.type : el.animation) || 'none');
    html += this.propRow('Type', 'select', enVal, _entranceTypes, v => {
      const dur = el.entrance?.duration || 0.6;
      this.updateProp(el, 'entrance', v === 'none' ? { type: 'none' } : { type: v, duration: dur });
    });
    const enDur = el.entrance?.duration || 0.6;
    html += this.propRow('Duration (s)', 'number', enDur, v => {
      const cur = el.entrance?.type || 'none';
      this.updateProp(el, 'entrance', { type: cur, duration: parseFloat(v) || 0.6 });
    });
    html += '</div>';

    html += '<div class="prop-section">';
    html += '<div class="prop-title">Emphasis (Mid-Life)</div>';
    const emVal = el.emphasis?.type || 'none';
    html += this.propRow('Type', 'select', emVal, _emphasisTypes, v => {
      const dur = el.emphasis?.duration || 0.4;
      this.updateProp(el, 'emphasis', v === 'none' ? { type: 'none' } : { type: v, duration: dur });
    });
    html += '</div>';

    html += '<div class="prop-section">';
    html += '<div class="prop-title">Exit Animation</div>';
    const exVal = el.exit?.type || 'none';
    html += this.propRow('Type', 'select', exVal, _exitTypes, v => {
      const dur = el.exit?.duration || 0.5;
      this.updateProp(el, 'exit', v === 'none' ? { type: 'none' } : { type: v, duration: dur });
    });
    const exDur = el.exit?.duration || 0.5;
    html += this.propRow('Duration (s)', 'number', exDur, v => {
      const cur = el.exit?.type || 'none';
      this.updateProp(el, 'exit', { type: cur, duration: parseFloat(v) || 0.5 });
    });
    html += '</div>';

    // Visibility toggle
    html += '<div class="prop-section">';
    html += '<div class="prop-title">Visibility</div>';
    html += this.propRow('Hidden', 'select', el.visible === false ? 'yes' : 'no', ['no', 'yes'], v => {
      this.updateProp(el, 'visible', v === 'yes' ? false : true);
    });
    html += '</div>';

    // Alignment
    html += '<div class="prop-section">';
    html += '<div class="prop-title">Align</div>';
    html += '<div class="prop-row" style="gap:4px;flex-wrap:wrap">';
    html += '<button class="btn sm" onclick="App.alignElement(\"left\")" title="Align Left">⫷</button>';
    html += '<button class="btn sm" onclick="App.alignElement(\"center-h\")" title="Center Horizontal">⫿</button>';
    html += '<button class="btn sm" onclick="App.alignElement(\"right\")" title="Align Right">⫸</button>';
    html += '<button class="btn sm" onclick="App.alignElement(\"top\")" title="Align Top">⊤</button>';
    html += '<button class="btn sm" onclick="App.alignElement(\"center-v\")" title="Center Vertical">⊡</button>';
    html += '<button class="btn sm" onclick="App.alignElement(\"bottom\")" title="Align Bottom">⊥</button>';
    html += '</div>';
    html += '</div>';

    // Layer ordering
    html += '<div class="prop-section">';
    html += '<div class="prop-title">Layer Order</div>';
    html += '<div class="prop-row" style="gap:4px">';
    html += '<button class="btn sm" onclick="App.bringToFront()" title="Bring to Front">⬆ Front</button>';
    html += '<button class="btn sm" onclick="App.sendToBack()" title="Send to Back">⬇ Back</button>';
    html += '<button class="btn sm" onclick="App.moveUp()" title="Move Up">↑</button>';
    html += '<button class="btn sm" onclick="App.moveDown()" title="Move Down">↓</button>';
    html += '</div>';
    html += '</div>';

    panel.innerHTML = html;
  },

  propRow(label, type, value, optionsOrCallback, maybeCallback) {
    // Smart detection: if 4th arg is a function, it's the callback (no options)
    let options, onChange;
    if (typeof optionsOrCallback === 'function') {
      onChange = optionsOrCallback;
      options = maybeCallback;
    } else {
      options = optionsOrCallback;
      onChange = maybeCallback;
    }

    const id = 'prop-' + label.replace(/\s/g, '-').toLowerCase();
    let input = '';
    if (type === 'select') {
      const opts = (options || []).map(o => `<option value="${o}" ${o === value ? 'selected' : ''}>${o}</option>`).join('');
      input = `<select class="prop-select" id="${id}" onchange="App._propChange('${id}', this.value)">${opts}</select>`;
    } else if (type === 'color') {
      input = `<input class="prop-input" type="color" id="${id}" value="${value || '#ffffff'}" onchange="App._propChange('${id}', this.value)">`;
    } else if (type === 'number') {
      input = `<input class="prop-input" type="number" id="${id}" value="${value ?? 0}" step="1" onchange="App._propChange('${id}', this.value)">`;
    } else {
      input = `<input class="prop-input" type="text" id="${id}" value="${this.esc(String(value || ''))}" onchange="App._propChange('${id}', this.value)">`;
    }
    if (onChange) this._propCallbacks[id] = onChange;
    return `<div class="prop-row"><div class="prop-label">${label}</div>${input}</div>`;
  },

  _fontPicker(label, value, onChange) {
    const fonts = ['Inter', 'Roboto', 'Open Sans', 'Lato', 'Montserrat', 'Oswald', 'Raleway', 'Poppins', 'Playfair Display', 'Merriweather', 'Source Code Pro', 'Fira Code', 'Bebas Neue', 'Anton', 'Permanent Marker', 'Pacifico', 'Lobster', 'Orbitron', 'Righteous', 'Caveat'];
    const id = 'prop-' + label.replace(/\s/g, '-').toLowerCase();
    const opts = fonts.map(f => `<option value="${f}" ${f === value ? 'selected' : ''}>${f}</option>`).join('');
    const extra = !fonts.includes(value) ? `<option value="${value}" selected>${value}</option>` : '';
    const select = `<select class="prop-select" id="${id}" onchange="App._propChange('${id}', this.value)" style="font-family:'${value}'">${extra}${opts}</select>`;
    if (onChange) this._propCallbacks[id] = onChange;
    return `<div class="prop-row"><div class="prop-label">${label}</div>${select}</div>`;
  },

  _propChange(id, value) {
    Logger.log('prop_change', { id, value: String(value).substring(0, 50) });
    if (this._propCallbacks?.[id]) this._propCallbacks[id](value);
  },

  updateProp(el, key, value) {
    if (value === undefined) { delete el[key]; }
    else { el[key] = value; }
    this.renderCanvas();
    this.renderTimeline();
    this.saveScene();
  },

  updateNestedProp(el, parent, key, value) {
    if (!el[parent]) el[parent] = {};
    el[parent][key] = value;
    this.renderCanvas();
    this.renderTimeline();
    this.saveScene();
  },

  async saveScene() {
    if (!this.project || !this.currentScene) return;
    await fetch(`${API}/api/projects/${this.project.id}/scenes/${this.currentScene.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.currentScene)
    });
  },

  // ---- Timeline (GROUPED by type, absolute timeline across all scenes) ----
  renderTimeline() {
    const tracks = document.getElementById('timeline-tracks');
    if (!tracks) return;
    const projectDur = this.duration || this._getProjectDuration();
    if (!projectDur || !this.scenes.length) {
      tracks.innerHTML = '<div class="empty-state" style="padding:16px"><p style="font-size:12px;color:var(--text-dim)">Add elements to see them on the timeline</p></div>';
      return;
    }

    // Collect ALL elements from ALL scenes with absolute time offsets
    const groups = {};
    const typeOrder = ['caption', 'text', 'image', 'shape'];
    const typeLabels = { caption: 'Captions', text: 'Text', image: 'Images', shape: 'Shapes' };
    const typeColors = { caption: '#4caf50', text: '#4a9eff', image: '#ff9800', shape: '#9c27b0' };

    for (const s of this.scenes) {
      const offset = this._getSceneTimeOffset(s);
      for (const el of (s.elements || [])) {
        const absEl = {
          ...el,
          _absStart: (el.start ?? 0) + offset,
          _absEnd: (el.end ?? 5) + offset,
          _sceneId: s.id,
        };
        if (!groups[el.type]) groups[el.type] = [];
        groups[el.type].push(absEl);
      }
    }

    let html = '';

    // Scene boundaries overlay
    html += '<div class="timeline-ruler">';
    const step = projectDur <= 30 ? 2 : projectDur <= 120 ? 5 : 10;
    for (let t = 0; t <= projectDur; t += step) {
      const pct = (t / projectDur * 100).toFixed(2);
      html += `<div class="timeline-ruler-tick" style="left:${pct}%"><span>${this.fmtDuration(t)}</span></div>`;
    }
    // Scene boundary lines
    let boundOffset = 0;
    for (let i = 0; i < this.scenes.length - 1; i++) {
      boundOffset += this.scenes[i].duration || 10;
      const pct = (boundOffset / projectDur * 100).toFixed(2);
      html += `<div class="timeline-scene-boundary" style="left:${pct}%"></div>`;
    }
    html += '</div>';

    // One track per type
    for (const type of typeOrder) {
      const els = groups[type];
      if (!els || !els.length) continue;

      const color = typeColors[type];
      const label = typeLabels[type];

      html += `<div class="timeline-track-group">`;
      html += `<div class="timeline-track-label" style="border-left:3px solid ${color}">${label} <span class="track-count">${els.length}</span></div>`;
      html += `<div class="timeline-track-bar">`;

      for (const el of els) {
        const startPct = ((el._absStart) / projectDur * 100).toFixed(2);
        const endPct = ((el._absEnd) / projectDur * 100).toFixed(2);
        const widthPct = Math.max(0.5, endPct - startPct).toFixed(2);
        const isSelected = el.id === this.currentElement?.id;
        const segLabel = (el.content || el.id || '').substring(0, 20);

        html += `<div class="timeline-segment ${isSelected ? 'selected' : ''}"
                      style="left:${startPct}%;width:${widthPct}%;background:${color}"
                      title="${this.esc(segLabel)}"
                      data-eid="${el.id}"
                      data-scene-id="${el._sceneId}"
                      data-duration="${projectDur}">
                   <div class="seg-handle seg-left" data-side="left"></div>
                   <span class="segment-label">${this.esc(segLabel)}</span>
                   <div class="seg-handle seg-right" data-side="right"></div>
                 </div>`;
      }

      html += `</div></div>`;
    }

    tracks.innerHTML = html;
    this._bindTimelineSegments();

    // Click ruler to seek
    const ruler = tracks.querySelector('.timeline-ruler');
    if (ruler) {
      ruler.addEventListener('pointerdown', e => {
        const rect = ruler.getBoundingClientRect();
        const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        this.seekTo(pct * projectDur);
        Logger.log('ruler_seek', { pct: pct.toFixed(3) });
      });
    }
  },

  _bindTimelineSegments() {
    const tracks = document.getElementById('timeline-tracks');
    if (!tracks) return;
    const projectDur = this.duration || this._getProjectDuration();

    // Click on segment to select AND seek to its start time
    tracks.querySelectorAll('.timeline-segment').forEach(seg => {
      seg.addEventListener('click', e => {
        if (e.target.classList.contains('seg-handle') || e.target.classList.contains('keyframe-dot')) return;
        e.stopPropagation();
        this.selectElement(seg.dataset.eid);
        // Seek playhead to the start of this element
        const found = findEl(seg.dataset.eid);
        if (found) {
          this.seekTo(found.offset + (found.el.start ?? 0));
        }
      });
    });

    // Helper: find element by eid across all scenes
    const findEl = (eid) => {
      for (const s of this.scenes) {
        const el = (s.elements || []).find(x => x.id === eid);
        if (el) return { el, scene: s, offset: this._getSceneTimeOffset(s) };
      }
      return null;
    };

    // Drag segment to move in time (absolute timeline)
    tracks.querySelectorAll('.timeline-segment').forEach(seg => {
      let dragStartX = null, dragOrigAbsStart = null, dragDuration = null, dragEl = null, dragSceneOffset = 0;
      const eid = seg.dataset.eid;

      seg.addEventListener('pointerdown', e => {
        if (e.target.classList.contains('seg-handle')) return;
        e.stopPropagation();
        this.selectElement(eid);
        const found = findEl(eid);
        if (!found) return;
        dragEl = found.el;
        dragSceneOffset = found.offset;
        dragStartX = e.clientX;
        dragDuration = projectDur;
        dragOrigAbsStart = (found.el.start ?? 0) + dragSceneOffset;
        seg.classList.add('dragging');
        seg.setPointerCapture(e.pointerId);
      });

      seg.addEventListener('pointermove', e => {
        if (dragStartX === null || !dragEl) return;
        const trackBar = seg.parentElement;
        const trackWidth = trackBar.clientWidth;
        const dx = e.clientX - dragStartX;
        const dt = (dx / trackWidth) * dragDuration;
        const origDuration = (dragEl.end ?? 5) - (dragEl.start ?? 0);
        const newAbsStart = Math.max(0, Math.min(dragOrigAbsStart + dt, projectDur - origDuration));
        // Convert back to scene-local time
        dragEl.start = Math.round((newAbsStart - dragSceneOffset) * 10) / 10;
        dragEl.end = Math.round((dragEl.start + origDuration) * 10) / 10;
        this.renderTimeline();
        this.renderCanvas();
      });

      seg.addEventListener('pointerup', e => {
        if (dragStartX !== null) {
          dragStartX = null;
          dragEl = null;
          seg.classList.remove('dragging');
          this.saveScene();
        }
      });
    });

    // Resize handles on segment edges
    tracks.querySelectorAll('.seg-handle').forEach(handle => {
      let resizeStartX = null, resizeOrigStart = null, resizeOrigEnd = null, resizeDuration = null, resizeEl = null, resizeSceneOffset = 0;
      const seg = handle.closest('.timeline-segment');
      const eid = seg.dataset.eid;
      const side = handle.dataset.side;

      handle.addEventListener('pointerdown', e => {
        e.stopPropagation();
        this.selectElement(eid);
        const found = findEl(eid);
        if (!found) return;
        resizeEl = found.el;
        resizeSceneOffset = found.offset;
        resizeStartX = e.clientX;
        resizeDuration = projectDur;
        resizeOrigStart = found.el.start ?? 0;
        resizeOrigEnd = found.el.end ?? 5;
        handle.setPointerCapture(e.pointerId);
      });

      handle.addEventListener('pointermove', e => {
        if (resizeStartX === null || !resizeEl) return;
        const trackBar = seg.parentElement;
        const trackWidth = trackBar.clientWidth;
        const dx = e.clientX - resizeStartX;
        const dt = (dx / trackWidth) * resizeDuration;

        if (side === 'left') {
          resizeEl.start = Math.max(0, Math.min(resizeOrigStart + dt, resizeOrigEnd - 0.1));
          resizeEl.start = Math.round(resizeEl.start * 10) / 10;
        } else {
          resizeEl.end = Math.max(resizeEl.start + 0.1, Math.min(resizeOrigEnd + dt, resizeDuration - resizeSceneOffset));
          resizeEl.end = Math.round(resizeEl.end * 10) / 10;
        }
        this.renderTimeline();
        this.renderCanvas();
      });

      handle.addEventListener('pointerup', e => {
        if (resizeStartX !== null) {
          resizeStartX = null;
          resizeEl = null;
          this.saveScene();
        }
      });
    });
  },

  // ---- Audio ----
  loadAudio(src) {
    console.log(`[AUDIO] loadAudio called: src=${src} existing=${!!this.audio} lastSrc=${this._lastAudioSrc}`);
    if (this.audio) { this.audio.pause(); this.audio = null; }
    if (!src) return;
    this._lastAudioSrc = src;

    // Convert file path to URL — handle all known path patterns
    let url = src;
    // If it's already a URL (starts with / or http), use as-is
    if (src.startsWith('/') || src.startsWith('http')) {
      url = src;
    }
    // Windows absolute path from VideoComposerWork or WordEditorWork
    else if (src.match(/^[A-Z]:\\/) || src.includes('AppData')) {
      const parts = src.split(/[/\\]/);
      // Try VideoComposerWork first, then WordEditorWork
      for (const workDir of ['VideoComposerWork', 'WordEditorWork']) {
        const idx = parts.findIndex(p => p === workDir);
        if (idx >= 0 && idx + 1 < parts.length) {
          const pid = parts[idx + 1];
          const filename = parts[parts.length - 1];
          url = `/audio/${pid}/${filename}`;
          break;
        }
      }
    }

    this.audio = new Audio(url);

    // Get duration from metadata
    this.audio.addEventListener('loadedmetadata', () => {
      this.duration = this.audio.duration || this.duration;
      // Recalculate total duration from scene sum (do NOT modify scene durations)
      const sceneTotal = this.scenes.reduce((n, s) => n + (s.duration || 10), 0);
      if (this.duration > sceneTotal) {
        // Extend LAST scene to cover remaining audio
        const last = this.scenes[this.scenes.length - 1];
        if (last) last.duration = this.duration - (sceneTotal - (last.duration || 10));
        this.duration = this._getProjectDuration();
      }
      this.updateTimeDisplay();
      this.updateAudioInfo();
      this.renderTimeline();
      Logger.log('audio_loaded', {
        duration: this.duration.toFixed(2),
        scenes: this.scenes.length,
        totalElements: this.scenes.reduce((n, s) => n + (s.elements || []).length, 0),
        sceneDurations: this.scenes.map(s => (s.duration || 10).toFixed(1)).join(','),
        src
      });
    });

    this.audio.addEventListener('timeupdate', () => {
      const audioT = this.audio.currentTime;
      if (this._seeking) {
        console.log(`[TIMEUPDATE] BLOCKED (seeking) audio=${audioT.toFixed(2)} current=${this.currentTime.toFixed(2)}`);
      } else {
        if (Math.abs(audioT - this.currentTime) > 0.5) {
          console.log(`[TIMEUPDATE] JUMP DETECTED audio=${audioT.toFixed(2)} current=${this.currentTime.toFixed(2)} diff=${(audioT - this.currentTime).toFixed(2)}`);
        }
        this.currentTime = audioT;
      }
      this.updateTimeDisplay();
      if (!this._playheadDrag) this.updatePlayhead();
      this.highlightWords();
      this.renderCanvas();
    });

    this.audio.addEventListener('ended', () => {
      this.playing = false;
      this.updatePlayButton();
    });

    this.audio.addEventListener('error', (e) => {
      Logger.log('audio_error', { src: url, error: String(e) });
      this.toast('Failed to load audio', 'error');
    });
  },

  togglePlay() {
    console.log(`[PLAY] togglePlay called: playing=${this.playing} audioTime=${this.audio?.currentTime?.toFixed(2)} readyState=${this.audio?.readyState}`);
    if (!this.audio) {
      this.toast('No audio loaded', 'error');
      return;
    }
    if (this.playing) {
      this.audio.pause();
      this.playing = false;
      if (this._renderRAF) { cancelAnimationFrame(this._renderRAF); this._renderRAF = null; }
      Logger.log('audio_pause', { time: this.currentTime.toFixed(2) });
    } else {
      this.audio.play();
      this.playing = true;
      // Log comprehensive state on play
      const totalEls = this.scenes.reduce((n, s) => n + (s.elements || []).length, 0);
      const captions = this.scenes.reduce((n, s) => n + (s.elements || []).filter(e => e.type === 'caption').length, 0);
      const others = totalEls - captions;
      Logger.log('audio_play', {
        time: this.currentTime.toFixed(2),
        duration: this.duration.toFixed(2),
        scenes: this.scenes.length,
        captions, otherElements: others,
        audioSrc: this._lastAudioSrc || 'none',
        audioReady: this.audio?.readyState || 0,
        currentSceneName: this.currentScene?.name || 'none'
      });
    }
    this.updatePlayButton();
    // Start smooth RAF render loop for animations
    if (this.playing) this._startRenderLoop();
  },

  _startRenderLoop() {
    if (this._renderRAF) return;
    console.log('[RAF] render loop started');
    let frameCount = 0;
    const loop = () => {
      if (!this.playing) { console.log('[RAF] render loop stopped'); this._renderRAF = null; return; }
      const audioT = this.audio?.currentTime ?? 0;
      if (!this._seeking && this.audio) {
        if (Math.abs(audioT - this.currentTime) > 0.3) {
          console.log(`[RAF] frame=${frameCount} audio=${audioT.toFixed(2)} was=${this.currentTime.toFixed(2)} CORRECTING`);
        }
        this.currentTime = audioT;
      }
      frameCount++;
      this.updateTimeDisplay();
      if (!this._playheadDrag) this.updatePlayhead();
      this.highlightWords();
      this.renderCanvas();
      this._renderRAF = requestAnimationFrame(loop);
    };
    this._renderRAF = requestAnimationFrame(loop);
  },

  _startSceneHighlightLoop() {
    if (this._sceneHighlightRAF) return;
    const loop = () => {
      if (!this.playing) { this._sceneHighlightRAF = null; return; }
      this._highlightActiveScene();
      this._sceneHighlightRAF = requestAnimationFrame(loop);
    };
    this._sceneHighlightRAF = requestAnimationFrame(loop);
  },

  updatePlayButton() {
    const btn = document.getElementById('play-btn');
    if (!btn) return;
    btn.innerHTML = this.playing
      ? '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><polygon points="5 3 19 12 5 21"/></svg>';
  },

  updateTimeDisplay() {
    const display = document.getElementById('time-display');
    if (display) display.textContent = `${this.fmtTime(this.currentTime)} / ${this.fmtTime(this.duration)}`;
  },

  updatePlayhead() {
    const playhead = document.getElementById('playhead');
    if (!playhead) return;
    const pct = this.duration > 0 ? (this.currentTime / this.duration) : 0;
    // Playhead is now a child of .timeline — position relative to tracks area
    const tracks = document.getElementById('timeline-tracks');
    if (!tracks) return;
    const tracksRect = tracks.getBoundingClientRect();
    const timeline = document.getElementById('timeline');
    const timelineRect = timeline ? timeline.getBoundingClientRect() : { top: 0, left: 0 };
    const tracksWidth = tracks.clientWidth;
    const px = pct * tracksWidth;
    // Position top so the playhead aligns with the top of tracks
    const topOffset = tracksRect.top - timelineRect.top;
    playhead.style.left = (px + tracks.offsetLeft) + 'px';
    playhead.style.top = topOffset + 'px';
    playhead.style.height = tracks.scrollHeight + 'px';
  },

  highlightWords() {
    const t = this.currentTime;
    // Build a lookup of all elements across all scenes (for cross-scene captions)
    const allElements = {};
    for (const s of this.scenes) {
      const offset = this._getSceneTimeOffset(s);
      for (const el of (s.elements || [])) {
        allElements[el.id] = { el, offset };
      }
    }
    document.querySelectorAll('.canvas-el[data-type="caption"] .word').forEach(wordEl => {
      const idx = parseInt(wordEl.dataset.idx);
      const caption = wordEl.closest('.canvas-el');
      if (!caption) return;
      const found = allElements[caption.dataset.eid];
      if (!found) return;
      const { el, offset } = found;
      if (!el?.words?.[idx]) return;
      const w = el.words[idx];
      // Convert scene-relative word timestamps to absolute for comparison
      const absWStart = w.start + offset;
      const absWEnd = w.end + offset;
      const wordAnim = wordEl.dataset.wordAnim || 'none';
      const unspoken = wordEl.dataset.unspoken || 'visible';
      if (t >= absWStart && t <= absWEnd) {
        // Currently spoken word — apply highlight + word animation
        wordEl.style.color = (el.style || {}).highlight || '#FFD700';
        wordEl.style.fontWeight = 'bold';
        wordEl.style.opacity = '1';
        if (wordAnim === 'typewriter') {
          wordEl.style.clipPath = 'inset(0 0 0 0)';
          wordEl.style.transform = 'none';
        } else if (wordAnim === 'wave') {
          wordEl.style.transform = `translateY(${Math.sin(Date.now() / 100) * 3}px)`;
        } else if (wordAnim === 'bounce-in') {
          wordEl.style.transform = 'scale(1.2)';
        } else if (wordAnim === 'scale-up') {
          wordEl.style.transform = 'scale(1.15)';
        } else if (wordAnim === 'glow-pulse') {
          wordEl.style.textShadow = `0 0 12px ${el.style?.highlight || '#FFD700'}`;
        }
      } else if (t > absWEnd) {
        // Already spoken — full visibility
        wordEl.style.color = (el.style || {}).color || '#FFFFFF';
        wordEl.style.fontWeight = 'normal';
        wordEl.style.opacity = '1';
        wordEl.style.transform = 'none';
        wordEl.style.clipPath = 'none';
        wordEl.style.textShadow = 'none';
      } else {
        // Not yet spoken — apply unspoken style
        wordEl.style.color = (el.style || {}).color || '#FFFFFF';
        wordEl.style.fontWeight = 'normal';
        wordEl.style.transform = 'none';
        wordEl.style.clipPath = 'none';
        wordEl.style.textShadow = 'none';
        if (unspoken === 'hidden') {
          wordEl.style.opacity = '0';
        } else if (unspoken === 'dimmed') {
          wordEl.style.opacity = '0.3';
        } else {
          wordEl.style.opacity = '0.5';
        }
      }
    });
  },

  // ---- Render & Export ----
  async renderProject() {
    if (!this.project) { this.toast('No project open', 'error'); return; }
    Logger.log('render_project', { pid: this.project.id });
    this.toast('Rendering...');
    const res = await fetch(`${API}/api/render/${this.project.id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    const data = await res.json();
    if (data.error) { this.toast(data.error, 'error'); return; }
    this.toast(data.message || 'Render complete!');
  },

  exportComposition() {
    if (!this.project || !this.currentScene) { this.toast('No scene to export', 'error'); return; }
    Logger.log('export_html');
    const html = this.generateHTML();
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.project.name || 'composition'}_${this.currentScene.name || 'scene'}.html`;
    a.click();
    URL.revokeObjectURL(url);
    this.toast('Exported HTML!');
  },

  generateHTML() {
    const scene = this.currentScene;
    const w = this.project?.width || 1920;
    const h = this.project?.height || 1080;
    let body = '';
    for (const el of (scene?.elements || [])) {
      body += this.elementToHTML(el, w, h);
    }
    return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:${w}px;height:${h}px;background:${scene?.bg_color || '#0e1116'};overflow:hidden;font-family:'Inter',sans-serif}
.el{position:absolute}
</style></head><body>
${body}
</body></html>`;
  },

  elementToHTML(el, w, h) {
    const x = this.toPx(el.x, w);
    const y = this.toPx(el.y, h);
    const ew = this.toPx(el.width, w);
    const eh = this.toPx(el.height, h);
    const style = `left:${x}px;top:${y}px;width:${ew}px;height:${eh}px;position:absolute;`;

    if (el.type === 'text') {
      return `<div class="el" style="${style}font-family:'${el.font || 'Inter'}';font-size:${el.size || 48}px;color:${el.color || '#fff'};font-weight:${el.weight || 'normal'};text-align:${el.align || 'center'};display:flex;align-items:center;justify-content:center">${this.esc(el.content || '')}</div>`;
    }
    if (el.type === 'shape') {
      return `<div class="el" style="${style}background:${el.fill || '#fff'};border-radius:${el.border_radius || 0}px"></div>`;
    }
    if (el.type === 'image') {
      return `<div class="el" style="${style}background-image:url('${el.src || ''}');background-size:${el.fit || 'cover'};background-position:center;border-radius:${el.border_radius || 0}px"></div>`;
    }
    return '';
  },

  // ---- Helpers ----
  toPx(val, total) {
    if (typeof val === 'string' && val.endsWith('%')) return parseFloat(val) / 100 * total;
    if (val > 100) return val;
    return val / 100 * total;
  },

  pxToPercent(px, total) { return (px / total * 100); },

  fmtDuration(s) {
    if (!s) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  },

  fmtTime(s) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    const ms = Math.floor((s % 1) * 1000);
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  },

  esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); },

  toast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  },

  closeModal() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.remove());
  }
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
