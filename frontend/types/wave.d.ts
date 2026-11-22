export interface WaveClip {id: string; name?: string; startOffset: number; buffer: AudioBuffer}
export interface WaveTrack {id: string; name: string; isMuted: boolean; isSolo: boolean; gain: number; pan: number; channelMode: string; sampleRate: number; clips: WaveClip[]}
export interface WaveDragState {x: number; trackId?: string | null; clipId?: string | null; initialStartOffset?: number}

export type EditableClip = import('./daw').PlaylistClipInput & {url?: string; duration?: number; pitch?: number; fineTune?: number; stretchMode?: string; isReversed?: boolean; isNormalized?: boolean; volume?: number; pan?: number; fadeIn?: number; fadeOut?: number};
export interface Slice {id: string; start: number; end: number; label: string; color: string}
export interface StemDetail {filename: string; size_bytes: number; url: string}
export interface StemSession {session_id: string; origin_name: string; title?: string; timestamp?: string; stems_detail: Record<string, StemDetail>; repair_metadata?: {cut_timestamp?: string; pre_cut_chord?: string; post_cut_chord?: string; repair_strategy?: string}}

export interface BrowserItem {id?: string | number; size_formatted?: string; name: string; path: string; is_dir?: boolean; category?: string; extension?: string; size?: number; modified?: string}
