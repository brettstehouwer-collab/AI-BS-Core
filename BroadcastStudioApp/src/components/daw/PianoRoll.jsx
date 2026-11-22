import React, { useState } from 'react';
import { theme } from '../../styles/theme';
import { useDawStore } from './dawStore';
import { AlignLeft, Music2, Trash2, Volume2, Mic, Radio, Zap, Sparkles } from 'lucide-react';
import AIPromptGenerator from './AIPromptGenerator';

const OCTAVES = ['5', '4', '3'];
const NOTE_NAMES = ['B', 'A#', 'A', 'G#', 'G', 'F#', 'F', 'E', 'D#', 'D', 'C#', 'C'];
const PIANO_KEYS = OCTAVES.flatMap(oct => NOTE_NAMES.map(n => `${n}${oct}`));

// Chord Interval Definitions
const CHORD_PRESETS = [
  { name: 'Major', intervals: [0, 4, 7] },
  { name: 'Minor', intervals: [0, 3, 7] },
  { name: 'Maj7', intervals: [0, 4, 7, 11] },
  { name: 'Min7', intervals: [0, 3, 7, 10] },
  { name: 'Dom7', intervals: [0, 4, 7, 10] },
  { name: 'Sus4', intervals: [0, 5, 7] },
];

const PianoRoll = () => {
  const activeChannelId = useDawStore(state => state.activeChannelId);
  const channels = useDawStore(state => state.channels);
  const currentStep = useDawStore(state => state.currentStep);
  const isPlaying = useDawStore(state => state.isPlaying);
  const stepCount = useDawStore(state => state.stepCount);
  const addOrToggleMidiNote = useDawStore(state => state.addOrToggleMidiNote);
  const previewNote = useDawStore(state => state.previewNote);
  const isMidiRecording = useDawStore(state => state.isMidiRecording);
  const toggleMidiRecording = useDawStore(state => state.toggleMidiRecording);

  const [selectedChord, setSelectedChord] = useState(null);
  const [selectedScale, setSelectedScale] = useState('All');

  const activeChannel = channels.find(c => c.id === activeChannelId) || channels[0];
  const midiNotes = activeChannel?.midiNotes || [];

  // Stamp a Chord at a given root note & step
  const stampChord = (rootKey, stepIdx) => {
    if (!selectedChord) {
      addOrToggleMidiNote(activeChannel.id, rootKey, stepIdx);
      return;
    }
    const rootIndex = PIANO_KEYS.indexOf(rootKey);
    if (rootIndex === -1) return;

    selectedChord.intervals.forEach(semitones => {
      // In PIANO_KEYS, lower index means higher octave (B5 is 0, C3 is last)
      const targetIdx = rootIndex - semitones;
      if (targetIdx >= 0 && targetIdx < PIANO_KEYS.length) {
        const chordNote = PIANO_KEYS[targetIdx];
        addOrToggleMidiNote(activeChannel.id, chordNote, stepIdx, 2);
      }
    });
  };

  return (
    <div style={{
      background: 'rgba(12, 15, 20, 0.98)',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      borderLeft: `1px solid ${theme.colors.border}`,
      borderRadius: '8px',
      overflow: 'hidden'
    }}>
      {/* Header Bar */}
      <div style={{
        padding: '8px 12px',
        borderBottom: `1px solid ${theme.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(20, 24, 30, 0.8)',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlignLeft size={16} color={theme.colors.secondary} />
          <h3 style={{ margin: 0, fontSize: '13px', color: '#fff', display: 'flex', alignItems: 'center', gap: '6px' }}>
            PIANO ROLL: <span style={{ color: activeChannel.color || theme.colors.accent }}>{activeChannel.name}</span>
          </h3>
        </div>

        {/* Hardware MIDI Controller Recording & Chord Tools */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {/* Live Web MIDI Input Toggle */}
          <button
            onClick={toggleMidiRecording}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              background: isMidiRecording ? '#ef4444' : 'rgba(255, 255, 255, 0.05)',
              color: isMidiRecording ? '#fff' : '#aaa',
              border: isMidiRecording ? '1px solid #dc2626' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '4px',
              padding: '3px 8px',
              fontSize: '10px',
              cursor: 'pointer',
              fontWeight: 'bold',
              animation: isMidiRecording ? 'pulse 1.5s infinite' : 'none'
            }}
            title="Connect & Record Hardware MIDI Keyboard"
          >
            <Radio size={12} /> {isMidiRecording ? 'REC MIDI ON' : 'MIDI In'}
          </button>

          {/* Chord Stamper Selector */}
          <div style={{ display: 'flex', gap: '2px', background: '#0a0d14', padding: '2px', borderRadius: '4px', border: '1px solid #30363d' }}>
            <button
              onClick={() => setSelectedChord(null)}
              style={{
                fontSize: '9px',
                background: selectedChord === null ? 'rgba(0, 240, 255, 0.2)' : 'transparent',
                color: selectedChord === null ? '#00f0ff' : '#666',
                border: 'none',
                borderRadius: '2px',
                padding: '2px 4px',
                cursor: 'pointer'
              }}
            >
              Single
            </button>
            {CHORD_PRESETS.map((c, ci) => (
              <button
                key={ci}
                onClick={() => setSelectedChord(selectedChord?.name === c.name ? null : c)}
                style={{
                  fontSize: '9px',
                  background: selectedChord?.name === c.name ? '#a855f7' : 'transparent',
                  color: selectedChord?.name === c.name ? '#fff' : '#888',
                  border: 'none',
                  borderRadius: '2px',
                  padding: '2px 4px',
                  cursor: 'pointer'
                }}
              >
                {c.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <AIPromptGenerator />

      {/* Piano Roll Body */}
      <div style={{ display: 'flex', flex: 1, overflowY: 'auto', overflowX: 'auto', position: 'relative' }}>
        
        {/* Left Side: Piano Keys */}
        <div style={{
          width: '56px',
          background: '#0d1117',
          display: 'flex',
          flexDirection: 'column',
          position: 'sticky',
          left: 0,
          zIndex: 5,
          borderRight: '1px solid #30363d'
        }}>
          {PIANO_KEYS.map(k => {
            const isBlack = k.includes('#');
            const isC = k.startsWith('C') && !isBlack;

            return (
              <div
                key={k}
                onClick={() => previewNote(activeChannel.id, k)}
                title={`Play ${k}`}
                style={{
                  height: '20px',
                  background: isBlack ? '#1a1f26' : '#e6edf3',
                  borderBottom: '1px solid rgba(0,0,0,0.4)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'flex-end',
                  paddingRight: '4px',
                  color: isBlack ? '#8b949e' : '#0d1117',
                  fontSize: '9px',
                  fontWeight: isC ? 'bold' : 'normal',
                  cursor: 'pointer',
                  userSelect: 'none',
                  borderLeft: isC ? `3px solid ${theme.colors.accent}` : 'none'
                }}
              >
                {isC ? k : isBlack ? '' : k.slice(0, 1)}
              </div>
            );
          })}
        </div>

        {/* Right Side: Step Note Grid */}
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          minWidth: `${stepCount * 28}px`,
          background: '#12161f'
        }}>
          {PIANO_KEYS.map(k => {
            const isBlack = k.includes('#');

            return (
              <div
                key={k}
                style={{
                  height: '20px',
                  display: 'flex',
                  background: isBlack ? 'rgba(0, 0, 0, 0.25)' : 'rgba(255, 255, 255, 0.02)',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                  position: 'relative'
                }}
              >
                {Array.from({ length: stepCount }).map((_, stepIdx) => {
                  const isBeat = stepIdx % 4 === 0;
                  const noteHere = midiNotes.find(n => n.note === k && n.step === stepIdx);

                  return (
                    <div
                      key={stepIdx}
                      onClick={() => stampChord(k, stepIdx)}
                      style={{
                        width: '28px',
                        height: '100%',
                        borderRight: isBeat ? '1px solid rgba(255, 255, 255, 0.15)' : '1px solid rgba(255, 255, 255, 0.03)',
                        cursor: 'crosshair',
                        position: 'relative',
                        background: noteHere ? 'transparent' : 'transparent'
                      }}
                    >
                      {/* Active MIDI Note Block */}
                      {noteHere && (
                        <div
                          style={{
                            position: 'absolute',
                            left: '1px',
                            top: '1px',
                            width: `${(noteHere.duration || 1) * 28 - 2}px`,
                            height: '17px',
                            background: activeChannel.color || theme.colors.accent,
                            borderRadius: '2px',
                            boxShadow: `0 0 8px ${activeChannel.color || theme.colors.accent}`,
                            display: 'flex',
                            alignItems: 'center',
                            paddingLeft: '4px',
                            fontSize: '9px',
                            color: '#000',
                            fontWeight: 'bold',
                            zIndex: 3,
                            overflow: 'hidden',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {k}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}

          {/* Animated Vertical Playhead */}
          {isPlaying && (
            <div
              style={{
                position: 'absolute',
                left: `${currentStep * 28}px`,
                top: 0,
                bottom: 0,
                width: '2px',
                background: '#fff',
                boxShadow: '0 0 8px #fff',
                zIndex: 10,
                pointerEvents: 'none',
                transition: 'left 0.05s linear'
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default PianoRoll;
