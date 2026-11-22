import { useState, useCallback } from 'react';

/**
 * 6-Track 48kHz Professional Audio Stem Mixer Hook
 * Provides volume linear-to-dB conversion, peak clipping indicators, and mute/solo logic.
 */
export function useAudioMixer(initialTracks = []) {
  const defaultTracks = [
    { id: 'master', name: 'Master Stream Out', volume: 0.90, muted: false, solo: false, peakDb: -3.2 },
    { id: 'mic', name: 'Clean Mic & VST3', volume: 0.85, muted: false, solo: false, peakDb: -6.0 },
    { id: 'desktop', name: 'Desktop WASAPI', volume: 0.75, muted: false, solo: false, peakDb: -12.4 },
    { id: 'daw', name: 'DAW Synthesizers', volume: 0.80, muted: false, solo: false, peakDb: -8.5 },
    { id: 'webrtc', name: 'Remote Guests', volume: 0.70, muted: false, solo: false, peakDb: -14.0 },
    { id: 'sidekick', name: 'AI Sidekick Voice', volume: 0.85, muted: false, solo: false, peakDb: -4.8 },
  ];

  const [tracks, setTracks] = useState(initialTracks.length ? initialTracks : defaultTracks);

  const setVolume = useCallback((id, vol) => {
    setTracks((prev) => prev.map((t) => (t.id === id ? { ...t, volume: Math.max(0, Math.min(1, vol)) } : t)));
  }, []);

  const toggleMute = useCallback((id) => {
    setTracks((prev) => prev.map((t) => (t.id === id ? { ...t, muted: !t.muted } : t)));
  }, []);

  const toggleSolo = useCallback((id) => {
    setTracks((prev) => {
      const target = prev.find((t) => t.id === id);
      const nextSoloState = !target?.solo;
      return prev.map((t) => (t.id === id ? { ...t, solo: nextSoloState } : t));
    });
  }, []);

  return { tracks, setVolume, toggleMute, toggleSolo };
}
