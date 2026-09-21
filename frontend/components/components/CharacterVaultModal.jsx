import React, { useState, useEffect } from 'react';
import './ScreenwritingTab.css';

export default function CharacterVaultModal({ backendUrl, onClose, onCharactersUpdate }) {
  const [characters, setCharacters] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingChar, setEditingChar] = useState(null);

  // Form State
  const [name, setName] = useState('');
  const [gender, setGender] = useState('Male');
  const [role, setRole] = useState('');
  const [voiceTag, setVoiceTag] = useState('');
  const [vocalTone, setVocalTone] = useState('');
  const [vocalPitch, setVocalPitch] = useState('');
  const [accent, setAccent] = useState('');
  const [personality, setPersonality] = useState('');
  const [bio, setBio] = useState('');
  const [speakingStyle, setSpeakingStyle] = useState('');

  const loadCharacters = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/projects/characters`);
      const data = await res.json();
      if (data.status === 'success') {
        setCharacters(data.characters || []);
        if (onCharactersUpdate) onCharactersUpdate(data.characters);
      }
    } catch (err) {
      console.error('Failed to load characters', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCharacters();
  }, []);

  const handleSave = async () => {
    if (!name.trim()) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/projects/characters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          name, 
          bio, 
          speaking_style: speakingStyle,
          gender,
          role,
          voice_tag: voiceTag,
          vocal_tone: vocalTone,
          vocal_pitch: vocalPitch,
          accent,
          personality
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setCharacters(data.characters);
        if (onCharactersUpdate) onCharactersUpdate(data.characters);
        resetForm();
      }
    } catch (err) {
      console.error('Failed to save character', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (charName) => {
    if (!window.confirm(`Delete character ${charName}?`)) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/screenwriting/projects/characters?name=${encodeURIComponent(charName)}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      if (data.status === 'success') {
        setCharacters(data.characters);
        if (onCharactersUpdate) onCharactersUpdate(data.characters);
        if (editingChar?.name === charName) resetForm();
      }
    } catch (err) {
      console.error('Failed to delete character', err);
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setEditingChar(null);
    setName('');
    setGender('Male');
    setRole('');
    setVoiceTag('');
    setVocalTone('');
    setVocalPitch('');
    setAccent('');
    setPersonality('');
    setBio('');
    setSpeakingStyle('');
  };

  const selectCharacter = (char) => {
    setEditingChar(char);
    setName(char.name || '');
    setGender(char.gender || 'Male');
    setRole(char.role || '');
    setVoiceTag(char.voice_tag || '');
    setVocalTone(char.vocal_tone || '');
    setVocalPitch(char.vocal_pitch || '');
    setAccent(char.accent || '');
    setPersonality(char.personality || '');
    setBio(char.bio || '');
    setSpeakingStyle(char.speaking_style || '');
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#111827', width: '960px', height: '720px', borderRadius: '12px', display: 'flex', overflow: 'hidden', border: '1px solid #374151', boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
        
        {/* Left List Pane */}
        <div style={{ width: '280px', background: '#1f2937', borderRight: '1px solid #374151', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #374151', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ color: '#fff', margin: 0, fontSize: '1rem' }}>🎭 Character Vault ({characters.length})</h3>
            <button onClick={resetForm} title="Add New Character" style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', width: '24px', height: '24px', cursor: 'pointer', fontWeight: 'bold' }}>+</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            {characters.map(c => (
              <div 
                key={c.name} 
                onClick={() => selectCharacter(c)}
                style={{ 
                  padding: '10px 12px', 
                  background: editingChar?.name === c.name ? '#374151' : 'transparent',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  marginBottom: '4px',
                  color: '#e5e7eb',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span style={{ marginRight: '6px', fontSize: '0.85rem' }}>{c.gender === 'Female' ? '👩' : '👨'}</span>
                  <strong style={{ fontSize: '0.95rem' }}>{c.name}</strong>
                  {c.role && <div style={{ fontSize: '0.75rem', color: '#9ca3af' }}>{c.role}</div>}
                  {c.vocal_pitch && <div style={{ fontSize: '0.7rem', color: '#38bdf8' }}>🎵 {c.vocal_pitch}</div>}
                </div>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(c.name); }} title="Delete Character" style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1rem', padding: '0 4px' }}>×</button>
              </div>
            ))}
            {characters.length === 0 && <div style={{ color: '#6b7280', padding: '12px', textAlign: 'center' }}>No characters found.</div>}
          </div>
        </div>

        {/* Right Editor Pane */}
        <div style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', position: 'relative', overflowY: 'auto' }}>
          <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: '#9ca3af', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
          
          <h2 style={{ color: '#facc15', marginTop: 0, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>{gender === 'Female' ? '👩' : '👨'}</span>
            {editingChar ? `Character Dossier: ${name}` : 'New Character Dossier'}
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Character Name</label>
              <input 
                type="text" 
                value={name} 
                onChange={e => setName(e.target.value)} 
                disabled={!!editingChar}
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.95rem' }} 
                placeholder="e.g. JACK"
              />
            </div>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Gender / Voice Profile</label>
              <select 
                value={gender} 
                onChange={e => setGender(e.target.value)} 
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.95rem' }}
              >
                <option value="Male">👨 Male</option>
                <option value="Female">👩 Female</option>
                <option value="Neutral">🎙️ Neutral / Voice-Over</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Role / Archetype</label>
              <input 
                type="text" 
                value={role} 
                onChange={e => setRole(e.target.value)} 
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.9rem' }} 
                placeholder="e.g. Syndicate Boss / Enforcer / Matriarch"
              />
            </div>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Suno v6 Voice Cue Tag</label>
              <input 
                type="text" 
                value={voiceTag} 
                onChange={e => setVoiceTag(e.target.value)} 
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.9rem' }} 
                placeholder="e.g. [Deep, commanding Mob Boss Male Voice]"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>🎵 Vocal Pitch (Soprano / Tenor / Baritone / Bass)</label>
              <input 
                type="text" 
                value={vocalPitch} 
                onChange={e => setVocalPitch(e.target.value)} 
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.9rem' }} 
                placeholder="e.g. Low-Medium Baritone / High Lyric Soprano"
              />
            </div>
            <div>
              <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>🗣️ Accent & Dialect Cadence</label>
              <input 
                type="text" 
                value={accent} 
                onChange={e => setAccent(e.target.value)} 
                className="sw-panel-input" 
                style={{ width: '100%', padding: '8px 10px', fontSize: '0.9rem' }} 
                placeholder="e.g. Midwestern American / Sicilian Immigrant / Aristocratic"
              />
            </div>
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>Vocal Acoustics & Delivery</label>
            <input 
              type="text" 
              value={vocalTone} 
              onChange={e => setVocalTone(e.target.value)} 
              className="sw-panel-input" 
              style={{ width: '100%', padding: '8px 10px', fontSize: '0.9rem' }} 
              placeholder="e.g. Gravelly baritone, commanding weight, slow deliberate cadence"
            />
          </div>

          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: '#9ca3af', fontSize: '0.85rem', display: 'block', marginBottom: '4px' }}>🧠 Personality Profile (Dialogue Insights & Psych Profile)</label>
            <textarea 
              value={personality} 
              onChange={e => setPersonality(e.target.value)} 
              className="sw-panel-input" 
              style={{ width: '100%', height: '70px', padding: '8px', resize: 'vertical' }} 
              placeholder="Psychological temperament, priorities, aggression vs affection, dialogue deductions..."
            />
          </div>

          <label style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '4px' }}>Biography, Physical Traits & Lore</label>
          <textarea 
            value={bio} 
            onChange={e => setBio(e.target.value)} 
            className="sw-panel-input" 
            style={{ width: '100%', height: '90px', marginBottom: '12px', padding: '8px', resize: 'vertical' }} 
            placeholder="Age, appearance, clothing, backstory, relationships..."
          />

          <label style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '4px' }}>Speaking Style (for Table Read & AI Ghostwriter)</label>
          <textarea 
            value={speakingStyle} 
            onChange={e => setSpeakingStyle(e.target.value)} 
            className="sw-panel-input" 
            style={{ width: '100%', height: '60px', marginBottom: '16px', padding: '8px', resize: 'vertical' }} 
            placeholder="Dialect, slang, vocabulary, sentence length, emotional rhythm..."
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: 'auto' }}>
            {editingChar && <button onClick={resetForm} style={{ padding: '8px 16px', background: 'transparent', color: '#fff', border: '1px solid #4b5563', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>}
            <button 
              onClick={handleSave} 
              disabled={isLoading || !name.trim()}
              style={{ padding: '8px 24px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              {isLoading ? 'Saving...' : 'Save Character Dossier'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
