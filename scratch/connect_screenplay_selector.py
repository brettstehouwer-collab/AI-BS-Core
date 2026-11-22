import os

file_path = r"C:\AI-BS\frontend\src\components\NeuralAudioStudioTab.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Add savedScreenplays state
old_state = "  const [voiceStudioStatus, setVoiceStudioStatus] = useState('');"
new_state = """  const [voiceStudioStatus, setVoiceStudioStatus] = useState('');
  const [savedScreenplays, setSavedScreenplays] = useState([]);
  const [selectedScreenplayId, setSelectedScreenplayId] = useState('');"""

text = text.replace(old_state, new_state, 1)

# 2. Add fetchScreenplays in useEffect
old_use_effect = """  useEffect(() => {
    fetchProfiles();
  }, []);"""

new_use_effect = """  useEffect(() => {
    fetchProfiles();
    fetchSavedScreenplays();
  }, []);

  const fetchSavedScreenplays = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/audio/screenplays/list`);
      if (res.ok) {
        const json = await res.json();
        if (json.projects) {
          setSavedScreenplays(json.projects);
        }
      }
    } catch {}
  };

  const handleSelectScreenplay = async (projId) => {
    if (!projId) return;
    setSelectedScreenplayId(projId);
    setCreativeTitle(projId);
    try {
      const res = await fetch(`${baseUrl}/api/audio/screenplays/load?project_id=${encodeURIComponent(projId)}`);
      if (res.ok) {
        const json = await res.json();
        if (json.content) {
          setCreativeScript(json.content);
        }
      }
    } catch {}
  };"""

text = text.replace(old_use_effect, new_use_effect, 1)

# 3. Add Project Dropdown above creativeTitle input
old_input_area = """                <input
                  type="text"
                  value={creativeTitle}
                  onChange={e => setCreativeTitle(e.target.value)}
                  placeholder="Chapter or Screenplay Title...\""""

new_input_area = """                {/* Saved Screenplay Archive Selector */}
                {savedScreenplays.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '0.82rem', color: '#38bdf8', fontWeight: '700' }}>
                      📁 Load from Screenplay Vault ({savedScreenplays.length} projects):
                    </span>
                    <select
                      value={selectedScreenplayId}
                      onChange={e => handleSelectScreenplay(e.target.value)}
                      style={{
                        flex: 1,
                        backgroundColor: '#0b1120',
                        color: '#f0f6fc',
                        border: '1px solid rgba(56, 189, 248, 0.4)',
                        padding: '8px 12px',
                        borderRadius: '8px',
                        fontSize: '0.85rem',
                        outline: 'none',
                        cursor: 'pointer'
                      }}
                    >
                      <option value="">-- Choose Screenplay or Scene to Narrate --</option>
                      {savedScreenplays.map(proj => (
                        <option key={proj.id} value={proj.id}>
                          {proj.title}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <input
                  type="text"
                  value={creativeTitle}
                  onChange={e => setCreativeTitle(e.target.value)}
                  placeholder="Chapter or Screenplay Title...\""""

text = text.replace(old_input_area, new_input_area, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(text)

# Also sync mirror
mirror_path = r"C:\AI-BS\frontend\src\components\components\NeuralAudioStudioTab.jsx"
with open(mirror_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Screenplay archive selector successfully connected to Frontend!")

