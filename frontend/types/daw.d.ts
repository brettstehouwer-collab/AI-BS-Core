import type * as Tone from 'tone';
import type { Node, Edge } from '@xyflow/react';

export type TrackId = string | number;
export type Update<T> = T | ((previous: T) => T);
export interface MidiNote { note: string; step: number; duration: number }
export interface ChannelBase {
  id: string; name: string; node: Tone.Channel; eq: Tone.EQ3; meter: Tone.Meter;
  sendReverb: Tone.Volume; sendDelay: Tone.Volume; sendPitch: Tone.Volume; sendVst: Tone.Volume;
  volume: number; pan: number; mute: boolean; solo: boolean; note: string | null;
  color: string; steps: boolean[]; midiNotes: MidiNote[];
}
export interface SnareInstrument {
  trigger(time: number, duration?: Tone.Unit.Time, velocity?: number): void;
  triggerAttackRelease(note: Tone.Unit.Frequency, duration?: Tone.Unit.Time, time?: number): void;
}
export interface AudioInstrument {
  player: Tone.Player; envelope: null;
  triggerAttack(): unknown;
  triggerAttackRelease(note: string, duration: Tone.Unit.Time, time?: number): unknown;
  triggerRelease(): unknown;
}
export type DawChannel = ChannelBase & (
  { type: 'kick'; synth: Tone.MembraneSynth } |
  { type: 'snare'; synth: SnareInstrument } |
  { type: 'hihat' | 'openhat'; synth: Tone.MetalSynth } |
  { type: 'clap'; synth: Tone.NoiseSynth } |
  { type: 'bass'; synth: Tone.PolySynth<Tone.MonoSynth> } |
  { type: 'lead' | 'pluck'; synth: Tone.PolySynth<Tone.Synth> } |
  { type: 'audio'; synth: AudioInstrument }
);
export interface PlaylistClip {
  id?: string; bar: number; length: number; title?: string; color?: string;
  patternId?: number; url?: string; audioUrl?: string | AudioBuffer | null; audioBuffer?: AudioBuffer | null;
  slipOffset?: number; muted?: boolean;
}
export interface PlaylistClipInput extends Partial<PlaylistClip> {
  trackId?: TrackId; startBar?: number; lengthBars?: number; name?: string;
  url?: string; buffer?: AudioBuffer;
}
export interface PlaylistTrack { id: TrackId; name: string; clips: PlaylistClip[] }
export interface VideoClip { id: string; bar: number; length: number; startOffset?: number; url?: string; src?: string; name?: string; color?: string; title?: string; muted?: boolean }
export interface VideoTrack { id: string; name: string; clips: VideoClip[] }
export interface Caption { word: string; start: number; end: number }
export interface Stem { name?: string; url?: string; color?: string; length?: number }
export interface VstPlugin { id?: string; name: string; path: string; vendor?: string; type?: string }
export interface VstParameter { name: string; raw_value: number; min?: number; max?: number; min_value?: number; max_value?: number; value?: number; label?: string }
export interface FxState {
  reverb: { enabled: boolean; decay: number; wet: number };
  delay: { enabled: boolean; time: Tone.Unit.Time; feedback: number; wet: number };
  distortion: { enabled: boolean; amount: number; wet: number };
  filter: { enabled: boolean; freq: number; type: BiquadFilterType };
  pitchShift: { enabled: boolean; pitch: number };
  vst: { enabled: boolean; pluginId: string | null; availablePlugins: VstPlugin[] };
}
export interface AssistantMessage { role: string; content: string; timestamp?: string; suggestions?: string[]; actions?: AssistantAction[]; engine?: string }
export interface AssistantAction {
  type: string; bpm?: number | string; volume?: number | string; view?: string; genre?: string;
  channelId?: string; fx?: keyof FxState; params?: Partial<FxState[keyof FxState]>;
}
export interface WidgetPosition { bar: number; trackId: TrackId | null; x: number; y: number }
export interface SubBus { id: string; name: string; volume: number; pan: number; mute: boolean; solo: boolean; color: string }
export interface DawState {
  compositorNodes: Node[]; compositorEdges: Edge[];
  isPlaying: boolean; playMode: string; bpm: number; currentStep: number; currentBar: number;
  stepCount: number; activePatternId: number; activeChannelId: string; activeMixerTrackId: number;
  isMetronomeOn: boolean; isEngineStarted: boolean; masterVolume: number; activeView: string;
  channels: DawChannel[]; fxState: FxState; playlistTracks: PlaylistTrack[]; videoTracks: VideoTrack[];
  captions: Caption[]; assistantDrawerOpen: boolean; assistantHistory: AssistantMessage[];
  aiWidgetVisible: boolean; aiWidgetPosition: WidgetPosition; availableVstPlugins: VstPlugin[];
  activeLoadedVstId: string | null; activeVstParams: VstParameter[]; isMidiRecording: boolean;
  midiInputs: { id: string; name: string }[]; activeMidiInput: string | null;
  subBuses: SubBus[]; theatricalSyncEnabled: boolean;
  setActiveView(view: string): void;
  fetchAvailableVstPlugins(): Promise<void>;
  loadVstPlugin(path: string): Promise<void>;
  setCompositorNodes(value: Update<Node[]>): void;
  setCompositorEdges(value: Update<Edge[]>): void;
  setPlaylistTracks(value: Update<PlaylistTrack[]>): void;
  addPlaylistClip(trackOrClip: TrackId | PlaylistClipInput, clip?: PlaylistClipInput): void;
  addStemTracksToPlaylist(stems: Stem[], projectName?: string): void;
  setCaptions(captions: Caption[]): void;
  initEngine(): Promise<void>;
  togglePlay(): Promise<void>;
  setBpm(bpm: number): void;
  setPlayMode(mode: string): void;
  toggleMetronome(): void;
  setActiveChannelId(id: string): void;
  setActiveMixerTrackId(id: number): void;
  addVideoClip(trackId: string, clip: Omit<VideoClip, 'id'> & { id?: string }): void;
  updateVideoClip(trackId: string, clipId: string, updates: Partial<VideoClip>): void;
  splitVideoClip(trackId: string, clipId: string, bar: number): void;
  toggleStep(channelId: string, step: number): void;
  setStepCount(count: number): void;
  addOrToggleMidiNote(channelId: string, note: string, step: number, duration?: number): void;
  previewNote(channelId: string, note: string): Promise<void>;
  triggerNoteStart(channelId: string, note: string): Promise<void>;
  triggerNoteEnd(channelId: string, note: string): void;
  setChannelVolume(channelId: string, volume: number): void;
  setChannelPan(channelId: string, pan: number): void;
  toggleChannelMute(channelId: string): void;
  toggleChannelSolo(channelId: string): void;
  setMasterVolume(volume: number): void;
  setChannelEQ(channelId: string, band: 'low' | 'mid' | 'high', value: number): void;
  setChannelEnvelope(channelId: string, param: 'attack' | 'decay' | 'sustain' | 'release', value: number): void;
  setChannelSend(channelId: string, fx: keyof FxState, volume: number): void;
  toggleFX(fx: keyof FxState): void;
  generateAIBeat(genre?: string): void;
  setAssistantDrawerOpen(open: boolean): void;
  toggleAssistantDrawer(): void;
  addAssistantMessage(message: AssistantMessage): void;
  clearAssistantHistory(): void;
  executeAssistantActions(actions?: AssistantAction[]): void;
  clearAllSteps(): void;
  addAudioChannel(url: string, name?: string): Promise<void>;
  setAiWidgetVisible(visible: boolean, position?: WidgetPosition | null): void;
  submitAIPrompt(prompt: string, bar: number, trackId: TrackId): Promise<void>;
  fetchVstParameters(id: string): Promise<void>;
  setVstParameter(id: string, parameter: string, value: number): Promise<void>;
  toggleMidiRecording(): Promise<void>;
  setSubBusVolume(id: string, volume: number): void;
  setSubBusPan(id: string, pan: number): void;
  toggleTheatricalSync(): void;
  broadcastTheatricalEvent(name: string, payload?: { theme?: string }): Promise<void>;
}

export interface WaveClip { id: string; name?: string; buffer: AudioBuffer | null; startOffset: number; color?: string }
export interface WaveTrack {
  id: string; name: string; clips: WaveClip[]; color: string;
  isMuted: boolean; isSolo: boolean; volume: number; pan: number;
}
