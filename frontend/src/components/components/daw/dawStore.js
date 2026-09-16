import { create } from 'zustand';
import * as Tone from 'tone';

// ═══════════════════════════════════════════════════════════════════════════
// MASTER AUDIO GRAPH SETUP (Tone.js)
// ═══════════════════════════════════════════════════════════════════════════

// Master Bus Chain: Master Channel -> EQ3 -> Compressor -> Limiter -> Destination
const masterLimiter = new Tone.Limiter(-0.1).toDestination();
const masterCompressor = new Tone.Compressor({
  threshold: -12,
  ratio: 3,
  attack: 0.03,
  release: 0.25
}).connect(masterLimiter);

const masterEQ = new Tone.EQ3({
  low: 0,
  mid: 0,
  high: 0
}).connect(masterCompressor);

const masterMeter = new Tone.Meter();
export const masterAnalyser = new Tone.Analyser('fft', 64).connect(masterMeter);
const masterVolumeNode = new Tone.Volume(0).connect(masterEQ);
masterVolumeNode.connect(masterAnalyser);

// Global Effect Busses (Sends)
const reverbFX = new Tone.Reverb({ decay: 2.5, preDelay: 0.01, wet: 1 }).connect(masterVolumeNode);
const delayFX = new Tone.FeedbackDelay({ delayTime: '8n', feedback: 0.4, wet: 1 }).connect(masterVolumeNode);
const distortionFX = new Tone.Distortion({ distortion: 0.3, wet: 0.2 }).connect(masterVolumeNode);
const filterFX = new Tone.Filter({ frequency: 2000, type: 'lowpass' }).connect(masterVolumeNode);
const pitchShiftFX = new Tone.PitchShift({ pitch: 0, windowSize: 0.1, delayTime: 0, feedback: 0, wet: 1 }).connect(masterVolumeNode);

class VSTBridgeNode {
  constructor() {
    this.ws = null;
    this.pluginId = null;
    this.workletLoaded = false;
    this.workletNode = null;
    
    this.input = new Tone.Gain(1);
    this.output = new Tone.Gain(1);
    this.dryNode = new Tone.Gain(1);
    
    this.input.connect(this.dryNode);
    this.dryNode.connect(this.output);
    this.context = Tone.getContext();
  }
  
  connect(destination) {
    this.output.connect(destination);
    return this;
  }
  
  disconnect(destination) {
    this.output.disconnect(destination);
    return this;
  }
  
  async setPlugin(pluginId) {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.pluginId = pluginId;
    
    if (pluginId) {
      if (!this.workletLoaded) {
        try {
          await Tone.context.addAudioWorkletModule('/vst-worklet.js');
          this.workletLoaded = true;
        } catch (e) {
          console.error("Failed to load VST AudioWorklet:", e);
          return;
        }
      }
      
      if (this.workletNode) {
        this.workletNode.disconnect();
        this.input.disconnect(this.workletNode);
      }
      
      this.workletNode = this.context.createAudioWorkletNode('vst-processor');
      
      // Route audio through the worklet
      this.input.disconnect(this.dryNode);
      Tone.connect(this.input, this.workletNode);
      Tone.connect(this.workletNode, this.output);
      
      this.ws = new WebSocket(`ws://localhost:8013/ws/vst/${pluginId}`);
      this.ws.binaryType = "arraybuffer";
      
      this.workletNode.port.onmessage = (event) => {
        if (this.ws && this.ws.readyState === 1) { // OPEN
          this.ws.send(event.data);
        }
      };
      
      this.ws.onmessage = (event) => {
         this.workletNode.port.postMessage(event.data, [event.data]);
      };
    } else {
      // Revert to bypass
      if (this.workletNode) {
        this.workletNode.disconnect();
        this.input.disconnect(this.workletNode);
      }
      this.input.connect(this.dryNode);
    }
  }
}
const vstBridgeFX = new VSTBridgeNode();
vstBridgeFX.connect(masterVolumeNode);

// ═══════════════════════════════════════════════════════════════════════════
// INSTRUMENT SYNTHESIS FACTORY
// ═══════════════════════════════════════════════════════════════════════════

const createChannelNodes = (trackIndex) => {
  const eq = new Tone.EQ3(0, 0, 0);
  const channel = new Tone.Channel({ volume: 0, pan: 0 }).connect(eq);
  eq.connect(masterVolumeNode);
  
  // Sends
  const sendReverb = new Tone.Volume(-Infinity).connect(reverbFX);
  const sendDelay = new Tone.Volume(-Infinity).connect(delayFX);
  const sendPitch = new Tone.Volume(-Infinity).connect(pitchShiftFX);
  const sendVst = new Tone.Volume(-Infinity).connect(vstBridgeFX.input);
  channel.connect(sendReverb);
  channel.connect(sendDelay);
  channel.connect(sendPitch);
  channel.connect(sendVst);

  const meter = new Tone.Meter();
  channel.connect(meter);
  return { channel, meter, eq, sendReverb, sendDelay, sendPitch, sendVst };
};

// 1. Kick (Punchy 909 / 808 Membrane)
const kickNodes = createChannelNodes(1);
const kickSynth = new Tone.MembraneSynth({
  pitchDecay: 0.05,
  octaves: 8,
  oscillator: { type: 'sine' },
  envelope: { attack: 0.001, decay: 0.4, sustain: 0.01, release: 0.4 }
}).connect(kickNodes.channel);

