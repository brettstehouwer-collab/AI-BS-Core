import re

with open(r'C:\AI-BS\frontend\src\components\BroadcastStudio.jsx', 'r', encoding='utf-8') as f:
    web = f.read()

with open(r'C:\AI-BS\BroadcastStudioApp\src\App.jsx', 'r', encoding='utf-8') as f:
    app = f.read()

# 1. Extract Settings Modal
settings_modal_match = re.search(r'(\{/\* ========================================================================= \*/\}\s*\{/\* ?? FULL AUDIO & VIDEO SETTINGS & SOURCE SELECTOR MODAL.*?)(?=\{/\* ========================================================================= \*/\}\s*\{/\* ? ADD NEW SOURCE MODAL)', web, re.DOTALL)
settings_modal_jsx = settings_modal_match.group(1) if settings_modal_match else ""

# 2. Extract Add Source Modal
add_source_modal_match = re.search(r'(\{/\* ========================================================================= \*/\}\s*\{/\* ? ADD NEW SOURCE MODAL.*?)(?=</div\>\s*</div\>\s*\);\s*\}\;\s*export default)', web, re.DOTALL)
add_source_modal_jsx = add_source_modal_match.group(1) if add_source_modal_match else ""

# 3. Extract Functions
functions_match = re.search(r'(// Capture Screen Media.*?)(?=// Program Canvas Render Loop)', web, re.DOTALL)
functions_str = functions_match.group(1) if functions_match else ""

start_stream_match = re.search(r'(const startStream = async \(\) => \{.*?\};\s*const stopStream = async \(\) => \{.*?\};\s*const panicStop = async \(\) => \{.*?\};)', web, re.DOTALL)
stream_funcs = start_stream_match.group(1) if start_stream_match else ""

chat_func_match = re.search(r'(const handleSendChat = \(e\) => \{.*?\};)', web, re.DOTALL)
chat_func = chat_func_match.group(1) if chat_func_match else ""

add_source_func_match = re.search(r'(const handleAddSource = \(sourceType, customLabel, deviceId = ""\) => \{.*?\};\s*const handleEndpointChange = \(index, field, value\) => \{.*?\};)', web, re.DOTALL)
add_source_funcs = add_source_func_match.group(1) if add_source_func_match else ""

# State variables to add
missing_states = '''
  const [videoResolution, setVideoResolution] = useState('1920x1080');
  const [videoFramerate, setVideoFramerate] = useState('60');
  const [hardwareEncoder, setHardwareEncoder] = useState('h264_nvenc');
  const [audioSampleRate, setAudioSampleRate] = useState('48000');
  const [audioBufferSize, setAudioBufferSize] = useState('512');
  const [enableNoiseSuppression, setEnableNoiseSuppression] = useState(true);
  const [enableEchoCancellation, setEnableEchoCancellation] = useState(true);
  const [enableDawLoopback, setEnableDawLoopback] = useState(true);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState('video');
  const [selectedGameSource, setSelectedGameSource] = useState('Auto-Detect Foreground Window');
  const [customProcessName, setCustomProcessName] = useState('');
  const [videoDevices, setVideoDevices] = useState([]);
  const [audioInputDevices, setAudioInputDevices] = useState([]);
  const [audioOutputDevices, setAudioOutputDevices] = useState([]);
  const [selectedVideoDeviceId, setSelectedVideoDeviceId] = useState('');
  const [selectedAudioInputId, setSelectedAudioInputId] = useState('');
  const [selectedAudioOutputId, setSelectedAudioOutputId] = useState('');
'''

# 4. Inject into App.jsx
app = app.replace('const [autoDetectGame, setAutoDetectGame] = useState(false);', 'const [autoDetectGame, setAutoDetectGame] = useState(false);\n' + missing_states)

# inject functions right before factory
app = app.replace('const factory = (node) => {', chat_func + '\n\n' + add_source_funcs + '\n\n' + stream_funcs + '\n\n  const factory = (node) => {')

# inject modals after Layout
app = app.replace('<Layout model={model} factory={factory} />\n      </div>', '<Layout model={model} factory={factory} />\n      </div>\n' + settings_modal_jsx + '\n' + add_source_modal_jsx)

# Replace the "Settings" button in navbar to toggle modal
app = app.replace('<button \n            style={{ backgroundColor: \\\'var(--bg-darker)\\\', color: \\\'var(--text-main)\\\', border: \\\'1px solid var(--glass-border)\\\', padding: \\\'8px 16px\\\', borderRadius: \\\'4px\\\', cursor: \\\'pointer\\\' }}\n          >\n            Settings\n          </button>', 
'<button onClick={() => setShowSettingsModal(true)} style={{ backgroundColor: \\\'var(--bg-darker)\\\', color: \\\'var(--text-main)\\\', border: \\\'1px solid var(--glass-border)\\\', padding: \\\'8px 16px\\\', borderRadius: \\\'4px\\\', cursor: \\\'pointer\\\' }}>Settings</button>')

# Add VU meter useEffect
vu_meter_effect = '''
  useEffect(() => {
    const meterInterval = setInterval(() => {
      setAudioChannels(prev => prev.map(ch => {
        if (ch.mute) return { ...ch, peak: 0 };
        const jitter = (Math.random() - 0.5) * 15;
        const target = Math.max(10, Math.min(95, ch.volume + jitter));
        return { ...ch, peak: Math.round(target) };
      }));
    }, 120);
    return () => clearInterval(meterInterval);
  }, []);
'''

app = app.replace('const refreshMediaDevices = async () => {', vu_meter_effect + '\n  const refreshMediaDevices = async () => {')

# Add missing icons
app = app.replace('import { Monitor, List, Layers, Sliders, MessageSquare, Activity, Rss, Plus, Trash2, Eye, EyeOff, Settings, ExternalLink, ScreenShare, Video, Cpu } from \\\'lucide-react\\\';',
'import { Monitor, List, Layers, Sliders, MessageSquare, Activity, Rss, Plus, Trash2, Eye, EyeOff, Settings, ExternalLink, ScreenShare, Video, Cpu, SlidersHorizontal, X, ShieldCheck, Gamepad2, Mic } from \\\'lucide-react\\\';')

with open(r'C:\AI-BS\BroadcastStudioApp\src\App.jsx', 'w', encoding='utf-8') as f:
    f.write(app)

print("App.jsx has been updated with missing functions and modals.")
