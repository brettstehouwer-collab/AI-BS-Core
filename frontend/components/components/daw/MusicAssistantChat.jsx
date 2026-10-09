import React, { useState, useRef, useEffect } from 'react';
import { 
  Sparkles, Send, Mic, MicOff, Volume2, VolumeX, Trash2, 
  Play, Square, Sliders, Music, Zap, Bot, User, CheckCircle2,
  Clock, ArrowRight, RefreshCw, X
} from 'lucide-react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';

export const MusicAssistantChat = ({ drawerMode = false, onClose = null }) => {
  const bpm = useDawStore(state => state.bpm);
  const isPlaying = useDawStore(state => state.isPlaying);
  const playMode = useDawStore(state => state.playMode);
  const masterVolume = useDawStore(state => state.masterVolume);
  const activeView = useDawStore(state => state.activeView);
  const assistantHistory = useDawStore(state => state.assistantHistory);
  const addAssistantMessage = useDawStore(state => state.addAssistantMessage);
  const clearAssistantHistory = useDawStore(state => state.clearAssistantHistory);
  const executeAssistantActions = useDawStore(state => state.executeAssistantActions);

  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [voiceSpeechEnabled, setVoiceSpeechEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [engineInfo, setEngineInfo] = useState('Ollama (RTX 4090)');
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [assistantHistory, isLoading]);

  // Speech Recognition (Web Speech API)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInputMessage(transcript);
          sendMessage(transcript);
        }
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const toggleMic = () => {
    if (!recognitionRef.current) {
      alert("Microphone speech recognition is not supported in this browser. Please use text input.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setIsListening(true);
      recognitionRef.current.start();
    }
  };

  // Text to Speech
  const speakResponse = (text) => {
    if (!voiceSpeechEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      // Strip markdown asterisks and emojis for speech
      const cleanText = text.replace(/[*_#`~]/g, '').replace(/[\u{1F600}-\u{1F6FF}]/gu, '');
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("TTS Error:", e);
    }
  };

  const sendMessage = async (customText = null) => {
    const textToSend = (customText !== null ? customText : inputMessage).trim();
    if (!textToSend || isLoading) return;

    // 1. Add User Message to History
    addAssistantMessage({
      role: 'user',
      content: textToSend
    });
    setInputMessage('');
    setIsLoading(true);

    const dawContext = {
      bpm,
      isPlaying,
      playMode,
      masterVolume,
      activeView
    };

    try {
      const res = await fetch('http://127.0.0.1:8080/api/audio/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: textToSend,
          history: assistantHistory.slice(-6).map(h => ({ role: h.role, content: h.content })),
          context: dawContext
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      const reply = data.reply || "I've processed your musical request.";
      const actions = data.actions || [];
      const suggestions = data.suggestions || ["⏱ 85 BPM Suno", "🥁 Synthwave Beat", "🎚 Open Mixer"];

      if (data.engine) {
        setEngineInfo(data.engine);
      }

      // Automatically execute actions on the live DAW!
      if (actions.length > 0) {
        executeAssistantActions(actions);
      }

      // Add Assistant Message to History
      addAssistantMessage({
        role: 'assistant',
        content: reply,
        actions,
        suggestions,
        engine: data.engine
      });

      // Speak if voice mode is enabled
      speakResponse(reply);

    } catch (err) {
      console.warn("Music Assistant API Error:", err);
      // Fallback message
      addAssistantMessage({
        role: 'assistant',
        content: `⚠️ Could not reach local chat engine: ${err.message}. Make sure AI-BS backend is active on Port 8080.`,
        suggestions: ["⏱ Set Tempo to 85 BPM", "🥁 Generate Trap Groove"]
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickPrompts = [
    { label: "🎼 Make Song With Assets", prompt: "Make a song with what assets I have" },
    { label: "🎲 Random Clean Beat", prompt: "Randomize a beat, none of that cyberpunk stuff" },
    { label: "🚀 Send to Studio", prompt: "Send my October 7v2 stems directly to the studio arranger" },
    { label: "⏱ Lock 85 BPM", prompt: "Set tempo to 85 BPM for Suno October 7v2 timing" },
    { label: "🥁 Synthwave Groove", prompt: "Generate an 80s synthwave beat with driving bassline and chords" },
    { label: "🔥 Dark Trap Beat", prompt: "Generate a dark trap beat with 808 sub-bass and rolling hi-hats" },
    { label: "☕ Lo-Fi Hip Hop", prompt: "Create a chill lo-fi hip hop beat with swing boom-bap rhythm" },
    { label: "✨ Isolate Stems", prompt: "Open the AI Stem Extractor and separate vocals from drums" },
    { label: "🎙️ Wave Studio", prompt: "Switch to Stehouwer Multi-Track Wave Studio" },
    { label: "🛠️ Fix Vocal Cut", prompt: "How do I smooth out a cut in a song where instruments and vocals were removed?" }
  ];

  const renderFormattedContent = (content) => {
    if (!content) return null;
    const lines = content.split('\n');
    const tokenRegex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;

    return lines.map((line, lIdx) => {
      const splitArr = line.split(tokenRegex);
      return (
        <div key={lIdx} style={{ minHeight: line.trim() ? 'auto' : '6px', marginBottom: '2px' }}>
          {splitArr.map((part, pIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <strong key={pIdx} style={{ color: '#fff', fontWeight: 'bold' }}>{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith('*') && part.endsWith('*')) {
              return <em key={pIdx} style={{ color: '#00f0ff', fontStyle: 'italic' }}>{part.slice(1, -1)}</em>;
            }
            if (part.startsWith('`') && part.endsWith('`')) {
              return <code key={pIdx} style={{ background: '#000', padding: '1px 5px', borderRadius: '3px', color: '#5eff7b', fontFamily: 'monospace', fontSize: '11px' }}>{part.slice(1, -1)}</code>;
            }
            return <span key={pIdx}>{part}</span>;
          })}
        </div>
      );
    });
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      width: '100%',
      background: '#090c10',
      color: '#c9d1d9',
      borderLeft: drawerMode ? '1px solid #30363d' : 'none',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* HEADER BAR */}
      <div style={{
        padding: '12px 16px',
        background: 'rgba(13, 17, 23, 0.95)',
        borderBottom: '1px solid #21262d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #a855f7, #00f0ff)',
            borderRadius: '6px',
            padding: '5px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 10px rgba(168, 85, 247, 0.4)'
          }}>
            <Bot size={18} color="#000" />
          </div>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
              AI Music Audio Assistant
              <span style={{ fontSize: '9px', background: 'rgba(168, 85, 247, 0.25)', color: '#c084fc', border: '1px solid #a855f7', padding: '1px 5px', borderRadius: '3px' }}>
                LOCAL LLM
              </span>
            </div>
            <div style={{ fontSize: '10px', color: '#8b949e' }}>
              Engine: <span style={{ color: '#58a6ff' }}>{engineInfo}</span> • GPU: <span style={{ color: '#5eff7b' }}>RTX 4090</span>
            </div>
          </div>
        </div>

        {/* Live DAW Telemetry Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: '#000',
          padding: '3px 8px',
          borderRadius: '4px',
          border: '1px solid #30363d',
          fontSize: '10px',
          fontFamily: 'monospace'
        }}>
          <span style={{ color: '#888' }}>BPM:</span>
          <b style={{ color: '#00f0ff' }}>{bpm}</b>
          <span style={{ color: '#30363d' }}>|</span>
          <span style={{ color: isPlaying ? '#5eff7b' : '#888' }}>{isPlaying ? '▶ PLAYING' : '⏹ STOPPED'}</span>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* TTS Voice Toggle */}
          <button
            onClick={() => setVoiceSpeechEnabled(prev => !prev)}
            title={voiceSpeechEnabled ? "Disable AI voice speech feedback" : "Enable AI voice speech feedback"}
            style={{
              background: voiceSpeechEnabled ? 'rgba(168, 85, 247, 0.25)' : 'rgba(255,255,255,0.06)',
              border: voiceSpeechEnabled ? '1px solid #a855f7' : '1px solid rgba(255,255,255,0.1)',
              color: voiceSpeechEnabled ? '#c084fc' : '#888',
              borderRadius: '4px',
              padding: '5px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px'
            }}
          >
            {voiceSpeechEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
            <span style={{ fontSize: '10px' }}>{voiceSpeechEnabled ? 'Voice ON' : 'Voice'}</span>
          </button>

          {/* Clear History */}
          <button
            onClick={clearAssistantHistory}
            title="Clear Chat History"
            style={{
              background: 'transparent',
              border: 'none',
              color: '#8b949e',
              cursor: 'pointer',
              padding: '5px'
            }}
          >
            <Trash2 size={14} />
          </button>

          {/* Close button if in drawer mode */}
          {drawerMode && onClose && (
            <button
              onClick={onClose}
              title="Close Assistant Drawer"
              style={{
                background: 'transparent',
                border: 'none',
                color: '#8b949e',
                cursor: 'pointer',
                padding: '5px'
              }}
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* QUICK ACTION PROMPT CHIPS */}
      <div style={{
        padding: '8px 12px',
        background: '#0d1117',
        borderBottom: '1px solid #21262d',
        display: 'flex',
        gap: '6px',
        overflowX: 'auto',
        whiteSpace: 'nowrap'
      }}>
        {quickPrompts.map((qp, idx) => (
          <button
            key={idx}
            onClick={() => sendMessage(qp.prompt)}
            style={{
              background: 'rgba(255, 255, 255, 0.04)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#c9d1d9',
              borderRadius: '12px',
              padding: '3px 10px',
              fontSize: '10px',
              fontWeight: '500',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              transition: 'all 0.15s ease'
            }}
            onMouseOver={(e) => { e.currentTarget.style.borderColor = '#a855f7'; e.currentTarget.style.color = '#fff'; }}
            onMouseOut={(e) => { e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'; e.currentTarget.style.color = '#c9d1d9'; }}
          >
            {qp.label}
          </button>
        ))}
      </div>

      {/* CHAT MESSAGES STREAM */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px'
      }}>
        {assistantHistory.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              style={{
                display: 'flex',
                gap: '10px',
                alignItems: 'flex-start',
                flexDirection: isUser ? 'row-reverse' : 'row'
              }}
            >
              {/* Avatar */}
              <div style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: isUser ? '#1f6feb' : 'linear-gradient(135deg, #a855f7, #00f0ff)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                boxShadow: isUser ? 'none' : '0 0 8px rgba(168, 85, 247, 0.3)'
              }}>
                {isUser ? <User size={15} color="#fff" /> : <Bot size={15} color="#000" />}
              </div>

              {/* Message Bubble */}
              <div style={{
                maxWidth: '85%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start'
              }}>
                <div style={{
                  background: isUser ? 'linear-gradient(135deg, #1f6feb, #1158c7)' : 'rgba(22, 27, 34, 0.95)',
                  border: isUser ? '1px solid #388bfd' : '1px solid #30363d',
                  borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
                  padding: '10px 14px',
                  color: '#fff',
                  fontSize: '12px',
                  lineHeight: '1.5',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {renderFormattedContent(msg.content)}
                </div>

                {/* Dispatched Actions Badges */}
                {msg.actions && msg.actions.length > 0 && (
                  <div style={{
                    marginTop: '6px',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '4px'
                  }}>
                    {msg.actions.map((act, actIdx) => (
                      <div
                        key={actIdx}
                        style={{
                          background: 'rgba(94, 255, 123, 0.12)',
                          border: '1px solid #5eff7b',
                          color: '#5eff7b',
                          borderRadius: '4px',
                          padding: '2px 8px',
                          fontSize: '10px',
                          fontWeight: 'bold',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '4px'
                        }}
                      >
                        <CheckCircle2 size={11} />
                        {act.type === 'SET_BPM' && `Locked ${act.bpm} BPM`}
                        {act.type === 'TOGGLE_PLAY' && `Playback Started`}
                        {act.type === 'STOP_PLAYBACK' && `Playback Stopped`}
                        {act.type === 'SET_VIEW' && `Opened ${act.view.toUpperCase()}`}
                        {act.type === 'SEND_TO_STUDIO' && `Dispatched Stems to Studio Arranger`}
                        {act.type === 'LOAD_TO_STUDIO' && `Loaded Tracks into Studio`}
                        {act.type === 'GENERATE_BEAT' && `Beat Programmed (${act.genre.toUpperCase()})`}
                        {act.type === 'SET_VOLUME' && `Volume Set: ${act.volume}dB`}
                        {act.type === 'SET_FX' && `FX Enhanced (${act.fx})`}
                        {act.type === 'MUTE_CHANNEL' && `Channel Muted`}
                      </div>
                    ))}
                  </div>
                )}

                {/* Followup Suggestions */}
                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div style={{
                    marginTop: '8px',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '6px'
                  }}>
                    {msg.suggestions.map((sug, sugIdx) => (
                      <button
                        key={sugIdx}
                        onClick={() => sendMessage(sug)}
                        style={{
                          background: 'rgba(168, 85, 247, 0.1)',
                          border: '1px solid rgba(168, 85, 247, 0.4)',
                          color: '#d8b4fe',
                          borderRadius: '10px',
                          padding: '2px 8px',
                          fontSize: '10px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px'
                        }}
                      >
                        <ArrowRight size={10} />
                        {sug}
                      </button>
                    ))}
                  </div>
                )}

                {/* Timestamp */}
                <span style={{ fontSize: '9px', color: '#6e7681', marginTop: '3px' }}>
                  {msg.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {/* Loading Indicator */}
        {isLoading && (
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #a855f7, #00f0ff)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 8px rgba(168, 85, 247, 0.3)'
            }}>
              <RefreshCw size={14} color="#000" className="spin" />
            </div>
            <div style={{
              background: 'rgba(22, 27, 34, 0.8)',
              border: '1px solid #30363d',
              borderRadius: '12px',
              padding: '8px 14px',
              color: '#8b949e',
              fontSize: '11px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span className="spin">⚡</span> Analyzing musical request with local engine...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* INPUT CONTROL BAR */}
      <div style={{
        padding: '12px 16px',
        background: '#0d1117',
        borderTop: '1px solid #21262d',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {/* Microphone Speech-To-Text Button */}
          <button
            onClick={toggleMic}
            title={isListening ? "Listening... click to stop" : "Speak to Assistant with Microphone"}
            style={{
              background: isListening ? '#f85149' : 'rgba(255, 255, 255, 0.08)',
              border: isListening ? '1px solid #ff7b72' : '1px solid rgba(255, 255, 255, 0.15)',
              color: '#fff',
              borderRadius: '6px',
              padding: '8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: isListening ? '0 0 10px rgba(248, 81, 73, 0.5)' : 'none'
            }}
          >
            {isListening ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          {/* Text Input */}
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? "Listening to your voice..." : "Tell me what to compose or adjust in natural language..."}
            disabled={isLoading}
            style={{
              flex: 1,
              background: '#07090e',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#fff',
              padding: '8px 12px',
              fontSize: '12px',
              outline: 'none',
              boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)'
            }}
          />

          {/* Send Button */}
          <button
            onClick={() => sendMessage()}
            disabled={isLoading || !inputMessage.trim()}
            style={{
              background: (!inputMessage.trim() || isLoading)
                ? '#21262d' 
                : 'linear-gradient(135deg, #a855f7, #7c3aed)',
              border: 'none',
              borderRadius: '6px',
              padding: '8px 16px',
              color: '#fff',
              fontSize: '12px',
              fontWeight: 'bold',
              cursor: (!inputMessage.trim() || isLoading) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: (!inputMessage.trim() || isLoading) ? 'none' : '0 0 10px rgba(168, 85, 247, 0.4)'
            }}
          >
            <Send size={14} />
            <span>Send</span>
          </button>
        </div>

        <div style={{ fontSize: '10px', color: '#6e7681', textAlign: 'center' }}>
          Natural language commands execute live in the DAW • Zero cloud fees • 100% Private local processing
        </div>
      </div>
    </div>
  );
};

export default MusicAssistantChat;