// 2. Snare (Layered Noise + Membrane)
const snareNodes = createChannelNodes(2);
const snareNoise = new Tone.NoiseSynth({
  noise: { type: 'pink' },
  envelope: { attack: 0.001, decay: 0.18, sustain: 0, release: 0.1 }
}).connect(snareNodes.channel);
const snareBody = new Tone.MembraneSynth({
  pitchDecay: 0.01,
  octaves: 2,
  envelope: { attack: 0.001, decay: 0.15, sustain: 0, release: 0.1 }
}).connect(snareNodes.channel);

// 3. Closed Hi-Hat (Crisp Metallic)
const hihatNodes = createChannelNodes(3);
const hihatSynth = new Tone.MetalSynth({
  frequency: 250,
  envelope: { attack: 0.001, decay: 0.04, release: 0.02 },
  harmonicity: 5.1,
  modulationIndex: 32,
  resonance: 4000,
  octaves: 1.5
}).connect(hihatNodes.channel);

// 4. Open Hi-Hat
const openHatNodes = createChannelNodes(4);
const openHatSynth = new Tone.MetalSynth({
  frequency: 220,
  envelope: { attack: 0.001, decay: 0.35, release: 0.2 },
  harmonicity: 4.5,
  modulationIndex: 28,
  resonance: 3500,
  octaves: 1.5
}).connect(openHatNodes.channel);

// 5. Clap / Perc
const clapNodes = createChannelNodes(5);
const clapSynth = new Tone.NoiseSynth({
  noise: { type: 'white' },
  envelope: { attack: 0.008, decay: 0.22, sustain: 0, release: 0.1 }
}).connect(clapNodes.channel);

// 6. 808 Sub-Bass (Deep saturated sine/square)
const bassNodes = createChannelNodes(6);
const bassSynth = new Tone.PolySynth(Tone.MonoSynth, {
  oscillator: { type: 'sine' },
  filter: { Q: 2, type: 'lowpass', rolloff: -24 },
  envelope: { attack: 0.02, decay: 0.3, sustain: 0.7, release: 0.8 },
  filterEnvelope: { attack: 0.01, decay: 0.2, sustain: 0.5, release: 0.5, baseFrequency: 100, octaves: 2.5 }
}).connect(bassNodes.channel);

// 7. Cyber PolySynth (Chords & Leads)
const leadNodes = createChannelNodes(7);
const leadSynth = new Tone.PolySynth(Tone.Synth, {
  oscillator: { type: 'sawtooth' },
  envelope: { attack: 0.02, decay: 0.2, sustain: 0.4, release: 0.6 }
}).connect(leadNodes.channel);

// 8. Neon Pluck Synth
const pluckNodes = createChannelNodes(8);
const pluckSynth = new Tone.PolySynth(Tone.FMSynth, {
  harmonicity: 2,
  modulationIndex: 5,
  oscillator: { type: 'triangle' },
  envelope: { attack: 0.005, decay: 0.2, sustain: 0.1, release: 0.3 }
}).connect(pluckNodes.channel);

// Metronome click
const metronomeSynth = new Tone.MembraneSynth({
  pitchDecay: 0.01,
  octaves: 1,
  envelope: { attack: 0.001, decay: 0.05, sustain: 0, release: 0.05 }
}).toDestination();

// ═══════════════════════════════════════════════════════════════════════════
// UNIFIED SAFE CHANNEL TRIGGER HELPER
// ═══════════════════════════════════════════════════════════════════════════

