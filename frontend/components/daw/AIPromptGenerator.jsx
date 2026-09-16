import React, { useState } from 'react';
import { Sparkles, Loader } from 'lucide-react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';

const AIPromptGenerator = () => {
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const activeChannelId = useDawStore(state => state.activeChannelId);
  const generateAIBeat = useDawStore(state => state.generateAIBeat);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setIsGenerating(true);
    
    // Simulate LLM Network Latency
    setTimeout(() => {
      // Mock basic LLM intent parsing
      const p = prompt.toLowerCase();
      let genre = 'trap';
      if (p.includes('synthwave') || p.includes('80s') || p.includes('retro')) {
        genre = 'synthwave';
      }
      
      generateAIBeat(genre);
      setIsGenerating(false);
      setPrompt('');
    }, 1500);
  };

  return (
    <div style={{
      padding: '8px 12px',
      background: 'rgba(20, 24, 30, 0.4)',
      borderBottom: `1px solid ${theme.colors.border}`,
      display: 'flex',
      alignItems: 'center',
      gap: '12px'
    }}>
      <Sparkles size={16} color="#a371f7" />
      <form onSubmit={handleGenerate} style={{ flex: 1, display: 'flex', gap: '8px' }}>
        <input 
          type="text"
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Prompt-to-MIDI (e.g. 'Generate a melancholic trap progression' or '80s synthwave bassline')..."
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
            padding: '6px 16px',
            fontSize: '12px',
            fontWeight: 'bold',
            cursor: isGenerating || !prompt.trim() ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            boxShadow: isGenerating ? 'none' : '0 0 10px rgba(163, 113, 247, 0.3)'
          }}
        >
          {isGenerating ? <Loader size={14} className="spin" /> : 'Compose MIDI'}
        </button>
      </form>
    </div>
  );
};

export default AIPromptGenerator;
