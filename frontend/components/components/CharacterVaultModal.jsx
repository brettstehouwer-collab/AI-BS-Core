import React, { useState, useEffect } from 'react';
import './ScreenwritingTab.css';

export default function CharacterVaultModal({ backendUrl, onClose, onCharactersUpdate }) {
  const [characters, setCharacters] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingChar, setEditingChar] = useState(null);

  // Form State
  const [name, setName] = useState('');
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
        body: JSON.stringify({ name, bio, speaking_style: speakingStyle })
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
    setBio('');
    setSpeakingStyle('');
  };

  const selectCharacter = (char) => {
    setEditingChar(char);
    setName(char.name || '');
    setBio(char.bio || '');
    setSpeakingStyle(char.speaking_style || '');
  };

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.85)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: '#111827', width: '800px', height: '600px', borderRadius: '12px', display: 'flex', overflow: 'hidden', border: '1px solid #374151', boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
        
        {/* Left List Pane */}
        <div style={{ width: '250px', background: '#1f2937', borderRight: '1px solid #374151', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #374151', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ color: '#fff', margin: 0, fontSize: '1rem' }}>🎭 Character Vault</h3>
            <button onClick={resetForm} style={{ background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '4px', width: '24px', height: '24px', cursor: 'pointer' }}>+</button>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
            {characters.map(c => (
              <div 
                key={c.name} 
                onClick={() => selectCharacter(c)}
                style={{ 
                  padding: '12px', 
                  background: editingChar?.name === c.name ? '#374151' : 'transparent',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  marginBottom: '4px',
                  color: '#e5e7eb',
                  display: 'flex',
                  justifyContent: 'space-between'
                }}
              >
                <span>{c.name}</span>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(c.name); }} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer' }}>x</button>
              </div>
            ))}
            {characters.length === 0 && <div style={{ color: '#6b7280', padding: '12px', textAlign: 'center' }}>No characters yet.</div>}
          </div>
        </div>

        {/* Right Editor Pane */}
        <div style={{ flex: 1, padding: '24px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'transparent', border: 'none', color: '#9ca3af', fontSize: '1.2rem', cursor: 'pointer' }}>✕</button>
          
          <h2 style={{ color: '#facc15', marginTop: 0, marginBottom: '24px' }}>
            {editingChar ? 'Edit Character' : 'New Character'}
          </h2>

          <label style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '4px' }}>Character Name</label>
          <input 
            type="text" 
            value={name} 
            onChange={e => setName(e.target.value)} 
            disabled={!!editingChar} // Prevent renaming for now as it's the ID
            className="sw-panel-input" 
            style={{ width: '100%', marginBottom: '16px', padding: '10px', fontSize: '1rem' }} 
            placeholder="e.g. JOHN DOE"
          />

          <label style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '4px' }}>Biography / Lore</label>
          <textarea 
            value={bio} 
            onChange={e => setBio(e.target.value)} 
            className="sw-panel-input" 
            style={{ width: '100%', flex: 1, marginBottom: '16px', padding: '10px', resize: 'none' }} 
            placeholder="Background story, goals, traits..."
          />

          <label style={{ color: '#9ca3af', fontSize: '0.85rem', marginBottom: '4px' }}>Speaking Style (for Ghostwriter AI)</label>
          <textarea 
            value={speakingStyle} 
            onChange={e => setSpeakingStyle(e.target.value)} 
            className="sw-panel-input" 
            style={{ width: '100%', height: '100px', marginBottom: '24px', padding: '10px', resize: 'none' }} 
            placeholder="E.g. Sarcastic, uses short sentences, stutters when nervous..."
          />

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            {editingChar && <button onClick={resetForm} style={{ padding: '8px 16px', background: 'transparent', color: '#fff', border: '1px solid #4b5563', borderRadius: '4px', cursor: 'pointer' }}>Cancel</button>}
            <button 
              onClick={handleSave} 
              disabled={isLoading || !name.trim()}
              style={{ padding: '8px 24px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
            >
              {isLoading ? 'Saving...' : 'Save Character'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