export const triggerChannel = (channel, note, duration = '16n', time = Tone.now(), velocity = 1) => {
  if (!channel || channel.mute) return;
  const synth = channel.synth;
  if (!synth) return;

  try {
    let durSec;
    if (typeof duration === 'number' && !isNaN(duration) && duration > 0) {
      durSec = duration;
    } else if (typeof duration === 'string' && duration.trim()) {
      try {
        durSec = Tone.Time(duration).toSeconds();
      } catch {
        durSec = 0.1;
      }
    } else {
      durSec = 0.1;
    }

    const scheduleTime = (time !== undefined && time !== null) ? time : Tone.now();

    switch (channel.type) {
      case 'snare':
        if (typeof synth.trigger === 'function') {
          synth.trigger(scheduleTime, durSec, velocity);
        } else if (typeof synth.triggerAttackRelease === 'function') {
          synth.triggerAttackRelease(note || 'G2', durSec, scheduleTime);
        }
        break;

      case 'clap':
        // NoiseSynth takes (duration, time, velocity)
        if (typeof synth.triggerAttackRelease === 'function') {
          synth.triggerAttackRelease(durSec, scheduleTime, velocity);
        }
        break;

      case 'hihat':
      case 'openhat':
        // MetalSynth takes (note, duration, time, velocity)
        if (typeof synth.triggerAttackRelease === 'function') {
          synth.triggerAttackRelease(note || channel.note || 'C5', durSec, scheduleTime, velocity);
        }
        break;

      case 'audio':
        if (synth.player && synth.player.loaded) {
          synth.player.start(scheduleTime);
        }
        break;

      case 'kick':
      case 'bass':
      case 'lead':
      case 'pluck':
      default:
        if (typeof synth.triggerAttackRelease === 'function') {
          synth.triggerAttackRelease(note || channel.note || 'C4', durSec, scheduleTime, velocity);
        }
        break;
    }
  } catch (err) {
    console.warn(`[DAW Engine] Error triggering channel ${channel.id}:`, err);
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// INITIAL CHANNEL DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

const DEFAULT_CHANNELS = [
  { 
    id: 'c1', 
    name: 'Kick 909', 
    type: 'kick', 
    synth: kickSynth, 
    node: kickNodes.channel, 
    eq: kickNodes.eq, 
    meter: kickNodes.meter, 
    sendReverb: kickNodes.sendReverb, 
    sendDelay: kickNodes.sendDelay, 
    sendPitch: kickNodes.sendPitch, 
    sendVst: kickNodes.sendVst, 
    volume: 0, 
    pan: 0, 
    mute: false, 
    solo: false, 
    note: 'C1', 
    color: '#ff5e5e', 
    steps: [true, false, false, false, true, false, false, false, true, false, false, false, true, false, false, false], 
    midiNotes: [] 
  },
  { 
    id: 'c2', 
    name: 'Snare Trap', 
    type: 'snare', 
    synth: { 
      trigger: (time, duration = '16n', velocity = 1) => { 
        const t = (time !== undefined && time !== null) ? time : Tone.now();
        snareNoise.triggerAttackRelease(duration, t, velocity); 
        snareBody.triggerAttackRelease('G2', duration, t, velocity); 
      },
      triggerAttackRelease: (note, duration = '16n', time) => {
        const t = (time !== undefined && time !== null) ? time : Tone.now();
        snareNoise.triggerAttackRelease(duration, t);
        snareBody.triggerAttackRelease(note || 'G2', duration, t);
      }
    }, 
    node: snareNodes.channel, 
    eq: snareNodes.eq, 
    meter: snareNodes.meter, 
    sendReverb: snareNodes.sendReverb, 
    sendDelay: snareNodes.sendDelay, 
    sendPitch: snareNodes.sendPitch, 
    sendVst: snareNodes.sendVst, 
    volume: 0, 
    pan: 0, 
    mute: false, 
    solo: false, 
    note: 'G2', 
    color: '#5eff7b', 
    steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false], 
    midiNotes: [] 
  },
  { 
    id: 'c3', 
    name: 'Hi-Hat Closed', 
    type: 'hihat', 
    synth: hihatSynth, 
    node: hihatNodes.channel, 
    eq: hihatNodes.eq, 
    meter: hihatNodes.meter, 
    sendReverb: hihatNodes.sendReverb, 
    sendDelay: hihatNodes.sendDelay, 
    sendPitch: hihatNodes.sendPitch, 
    sendVst: hihatNodes.sendVst, 
    volume: -3, 
    pan: 0.1, 
    mute: false, 
    solo: false, 
    note: 'C5', 
    color: '#5ee4ff', 
    steps: [true, false, true, false, true, false, true, false, true, false, true, false, true, false, true, false], 
    midiNotes: [] 
  },
  { 
    id: 'c4', 
    name: 'Hi-Hat Open', 
    type: 'openhat', 
    synth: openHatSynth, 
    node: openHatNodes.channel, 
    eq: openHatNodes.eq, 
    meter: openHatNodes.meter, 
    sendReverb: openHatNodes.sendReverb, 
    sendDelay: openHatNodes.sendDelay, 
    sendPitch: openHatNodes.sendPitch, 
    sendVst: openHatNodes.sendVst, 
    volume: -4, 
    pan: -0.2, 
    mute: false, 
    solo: false, 
    note: 'C5', 
    color: '#ffbd5e', 
    steps: [false, false, true, false, false, false, true, false, false, false, true, false, false, false, true, false], 
    midiNotes: [] 
  },
  { 
    id: 'c5', 
    name: 'Clap 808', 
    type: 'clap', 
    synth: clapSynth, 
    node: clapNodes.channel, 
    eq: clapNodes.eq, 
    meter: clapNodes.meter, 
    sendReverb: clapNodes.sendReverb, 
    sendDelay: clapNodes.sendDelay, 
    sendPitch: clapNodes.sendPitch, 
    sendVst: clapNodes.sendVst, 
    volume: -2, 
    pan: 0, 
    mute: false, 
    solo: false, 
    note: null, 
    color: '#d95eff', 
    steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false], 
    midiNotes: [] 
  },
  { 
    id: 'c6', 
    name: '808 Sub-Bass', 
    type: 'bass', 
    synth: bassSynth, 
    node: bassNodes.channel, 
    eq: bassNodes.eq, 
    meter: bassNodes.meter, 
    sendReverb: bassNodes.sendReverb, 
    sendDelay: bassNodes.sendDelay, 
    sendPitch: bassNodes.sendPitch, 
    sendVst: bassNodes.sendVst, 
    volume: 1, 
    pan: 0, 
    mute: false, 
    solo: false, 
    note: 'C2', 
    color: '#ff3b30', 
    steps: [true, false, false, false, false, false, true, false, false, false, false, false, true, false, false, false], 
    midiNotes: [{ step: 0, note: 'C2', duration: 2 }, { step: 6, note: 'D#2', duration: 2 }, { step: 12, note: 'G2', duration: 2 }] 
  },
  { 
    id: 'c7', 
    name: 'Cyber Lead', 
    type: 'lead', 
    synth: leadSynth, 
    node: leadNodes.channel, 
    eq: leadNodes.eq, 
    meter: leadNodes.meter, 
    sendReverb: leadNodes.sendReverb, 
    sendDelay: leadNodes.sendDelay, 
    sendPitch: leadNodes.sendPitch, 
    sendVst: leadNodes.sendVst, 
    volume: -3, 
    pan: 0, 
    mute: false, 
    solo: false, 
    note: 'C4', 
    color: '#00f0ff', 
    steps: Array(16).fill(false), 
    midiNotes: [{ step: 0, note: 'C4', duration: 2 }, { step: 4, note: 'D#4', duration: 2 }, { step: 8, note: 'G4', duration: 2 }, { step: 12, note: 'A#4', duration: 2 }] 
  },
  { 
    id: 'c8', 
    name: 'Neon Pluck', 
    type: 'pluck', 
    synth: pluckSynth, 
    node: pluckNodes.channel, 
    eq: pluckNodes.eq, 
    meter: pluckNodes.meter, 
    sendReverb: pluckNodes.sendReverb, 
    sendDelay: pluckNodes.sendDelay, 
    sendPitch: pluckNodes.sendPitch, 
    sendVst: pluckNodes.sendVst, 
    volume: -4, 
    pan: 0.2, 
    mute: false, 
    solo: false, 
    note: 'C5', 
    color: '#ff007f', 
    steps: Array(16).fill(false), 
    midiNotes: [{ step: 2, note: 'G4', duration: 1 }, { step: 6, note: 'A#4', duration: 1 }, { step: 10, note: 'D5', duration: 1 }, { step: 14, note: 'C5', duration: 1 }] 
  }
];

