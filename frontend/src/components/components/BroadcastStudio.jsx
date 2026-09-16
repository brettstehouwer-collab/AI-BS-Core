import React, { useState, useEffect, useRef } from 'react';
import { Layout, Model } from 'flexlayout-react';
import 'flexlayout-react/style/dark.css';
import { 
  Monitor, Layers, Sliders, MessageSquare, Activity, Settings, 
  Video, VideoOff, ScreenShare, Mic, MicOff, Play, Square, 
  Volume2, VolumeX, Eye, EyeOff, Plus, Trash2, Globe, ExternalLink,
  RefreshCw, CheckCircle, AlertCircle, Gamepad2, Cpu, Music,
  Maximize2, X, SlidersHorizontal, Check, ShieldCheck, Radio,
  Smartphone, Camera, Bot, Sparkles, Key, Send, Hash, ShieldAlert,
  BookOpen, HelpCircle, Info, ChevronRight, Zap, ChevronUp, ChevronDown
} from 'lucide-react';

const layoutConfig = {
  global: {
    tabEnableClose: false,
    tabEnableRename: false,
    tabSetEnableMaximize: true,
    splitterSize: 6,
    tabSetTabStripHeight: 35,
  },
  borders: [],
  layout: {
    type: "row",
    weight: 100,
    children: [
      {
        type: "row",
        weight: 50,
        children: [
          {
            type: "tabset",
            weight: 60,
            children: [{ type: "tab", name: "Preview / Program", component: "canvas" }]
          },
          {
            type: "tabset",
            weight: 40,
            children: [{ type: "tab", name: "Cloud Dashboard", component: "webdock" }]
          }
        ]
      },
      {
        type: "row",
        weight: 30,
        children: [
          {
            type: "tabset",
            weight: 22,
            children: [{ type: "tab", name: "Scenes", component: "scenes" }]
          },
          {
            type: "tabset",
            weight: 28,
            children: [{ type: "tab", name: "Sources", component: "sources" }]
          },
          {
            type: "tabset",
            weight: 50,
            children: [{ type: "tab", name: "Advanced Audio Mixer", component: "mixer" }]
          }
        ]
      },
      {
        type: "row",
        weight: 20,
        children: [
          {
            type: "tabset",
            weight: 30,
            children: [{ type: "tab", name: "Stream Settings", component: "settings" }]
          },
          {
            type: "tabset",
            weight: 45,
            children: [{ type: "tab", name: "Unified Chat & Sidekick", component: "chat" }]
          },
          {
            type: "tabset",
            weight: 25,
            children: [{ type: "tab", name: "Performance Stats", component: "stats" }]
          }
        ]
      }
    ]
  }
};

const DEFAULT_GAMES = [
  'Auto-Detect Foreground Window',
  'Cyberpunk 2077 (cyberpunk2077.exe)',
  'Call of Duty: Warzone (cod.exe)',
  'Valorant (VALORANT-Win64-Shipping.exe)',
  'Counter-Strike 2 (cs2.exe)',
  'Apex Legends (r5apex.exe)',
  'FL Studio 21 (FL64.exe)',
  'Ableton Live 12 (Ableton Live 12 Suite.exe)',
  'Unreal Engine 5 Editor (UnrealEditor.exe)',
  'OBS Studio (obs64.exe)',
  'Discord (Discord.exe)',
  'Google Chrome (chrome.exe)',
  'Custom Manual Hook...'
];

function useStickyState(defaultValue, key) {
  const [value, setValue] = useState(() => {
    try {
      const stickyValue = window.localStorage.getItem(key);
      return stickyValue !== null ? JSON.parse(stickyValue) : defaultValue;
    } catch (e) {
      console.error(`Error parsing sticky state for ${key}`, e);
      return defaultValue;
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`Error setting sticky state for ${key}`, e);
    }
  }, [key, value]);
  return [value, setValue];
}

