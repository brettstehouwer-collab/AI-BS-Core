import React, { useState, useEffect, useRef } from 'react';

export default function ProjectAudioPlayer({
  projectName,
  backendUrl = '',
  isOpen = true,
  onClose,
  onInsertScript
}) {
  const [audioInfo, setAudioInfo] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playbackRate, setPlaybackRate] = useState(1.0);
  const [volume, setVolume] = useState(1.0);
  
  // Transcription States
  const [transcribeStatus, setTranscribeStatus] = useState('idle'); // idle, processing, completed, error
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [transcribeStep, setTranscribeStep] = useState('');
  const [transcriptContent, setTranscriptContent] = useState('');
  const [showTranscriptModal, setShowTranscriptModal] = useState(false);
  const [isSyncingChroma, setIsSyncingChroma] = useState(false);

  const audioRef = useRef(null);
  const pollIntervalRef = useRef(null);

  const fetchAudioInfo = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/projects/${encodeURIComponent(projectName)}/audio/info`);
      const data = await res.json();
      if (data.status === 'success' && data.has_audio) {
        setAudioInfo(data);
        setDuration(data.duration_seconds || 0);
        checkTranscriptExists();
      } else {
        setAudioInfo(null);
      }
    } catch (err) {
      console.error('Failed to fetch audio info:', err);
    }
  };

  const checkTranscriptExists = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/projects/${encodeURIComponent(projectName)}/audio/transcript`);
      const data = await res.json();
      if (data.has_transcript) {
        setTranscriptContent(data.transcript_markdown);
        setTranscribeStatus('completed');
      } else if (data.task && data.task.status === 'processing') {
        setTranscribeStatus('processing');
        setTranscribeProgress(data.task.progress || 10);
        setTranscribeStep(data.task.step || 'Processing...');
        startPollingStatus();
      }
    } catch (err) {
      console.error('Failed to check transcript:', err);
    }
  };

  const startTranscription = async () => {
    setTranscribeStatus('processing');
    setTranscribeProgress(10);
    setTranscribeStep('Starting Whisper AI transcription...');
    try {
      await fetch(`${backendUrl}/api/screenwriting/projects/${encodeURIComponent(projectName)}/audio/transcribe`, {
        method: 'POST'
      });
      startPollingStatus();
    } catch (err) {
      console.error('Failed to start transcription:', err);
      setTranscribeStatus('error');
    }
  };

  const startPollingStatus = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/api/screenwriting/projects/${encodeURIComponent(projectName)}/audio/transcribe/status`);
        const data = await res.json();
        if (data.status === 'processing') {
          setTranscribeProgress(data.progress || 50);
          setTranscribeStep(data.step || 'Transcribing speech...');
        } else if (data.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setTranscribeStatus('completed');
          checkTranscriptExists();
        } else if (data.status === 'error') {
          clearInterval(pollIntervalRef.current);
          setTranscribeStatus('error');
        }
      } catch (e) {
        console.error('Error polling transcribe status:', e);
      }
    }, 2500);
  };

  useEffect(() => {
    if (projectName) {
      fetchAudioInfo();
      setIsPlaying(false);
      setCurrentTime(0);
    }
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [projectName]);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (audioRef.current.duration && !isNaN(audioRef.current.duration)) {
        setDuration(audioRef.current.duration);
      }
    }
  };

  const handleSeek = (e) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const handleRateChange = (rate) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  };

  const formatTime = (secs) => {
    if (isNaN(secs) || secs === 0) return "00:00";
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) {
      return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  if (!isOpen || !audioInfo) return null;

  return (
    <>
      <div style={{
        background: 'linear-gradient(90deg, #0b1329 0%, #111d3d 50%, #0b1329 100%)',
        borderBottom: '1px solid #1e3a8a',
        color: '#e2e8f0',
        padding: '8px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
        zIndex: 90,
        flexShrink: 0
      }}>
        <audio
          ref={audioRef}
          src={`${backendUrl}${audioInfo.stream_url}`}
          onTimeUpdate={handleTimeUpdate}
          onEnded={() => setIsPlaying(false)}
          preload="metadata"
        />

        {/* Left: Info Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.4rem' }}>🎙️</span>
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '0.85rem', color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>ElevenLabs Audio Drama Master</span>
              <span style={{ background: '#1e3a8a', color: '#93c5fd', fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px' }}>
                {audioInfo.duration_formatted}
              </span>
              <span style={{ background: '#065f46', color: '#6ee7b7', fontSize: '0.7rem', padding: '1px 6px', borderRadius: '4px' }}>
                {audioInfo.size_mb} MB
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              {audioInfo.file_name} • {audioInfo.sample_rate} Hz
            </div>
          </div>
        </div>

        {/* Center: Controls & Scrubber */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, maxWidth: '540px', minWidth: '280px' }}>
          {/* Play/Pause Button */}
          <button
            onClick={togglePlay}
            style={{
              background: isPlaying ? '#ef4444' : '#2563eb',
              color: '#fff',
              border: 'none',
              borderRadius: '50%',
              width: '34px',
              height: '34px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: '1rem',
              boxShadow: '0 2px 8px rgba(37, 99, 235, 0.4)',
              flexShrink: 0
            }}
            title={isPlaying ? "Pause Audio Drama" : "Play Audio Drama"}
          >
            {isPlaying ? '⏸' : '▶'}
          </button>

          {/* Timestamps & Progress Bar */}
          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#94a3b8', minWidth: '45px' }}>
            {formatTime(currentTime)}
          </span>

          <input
            type="range"
            min="0"
            max={duration || 100}
            value={currentTime}
            onChange={handleSeek}
            style={{
              flex: 1,
              accentColor: '#38bdf8',
              cursor: 'pointer',
              height: '5px'
            }}
          />

          <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: '#94a3b8', minWidth: '45px' }}>
            {formatTime(duration)}
          </span>
        </div>

        {/* Right: Transcription & Speed & Download */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Audio to Text Transcription Action */}
          {transcribeStatus === 'completed' ? (
            <button
              onClick={() => setShowTranscriptModal(true)}
              style={{
                background: '#047857',
                color: '#ecfdf5',
                border: '1px solid #10b981',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                boxShadow: '0 0 10px rgba(16, 185, 129, 0.3)'
              }}
              title="Open full audio transcript document"
            >
              📄 View Text Transcript
            </button>
          ) : transcribeStatus === 'processing' ? (
            <div style={{
              background: '#312e81',
              color: '#c7d2fe',
              border: '1px solid #6366f1',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '0.75rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span style={{ animation: 'spin 1s linear infinite' }}>⏳</span>
              <span>Transcribing ({transcribeProgress}%)...</span>
            </div>
          ) : (
            <button
              onClick={startTranscription}
              style={{
                background: '#1e293b',
                color: '#38bdf8',
                border: '1px solid #0284c7',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
              title="Convert this entire audio file into a text document using Whisper AI"
            >
              📝 Transcribe to Text Doc
            </button>
          )}

          {/* Playback speed selector */}
          <div style={{ display: 'flex', gap: '2px', background: '#0a0f1d', padding: '2px', borderRadius: '4px', border: '1px solid #1e293b' }}>
            {[1.0, 1.25, 1.5, 2.0].map((rate) => (
              <button
                key={rate}
                onClick={() => handleRateChange(rate)}
                style={{
                  background: playbackRate === rate ? '#2563eb' : 'transparent',
                  color: playbackRate === rate ? '#fff' : '#94a3b8',
                  border: 'none',
                  borderRadius: '3px',
                  padding: '2px 5px',
                  fontSize: '0.7rem',
                  cursor: 'pointer'
                }}
              >
                {rate}x
              </button>
            ))}
          </div>

          {/* Download Audio */}
          <a
            href={`${backendUrl}${audioInfo.stream_url}`}
            download={audioInfo.file_name}
            style={{
              background: '#1e293b',
              color: '#38bdf8',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '0.75rem',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            title="Download Master Audio File"
          >
            ⬇️ WAV
          </a>

          {typeof onClose === 'function' && (
            <button
              onClick={onClose}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.1rem', cursor: 'pointer', marginLeft: '4px' }}
              title="Hide Audio Bar"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* ── Audio Transcript Document Viewer Modal ── */}
      {showTranscriptModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.8)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            background: '#0f172a',
            border: '1px solid #334155',
            borderRadius: '8px',
            width: '90%',
            maxWidth: '900px',
            height: '85vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)'
          }}>
            {/* Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>📄 Audio Adaptation Transcript: {projectName}</span>
                  <span style={{ fontSize: '0.75rem', background: '#065f46', color: '#6ee7b7', padding: '2px 8px', borderRadius: '4px' }}>
                    Whisper AI Verified
                  </span>
                </h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                  Source: {audioInfo.file_name} ({audioInfo.duration_formatted})
                </p>
              </div>
              <button
                onClick={() => setShowTranscriptModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {/* Document Body */}
            <div style={{
              flex: 1,
              padding: '20px',
              overflowY: 'auto',
              background: '#090d16',
              color: '#cbd5e1',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '0.9rem',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap'
            }}>
              {transcriptContent || 'Loading transcript content...'}
            </div>

            {/* Actions Footer */}
            <div style={{
              padding: '14px 20px',
              borderTop: '1px solid #1e293b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              background: '#0b1120'
            }}>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                📁 Saved to <code>screenplay_projects/{projectName}/transcripts/audio_transcript.md</code>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(transcriptContent);
                    alert("Transcript copied to clipboard!");
                  }}
                  style={{
                    background: '#1e293b',
                    color: '#e2e8f0',
                    border: '1px solid #334155',
                    borderRadius: '4px',
                    padding: '6px 14px',
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  📋 Copy All Text
                </button>

                <button
                  onClick={() => {
                    const blob = new Blob([transcriptContent], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${projectName}_audio_transcript.md`;
                    a.click();
                  }}
                  style={{
                    background: '#2563eb',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '6px 14px',
                    fontSize: '0.8rem',
                    fontWeight: 'bold',
                    cursor: 'pointer'
                  }}
                >
                  ⬇️ Download .MD Document
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
