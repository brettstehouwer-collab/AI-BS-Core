import os

input_file = r"C:\AI-BS\frontend\src\components\NeuralAudioStudioTab.jsx"
with open(input_file, "r", encoding="utf-8") as f:
    text = f.read()

target = """        {/* ══════════ 1. ZERO-SHOT VOICE CLONING (ELEVENLABS PARITY) ══════════ */}
        {activeTab === 'tts_zero_shot' && ("""

creative_section = """        {/* ══════════ 0. AUDIOBOOK & SCREENPLAY CREATIVE STUDIO (VOICESTUDIO INTEGRATED) ══════════ */}
        {activeTab === 'audiobook_screenplay' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '14px' }}>
              <div>
                <h2 style={{ margin: '0 0 4px 0', fontSize: '1.4rem', fontFamily: 'serif', color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  📖 Audiobook & Screenplay Creative Reader
                  <span style={{ fontSize: '0.75rem', color: '#10b981', border: '1px solid rgba(16,185,129,0.4)', padding: '2px 8px', borderRadius: '4px' }}>
                    VoiceStudio Local Engine Ready
                  </span>
                </h2>
                <p style={{ margin: 0, fontSize: '0.84rem', color: '#94a3b8' }}>
                  Synthesize complete audiobook chapters, script character dialogues, and multi-voice screenplay table reads powered by your local RTX 4090.
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <button
                  onClick={handleLaunchVoiceStudio}
                  disabled={isLaunchingVoiceStudio}
                  style={{
                    backgroundColor: '#1e293b',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.4)',
                    padding: '8px 16px',
                    borderRadius: '8px',
                    fontWeight: '700',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <ExternalLink size={15} />
                  {isLaunchingVoiceStudio ? 'Launching...' : 'Open VoiceStudio App (646 Langs)'}
                </button>
              </div>
            </div>

            {voiceStudioStatus && (
              <div style={{ padding: '8px 14px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.1)', border: '1px solid rgba(56, 189, 248, 0.3)', color: '#38bdf8', fontSize: '0.82rem' }}>
                ℹ️ {voiceStudioStatus}
              </div>
            )}

            {/* Mode Selector & Quick Presets */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => setCreativeMode('screenplay')}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  backgroundColor: creativeMode === 'screenplay' ? '#0284c7' : 'rgba(255,255,255,0.05)',
                  color: '#ffffff',
                  border: creativeMode === 'screenplay' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <Film size={15} /> Screenplay / Table Read
              </button>

              <button
                onClick={() => setCreativeMode('audiobook')}
                style={{
                  padding: '8px 18px',
                  borderRadius: '8px',
                  backgroundColor: creativeMode === 'audiobook' ? '#0284c7' : 'rgba(255,255,255,0.05)',
                  color: '#ffffff',
                  border: creativeMode === 'audiobook' ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.1)',
                  fontWeight: '700',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <BookOpen size={15} /> Audiobook Chapter Narration
              </button>

              <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginLeft: 'auto' }}>
                Preset: <strong>{creativeMode === 'screenplay' ? 'Dual-Voice Script' : 'Solo Narrator'}</strong>
              </span>
            </div>

            {/* Main Creative Input & Narrator Pick */}
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '20px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <input
                  type="text"
                  value={creativeTitle}
                  onChange={e => setCreativeTitle(e.target.value)}
                  placeholder="Chapter or Screenplay Title..."
                  style={{
                    backgroundColor: '#0b1120',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    color: '#ffffff',
                    fontWeight: '700',
                    fontSize: '0.95rem',
                    outline: 'none'
                  }}
                />

                <textarea
                  value={creativeScript}
                  onChange={e => setCreativeScript(e.target.value)}
                  rows={10}
                  placeholder="Paste your screenplay, character cues, or audiobook text here..."
                  style={{
                    backgroundColor: '#0b1120',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    borderRadius: '12px',
                    padding: '16px',
                    color: '#f0f6fc',
                    fontSize: '0.92rem',
                    fontFamily: 'monospace',
                    outline: 'none',
                    resize: 'vertical',
                    lineHeight: '1.6'
                  }}
                />

                <button
                  onClick={handleNarrateCreative}
                  disabled={isNarrating}
                  style={{
                    backgroundColor: isNarrating ? '#0284c7' : '#0284c7',
                    color: '#ffffff',
                    border: 'none',
                    padding: '14px 24px',
                    borderRadius: '10px',
                    fontWeight: '800',
                    fontSize: '1rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px',
                    boxShadow: '0 4px 16px rgba(2, 132, 199, 0.4)'
                  }}
                >
                  {isNarrating ? <RefreshCw className="animate-spin" size={18} /> : <Zap size={18} />}
                  {isNarrating ? 'Generating Voice Performance...' : `🎙️ Render Full ${creativeMode === 'screenplay' ? 'Screenplay Scene' : 'Audiobook Chapter'}`}
                </button>
              </div>

              {/* Narrator Profile Picker */}
              <div style={{ backgroundColor: '#0b1120', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '12px', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#38bdf8' }}>Lead Narrator Profile</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {profiles.map(p => (
                    <div
                      key={p.id}
                      onClick={() => setSelectedProfile(p.id)}
                      style={{
                        padding: '10px 12px',
                        borderRadius: '8px',
                        border: selectedProfile === p.id ? '1px solid #38bdf8' : '1px solid rgba(255,255,255,0.08)',
                        backgroundColor: selectedProfile === p.id ? 'rgba(14, 165, 233, 0.2)' : 'transparent',
                        cursor: 'pointer'
                      }}
                    >
                      <strong style={{ color: '#ffffff', fontSize: '0.88rem', display: 'block' }}>{p.name}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{p.gender} • {p.timbre.replace(/_/g, ' ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Rendered Narration Audio Player */}
            {creativeAudioResult && (
              <div style={{ backgroundColor: '#0f172a', border: '1px solid #10b981', borderRadius: '12px', padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ color: '#10b981', fontWeight: '800' }}>✓ Mastered Audio Rendered</span>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>({creativeAudioResult.duration_words} words)</span>
                  </div>
                  <a
                    href={creativeAudioResult.audio_data_url}
                    download={creativeAudioResult.filename}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      color: '#38bdf8',
                      textDecoration: 'none',
                      fontSize: '0.85rem',
                      fontWeight: '700'
                    }}
                  >
                    <Download size={14} /> Download WAV Master
                  </a>
                </div>

                <audio controls src={creativeAudioResult.audio_data_url} style={{ width: '100%', outline: 'none' }} />
              </div>
            )}
          </div>
        )}

""" + target

if target in text:
    new_text = text.replace(target, creative_section, 1)
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Injected successfully!")
else:
    print("Target not found!")

