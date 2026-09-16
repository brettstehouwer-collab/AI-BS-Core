// frontend/services/sonificationService.js
// Sub-millisecond SQLite FTS5 RAG Sonification & Neural DAW Audio Graph Controller (v5.154.0)

const BACKEND_URL = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  ? 'https://ai-bs-dashboard.web.app'
  : (import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8080');

const API_BASE = `${BACKEND_URL}/api/audio`;

class SonificationEngine {
  constructor() {
    this.audioCtx = null;
    this.masterGain = null;
    this.sidechainCompressor = null;
    this.bedGain = null;
    this.stingerGain = null;
    this.currentBedAudio = null;
    this.isInitialized = false;
  }

  initAudioGraph() {
    if (this.isInitialized && this.audioCtx) return;
    try {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return;

      this.audioCtx = new AudioContextClass();
      
      // Master Output
      this.masterGain = this.audioCtx.createGain();
      this.masterGain.gain.setValueAtTime(0.85, this.audioCtx.currentTime);
      this.masterGain.connect(this.audioCtx.destination);

      // Sidechain Ducking Compressor
      this.sidechainCompressor = this.audioCtx.createDynamicsCompressor();
      this.sidechainCompressor.threshold.setValueAtTime(-24, this.audioCtx.currentTime);
      this.sidechainCompressor.knee.setValueAtTime(12, this.audioCtx.currentTime);
      this.sidechainCompressor.ratio.setValueAtTime(8, this.audioCtx.currentTime);
      this.sidechainCompressor.attack.setValueAtTime(0.005, this.audioCtx.currentTime);
      this.sidechainCompressor.release.setValueAtTime(0.35, this.audioCtx.currentTime);
      this.sidechainCompressor.connect(this.masterGain);

      // Background Bed Sub-Mix Bus
      this.bedGain = this.audioCtx.createGain();
      this.bedGain.gain.setValueAtTime(0.25, this.audioCtx.currentTime);
      this.bedGain.connect(this.sidechainCompressor);

      // Foreground Stinger Bus
      this.stingerGain = this.audioCtx.createGain();
      this.stingerGain.gain.setValueAtTime(0.7, this.audioCtx.currentTime);
      this.stingerGain.connect(this.masterGain);

      this.isInitialized = true;
    } catch (e) {
      console.warn("SonificationEngine: WebAudio initialization deferred until user interaction.", e);
    }
  }

  resumeIfSuspended() {
    this.initAudioGraph();
    if (this.audioCtx && this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
  }

  /**
   * Sub-2ms parametric search across 101,063 audio assets using SQLite FTS5 BM25.
   */
  async searchCorpus(params = {}) {
    const query = new URLSearchParams();
    if (params.category) query.set('category', params.category);
    if (params.bpm) query.set('bpm', params.bpm);
    if (params.musical_key) query.set('musical_key', params.musical_key);
    if (params.timbral_spectrum) query.set('timbral_spectrum', params.timbral_spectrum);
    if (params.semantic_context) query.set('semantic_context', params.semantic_context);
    if (params.data_bindings) query.set('data_bindings', params.data_bindings);
    if (params.q) query.set('q', params.q);
    query.set('limit', params.limit || 5);

    try {
      const res = await fetch(`${API_BASE}/search?${query.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (e) {
      console.error("searchCorpus error:", e);
      return { count: 0, results: [] };
    }
  }

  /**
   * Plays a dynamic data anomaly / metric stinger for table reading & dashboard alerts.
   */
  async sonifyDataVariance(metricName, prevVal, currVal, threshold = 10) {
    this.resumeIfSuspended();
    const delta = currVal - prevVal;
    const isCritical = Math.abs(delta) >= threshold;
    const valence = delta >= 0 ? "positive" : (isCritical ? "critical" : "negative");

    try {
      const res = await fetch(`${API_BASE}/sonify/query?event_type=variance_breach&valence=${valence}&variance=${delta}`);
      const data = await res.json();

      if (data.transient_stingers && data.transient_stingers.length > 0) {
        const topStinger = data.transient_stingers[0];
        const streamUrl = `${BACKEND_URL}${topStinger.stream_url}`;
        this.playTransient(streamUrl, isCritical ? 0.9 : 0.5);
      }
    } catch (e) {
      console.warn("sonifyDataVariance fetch failed:", e);
    }
  }

  /**
   * Sets the continuous background harmonic bed with smooth crossfade.
   */
  async setHarmonicBed(mood = 'positive', musicalKey = 'Cmin', bpm = '140') {
    this.resumeIfSuspended();
    try {
      const res = await fetch(`${API_BASE}/sonify/query?event_type=row_transition&valence=${mood}&preferred_key=${musicalKey}&preferred_bpm=${bpm}`);
      const data = await res.json();

      if (data.harmonic_beds && data.harmonic_beds.length > 0) {
        const topBed = data.harmonic_beds[0];
        const streamUrl = `${BACKEND_URL}${topBed.stream_url}`;
        this.crossfadeBed(streamUrl);
      }
    } catch (e) {
      console.warn("setHarmonicBed error:", e);
    }
  }

  playTransient(url, volume = 0.7) {
    if (!this.audioCtx) return;
    const audio = new Audio(url);
    audio.crossOrigin = "anonymous";
    const source = this.audioCtx.createMediaElementSource(audio);
    
    const gainNode = this.audioCtx.createGain();
    gainNode.gain.setValueAtTime(volume, this.audioCtx.currentTime);
    
    source.connect(gainNode);
    gainNode.connect(this.stingerGain || this.masterGain);
    audio.play().catch(err => console.warn("playTransient blocked:", err));
  }

  crossfadeBed(url) {
    if (!this.audioCtx) return;
    
    if (this.currentBedAudio) {
      try {
        this.currentBedAudio.pause();
        this.currentBedAudio = null;
      } catch (e) {}
    }

    const audio = new Audio(url);
    audio.crossOrigin = "anonymous";
    audio.loop = true;
    
    const source = this.audioCtx.createMediaElementSource(audio);
    source.connect(this.bedGain || this.masterGain);
    
    audio.play().then(() => {
      this.currentBedAudio = audio;
    }).catch(err => console.warn("crossfadeBed autoplay blocked:", err));
  }

  /**
   * Automatically ducks background bed volume during TTS vocal playback.
   */
  duckVoiceBed(durationMs = 2500, duckDb = -14) {
    if (!this.audioCtx || !this.bedGain) return;
    const currTime = this.audioCtx.currentTime;
    const duckLinear = Math.pow(10, duckDb / 20); // ~0.20
    const normalLinear = 0.25;

    this.bedGain.gain.cancelScheduledValues(currTime);
    this.bedGain.gain.setValueAtTime(this.bedGain.gain.value, currTime);
    this.bedGain.gain.linearRampToValueAtTime(duckLinear, currTime + 0.05);
    this.bedGain.gain.setValueAtTime(duckLinear, currTime + (durationMs / 1000));
    this.bedGain.gain.linearRampToValueAtTime(normalLinear, currTime + (durationMs / 1000) + 0.4);
  }

  stopAll() {
    if (this.currentBedAudio) {
      this.currentBedAudio.pause();
      this.currentBedAudio = null;
    }
  }
}

export const sonification = new SonificationEngine();
export default sonification;
