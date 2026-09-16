import { create } from 'zustand';

export const useOmniStore = create((set, get) => ({
  // Global AV State
  isMasterLive: false,
  setMasterLive: (status) => set({ isMasterLive: status }),
  
  // Shared Telemetry
  telemetry: {
    fps: "0.0",
    bitrate: "0.0kbits/s",
    speed: "0.0x",
    dropped: "0",
    game_name: "None Detected"
  },
  setTelemetry: (data) => set({ telemetry: data }),

  // Cross-Communication Flags
  activeVideoSource: null,
  setActiveVideoSource: (source) => set({ activeVideoSource: source }),

  // DAW Audio Stream reference for Broadcast
  masterAudioNode: null,
  setMasterAudioNode: (node) => set({ masterAudioNode: node })
}));
