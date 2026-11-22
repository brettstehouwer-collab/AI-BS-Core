import { useState, useEffect, useRef } from 'react';
import { AudioMasteringChain } from '../core/audioMasteringChain';

export function useAudioMixer(initialChannels) {
  const [channels, setChannels] = useState(initialChannels);
  const dspChainRef = useRef(null);
  const monitorFrameRef = useRef(null);

  useEffect(() => {
    if (!dspChainRef.current) {
      dspChainRef.current = new AudioMasteringChain();
    }
    
    // Add audio tracks from streams when they become available
    channels.forEach(channel => {
      if (channel.stream && !dspChainRef.current.channels.has(channel.id)) {
        dspChainRef.current.addChannel(channel.id, channel.stream);
        dspChainRef.current.setVolume(channel.id, channel.volume);
        dspChainRef.current.setMute(channel.id, channel.mute);
      }
    });

    const updatePeaks = () => {
      if (dspChainRef.current) {
        setChannels(prevChannels => prevChannels.map(ch => {
          if (dspChainRef.current.channels.has(ch.id)) {
            const peak = dspChainRef.current.getPeak(ch.id);
            return { ...ch, peak };
          }
          return ch;
        }));
      }
      monitorFrameRef.current = requestAnimationFrame(updatePeaks);
    };
    
    monitorFrameRef.current = requestAnimationFrame(updatePeaks);

    return () => {
      if (monitorFrameRef.current) {
        cancelAnimationFrame(monitorFrameRef.current);
      }
    };
  }, [channels]);

  const updateVolume = (id, newVolume) => {
    if (dspChainRef.current) {
      dspChainRef.current.setVolume(id, newVolume);
    }
    setChannels(prev => prev.map(ch => ch.id === id ? { ...ch, volume: newVolume } : ch));
  };

  const toggleMute = (id) => {
    const channel = channels.find(c => c.id === id);
    if (channel && dspChainRef.current) {
      dspChainRef.current.setMute(id, !channel.mute);
    }
    setChannels(prev => prev.map(ch => ch.id === id ? { ...ch, mute: !ch.mute } : ch));
  };

  const resumeAudioContext = () => {
    if (dspChainRef.current) {
      dspChainRef.current.resume();
    }
  };

  return { channels, updateVolume, toggleMute, resumeAudioContext };
}
