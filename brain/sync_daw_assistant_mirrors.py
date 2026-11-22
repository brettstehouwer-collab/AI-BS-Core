import os
import hashlib
import shutil

src_daw_store = r"C:\AI-BS\frontend\src\components\daw\dawStore.js"
src_chat = r"C:\AI-BS\frontend\src\components\daw\MusicAssistantChat.jsx"

# 1. Patch dawStore.js
with open(src_daw_store, "r", encoding="utf-8") as f:
    daw_content = f.read()

# Enhance addStemTracksToPlaylist to avoid duplicate stem tracks
old_add_stem = """  // Add multi-track stems directly onto Arranger tracks
  addStemTracksToPlaylist: (stemsArray, projectName = 'Stems') => set(state => {
    const timestamp = Date.now();
    const newTracks = stemsArray.map((stem, idx) => ({"""

new_add_stem = """  // Add multi-track stems directly onto Arranger tracks
  addStemTracksToPlaylist: (stemsArray, projectName = 'Stems') => set(state => {
    const timestamp = Date.now();
    const baseTracks = state.playlistTracks.filter(t => !String(t.id).startsWith('stem_track_'));
    const newTracks = stemsArray.map((stem, idx) => ({"""

old_return = """    return {
      playlistTracks: [...state.playlistTracks, ...newTracks]
    };
  }),"""

new_return = """    return {
      playlistTracks: [...baseTracks, ...newTracks]
    };
  }),"""

if old_add_stem in daw_content:
    daw_content = daw_content.replace(old_add_stem, new_add_stem)
    daw_content = daw_content.replace(old_return, new_return)
    print("Patched addStemTracksToPlaylist in dawStore.js")
else:
    print("addStemTracksToPlaylist already patched or signature altered")

# Update initial assistant prompt suggestions in dawStore.js
old_suggestions = 'suggestions: ["⏱ Set Tempo to 85 BPM", "🥁 Compose Synthwave Beat", "✨ Open AI Stem Suite", "🎙️ Switch to Wave Studio"],'
new_suggestions = 'suggestions: ["🎼 Make Song With Assets", "⏱ Set Tempo to 85 BPM", "🥁 Compose Synthwave Beat", "✨ Open AI Stem Suite"],'
if old_suggestions in daw_content:
    daw_content = daw_content.replace(old_suggestions, new_suggestions)
    print("Updated initial suggestions in dawStore.js")

with open(src_daw_store, "w", encoding="utf-8") as f:
    f.write(daw_content)

# 2. Patch MusicAssistantChat.jsx
with open(src_chat, "r", encoding="utf-8") as f:
    chat_content = f.read()

old_quick = """  const quickPrompts = [
    { label: "🚀 Send to Studio", prompt: "Send my October 7v2 stems directly to the studio arranger" },"""

new_quick = """  const quickPrompts = [
    { label: "🎼 Make Song With Assets", prompt: "Make a song with what assets I have" },
    { label: "🚀 Send to Studio", prompt: "Send my October 7v2 stems directly to the studio arranger" },"""

if old_quick in chat_content:
    chat_content = chat_content.replace(old_quick, new_quick)
    print("Added 'Make Song With Assets' quick prompt chip in MusicAssistantChat.jsx")

with open(src_chat, "w", encoding="utf-8") as f:
    f.write(chat_content)

# 3. Synchronize across all 4 mirrors
mirrors_daw_store = [
    r"C:\AI-BS\frontend\src\components\daw\dawStore.js",
    r"C:\AI-BS\frontend\components\daw\dawStore.js",
    r"C:\AI-BS\frontend\src\components\components\daw\dawStore.js",
    r"C:\AI-BS\frontend\components\components\daw\dawStore.js"
]

mirrors_chat = [
    r"C:\AI-BS\frontend\src\components\daw\MusicAssistantChat.jsx",
    r"C:\AI-BS\frontend\components\daw\MusicAssistantChat.jsx",
    r"C:\AI-BS\frontend\src\components\components\daw\MusicAssistantChat.jsx",
    r"C:\AI-BS\frontend\components\components\daw\MusicAssistantChat.jsx"
]

for dst in mirrors_daw_store[1:]:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src_daw_store, dst)

for dst in mirrors_chat[1:]:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src_chat, dst)

# 4. Verify SHA-256 byte parity
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()

print("\n--- Parity Verification for dawStore.js ---")
base_hash = sha256(mirrors_daw_store[0])
for m in mirrors_daw_store:
    h = sha256(m)
    print(f"[{'PASS' if h == base_hash else 'FAIL'}] {h[:12]}... {m}")

print("\n--- Parity Verification for MusicAssistantChat.jsx ---")
base_hash_chat = sha256(mirrors_chat[0])
for m in mirrors_chat:
    h = sha256(m)
    print(f"[{'PASS' if h == base_hash_chat else 'FAIL'}] {h[:12]}... {m}")
