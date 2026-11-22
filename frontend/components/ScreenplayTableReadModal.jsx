import { useState, useEffect, useRef } from "react";
import './ScreenplayTableReadModal.css';
import { useAppStore } from './useAppStore';

const DEFAULT_NEURAL_VOICES = [
  { id: 'en-US-GuyNeural', name: '🎙️ Guy Neural (Deep Cinematic Narrator)' },
  { id: 'en-US-ChristopherNeural', name: '🎭 Christopher Neural (Authoritative Dramatic)' },
  { id: 'en-US-AriaNeural', name: '🌟 Aria Neural (Expressive Lead Female)' },
  { id: 'en-US-JennyNeural', name: '🌸 Jenny Neural (Warm Natural Female)' },
  { id: 'en-US-EricNeural', name: '⚡ Eric Neural (Dynamic Lead Male)' },
  { id: 'en-US-RogerNeural', name: '🕶️ Roger Neural (Grounded Mature Male)' },
  { id: 'en-US-SteffanNeural', name: '🎬 Steffan Neural (Intense Character Male)' },
  { id: 'en-GB-SoniaNeural', name: '👑 Sonia Neural (British Dramatic Female)' },
  { id: 'en-GB-RyanNeural', name: '🎩 Ryan Neural (British Lead Male)' },
  { id: 'en-US-AvaNeural', name: '✨ Ava Neural (Contemporary Conversational)' },
  { id: 'en-US-AndrewNeural', name: '🔥 Andrew Neural (Energetic Protagonist)' },
  { id: 'en-US-MichelleNeural', name: '💎 Michelle Neural (Polished Professional)' }
];

