export interface CaptureWindow { hwnd?: number; title: string; process_name: string; pid?: number; game_name?: string; name?: string; is_game?: boolean }
export interface ActiveGame { name?: string; game_name: string; title: string; process_name?: string; hwnd?: number; exe?: string }
export interface BroadcastSource { id: string; name: string; type: string; enabled: boolean; active: boolean; opacity: number; volume: number; deviceId?: string; color?: string; borderWidth?: number; label?: string; recentSub?: string; latestFollower?: string; topDonor?: string; activeAlert?: boolean; alertMessage?: string }
export type BroadcastOverlay = BroadcastSource;
export interface ProbeResult { name: string; reachable: boolean; status: string; message: string; latency_ms?: number; masked_key?: string; validation?: { valid: boolean; errors?: string[]; warnings?: string[] } }
export interface TwitchLiveInfo { live: boolean; verified: boolean; viewer_count?: number; title?: string; message?: string }
export interface BroadcastChatMessage { id: number | string; user: string; badge?: string; text: string; time: string; platform?: string; color?: string }
export interface DeviceChoice { deviceId: string; label: string }
export interface AdvancedDisplayOptions extends DisplayMediaStreamOptions {
  surfaceSwitching?: 'include' | 'exclude'; systemAudio?: 'include' | 'exclude';
  selfBrowserSurface?: 'include' | 'exclude'; monitorTypeSurfaces?: 'include' | 'exclude';
}
