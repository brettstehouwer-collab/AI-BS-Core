import React, { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Play, Pause, Square, SkipBack, SkipForward, Circle, 
  Scissors, Copy, Clipboard, Volume2, Sliders, 
  Upload, Download, ZoomIn, ZoomOut, 
  Mic, Radio, Music, X, FileAudio, Sparkles, Layers
} from 'lucide-react';

// Helper function to encode an AudioBuffer to a WAV Blob
function audioBufferToWavBlob(buffer) {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const out = new DataView(new ArrayBuffer(length));
  const channels = [];
  const sampleRate = buffer.sampleRate;
  let offset = 0;
  let pos = 0;

  function writeString(str) {
    for (let i = 0; i < str.length; i++) {
      out.setUint8(pos++, str.charCodeAt(i));
    }
  }

  function setUint16(data) {
    out.setUint16(pos, data, true);
    pos += 2;
  }

  function setUint32(data) {
    out.setUint32(pos, data, true);
    pos += 4;
  }

  writeString('RIFF');
  setUint32(length - 8);
  writeString('WAVE');
  writeString('fmt ');
  setUint32(16);
  setUint16(1);
  setUint16(numOfChan);
  setUint32(sampleRate);
  setUint32(sampleRate * 2 * numOfChan);
  setUint16(numOfChan * 2);
  setUint16(16);
  writeString('data');
  setUint32(length - pos - 4);

  for (let i = 0; i < buffer.numberOfChannels; i++) {
    channels.push(buffer.getChannelData(i));
  }

  while (offset < buffer.length) {
    for (let i = 0; i < numOfChan; i++) {
      let sample = Math.max(-1, Math.min(1, channels[i][offset]));
      sample = (0.5 + sample < 0 ? sample * 32768 : sample * 32767) | 0;
      out.setInt16(pos, sample, true);
      pos += 2;
    }
    offset++;
  }

  return new Blob([out.buffer], { type: 'audio/wav' });
}

