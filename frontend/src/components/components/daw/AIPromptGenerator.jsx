import React, { useState } from 'react';
import { Sparkles, Loader, Bot, MessageSquare } from 'lucide-react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';

const AIPromptGenerator = () => {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const bpm = useDawStore(state => state.bpm);
  const isPlaying = useDawStore(state => state.isPlaying);
  const playMode = useDawStore(state => state.playMode);
  const activeView = useDawStore(state => state.activeView);
  const masterVolume = useDawStore(state => state.masterVolume);
  const generateAIBeat = useDawStore(state => state.generateAIBeat);
  const executeAssistantActions = useDawStore(state => state.executeAssistantActions);
  const addAssistantMessage = useDawStore(state => state.addAssistantMessage);
  const toggleAssistantDrawer = useDawStore(state => state.toggleAssistantDrawer);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || isGenerating) return;

    const currentPrompt = prompt.trim();
    setIsGenerating(true);

    // Add to assistant conversation history
    addAssistantMessage({
      role: 'user',
      content: currentPrompt
    });

    try {
      const res = await fetch('http://127.0.0.1:8080/api/audio/assistant/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: currentPrompt,
          context: { bpm, isPlaying, playMode, activeView, masterVolume }
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.actions && data.actions.length > 0) {
          executeAssistantActions(data.actions);
        } else {
          // Heuristic fallback genre check
          const p = currentPrompt.toLowerCase();
          let genre = 'trap';
          if (p.includes('synthwave') || p.includes('80s') || p.includes('retro')) genre = 'synthwave';
          else if (p.includes('lofi') || p.includes('chill')) genre = 'lofi';
          else if (p.includes('cyberpunk') || p.includes('dark')) genre = 'cyberpunk';
          generateAIBeat(genre);
        }

        addAssistantMessage({
          role: 'assistant',
          content: data.reply || "MIDI & groove pattern successfully composed and loaded onto your Channel Rack.",
          actions: data.actions || [],
          suggestions: data.suggestions || []
        });
      } else {
        // Local offline fallback
        const p = currentPrompt.toLowerCase();
        let genre = 'trap';
        if (p.includes('synthwave') || p.includes('80s') || p.includes('retro')) genre = 'synthwave';
        else if (p.includes('lofi') || p.includes('chill')) genre = 'lofi';
        generateAIBeat(genre);
      }
    } catch (err) {
      console.warn("AI Prompt Generator fallback:", err);
      generateAIBeat('trap');
    } finally {
      setIsGenerating(false);
      setPrompt('');
    }
  };

  return (
    <div style={{
      padding: '8px 12px',
      background: 'rgba(20, 24, 30, 0.6)',
      borderBottom: `1px solid ${theme.colors.border}`,
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }}>
      <Sparkles size={16} color="#a371f7" />
      <form onSubmit={handleGenerate} style={{ flex: 1, display: 'flex', gap: '8px' }}>
        <input 
          type="text"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Natural Language Music Producer (e.g. 'Set tempo to 128 and create a synthwave beat' or 'Chill lofi drums')..."
          style={{
            flex: 1,
            background: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '4px',
            color: '#c9d1d9',
            padding: '6px 12px',
            fontSize: '12px',
            outline: 'none',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.5)'
          }}
          disabled={isGenerating}
        />
        <button
          type="submit"
          disabled={isGenerating || !prompt.trim()}
          style={{
            background: isGenerating ? '#30363d' : 'linear-gradient(135deg, #8a2be2, #a371f7)',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            padding: '6px 14px',
            fontSize: '12px',
            fontWeight: 'bold',
            cursor: isGenerating || !prompt.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: isGenerating ? 'none' : '0 0 10px rgba(163, 113, 247, 0.3)'
          }}
        >
          {isGenerating ? <Loader size={14} className="spin" /> : 'Compose'}
        </button>

        <button
          type="button"
          onClick={toggleAssistantDrawer}
          style={{
            background: 'rgba(168, 85, 247, 0.15)',
            border: '1px solid rgba(168, 85, 247, 0.4)',
            color: '#d8b4fe',
            borderRadius: '4px',
            padding: '6px 10px',
            fontSize: '11px',
            fontWeight: 'bold',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}
          title="Open Full Assistant Chat Drawer"
        >
          <Bot size={13} />
          <span>Chat</span>
        </button>
      </form>
    </div>
  );
};

export default AIPromptGenerator;