/** @param {{"isOpen": boolean, "onClose"?: () => void, "screenplayText"?: string, "projectName"?: string}} props */
export default function ScreenplayTableReadModal({
  isOpen,
  onClose,
  screenplayText = '',
  projectName = 'Screenplay Project'
}) {
  const BACKEND_URL = useAppStore(state => state.BACKEND_URL) || 'http://127.0.0.1:8000';
  const [segments, setSegments] = useState(/** @type {Array<{"type": string, "speaker": string, "text": string}>} */ ([]));
  const [characters, setCharacters] = useState(/** @type {Array<string>} */ ([]));
  const [voiceMap, setVoiceMap] = useState(/** @type {Record<string, {voice?: string, pitchHz?: number, rate?: number, role?: string}>} */ ({}));
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [speed, setSpeed] = useState(1.0);
  const [availableVoices, setAvailableVoices] = useState(DEFAULT_NEURAL_VOICES);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  
  const activeLineRef = useRef(/** @type {HTMLDivElement | null} */ (null));
  const audioRef = useRef(/** @type {HTMLAudioElement | null} */ (null));
  const audioCache = useRef(new Map());
  const isComponentMounted = useRef(true);

  useEffect(() => {
    isComponentMounted.current = true;
    return () => {
      isComponentMounted.current = false;
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  // Fetch full list of Studio Neural Voices from Backend
  useEffect(() => {
    const loadStudioVoices = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/screenwriting/studio_voices`);
        /** @type {{status: string, voices: Array<{ShortName: string, Gender: string, Locale: string}>}} */
        const data = await response.json();
        if (data.status === 'success' && data.voices && data.voices.length > 0) {
          const formatted = data.voices.map( 
v => ({
            id: v.ShortName,
            name: `${v.Gender === 'Female' ? '👩' : '👨'} ${v.ShortName.replace('en-US-', '').replace('Neural', '')} (${v.Locale})`
          }));
          // Combine defaults at top
          const combined = [
            ...DEFAULT_NEURAL_VOICES,
            ...formatted.filter( 
f => !DEFAULT_NEURAL_VOICES.some(d => d.id === f.id))
          ];
          setAvailableVoices(combined);
        }
      } catch (err) {
        console.warn('Using default neural voice cast:', err);
      }
    };
    loadStudioVoices();
  }, [BACKEND_URL]);

  // Parse Fountain / Script text into structured dialogue & action segments
  useEffect(() => {
    if (!screenplayText) return;

    const lines = screenplayText.split('\n');
    const parsed = [];
    const charSet = new Set();
    let currentCharacter = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) {
        currentCharacter = null;
        continue;
      }

      // Sluglines / Scene Headings
      if (line.startsWith('INT.') || line.startsWith('EXT.') || line.startsWith('INT/EXT.')) {
        parsed.push({ type: 'slugline', text: line, speaker: 'NARRATOR' });
        currentCharacter = null;
      }
      // Character Cue (Uppercase, < 32 chars, not a scene heading or parenthesis)
      else if (
        line === line.toUpperCase() &&
        line.length < 32 &&
        !line.startsWith('(') &&
        !line.endsWith(':') &&
        !line.startsWith('INT.') &&
        !line.startsWith('EXT.')
      ) {
        const cleanChar = line.replace(/\(.*\)/, '').trim();
        currentCharacter = cleanChar;
        charSet.add(cleanChar);
      }
      // Dialogue
      else if (currentCharacter) {
        parsed.push({ type: 'dialogue', text: line, speaker: currentCharacter });
      }
      // Action / Scene Description
      else {
        parsed.push({ type: 'action', text: line, speaker: 'NARRATOR' });
      }
    }

    setSegments(parsed);
    const charList = Array.from(charSet);
    setCharacters(charList);

    // Assign realistic cast members
    /** @type {Record<string, {"voice": string, "pitchHz": number, "rate": number, "role": string}>} */
const initialMap = {
      NARRATOR: { voice: 'en-US-GuyNeural', pitchHz: 0, rate: 1.0, role: 'Narrator / Action' }
    };
    const voicePool = [
      'en-US-AriaNeural', 'en-US-EricNeural', 'en-US-JennyNeural', 
      'en-US-ChristopherNeural', 'en-US-AvaNeural', 'en-US-RogerNeural',
      'en-GB-SoniaNeural', 'en-GB-RyanNeural', 'en-US-SteffanNeural', 'en-US-AndrewNeural'
    ];
    charList.forEach(
(char,  idx) => {
      initialMap[char] = {
        voice: voicePool[idx % voicePool.length],
        pitchHz: 0,
        rate: 1.0,
        role: `Cast Role #${idx + 1}`
      };
    });
    setVoiceMap(initialMap);
  }, [screenplayText]);

  // Teleprompter Auto-Scroll to Active Line
  useEffect(() => {
    if (activeLineRef.current) {
      activeLineRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [currentIdx]);

  // Audio Generation Helper with Caching
  /** @param {string} text @param {string} voice @param {number} pitchHz @param {number} speedMultiplier */
const fetchAudioBlob = async ( text,  voice,  pitchHz,  speedMultiplier) => {
    const ratePercent = Math.round((speedMultiplier - 1.0) * 100);
    const rateStr = ratePercent >= 0 ? `+${ratePercent}%` : `${ratePercent}%`;
    const pitchStr = pitchHz >= 0 ? `+${pitchHz}Hz` : `${pitchHz}Hz`;
    const cacheKey = `${text}_${voice}_${pitchStr}_${rateStr}`;

    if (audioCache.current.has(cacheKey)) {
      return audioCache.current.get(cacheKey);
    }

    const response = await fetch(`${BACKEND_URL}/api/screenwriting/generate_audio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text || "(silence)",
        voice: voice || "en-US-AriaNeural",
        rate: rateStr,
        pitch: pitchStr
      })
    });

    if (!response.ok) throw new Error(`Audio generation failed (${response.status})`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    audioCache.current.set(cacheKey, url);
    return url;
  };

  // Playback Controller
  /** @param {number} idx */
const speakCurrentSegment = async ( idx) => {
    if (idx >= segments.length) {
      setIsPlaying(false);
      return;
    }

    const seg = segments[idx];
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }

    const speakerConfig = voiceMap[seg.speaker] || { voice: 'en-US-AriaNeural', pitchHz: 0 };
    const voice = speakerConfig.voice || 'en-US-AriaNeural';
    const pitchHz = speakerConfig.pitchHz || 0;

    setIsLoadingAudio(true);
    try {
      const audioUrl = await fetchAudioBlob(seg.text, voice, pitchHz, speed);
      setIsLoadingAudio(false);

      // Pre-fetch next line in background
      if (idx + 1 < segments.length) {
        const nextSeg = segments[idx + 1];
        const nextConfig = voiceMap[nextSeg.speaker] || { voice: 'en-US-AriaNeural', pitchHz: 0 };
        fetchAudioBlob(nextSeg.text, nextConfig.voice || 'en-US-AriaNeural', nextConfig.pitchHz || 0, speed).catch(() => {});
      }

      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        if (isComponentMounted.current && isPlaying) {
          setCurrentIdx(prev => prev + 1);
        }
      };

      audio.onerror = (e) => {
        console.error("Audio element error:", e);
        if (isComponentMounted.current && isPlaying) {
          setCurrentIdx(prev => prev + 1);
        }
      };

      if (isPlaying) {
        audio.play().catch(e => console.error("Playback error:", e));
      }
    } catch (err) {
      console.error("Audio generation exception:", err);
      setIsLoadingAudio(false);
      if (isPlaying) setCurrentIdx(prev => prev + 1);
    }
  };

  useEffect(() => {
    if (isPlaying) {
      speakCurrentSegment(currentIdx);
    } else {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    }
  }, [isPlaying, currentIdx]);

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
  };

  const handleStop = () => {
    setIsPlaying(false);
    setCurrentIdx(0);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="table-read-modal-backdrop" onClick={onClose}>
      <div className="table-read-modal-card" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="table-read-header">
          <div className="header-title-group">
            <span className="studio-icon">🎙️</span>
            <div>
              <h2 className="studio-title">Multi-Voice AI Audio Table Read Studio</h2>
              <p className="studio-subtitle">Realistic Neural Voice Cast & Synchronized Teleprompter • {projectName}</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Studio Body (Left: Teleprompter / Right: Voice Cast Matrix) */}
        <div className="table-read-body">
          {/* Teleprompter Script View */}
          <div className="teleprompter-pane">
            <div className="teleprompter-container">
              {segments.length > 0 ? (
                segments.map(
(seg,  idx) => {
                  const isActive = idx === currentIdx;
                  return (
                    <div
                      key={idx}
                      ref={isActive ? activeLineRef : null}
                      className={`teleprompter-line line-${seg.type} ${isActive ? 'active-reading' : ''}`}
                      onClick={() => {
                        setCurrentIdx(idx);
                        if (!isPlaying) setIsPlaying(true);
                      }}
                    >
                      {seg.type === 'dialogue' && (
                        <span className="speaker-tag">{seg.speaker}: </span>
                      )}
                      <span className="line-text">{seg.text}</span>
                      {isActive && isLoadingAudio && (
                        <span className="audio-loading-badge"> ⏳ generating voice...</span>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="teleprompter-empty">No script lines detected. Open a screenplay in Screenwriting Studio first.</div>
              )}
            </div>
          </div>

          {/* Voice Cast & Audio Settings Sidebar */}
          <div className="voice-cast-pane">
            <h3 className="cast-title">🎭 Character Voice Cast Matrix</h3>
            <p className="cast-subtitle">{characters.length + 1} Roles Configured • High-Quality Neural Voices</p>

            <div className="cast-list">
              {/* Narrator */}
              <div className="cast-card narrator-card">
                <div className="cast-card-top">
                  <span className="char-badge">📖 Narrator / Action</span>
                </div>
                <div className="cast-voice-select">
                  <label>Assigned Voice:</label>
                  <select
                    value={voiceMap['NARRATOR']?.voice || 'en-US-GuyNeural'}
                    onChange={e => {
                      const v = e.target.value;
                      setVoiceMap(prev => ({ ...prev, NARRATOR: { ...prev.NARRATOR, voice: v } }));
                    }}
                  >
                    {availableVoices.map( 
v => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                </div>
                <div className="cast-controls">
                  <label>Pitch Offset:</label>
                  <input
                    type="range"
                    min="-20"
                    max="20"
                    step="2"
                    value={voiceMap['NARRATOR']?.pitchHz || 0}
                    onChange={e => {
                      const hz = parseInt(e.target.value, 10);
                      setVoiceMap(prev => ({ ...prev, NARRATOR: { ...prev.NARRATOR, pitchHz: hz } }));
                    }}
                  />
                  <span>{voiceMap['NARRATOR']?.pitchHz || 0} Hz</span>
                </div>
              </div>

              {/* Characters List */}
              {characters.map(char => (
                <div key={char} className="cast-card">
                  <div className="cast-card-top">
                    <span className="char-badge">👤 {char}</span>
                  </div>
                  <div className="cast-voice-select">
                    <label>Assigned Voice:</label>
                    <select
                      value={voiceMap[char]?.voice || 'en-US-AriaNeural'}
                      onChange={e => {
                        const v = e.target.value;
                        setVoiceMap(prev => ({ ...prev, [char]: { ...prev[char], voice: v } }));
                      }}
                    >
                      {availableVoices.map( 
v => (
                        <option key={v.id} value={v.id}>{v.name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="cast-controls">
                    <label>Pitch Offset:</label>
                    <input
                      type="range"
                      min="-20"
                      max="20"
                      step="2"
                      value={voiceMap[char]?.pitchHz || 0}
                      onChange={e => {
                        const hz = parseInt(e.target.value, 10);
                        setVoiceMap(prev => ({ ...prev, [char]: { ...prev[char], pitchHz: hz } }));
                      }}
                    />
                    <span>{voiceMap[char]?.pitchHz || 0} Hz</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Playback Control Bar */}
        <div className="table-read-footer">
          <div className="playback-controls">
            <button className="ctrl-btn" onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}>
              ⏮️ Prev
            </button>
            <button className={`ctrl-btn play-btn ${isPlaying ? 'playing' : ''}`} onClick={togglePlay}>
              {isPlaying ? '⏸️ Pause Table Read' : '▶️ Start Table Read'}
            </button>
            <button className="ctrl-btn" onClick={handleStop}>
              ⏹️ Stop
            </button>
            <button className="ctrl-btn" onClick={() => setCurrentIdx(Math.min(segments.length - 1, currentIdx + 1))}>
              ⏭️ Next
            </button>
          </div>

          <div className="speed-controls">
            <span className="speed-label">Playback Speed:</span>
            {[0.8, 1.0, 1.2, 1.5].map(s => (
              <button
                key={s}
                className={`speed-pill ${speed === s ? 'active' : ''}`}
                onClick={() => setSpeed(s)}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="progress-info">
            Line {currentIdx + 1} of {Math.max(1, segments.length)} ({Math.round(((currentIdx + 1) / Math.max(1, segments.length)) * 100)}%)
          </div>
        </div>
      </div>
    </div>
  );
}