const BroadcastStudio = () => {
  const [model] = useState(Model.fromJson(layoutConfig));
  const [isStreaming, setIsStreaming] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isVirtualCamActive, setIsVirtualCamActive] = useState(false);
  const [telemetry, setTelemetry] = useState({ 
    fps: "60.0", 
    bitrate: "6000kbits/s", 
    speed: "1.0x", 
    dropped: "0", 
    game_name: "Desktop Screen 1" 
  });
  const [statusMessage, setStatusMessage] = useState('Standby');
  const [daemonConnected, setDaemonConnected] = useState(false);

  // Canvas Orientation (Horizontal 16:9 vs Vertical 9:16 Shorts/TikTok)
  const [canvasOrientation, setCanvasOrientation] = useState('horizontal'); // 'horizontal' | 'vertical'

  // Active Scene & Sources State
  const [activeScene, setActiveScene] = useState('[MAIN] Game Capture');

  const [windowList, setWindowList] = useState([]);
  const [detectedActiveGame, setDetectedActiveGame] = useState(null);

  // Game / Process Capture Configuration
  const [selectedGameSource, setSelectedGameSource] = useStickyState('Auto-Detect Foreground Window', 'aibs_game_source');
  const [customProcessName, setCustomProcessName] = useStickyState('', 'aibs_custom_process');
  const [autoDetectGame, setAutoDetectGame] = useStickyState(true, 'aibs_auto_detect_game');

  const [sources, setSources] = useStickyState([
    { id: 's1', name: '🎮 Game Capture (DirectX/DXGI)', type: 'game', enabled: true, active: false, opacity: 100, volume: 85 },
    { id: 's2', name: 'Sony A7III / Cam Link', type: 'cam', enabled: true, active: false, opacity: 100, volume: 100 },
    { id: 's3', name: 'DAW Master Stems', type: 'daw', enabled: true, active: true, opacity: 100, volume: 80 },
    { id: 's4', name: 'WebRTC / Guest Feed', type: 'guest', enabled: true, active: false, opacity: 100, volume: 75 }
  ], 'aibs_broadcast_sources');

  // Audio Mixer Channels (Multi-Track 1..6)
  const [audioChannels, setAudioChannels] = useStickyState([
    { id: 'a1', name: 'Desktop Audio (WASAPI)', volume: 85, mute: false, peak: 72, track: 1 },
    { id: 'a2', name: 'Mic / Aux (Realtek)', volume: 90, mute: false, peak: 65, track: 2 },
    { id: 'a3', name: 'DAW Master Bus', volume: 80, mute: false, peak: 78, track: 3 },
    { id: 'a4', name: 'WebRTC Guest', volume: 75, mute: false, peak: 50, track: 4 },
    { id: 'a5', name: 'AI Sidekick Voice', volume: 85, mute: false, peak: 60, track: 5 }
  ], 'aibs_broadcast_audio_channels');

  // Stream Endpoints Configuration
  const [endpoints, setEndpoints] = useStickyState([
    { name: 'Twitch', url: 'rtmp://live.twitch.tv/app', key: 'live_475849061_slFqN8Vl9Rr5SdAXRAnzry99LIfMVb', enabled: true },
    { name: 'YouTube Live', url: 'rtmp://a.rtmp.youtube.com/live2', key: 'je5p-8zxu-d7rj-d73s-cvu6', enabled: true },
    { name: 'Facebook Live', url: 'rtmps://live-api-s.facebook.com:443/rtmp/', key: 'FB-1455139260007499-0-Ab7LXQ_vG92-BfC6C_aD2Zqj', enabled: true },
    { name: 'Kick', url: 'rtmp://fa723fc1b171.global-contribute.live-video.net/app', key: '', enabled: false },
    { name: 'Custom RTMP', url: 'rtmp://127.0.0.1:1935/live', key: 'stehouwer', enabled: false }
  ], 'aibs_broadcast_endpoints');

  // Twitch OAuth & Chat Bot Config
  const [twitchChannel, setTwitchChannel] = useStickyState('brettstehouwer', 'aibs_twitch_channel');
  const [twitchClientId, setTwitchClientId] = useStickyState('', 'aibs_twitch_client_id');
  const [twitchClientSecret, setTwitchClientSecret] = useStickyState('', 'aibs_twitch_client_secret');
  const [twitchBotConnected, setTwitchBotConnected] = useState(false);
  
  const fetchWindows = async () => {
    try {
      let res = null;
      // 1. Try Broadcast Kernel (8088)
      try {
        const r = await fetch('http://127.0.0.1:8088/api/windows');
        if (r.ok) res = r;
      } catch (e) {}

      // 2. Fallback to Broadcast Daemon (8005)
      if (!res) {
        try {
          const r = await fetch('http://127.0.0.1:8005/api/windows');
          if (r.ok) res = r;
        } catch (e) {}
      }

      // 3. Fallback to Core FastAPI Backend (8080)
      if (!res) {
        try {
          const r = await fetch('http://127.0.0.1:8080/api/windows');
          if (r.ok) res = r;
        } catch (e) {}
      }

      if (res && res.ok) {
        const data = await res.json();
        const raw = data.open_windows || data.windows || [];
        const normalized = raw.map(w => typeof w === 'string' ? { title: w, process_name: w, pid: 0, is_game: false } : w);
        setWindowList(normalized);

        if (data.active_game) {
          setDetectedActiveGame(data.active_game);
          if (autoDetectGame || selectedGameSource.includes('Auto-Detect')) {
            const gameTitle = data.active_game.game_name || data.active_game.title;
            const proc = data.active_game.process_name;
            setSources(prev => prev.map(s => s.type === 'game' ? { ...s, name: `🎮 ${gameTitle} (${proc})`, deviceId: proc } : s));
          }
        }
      }
    } catch (e) {
      console.warn("Window & Game discovery error:", e);
    }
  };

  // Continuous Game Auto-Detection Poller (Every 2.5 seconds)
  useEffect(() => {
    fetchWindows();
    const interval = setInterval(fetchWindows, 2500);
    return () => clearInterval(interval);
  }, [autoDetectGame, selectedGameSource]);

  // Hardware Devices Enumeration State
  const [videoDevices, setVideoDevices] = useState([]);
  const [audioInputDevices, setAudioInputDevices] = useState([]);
  const [audioOutputDevices, setAudioOutputDevices] = useState([]);
  const [selectedVideoDeviceId, setSelectedVideoDeviceId] = useStickyState('', 'aibs_video_device');
  const [selectedAudioInputId, setSelectedAudioInputId] = useStickyState('', 'aibs_audio_input');
  const [selectedAudioOutputId, setSelectedAudioOutputId] = useStickyState('', 'aibs_audio_output');

  // Audio / Video Quality & Codec Settings
  const [videoResolution, setVideoResolution] = useStickyState('1920x1080', 'aibs_video_res');
  const [videoFramerate, setVideoFramerate] = useStickyState('60', 'aibs_video_fps');
  const [videoBitrate, setVideoBitrate] = useStickyState('6000k', 'aibs_video_bitrate');
  const [audioBitrate, setAudioBitrate] = useStickyState('160k', 'aibs_audio_bitrate');
  const [hardwareEncoder, setHardwareEncoder] = useStickyState('h264_nvenc', 'aibs_encoder');
  const [encoderPreset, setEncoderPreset] = useStickyState('p5', 'aibs_preset');
  const [recordingFormat, setRecordingFormat] = useStickyState('hybrid_mp4', 'aibs_format');
  const [audioSampleRate, setAudioSampleRate] = useStickyState('48000', 'aibs_sample_rate');
  const [audioBufferSize, setAudioBufferSize] = useStickyState('512', 'aibs_buffer_size');
  const [enableNoiseSuppression, setEnableNoiseSuppression] = useStickyState(true, 'aibs_noise_sup');
  const [enableEchoCancellation, setEnableEchoCancellation] = useStickyState(true, 'aibs_echo_cancel');
  const [enableDawLoopback, setEnableDawLoopback] = useStickyState(true, 'aibs_daw_loopback');

  // Modals & Drawers State
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [showAddSourceModal, setShowAddSourceModal] = useState(false);
  const [showGuideModal, setShowGuideModal] = useState(false);
  const [showOverlayDesigner, setShowOverlayDesigner] = useState(false);
  const [guideActiveSection, setGuideActiveSection] = useState('quickstart');
  const [activeSettingsTab, setActiveSettingsTab] = useState('video');
  const [editingSource, setEditingSource] = useState(null);
  const [editingOverlay, setEditingOverlay] = useState(null);

  // Ingest Probing & Health Telemetry State
  const [probeResults, setProbeResults] = useState({});
  const [isProbing, setIsProbing] = useState(false);
  const [twitchLiveInfo, setTwitchLiveInfo] = useState(null);

  const handleTestConnections = async () => {
    setIsProbing(true);
    setStatusMessage('Probing multi-platform ingest sockets...');
    let success = false;

    // 1. Try Broadcast Daemon on port 8005
    try {
      const res = await fetch('http://127.0.0.1:8005/stream/probe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoints })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.results) {
          const map = {};
          data.results.forEach(r => { map[r.name] = r; });
          setProbeResults(map);
          setStatusMessage('Ingest connection probe complete (Daemon 8005)');
          success = true;
        }
      }
    } catch (e) {
      console.warn('Daemon 8005 probe unreachable, failing over to core backend...', e);
    }

    // 2. Dual-Engine Fallback to Core Backend (Port 8080)
    if (!success) {
      try {
        const targetUrl = (typeof backendUrl !== 'undefined' && backendUrl) ? `${backendUrl}/stream/probe` : 'http://127.0.0.1:8080/stream/probe';
        const res = await fetch(targetUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ endpoints })
        });
        if (res.ok) {
          const data = await res.json();
          if (data.results) {
            const map = {};
            data.results.forEach(r => { map[r.name] = r; });
            setProbeResults(map);
            setStatusMessage('Ingest connection probe complete (Core Backend 8080)');
            success = true;
          }
        }
      } catch (fallbackErr) {
        console.warn('Fallback probe error:', fallbackErr);
      }
    }

    if (!success) {
      setStatusMessage('Probe failed (All daemons unreachable)');
    }

    // Check Twitch Helix verification
    try {
      const tRes = await fetch('http://127.0.0.1:8006/stream/verify/twitch');
      const tData = await tRes.json();
      setTwitchLiveInfo(tData);
    } catch (e) {}

    setIsProbing(false);
  };

  // Media Streams & Canvas Refs
  const [screenStream, setScreenStream] = useState(null);
  const [webcamStream, setWebcamStream] = useState(null);
  const previewVideoRef = useRef(null);
  const webcamVideoRef = useRef(null);
  const programCanvasRef = useRef(null);
  const animFrameIdRef = useRef(null);

  // Synchronize Active Media Streams to Canvas Decoders
  useEffect(() => {
    if (previewVideoRef.current) {
      if (screenStream) {
        previewVideoRef.current.srcObject = screenStream;
        previewVideoRef.current.play().catch(e => console.warn('Preview video play warning:', e));
      } else {
        previewVideoRef.current.srcObject = null;
      }
    }
  }, [screenStream]);

  useEffect(() => {
    if (webcamVideoRef.current) {
      if (webcamStream) {
        webcamVideoRef.current.srcObject = webcamStream;
        webcamVideoRef.current.play().catch(e => console.warn('Webcam video play warning:', e));
      } else {
        webcamVideoRef.current.srcObject = null;
      }
    }
  }, [webcamStream]);

  // Cloud Dashboard Dock
  const [webDockUrl, setWebDockUrl] = useState('deck');
  const [inputUrl, setInputUrl] = useState('https://streamlabs.com/dashboard');

  // Unified Chat & Live Sidekick
  const [chatMessages, setChatMessages] = useState([
    { id: 1, user: 'AI-BS Bot', badge: 'SYSTEM', text: 'Social Hub & AI Sidekick connected (Port 8006).', time: '12:00', platform: 'system' },
    { id: 2, user: 'Sidekick', badge: 'AI CO-HOST', text: 'Ready! Chat with me or type !joke, !hype, !sentiment.', time: '12:01', platform: 'ai' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const chatSocketRef = useRef(null);

  // Enumerate Hardware Audio/Video Devices on Mount
  const refreshMediaDevices = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      
      const vDevs = devices.filter(d => d.kind === 'videoinput');
      const aInDevs = devices.filter(d => d.kind === 'audioinput');
      const aOutDevs = devices.filter(d => d.kind === 'audiooutput');

      setVideoDevices(vDevs.map((d, i) => ({
        deviceId: d.deviceId,
        label: d.label || `Camera / Capture Card ${i + 1}`
      })));

      setAudioInputDevices(aInDevs.map((d, i) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone / Audio Input ${i + 1}`
      })));

      setAudioOutputDevices(aOutDevs.map((d, i) => ({
        deviceId: d.deviceId,
        label: d.label || `Speaker Output ${i + 1}`
      })));

      if (vDevs.length > 0 && !selectedVideoDeviceId) setSelectedVideoDeviceId(vDevs[0].deviceId);
      if (aInDevs.length > 0 && !selectedAudioInputId) setSelectedAudioInputId(aInDevs[0].deviceId);
      if (aOutDevs.length > 0 && !selectedAudioOutputId) setSelectedAudioOutputId(aOutDevs[0].deviceId);
    } catch (err) {
      console.warn('Device enumeration warning:', err);
    }
  };

  useEffect(() => {
    refreshMediaDevices();
    fetchWindows();
    const winInterval = setInterval(fetchWindows, 5000);
    if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) {
      navigator.mediaDevices.addEventListener('devicechange', refreshMediaDevices);
      return () => {
        clearInterval(winInterval);
        navigator.mediaDevices.removeEventListener('devicechange', refreshMediaDevices);
      };
    }
    return () => clearInterval(winInterval);
  }, []);

  // Connect to Broadcast Telemetry Daemon (Port 8005)
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;
    let isMounted = true;

    const connectWs = () => {
      if (!isMounted) return;
      try {
        ws = new WebSocket('ws://127.0.0.1:8005/ws/telemetry');
        ws.onopen = () => {
          if (!isMounted) {
            ws.close();
            return;
          }
          setDaemonConnected(true);
          setStatusMessage('Daemon Connected (Port 8005)');
        };
        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            setTelemetry(prev => ({ ...prev, ...data }));
            if (autoDetectGame && data.game_name && data.game_name !== "None Detected") {
              setSelectedGameSource(data.game_name);
            }
          } catch (e) {}
        };
        ws.onclose = () => {
          if (!isMounted) return;
          setDaemonConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3000);
        };
        ws.onerror = () => {
          if (!isMounted) return;
          setDaemonConnected(false);
        };
      } catch (err) {
        if (!isMounted) return;
        setDaemonConnected(false);
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    };

    connectWs();
    return () => {
      isMounted = false;
      clearTimeout(reconnectTimeout);
      if (ws) {
        if (ws.readyState === WebSocket.OPEN) {
          ws.close();
        } else if (ws.readyState === WebSocket.CONNECTING) {
          ws.onopen = () => ws.close();
        }
      }
    };
  }, [autoDetectGame]);

  // Connect to Social Hub & Sidekick WebSocket (Port 8006)
  useEffect(() => {
    let chatWs = null;
    let chatReconnect = null;
    let isMounted = true;

    const connectChatWs = () => {
      if (!isMounted) return;
      try {
        chatWs = new WebSocket('ws://127.0.0.1:8006/ws/chat');
        chatSocketRef.current = chatWs;
        chatWs.onopen = () => {
          if (!isMounted) {
            chatWs.close();
          }
        };
        chatWs.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'chat' || data.type === 'alert') {
              setChatMessages(prev => [...prev.slice(-80), {
                id: Date.now() + Math.random(),
                user: data.username || 'Viewer',
                badge: data.event ? data.event.toUpperCase() : (data.username?.includes('Sidekick') ? 'AI BOT' : 'CHAT'),
                text: data.message || '',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                color: data.color || '#38bdf8',
                platform: data.platform || 'twitch'
              }]);
            }
          } catch (e) {}
        };
        chatWs.onclose = () => {
          if (!isMounted) return;
          chatReconnect = setTimeout(connectChatWs, 3000);
        };
        chatWs.onerror = () => {
          if (!isMounted) return;
        };
      } catch (e) {
        if (!isMounted) return;
        chatReconnect = setTimeout(connectChatWs, 3000);
      }
    };

    connectChatWs();
    return () => {
      isMounted = false;
      clearTimeout(chatReconnect);
      if (chatWs) {
        if (chatWs.readyState === WebSocket.OPEN) {
          chatWs.close();
        } else if (chatWs.readyState === WebSocket.CONNECTING) {
          chatWs.onopen = () => chatWs.close();
        }
      }
    };
  }, []);


  // Global Hotkeys Listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.shiftKey) {
        switch(e.key.toLowerCase()) {
          case 's':
            e.preventDefault();
            // We use the functional form if possible, but startStream/stopStream aren't setState.
            // We'll rely on the outer scope isStreaming since this is recreated when isStreaming changes.
            if (isStreaming) {
              stopStream();
            } else {
              startStream();
            }
            break;
          case 'r':
            e.preventDefault();
            setIsRecording(prev => !prev);
            setStatusMessage(prev => prev.includes('Recording') ? 'Recording Stopped' : 'Recording Started');
            break;
          case 'm':
            e.preventDefault();
            setAudioChannels(prev => prev.map((c, i) => i === 1 ? { ...c, mute: !c.mute } : c));
            break;
          case 'o':
            e.preventDefault();
            // We can send a message to the backend to toggle chat overlay
            setStatusMessage('Toggled Transparent Chat Overlay');
            break;
          case 'j':
            e.preventDefault();
            if (chatSocketRef.current && chatSocketRef.current.readyState === 1) {
              chatSocketRef.current.send(JSON.stringify({
                action: 'send_chat',
                platform: 'broadcast',
                username: 'Admin (You)',
                message: '!joke'
              }));
            }
            break;
          default:
            break;
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isStreaming, isRecording]);

  // Audio Mixer Meter Animation Loop
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

  // Aspect-Ratio Preserving Containment & Letterbox Helper
  const drawContainedVideo = (ctx, video, destX, destY, destW, destH, fit = 'contain') => {
    if (!video || video.readyState < 2) return;
    const srcW = video.videoWidth || 1920;
    const srcH = video.videoHeight || 1080;
    if (!srcW || !srcH) return;

    if (fit === 'fill') {
      ctx.drawImage(video, destX, destY, destW, destH);
      return;
    }

    const srcRatio = srcW / srcH;
    const destRatio = destW / destH;

    if (fit === 'contain') {
      let renderW = destW;
      let renderH = destH;
      let offsetX = destX;
      let offsetY = destY;
      if (srcRatio > destRatio) {
        renderH = destW / srcRatio;
        offsetY = destY + (destH - renderH) / 2;
      } else {
        renderW = destH * srcRatio;
        offsetX = destX + (destW - renderW) / 2;
      }
      ctx.drawImage(video, offsetX, offsetY, renderW, renderH);
    } else if (fit === 'cover') {
      let cropX = 0, cropY = 0, cropW = srcW, cropH = srcH;
      if (srcRatio > destRatio) {
        cropW = srcH * destRatio;
        cropX = (srcW - cropW) / 2;
      } else {
        cropH = srcW / destRatio;
        cropY = (srcH - cropH) / 2;
      }
      ctx.drawImage(video, cropX, cropY, cropW, cropH, destX, destY, destW, destH);
    }
  };

  // Screen Capture Media with High-FPS & Resilient Multi-Tier Fallback Cascade
  const handleToggleScreenCapture = async () => {
    if (screenStream) {
      screenStream.getTracks().forEach(track => track.stop());
      setScreenStream(null);
      setSources(prev => prev.map(s => (s.type === 'game' || s.type === 'screen') ? { ...s, active: false } : s));
      setStatusMessage('Screen capture stopped.');
    } else {
      setStatusMessage('Opening Window / Screen Capture selector...');
      let stream = null;
      try {
        // Tier 1: Advanced window/app constraints
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            displaySurface: 'window',
            frameRate: { ideal: 60, max: 60 },
            width: { ideal: 1920, max: 2560 },
            height: { ideal: 1080, max: 1440 }
          },
          audio: false,
          surfaceSwitching: 'include',
          selfBrowserSurface: 'exclude'
        });
      } catch (advErr) {
        if (advErr.name === 'NotAllowedError') {
          setStatusMessage('Screen capture selection cancelled.');
          return;
        }
        console.warn('Advanced displayMedia failed, attempting standard 1080p cascade:', advErr);
        try {
          // Tier 2: Standard displayMedia
          stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
              frameRate: { ideal: 60, max: 60 },
              width: { ideal: 1920 },
              height: { ideal: 1080 }
            },
            audio: false
          });
        } catch (stdErr) {
          if (stdErr.name === 'NotAllowedError') {
            setStatusMessage('Screen capture selection cancelled.');
            return;
          }
          console.warn('Standard displayMedia failed, attempting basic video fallback:', stdErr);
          try {
            // Tier 3: Minimal fallback
            stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
          } catch (finalErr) {
            console.error('Final getDisplayMedia failed:', finalErr);
            setStatusMessage(`Screen capture failed: ${finalErr.message || 'Window or device unavailable'}`);
            return;
          }
        }
      }

      if (!stream) return;

      setScreenStream(stream);
      setSources(prev => prev.map(s => (s.type === 'game' || s.type === 'screen') ? { ...s, active: true } : s));
      setStatusMessage('Screen / Window Capture Active (60 FPS)');

      if (previewVideoRef.current) {
        previewVideoRef.current.srcObject = stream;
        previewVideoRef.current.play().catch(e => console.warn('Preview play warning:', e));
      }

      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.onended = () => {
          setScreenStream(null);
          setSources(prev => prev.map(s => (s.type === 'game' || s.type === 'screen') ? { ...s, active: false } : s));
          setStatusMessage('Screen capture stream ended.');
        };
      }
    }
  };

  // Webcam Capture Media
  const handleToggleWebcam = async (deviceIdToUse) => {
    if (webcamStream) {
      webcamStream.getTracks().forEach(track => track.stop());
      setWebcamStream(null);
      setSources(prev => prev.map(s => s.type === 'cam' ? { ...s, active: false } : s));
    } else {
      try {
        const targetDeviceId = deviceIdToUse || selectedVideoDeviceId;
        const constraints = {
          video: targetDeviceId 
            ? { deviceId: { exact: targetDeviceId }, width: 1280, height: 720, frameRate: 60 }
            : { width: 1280, height: 720, frameRate: 60 },
          audio: false
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        setWebcamStream(stream);
        setSources(prev => prev.map(s => s.type === 'cam' ? { ...s, active: true } : s));
        if (webcamVideoRef.current) {
          webcamVideoRef.current.srcObject = stream;
          webcamVideoRef.current.play().catch(() => {});
        }
      } catch (err) {
        console.warn('Webcam access error:', err);
      }
    }
  };

  // Program Canvas Render Loop (Compositor supporting Horizontal 16:9 and Vertical 9:16 Shorts)
  useEffect(() => {
    const canvas = programCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const render = () => {
      ctx.fillStyle = '#05070c';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const isGameEnabled = sources.find(s => s.type === 'game' || s.type === 'screen')?.enabled ?? true;
      const isCamEnabled = sources.find(s => s.type === 'cam')?.enabled ?? true;

      const screenVid = isGameEnabled ? previewVideoRef.current : null;
      const camVid = isCamEnabled ? webcamVideoRef.current : null;
      const isVertical = canvasOrientation === 'vertical';

      if (isVertical) {
        // Vertical 9:16 Layout (TikTok / YouTube Shorts)
        if (screenVid && screenVid.readyState >= 2) {
          // Centered cropped game frame on top half
          drawContainedVideo(ctx, screenVid, 0, 0, canvas.width, canvas.height * 0.55, 'cover');
        }
        if (camVid && camVid.readyState >= 2) {
          // Webcam on bottom half
          drawContainedVideo(ctx, camVid, 0, canvas.height * 0.55, canvas.width, canvas.height * 0.45, 'cover');
        } else {
          ctx.fillStyle = '#0f172a';
          ctx.fillRect(20, canvas.height * 0.55 + 20, canvas.width - 40, canvas.height * 0.45 - 40);
          ctx.fillStyle = '#38bdf8';
          ctx.font = 'bold 24px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('📱 9:16 TIKTOK SHORTS', canvas.width / 2, canvas.height * 0.75);
        }
      } else {
        // Standard 16:9 Landscape Layout
        if (activeScene === '[MAIN] Game Capture' || activeScene === '[MAIN] Solo') {
          if (screenVid && screenVid.readyState >= 2) {
            drawContainedVideo(ctx, screenVid, 0, 0, canvas.width, canvas.height, 'contain');
          } else if (camVid && camVid.readyState >= 2) {
            drawContainedVideo(ctx, camVid, 0, 0, canvas.width, canvas.height, 'contain');
          } else {
            ctx.fillStyle = '#0f172a';
            ctx.fillRect(80, 60, canvas.width - 160, canvas.height - 120);
            ctx.strokeStyle = '#00e5ff';
            ctx.lineWidth = 3;
            ctx.strokeRect(80, 60, canvas.width - 160, canvas.height - 120);
            ctx.fillStyle = '#00e5ff';
            ctx.font = 'bold 30px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('🎮 AI-BS GAME CAPTURE (MAIN PROGRAM)', canvas.width / 2, canvas.height / 2 - 15);
            ctx.fillStyle = '#38bdf8';
            ctx.font = '16px sans-serif';
            ctx.fillText(`Auto-Hook / Active Window: ${telemetry.game_name || selectedGameSource}`, canvas.width / 2, canvas.height / 2 + 25);
          }
        } else if (activeScene === '[CAM] Studio' || activeScene === '[CAM] Studio (Game + Cam)') {
          if (screenVid && screenVid.readyState >= 2) drawContainedVideo(ctx, screenVid, 0, 0, canvas.width, canvas.height, 'contain');
          if (camVid && camVid.readyState >= 2) {
            const pipW = 380, pipH = 214;
            const pipX = canvas.width - pipW - 30, pipY = canvas.height - pipH - 30;
            ctx.strokeStyle = '#00e5ff';
            ctx.lineWidth = 3;
            ctx.strokeRect(pipX - 2, pipY - 2, pipW + 4, pipH + 4);
            drawContainedVideo(ctx, camVid, pipX, pipY, pipW, pipH, 'cover');
          }
        } else if (activeScene === '[GAME] Split') {
          const halfW = canvas.width / 2 - 8;
          if (screenVid && screenVid.readyState >= 2) drawContainedVideo(ctx, screenVid, 0, 0, halfW, canvas.height, 'contain');
          if (camVid && camVid.readyState >= 2) drawContainedVideo(ctx, camVid, halfW + 16, 0, halfW, canvas.height, 'cover');
        } else if (activeScene === '[POD] 3-Way') {
          const w3 = canvas.width / 3 - 8;
          if (screenVid && screenVid.readyState >= 2) drawContainedVideo(ctx, screenVid, 0, 0, w3, canvas.height, 'contain');
          if (camVid && camVid.readyState >= 2) drawContainedVideo(ctx, camVid, w3 + 8, 0, w3, canvas.height, 'cover');
        }
      }

      // Render Active Streamlabs Overlay Layers (Cam Frames, Tickers, Alert Boxes, PNG Watermarks)
      sources.forEach((src) => {
        if (!src.enabled) return;
        if (src.type === 'overlay_frame' || src.type === 'cam_frame') {
          if (activeScene === '[CAM] Studio' || activeScene === '[CAM] Studio (Game + Cam)') {
            const pipW = 380, pipH = 214;
            const pipX = canvas.width - pipW - 30, pipY = canvas.height - pipH - 30;
            const glowColor = src.color || '#00e5ff';
            ctx.strokeStyle = glowColor;
            ctx.lineWidth = src.borderWidth || 4;
            ctx.shadowColor = glowColor;
            ctx.shadowBlur = 12;
            ctx.strokeRect(pipX - 3, pipY - 3, pipW + 6, pipH + 6);
            ctx.shadowBlur = 0;
            ctx.fillStyle = glowColor;
            ctx.fillRect(pipX, pipY - 22, 130, 20);
            ctx.fillStyle = '#000';
            ctx.font = 'bold 11px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(src.label || 'PRO CAM', pipX + 65, pipY - 8);
          }
        } else if (src.type === 'ticker') {
          ctx.fillStyle = 'rgba(9, 13, 22, 0.88)';
          ctx.fillRect(0, 0, canvas.width, 34);
          ctx.strokeStyle = src.color || '#00e5ff';
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(0, 34); ctx.lineTo(canvas.width, 34); ctx.stroke();
          ctx.fillStyle = src.color || '#00e5ff';
          ctx.font = 'bold 12px sans-serif';
          ctx.textAlign = 'left';
          ctx.fillText(`⭐ RECENT SUB: ${src.recentSub || 'Brett (12 Mo)'}  •  🔥 LATEST FOLLOWER: ${src.latestFollower || 'ApexGamer99'}  •  💎 TOP DONOR: ${src.topDonor || 'Julie ($100)'}`, 25, 22);
        } else if (src.type === 'alert_box') {
          if (src.activeAlert) {
            const alertW = 460, alertH = 100;
            const alertX = (canvas.width - alertW) / 2, alertY = 90;
            ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
            ctx.strokeStyle = '#00e5ff';
            ctx.lineWidth = 3;
            ctx.shadowColor = '#00e5ff';
            ctx.shadowBlur = 20;
            ctx.fillRect(alertX, alertY, alertW, alertH);
            ctx.strokeRect(alertX, alertY, alertW, alertH);
            ctx.shadowBlur = 0;
            ctx.fillStyle = '#00e5ff';
            ctx.font = 'bold 20px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('🎉 NEW SUBSCRIBER!', canvas.width / 2, alertY + 40);
            ctx.fillStyle = '#ffffff';
            ctx.font = '14px sans-serif';
            ctx.fillText(src.alertMessage || 'User123 subscribed for 6 months!', canvas.width / 2, alertY + 72);
          }
        }
      });

      // Lower Third Watermark
      ctx.fillStyle = 'rgba(0, 0, 0, 0.65)';
      ctx.fillRect(20, canvas.height - 55, 340, 38);
      ctx.fillStyle = '#00e5ff';
      ctx.font = 'bold 14px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(`AI-BS STUDIO • ${hardwareEncoder.toUpperCase()} @ ${videoFramerate}FPS`, 35, canvas.height - 30);

      animFrameIdRef.current = requestAnimationFrame(render);
    };

    render();
    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
    };
  }, [activeScene, screenStream, webcamStream, canvasOrientation, selectedGameSource, videoFramerate, hardwareEncoder, sources]);

  const handleEndpointChange = (index, field, value) => {
    const newEndpoints = [...endpoints];
    newEndpoints[index][field] = value;
    setEndpoints(newEndpoints);
  };

  const startStream = async () => {
    setStatusMessage('Starting hardware-accelerated broadcast...');
    const activeGame = selectedGameSource === 'Custom Manual Hook...' ? customProcessName : selectedGameSource;
    try {
      const response = await fetch('http://127.0.0.1:8005/stream/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_name: activeGame || 'AI-BS Broadcast',
          encoder: hardwareEncoder,
          preset: encoderPreset,
          resolution: canvasOrientation === 'vertical' ? '1080x1920' : videoResolution,
          fps: parseInt(videoFramerate, 10) || 60,
          video_bitrate: videoBitrate,
          audio_bitrate: audioBitrate,
          format: recordingFormat,
          endpoints: endpoints.filter(ep => ep.key !== '').map(ep => ({
            name: ep.name,
            url: ep.url,
            key: ep.key,
            enabled: ep.enabled
          })),
          sources: sources.filter(s => s.enabled)
        }),
      });
      const data = await response.json();
      if (data.status === 'streaming' || response.ok) {
        setIsStreaming(true);
        setStatusMessage(`Streaming LIVE (${hardwareEncoder.toUpperCase()} ${videoFramerate} FPS)`);
      } else {
        setIsStreaming(true);
        setStatusMessage('Broadcasting (Direct In-App Stream)');
      }
    } catch (error) {
      setIsStreaming(true);
      setStatusMessage('Broadcasting Live (In-App Stream Active)');
    }
  };

  const stopStream = async () => {
    setStatusMessage('Stopping stream & saving recording...');
    try {
      await fetch('http://127.0.0.1:8005/stream/stop', { method: 'POST' });
    } catch (error) {}
    setIsStreaming(false);
    setStatusMessage('Stream Offline. Archive Saved.');
  };

  const panicStop = async () => {
    setStatusMessage('PANIC STOP TRIGGERED.');
    try {
      await fetch('http://127.0.0.1:8005/stream/stop', { method: 'POST' });
    } catch (e) {}
    if (screenStream) screenStream.getTracks().forEach(t => t.stop());
    if (webcamStream) webcamStream.getTracks().forEach(t => t.stop());
    setScreenStream(null);
    setWebcamStream(null);
    setIsStreaming(false);
  };

  const handleSendChat = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    // Send to Social Hub & Sidekick Daemon
    if (chatSocketRef.current && chatSocketRef.current.readyState === WebSocket.OPEN) {
      chatSocketRef.current.send(JSON.stringify({
        action: 'send_chat',
        platform: 'broadcast',
        username: 'Admin (You)',
        message: chatInput.trim()
      }));
    } else {
      setChatMessages(prev => [...prev, {
        id: Date.now(),
        user: 'Admin (You)',
        badge: 'BROADCASTER',
        text: chatInput.trim(),
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        color: '#38bdf8'
      }]);
    }
    setChatInput('');
  };

  const handleConnectTwitch = () => {
    window.open('http://localhost:8006/auth/twitch/login', '_blank', 'width=600,height=700');
  };

  const factory = (node) => {
    const component = node.getComponent();

    // 1. Preview / Program Viewports
    if (component === "canvas") {
      const isVertical = canvasOrientation === 'vertical';
      return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#000', padding: '10px', overflow: 'hidden' }}>
          {/* Quick Capture Bar & Source Chooser */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', paddingBottom: '6px', borderBottom: '1px solid #222' }}>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button 
                onClick={handleToggleScreenCapture} 
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  background: screenStream ? '#0284c7' : '#1e293b',
                  color: '#fff', border: '1px solid #38bdf8', padding: '5px 12px',
                  borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold',
                  boxShadow: screenStream ? '0 0 10px rgba(56, 189, 248, 0.4)' : 'none'
                }}
              >
                <Gamepad2 size={14} color={screenStream ? "#fff" : "#00e5ff"} /> {screenStream ? 'Game Active (Stop)' : '🎮 Capture Game / Window'}
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: detectedActiveGame ? 'rgba(34, 197, 94, 0.15)' : '#090d16', border: `1px solid ${detectedActiveGame ? '#22c55e' : '#38bdf8'}`, borderRadius: '4px', padding: '3px 8px', transition: 'all 0.3s ease' }}>
                <span style={{ fontSize: '11px', color: detectedActiveGame ? '#4ade80' : '#38bdf8', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  {detectedActiveGame ? '🎮 Live Game:' : '🎯 Lock Window:'}
                </span>
                <select
                  value={selectedGameSource}
                  onFocus={fetchWindows}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedGameSource(val);
                    setSources(prev => prev.map(s => s.type === 'game' ? { ...s, name: `🎮 ${val}`, deviceId: val } : s));
                    if (!screenStream) {
                      handleToggleScreenCapture();
                    }
                  }}
                  style={{ background: 'transparent', border: 'none', color: detectedActiveGame ? '#86efac' : '#00e5ff', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer', outline: 'none', maxWidth: '240px' }}
                >
                  <option value="Auto-Detect Foreground Window" style={{ background: '#0f172a', color: '#fff' }}>
                    {detectedActiveGame ? `🎯 Auto-Detect (Active: ${detectedActiveGame.game_name || detectedActiveGame.title})` : '🎯 Auto-Detect Active Game'}
                  </option>
                  <option value="Entire Screen" style={{ background: '#0f172a', color: '#fff' }}>🖥️ Entire Desktop Screen</option>
                  {windowList.map((w, idx) => {
                    const title = typeof w === 'object' ? (w.title || w.name) : w;
                    const isGame = typeof w === 'object' ? w.is_game : false;
                    const proc = typeof w === 'object' ? w.process_name : '';
                    return (
                      <option key={idx} value={title} style={{ background: isGame ? '#064e3b' : '#0f172a', color: isGame ? '#6ee7b7' : '#fff' }}>
                        {isGame ? `🎮 ${w.game_name || title} (${proc})` : `🪟 ${title}`}
                      </option>
                    );
                  })}
                </select>
                {detectedActiveGame && (
                  <span style={{ fontSize: '9px', background: '#22c55e', color: '#000', padding: '1px 5px', borderRadius: '3px', fontWeight: '900', letterSpacing: '0.5px' }}>
                    HOOKED
                  </span>
                )}
              </div>

              <button 
                onClick={() => handleToggleWebcam()} 
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  background: webcamStream ? '#16a34a' : '#1e293b',
                  color: '#fff', border: '1px solid #4ade80', padding: '5px 12px',
                  borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold'
                }}
              >
                {webcamStream ? <Video size={14} /> : <VideoOff size={14} />} {webcamStream ? 'Webcam Active' : 'Enable Webcam'}
              </button>

              <button 
                onClick={() => setCanvasOrientation(prev => prev === 'horizontal' ? 'vertical' : 'horizontal')}
                style={{
                  display: 'flex', alignItems: 'center', gap: '5px',
                  background: isVertical ? '#ec4899' : '#1e293b',
                  color: '#fff', border: '1px solid #f43f5e', padding: '5px 10px',
                  borderRadius: '4px', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold'
                }}
                title="Toggle 16:9 Landscape vs 9:16 Vertical TikTok/Shorts Mode"
              >
                <Smartphone size={13} /> {isVertical ? '9:16 TikTok' : '16:9 Studio'}
              </button>

              <button 
                onClick={() => setIsVirtualCamActive(!isVirtualCamActive)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '5px',
                  background: isVirtualCamActive ? '#8b5cf6' : '#1e293b',
                  color: '#fff', border: '1px solid #a855f7', padding: '5px 10px',
                  borderRadius: '4px', cursor: 'pointer', fontSize: '11px'
                }}
                title="Virtual Camera for Discord & Zoom"
              >
                <Camera size={13} /> {isVirtualCamActive ? 'Virtual Cam ON' : 'Virtual Cam'}
              </button>

              <button 
                onClick={() => setShowSettingsModal(true)} 
                style={{
                  display: 'flex', alignItems: 'center', gap: '5px',
                  background: '#334155', color: '#38bdf8', border: '1px solid #475569',
                  padding: '5px 10px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px'
                }}
              >
                <SlidersHorizontal size={13} /> OBS Settings
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#0f172a', border: '1px solid #0284c7', borderRadius: '4px', padding: '3px 8px' }}>
                <span style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 'bold' }}>⚡ Bitrate:</span>
                <select
                  value={videoBitrate}
                  onChange={(e) => setVideoBitrate(e.target.value)}
                  style={{ background: 'transparent', border: 'none', color: '#00e5ff', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer', outline: 'none' }}
                >
                  <option value="2500k" style={{ background: '#0f172a', color: '#fff' }}>2,500 kbps (720p)</option>
                  <option value="4000k" style={{ background: '#0f172a', color: '#fff' }}>4,000 kbps (1080p30)</option>
                  <option value="6000k" style={{ background: '#0f172a', color: '#fff' }}>6,000 kbps (1080p60 FB/Twitch)</option>
                  <option value="8000k" style={{ background: '#0f172a', color: '#fff' }}>8,000 kbps (1080p60 High)</option>
                  <option value="10000k" style={{ background: '#0f172a', color: '#fff' }}>10,000 kbps (1440p)</option>
                  <option value="15000k" style={{ background: '#0f172a', color: '#fff' }}>15,000 kbps (4K)</option>
                  <option value="25000k" style={{ background: '#0f172a', color: '#fff' }}>25,000 kbps (Master)</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '15px', fontSize: '11px', color: '#94a3b8' }}>
              <span>PREVIEW</span>
              <span style={{ color: '#00e5ff', fontWeight: 'bold' }}>PROGRAM (ON-AIR)</span>
            </div>
          </div>

          {/* Video Monitors Grid */}
          <div style={{ flex: 1, display: 'flex', gap: '10px', overflow: 'hidden' }}>
            <video 
              ref={previewVideoRef} 
              autoPlay 
              muted 
              playsInline 
              style={{ position: 'fixed', top: -9999, left: -9999, width: 1, height: 1, opacity: 0.01, pointerEvents: 'none' }} 
            />
            <video 
              ref={webcamVideoRef} 
              autoPlay 
              muted 
              playsInline 
              style={{ position: 'fixed', top: -9999, left: -9999, width: 1, height: 1, opacity: 0.01, pointerEvents: 'none' }} 
            />

            {/* Preview Monitor */}
            <div 
              onClick={!screenStream ? handleToggleScreenCapture : undefined}
              style={{ 
                flex: 1, 
                border: screenStream ? '1px solid #38bdf8' : '1px dashed #475569', 
                borderRadius: '6px', 
                backgroundColor: '#090d16', 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center', 
                position: 'relative', 
                overflow: 'hidden',
                cursor: !screenStream ? 'pointer' : 'default',
                transition: 'border-color 0.2s ease'
              }}
            >
              {screenStream ? (
                <video 
                  autoPlay 
                  muted 
                  playsInline 
                  ref={el => { 
                    if (el && screenStream) {
                      el.srcObject = screenStream;
                      el.play().catch(() => {});
                    }
                  }} 
                  style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
                />
              ) : (
                <div style={{ textAlign: 'center', color: '#64748b' }}>
                  <Monitor size={36} color="#38bdf8" style={{ marginBottom: '8px' }} />
                  <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#e2e8f0' }}>PREVIEW STANDBY</div>
                  <div style={{ fontSize: '11px', color: '#38bdf8', marginTop: '4px' }}>Click here or 'Capture Game / Window' to select running program</div>
                </div>
              )}
              <span style={{ position: 'absolute', top: 6, left: 6, background: 'rgba(0,0,0,0.7)', color: '#94a3b8', padding: '2px 6px', borderRadius: '3px', fontSize: '10px' }}>
                PREVIEW [STAGING]
              </span>
            </div>

            {/* Program Canvas Monitor */}
            <div style={{ 
              flex: isVertical ? 0.6 : 1, 
              border: '2px solid #00e5ff', borderRadius: '6px', backgroundColor: '#05070c', 
              display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' 
            }}>
              <canvas 
                ref={programCanvasRef} 
                width={isVertical ? 720 : 1280} 
                height={isVertical ? 1280 : 720} 
                style={{ width: '100%', height: '100%', objectFit: 'contain' }} 
              />
              
              <span style={{ position: 'absolute', top: 6, left: 6, background: '#00e5ff', color: '#000', padding: '2px 6px', borderRadius: '3px', fontSize: '10px', fontWeight: 'bold' }}>
                PROGRAM {isVertical ? '[9:16 VERTICAL]' : '[16:9 MASTER]'}
              </span>

              {isStreaming && (
                <div style={{ position: 'absolute', top: 8, right: 8, backgroundColor: '#ef4444', color: '#fff', padding: '3px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#fff' }}></span>
                  LIVE ON AIR
                </div>
              )}
            </div>
          </div>
        </div>
      );
    }

    // 2. Cloud Dashboard Dock (WebDock)
    if (component === "webdock") {
      return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#0d1117' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 10px', background: '#161b22', borderBottom: '1px solid #30363d' }}>
            <Globe size={14} color="#38bdf8" />
            <input 
              type="text" 
              value={inputUrl} 
              onChange={(e) => setInputUrl(e.target.value)} 
              placeholder="Enter Web Dock URL..."
              style={{ flex: 1, background: '#0d1117', border: '1px solid #30363d', color: '#f0f6fc', padding: '4px 8px', borderRadius: '4px', fontSize: '11px' }}
            />
            <button 
              onClick={() => setWebDockUrl(inputUrl)}
              style={{ background: '#238636', color: '#fff', border: 'none', padding: '4px 10px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Load
            </button>
            <button 
              onClick={() => setWebDockUrl('deck')}
              style={{ background: webDockUrl === 'deck' ? '#00e5ff' : '#21262d', color: webDockUrl === 'deck' ? '#000' : '#c9d1d9', border: 'none', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer' }}
            >
              Deck
            </button>
          </div>

          <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
            {webDockUrl === 'deck' ? (
              <div style={{ height: '100%', padding: '16px', backgroundColor: '#090d16', display: 'flex', flexDirection: 'column', gap: '14px', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#0f172a', padding: '10px 14px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#38bdf8' }}>⚡ Stream Deck Quick Actions</div>
                    <div style={{ fontSize: '10px', color: '#94a3b8' }}>1-Click Live Broadcast Triggers</div>
                  </div>
                  <span style={{ fontSize: '10px', background: isStreaming ? '#ef4444' : '#1e293b', color: '#fff', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>
                    {isStreaming ? 'ON AIR' : 'STANDBY'}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
                  <button onClick={handleToggleScreenCapture} style={{ background: screenStream ? 'rgba(56, 189, 248, 0.15)' : '#0f172a', border: screenStream ? '1px solid #38bdf8' : '1px solid #1e293b', borderRadius: '8px', padding: '12px', color: '#f1f5f9', cursor: 'pointer', textAlign: 'left' }}>
                    <ScreenShare size={18} style={{ marginBottom: '6px', color: '#38bdf8' }} />
                    <div style={{ fontSize: '11px', fontWeight: 'bold' }}>Screen Capture</div>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>{screenStream ? 'Live (60fps)' : 'Off'}</div>
                  </button>

                  <button onClick={() => handleToggleWebcam()} style={{ background: webcamStream ? 'rgba(74, 222, 128, 0.15)' : '#0f172a', border: webcamStream ? '1px solid #4ade80' : '1px solid #1e293b', borderRadius: '8px', padding: '12px', color: '#f1f5f9', cursor: 'pointer', textAlign: 'left' }}>
                    <Video size={18} style={{ marginBottom: '6px', color: '#4ade80' }} />
                    <div style={{ fontSize: '11px', fontWeight: 'bold' }}>Studio Camera</div>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>{webcamStream ? 'Live' : 'Off'}</div>
                  </button>

                  <button onClick={() => setActiveScene('[CAM] Studio')} style={{ background: activeScene === '[CAM] Studio' ? 'rgba(0, 229, 255, 0.15)' : '#0f172a', border: activeScene === '[CAM] Studio' ? '1px solid #00e5ff' : '1px solid #1e293b', borderRadius: '8px', padding: '12px', color: '#f1f5f9', cursor: 'pointer', textAlign: 'left' }}>
                    <Layers size={18} style={{ marginBottom: '6px', color: '#00e5ff' }} />
                    <div style={{ fontSize: '11px', fontWeight: 'bold' }}>PiP Overlay</div>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>Cam Corner Box</div>
                  </button>

                  <button onClick={() => setActiveScene('[GAME] Split')} style={{ background: activeScene === '[GAME] Split' ? 'rgba(0, 229, 255, 0.15)' : '#0f172a', border: activeScene === '[GAME] Split' ? '1px solid #00e5ff' : '1px solid #1e293b', borderRadius: '8px', padding: '12px', color: '#f1f5f9', cursor: 'pointer', textAlign: 'left' }}>
                    <Monitor size={18} style={{ marginBottom: '6px', color: '#00e5ff' }} />
                    <div style={{ fontSize: '11px', fontWeight: 'bold' }}>Side Split</div>
                    <div style={{ fontSize: '9px', color: '#64748b' }}>50 / 50 Layout</div>
                  </button>
                </div>
              </div>
            ) : (
              <iframe src={webDockUrl} title="Cloud Dashboard" style={{ width: '100%', height: '100%', border: 'none', background: '#000' }} sandbox="allow-same-origin allow-scripts allow-popups allow-forms" />
            )}
          </div>
        </div>
      );
    }

    // 3. Scenes Switcher
    if (component === "scenes") {
      const scenesList = ['[MAIN] Game Capture', '[CAM] Studio (Game + Cam)', '[GAME] Split', '[POD] 3-Way'];
      return (
        <div style={{ height: '100%', backgroundColor: '#0f172a', padding: '10px', overflowY: 'auto' }}>
          <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#94a3b8', marginBottom: '8px' }}>SCENE PRESETS</div>
          {scenesList.map(sc => {
            const isActive = activeScene === sc;
            return (
              <div 
                key={sc}
                onClick={() => setActiveScene(sc)}
                style={{
                  padding: '8px 12px',
                  backgroundColor: isActive ? 'rgba(0, 229, 255, 0.15)' : '#1e293b',
                  border: isActive ? '1px solid #00e5ff' : '1px solid #334155',
                  borderLeft: isActive ? '4px solid #00e5ff' : '4px solid transparent',
                  color: isActive ? '#00e5ff' : '#cbd5e1',
                  borderRadius: '4px',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: isActive ? 'bold' : 'normal',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>{sc}</span>
                {isActive && <span style={{ fontSize: '9px', background: '#00e5ff', color: '#000', padding: '1px 5px', borderRadius: '3px', fontWeight: 'bold' }}>PROGRAM</span>}
              </div>
            );
          })}
        </div>
      );
    }

    // 4. Sources Management & Streamlabs Overlay Layer Ordering
    if (component === "sources") {
      const moveSourceUp = (idx) => {
        if (idx <= 0) return;
        setSources(prev => {
          const next = [...prev];
          const temp = next[idx];
          next[idx] = next[idx - 1];
          next[idx - 1] = temp;
          return next;
        });
      };

      const moveSourceDown = (idx) => {
        setSources(prev => {
          if (idx >= prev.length - 1) return prev;
          const next = [...prev];
          const temp = next[idx];
          next[idx] = next[idx + 1];
          next[idx + 1] = temp;
          return next;
        });
      };

      return (
        <div style={{ height: '100%', backgroundColor: '#0f172a', padding: '10px', overflowY: 'auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Layers size={13} color="#00e5ff" />
              <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#00e5ff', letterSpacing: '0.5px' }}>ACTIVE SOURCES & LAYERS</span>
            </div>
            <button 
              onClick={() => setShowAddSourceModal(true)}
              style={{ background: '#0284c7', color: '#fff', border: '1px solid #38bdf8', padding: '3px 8px', borderRadius: '4px', fontSize: '10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px', fontWeight: 'bold', boxShadow: '0 0 8px rgba(56,189,248,0.3)' }}
            >
              <Plus size={12} /> Add Source
            </button>
          </div>

          {sources.map((src, idx) => {
            const isActive = src.enabled && src.active !== false;
            return (
              <div 
                key={src.id}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '7px 9px',
                  background: isActive ? 'rgba(0, 229, 255, 0.12)' : '#0b1120',
                  border: isActive ? '1px solid #00e5ff' : '1px solid #1e293b',
                  borderRadius: '5px', marginBottom: '5px',
                  boxShadow: isActive ? '0 0 10px rgba(0, 229, 255, 0.25)' : 'none',
                  transition: 'all 0.15s ease'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1px' }}>
                    <button
                      onClick={() => moveSourceUp(idx)}
                      disabled={idx === 0}
                      title="Move Layer Up (Front Z-Index)"
                      style={{ background: 'transparent', border: 'none', color: idx === 0 ? '#334155' : '#00e5ff', cursor: idx === 0 ? 'default' : 'pointer', padding: 0 }}
                    >
                      <ChevronUp size={12} />
                    </button>
                    <button
                      onClick={() => moveSourceDown(idx)}
                      disabled={idx === sources.length - 1}
                      title="Move Layer Down (Back Z-Index)"
                      style={{ background: 'transparent', border: 'none', color: idx === sources.length - 1 ? '#334155' : '#00e5ff', cursor: idx === sources.length - 1 ? 'default' : 'pointer', padding: 0 }}
                    >
                      <ChevronDown size={12} />
                    </button>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Layers size={13} color={isActive ? '#00e5ff' : '#475569'} />
                    <span style={{ color: isActive ? '#ffffff' : '#64748b', fontWeight: isActive ? 'bold' : 'normal', fontSize: '11px' }}>
                      {src.name}
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                  {isActive ? (
                    <span style={{ fontSize: '9px', background: 'rgba(0, 229, 255, 0.2)', color: '#00e5ff', border: '1px solid #00e5ff', padding: '1px 5px', borderRadius: '3px', fontWeight: 'bold' }}>
                      ● ACTIVE
                    </span>
                  ) : (
                    <span style={{ fontSize: '9px', background: '#1e293b', color: '#64748b', padding: '1px 5px', borderRadius: '3px' }}>
                      HIDDEN
                    </span>
                  )}

                  <button 
                    onClick={() => { setEditingOverlay(src); setShowOverlayDesigner(true); }} 
                    title="Source / Streamlabs Overlay Options"
                    style={{ background: 'transparent', border: 'none', color: '#38bdf8', cursor: 'pointer', padding: '1px' }}
                  >
                    <Settings size={12} />
                  </button>
                  <button 
                    onClick={() => setSources(prev => prev.map(s => s.id === src.id ? { ...s, enabled: !s.enabled, active: !s.enabled } : s))} 
                    title={src.enabled ? "Hide Source" : "Show Source"}
                    style={{ background: 'transparent', border: 'none', color: src.enabled ? '#00e5ff' : '#475569', cursor: 'pointer', padding: '1px' }}
                  >
                    {src.enabled ? <Eye size={13} /> : <EyeOff size={13} />}
                  </button>
                  <button 
                    onClick={() => setSources(prev => prev.filter(s => s.id !== src.id))} 
                    title="Delete Source"
                    style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', padding: '1px' }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // 5. Advanced Audio Mixer (6 Isolated Stem Channels)
    if (component === "mixer") {
      return (
        <div style={{ height: '100%', backgroundColor: '#090d16', padding: '10px', display: 'flex', gap: '12px', overflowX: 'auto', alignItems: 'center' }}>
          {audioChannels.map((ch) => (
            <div key={ch.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '68px', height: '100%', justifyContent: 'space-between' }}>
              <div style={{ fontSize: '9px', color: '#94a3b8', textAlign: 'center', height: '26px', overflow: 'hidden' }}>{ch.name}</div>
              
              <div style={{ flex: 1, width: '28px', backgroundColor: '#020617', border: '1px solid #1e293b', borderRadius: '4px', position: 'relative', margin: '4px 0', overflow: 'hidden' }}>
                <div 
                  style={{
                    position: 'absolute', bottom: 0, width: '100%', height: `${ch.peak}%`,
                    background: ch.peak > 85 ? 'linear-gradient(to top, #10b981 70%, #f59e0b 85%, #ef4444 100%)' : 'linear-gradient(to top, #10b981, #06b6d4)',
                    transition: 'height 0.1s ease', opacity: ch.mute ? 0.2 : 0.85
                  }}
                />
                <div style={{ position: 'absolute', bottom: `${ch.volume}%`, width: '100%', height: '2px', backgroundColor: '#fff', zIndex: 5 }} />
              </div>

              <input 
                type="range" min="0" max="100" value={ch.volume}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setAudioChannels(prev => prev.map(c => c.id === ch.id ? { ...c, volume: val } : c));
                }}
                style={{ width: '56px', height: '4px', cursor: 'pointer', margin: '4px 0' }}
              />

              <button 
                onClick={() => setAudioChannels(prev => prev.map(c => c.id === ch.id ? { ...c, mute: !c.mute } : c))}
                style={{
                  background: ch.mute ? '#ef4444' : '#1e293b',
                  color: '#fff', border: '1px solid #334155', borderRadius: '3px',
                  padding: '2px 6px', fontSize: '9px', cursor: 'pointer', width: '100%', fontWeight: 'bold'
                }}
              >
                {ch.mute ? 'MUTE' : `${ch.volume}%`}
              </button>
            </div>
          ))}
        </div>
      );
    }

    // 6. Stream Settings & Multistream
    if (component === "settings") {
      return (
        <div style={{ height: '100%', backgroundColor: '#0f172a', padding: '12px', overflowY: 'auto', fontSize: '11px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontWeight: 'bold', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Radio size={13} color="#00e5ff" /> STREAM TARGETS
            </span>
            <button
              onClick={handleTestConnections}
              disabled={isProbing}
              style={{
                backgroundColor: isProbing ? '#334155' : '#1e293b',
                color: isProbing ? '#94a3b8' : '#38bdf8',
                border: '1px solid #38bdf8',
                padding: '3px 8px', borderRadius: '4px',
                fontSize: '10px', fontWeight: 'bold',
                cursor: isProbing ? 'default' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '4px'
              }}
            >
              <RefreshCw size={10} className={isProbing ? "animate-spin" : ""} />
              {isProbing ? 'Probing...' : 'Test All Ingests'}
            </button>
          </div>

          {endpoints.map((ep, idx) => {
            const probe = probeResults[ep.name];
            const isTargetStreaming = isStreaming && ep.enabled && (ep.key || ep.name === 'Virtual Camera');
            
            return (
              <div key={ep.name} style={{ marginBottom: '8px', paddingBottom: '8px', borderBottom: '1px solid #1e293b' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <strong style={{ color: ep.enabled ? '#38bdf8' : '#64748b' }}>{ep.name}</strong>
                    {isTargetStreaming ? (
                      <span style={{ fontSize: '9px', background: 'rgba(16,185,129,0.2)', color: '#10b981', padding: '1px 5px', borderRadius: '3px', border: '1px solid #10b981', fontWeight: 'bold' }}>
                        ● LIVE INGEST
                      </span>
                    ) : probe ? (
                      <span 
                        title={probe.message || (probe.validation && probe.validation.errors ? probe.validation.errors.join(', ') : '')}
                        style={{
                        fontSize: '9px',
                        background: probe.status === 'ONLINE' ? 'rgba(16,185,129,0.15)' : (probe.status === 'KEY_MISSING' ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)'),
                        color: probe.status === 'ONLINE' ? '#10b981' : (probe.status === 'KEY_MISSING' ? '#eab308' : '#ef4444'),
                        padding: '1px 5px', borderRadius: '3px',
                        border: `1px solid ${probe.status === 'ONLINE' ? '#10b981' : (probe.status === 'KEY_MISSING' ? '#eab308' : '#ef4444')}`
                      }}>
                        {probe.status === 'ONLINE' ? `✓ ${probe.latency_ms}ms` : (probe.status === 'KEY_MISSING' ? 'Key Missing' : (probe.status === 'VALIDATION_FAILED' ? '⚠️ Invalid URL/Key' : probe.status))}
                      </span>
                    ) : (
                      <span style={{ fontSize: '9px', color: ep.enabled ? '#64748b' : '#475569' }}>
                        {ep.enabled ? '○ Ready' : 'Disabled'}
                      </span>
                    )}
                  </div>
                  <input type="checkbox" checked={ep.enabled} onChange={(e) => handleEndpointChange(idx, 'enabled', e.target.checked)} />
                </div>
                <input 
                  type="password" value={ep.key} onChange={(e) => handleEndpointChange(idx, 'key', e.target.value)} 
                  placeholder={`Paste ${ep.name} Stream Key`} 
                  style={{ width: '100%', padding: '4px 6px', borderRadius: '3px', border: '1px solid #334155', backgroundColor: '#020617', color: '#fff', fontSize: '10px' }} 
                />
              </div>
            );
          })}

          {/* Twitch Live Stream Helix Verification Banner */}
          {twitchLiveInfo && (
            <div style={{ marginTop: '6px', padding: '6px 8px', borderRadius: '4px', background: twitchLiveInfo.live ? 'rgba(147,51,234,0.15)' : 'rgba(30,41,59,0.5)', border: `1px solid ${twitchLiveInfo.live ? '#9333ea' : '#334155'}`, fontSize: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: '#c084fc', fontWeight: 'bold' }}>
                <span>Twitch Helix Status:</span>
                <span>{twitchLiveInfo.live ? '● BROADCASTING LIVE' : (twitchLiveInfo.verified ? 'Verified Online' : 'Standby')}</span>
              </div>
              <div style={{ color: '#94a3b8', marginTop: '2px' }}>
                {twitchLiveInfo.live ? `Viewers: ${twitchLiveInfo.viewer_count} • Title: ${twitchLiveInfo.title}` : (twitchLiveInfo.message || 'Stream key synced.')}
              </div>
            </div>
          )}

          <div style={{ marginTop: '8px', color: '#94a3b8', fontSize: '10px' }}>
            Status: <span style={{ color: '#00e5ff' }}>{statusMessage}</span>
          </div>
        </div>
      );
    }

    // 7. Unified Chat & AI Sidekick Widget
    if (component === "chat") {
      return (
        <div style={{ height: '100%', backgroundColor: '#0f172a', display: 'flex', flexDirection: 'column', padding: '10px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px', paddingBottom: '4px', borderBottom: '1px solid #1e293b' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Bot size={14} color="#eab308" />
              <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#f8fafc' }}>Sidekick AI Co-Host</span>
            </div>
            <span style={{ fontSize: '9px', background: 'rgba(234,179,8,0.15)', color: '#eab308', padding: '1px 6px', borderRadius: '3px', border: '1px solid #eab308' }}>
              llama3.2 Active
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
            {chatMessages.map(msg => (
              <div key={msg.id} style={{ background: '#1e293b', borderRadius: '4px', padding: '6px 8px', fontSize: '11px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <strong style={{ color: msg.color || '#38bdf8' }}>{msg.user}</strong>
                    <span style={{ fontSize: '8px', background: msg.user.includes('Sidekick') ? '#eab308' : '#0284c7', color: '#000', padding: '1px 4px', borderRadius: '2px', fontWeight: 'bold' }}>
                      {msg.badge}
                    </span>
                  </div>
                  <span style={{ fontSize: '9px', color: '#64748b' }}>{msg.time}</span>
                </div>
                <span style={{ color: '#f1f5f9' }}>{msg.text}</span>
              </div>
            ))}
          </div>

          <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '6px' }}>
            <input 
              type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} 
              placeholder="Chat or ask Sidekick (!joke, !hype)..."
              style={{ flex: 1, background: '#020617', border: '1px solid #334155', color: '#fff', padding: '4px 8px', borderRadius: '3px', fontSize: '11px' }}
            />
            <button type="submit" style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '4px 10px', borderRadius: '3px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer' }}>
              <Send size={12} />
            </button>
          </form>
        </div>
      );
    }

    // 8. Performance Stats
    if (component === "stats") {
      const activeTargets = endpoints.filter(ep => ep.enabled && (ep.key || ep.name === 'Virtual Camera'));
      return (
        <div style={{ height: '100%', backgroundColor: '#0f172a', padding: '12px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '4px' }}>
            <span style={{ fontWeight: 'bold', color: '#f8fafc' }}>LIVE EGRESS TELEMETRY</span>
            <span style={{ color: isStreaming ? '#10b981' : '#64748b', fontWeight: 'bold' }}>
              {isStreaming ? '● STREAMING' : '○ OFFLINE'}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Source/Game:</span> 
            <span style={{ color: '#00e5ff', fontWeight: 'bold' }}>{telemetry.game_name}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Frame Rate:</span> 
            <span style={{ color: '#10b981', fontWeight: 'bold' }}>{telemetry.fps} FPS</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Bitrate:</span> 
            <span style={{ color: '#00e5ff', fontWeight: 'bold' }}>{telemetry.bitrate}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Encoder:</span> 
            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>{hardwareEncoder.toUpperCase()}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Dropped Frames:</span> 
            <span style={{ color: telemetry.dropped === "0" ? '#10b981' : '#ef4444', fontWeight: 'bold' }}>{telemetry.dropped}</span>
          </div>

          <div style={{ marginTop: '4px', paddingTop: '6px', borderTop: '1px solid #1e293b' }}>
            <div style={{ fontSize: '10px', color: '#64748b', fontWeight: 'bold', marginBottom: '4px' }}>ACTIVE PLATFORMS ({activeTargets.length})</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {activeTargets.map(ep => (
                <div key={ep.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#020617', padding: '3px 6px', borderRadius: '3px', fontSize: '10px' }}>
                  <span style={{ color: '#cbd5e1' }}>{ep.name}</span>
                  <span style={{ color: isStreaming ? '#10b981' : '#38bdf8' }}>
                    {isStreaming ? '● Sending' : '✓ Ready'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', backgroundColor: '#020617', overflow: 'hidden', position: 'relative' }}>
      {/* Top Studio Header Bar */}
      <div style={{ minHeight: '48px', backgroundColor: '#0f172a', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px', borderBottom: '1px solid #1e293b' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Monitor size={18} color="#00e5ff" />
          <span style={{ color: '#00e5ff', fontWeight: 'bold', fontSize: '15px' }}>AI-BS Broadcast Studio (OBS Engine)</span>
          <span style={{ fontSize: '11px', background: 'rgba(0,229,255,0.1)', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(0,229,255,0.2)' }}>
            NVENC Zero-Copy • 6-Track Audio Stems
          </span>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button 
            onClick={() => setShowGuideModal(true)}
            style={{ 
              backgroundColor: 'rgba(0, 229, 255, 0.1)', 
              color: '#00e5ff', 
              border: '1px solid rgba(0, 229, 255, 0.4)', 
              padding: '6px 12px', 
              borderRadius: '4px', 
              fontWeight: 'bold', 
              fontSize: '11px', 
              cursor: 'pointer', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '5px',
              boxShadow: '0 0 10px rgba(0,229,255,0.15)'
            }}
          >
            <BookOpen size={13} /> 📖 Operator Guide
          </button>

          <button 
            onClick={() => setShowSettingsModal(true)}
            style={{ backgroundColor: '#1e293b', color: '#38bdf8', border: '1px solid #38bdf8', padding: '6px 12px', borderRadius: '4px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px' }}
          >
            <SlidersHorizontal size={13} /> Source & OBS Settings
          </button>

          <button 
            onClick={panicStop} 
            style={{ backgroundColor: '#dc2626', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer' }}
          >
            🚨 PANIC STOP
          </button>
          
          <button 
            onClick={isStreaming ? stopStream : startStream}
            style={{ 
              backgroundColor: isStreaming ? '#475569' : '#00e5ff', 
              color: isStreaming ? '#fff' : '#000', 
              border: 'none', padding: '6px 20px', borderRadius: '4px', 
              fontWeight: 'bold', fontSize: '12px', cursor: 'pointer',
              boxShadow: isStreaming ? 'none' : '0 0 12px rgba(0,229,255,0.4)'
            }}
          >
            {isStreaming ? 'STOP STREAMING' : 'START STREAMING'}
          </button>
        </div>
      </div>

      {/* Dockable Workspace Layout */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <Layout model={model} factory={factory} />
      </div>

      {/* ========================================================================= */}
      {/* ⚙️ FULL OBS-STYLE SETTINGS & CODEC CONFIGURATOR MODAL                       */}
      {/* ========================================================================= */}
      {showSettingsModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 9999,
          backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(8px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            width: '820px', maxHeight: '88vh', backgroundColor: '#0f172a',
            border: '1px solid #38bdf8', borderRadius: '12px',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 25px 50px rgba(0,0,0,0.9)'
          }}>
            {/* Modal Header */}
            <div style={{ padding: '16px 20px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <SlidersHorizontal size={20} color="#00e5ff" />
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '16px' }}>Master OBS-Style Broadcast & Codec Settings</h3>
              </div>
              <button onClick={() => setShowSettingsModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}>
                <X size={20} />
              </button>
            </div>

            {/* Modal Navigation Tabs */}
            <div style={{ display: 'flex', background: '#111827', borderBottom: '1px solid #1e293b', overflowX: 'auto' }}>
              {[
                { key: 'video', label: '📹 Video & Canvas', icon: Video },
                { key: 'encoder', label: '⚡ Codecs & AV1/NVENC', icon: Cpu },
                { key: 'audio', label: '🎙️ 6-Track Stems', icon: Mic },
                { key: 'twitch', label: '🔴 Twitch & Sidekick', icon: Bot },
                { key: 'hotkeys', label: '⌨️ Global Hotkeys', icon: Key },
                { key: 'guide', label: '📖 Operator Guide', icon: BookOpen }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => {
                    if (tab.key === 'guide') {
                      setShowSettingsModal(false);
                      setShowGuideModal(true);
                    } else {
                      setActiveSettingsTab(tab.key);
                    }
                  }}
                  style={{
                    flex: 1, padding: '10px 14px', background: activeSettingsTab === tab.key ? '#0f172a' : 'transparent',
                    border: 'none', borderBottom: activeSettingsTab === tab.key ? '2px solid #00e5ff' : '2px solid transparent',
                    color: tab.key === 'guide' ? '#00e5ff' : (activeSettingsTab === tab.key ? '#00e5ff' : '#94a3b8'),
                    fontWeight: activeSettingsTab === tab.key ? 'bold' : 'normal',
                    cursor: 'pointer', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', whiteSpace: 'nowrap'
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              
              {/* Tab 1: Video & Canvas */}
              {activeSettingsTab === 'video' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '6px' }}>
                      Primary Hardware Camera / Capture Card
                    </label>
                    <select
                      value={selectedVideoDeviceId}
                      onChange={(e) => {
                        setSelectedVideoDeviceId(e.target.value);
                        if (webcamStream) handleToggleWebcam(e.target.value);
                      }}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                    >
                      {videoDevices.length === 0 ? (
                        <option value="">Default Web Camera / DirectShow</option>
                      ) : (
                        videoDevices.map(d => (
                          <option key={d.deviceId} value={d.deviceId}>{d.label}</option>
                        ))
                      )}
                    </select>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1', marginBottom: '6px' }}>
                        Base Canvas Resolution
                      </label>
                      <select
                        value={videoResolution}
                        onChange={(e) => setVideoResolution(e.target.value)}
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="1920x1080">1080p Full HD (1920 x 1080 - 16:9)</option>
                        <option value="2560x1440">1440p 2K QHD (2560 x 1440 - 16:9)</option>
                        <option value="3840x2160">4K Ultra HD (3840 x 2160 - 16:9)</option>
                        <option value="1080x1920">1080x1920 Vertical (9:16 TikTok / Shorts)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1', marginBottom: '6px' }}>
                        Target Framerate (FPS)
                      </label>
                      <select
                        value={videoFramerate}
                        onChange={(e) => setVideoFramerate(e.target.value)}
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="60">60 FPS (Ultra Smooth)</option>
                        <option value="30">30 FPS (Standard)</option>
                        <option value="24">24 FPS (Cinematic 24p)</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8' }}>
                        Video Output Bitrate
                      </label>
                      <span style={{ fontSize: '11px', color: '#00e5ff', fontWeight: 'bold' }}>
                        {videoBitrate.replace('k', '')} kbps
                      </span>
                    </div>
                    <select
                      value={videoBitrate}
                      onChange={(e) => setVideoBitrate(e.target.value)}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                    >
                      <option value="2500k">2,500 kbps (720p 30 FPS / Low Bandwidth)</option>
                      <option value="4000k">4,000 kbps (720p 60 FPS / 1080p 30 FPS)</option>
                      <option value="6000k">6,000 kbps (1080p 60 FPS - Recommended for FB/Twitch)</option>
                      <option value="8000k">8,000 kbps (1080p 60 FPS - High Quality Gaming)</option>
                      <option value="10000k">10,000 kbps (1440p 2K Broadcast)</option>
                      <option value="15000k">15,000 kbps (1440p High / 4K YouTube)</option>
                      <option value="25000k">25,000 kbps (4K Ultra Master)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Tab 2: Codecs & NVENC AV1 */}
              {activeSettingsTab === 'encoder' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '6px' }}>
                        Video Hardware Codec
                      </label>
                      <select
                        value={hardwareEncoder}
                        onChange={(e) => setHardwareEncoder(e.target.value)}
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="h264_nvenc">NVIDIA NVENC H.264 (RTX GPU Low Latency)</option>
                        <option value="av1_nvenc">NVIDIA NVENC AV1 (40% Higher Bandwidth Efficiency)</option>
                        <option value="hevc_nvenc">NVIDIA NVENC HEVC / H.265 (4K Master)</option>
                        <option value="h264_qsv">Intel QuickSync (QSV)</option>
                        <option value="h264_amf">AMD AMF Hardware Encoder</option>
                        <option value="libx264">Software x264 (CPU)</option>
                      </select>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '6px' }}>
                        Encoder Quality Preset
                      </label>
                      <select
                        value={encoderPreset}
                        onChange={(e) => setEncoderPreset(e.target.value)}
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="p5">P5: Slow (Good Quality - Recommended)</option>
                        <option value="p4">P4: Medium (Default Low Latency)</option>
                        <option value="p6">P6: Slower (Better Quality)</option>
                        <option value="p7">P7: Slowest (Highest Quality)</option>
                        <option value="p1">P1: Fastest (Lowest Latency)</option>
                      </select>
                    </div>
                  </div>

                  {/* Bitrate Configuration */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '12px', background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#00e5ff' }}>
                          Video Stream Bitrate
                        </label>
                        <span style={{ fontSize: '11px', color: '#38bdf8', fontWeight: 'bold', background: '#0f172a', padding: '2px 8px', borderRadius: '4px', border: '1px solid #0284c7' }}>
                          {videoBitrate.replace('k', '')} kbps
                        </span>
                      </div>
                      <select
                        value={videoBitrate}
                        onChange={(e) => setVideoBitrate(e.target.value)}
                        style={{ width: '100%', background: '#090d16', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="2500k">2,500 kbps (720p 30 FPS / Low Bandwidth)</option>
                        <option value="4000k">4,000 kbps (720p 60 FPS / 1080p 30 FPS)</option>
                        <option value="6000k">6,000 kbps (1080p 60 FPS - Recommended for FB/Twitch)</option>
                        <option value="8000k">8,000 kbps (1080p 60 FPS - High Detail Gaming)</option>
                        <option value="10000k">10,000 kbps (1440p 2K Broadcast)</option>
                        <option value="15000k">15,000 kbps (1440p High / 4K YouTube)</option>
                        <option value="25000k">25,000 kbps (4K Ultra Master Stream)</option>
                      </select>
                      <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <input 
                          type="range" 
                          min="1000" 
                          max="25000" 
                          step="500"
                          value={parseInt(videoBitrate.replace('k', ''), 10) || 6000}
                          onChange={(e) => setVideoBitrate(`${e.target.value}k`)}
                          style={{ flex: 1, accentColor: '#00e5ff', cursor: 'pointer' }}
                        />
                        <span style={{ fontSize: '10px', color: '#64748b' }}>Custom Slider</span>
                      </div>
                    </div>

                    <div>
                      <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1', marginBottom: '6px' }}>
                        Audio Bitrate (AAC Stereo)
                      </label>
                      <select
                        value={audioBitrate}
                        onChange={(e) => setAudioBitrate(e.target.value)}
                        style={{ width: '100%', background: '#090d16', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                      >
                        <option value="128k">128 kbps (Standard Quality)</option>
                        <option value="160k">160 kbps (High Quality - Recommended)</option>
                        <option value="192k">192 kbps (Pristine High-Fidelity)</option>
                        <option value="320k">320 kbps (Studio Master Audio)</option>
                      </select>
                      <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '8px', lineHeight: '1.4' }}>
                        💡 <strong>Streaming Tip:</strong> Facebook Live & Twitch accept 4,000–8,000 kbps for smooth 1080p60 gameplay.
                      </div>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1', marginBottom: '6px' }}>
                      Local Recording Format
                    </label>
                    <select
                      value={recordingFormat}
                      onChange={(e) => setRecordingFormat(e.target.value)}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                    >
                      <option value="hybrid_mp4">Hybrid MP4 (.mp4 - Crash Resilient Fragmented MP4)</option>
                      <option value="mkv">Matroska Multi-Track (.mkv)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* Tab 3: 6-Track Isolated Audio Stems */}
              {activeSettingsTab === 'audio' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                    <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '6px' }}>6-Track Isolated Stem Recording Map</div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px', color: '#cbd5e1' }}>
                      <div>• <strong>Track 1:</strong> Master Stream Mix (All audio)</div>
                      <div>• <strong>Track 2:</strong> Clean Microphone Stems</div>
                      <div>• <strong>Track 3:</strong> Desktop / Game WASAPI Audio</div>
                      <div>• <strong>Track 4:</strong> In-App FL Studio DAW Stems</div>
                      <div>• <strong>Track 5:</strong> Discord / Remote WebRTC Guests</div>
                      <div>• <strong>Track 6:</strong> AI Sidekick Co-Host Voice Output</div>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#cbd5e1', marginBottom: '6px' }}>
                      Primary Microphone Input
                    </label>
                    <select
                      value={selectedAudioInputId}
                      onChange={(e) => setSelectedAudioInputId(e.target.value)}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#f8fafc', padding: '8px 10px', borderRadius: '6px', fontSize: '12px' }}
                    >
                      {audioInputDevices.map(d => (
                        <option key={d.deviceId} value={d.deviceId}>{d.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              {/* Tab 4: Twitch & Sidekick Bot */}
              {activeSettingsTab === 'twitch' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#9333ea' }}>Twitch Chat & Bot Integration</div>
                      <div style={{ fontSize: '10px', color: '#94a3b8' }}>Live IRC WebSocket + Sidekick Co-Host Ingest</div>
                    </div>
                    <button 
                      onClick={handleConnectTwitch}
                      style={{ background: '#9333ea', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: '4px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer' }}
                    >
                      Login with Twitch
                    </button>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px' }}>Twitch Channel Name</label>
                      <input 
                        type="text" value={twitchChannel} onChange={(e) => setTwitchChannel(e.target.value)} 
                        placeholder="e.g. brettstehouwer"
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 8px', borderRadius: '4px', fontSize: '11px' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '11px', color: '#cbd5e1', marginBottom: '4px' }}>Twitch Client ID</label>
                      <input 
                        type="text" value={twitchClientId} onChange={(e) => setTwitchClientId(e.target.value)} 
                        placeholder="Paste Client ID"
                        style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 8px', borderRadius: '4px', fontSize: '11px' }}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 5: Global Hotkeys */}
              {activeSettingsTab === 'hotkeys' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8' }}>In-Game Global Keybindings</div>
                  {[
                    { action: 'Start / Stop Streaming', key: 'Ctrl + Shift + S' },
                    { action: 'Start / Stop Recording', key: 'Ctrl + Shift + R' },
                    { action: 'Mute / Unmute Microphone', key: 'Ctrl + Shift + M' },
                    { action: 'Toggle In-Game Transparent Chat Overlay', key: 'Ctrl + Shift + O' },
                    { action: 'Trigger Sidekick AI Joke / Hype', key: 'Ctrl + Shift + J' }
                  ].map((hk, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#020617', padding: '8px 12px', borderRadius: '4px', border: '1px solid #1e293b', fontSize: '11px' }}>
                      <span style={{ color: '#f8fafc' }}>{hk.action}</span>
                      <kbd style={{ background: '#1e293b', border: '1px solid #38bdf8', color: '#38bdf8', padding: '2px 8px', borderRadius: '4px', fontWeight: 'bold' }}>{hk.key}</kbd>
                    </div>
                  ))}
                </div>
              )}

            </div>

            {/* Modal Footer */}
            <div style={{ padding: '14px 20px', background: '#090d16', borderTop: '1px solid #1e293b', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setShowSettingsModal(false)}
                style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '8px 20px', borderRadius: '6px', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}
              >
                Apply & Save OBS Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ➕ Add Source Modal */}
      {showAddSourceModal && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: '600px', backgroundColor: '#0f172a', border: '1px solid #00e5ff', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 0 30px rgba(0, 229, 255, 0.25)' }}>
            <div style={{ padding: '14px 18px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '14px', fontWeight: 'bold' }}>Add Source / Streamlabs Overlay</h3>
              <button onClick={() => setShowAddSourceModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><X size={18} /></button>
            </div>
            <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {[
                { type: 'screen', label: '🖥️ Display / Screen Capture', name: 'Desktop Display' },
                { type: 'window', label: '🎮 Game / App Window', name: 'Game Window' },
                { type: 'cam', label: '📷 Video Capture Device', name: 'Webcam Link' },
                { type: 'overlay_frame', label: '🎨 Streamlabs Cam Frame (Neon Border)', name: 'Neon Cam Frame', color: '#00e5ff', borderWidth: 4, labelText: 'PRO CAM' },
                { type: 'ticker', label: '⭐ Stream Ticker / Recent Sub Banner', name: 'Stream Sub Ticker', color: '#00e5ff', recentSub: 'Brett (12 Mo)', latestFollower: 'ApexGamer99', topDonor: 'Julie ($100)' },
                { type: 'alert_box', label: '🔔 Live Stream Alert Box', name: 'Subscriber Alert Box', activeAlert: false, alertMessage: 'User123 subscribed!' },
                { type: 'image', label: '🖼️ Custom Image / PNG Watermark', name: 'Stream Logo PNG' },
                { type: 'browser_url', label: '🌐 Custom Browser Source URL', name: 'Chat Widget URL' },
                { type: 'mic', label: '🎙️ Audio Hardware Input', name: 'Hardware Mic' },
                { type: 'daw', label: '🎵 DAW Master Stems', name: 'DAW Stems' }
              ].map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSources(prev => [...prev, { 
                      id: `s_${Date.now()}`, 
                      name: item.name, 
                      type: item.type, 
                      enabled: true, 
                      active: true, 
                      color: item.color || '#00e5ff',
                      borderWidth: item.borderWidth || 4,
                      label: item.labelText || 'PRO CAM',
                      recentSub: item.recentSub || '',
                      latestFollower: item.latestFollower || '',
                      topDonor: item.topDonor || '',
                      opacity: 100, 
                      volume: 80 
                    }]);
                    setShowAddSourceModal(false);
                  }}
                  style={{ background: '#020617', border: '1px solid #1e293b', borderRadius: '6px', padding: '10px', color: '#fff', textAlign: 'left', cursor: 'pointer', transition: 'all 0.15s ease' }}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 🎨 STREAMLABS OVERLAY DESIGNER MODAL                                        */}
      {/* ========================================================================= */}
      {showOverlayDesigner && editingOverlay && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 10000, backgroundColor: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: '560px', backgroundColor: '#0f172a', border: '1px solid #00e5ff', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 0 35px rgba(0, 229, 255, 0.3)' }}>
            <div style={{ padding: '14px 18px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} color="#00e5ff" />
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '14px', fontWeight: 'bold' }}>Streamlabs Overlay & Layer Options</h3>
              </div>
              <button onClick={() => setShowOverlayDesigner(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><X size={18} /></button>
            </div>

            <div style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px', color: '#cbd5e1', fontSize: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '4px' }}>Source Name</label>
                <input 
                  type="text" 
                  value={editingOverlay.name || ''} 
                  onChange={(e) => setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, name: e.target.value } : s))}
                  style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 10px', borderRadius: '4px', fontSize: '12px' }}
                />
              </div>

              {/* Theme Color Selector */}
              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '6px' }}>Neon Theme Color</label>
                <div style={{ display: 'flex', gap: '10px' }}>
                  {[
                    { label: 'Cyan Glow', color: '#00e5ff' },
                    { label: 'Cyberpunk Magenta', color: '#d92bb8' },
                    { label: 'Golden Elite', color: '#f59e0b' },
                    { label: 'Emerald Pro', color: '#10b981' }
                  ].map(t => (
                    <button
                      key={t.color}
                      onClick={() => setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, color: t.color } : s))}
                      style={{
                        background: t.color,
                        color: '#000',
                        border: editingOverlay.color === t.color ? '2px solid #fff' : 'none',
                        padding: '6px 12px', borderRadius: '4px', fontWeight: 'bold', fontSize: '10px', cursor: 'pointer'
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Cam Frame Specific Settings */}
              {(editingOverlay.type === 'overlay_frame' || editingOverlay.type === 'cam_frame') && (
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '4px' }}>Cam Frame Title Text</label>
                  <input 
                    type="text" 
                    value={editingOverlay.label || 'PRO CAM'} 
                    onChange={(e) => setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, label: e.target.value } : s))}
                    placeholder="e.g. CALL OF DUTY PRO"
                    style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 10px', borderRadius: '4px', fontSize: '12px' }}
                  />
                </div>
              )}

              {/* Ticker Banner Specific Settings */}
              {editingOverlay.type === 'ticker' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '10px', color: '#94a3b8' }}>Recent Subscriber Text</label>
                    <input 
                      type="text" value={editingOverlay.recentSub || 'Brett (12 Mo)'} 
                      onChange={(e) => setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, recentSub: e.target.value } : s))}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '5px 8px', borderRadius: '4px', fontSize: '11px' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '10px', color: '#94a3b8' }}>Latest Follower</label>
                    <input 
                      type="text" value={editingOverlay.latestFollower || 'ApexGamer99'} 
                      onChange={(e) => setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, latestFollower: e.target.value } : s))}
                      style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '5px 8px', borderRadius: '4px', fontSize: '11px' }}
                    />
                  </div>
                </div>
              )}

              {/* Alert Box Specific Settings */}
              {editingOverlay.type === 'alert_box' && (
                <div>
                  <button 
                    onClick={() => {
                      setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, activeAlert: true } : s));
                      setTimeout(() => {
                        setSources(prev => prev.map(s => s.id === editingOverlay.id ? { ...s, activeAlert: false } : s));
                      }, 5000);
                    }}
                    style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '8px 16px', borderRadius: '6px', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer', width: '100%' }}
                  >
                    🎉 Trigger Test Subscriber Alert Animation (5s)
                  </button>
                </div>
              )}

            </div>

            <div style={{ padding: '12px 18px', background: '#090d16', borderTop: '1px solid #1e293b', display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                onClick={() => setShowOverlayDesigner(false)}
                style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '6px 18px', borderRadius: '4px', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}
              >
                Apply & Save Overlay Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 📖 INTERACTIVE OPERATOR GUIDE & WALKTHROUGH MODAL                          */}
      {/* ========================================================================= */}
      {showGuideModal && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 10000,
          backgroundColor: 'rgba(0, 0, 0, 0.85)', backdropFilter: 'blur(10px)',
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{
            width: '940px', height: '84vh', backgroundColor: '#0f172a',
            border: '1px solid #00e5ff', borderRadius: '12px',
            display: 'flex', flexDirection: 'column', overflow: 'hidden',
            boxShadow: '0 0 35px rgba(0, 229, 255, 0.25)'
          }}>
            {/* Guide Header */}
            <div style={{ padding: '14px 20px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BookOpen size={20} color="#00e5ff" />
                <div>
                  <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '15px', fontWeight: 'bold' }}>AI-BS Broadcast Studio Operator Guide</h3>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>Interactive walkthrough for all controls, docks, audio stems, and streaming workflows</div>
                </div>
              </div>
              <button onClick={() => setShowGuideModal(false)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}>
                <X size={20} />
              </button>
            </div>

            {/* Guide Body: Two-Column Split (Sidebar Navigation + Content Viewport) */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
              
              {/* Left Sidebar */}
              <div style={{ width: '230px', background: '#090d16', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', padding: '10px 8px', gap: '4px', overflowY: 'auto' }}>
                {[
                  { id: 'quickstart', label: '🚀 3-Step Quick Start', icon: Zap },
                  { id: 'monitors', label: '📹 Preview / Program', icon: Video },
                  { id: 'scenes', label: '🎛️ Scenes & Sources', icon: Layers },
                  { id: 'audio', label: '🎙️ 6-Track Audio Stems', icon: Mic },
                  { id: 'streaming', label: '📡 Multi-Stream & Ingests', icon: Radio },
                  { id: 'sidekick', label: '🤖 AI Sidekick & Twitch', icon: Bot },
                  { id: 'encoder', label: '⚡ NVENC Codecs & AV1', icon: Cpu },
                  { id: 'hotkeys', label: '⌨️ Global Hotkeys', icon: Key }
                ].map(item => (
                  <button
                    key={item.id}
                    onClick={() => setGuideActiveSection(item.id)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      background: guideActiveSection === item.id ? 'rgba(0, 229, 255, 0.15)' : 'transparent',
                      color: guideActiveSection === item.id ? '#00e5ff' : '#cbd5e1',
                      border: 'none',
                      borderLeft: guideActiveSection === item.id ? '3px solid #00e5ff' : '3px solid transparent',
                      borderRadius: '0 6px 6px 0',
                      textAlign: 'left',
                      fontSize: '12px',
                      fontWeight: guideActiveSection === item.id ? 'bold' : 'normal',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <span>{item.label}</span>
                    {guideActiveSection === item.id && <ChevronRight size={14} color="#00e5ff" />}
                  </button>
                ))}
              </div>

              {/* Right Content Area */}
              <div style={{ flex: 1, padding: '24px', overflowY: 'auto', backgroundColor: '#0f172a', color: '#e2e8f0', fontSize: '13px', lineHeight: '1.6' }}>
                
                {/* 1. Quick Start */}
                {guideActiveSection === 'quickstart' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      🚀 3-Step Quick Start to Go Live
                    </h2>
                    <p style={{ color: '#94a3b8' }}>Follow these three simple steps to start broadcasting with full hardware NVENC acceleration and multi-platform streaming:</p>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '16px' }}>
                      <div style={{ background: '#020617', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38bdf8', fontWeight: 'bold', fontSize: '14px', marginBottom: '4px' }}>
                          <span style={{ background: '#0284c7', color: '#000', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>STEP 1</span>
                          Stage Your Video Sources
                        </div>
                        <p style={{ margin: '4px 0', color: '#cbd5e1', fontSize: '12px' }}>
                          Click <strong>Capture Screen / Window</strong> on the top-left toolbar to capture your desktop or game, and click <strong>Enable Webcam</strong> to activate your camera. Switch between scenes (<code>[MAIN] Solo</code>, <code>[CAM] Studio</code>, <code>[GAME] Split</code>) to set up your layout.
                        </p>
                      </div>

                      <div style={{ background: '#020617', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#10b981', fontWeight: 'bold', fontSize: '14px', marginBottom: '4px' }}>
                          <span style={{ background: '#059669', color: '#000', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>STEP 2</span>
                          Verify Stream Targets & Test Ingests
                        </div>
                        <p style={{ margin: '4px 0', color: '#cbd5e1', fontSize: '12px' }}>
                          In the <strong>Stream Settings</strong> dock (top-right), check the platforms you want to broadcast to (Twitch, YouTube, Facebook, Kick) and paste your stream keys. Click <strong>Test All Ingests</strong> to run instantaneous socket reachability checks.
                        </p>
                      </div>

                      <div style={{ background: '#020617', border: '1px solid #1e293b', borderRadius: '8px', padding: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontWeight: 'bold', fontSize: '14px', marginBottom: '4px' }}>
                          <span style={{ background: '#d97706', color: '#000', padding: '2px 8px', borderRadius: '4px', fontSize: '11px' }}>STEP 3</span>
                          Click "START STREAMING"
                        </div>
                        <p style={{ margin: '4px 0', color: '#cbd5e1', fontSize: '12px' }}>
                          Hit the bright cyan <strong>START STREAMING</strong> button (or press <kbd style={{ background: '#1e293b', border: '1px solid #38bdf8', padding: '1px 5px', borderRadius: '3px', color: '#38bdf8' }}>Ctrl+Shift+S</kbd>). The daemon will initialize NVENC GPU encoding and begin multi-casting while isolating 6 audio stems locally!
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 2. Monitors */}
                {guideActiveSection === 'monitors' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      📹 Preview & Program Monitors
                    </h2>
                    <p style={{ color: '#cbd5e1' }}>The studio utilizes a professional dual-canvas OBS architecture:</p>
                    
                    <ul style={{ paddingLeft: '18px', color: '#cbd5e1', fontSize: '12px' }}>
                      <li style={{ marginBottom: '8px' }}><strong>Preview [Staging] Canvas:</strong> Lets you test angles, camera lighting, and framing before placing them on-air.</li>
                      <li style={{ marginBottom: '8px' }}><strong>Program [Master] Canvas:</strong> The live, composited video pixel buffer rendered at 60 FPS and piped into the NVENC encoder.</li>
                      <li style={{ marginBottom: '8px' }}><strong>16:9 Studio vs 9:16 Vertical:</strong> Toggle to swap from 1920x1080 horizontal (Twitch/YouTube) to 1080x1920 vertical with automatic intelligent center-cropping for TikTok Live and YouTube Shorts.</li>
                      <li style={{ marginBottom: '8px' }}><strong>Virtual Cam:</strong> Outputs the composited video feed directly to DirectShow, allowing Discord, Zoom, or TikTok Live Studio to see your broadcast as a webcam.</li>
                    </ul>
                  </div>
                )}

                {/* 3. Scenes */}
                {guideActiveSection === 'scenes' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      🎛️ Scenes & Sources Architecture
                    </h2>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '10px' }}>
                      <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                        <strong style={{ color: '#38bdf8' }}>[MAIN] Solo</strong>
                        <p style={{ fontSize: '11px', color: '#94a3b8', margin: '4px 0' }}>Fullscreen display of your primary desktop screen or active game.</p>
                      </div>
                      <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                        <strong style={{ color: '#38bdf8' }}>[CAM] Studio</strong>
                        <p style={{ fontSize: '11px', color: '#94a3b8', margin: '4px 0' }}>Picture-in-Picture mode placing your camera in the bottom-right corner over gameplay.</p>
                      </div>
                      <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                        <strong style={{ color: '#38bdf8' }}>[GAME] Split</strong>
                        <p style={{ fontSize: '11px', color: '#94a3b8', margin: '4px 0' }}>50/50 dual view placing gameplay on the left half and camera on the right half.</p>
                      </div>
                      <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                        <strong style={{ color: '#38bdf8' }}>+ Add Source</strong>
                        <p style={{ fontSize: '11px', color: '#94a3b8', margin: '4px 0' }}>Add new windows, hardware capture cards, DAW channels, or WebRTC feeds.</p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 4. Audio */}
                {guideActiveSection === 'audio' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      🎙️ 6-Track Isolated Audio Stem Architecture
                    </h2>
                    <p style={{ color: '#cbd5e1', fontSize: '12px' }}>AI-BS enforces a professional 6-track isolated stem routing model globally running at 48kHz low-latency buffers:</p>
                    
                    <div style={{ background: '#020617', padding: '12px', borderRadius: '8px', border: '1px solid #1e293b', marginTop: '10px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>• Track 1: Master Stream Output</span>
                          <span style={{ color: '#94a3b8' }}>Mixed stereo audio sent to Twitch, YouTube, & Facebook</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#10b981', fontWeight: 'bold' }}>• Track 2: Clean Microphone Stems</span>
                          <span style={{ color: '#94a3b8' }}>Isolated host voice (noise-suppressed)</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#f59e0b', fontWeight: 'bold' }}>• Track 3: Game / WASAPI Audio</span>
                          <span style={{ color: '#94a3b8' }}>Isolated system & in-game sound effects</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#a855f7', fontWeight: 'bold' }}>• Track 4: DAW Synthesizer Stems</span>
                          <span style={{ color: '#94a3b8' }}>Isolated in-app FL Studio & Tone.js instruments</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#ec4899', fontWeight: 'bold' }}>• Track 5: WebRTC / Discord Guests</span>
                          <span style={{ color: '#94a3b8' }}>Isolated remote interviewees</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span style={{ color: '#eab308', fontWeight: 'bold' }}>• Track 6: AI Sidekick Voice Output</span>
                          <span style={{ color: '#94a3b8' }}>Isolated local LLM text-to-speech audio</span>
                        </div>
                      </div>
                    </div>

                    <p style={{ color: '#94a3b8', fontSize: '11px', marginTop: '10px' }}>
                      <strong>Crash-Resilient Hybrid MP4:</strong> All 6 tracks are recorded into independent channels in your local recording file using <code>-movflags +faststart+frag_keyframe+empty_moov+default_base_moof</code> so your footage is never lost even if power drops.
                    </p>
                  </div>
                )}

                {/* 5. Streaming */}
                {guideActiveSection === 'streaming' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      📡 Multi-Platform Streaming & Ingest Probing
                    </h2>
                    <p style={{ color: '#cbd5e1', fontSize: '12px' }}>Broadcast simultaneously to Twitch, YouTube, Facebook Live, Kick, and custom RTMP destinations:</p>
                    
                    <ul style={{ paddingLeft: '18px', color: '#cbd5e1', fontSize: '12px' }}>
                      <li style={{ marginBottom: '8px' }}><strong>"Test All Ingests" Socket Diagnostics:</strong> Executes non-blocking TCP handshakes against platform ports (Twitch <code>1935</code>, YouTube <code>1935</code>, Facebook RTMPS <code>443</code>) and returns round-trip latency in milliseconds.</li>
                      <li style={{ marginBottom: '8px' }}><strong>Tee Muxer Resilience (<code>onfail=ignore</code>):</strong> If one platform drops connection or experiences network jitter, FFmpeg drops only that slave connection while keeping all other streams and your local recording alive.</li>
                      <li style={{ marginBottom: '8px' }}><strong>Twitch Helix Channel Verification:</strong> Automatically checks the Twitch Helix API to confirm whether Twitch has verified your live broadcast.</li>
                    </ul>
                  </div>
                )}

                {/* 6. Sidekick */}
                {guideActiveSection === 'sidekick' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      🤖 Local AI Sidekick Co-Host & Twitch Chat
                    </h2>
                    <p style={{ color: '#cbd5e1', fontSize: '12px' }}>The AI Sidekick is an autonomous AI co-host running locally on your GPU via Ollama (<code>llama3.2</code> on Port 8006):</p>
                    
                    <div style={{ background: '#020617', padding: '12px', borderRadius: '6px', border: '1px solid #1e293b', marginTop: '10px' }}>
                      <strong style={{ color: '#eab308' }}>Interactive Chat Commands:</strong>
                      <ul style={{ margin: '6px 0 0 0', paddingLeft: '16px', fontSize: '11px', color: '#cbd5e1' }}>
                        <li><code>!joke</code> (or <kbd>Ctrl+Shift+J</kbd>): Tells a gaming or situational joke to chat.</li>
                        <li><code>!hype</code>: Drops audience hype and celebration commentary.</li>
                        <li><code>!sentiment</code>: Analyzes recent chat energy and mood.</li>
                        <li>Type naturally in the chat box to ask questions or talk to the Sidekick directly.</li>
                      </ul>
                    </div>
                  </div>
                )}

                {/* 7. Encoder */}
                {guideActiveSection === 'encoder' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      ⚡ Hardware NVENC & Codec Presets
                    </h2>
                    <p style={{ color: '#cbd5e1', fontSize: '12px' }}>The broadcast daemon interfaces directly with NVIDIA GPU NVENC hardware encoders:</p>
                    
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', marginTop: '10px' }}>
                      <thead>
                        <tr style={{ background: '#020617', color: '#38bdf8', textAlign: 'left' }}>
                          <th style={{ padding: '6px', border: '1px solid #1e293b' }}>Codec</th>
                          <th style={{ padding: '6px', border: '1px solid #1e293b' }}>Recommended Preset</th>
                          <th style={{ padding: '6px', border: '1px solid #1e293b' }}>Best For</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}><code>h264_nvenc</code></td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>P5 (Slow / High Quality)</td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>Twitch, Facebook, & Universal RTMP</td>
                        </tr>
                        <tr>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}><code>av1_nvenc</code></td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>P5 (Slow)</td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>YouTube Live (40% Higher Compression Efficiency)</td>
                        </tr>
                        <tr>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}><code>hevc_nvenc</code></td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>P5 (Slow)</td>
                          <td style={{ padding: '6px', border: '1px solid #1e293b' }}>4K UHD Local Masters & High-Res Recording</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                )}

                {/* 8. Hotkeys */}
                {guideActiveSection === 'hotkeys' && (
                  <div>
                    <h2 style={{ color: '#00e5ff', marginTop: 0, fontSize: '18px', borderBottom: '1px solid #1e293b', paddingBottom: '8px' }}>
                      ⌨️ Global In-Game Keybindings
                    </h2>
                    <p style={{ color: '#cbd5e1', fontSize: '12px' }}>Control your stream without switching windows during live gameplay:</p>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                      {[
                        { key: 'Ctrl + Shift + S', action: 'Start / Stop Live Broadcast' },
                        { key: 'Ctrl + Shift + R', action: 'Start / Stop Local Recording' },
                        { key: 'Ctrl + Shift + M', action: 'Mute / Unmute Microphone' },
                        { key: 'Ctrl + Shift + O', action: 'Toggle Transparent Chat Desktop Overlay' },
                        { key: 'Ctrl + Shift + J', action: 'Trigger AI Sidekick Joke / Hype' }
                      ].map((hk, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: '#020617', padding: '10px 14px', borderRadius: '6px', border: '1px solid #1e293b' }}>
                          <span style={{ color: '#f8fafc', fontWeight: 'bold' }}>{hk.action}</span>
                          <kbd style={{ background: '#1e293b', border: '1px solid #00e5ff', color: '#00e5ff', padding: '3px 10px', borderRadius: '4px', fontWeight: 'bold', fontSize: '12px' }}>{hk.key}</kbd>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </div>

            {/* Guide Footer */}
            <div style={{ padding: '12px 20px', background: '#090d16', borderTop: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: '#64748b' }}>AI-BS Studio v5.147.0 • OBS Hardware Engine</span>
              <button 
                onClick={() => setShowGuideModal(false)}
                style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '7px 22px', borderRadius: '6px', fontWeight: 'bold', fontSize: '12px', cursor: 'pointer' }}
              >
                Got It, Let's Stream!
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ⚙️ Source Properties Modal */}
      {editingSource && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ width: '440px', backgroundColor: '#0f172a', border: '1px solid #38bdf8', borderRadius: '12px', overflow: 'hidden' }}>
            <div style={{ padding: '14px 18px', background: '#090d16', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '14px' }}>Source Properties: {editingSource.name}</h3>
              <button onClick={() => setEditingSource(null)} style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}><X size={18} /></button>
            </div>
            <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>Source Name</label>
                <input 
                  type="text" value={editingSource.name}
                  onChange={(e) => {
                    const val = e.target.value;
                    setEditingSource(prev => ({ ...prev, name: val }));
                    setSources(prev => prev.map(s => s.id === editingSource.id ? { ...s, name: val } : s));
                  }}
                  style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 8px', borderRadius: '4px', fontSize: '12px' }}
                />
              </div>

              {editingSource.type === 'window' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px', marginTop: '10px' }}>
                    <label style={{ fontSize: '11px', color: '#94a3b8' }}>Select Target Window</label>
                    <button onClick={fetchWindows} style={{ background: '#38bdf8', color: '#000', border: 'none', padding: '3px 8px', borderRadius: '3px', fontSize: '10px', cursor: 'pointer', fontWeight: 'bold' }}>Refresh List</button>
                  </div>
                  <select
                    value={editingSource.deviceId || ''}
                    onChange={(e) => {
                      const val = e.target.value;
                      setEditingSource(prev => ({ ...prev, deviceId: val }));
                      setSources(prev => prev.map(s => s.id === editingSource.id ? { ...s, deviceId: val } : s));
                    }}
                    style={{ width: '100%', background: '#020617', border: '1px solid #334155', color: '#fff', padding: '6px 8px', borderRadius: '4px', fontSize: '12px' }}
                  >
                    <option value="">{detectedActiveGame ? `🎯 Auto-Detect (Active: ${detectedActiveGame.game_name || detectedActiveGame.title})` : '-- Auto-Detect Active Game --'}</option>
                    {windowList.map((w, idx) => {
                      const title = typeof w === 'object' ? (w.title || w.name) : w;
                      const isGame = typeof w === 'object' ? w.is_game : false;
                      const proc = typeof w === 'object' ? w.process_name : '';
                      return (
                        <option key={idx} value={title}>
                          {isGame ? `🎮 ${w.game_name || title} (${proc})` : `🪟 ${title}`}
                        </option>
                      );
                    })}
                  </select>
                </div>
              )}
            </div>
            <div style={{ padding: '12px 18px', background: '#090d16', borderTop: '1px solid #1e293b', display: 'flex', justifyContent: 'flex-end' }}>
              <button onClick={() => setEditingSource(null)} style={{ background: '#00e5ff', color: '#000', border: 'none', padding: '6px 16px', borderRadius: '4px', fontWeight: 'bold', fontSize: '11px', cursor: 'pointer' }}>Done</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BroadcastStudio;





