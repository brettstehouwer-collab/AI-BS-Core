import os
import hashlib
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

src_daw = r"C:\AI-BS\frontend\src\components\daw\dawStore.js"
src_rack = r"C:\AI-BS\frontend\src\components\daw\ChannelRack.jsx"
src_chat = r"C:\AI-BS\frontend\src\components\daw\MusicAssistantChat.jsx"

# 1. Patch dawStore.js
with open(src_daw, "r", encoding="utf-8") as f:
    daw_content = f.read()

old_generate_beat = """  // AI Beat Assistant Preset Generator
  generateAIBeat: (genre = 'trap') => {
    set(state => {
      const g = (genre || 'trap').toLowerCase();
      if (g.includes('trap') || g.includes('drill')) {"""

new_generate_beat = """  // AI Beat Assistant Preset Generator (Supports Clean Random Grooves - Zero Cyberpunk)
  generateAIBeat: (genre = 'random') => {
    set(state => {
      let g = (genre || 'random').toLowerCase();
      const cleanPool = ['suno_rock', 'boombap', 'lofi', 'rnb', 'funk_pop', 'acoustic_ballad', 'melodic_trap', 'synthwave'];
      if (g.includes('random') || g === 'shuffle' || g === 'roll') {
        const randIdx = Math.floor(Math.random() * cleanPool.length);
        g = cleanPool[randIdx];
      }

      if (g.includes('boombap') || g.includes('hiphop') || g.includes('hip hop')) {
        // 90s Boom-Bap (90 BPM) - Punchy kick, snappy acoustic snare, swinging hats
        return {
          bpm: 90,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, false, false, true, false, false, true, false, false, false, false, false, false] };
            if (ch.type === 'snare' || ch.type === 'clap') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [true, false, true, true, true, false, true, true, true, false, true, true, true, false, true, true] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'G1', duration: 2 }, { step: 6, note: 'Bb1', duration: 2 }, { step: 9, note: 'C2', duration: 2 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 0, note: 'G3', duration: 4 }, { step: 8, note: 'F3', duration: 4 }] };
            return ch;
          })
        };
      } else if (g.includes('rnb') || g.includes('soul')) {
        // Smooth R&B Soul (78 BPM) - Laid-back kick, emotional progression
        return {
          bpm: 78,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, false, false, false, true, false, false, true, false, false, false, false, false] };
            if (ch.type === 'snare' || ch.type === 'clap') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [true, true, false, true, true, true, false, true, true, true, false, true, true, true, false, true] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'Eb1', duration: 3 }, { step: 7, note: 'Ab1', duration: 3 }, { step: 12, note: 'Bb1', duration: 2 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 0, note: 'Eb3', duration: 4 }, { step: 6, note: 'G3', duration: 4 }, { step: 12, note: 'Bb3', duration: 4 }] };
            return ch;
          })
        };
      } else if (g.includes('funk') || g.includes('pop')) {
        // Upbeat Funk-Pop (108 BPM) - Energetic syncopation
        return {
          bpm: 108,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, true, false, false, true, false, false, true, false, false, false, true, false] };
            if (ch.type === 'snare' || ch.type === 'clap') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [true, false, true, false, true, false, true, false, true, false, true, false, true, false, true, false] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'E1', duration: 1 }, { step: 3, note: 'G1', duration: 1 }, { step: 7, note: 'A1', duration: 1 }, { step: 10, note: 'D2', duration: 1 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 4, note: 'E3', duration: 2 }, { step: 12, note: 'G3', duration: 2 }] };
            return ch;
          })
        };
      } else if (g.includes('acoustic') || g.includes('ballad')) {
        // Organic Acoustic Ballad (76 BPM) - Natural pulse, resonant acoustic piano
        return {
          bpm: 76,
          channels: state.channels.map(ch => {
            if (ch.type === 'kick') return { ...ch, steps: [true, false, false, false, false, false, false, false, true, false, false, false, false, false, false, false] };
            if (ch.type === 'snare' || ch.type === 'clap') return { ...ch, steps: [false, false, false, false, true, false, false, false, false, false, false, false, true, false, false, false] };
            if (ch.type === 'hihat') return { ...ch, steps: [true, false, true, false, true, false, true, false, true, false, true, false, true, false, true, false] };
            if (ch.type === 'bass') return { ...ch, midiNotes: [{ step: 0, note: 'C2', duration: 4 }, { step: 8, note: 'G1', duration: 4 }] };
            if (ch.type === 'lead') return { ...ch, midiNotes: [{ step: 0, note: 'E3', duration: 4 }, { step: 8, note: 'D3', duration: 4 }] };
            return ch;
          })
        };
      } else if (g.includes('trap') || g.includes('drill')) {"""