let repeatEventId = null;
let transportStepIndex = 0;

export const useDawStore = create((set, get) => ({
  compositorNodes: [
    { id: '1', type: 'videoSource', position: { x: 50, y: 150 }, data: { trackName: 'V1' } },
    { id: '2', type: 'colorTransform', position: { x: 300, y: 150 }, data: { lut: 'Rec.709' } },
    { id: '3', type: 'masterOut', position: { x: 550, y: 150 }, data: { resolution: '1920x1080' } }
  ],
  compositorEdges: [
    { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#00f0ff' } },
    { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#5eff7b' } }
  ],
  
  // App state
  isPlaying: false,
  playMode: 'PAT', // 'PAT' or 'SONG'
  bpm: 130,
  currentStep: 0,
  currentBar: 0,
  stepCount: 16, // 16 or 32
  activePatternId: 1,
  activeChannelId: 'c7', // Focus for Piano Roll
  activeMixerTrackId: 0, // 0 = Master, 1-8 = Inserts
  isMetronomeOn: false,
  isEngineStarted: false,
  masterVolume: 0,
  activeView: 'multimedia', // 'multimedia', 'all', 'channel_rack', 'playlist', 'mixer', 'vst_thematic'
  setActiveView: (view) => set({ activeView: view }),
  
  channels: DEFAULT_CHANNELS,
  
  // FX Parameters
  fxState: {
    reverb: { enabled: true, decay: 2.5, wet: 0.3 },
    delay: { enabled: true, time: '8n', feedback: 0.4, wet: 0.25 },
    distortion: { enabled: false, amount: 0.3, wet: 0.2 },
    filter: { enabled: false, freq: 2000, type: 'lowpass' },
    pitchShift: { enabled: false, pitch: 0 },
    vst: { enabled: false, pluginId: null, availablePlugins: [] }
  },
  
  fetchAvailableVstPlugins: async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 1500);
      const res = await fetch('http://localhost:8013/api/vst/scan', { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.status === 'success') {
        set(state => ({ fxState: { ...state.fxState, vst: { ...state.fxState.vst, availablePlugins: data.plugins || [] } } }));
      }
    } catch(e) {
      // VST daemon is optional, silent fallback
    }
  },
  
  loadVstPlugin: async (pluginPath) => {
    try {
      const res = await fetch('http://localhost:8013/api/vst/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: pluginPath })
      });
      const data = await res.json();
      if (data && data.status === 'success') {
        set(state => ({ fxState: { ...state.fxState, vst: { ...state.fxState.vst, pluginId: data.plugin_id } } }));
        vstBridgeFX.setPlugin(data.plugin_id);
      }
    } catch(e) {
      console.warn('Failed to load VST plugin:', e);
    }
  },

  // Node Compositor state actions
  setCompositorNodes: (fn) => set(state => ({ compositorNodes: typeof fn === 'function' ? fn(state.compositorNodes) : fn })),
  setCompositorEdges: (fn) => set(state => ({ compositorEdges: typeof fn === 'function' ? fn(state.compositorEdges) : fn })),

  // -----------------------------------------
  // PLAYBACK & SEQUENCING
  // -----------------------------------------

  // Playlist Timeline Clips
  playlistTracks: [
    { id: 1, name: 'Drums', clips: [{ bar: 0, length: 4, patternId: 1, color: '#ff5e5e' }, { bar: 4, length: 4, patternId: 1, color: '#ff5e5e' }] },
    { id: 2, name: 'Bassline', clips: [{ bar: 0, length: 4, patternId: 1, color: '#ff3b30' }, { bar: 4, length: 4, patternId: 1, color: '#ff3b30' }] },
    { id: 3, name: 'Synth Chords', clips: [{ bar: 0, length: 4, patternId: 1, color: '#00f0ff' }, { bar: 4, length: 4, patternId: 1, color: '#00f0ff' }] },
    { id: 4, name: 'Lead Melodies', clips: [{ bar: 4, length: 4, patternId: 1, color: '#ff007f' }] },
    { id: 5, name: 'Percussion FX', clips: [{ bar: 2, length: 2, patternId: 1, color: '#d95eff' }] },
    { id: 6, name: 'Automations', clips: [] }
  ],

  setPlaylistTracks: (tracksOrFn) => set(state => ({
    playlistTracks: typeof tracksOrFn === 'function' ? tracksOrFn(state.playlistTracks) : tracksOrFn
  })),

  addPlaylistClip: (trackId, clip) => set(state => {
    const exists = state.playlistTracks.some(t => t.id === trackId);
    if (!exists) {
      return {
        playlistTracks: [...state.playlistTracks, { id: trackId, name: clip.title || 'Audio Clip', clips: [clip] }]
      };
    }
    return {
      playlistTracks: state.playlistTracks.map(t => 
        t.id === trackId ? { ...t, clips: [...t.clips, clip] } : t
      )
    };
  }),

  // Video Tracks for Multimedia AV Studio
  videoTracks: [
    { id: 'v1', name: 'V1', clips: [] },
    { id: 'v2', name: 'V2', clips: [] }
  ],
  
  captions: [], // Array of { word, start, end }
  setCaptions: (captions) => set({ captions }),

  // Initialize Web Audio Engine
  initEngine: async () => {
    try {
      if (Tone.context.state !== 'running') {
        await Tone.start();
      }
    } catch (e) {
      console.warn("Tone.start() waiting for user gesture:", e);
    }

    Tone.Transport.bpm.value = get().bpm;

    if (!get().isEngineStarted) {
      if (repeatEventId !== null) {
        Tone.Transport.clear(repeatEventId);
        repeatEventId = null;
      }

      // Step Sequencer Repeat Loop (Accurately timed 16n callback)
      repeatEventId = Tone.Transport.scheduleRepeat((time) => {
        const state = get();
        const stepCount = state.stepCount || 16;
        const channels = state.channels;
        const isMetronome = state.isMetronomeOn;

        const currentStepTick = transportStepIndex % stepCount;
        const currentBarTick = Math.floor(transportStepIndex / stepCount) % 16;
        transportStepIndex++;

        // Metronome Click on every beat (every 4 steps in 16th time)
        if (isMetronome && currentStepTick % 4 === 0) {
          try {
            metronomeSynth.triggerAttackRelease(currentStepTick === 0 ? 'C5' : 'G4', '32n', time, 0.4);
          } catch (e) {
            // ignore
          }
        }

        // Trigger Channel Steps
        channels.forEach(ch => {
          if (ch.mute) return;
          
          // Check Step Sequencer grid
          if (ch.steps && ch.steps[currentStepTick]) {
            triggerChannel(ch, ch.note, '16n', time);
          }

          // Check Piano Roll MIDI Notes
          if (ch.midiNotes && ch.midiNotes.length > 0) {
            const notesAtStep = ch.midiNotes.filter(n => n.step === currentStepTick);
            notesAtStep.forEach(n => {
              const durSec = (n.duration || 1) * Tone.Time('16n').toSeconds();
              triggerChannel(ch, n.note, durSec, time);
            });
          }
        });

        // Exact Visual Sync via Tone.Draw (runs on requestAnimationFrame at precise audio time)
        Tone.Draw.schedule(() => {
          set({ currentStep: currentStepTick, currentBar: currentBarTick });
        }, time);

      }, '16n');

      set({ isEngineStarted: true });
    }
  },

  // Transport Actions
  togglePlay: async () => {
    await get().initEngine();
    const playing = !get().isPlaying;
    if (playing) {
      transportStepIndex = 0;
      set({ currentStep: 0, currentBar: 0 });
      Tone.Transport.position = 0;
      Tone.Transport.start();
    } else {
      Tone.Transport.stop();
      transportStepIndex = 0;
      set({ currentStep: 0, currentBar: 0 });
    }
    set({ isPlaying: playing });
  },

  setBpm: (bpm) => {
    Tone.Transport.bpm.value = bpm;
    set({ bpm });
  },

  setPlayMode: (playMode) => set({ playMode }),
  toggleMetronome: () => set(state => ({ isMetronomeOn: !state.isMetronomeOn })),
  setActiveView: (activeView) => set({ activeView }),
  setActiveChannelId: (activeChannelId) => set({ activeChannelId }),
  setActiveMixerTrackId: (activeMixerTrackId) => set({ activeMixerTrackId }),

  // Video Track Actions
  addVideoClip: (trackId, clip) => set(state => ({
    videoTracks: state.videoTracks.map(track => {
      if (track.id === trackId) {
        return { ...track, clips: [...track.clips, { id: Math.random().toString(36).substr(2, 9), ...clip }] };
      }
      return track;
    })
  })),
  updateVideoClip: (trackId, clipId, updates) => set(state => ({
    videoTracks: state.videoTracks.map(track => {
      if (track.id === trackId) {
        return {
          ...track,
          clips: track.clips.map(clip => clip.id === clipId ? { ...clip, ...updates } : clip)
        };
      }
      return track;
    })
  })),
  splitVideoClip: (trackId, clipId, splitAtBar) => set(state => {
    return {
      videoTracks: state.videoTracks.map(track => {
        if (track.id === trackId) {
          const clipIndex = track.clips.findIndex(c => c.id === clipId);
          if (clipIndex === -1) return track;
          const clip = track.clips[clipIndex];
          if (splitAtBar > clip.bar && splitAtBar < clip.bar + clip.length) {
            const splitPoint = splitAtBar - clip.bar;
            const firstHalf = { ...clip, length: splitPoint };
            const secondHalf = { 
              ...clip, 
              id: Math.random().toString(36).substr(2, 9), 
              bar: splitAtBar, 
              length: clip.length - splitPoint,
              startOffset: (clip.startOffset || 0) + splitPoint
            };
            const newClips = [...track.clips];
            newClips.splice(clipIndex, 1, firstHalf, secondHalf);
            return { ...track, clips: newClips };
          }
        }
        return track;
      })
    };
  }),

  // Step Sequencer Actions
  toggleStep: (channelId, stepIndex) => {
    set(state => ({
      channels: state.channels.map(ch => {
        if (ch.id === channelId) {
          const newSteps = [...ch.steps];
          newSteps[stepIndex] = !newSteps[stepIndex];
          return { ...ch, steps: newSteps };
        }
        return ch;
      })
    }));
  },

  setStepCount: (stepCount) => {
    set(state => ({
      stepCount,
      channels: state.channels.map(ch => {
        let newSteps = [...ch.steps];
        if (stepCount > newSteps.length) {
          newSteps = [...newSteps, ...Array(stepCount - newSteps.length).fill(false)];
        } else {
          newSteps = newSteps.slice(0, stepCount);
        }
        return { ...ch, steps: newSteps };
      })
    }));
  },

  // Piano Roll Actions
  addOrToggleMidiNote: (channelId, note, step) => {
    set(state => ({
      channels: state.channels.map(ch => {
        if (ch.id === channelId) {
          const existingIndex = ch.midiNotes.findIndex(n => n.note === note && n.step === step);
          let newNotes = [...ch.midiNotes];
          if (existingIndex >= 0) {
            newNotes.splice(existingIndex, 1); // Remove
          } else {
            newNotes.push({ note, step, duration: 2 }); // Add
          }
          return { ...ch, midiNotes: newNotes };
        }
        return ch;
      })
    }));
  },

  previewNote: async (channelId, note) => {
    await get().initEngine();
    const ch = get().channels.find(c => c.id === channelId);
    if (ch) {
      triggerChannel(ch, note, '8n', Tone.now());
    }
  },

  // MIDI / QWERTY Input Handlers
  triggerNoteStart: async (channelId, note) => {
    await get().initEngine();
    const ch = get().channels.find(c => c.id === channelId);
    if (!ch || !ch.synth) return;
    const now = Tone.now();

    if (ch.type === 'clap') {
      triggerChannel(ch, null, '16n', now);
    } else if (ch.type === 'snare') {
      if (ch.synth.trigger) ch.synth.trigger(now);
    } else if (typeof ch.synth.triggerAttack === 'function') {
      ch.synth.triggerAttack(note || ch.note || 'C4', now);
    } else {
      triggerChannel(ch, note, '16n', now);
    }
  },

  triggerNoteEnd: (channelId, note) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (!ch || !ch.synth) return;
    const now = Tone.now();
    
    if (typeof ch.synth.triggerRelease === 'function') {
      try {
        if (ch.type === 'lead' || ch.type === 'pluck') {
          ch.synth.triggerRelease(note, now);
        } else if (ch.type !== 'clap' && ch.type !== 'snare' && ch.type !== 'kick') {
          ch.synth.triggerRelease(now);
        }
      } catch (e) {
        // Safe fallback
      }
    }
  },

  // Mixer Actions
  setChannelVolume: (channelId, volume) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (ch && ch.node) {
      ch.node.volume.value = volume;
    }
    set(state => ({
      channels: state.channels.map(c => c.id === channelId ? { ...c, volume } : c)
    }));
  },

  setChannelPan: (channelId, pan) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (ch && ch.node) {
      ch.node.pan.value = pan;
    }
    set(state => ({
      channels: state.channels.map(c => c.id === channelId ? { ...c, pan } : c)
    }));
  },

  toggleChannelMute: (channelId) => {
    set(state => ({
      channels: state.channels.map(c => {
        if (c.id === channelId) {
          const mute = !c.mute;
          if (c.node) c.node.mute = mute;
          return { ...c, mute };
        }
        return c;
      })
    }));
  },

  toggleChannelSolo: (channelId) => {
    set(state => {
      const target = state.channels.find(c => c.id === channelId);
      const newSolo = !target.solo;
      return {
        channels: state.channels.map(c => {
          const isSolo = c.id === channelId ? newSolo : false;
          if (c.node) c.node.mute = newSolo ? c.id !== channelId : false;
          return { ...c, solo: isSolo };
        })
      };
    });
  },

  setMasterVolume: (val) => {
    masterVolumeNode.volume.value = val;
    set({ masterVolume: val });
  },

  // Sound Designer (EQ & ADSR)
  setChannelEQ: (channelId, band, value) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (ch && ch.eq) {
      if (band === 'low') ch.eq.low.value = value;
      if (band === 'mid') ch.eq.mid.value = value;
      if (band === 'high') ch.eq.high.value = value;
    }
  },

  setChannelEnvelope: (channelId, param, value) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (ch && ch.synth && ch.synth.envelope) {
      ch.synth.envelope[param] = value;
    }
  },

  setChannelSend: (channelId, fxName, volume) => {
    const ch = get().channels.find(c => c.id === channelId);
    if (ch) {
      if (fxName === 'reverb' && ch.sendReverb) ch.sendReverb.volume.value = volume;
      if (fxName === 'delay' && ch.sendDelay) ch.sendDelay.volume.value = volume;
      if (fxName === 'pitchShift' && ch.sendPitch) ch.sendPitch.volume.value = volume;
      if (fxName === 'vst' && ch.sendVst) ch.sendVst.volume.value = volume;
    }
  },

  // FX Controls
  toggleFX: (fxName) => {
    set(state => {
      const newState = !state.fxState[fxName].enabled;
      const newFX = { ...state.fxState, [fxName]: { ...state.fxState[fxName], enabled: newState } };
      
      if (fxName === 'reverb') {
        newState ? reverbFX.connect(masterVolumeNode) : reverbFX.disconnect(masterVolumeNode);
      } else if (fxName === 'delay') {
        newState ? delayFX.connect(masterVolumeNode) : delayFX.disconnect(masterVolumeNode);
      } else if (fxName === 'distortion') {
        newState ? distortionFX.connect(masterVolumeNode) : distortionFX.disconnect(masterVolumeNode);
      } else if (fxName === 'pitchShift') {
        newState ? pitchShiftFX.connect(masterVolumeNode) : pitchShiftFX.disconnect(masterVolumeNode);
      } else if (fxName === 'vst') {
        newState ? vstBridgeFX.connect(masterVolumeNode) : vstBridgeFX.disconnect(masterVolumeNode);
      }
      return { fxState: newFX };
    });
  },

  // AI Beat Assistant Preset Generator
  generateAIBeat: (genre = 'trap') => {
    set(state => {
      if (genre === 'trap') {
        return {
          bpm: 140,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, false, false, true, false, false, false, true, false, false, false, false, false] };
            if (ch.type === 'snare' || ch.type === 'clap') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'C2', duration: 2 }, { step: 6, note: 'D#2', duration: 2 }, { step: 10, note: 'G2', duration: 2 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 0, note: 'C4', duration: 4 }, { step: 4, note: 'D#4', duration: 4 }, { step: 8, note: 'G4', duration: 4 }, { step: 12, note: 'A#4', duration: 4 }] };
            return ch;
          })
        };
      } else if (genre === 'synthwave') {
        return {
          bpm: 120,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, true, false, false, false, true, false, false, false, true, false, false, false] };
            if (ch.type === 'snare') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [false, false, true, false, false, false, true, false, false, false, true, false, false, false, true, false] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'A1', duration: 1 }, { step: 2, note: 'A1', duration: 1 }, { step: 4, note: 'A1', duration: 1 }, { step: 6, note: 'A1', duration: 1 }, { step: 8, note: 'F1', duration: 1 }, { step: 10, note: 'F1', duration: 1 }, { step: 12, note: 'G1', duration: 1 }, { step: 14, note: 'G1', duration: 1 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 0, note: 'A3', duration: 4 }, { step: 8, note: 'F3', duration: 4 }, { step: 12, note: 'G3', duration: 4 }] };
            return ch;
          })
        };
      }
      return state;
    });
  },

  clearAllSteps: () => {
    set(state => ({
      channels: state.channels.map(ch => ({
        ...ch,
        steps: Array(state.stepCount).fill(false),
        midiNotes: []
      }))
    }));
  },

  // Add Audio Channel (for Microphone Recording or file import)
  addAudioChannel: async (audioUrl, name = 'Mic Record') => {
    const { channel, meter, eq, sendReverb, sendDelay, sendPitch, sendVst } = createChannelNodes(get().channels.length + 1);
    const player = new Tone.Player(audioUrl).connect(channel);
    try {
      await Tone.loaded();
    } catch (e) {
      console.warn("Tone.loaded() for audio track:", e);
    }

    const newId = `c${get().channels.length + 1}_${Date.now()}`;
    const newChannel = {
      id: newId,
      name,
      type: 'audio',
      synth: {
        player,
        triggerAttack: () => player.start(),
        triggerAttackRelease: (note, dur, time) => player.start(time || Tone.now()),
        triggerRelease: () => player.stop(),
        envelope: null
      },
      node: channel,
      eq,
      meter,
      sendReverb,
      sendDelay,
      sendPitch,
      sendVst,
      volume: 0,
      pan: 0,
      mute: false,
      solo: false,
      note: null,
      color: '#ffc107',
      steps: Array(get().stepCount).fill(false),
      midiNotes: []
    };
    
    set(state => ({
      channels: [...state.channels, newChannel]
    }));
  },

  // Floating AI Context Widget State
  aiWidgetVisible: false,
  aiWidgetPosition: { bar: 0, trackId: null, x: 0, y: 0 },
  
  setAiWidgetVisible: (visible, position = null) => {
    set(state => ({
      aiWidgetVisible: visible,
      aiWidgetPosition: position || state.aiWidgetPosition
    }));
  },

  submitAIPrompt: async (prompt, bar, trackId) => {
    try {
      const response = await fetch('http://localhost:8000/api/ai/audio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, bar, trackId })
      });
      const data = await response.json();
      if (data.success && data.url) {
        const audioUrl = data.url.startsWith('http') ? data.url : `http://localhost:8000${data.url}`;
        await get().addAudioChannel(audioUrl, `AI: ${prompt}`);
      }
    } catch (error) {
      console.error("AI Audio Generation Failed:", error);
    }
    set({ aiWidgetVisible: false });
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // VST3 PLUGIN SCANNING & PARAMETER MUTATION
  // ═══════════════════════════════════════════════════════════════════════════
  availableVstPlugins: [],
  activeLoadedVstId: null,
  activeVstParams: [],

  fetchAvailableVstPlugins: async () => {
    try {
      const res = await fetch('http://localhost:8013/api/vst/scan');
      if (res.ok) {
        const data = await res.json();
        set({ availableVstPlugins: data.plugins || [] });
      }
    } catch (e) {
      console.debug("VST3 Bridge Daemon scan unavailable:", e);
    }
  },

  loadVstPlugin: async (pluginPath) => {
    try {
      const res = await fetch('http://localhost:8013/api/vst/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: pluginPath })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'success') {
          const pluginId = data.plugin_id;
          set({ activeLoadedVstId: pluginId });
          await vstBridgeFX.setPlugin(pluginId);
          await get().fetchVstParameters(pluginId);
        }
      }
    } catch (e) {
      console.error("Failed to load VST plugin:", e);
    }
  },

  fetchVstParameters: async (pluginId) => {
    try {
      const res = await fetch(`http://localhost:8013/api/vst/parameters/${pluginId}`);
      if (res.ok) {
        const data = await res.json();
        set({ activeVstParams: data.parameters || [] });
      }
    } catch (e) {
      console.debug("Failed to fetch VST parameters:", e);
    }
  },

  setVstParameter: async (pluginId, paramName, value) => {
    try {
      await fetch('http://localhost:8013/api/vst/set-param', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plugin_id: pluginId, param_name: paramName, value })
      });
      set(state => ({
        activeVstParams: state.activeVstParams.map(p => 
          p.name === paramName ? { ...p, raw_value: value } : p
        )
      }));
    } catch (e) {
      console.debug("Failed to mutate VST parameter:", e);
    }
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // HARDWARE WEB MIDI RECORDING CONTROLLER
  // ═══════════════════════════════════════════════════════════════════════════
  isMidiRecording: false,
  midiInputs: [],
  activeMidiInput: null,

  toggleMidiRecording: async () => {
    const isRec = !get().isMidiRecording;
    set({ isMidiRecording: isRec });
    if (isRec && navigator.requestMIDIAccess) {
      try {
        const midiAccess = await navigator.requestMIDIAccess();
        const inputs = Array.from(midiAccess.inputs.values());
        set({ midiInputs: inputs.map(i => ({ id: i.id, name: i.name || 'MIDI Controller' })) });

        inputs.forEach(input => {
          input.onmidimessage = (msg) => {
            if (!get().isMidiRecording) return;
            const [status, noteNum, velocity] = msg.data;
            const command = status >> 4;
            // 9 = note on, 8 = note off
            if (command === 9 && velocity > 0) {
              const noteNames = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
              const octave = Math.floor(noteNum / 12) - 1;
              const noteName = `${noteNames[noteNum % 12]}${octave}`;
              const activeChId = get().activeChannelId;
              const curStep = get().currentStep;
              get().previewNote(activeChId, noteName);
              get().addOrToggleMidiNote(activeChId, curStep, noteName, 1);
            }
          };
        });
      } catch (err) {
        console.warn("Web MIDI Access error:", err);
      }
    }
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // SUB-MIX SUMMING BUSES
  // ═══════════════════════════════════════════════════════════════════════════
  subBuses: [
    { id: 'bus_drums', name: 'BUS A: Drums', volume: 0, pan: 0, mute: false, solo: false, color: '#ef4444' },
    { id: 'bus_inst', name: 'BUS B: Inst', volume: 0, pan: 0, mute: false, solo: false, color: '#3b82f6' },
    { id: 'bus_vox', name: 'BUS C: Vocals', volume: 0, pan: 0, mute: false, solo: false, color: '#10b981' },
    { id: 'bus_fx', name: 'BUS D: Master FX', volume: 0, pan: 0, mute: false, solo: false, color: '#a855f7' }
  ],

  setSubBusVolume: (busId, volume) => {
    set(state => ({
      subBuses: state.subBuses.map(b => b.id === busId ? { ...b, volume } : b)
    }));
  },

  setSubBusPan: (busId, pan) => {
    set(state => ({
      subBuses: state.subBuses.map(b => b.id === busId ? { ...b, pan } : b)
    }));
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // THEATRICAL EVENTBUS TRANSPORT SYNC
  // ═══════════════════════════════════════════════════════════════════════════
  theatricalSyncEnabled: true,

  toggleTheatricalSync: () => {
    set(state => ({ theatricalSyncEnabled: !state.theatricalSyncEnabled }));
  },

  broadcastTheatricalEvent: async (eventName, payload = {}) => {
    if (!get().theatricalSyncEnabled) return;
    try {
      // Broadcast to Port 8013 VST daemon and Port 8080 Unreal / Matrix EventBus
      fetch('http://localhost:8013/api/vst/trigger-theme', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: payload.theme || 'hype' })
      }).catch(() => {});

      fetch('http://localhost:8080/api/unreal/theatrical/stage-trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme: payload.theme || 'hype' })
      }).catch(() => {});
    } catch (e) {
      console.debug("Theatrical sync broadcast suppressed:", e);
    }
  }
}));