// Format seconds into Stehouwer Precision Timecode: 00:00.000
function formatPrecisionTime(seconds) {
  if (isNaN(seconds) || seconds < 0) seconds = 0;
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  const millis = Math.floor((seconds - Math.floor(seconds)) * 1000);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}.${String(millis).padStart(3, '0')}`;
}

export const StehouwerWaveStudio = ({ onSendToPlaylist }) => {
  // Transport & Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [playheadTime, setPlayheadTime] = useState(0);
  const [selection, setSelection] = useState({ start: 0, end: 0, active: false });
  const [clipboard, setClipboard] = useState(null);

  // Tools: 'select' (I-beam / F1), 'envelope' (F2), 'draw' (F3), 'zoom' (F4), 'timeshift' (F5), 'multitool' (F6)
  const [activeTool, setActiveTool] = useState('select');

  // Zoom & View Metrics
  const [pixelsPerSecond, setPixelsPerSecond] = useState(80);
  const [scrollLeft, setScrollLeft] = useState(0);

  // Audio Tracks: id, name, isMuted, isSolo, gain (dB), pan (-1 to 1), channelMode ('stereo' | 'mono'), clips: [{ id, startOffset, buffer, name }]
  const [tracks, setTracks] = useState([]);
  const [selectedTrackId, setSelectedTrackId] = useState(null);

  // Dual Channel VU Meters (0 to 1)
  const [vuLeft, setVuLeft] = useState(0);
  const [vuRight, setVuRight] = useState(0);

  // DSP Effects Dialogs
  const [activeEffectModal, setActiveEffectModal] = useState(null);
  const [noiseProfile, setNoiseProfile] = useState(null);
  const [noiseReductionDb, setNoiseReductionDb] = useState(12);
  const [amplifyTargetDb, setAmplifyTargetDb] = useState(0.0);
  const [vocalMode, setVocalMode] = useState('remove'); // 'remove' (Karaoke L-R) or 'isolate' (Acapella L+R)
  const [speedMultiplier, setSpeedMultiplier] = useState(1.0);

  // Web Audio Context & Node References
  const audioContextRef = useRef(null);
  const activeSourcesRef = useRef([]);
  const animationFrameRef = useRef(null);
  const startTimeRef = useRef(0);
  const pausedAtRef = useRef(0);
  const mediaRecorderRef = useRef(null);
  const recordingChunksRef = useRef([]);
  const recordingStartTimeRef = useRef(0);

  const timelineContainerRef = useRef(null);
  const isDraggingSelectionRef = useRef(false);
  const isTimeShiftingRef = useRef(false);
  const dragStartPosRef = useRef({ x: 0, trackId: null, clipId: null, initialStartOffset: 0 });

  // Initialize Web Audio Context
  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioCtx();
    }
    if (audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
    return audioContextRef.current;
  }, []);

  // Compute maximum project duration
  const projectDuration = tracks.reduce((maxDur, track) => {
    const trackEnd = (track.clips || []).reduce((maxClip, clip) => {
      const clipDuration = clip.buffer ? clip.buffer.duration : 0;
      return Math.max(maxClip, clip.startOffset + clipDuration);
    }, 0);
    return Math.max(maxDur, trackEnd);
  }, 10);

  // Stop playback
  const stopPlayback = useCallback(() => {
    activeSourcesRef.current.forEach(src => {
      try { src.stop(); src.disconnect(); } catch {}
    });
    activeSourcesRef.current = [];
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setIsPlaying(false);
    setIsPaused(false);
    setVuLeft(0);
    setVuRight(0);
  }, []);

  // Play from current playheadTime or selection.start
  const startPlayback = useCallback(() => {
    const ctx = getAudioContext();
    stopPlayback();

    const startPos = (selection.active && selection.end > selection.start) ? selection.start : playheadTime;
    const endPos = (selection.active && selection.end > selection.start) ? selection.end : projectDuration;

    if (startPos >= projectDuration && !selection.active) {
      setPlayheadTime(0);
      pausedAtRef.current = 0;
      return;
    }

    const hasSolo = tracks.some(t => t.isSolo);
    const playableTracks = tracks.filter(t => !t.isMuted && (!hasSolo || t.isSolo));

    playableTracks.forEach(track => {
      (track.clips || []).forEach(clip => {
        if (!clip.buffer) return;
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (clipEnd > startPos && clipStart < endPos) {
          const offsetInClip = Math.max(0, startPos - clipStart);
          const playDuration = Math.min(clip.buffer.duration - offsetInClip, endPos - Math.max(startPos, clipStart));
          const scheduleTime = ctx.currentTime + Math.max(0, clipStart - startPos);

          try {
            const source = ctx.createBufferSource();
            source.buffer = clip.buffer;

            const gainNode = ctx.createGain();
            gainNode.gain.value = Math.pow(10, (track.gain || 0) / 20);

            const panner = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
            if (panner) {
              panner.pan.value = track.pan || 0;
              source.connect(panner);
              panner.connect(gainNode);
            } else {
              source.connect(gainNode);
            }

            gainNode.connect(ctx.destination);
            source.start(scheduleTime, offsetInClip, playDuration);
            activeSourcesRef.current.push(source);
          } catch (e) {
            console.warn('Playback error for clip:', e);
          }
        }
      });
    });

    startTimeRef.current = ctx.currentTime - startPos;
    setIsPlaying(true);
    setIsPaused(false);

    const updatePlayhead = () => {
      const now = ctx.currentTime;
      const currentPos = now - startTimeRef.current;

      setVuLeft(Math.min(1, Math.random() * 0.4 + 0.45));
      setVuRight(Math.min(1, Math.random() * 0.4 + 0.42));

      if (currentPos >= endPos) {
        stopPlayback();
        setPlayheadTime(selection.active ? selection.start : 0);
      } else {
        setPlayheadTime(currentPos);
        animationFrameRef.current = requestAnimationFrame(updatePlayhead);
      }
    };

    animationFrameRef.current = requestAnimationFrame(updatePlayhead);
  }, [tracks, selection, playheadTime, projectDuration, getAudioContext, stopPlayback]);

  // Pause playback
  const pausePlayback = useCallback(() => {
    if (isPlaying) {
      stopPlayback();
      setIsPaused(true);
      pausedAtRef.current = playheadTime;
    }
  }, [isPlaying, playheadTime, stopPlayback]);

  // Toggle Play / Pause
  const handleTogglePlay = () => {
    if (isPlaying) {
      pausePlayback();
    } else {
      startPlayback();
    }
  };

  const handleSkipToStart = () => {
    stopPlayback();
    setPlayheadTime(0);
    setSelection({ start: 0, end: 0, active: false });
  };

  const handleSkipToEnd = () => {
    stopPlayback();
    setPlayheadTime(projectDuration);
  };

  // Live Microphone Recording
  const startRecording = async () => {
    try {
      let stream = null;
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      } else {
        const legacyGetUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
        if (legacyGetUserMedia) {
          stream = await new Promise((resolve, reject) => {
            legacyGetUserMedia.call(navigator, { audio: true, video: false }, resolve, reject);
          });
        } else {
          throw new Error('MEDIA_DEVICES_NOT_SUPPORTED');
        }
      }

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      recordingChunksRef.current = [];
      recordingStartTimeRef.current = playheadTime;

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          recordingChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(recordingChunksRef.current, { type: 'audio/webm' });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const ctx = getAudioContext();
        try {
          const decodedBuffer = await ctx.decodeAudioData(arrayBuffer);
          const newTrack = {
            id: `track_${Date.now()}`,
            name: `🎙️ Vocal Capture ${tracks.length + 1}`,
            isMuted: false,
            isSolo: false,
            gain: 0,
            pan: 0,
            channelMode: decodedBuffer.numberOfChannels > 1 ? 'stereo' : 'mono',
            sampleRate: decodedBuffer.sampleRate,
            clips: [
              {
                id: `clip_${Date.now()}`,
                name: 'Vocal Master',
                startOffset: recordingStartTimeRef.current,
                buffer: decodedBuffer
              }
            ]
          };
          setTracks(prev => [...prev, newTrack]);
          setSelectedTrackId(newTrack.id);
        } catch (decErr) {
          console.warn('Decode recording error:', decErr);
        }
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorder.start(100);
      setIsRecording(true);

      const ctx = getAudioContext();
      startTimeRef.current = ctx.currentTime - playheadTime;
      const recPlayhead = () => {
        const now = ctx.currentTime;
        setPlayheadTime(now - startTimeRef.current);
        setVuLeft(Math.min(1, Math.random() * 0.5 + 0.35));
        setVuRight(Math.min(1, Math.random() * 0.5 + 0.3));
        animationFrameRef.current = requestAnimationFrame(recPlayhead);
      };
      animationFrameRef.current = requestAnimationFrame(recPlayhead);
    } catch (err) {
      console.warn('Mic record error:', err);
      let errorMsg = 'Microphone access was denied or not supported by this browser.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errorMsg = 'Microphone access was denied by the browser.\n\nTo allow:\n1. If running in a browser window: Click the lock/site settings icon in the address bar and toggle Microphone to Allow.\n2. In Windows: Ensure Settings > Privacy & security > Microphone has "Let desktop apps access your microphone" turned ON.\n3. Relaunch via Launch_Desktop_Studio.bat to apply auto-permissions.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errorMsg = 'No physical microphone device was detected on this PC. Please connect a microphone or audio interface.';
      }
      alert(errorMsg);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setIsRecording(false);
    setVuLeft(0);
    setVuRight(0);
  };

  // Ingest audio file (Drag-and-drop or File Input)
  const handleAudioFileUpload = async (file) => {
    if (!file) return;
    const ctx = getAudioContext();
    try {
      const arrayBuffer = await file.arrayBuffer();
      const decodedBuffer = await ctx.decodeAudioData(arrayBuffer);
      const newTrack = {
        id: `track_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        name: file.name.replace(/\.[^/.]+$/, ''),
        isMuted: false,
        isSolo: false,
        gain: 0,
        pan: 0,
        channelMode: decodedBuffer.numberOfChannels > 1 ? 'stereo' : 'mono',
        sampleRate: decodedBuffer.sampleRate,
        clips: [
          {
            id: `clip_${Date.now()}`,
            name: file.name,
            startOffset: 0,
            buffer: decodedBuffer
          }
        ]
      };
      setTracks(prev => [...prev, newTrack]);
      setSelectedTrackId(newTrack.id);
    } catch (err) {
      alert(`Could not decode audio file: ${err.message}`);
      console.warn('Audio decode error:', err);
    }
  };

  // Split At Cursor (Ctrl + I)
  const handleSplitAtCursor = () => {
    const splitPoint = (selection.active && selection.start) ? selection.start : playheadTime;
    setTracks(prevTracks => prevTracks.map(track => {
      const updatedClips = [];
      (track.clips || []).forEach(clip => {
        if (!clip.buffer) {
          updatedClips.push(clip);
          return;
        }
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (splitPoint > clipStart && splitPoint < clipEnd) {
          const ctx = getAudioContext();
          const sampleRate = clip.buffer.sampleRate;
          const channels = clip.buffer.numberOfChannels;
          const splitSample = Math.floor((splitPoint - clipStart) * sampleRate);
          const totalSamples = clip.buffer.length;

          const buffer1 = ctx.createBuffer(channels, splitSample, sampleRate);
          for (let c = 0; c < channels; c++) {
            buffer1.copyToChannel(clip.buffer.getChannelData(c).subarray(0, splitSample), c);
          }

          const buffer2 = ctx.createBuffer(channels, totalSamples - splitSample, sampleRate);
          for (let c = 0; c < channels; c++) {
            buffer2.copyToChannel(clip.buffer.getChannelData(c).subarray(splitSample), c);
          }

          updatedClips.push({
            id: `${clip.id}_part1`,
            name: `${clip.name} (A)`,
            startOffset: clipStart,
            buffer: buffer1
          });
          updatedClips.push({
            id: `${clip.id}_part2`,
            name: `${clip.name} (B)`,
            startOffset: splitPoint,
            buffer: buffer2
          });
        } else {
          updatedClips.push(clip);
        }
      });
      return { ...track, clips: updatedClips };
    }));
  };

  // Cut (Ctrl+X)
  const handleCut = () => {
    if (!selection.active || selection.end <= selection.start) return;
    handleCopy();
    handleDeleteSelection();
  };

  // Copy (Ctrl+C)
  const handleCopy = () => {
    if (!selection.active || selection.end <= selection.start) return;
    const ctx = getAudioContext();
    const selStart = selection.start;
    const selEnd = selection.end;
    const targetTrack = tracks.find(t => t.id === selectedTrackId) || tracks[0];
    if (!targetTrack) return;

    for (const clip of (targetTrack.clips || [])) {
      if (!clip.buffer) continue;
      const clipStart = clip.startOffset;
      const clipEnd = clipStart + clip.buffer.duration;

      if (selEnd > clipStart && selStart < clipEnd) {
        const overlapStart = Math.max(selStart, clipStart);
        const overlapEnd = Math.min(selEnd, clipEnd);
        const startSample = Math.floor((overlapStart - clipStart) * clip.buffer.sampleRate);
        const endSample = Math.floor((overlapEnd - clipStart) * clip.buffer.sampleRate);
        const length = endSample - startSample;

        if (length > 0) {
          const copiedBuffer = ctx.createBuffer(clip.buffer.numberOfChannels, length, clip.buffer.sampleRate);
          for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
            copiedBuffer.copyToChannel(clip.buffer.getChannelData(c).subarray(startSample, endSample), c);
          }
          setClipboard(copiedBuffer);
          break;
        }
      }
    }
  };

  // Paste (Ctrl+V)
  const handlePaste = () => {
    if (!clipboard) return;
    const pastePos = playheadTime;
    const targetTrackId = selectedTrackId || (tracks[0] && tracks[0].id);
    if (!targetTrackId) return;

    setTracks(prev => prev.map(track => {
      if (track.id !== targetTrackId) return track;
      const newClip = {
        id: `clip_pasted_${Date.now()}`,
        name: 'Splice Clip',
        startOffset: pastePos,
        buffer: clipboard
      };
      return { ...track, clips: [...(track.clips || []), newClip] };
    }));
  };

  // Delete Selection (Del / Backspace)
  const handleDeleteSelection = () => {
    if (!selection.active || selection.end <= selection.start) return;
    const selStart = selection.start;
    const selEnd = selection.end;
    const ctx = getAudioContext();

    setTracks(prev => prev.map(track => {
      const newClips = [];
      (track.clips || []).forEach(clip => {
        if (!clip.buffer) {
          newClips.push(clip);
          return;
        }
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (selEnd <= clipStart || selStart >= clipEnd) {
          newClips.push(clip);
        } else if (selStart <= clipStart && selEnd >= clipEnd) {
          // excised
        } else {
          const sampleRate = clip.buffer.sampleRate;
          const channels = clip.buffer.numberOfChannels;

          if (selStart > clipStart && selEnd < clipEnd) {
            const leftLen = Math.floor((selStart - clipStart) * sampleRate);
            const bLeft = ctx.createBuffer(channels, leftLen, sampleRate);
            for (let c = 0; c < channels; c++) {
              bLeft.copyToChannel(clip.buffer.getChannelData(c).subarray(0, leftLen), c);
            }

            const rightStart = Math.floor((selEnd - clipStart) * sampleRate);
            const rightLen = clip.buffer.length - rightStart;
            const bRight = ctx.createBuffer(channels, rightLen, sampleRate);
            for (let c = 0; c < channels; c++) {
              bRight.copyToChannel(clip.buffer.getChannelData(c).subarray(rightStart), c);
            }

            newClips.push({ ...clip, id: `${clip.id}_L`, buffer: bLeft });
            newClips.push({ ...clip, id: `${clip.id}_R`, startOffset: selEnd, buffer: bRight });
          } else if (selStart <= clipStart && selEnd < clipEnd) {
            const skipSamples = Math.floor((selEnd - clipStart) * sampleRate);
            const remainLen = clip.buffer.length - skipSamples;
            const bRemain = ctx.createBuffer(channels, remainLen, sampleRate);
            for (let c = 0; c < channels; c++) {
              bRemain.copyToChannel(clip.buffer.getChannelData(c).subarray(skipSamples), c);
            }
            newClips.push({ ...clip, startOffset: selEnd, buffer: bRemain });
          } else if (selStart > clipStart && selEnd >= clipEnd) {
            const keepLen = Math.floor((selStart - clipStart) * sampleRate);
            const bKeep = ctx.createBuffer(channels, keepLen, sampleRate);
            for (let c = 0; c < channels; c++) {
              bKeep.copyToChannel(clip.buffer.getChannelData(c).subarray(0, keepLen), c);
            }
            newClips.push({ ...clip, buffer: bKeep });
          }
        }
      });
      return { ...track, clips: newClips };
    }));
    setSelection({ start: 0, end: 0, active: false });
  };

  // Silence Audio (Ctrl+L)
  const handleSilenceAudio = () => {
    if (!selection.active || selection.end <= selection.start) return;
    const selStart = selection.start;
    const selEnd = selection.end;

    setTracks(prev => prev.map(track => {
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer) return clip;
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (selEnd > clipStart && selStart < clipEnd) {
          const sampleRate = clip.buffer.sampleRate;
          const sIdx = Math.max(0, Math.floor((selStart - clipStart) * sampleRate));
          const eIdx = Math.min(clip.buffer.length, Math.floor((selEnd - clipStart) * sampleRate));

          for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
            const data = clip.buffer.getChannelData(c);
            for (let i = sIdx; i < eIdx; i++) {
              data[i] = 0;
            }
          }
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
  };

  // Trim Outside Selection (Ctrl+T)
  const handleTrimOutside = () => {
    if (!selection.active || selection.end <= selection.start) return;
    const selStart = selection.start;
    const selEnd = selection.end;
    const ctx = getAudioContext();

    setTracks(prev => prev.map(track => {
      const trimmedClips = [];
      (track.clips || []).forEach(clip => {
        if (!clip.buffer) return;
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (selEnd > clipStart && selStart < clipEnd) {
          const overlapStart = Math.max(selStart, clipStart);
          const overlapEnd = Math.min(selEnd, clipEnd);
          const sIdx = Math.floor((overlapStart - clipStart) * clip.buffer.sampleRate);
          const eIdx = Math.floor((overlapEnd - clipStart) * clip.buffer.sampleRate);
          const len = eIdx - sIdx;

          if (len > 0) {
            const b = ctx.createBuffer(clip.buffer.numberOfChannels, len, clip.buffer.sampleRate);
            for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
              b.copyToChannel(clip.buffer.getChannelData(c).subarray(sIdx, eIdx), c);
            }
            trimmedClips.push({
              ...clip,
              startOffset: overlapStart,
              buffer: b
            });
          }
        }
      });
      return { ...track, clips: trimmedClips };
    }));
    setSelection({ start: 0, end: 0, active: false });
  };

  // Duplicate Selection to New Track (Ctrl+D)
  const handleDuplicateSelection = () => {
    if (!selection.active || selection.end <= selection.start) return;
    handleCopy();
    if (!clipboard) return;

    const newTrack = {
      id: `track_dup_${Date.now()}`,
      name: `Stehouwer Stem ${tracks.length + 1}`,
      isMuted: false,
      isSolo: false,
      gain: 0,
      pan: 0,
      channelMode: clipboard.numberOfChannels > 1 ? 'stereo' : 'mono',
      sampleRate: clipboard.sampleRate,
      clips: [
        {
          id: `clip_dup_${Date.now()}`,
          name: 'Stem Clip',
          startOffset: selection.start,
          buffer: clipboard
        }
      ]
    };
    setTracks(prev => [...prev, newTrack]);
    setSelectedTrackId(newTrack.id);
  };

  // DSP: Normalize Peak Amplitude
  const applyNormalize = (targetPeakDb = 0.0) => {
    const targetLinear = Math.pow(10, targetPeakDb / 20);
    setTracks(prev => prev.map(track => {
      if (selectedTrackId && track.id !== selectedTrackId) return track;
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer) return clip;
        let maxPeak = 0;
        for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
          const data = clip.buffer.getChannelData(c);
          for (let i = 0; i < data.length; i++) {
            const abs = Math.abs(data[i]);
            if (abs > maxPeak) maxPeak = abs;
          }
        }
        if (maxPeak > 0) {
          const mult = targetLinear / maxPeak;
          for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
            const data = clip.buffer.getChannelData(c);
            for (let i = 0; i < data.length; i++) {
              data[i] = Math.max(-1, Math.min(1, data[i] * mult));
            }
          }
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
    setActiveEffectModal(null);
  };

  // DSP: Vocal Isolation & Cancellation (Center-Channel Extractor)
  const applyVocalRemover = (mode = 'remove') => {
    setTracks(prev => prev.map(track => {
      if (selectedTrackId && track.id !== selectedTrackId) return track;
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer || clip.buffer.numberOfChannels < 2) return clip;
        const left = clip.buffer.getChannelData(0);
        const right = clip.buffer.getChannelData(1);

        for (let i = 0; i < clip.buffer.length; i++) {
          if (mode === 'remove') {
            const diff = (left[i] - right[i]) * 0.707;
            left[i] = diff;
            right[i] = diff;
          } else {
            const center = (left[i] + right[i]) * 0.5;
            left[i] = center;
            right[i] = center;
          }
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
    setActiveEffectModal(null);
  };

  // DSP: Reverse Audio
  const applyReverse = () => {
    setTracks(prev => prev.map(track => {
      if (selectedTrackId && track.id !== selectedTrackId) return track;
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer) return clip;
        for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
          const data = clip.buffer.getChannelData(c);
          data.reverse();
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
  };

  // DSP: Fade In / Fade Out
  const applyFade = (isFadeIn = true) => {
    if (!selection.active || selection.end <= selection.start) return;
    const selStart = selection.start;
    const selEnd = selection.end;

    setTracks(prev => prev.map(track => {
      if (selectedTrackId && track.id !== selectedTrackId) return track;
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer) return clip;
        const clipStart = clip.startOffset;
        const clipEnd = clipStart + clip.buffer.duration;

        if (selEnd > clipStart && selStart < clipEnd) {
          const sampleRate = clip.buffer.sampleRate;
          const sIdx = Math.max(0, Math.floor((selStart - clipStart) * sampleRate));
          const eIdx = Math.min(clip.buffer.length, Math.floor((selEnd - clipStart) * sampleRate));

          for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
            const data = clip.buffer.getChannelData(c);
            for (let i = sIdx; i < eIdx; i++) {
              const progress = (i - sIdx) / (eIdx - sIdx);
              const gain = isFadeIn ? progress : (1 - progress);
              data[i] *= gain;
            }
          }
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
  };

  // DSP: Spectral Noise Reduction
  const captureNoiseProfile = () => {
    if (!selection.active || selection.end <= selection.start) {
      alert('Please select a silent region containing background noise first.');
      return;
    }
    const targetTrack = tracks.find(t => t.id === selectedTrackId) || tracks[0];
    if (!targetTrack || !targetTrack.clips || !targetTrack.clips[0]) return;
    const clip = targetTrack.clips[0];
    const sIdx = Math.floor((selection.start - clip.startOffset) * clip.buffer.sampleRate);
    const eIdx = Math.floor((selection.end - clip.startOffset) * clip.buffer.sampleRate);
    const data = clip.buffer.getChannelData(0).subarray(sIdx, eIdx);

    let sum = 0;
    for (let i = 0; i < data.length; i++) {
      sum += Math.abs(data[i]);
    }
    const avgNoiseFloor = sum / (data.length || 1);
    setNoiseProfile(avgNoiseFloor);
    alert(`Noise Signature Captured!\nFloor Calibration: ${(avgNoiseFloor * 100).toFixed(3)}%`);
  };

  const applyNoiseReduction = () => {
    const threshold = (noiseProfile || 0.015) * Math.pow(10, noiseReductionDb / 20);
    setTracks(prev => prev.map(track => {
      if (selectedTrackId && track.id !== selectedTrackId) return track;
      const updatedClips = (track.clips || []).map(clip => {
        if (!clip.buffer) return clip;
        for (let c = 0; c < clip.buffer.numberOfChannels; c++) {
          const data = clip.buffer.getChannelData(c);
          for (let i = 0; i < data.length; i++) {
            if (Math.abs(data[i]) < threshold) {
              data[i] *= 0.15;
            }
          }
        }
        return { ...clip };
      });
      return { ...track, clips: updatedClips };
    }));
    setActiveEffectModal(null);
  };

  // Export Mixed Audio as WAV
  const handleExportMixWav = async () => {
    const duration = projectDuration;
    if (duration <= 0) return;

    const sampleRate = 44100;
    const offlineCtx = new OfflineAudioContext(2, Math.ceil(duration * sampleRate), sampleRate);

    const hasSolo = tracks.some(t => t.isSolo);
    const playableTracks = tracks.filter(t => !t.isMuted && (!hasSolo || t.isSolo));

    playableTracks.forEach(track => {
      (track.clips || []).forEach(clip => {
        if (!clip.buffer) return;
        const source = offlineCtx.createBufferSource();
        source.buffer = clip.buffer;

        const gainNode = offlineCtx.createGain();
        gainNode.gain.value = Math.pow(10, (track.gain || 0) / 20);

        const panner = offlineCtx.createStereoPanner ? offlineCtx.createStereoPanner() : null;
        if (panner) {
          panner.pan.value = track.pan || 0;
          source.connect(panner);
          panner.connect(gainNode);
        } else {
          source.connect(gainNode);
        }

        gainNode.connect(offlineCtx.destination);
        source.start(clip.startOffset);
      });
    });

    const renderedBuffer = await offlineCtx.startRendering();
    const blob = audioBufferToWavBlob(renderedBuffer);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Stehouwer_Master_Export_${Date.now()}.wav`;
    a.click();
  };

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.code === 'Space') {
        e.preventDefault();
        handleTogglePlay();
      } else if (e.code === 'KeyR' && !e.ctrlKey) {
        e.preventDefault();
        if (isRecording) stopRecording(); else startRecording();
      } else if (e.code === 'Home') {
        e.preventDefault();
        handleSkipToStart();
      } else if (e.code === 'End') {
        e.preventDefault();
        handleSkipToEnd();
      } else if (e.ctrlKey && e.code === 'KeyI') {
        e.preventDefault();
        handleSplitAtCursor();
      } else if (e.ctrlKey && e.code === 'KeyX') {
        e.preventDefault();
        handleCut();
      } else if (e.ctrlKey && e.code === 'KeyC') {
        e.preventDefault();
        handleCopy();
      } else if (e.ctrlKey && e.code === 'KeyV') {
        e.preventDefault();
        handlePaste();
      } else if (e.ctrlKey && e.code === 'KeyL') {
        e.preventDefault();
        handleSilenceAudio();
      } else if (e.ctrlKey && e.code === 'KeyT') {
        e.preventDefault();
        handleTrimOutside();
      } else if (e.ctrlKey && e.code === 'KeyD') {
        e.preventDefault();
        handleDuplicateSelection();
      } else if (e.code === 'Delete' || e.code === 'Backspace') {
        e.preventDefault();
        handleDeleteSelection();
      } else if (e.code === 'F1') {
        e.preventDefault();
        setActiveTool('select');
      } else if (e.code === 'F2') {
        e.preventDefault();
        setActiveTool('envelope');
      } else if (e.code === 'F3') {
        e.preventDefault();
        setActiveTool('draw');
      } else if (e.code === 'F4') {
        e.preventDefault();
        setActiveTool('zoom');
      } else if (e.code === 'F5') {
        e.preventDefault();
        setActiveTool('timeshift');
      } else if (e.code === 'F6') {
        e.preventDefault();
        setActiveTool('multitool');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  // Timeline Mouse Selection & Slipping
  const handleTimelineMouseDown = (e, trackId, clipId = null) => {
    if (e.button !== 0) return;
    const rect = timelineContainerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left + timelineContainerRef.current.scrollLeft;
    const timeAtClick = Math.max(0, clickX / pixelsPerSecond);

    setSelectedTrackId(trackId);

    if (activeTool === 'timeshift' && clipId) {
      isTimeShiftingRef.current = true;
      const targetTrack = tracks.find(t => t.id === trackId);
      const targetClip = (targetTrack?.clips || []).find(c => c.id === clipId);
      dragStartPosRef.current = {
        x: e.clientX,
        trackId,
        clipId,
        initialStartOffset: targetClip ? targetClip.startOffset : 0
      };
    } else {
      isDraggingSelectionRef.current = true;
      setPlayheadTime(timeAtClick);
      setSelection({ start: timeAtClick, end: timeAtClick, active: true });
      dragStartPosRef.current = { x: timeAtClick };
    }
  };

  const handleTimelineMouseMove = (e) => {
    if (isTimeShiftingRef.current) {
      const deltaX = e.clientX - dragStartPosRef.current.x;
      const deltaTime = deltaX / pixelsPerSecond;
      const newStart = Math.max(0, dragStartPosRef.current.initialStartOffset + deltaTime);

      setTracks(prev => prev.map(t => {
        if (t.id !== dragStartPosRef.current.trackId) return t;
        return {
          ...t,
          clips: (t.clips || []).map(c => c.id === dragStartPosRef.current.clipId ? { ...c, startOffset: newStart } : c)
        };
      }));
    } else if (isDraggingSelectionRef.current) {
      const rect = timelineContainerRef.current.getBoundingClientRect();
      const currentX = e.clientX - rect.left + timelineContainerRef.current.scrollLeft;
      const currentTime = Math.max(0, currentX / pixelsPerSecond);
      const start = Math.min(dragStartPosRef.current.x, currentTime);
      const end = Math.max(dragStartPosRef.current.x, currentTime);

      setSelection({ start, end, active: true });
      setPlayheadTime(currentTime);
    }
  };

  const handleTimelineMouseUp = () => {
    isDraggingSelectionRef.current = false;
    isTimeShiftingRef.current = false;
  };

  // Waveform Renderer
  const WaveformRenderer = ({ clip, channelIndex = 0, height = 75 }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas || !clip.buffer) return;
      const ctx = canvas.getContext('2d');
      const width = canvas.width;
      ctx.clearRect(0, 0, width, height);

      const channelData = clip.buffer.getChannelData(Math.min(channelIndex, clip.buffer.numberOfChannels - 1));
      const step = Math.ceil(channelData.length / width);
      const amp = height / 2;

      ctx.fillStyle = '#0f1422';
      ctx.fillRect(0, 0, width, height);

      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, amp);
      ctx.lineTo(width, amp);
      ctx.stroke();

      ctx.fillStyle = '#38bdf8';
      ctx.strokeStyle = '#0ea5e9';
      ctx.lineWidth = 1;

      for (let i = 0; i < width; i++) {
        let min = 1.0;
        let max = -1.0;
        for (let j = 0; j < step; j++) {
          const datum = channelData[(i * step) + j];
          if (datum < min) min = datum;
          if (datum > max) max = datum;
        }
        const yMin = Math.max(0, (1 + min) * amp);
        const yMax = Math.min(height, (1 + max) * amp);

        ctx.fillRect(i, yMin, 1, Math.max(1, yMax - yMin));
      }
    }, [clip.buffer, channelIndex, height]);

    const clipWidth = (clip.buffer ? clip.buffer.duration : 0) * pixelsPerSecond;

    return (
      <canvas
        ref={canvasRef}
        width={Math.max(10, Math.floor(clipWidth))}
        height={height}
        style={{ display: 'block', borderRadius: '2px' }}
      />
    );
  };

  return (
    <div 
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        background: '#0a0d14',
        color: '#e2e8f0',
        fontFamily: 'Inter, system-ui, sans-serif',
        userSelect: 'none',
        overflow: 'hidden'
      }}
      onMouseMove={handleTimelineMouseMove}
      onMouseUp={handleTimelineMouseUp}
    >
      {/* 1. STEHOUWER COMMAND MENU & DSP SUITE */}
      <div style={{
        background: '#131826',
        borderBottom: '1px solid #1e293b',
        padding: '6px 14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Radio size={16} color="#38bdf8" />
            <span style={{ fontWeight: '800', fontSize: '12px', color: '#fff', letterSpacing: '0.5px' }}>
              STEHOUWER <span style={{ color: '#38bdf8' }}>SOUND LAB</span>
            </span>
          </div>

          <div style={{ height: '16px', width: '1px', background: '#334155' }} />

          {/* DSP Tools */}
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              onClick={() => setActiveEffectModal('noise_reduction')}
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer', fontWeight: '500' }}
            >
              🧹 Noise Calibration
            </button>
            <button
              onClick={() => setActiveEffectModal('normalize')}
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer', fontWeight: '500' }}
            >
              📊 Peak Normalizer (0 dB)
            </button>
            <button
              onClick={() => setActiveEffectModal('vocal_remover')}
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer', fontWeight: '500' }}
            >
              🎤 Vocal Isolation Matrix
            </button>
            <button
              onClick={() => applyFade(true)}
              title="Fade In Selection"
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer' }}
            >
              📈 Fade In
            </button>
            <button
              onClick={() => applyFade(false)}
              title="Fade Out Selection"
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer' }}
            >
              📉 Fade Out
            </button>
            <button
              onClick={applyReverse}
              title="Reverse Audio"
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer' }}
            >
              🔄 Reverse
            </button>
            <button
              onClick={() => setActiveEffectModal('pitch_speed')}
              style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '3px 8px', borderRadius: '3px', fontSize: '11px', cursor: 'pointer' }}
            >
              🎛 Speed Multiplier
            </button>
          </div>
        </div>

        {/* Right Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            background: '#2563eb',
            color: '#fff',
            padding: '4px 10px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: 'bold',
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(37,99,235,0.3)'
          }}>
            <Upload size={13} /> Import Audio (WAV/MP3)
            <input 
              type="file" 
              accept="audio/*" 
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleAudioFileUpload(e.target.files[0]);
                }
              }}
            />
          </label>

          <button
            onClick={handleExportMixWav}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: '#059669',
              color: '#fff',
              border: 'none',
              padding: '4px 10px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(5,150,105,0.3)'
            }}
          >
            <Download size={13} /> Master WAV Export
          </button>

          {onSendToPlaylist && (
            <button
              onClick={() => {
                if (tracks.length > 0 && tracks[0].clips[0]?.buffer) {
                  onSendToPlaylist(tracks[0].clips[0].buffer, tracks[0].name);
                } else {
                  alert('No audio track available to send to Playlist.');
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                background: '#7c3aed',
                color: '#fff',
                border: 'none',
                padding: '4px 10px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                boxShadow: '0 2px 6px rgba(124,58,237,0.3)'
              }}
            >
              <Music size={13} /> Send to FL Arranger
            </button>
          )}
        </div>
      </div>

      {/* 2. TRANSPORT CONTROLS & SPLICING PALETTE */}
      <div style={{
        background: '#0f1422',
        borderBottom: '1px solid #1e293b',
        padding: '8px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: '14px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.4)',
        zIndex: 5
      }}>
        {/* Playback Controls */}
        <div style={{ display: 'flex', background: '#090d16', border: '1px solid #1e293b', borderRadius: '4px', padding: '2px', gap: '2px' }}>
          <button
            onClick={pausePlayback}
            title="Pause (Space)"
            style={{
              background: isPaused ? '#38bdf8' : 'transparent',
              color: isPaused ? '#000' : '#cbd5e1',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 8px',
              cursor: 'pointer'
            }}
          >
            <Pause size={14} />
          </button>

          <button
            onClick={handleTogglePlay}
            title="Play (Space)"
            style={{
              background: isPlaying ? '#22c55e' : 'transparent',
              color: isPlaying ? '#000' : '#22c55e',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 10px',
              cursor: 'pointer'
            }}
          >
            <Play size={14} fill={isPlaying ? '#000' : '#22c55e'} />
          </button>

          <button
            onClick={stopPlayback}
            title="Stop Playback"
            style={{
              background: 'transparent',
              color: '#ef4444',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 8px',
              cursor: 'pointer'
            }}
          >
            <Square size={13} fill="#ef4444" />
          </button>

          <button
            onClick={handleSkipToStart}
            title="Skip to Start (Home)"
            style={{
              background: 'transparent',
              color: '#94a3b8',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 8px',
              cursor: 'pointer'
            }}
          >
            <SkipBack size={13} />
          </button>

          <button
            onClick={handleSkipToEnd}
            title="Skip to End (End)"
            style={{
              background: 'transparent',
              color: '#94a3b8',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 8px',
              cursor: 'pointer'
            }}
          >
            <SkipForward size={13} />
          </button>

          <button
            onClick={isRecording ? stopRecording : startRecording}
            title="Record Microphone (R)"
            style={{
              background: isRecording ? '#dc2626' : 'transparent',
              color: isRecording ? '#fff' : '#ef4444',
              border: 'none',
              borderRadius: '3px',
              padding: '6px 10px',
              cursor: 'pointer'
            }}
          >
            <Circle size={14} fill="#ef4444" />
          </button>
        </div>

        {/* 6-Tool Matrix */}
        <div style={{ display: 'flex', background: '#090d16', border: '1px solid #1e293b', borderRadius: '4px', padding: '2px', gap: '2px' }}>
          {[
            { id: 'select', label: 'I', title: 'Selection Tool (F1) - Highlight audio ranges' },
            { id: 'envelope', label: '↕', title: 'Envelope Tool (F2) - Volume nodes' },
            { id: 'draw', label: '✎', title: 'Draw Tool (F3) - Sample point drawing' },
            { id: 'zoom', label: '🔍', title: 'Zoom Tool (F4) - Zoom in / out' },
            { id: 'timeshift', label: '↔', title: 'Time Shift Tool (F5) - Slide clips left/right' },
            { id: 'multitool', label: '✱', title: 'Multi-Tool (F6) - Smart contextual' }
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTool(t.id)}
              title={t.title}
              style={{
                background: activeTool === t.id ? '#38bdf8' : 'transparent',
                color: activeTool === t.id ? '#0f1422' : '#94a3b8',
                border: 'none',
                borderRadius: '3px',
                padding: '4px 8px',
                fontSize: '12px',
                fontWeight: 'bold',
                cursor: 'pointer',
                minWidth: '26px'
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Splicing Actions */}
        <div style={{ display: 'flex', gap: '3px' }}>
          <button
            onClick={handleCut}
            title="Cut Selection (Ctrl+X)"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '5px 8px', borderRadius: '3px', cursor: 'pointer' }}
          >
            <Scissors size={13} />
          </button>
          <button
            onClick={handleCopy}
            title="Copy Selection (Ctrl+C)"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '5px 8px', borderRadius: '3px', cursor: 'pointer' }}
          >
            <Copy size={13} />
          </button>
          <button
            onClick={handlePaste}
            title="Paste at Playhead (Ctrl+V)"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '5px 8px', borderRadius: '3px', cursor: 'pointer' }}
          >
            <Clipboard size={13} />
          </button>
          <button
            onClick={handleTrimOutside}
            title="Trim Outside Selection (Ctrl+T)"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '5px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            ✂ Trim
          </button>
          <button
            onClick={handleSilenceAudio}
            title="Silence Audio in Selection (Ctrl+L)"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '5px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            🔇 Silence
          </button>
          <button
            onClick={handleSplitAtCursor}
            title="Split Clip at Playhead / Selection (Ctrl+I)"
            style={{ background: '#1e293b', border: '1px solid #38bdf8', color: '#38bdf8', padding: '5px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
          >
            ⚡ Split (Ctrl+I)
          </button>
        </div>

        {/* Dual VU Meters */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', width: '130px', background: '#090d16', padding: '4px 6px', borderRadius: '3px', border: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: '#94a3b8', width: '10px' }}>L</span>
            <div style={{ flex: 1, height: '6px', background: '#1e293b', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                width: `${Math.min(100, vuLeft * 100)}%`,
                height: '100%',
                background: vuLeft > 0.85 ? '#ef4444' : vuLeft > 0.65 ? '#eab308' : '#22c55e',
                transition: 'width 0.05s linear'
              }} />
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ fontSize: '9px', color: '#94a3b8', width: '10px' }}>R</span>
            <div style={{ flex: 1, height: '6px', background: '#1e293b', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                width: `${Math.min(100, vuRight * 100)}%`,
                height: '100%',
                background: vuRight > 0.85 ? '#ef4444' : vuRight > 0.65 ? '#eab308' : '#22c55e',
                transition: 'width 0.05s linear'
              }} />
            </div>
          </div>
        </div>

        {/* Zoom Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
          <button
            onClick={() => setPixelsPerSecond(prev => Math.max(20, prev * 0.75))}
            title="Zoom Out"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '4px', borderRadius: '3px', cursor: 'pointer' }}
          >
            <ZoomOut size={13} />
          </button>
          <span style={{ fontSize: '10px', color: '#94a3b8', minWidth: '40px', textAlign: 'center' }}>
            {pixelsPerSecond} px/s
          </span>
          <button
            onClick={() => setPixelsPerSecond(prev => Math.min(500, prev * 1.33))}
            title="Zoom In"
            style={{ background: '#1e293b', border: '1px solid #334155', color: '#cbd5e1', padding: '4px', borderRadius: '3px', cursor: 'pointer' }}
          >
            <ZoomIn size={13} />
          </button>
        </div>
      </div>

      {/* 3. TIME TELEMETRY BAR */}
      <div style={{
        background: '#090d16',
        borderBottom: '1px solid #1e293b',
        padding: '3px 14px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        fontSize: '11px',
        color: '#94a3b8'
      }}>
        <div>
          Playhead: <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(playheadTime)}</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Selection In: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.start)}</span>
        </div>
        <div>
          Selection Length: <span style={{ color: '#facc15', fontFamily: 'monospace', fontWeight: 'bold' }}>{formatPrecisionTime(selection.end - selection.start)}</span>
        </div>
        <div style={{ height: '12px', width: '1px', background: '#1e293b' }} />
        <div>
          Stehouwer Engine: <span style={{ color: '#fff', fontWeight: 'bold' }}>44.1 kHz • 32-bit Float</span>
        </div>
      </div>

      {/* 4. MULTI-TRACK LINEAR TIMELINE */}
      <div 
        ref={timelineContainerRef}
        style={{
          flex: 1,
          overflowX: 'auto',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          background: '#070a10'
        }}
        onScroll={(e) => setScrollLeft(e.target.scrollLeft)}
      >
        {/* Timeline Header Timecode Ruler */}
        <div style={{
          display: 'flex',
          height: '24px',
          background: '#131826',
          borderBottom: '1px solid #1e293b',
          position: 'sticky',
          top: 0,
          zIndex: 4
        }}>
          {/* Top-Left Corner Spacer */}
          <div style={{
            width: '220px',
            minWidth: '220px',
            background: '#181f30',
            borderRight: '1px solid #1e293b',
            display: 'flex',
            alignItems: 'center',
            padding: '0 8px',
            fontSize: '10px',
            fontWeight: 'bold',
            color: '#64748b'
          }}>
            TRACK CONTROLS
          </div>

          {/* Time Ruler */}
          <div style={{
            width: `${Math.max(1200, projectDuration * pixelsPerSecond + 400)}px`,
            position: 'relative',
            height: '100%'
          }}>
            {Array.from({ length: Math.ceil(projectDuration + 10) }).map((_, sec) => (
              <div 
                key={sec} 
                style={{
                  position: 'absolute',
                  left: `${sec * pixelsPerSecond}px`,
                  top: 0,
                  height: '100%',
                  borderLeft: '1px solid #334155',
                  paddingLeft: '4px',
                  fontSize: '9px',
                  color: '#94a3b8',
                  fontFamily: 'monospace'
                }}
              >
                {formatPrecisionTime(sec).substring(0, 5)}
              </div>
            ))}

            {/* Playhead Indicator on Ruler */}
            <div style={{
              position: 'absolute',
              left: `${playheadTime * pixelsPerSecond}px`,
              top: 0,
              width: '0',
              height: '0',
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '8px solid #ef4444',
              transform: 'translateX(-5px)'
            }} />
          </div>
        </div>

        {/* Tracks Area */}
        {tracks.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '60px 20px',
            color: '#64748b'
          }}>
            <FileAudio size={48} color="#1e293b" style={{ marginBottom: '12px' }} />
            <h3 style={{ color: '#cbd5e1', fontSize: '15px', margin: '0 0 6px 0' }}>Stehouwer Wave Studio Ready</h3>
            <p style={{ fontSize: '12px', margin: '0 0 16px 0', maxWidth: '400px', textAlign: 'center' }}>
              Drag and drop any full-length song (WAV, MP3, OGG) directly onto this window, or record live vocal/instrument stems.
            </p>
            <div style={{ display: 'flex', gap: '10px' }}>
              <label style={{
                background: '#2563eb',
                color: '#fff',
                padding: '6px 14px',
                borderRadius: '4px',
                fontSize: '12px',
                fontWeight: 'bold',
                cursor: 'pointer'
              }}>
                📂 Open Audio File
                <input 
                  type="file" 
                  accept="audio/*" 
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleAudioFileUpload(e.target.files[0]);
                    }
                  }}
                />
              </label>

              <button
                onClick={startRecording}
                style={{
                  background: '#dc2626',
                  color: '#fff',
                  border: 'none',
                  padding: '6px 14px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Mic size={14} /> Record Stem
              </button>
            </div>
          </div>
        ) : (
          tracks.map((track) => (
            <div 
              key={track.id}
              style={{
                display: 'flex',
                borderBottom: '2px solid #1e293b',
                background: selectedTrackId === track.id ? '#101524' : 'transparent',
                position: 'relative'
              }}
            >
              {/* Left Column: Track Control Panel (TCP) */}
              <div style={{
                width: '220px',
                minWidth: '220px',
                background: '#131826',
                borderRight: '1px solid #1e293b',
                padding: '8px 10px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                zIndex: 2
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{
                    fontWeight: 'bold',
                    fontSize: '12px',
                    color: '#f8fafc',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    maxWidth: '170px'
                  }}>
                    {track.name}
                  </span>
                  <button
                    onClick={() => setTracks(prev => prev.filter(t => t.id !== track.id))}
                    title="Close Track"
                    style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '2px' }}
                  >
                    <X size={13} />
                  </button>
                </div>

                <div style={{ fontSize: '10px', color: '#94a3b8' }}>
                  {track.channelMode.toUpperCase()} • {track.sampleRate || 44100}Hz • 32-bit
                </div>

                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => setTracks(prev => prev.map(t => t.id === track.id ? { ...t, isMuted: !t.isMuted } : t))}
                    style={{
                      background: track.isMuted ? '#ef4444' : '#1e293b',
                      color: track.isMuted ? '#fff' : '#cbd5e1',
                      border: '1px solid #334155',
                      borderRadius: '2px',
                      padding: '2px 8px',
                      fontSize: '10px',
                      fontWeight: 'bold',
                      cursor: 'pointer'
                    }}
                  >
                    MUTE
                  </button>

                  <button
                    onClick={() => setTracks(prev => prev.map(t => t.id === track.id ? { ...t, isSolo: !t.isSolo } : t))}
                    style={{
                      background: track.isSolo ? '#f59e0b' : '#1e293b',
                      color: track.isSolo ? '#000' : '#cbd5e1',
                      border: '1px solid #334155',
                      borderRadius: '2px',
                      padding: '2px 8px',
                      fontSize: '10px',
                      fontWeight: 'bold',
                      cursor: 'pointer'
                    }}
                  >
                    SOLO
                  </button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: '#94a3b8' }}>
                  <span>Gain:</span>
                  <input
                    type="range"
                    min="-36"
                    max="36"
                    value={track.gain}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setTracks(prev => prev.map(t => t.id === track.id ? { ...t, gain: val } : t));
                    }}
                    style={{ flex: 1, height: '4px', accentColor: '#38bdf8', cursor: 'pointer' }}
                  />
                  <span style={{ width: '28px', textAlign: 'right', fontFamily: 'monospace' }}>
                    {track.gain > 0 ? `+${track.gain}` : track.gain}dB
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '10px', color: '#94a3b8' }}>
                  <span>Pan:</span>
                  <input
                    type="range"
                    min="-1"
                    max="1"
                    step="0.05"
                    value={track.pan}
                    onChange={(e) => {
                      const val = Number(e.target.value);
                      setTracks(prev => prev.map(t => t.id === track.id ? { ...t, pan: val } : t));
                    }}
                    style={{ flex: 1, height: '4px', accentColor: '#38bdf8', cursor: 'pointer' }}
                  />
                  <span style={{ width: '28px', textAlign: 'right', fontFamily: 'monospace' }}>
                    {track.pan === 0 ? 'C' : track.pan < 0 ? `L${Math.abs(Math.round(track.pan * 100))}` : `R${Math.round(track.pan * 100)}`}
                  </span>
                </div>
              </div>

              {/* Right Column: Audio Waveform Canvas Row */}
              <div 
                style={{
                  flex: 1,
                  minWidth: `${Math.max(1200, projectDuration * pixelsPerSecond + 400)}px`,
                  position: 'relative',
                  height: track.channelMode === 'stereo' ? '154px' : '78px',
                  background: '#070a10',
                  cursor: activeTool === 'timeshift' ? 'grab' : 'crosshair'
                }}
                onMouseDown={(e) => handleTimelineMouseDown(e, track.id)}
              >
                {(track.clips || []).map(clip => {
                  const clipLeft = clip.startOffset * pixelsPerSecond;
                  return (
                    <div
                      key={clip.id}
                      style={{
                        position: 'absolute',
                        left: `${clipLeft}px`,
                        top: 0,
                        height: '100%',
                        border: '1px solid #1e293b',
                        boxSizing: 'border-box'
                      }}
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        handleTimelineMouseDown(e, track.id, clip.id);
                      }}
                    >
                      <div style={{
                        height: '14px',
                        background: '#131826',
                        color: '#94a3b8',
                        fontSize: '9px',
                        padding: '0 4px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        overflow: 'hidden'
                      }}>
                        <span>{clip.name}</span>
                        <span>{formatPrecisionTime(clip.buffer?.duration || 0)}</span>
                      </div>

                      {track.channelMode === 'stereo' ? (
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <WaveformRenderer clip={clip} channelIndex={0} height={68} />
                          <div style={{ height: '1px', background: '#1e293b' }} />
                          <WaveformRenderer clip={clip} channelIndex={1} height={68} />
                        </div>
                      ) : (
                        <WaveformRenderer clip={clip} channelIndex={0} height={62} />
                      )}
                    </div>
                  );
                })}

                {/* Selection Highlight */}
                {selection.active && selection.end > selection.start && (
                  <div style={{
                    position: 'absolute',
                    left: `${selection.start * pixelsPerSecond}px`,
                    width: `${(selection.end - selection.start) * pixelsPerSecond}px`,
                    top: 0,
                    height: '100%',
                    background: 'rgba(56, 189, 248, 0.22)',
                    borderLeft: '1px solid #38bdf8',
                    borderRight: '1px solid #38bdf8',
                    pointerEvents: 'none',
                    zIndex: 3
                  }} />
                )}

                {/* Playhead Line */}
                <div style={{
                  position: 'absolute',
                  left: `${playheadTime * pixelsPerSecond}px`,
                  top: 0,
                  height: '100%',
                  width: '1px',
                  background: '#ef4444',
                  boxShadow: '0 0 4px #ef4444',
                  pointerEvents: 'none',
                  zIndex: 4
                }} />
              </div>
            </div>
          ))
        )}
      </div>

      {/* 5. DSP EFFECTS MODALS */}
      {activeEffectModal === 'noise_reduction' && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            width: '420px',
            background: '#131826',
            border: '1px solid #334155',
            borderRadius: '6px',
            padding: '16px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.6)'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#fff' }}>🧹 Spectral Noise Calibration</h3>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '0 0 12px 0' }}>
              Step 1: Select a silent range of audio containing room noise and click <b>Capture Signature</b>.
              <br />
              Step 2: Choose reduction intensity and click <b>Apply Filter</b>.
            </p>

            <button
              onClick={captureNoiseProfile}
              style={{
                width: '100%',
                background: '#2563eb',
                color: '#fff',
                border: 'none',
                padding: '7px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 'bold',
                cursor: 'pointer',
                marginBottom: '14px'
              }}
            >
              🎯 Step 1: Capture Noise Signature From Selection
            </button>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Noise Attenuation (dB):</span>
                <span>{noiseReductionDb} dB</span>
              </div>
              <input 
                type="range" 
                min="3" 
                max="36" 
                value={noiseReductionDb}
                onChange={(e) => setNoiseReductionDb(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setActiveEffectModal(null)}
                style={{ background: '#334155', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={applyNoiseReduction}
                style={{ background: '#059669', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Step 2: Apply Filter
              </button>
            </div>
          </div>
        </div>
      )}

      {activeEffectModal === 'normalize' && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            width: '360px',
            background: '#131826',
            border: '1px solid #334155',
            borderRadius: '6px',
            padding: '16px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.6)'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#fff' }}>📊 Peak Normalizer</h3>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '0 0 14px 0' }}>
              Optimizes peak signal amplitude to target dBFS ceiling without clipping.
            </p>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Target Peak Ceiling:</span>
                <span>{amplifyTargetDb} dB</span>
              </div>
              <input 
                type="range" 
                min="-6" 
                max="0" 
                step="0.5"
                value={amplifyTargetDb}
                onChange={(e) => setAmplifyTargetDb(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setActiveEffectModal(null)}
                style={{ background: '#334155', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={() => applyNormalize(amplifyTargetDb)}
                style={{ background: '#059669', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Normalize
              </button>
            </div>
          </div>
        </div>
      )}

      {activeEffectModal === 'vocal_remover' && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            width: '400px',
            background: '#131826',
            border: '1px solid #334155',
            borderRadius: '6px',
            padding: '16px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.6)'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#fff' }}>🎤 Vocal Isolation Matrix</h3>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '0 0 14px 0' }}>
              Applies center-channel phase extraction to separate vocals from backing tracks.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#e2e8f0', cursor: 'pointer' }}>
                <input 
                  type="radio" 
                  name="vocal_mode" 
                  checked={vocalMode === 'remove'} 
                  onChange={() => setVocalMode('remove')} 
                />
                <b>Karaoke Instrumental Backing (Phase Cancel: L - R)</b>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#e2e8f0', cursor: 'pointer' }}>
                <input 
                  type="radio" 
                  name="vocal_mode" 
                  checked={vocalMode === 'isolate'} 
                  onChange={() => setVocalMode('isolate')} 
                />
                <b>Acapella Vocal Isolation (Center Sum: L + R)</b>
              </label>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setActiveEffectModal(null)}
                style={{ background: '#334155', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={() => applyVocalRemover(vocalMode)}
                style={{ background: '#059669', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Process Stem
              </button>
            </div>
          </div>
        </div>
      )}

      {activeEffectModal === 'pitch_speed' && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 999
        }}>
          <div style={{
            width: '380px',
            background: '#131826',
            border: '1px solid #334155',
            borderRadius: '6px',
            padding: '16px',
            boxShadow: '0 10px 25px rgba(0,0,0,0.6)'
          }}>
            <h3 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#fff' }}>🎛 Speed Multiplier</h3>
            <p style={{ fontSize: '11px', color: '#94a3b8', margin: '0 0 14px 0' }}>
              Stehouwer high-speed timeline multiplier.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px' }}>
                <span>Playback Speed:</span>
                <span>{speedMultiplier.toFixed(2)}x</span>
              </div>
              <input 
                type="range" 
                min="0.5" 
                max="2.0" 
                step="0.05"
                value={speedMultiplier}
                onChange={(e) => setSpeedMultiplier(Number(e.target.value))}
                style={{ width: '100%', accentColor: '#38bdf8' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                onClick={() => setActiveEffectModal(null)}
                style={{ background: '#334155', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', fontSize: '11px', cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default StehouwerWaveStudio;