if old_generate_beat in daw_content:
    daw_content = daw_content.replace(old_generate_beat, new_generate_beat)
    print("Patched generateAIBeat in dawStore.js")
else:
    print("generateAIBeat already updated in dawStore.js")

with open(src_daw, "w", encoding="utf-8") as f:
    f.write(daw_content)

# 2. Patch ChannelRack.jsx
with open(src_rack, "r", encoding="utf-8") as f:
    rack_content = f.read()

old_rack_btns = """        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button
            onClick={() => generateAIBeat('trap')}"""

new_rack_btns = """        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button
            onClick={() => generateAIBeat('random')}
            title="Roll a Clean Random Beat (Organic, Rock, Boom-Bap, R&B, Lo-Fi - Zero Cyberpunk)"
            style={{
              background: 'rgba(255, 193, 7, 0.15)',
              border: '1px solid #ffc107',
              borderRadius: '4px',
              color: '#ffc107',
              padding: '3px 8px',
              fontSize: '11px',
              fontWeight: 'bold',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <Sparkles size={11} /> 🎲 Random Beat
          </button>

          <button
            onClick={() => generateAIBeat('trap')}"""

if old_rack_btns in rack_content:
    rack_content = rack_content.replace(old_rack_btns, new_rack_btns)
    print("Added '🎲 Random Beat' button to ChannelRack.jsx")
else:
    print("ChannelRack.jsx already has random button")

with open(src_rack, "w", encoding="utf-8") as f:
    f.write(rack_content)

# 3. Patch MusicAssistantChat.jsx
with open(src_chat, "r", encoding="utf-8") as f:
    chat_content = f.read()

old_chat_prompts = """  const quickPrompts = [
    { label: "🎼 Make Song With Assets", prompt: "Make a song with what assets I have" },"""

new_chat_prompts = """  const quickPrompts = [
    { label: "🎼 Make Song With Assets", prompt: "Make a song with what assets I have" },
    { label: "🎲 Random Clean Beat", prompt: "Randomize a beat, none of that cyberpunk stuff" },"""

if old_chat_prompts in chat_content:
    chat_content = chat_content.replace(old_chat_prompts, new_chat_prompts)
    print("Added '🎲 Random Clean Beat' chip in MusicAssistantChat.jsx")

with open(src_chat, "w", encoding="utf-8") as f:
    f.write(chat_content)

# 4. Multi-Mirror Sync
files_to_sync = [
    (src_daw, [
        r"C:\AI-BS\frontend\components\daw\dawStore.js",
        r"C:\AI-BS\frontend\src\components\components\daw\dawStore.js",
        r"C:\AI-BS\frontend\components\components\daw\dawStore.js"
    ]),
    (src_rack, [
        r"C:\AI-BS\frontend\components\daw\ChannelRack.jsx",
        r"C:\AI-BS\frontend\src\components\components\daw\ChannelRack.jsx",
        r"C:\AI-BS\frontend\components\components\daw\ChannelRack.jsx"
    ]),
    (src_chat, [
        r"C:\AI-BS\frontend\components\daw\MusicAssistantChat.jsx",
        r"C:\AI-BS\frontend\src\components\components\daw\MusicAssistantChat.jsx",
        r"C:\AI-BS\frontend\components\components\daw\MusicAssistantChat.jsx"
    ])
]

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

print("\n--- Synchronizing All 4 Mirrors ---")
for src, mirrors in files_to_sync:
    base_h = sha256(src)
    for dst in mirrors:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        h = sha256(dst)
        assert h == base_h, f"Parity mismatch on {dst}"
    print(f"[PASS] 100% SHA256 parity: {os.path.basename(src)}")
