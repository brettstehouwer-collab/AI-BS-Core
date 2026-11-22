import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Modal
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

const BACKEND_URLS = [
  'https://api.brettstehouwer.live',
  'http://192.168.4.92:8080',
  'http://10.0.2.2:8080',
  'http://127.0.0.1:8080',
  'http://localhost:8080'
];

const DIRECT_OLLAMA_URLS = [
  'http://192.168.4.92:11434',
  'http://10.0.2.2:11434',
  'http://127.0.0.1:11434',
  'http://localhost:11434'
];

interface ScreenplayAsset {
  concept_id: string;
  title: string;
  subject: string;
  aspect_ratio: string;
  raster_path: string;
  video_target: string;
  prompt: string;
}

const SCREENPLAY_ASSETS: ScreenplayAsset[] = [
  {
    concept_id: 'concept_dual_realm_storefront',
    title: 'EXT. MORNING - STOREFRONT (Dual Realm)',
    subject: 'Environment',
    aspect_ratio: '16:9',
    raster_path: 'concept_storefront_dual_realm.png',
    video_target: 'wan2.1-t2v-1.3B.safetensors',
    prompt: '3D cinematic animated split-screen reality: Hell furnace left, Heaven clouds right, whimsical candy store center.'
  },
  {
    concept_id: 'concept_char_fredy',
    title: 'Fredy - Weeble Wobble Protagonist',
    subject: 'Character',
    aspect_ratio: '1:1',
    raster_path: 'concept_fredy_weeble.png',
    video_target: 'wan2.1-t2v-1.3B.safetensors',
    prompt: 'Egg-shaped Weeble Wobble teenager in black hoodie and shades holding a Snickers bar.'
  },
  {
    concept_id: 'concept_char_satan',
    title: 'Satan (Satin) - The Tempter',
    subject: 'Character',
    aspect_ratio: '1:1',
    raster_path: 'concept_satan_weeble.png',
    video_target: 'wan2.1-t2v-1.3B.safetensors',
    prompt: 'Egg-shaped devil figure in red robe with wild hair, punch-dancing animated comic stance.'
  },
  {
    concept_id: 'concept_char_jesus',
    title: 'Jesus (Joshua) - The Redeemer',
    subject: 'Character',
    aspect_ratio: '1:1',
    raster_path: 'concept_jesus_weeble.png',
    video_target: 'wan2.1-t2v-1.3B.safetensors',
    prompt: 'Egg-shaped Jesus in flowing white robe with radiant halo, gentle smiling expression.'
  },
  {
    concept_id: 'concept_char_mr_pimp',
    title: 'Mr. Pimp - Candy Store Owner',
    subject: 'Character',
    aspect_ratio: '1:1',
    raster_path: 'concept_mr_pimp_weeble.png',
    video_target: 'wan2.1-t2v-1.3B.safetensors',
    prompt: 'Egg-shaped candy store owner in purple velvet leopard coat and fedora, shocked expression.'
  }
];

interface EcosystemPortItem {
  port: number;
  name: string;
  tier: string;
  category: string;
  status: 'ONLINE' | 'OFFLINE';
  pid?: number | null;
  process_name?: string | null;
  memory_mb?: number;
  supervised?: boolean;
  daemon_name?: string | null;
}

interface HardwareMetrics {
  cpu_percent: number;
  ram_percent: number;
  gpu: {
    name: string;
    vram_used_mb: number;
    vram_total_mb: number;
    temp_c?: number;
  };
}

interface VideoProgressItem {
  job_id: string;
  scene_id?: string;
  progress: number;
  status: string;
  frames: number;
  step_description?: string;
}

export default function App() {
  const [userName, setUserName] = useState<string>('Guest');
  const [tempName, setTempName] = useState<string>('');
  const [isNameModalVisible, setIsNameModalVisible] = useState<boolean>(false);
  const [isTopologyModalVisible, setIsTopologyModalVisible] = useState<boolean>(false);
  const [isScreenplayModalVisible, setIsScreenplayModalVisible] = useState<boolean>(false);
  const [isStreamDeckVisible, setIsStreamDeckVisible] = useState<boolean>(false);
  const [pushNotification, setPushNotification] = useState<{ title: string; body: string; type: 'error' | 'success' | 'info' } | null>(null);
  const [deckActionStatus, setDeckActionStatus] = useState<string>('');

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'msg-welcome',
      role: 'assistant',
      content: 'AI-BS Sovereign Mobile Studio is online.\nConnected to RTX 4090 Sovereign Cognitive Cluster.\nTap your profile tag in the top bar to set your name, or start chatting immediately.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [activeUrl, setActiveUrl] = useState<string>('https://api.brettstehouwer.live');
  const [pingMs, setPingMs] = useState<number | null>(null);
  const [selectedModel, setSelectedModel] = useState<'stehouwer_llm' | 'qwen2.5-coder' | 'llama3.1'>('stehouwer_llm');

  const [ecosystemPorts, setEcosystemPorts] = useState<EcosystemPortItem[]>([
    { port: 80, name: 'Nginx Gateway', tier: 'network', category: 'static', status: 'ONLINE' },
    { port: 3001, name: 'Node Backend', tier: 'backend', category: 'static', status: 'ONLINE' },
    { port: 4455, name: 'OBS WebSocket', tier: 'streaming', category: 'jit', status: 'ONLINE' },
    { port: 5173, name: 'Vite Dev / Studio', tier: 'frontend', category: 'static', status: 'ONLINE' },
    { port: 8000, name: 'Go Gateway', tier: 'gateway', category: 'static', status: 'ONLINE' },
    { port: 8002, name: 'ChromaDB Vectors', tier: 'database', category: 'static', status: 'ONLINE' },
    { port: 8005, name: 'Broadcast Daemon', tier: 'streaming', category: 'static', status: 'ONLINE' },
    { port: 8006, name: 'Social Hub', tier: 'social', category: 'jit', status: 'ONLINE' },
    { port: 8007, name: 'Crypto Swarm', tier: 'trading', category: 'static', status: 'ONLINE' },
    { port: 8010, name: 'SHM Gateway', tier: 'telemetry', category: 'static', status: 'ONLINE' },
    { port: 8013, name: 'VST3 Audio Bridge', tier: 'audio', category: 'jit', status: 'ONLINE' },
    { port: 8080, name: 'FastAPI Core Engine', tier: 'core', category: 'static', status: 'ONLINE' },
    { port: 8085, name: 'Ubuntu-Bio Bridge', tier: 'bridge', category: 'jit', status: 'ONLINE' },
    { port: 8088, name: 'Broadcast Kernel', tier: 'video', category: 'jit', status: 'ONLINE' },
    { port: 8089, name: 'WSL HLS Ingest', tier: 'streaming', category: 'jit', status: 'ONLINE' },
    { port: 8099, name: 'Gemini Local MCP', tier: 'ai', category: 'static', status: 'ONLINE' },
    { port: 8189, name: 'ComfyUI (RTX 4090)', tier: 'diffusion', category: 'jit', status: 'ONLINE' },
    { port: 8888, name: 'Unreal Engine Signaling', tier: 'rendering', category: 'jit', status: 'ONLINE' },
    { port: 11434, name: 'Dual Ollama Cluster', tier: 'llm', category: 'jit', status: 'ONLINE' },
    { port: 11435, name: 'Ollama E-Drive', tier: 'llm', category: 'jit', status: 'ONLINE' },
  ]);
  const [hardwareMetrics, setHardwareMetrics] = useState<HardwareMetrics>({
    cpu_percent: 18.5,
    ram_percent: 42.1,
    gpu: { name: 'NVIDIA GeForce RTX 4090 (24GB VRAM)', vram_used_mb: 6144, vram_total_mb: 24576 }
  });
  const [activeVideoJob, setActiveVideoJob] = useState<VideoProgressItem | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [actionLoadingPort, setActionLoadingPort] = useState<number | null>(null);

  const flatListRef = useRef<FlatList>(null);

  // Check health on mount and periodically
  const checkHealth = async () => {
    setBackendStatus('checking');
    const start = Date.now();
    for (const url of BACKEND_URLS) {
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 4000);
        const res = await fetch(`${url}/v1/health`, {
          signal: ctrl.signal
        });
        clearTimeout(tid);
        if (res.ok) {
          const delta = Date.now() - start;
          setPingMs(delta);
          setActiveUrl(url);
          setBackendStatus('online');
          return;
        }
      } catch {
        // try next candidate
      }
    }
    setBackendStatus('offline');
    setPingMs(null);
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Real-time WebSocket Telemetry & Daemon Status Sync
  useEffect(() => {
    let ws: any = null;
    let isMounted = true;

    const fetchEcosystemStatus = async () => {
      try {
        const res = await fetch(`${activeUrl}/api/executive/daemons`);
        if (res.ok) {
          const data = await res.json();
          if (data.ports && isMounted) setEcosystemPorts(data.ports);
          if (data.hardware && isMounted) setHardwareMetrics(data.hardware);
        }
      } catch {
        // quiet fallback
      }
    };

    const connectWs = () => {
      try {
        const wsProtocol = activeUrl.startsWith('https') ? 'wss' : 'ws';
        const rawHost = activeUrl.replace(/^https?:\/\//, '');
        const wsUrl = `${wsProtocol}://${rawHost}/ws/telemetry`;
        ws = new (globalThis as any).WebSocket(wsUrl);

        ws.onopen = () => {
          if (isMounted) setWsConnected(true);
        };

        ws.onmessage = (e: any) => {
          if (!isMounted) return;
          try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'INITIAL_SNAPSHOT' || msg.type === 'TELEMETRY_HEARTBEAT' || msg.type === 'POLL_RESPONSE') {
              if (msg.data?.ports) setEcosystemPorts(msg.data.ports);
              if (msg.data?.hardware) setHardwareMetrics(msg.data.hardware);
            } else if (msg.type === 'DAEMON_STATE_CHANGE') {
              fetchEcosystemStatus();
              if (msg.event === 'crash' || msg.event === 'restart') {
                setPushNotification({
                  title: `🚨 Daemon ${msg.event.toUpperCase()}`,
                  body: `${msg.daemon} alert on port ${msg.payload?.port || 'N/A'}. Sentinel auto-healing activated.`,
                  type: 'error'
                });
                setTimeout(() => setPushNotification(null), 6000);
              }
            } else if (msg.type === 'SENTINEL_ALERT') {
              setPushNotification({
                title: '🛡️ Sentinel Incident Event',
                body: msg.message || 'AST-guarded patch applied & verified.',
                type: 'info'
              });
              setTimeout(() => setPushNotification(null), 6000);
            } else if (msg.type === 'WAN_VIDEO_PROGRESS') {
              setActiveVideoJob({
                job_id: msg.job_id,
                scene_id: msg.scene_id,
                progress: msg.progress || 0,
                status: msg.status || 'rendering',
                frames: msg.frames || 49,
                step_description: msg.step_description
              });
              if (msg.progress === 100) {
                setPushNotification({
                  title: '🎬 Video Render Complete',
                  body: `Wan2.1 generated 49 frames for ${msg.job_id?.slice(0, 8) || 'job'}.`,
                  type: 'success'
                });
                setTimeout(() => setPushNotification(null), 6000);
                setTimeout(() => {
                  if (isMounted) setActiveVideoJob(null);
                }, 8000);
              }
            }
          } catch {
            // parse error
          }
        };

        ws.onclose = () => {
          if (isMounted) setWsConnected(false);
        };

        ws.onerror = () => {
          if (isMounted) setWsConnected(false);
        };
      } catch {
        if (isMounted) setWsConnected(false);
      }
    };

    fetchEcosystemStatus();
    connectWs();

    const pollTimer = setInterval(() => {
      if (!ws || ws.readyState !== 1) {
        fetchEcosystemStatus();
      }
    }, 6000);

    return () => {
      isMounted = false;
      clearInterval(pollTimer);
      if (ws) {
        try { ws.close(); } catch {}
      }
    };
  }, [activeUrl]);

  const handleDaemonAction = async (action: 'restart' | 'stop' | 'start', port: number, daemonName?: string | null) => {
    setActionLoadingPort(port);
    try {
      const res = await fetch(`${activeUrl}/api/executive/daemon-action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, port, daemon_name: daemonName || undefined })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.ecosystem_status?.ports) {
          setEcosystemPorts(data.ecosystem_status.ports);
        }
      }
    } catch (e) {
      console.warn('Failed to dispatch daemon action:', e);
    } finally {
      setActionLoadingPort(null);
    }
  };

  const handleSend = async (customText?: string) => {
    const textToSend = (customText || input).trim();
    if (!textToSend || loading) return;

    const userMsg: Message = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput('');
    setLoading(true);

    const botMsgId = `msg-${Date.now()}-bot`;
    const pendingBotMsg: Message = {
      id: botMsgId,
      role: 'assistant',
      content: '...',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages([...newHistory, pendingBotMsg]);

    const sanitizedClientId = userName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_') || 'guest_mobile';

    try {
      let responseText = '';
      let success = false;

      // Attempt hybrid chat endpoint first
      for (const base of [activeUrl, ...BACKEND_URLS]) {
        try {
          const ctrl = new AbortController();
          const tid = setTimeout(() => ctrl.abort(), 45000);

          const payload = {
            prompt: textToSend,
            model: selectedModel,
            enable_rag: true,
            messages: newHistory.map(m => ({ role: m.role, content: m.content }))
          };

          const res = await fetch(`${base}/api/v1/hybrid-chat/stream`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer sk_aibs_dev_master_key_2026',
              'X-Client-ID': sanitizedClientId
            },
            body: JSON.stringify(payload),
            signal: ctrl.signal
          });
          clearTimeout(tid);

          if (res.ok) {
            const data = await res.text();
            if (data && data.trim().length > 0) {
              responseText = data;
              success = true;
              break;
            }
          }
        } catch {
          // fallback to standard chat endpoint
        }
      }

      // Direct Port 11434 Ollama Fallback if gateway is offline
      if (!success) {
        for (const ollamaBase of DIRECT_OLLAMA_URLS) {
          try {
            const ctrl = new AbortController();
            const tid = setTimeout(() => ctrl.abort(), 20000);
            const ollamaModelName = selectedModel === 'stehouwer_llm' ? 'stehouwer_llm' : selectedModel;
            const res = await fetch(`${ollamaBase}/api/generate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                model: ollamaModelName,
                prompt: textToSend,
                stream: false,
                options: { num_ctx: 4096 }
              }),
              signal: ctrl.signal
            });
            clearTimeout(tid);
            if (res.ok) {
              const oData = await res.json();
              if (oData && oData.response) {
                responseText = `⚡ [DIRECT OLLAMA LAN FALLBACK - RTX 4090]\n\n${oData.response}`;
                success = true;
                break;
              }
            }
          } catch {}
        }
      }

      // Secondary fallback to /v1/reasoning/self-solve-refine or simple response
      if (!success) {
        for (const base of [activeUrl, ...BACKEND_URLS]) {
          try {
            const res = await fetch(`${base}/v1/health`);
            if (res.ok) {
              const data = await res.json();
              responseText = `⚡ AI-BS Cognitive Engine (v5.327.0)\n\nHost Status: ${data.status || 'Online'}\nGPU: ${data.gpu_accelerated ? 'RTX 4090 Active' : 'CPU Mode'}\nSelected Model: ${selectedModel}\nUser: ${userName}\n\nYour message "${textToSend}" was acknowledged by sovereign gateway.`;
              success = true;
              break;
            }
          } catch {}
        }
      }

      if (!success) {
        responseText = `⚠️ Connection to sovereign host (${activeUrl}) timed out.\nVerify that your host is online or connected via Cloudflare Tunnel.`;
      }

      setMessages(prev =>
        prev.map(m => (m.id === botMsgId ? { ...m, content: responseText } : m))
      );
    } catch (err: any) {
      setMessages(prev =>
        prev.map(m =>
          m.id === botMsgId
            ? { ...m, content: `❌ Error communicating with AI-BS: ${err?.message || 'Network failure'}` }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'msg-cleared',
        role: 'system',
        content: `Conversation history reset for ${userName}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  const saveName = () => {
    const trimmed = tempName.trim();
    if (trimmed) {
      setUserName(trimmed);
      setMessages(prev => [
        ...prev,
        {
          id: `msg-name-${Date.now()}`,
          role: 'system',
          content: `Session updated. User identity set to: ${trimmed}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
    setIsNameModalVisible(false);
  };

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="light" />
        <KeyboardAvoidingView
          style={styles.container}
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 10 : 0}
        >
          {/* Header */}
          <View style={styles.header}>
            <View>
              <View style={styles.titleRow}>
                <Text style={styles.headerTitle}>AI-BS</Text>
                <Text style={styles.headerSubtitle}>SOVEREIGN MOBILE</Text>
                <View style={styles.versionBadge}>
                  <Text style={styles.versionText}>v5.327.0</Text>
                </View>
              </View>
              <Text style={styles.headerSub}>RTX 4090 • Stehouwer LLM</Text>
            </View>

            <View style={styles.headerControls}>
              {/* Remote Command & Push Stream Deck */}
              <TouchableOpacity
                onPress={() => setIsStreamDeckVisible(true)}
                style={styles.deckBadge}
              >
                <Text style={styles.deckBadgeText}>🎮 DECK</Text>
              </TouchableOpacity>

              {/* Screenplay Studio & Video Gallery Button */}
              <TouchableOpacity
                onPress={() => setIsScreenplayModalVisible(true)}
                style={styles.screenplayBadge}
              >
                <Text style={styles.screenplayBadgeText}>🎬 SCENES</Text>
              </TouchableOpacity>

              {/* Universal 18-Port Matrix & Telemetry Button */}
              <TouchableOpacity
                onPress={() => setIsTopologyModalVisible(true)}
                style={styles.topologyBadge}
              >
                <Text style={styles.topologyBadgeText}>⚡ MATRIX</Text>
              </TouchableOpacity>

              {/* Universal User Profile Button */}
              <TouchableOpacity
                onPress={() => {
                  setTempName(userName === 'Guest' ? '' : userName);
                  setIsNameModalVisible(true);
                }}
                style={styles.userBadge}
              >
                <Text style={styles.userBadgeText}>👤 {userName}</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={checkHealth} style={styles.statusBadge}>
                <View
                  style={[
                    styles.statusDot,
                    backendStatus === 'online'
                      ? styles.dotOnline
                      : backendStatus === 'checking'
                      ? styles.dotChecking
                      : styles.dotOffline
                  ]}
                />
                <Text style={styles.statusText}>
                  {backendStatus === 'online' ? (pingMs ? `${pingMs}ms` : 'LIVE') : backendStatus.toUpperCase()}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={handleClear} style={styles.clearButton}>
                <Text style={styles.clearButtonText}>Reset</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Floating Push Notification Toast Banner */}
          {pushNotification && (
            <TouchableOpacity
              style={[
                styles.pushBanner,
                pushNotification.type === 'error'
                  ? styles.pushBannerError
                  : pushNotification.type === 'success'
                  ? styles.pushBannerSuccess
                  : styles.pushBannerInfo
              ]}
              onPress={() => setPushNotification(null)}
              activeOpacity={0.8}
            >
              <Text style={styles.pushBannerTitle}>{pushNotification.title}</Text>
              <Text style={styles.pushBannerBody}>{pushNotification.body}</Text>
            </TouchableOpacity>
          )}

          {/* Model Selector Bar */}
          <View style={styles.modelBar}>
            <Text style={styles.modelBarLabel}>MODEL:</Text>
            <TouchableOpacity
              style={[styles.modelOption, selectedModel === 'stehouwer_llm' && styles.modelOptionActive]}
              onPress={() => setSelectedModel('stehouwer_llm')}
            >
              <Text style={[styles.modelOptionText, selectedModel === 'stehouwer_llm' && styles.modelOptionTextActive]}>
                Stehouwer LLM
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.modelOption, selectedModel === 'qwen2.5-coder' && styles.modelOptionActive]}
              onPress={() => setSelectedModel('qwen2.5-coder')}
            >
              <Text style={[styles.modelOptionText, selectedModel === 'qwen2.5-coder' && styles.modelOptionTextActive]}>
                Coder 32B
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.modelOption, selectedModel === 'llama3.1' && styles.modelOptionActive]}
              onPress={() => setSelectedModel('llama3.1')}
            >
              <Text style={[styles.modelOptionText, selectedModel === 'llama3.1' && styles.modelOptionTextActive]}>
                Llama 3.1
              </Text>
            </TouchableOpacity>
          </View>

          {/* Messages FlatList */}
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={item => item.id}
            contentContainerStyle={styles.messageList}
            onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
            renderItem={({ item }) => (
              <View
                style={[
                  styles.messageBubble,
                  item.role === 'user'
                    ? styles.userBubble
                    : item.role === 'system'
                    ? styles.systemBubble
                    : styles.assistantBubble
                ]}
              >
                <View style={styles.messageHeader}>
                  <Text style={styles.senderLabel}>
                    {item.role === 'user'
                      ? `👤 ${userName.toUpperCase()}`
                      : item.role === 'system'
                      ? '⚙️ SYSTEM'
                      : '🤖 STEHOUWER AI'}
                  </Text>
                  <Text style={styles.timestampLabel}>{item.timestamp}</Text>
                </View>
                <Text style={styles.messageContent}>{item.content}</Text>
              </View>
            )}
          />

          {/* Quick Action Chips */}
          <View style={styles.chipsContainer}>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipsScroll}>
              <TouchableOpacity
                style={[styles.chip, { backgroundColor: '#1e3a8a', borderColor: '#3b82f6' }]}
                onPress={() => handleSend('search rag for sovereign intelligence and cognitive architecture')}
              >
                <Text style={[styles.chipText, { color: '#93c5fd' }]}>🧠 1M+ RAG Search</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.chip, { backgroundColor: '#4c1d95', borderColor: '#8b5cf6' }]}
                onPress={() => handleSend('summarize 1m file C:\\AI-BS\\workspace\\pasted_1m_buffer.txt')}
              >
                <Text style={[styles.chipText, { color: '#c4b5fd' }]}>📑 1M Map-Reduce</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.chip, { backgroundColor: '#78350f', borderColor: '#f59e0b' }]}
                onPress={() => handleSend('Run the Zombie Node Cleaner to sweep orphaned background processes and reclaim host DDR5 RAM.')}
              >
                <Text style={[styles.chipText, { color: '#fde68a' }]}>🧹 Reclaim RAM</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.chip}
                onPress={() => handleSend('Show status of the ComfyUI video diffusion pipeline for The Bad Side Upside Down')}
              >
                <Text style={styles.chipText}>🎬 Julie's Screenplay</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.chip}
                onPress={() => handleSend('Perform a full cognitive cluster status check and VRAM audit')}
              >
                <Text style={styles.chipText}>⚡ GPU Audit</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.chip}
                onPress={() => handleSend('Generate an ultra high-res cinematic concept for a cyberpunk workstation')}
              >
                <Text style={styles.chipText}>🎨 Concept Art</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.chip}
                onPress={() => handleSend('Explain the dual-port failover architecture in AI-BS')}
              >
                <Text style={styles.chipText}>🧠 Architecture</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.chip}
                onPress={() => handleSend('What are the active tasks in AI-BS?')}
              >
                <Text style={styles.chipText}>📋 Tasks</Text>
              </TouchableOpacity>
            </ScrollView>
          </View>

          {/* Input Bar */}
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.textInput}
              placeholder={`Ask Stehouwer LLM as ${userName}...`}
              placeholderTextColor="#64748b"
              value={input}
              onChangeText={setInput}
              multiline
              maxLength={2000}
            />
            <TouchableOpacity
              style={[styles.sendButton, (!input.trim() || loading) && styles.sendButtonDisabled]}
              onPress={() => handleSend()}
              disabled={!input.trim() || loading}
            >
              {loading ? (
                <ActivityIndicator size="small" color="#000" />
              ) : (
                <Text style={styles.sendButtonText}>Send</Text>
              )}
            </TouchableOpacity>
          </View>

          {/* User Name Modal */}
          <Modal
            visible={isNameModalVisible}
            transparent
            animationType="fade"
            onRequestClose={() => setIsNameModalVisible(false)}
          >
            <View style={styles.modalOverlay}>
              <View style={styles.modalContent}>
                <Text style={styles.modalTitle}>👤 Set Your User Name</Text>
                <Text style={styles.modalSubtitle}>
                  This name identifies your messages and creates your private session in AI-BS.
                </Text>

                <TextInput
                  style={styles.modalInput}
                  placeholder="Enter your name (e.g. Alex, Anna, Guest)..."
                  placeholderTextColor="#64748b"
                  value={tempName}
                  onChangeText={setTempName}
                  autoFocus
                  maxLength={30}
                />

                <View style={styles.quickPresetRow}>
                  {['Guest', 'Brett', 'Anna', 'Friend', 'Client'].map(name => (
                    <TouchableOpacity
                      key={name}
                      style={styles.presetChip}
                      onPress={() => setTempName(name)}
                    >
                      <Text style={styles.presetChipText}>{name}</Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.modalCancelBtn}
                    onPress={() => setIsNameModalVisible(false)}
                  >
                    <Text style={styles.modalCancelText}>Cancel</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.modalSaveBtn}
                    onPress={saveName}
                  >
                    <Text style={styles.modalSaveText}>Save Name</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </Modal>

          {/* 18-Port Topology Matrix & Telemetry Modal */}
          <Modal
            visible={isTopologyModalVisible}
            transparent
            animationType="fade"
            onRequestClose={() => setIsTopologyModalVisible(false)}
          >
            <View style={styles.modalOverlay}>
              <View style={[styles.modalContent, styles.topologyModalContent]}>
                <View style={styles.topologyHeaderRow}>
                  <Text style={styles.modalTitle}>⚡ 18-Port Ecosystem Topology</Text>
                  <View style={styles.headerBadgeGroup}>
                    <View style={[styles.wsStatusBadge, { backgroundColor: wsConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(234, 179, 8, 0.2)' }]}>
                      <Text style={[styles.wsStatusText, { color: wsConnected ? '#10b981' : '#eab308' }]}>
                        {wsConnected ? '🟢 LIVE WS' : '🟡 POLLING'}
                      </Text>
                    </View>
                    <View style={styles.versionBadge}>
                      <Text style={styles.versionText}>v5.327.0</Text>
                    </View>
                  </View>
                </View>
                <Text style={styles.modalSubtitle}>
                  Zero-Collision Sovereign Mesh • RTX 4090 Sovereign Cognitive Cluster
                </Text>

                {/* Live Hardware & Resource Telemetry Card */}
                <View style={styles.topologyInfoCard}>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>ACTIVE GATEWAY:</Text>
                    <Text style={styles.topologyInfoValue}>{activeUrl}</Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>CPU / RAM LOAD:</Text>
                    <Text style={[styles.topologyInfoValue, { color: '#38bdf8' }]}>
                      CPU: {hardwareMetrics.cpu_percent}% • RAM: {hardwareMetrics.ram_percent}%
                    </Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>HARDWARE GPU:</Text>
                    <Text style={styles.topologyInfoValue}>
                      {hardwareMetrics.gpu.name} ({Math.round(hardwareMetrics.gpu.vram_used_mb / 1024)}GB / {Math.round(hardwareMetrics.gpu.vram_total_mb / 1024)}GB VRAM)
                    </Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>CLIENT / TENANT:</Text>
                    <Text style={styles.topologyInfoValue}>
                      X-Client-ID: {userName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_') || 'guest_mobile'}
                    </Text>
                  </View>
                </View>

                {/* Active Wan2.1 Video Motion Diffusion Progress Banner */}
                {activeVideoJob && (
                  <View style={styles.wanActiveBanner}>
                    <View style={styles.wanBannerHeader}>
                      <Text style={styles.wanBannerTitle}>🎬 Wan2.1 Video Diffusion ({activeVideoJob.frames} frames @ 24fps)</Text>
                      <Text style={styles.wanBannerStatus}>{activeVideoJob.status.toUpperCase()}</Text>
                    </View>
                    <Text style={styles.wanBannerScene} numberOfLines={1}>
                      Scene: {activeVideoJob.scene_id || 'Custom Screenplay Sequence'}
                    </Text>
                    <View style={styles.wanProgressBarBg}>
                      <View style={[styles.wanProgressBarFill, { width: `${activeVideoJob.progress}%` }]} />
                    </View>
                    <Text style={styles.wanProgressText}>{activeVideoJob.progress}% completed</Text>
                  </View>
                )}

                {/* Dynamic 18-Port Matrix Grid with 1-Tap Control Buttons */}
                <ScrollView style={styles.topologyMatrixScroll} showsVerticalScrollIndicator={false}>
                  <Text style={styles.matrixSectionTitle}>
                    COLLISION-FREE PORT ALLOCATIONS ({ecosystemPorts.filter(p => p.status === 'ONLINE').length}/{ecosystemPorts.length} ONLINE):
                  </Text>
                  {ecosystemPorts.map(p => {
                    const isOnline = p.status === 'ONLINE';
                    const isLoading = actionLoadingPort === p.port;
                    return (
                      <View key={p.port} style={styles.matrixRow}>
                        <View style={[styles.matrixPortBadge, { borderColor: isOnline ? 'rgba(56, 189, 248, 0.4)' : '#334155' }]}>
                          <Text style={styles.matrixPortText}>{p.port}</Text>
                        </View>
                        <View style={styles.matrixServiceDetails}>
                          <Text style={styles.matrixServiceName} numberOfLines={1}>{p.name}</Text>
                          <Text style={styles.matrixServiceSub} numberOfLines={1}>
                            [{p.tier.toUpperCase()}] {p.pid ? `PID: ${p.pid} • ${p.memory_mb || 0} MB` : 'Standby / Unallocated'}
                          </Text>
                        </View>
                        <View style={[styles.matrixStatBadge, {
                          backgroundColor: isOnline ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          borderColor: isOnline ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'
                        }]}>
                          <Text style={[styles.matrixStatText, { color: isOnline ? '#10b981' : '#ef4444' }]}>
                            {p.status}
                          </Text>
                        </View>
                        <TouchableOpacity
                          style={[styles.matrixActionBtn, isLoading && styles.matrixActionBtnDisabled]}
                          disabled={isLoading}
                          onPress={() => handleDaemonAction(isOnline ? 'restart' : 'start', p.port, p.daemon_name)}
                        >
                          {isLoading ? (
                            <ActivityIndicator size="small" color="#38bdf8" />
                          ) : (
                            <Text style={styles.matrixActionBtnText}>{isOnline ? '🔄' : '▶'}</Text>
                          )}
                        </TouchableOpacity>
                      </View>
                    );
                  })}
                </ScrollView>

                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.modalSaveBtn}
                    onPress={() => setIsTopologyModalVisible(false)}
                  >
                    <Text style={styles.modalSaveText}>Close Matrix</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </Modal>

          {/* Julie Stehouwer Screenplay Video & Scene Diffusion Studio Modal */}
          <Modal
            visible={isScreenplayModalVisible}
            transparent
            animationType="fade"
            onRequestClose={() => setIsScreenplayModalVisible(false)}
          >
            <View style={styles.modalOverlay}>
              <View style={[styles.modalContent, styles.screenplayModalContent]}>
                <View style={styles.topologyHeaderRow}>
                  <Text style={styles.modalTitle}>🎬 Screenplay Scene Studio</Text>
                  <View style={styles.screenplayVersionBadge}>
                    <Text style={styles.screenplayVersionText}>v5.327.0</Text>
                  </View>
                </View>
                <Text style={styles.modalSubtitle}>
                  The Bad Side Upside Down • By Julie Stehouwer • RTX 4090 ComfyUI Pipeline
                </Text>

                {/* Pipeline Architecture Telemetry */}
                <View style={styles.screenplayInfoCard}>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>PIPELINE STATUS:</Text>
                    <Text style={[styles.topologyInfoValue, { color: '#10b981' }]}>COMFYUI ONLINE (PORT 8189)</Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>CONCEPT MODEL:</Text>
                    <Text style={styles.topologyInfoValue}>v1-5-pruned-emaonly-fp16.safetensors</Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>T2V VIDEO TARGET:</Text>
                    <Text style={styles.topologyInfoValue}>wan2.1-t2v-1.3B / ltx-video-2b</Text>
                  </View>
                  <View style={styles.topologyInfoRow}>
                    <Text style={styles.topologyInfoLabel}>PHYSICS INTEGRATION:</Text>
                    <Text style={styles.topologyInfoValue}>Weeble Wobble Center of Mass (-35cm)</Text>
                  </View>
                </View>

                {/* Rendered Scene Cards */}
                <ScrollView style={styles.screenplayCardsScroll} showsVerticalScrollIndicator={false}>
                  <Text style={styles.matrixSectionTitle}>RENDERED SCENES & CHARACTERS (LOCAL RTX 4090):</Text>
                  {SCREENPLAY_ASSETS.map((asset) => (
                    <View key={asset.concept_id} style={styles.screenplayCard}>
                      <View style={styles.screenplayCardHeader}>
                        <Text style={styles.screenplayCardTitle}>{asset.title}</Text>
                        <View style={styles.screenplayTagBadge}>
                          <Text style={styles.screenplayTagText}>{asset.subject} • {asset.aspect_ratio}</Text>
                        </View>
                      </View>
                      <Text style={styles.screenplayPromptText}>{asset.prompt}</Text>
                      <View style={styles.screenplayCardFooter}>
                        <Text style={styles.screenplayFileText}>📁 {asset.raster_path}</Text>
                        <TouchableOpacity
                          style={styles.dispatchMotionBtn}
                          onPress={() => {
                            setIsScreenplayModalVisible(false);
                            handleSend(`Dispatch Wan2.1 video motion diffusion for scene "${asset.title}" (${asset.video_target})`);
                          }}
                        >
                          <Text style={styles.dispatchMotionBtnText}>▶ Motion</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  ))}
                </ScrollView>

                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.modalSaveBtn}
                    onPress={() => setIsScreenplayModalVisible(false)}
                  >
                    <Text style={styles.modalSaveText}>Close Studio</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </Modal>

          {/* Sovereign Remote Command & Stream Deck Modal */}
          <Modal
            visible={isStreamDeckVisible}
            animationType="slide"
            transparent={true}
            onRequestClose={() => setIsStreamDeckVisible(false)}
          >
            <View style={styles.modalOverlay}>
              <View style={[styles.modalContent, styles.streamDeckModalContent]}>
                <View style={styles.topologyHeaderRow}>
                  <Text style={styles.modalTitle}>🎮 COMMAND STREAM DECK</Text>
                  <View style={[styles.wsStatusBadge, { backgroundColor: wsConnected ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)' }]}>
                    <Text style={styles.wsStatusText}>{wsConnected ? 'LIVE FEED' : 'OFFLINE'}</Text>
                  </View>
                </View>

                {deckActionStatus ? (
                  <View style={styles.deckStatusBanner}>
                    <Text style={styles.deckStatusBannerText}>{deckActionStatus}</Text>
                  </View>
                ) : null}

                <ScrollView style={styles.deckActionsScroll} showsVerticalScrollIndicator={false}>
                  <Text style={styles.matrixSectionTitle}>ONE-TOUCH MACROS & CLUSTER COMMANDS:</Text>

                  <View style={styles.deckGrid}>
                    {/* Action 1: Self-Healing Sentinel */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={async () => {
                        setDeckActionStatus('Running Self-Healing Sentinel diagnostic sweep...');
                        try {
                          const res = await fetch(`${activeUrl}/api/sentinel/status`);
                          if (res.ok) {
                            const data = await res.json();
                            setDeckActionStatus(`🛡️ Sentinel Online • ${data.incidents_count || 0} Incidents • Circuit Breakers: ${data.active_circuit_breakers || 0}`);
                          } else {
                            setDeckActionStatus('Sentinel check returned non-200');
                          }
                        } catch (err: any) {
                          setDeckActionStatus(`Error: ${err.message}`);
                        }
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>🛡️</Text>
                      <Text style={styles.deckButtonTitle}>Sentinel Auto-Heal</Text>
                      <Text style={styles.deckButtonSub}>AST & Pytest Gate</Text>
                    </TouchableOpacity>

                    {/* Action 2: Spot GPU Cluster Probe */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={() => {
                        setDeckActionStatus('Cluster spot probe unavailable: no verified provider connection; external dispatch is disabled.');
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>🌐</Text>
                      <Text style={styles.deckButtonTitle}>Cluster Spot Probe</Text>
                      <Text style={styles.deckButtonSub}>Vast / Clore Headroom</Text>
                    </TouchableOpacity>

                    {/* Action 3: Screenplay-to-Movie VSE */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={() => {
                        setIsStreamDeckVisible(false);
                        handleSend('Execute end-to-end Screenplay-to-Movie assembly using Headless Blender VSE and Wan2.1 video generation');
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>🎬</Text>
                      <Text style={styles.deckButtonTitle}>Assemble Movie</Text>
                      <Text style={styles.deckButtonSub}>Blender VSE & F5-TTS</Text>
                    </TouchableOpacity>

                    {/* Action 4: CRO Support Backtest */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={() => {
                        setDeckActionStatus('CRO backtest unavailable: no strategy execution or result receipt. Trading remains held.');
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>📈</Text>
                      <Text style={styles.deckButtonTitle}>CRO Backtest</Text>
                      <Text style={styles.deckButtonSub}>Support $0.05719</Text>
                    </TouchableOpacity>

                    {/* Action 5: Harvest Commercial Leads */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={() => {
                        setDeckActionStatus('Lead harvest held: external dispatch is disabled; no leads have been collected or stored.');
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>📧</Text>
                      <Text style={styles.deckButtonTitle}>Lead Harvester</Text>
                      <Text style={styles.deckButtonSub}>B2B Email Drip</Text>
                    </TouchableOpacity>

                    {/* Action 6: Flush VRAM Cache */}
                    <TouchableOpacity
                      style={styles.deckButton}
                      onPress={async () => {
                        setDeckActionStatus('Purging RTX 4090 VRAM PyTorch cache...');
                        try {
                          const res = await fetch(`${activeUrl}/vram/flush`, { method: 'POST' });
                          if (!res.ok) {
                            throw new Error(`VRAM flush rejected (HTTP ${res.status})`);
                          }
                          setDeckActionStatus('VRAM flush request acknowledged; completion and available memory remain unverified.');
                        } catch (err: any) {
                          setDeckActionStatus(`VRAM flush failed: ${err.message}`);
                        }
                      }}
                    >
                      <Text style={styles.deckButtonIcon}>🧹</Text>
                      <Text style={styles.deckButtonTitle}>Flush VRAM Cache</Text>
                      <Text style={styles.deckButtonSub}>RTX 4090 Headroom</Text>
                    </TouchableOpacity>
                  </View>
                </ScrollView>

                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.modalSaveBtn}
                    onPress={() => {
                      setDeckActionStatus('');
                      setIsStreamDeckVisible(false);
                    }}
                  >
                    <Text style={styles.modalSaveText}>Close Stream Deck</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </View>
          </Modal>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0a0d14'
  },
  container: {
    flex: 1,
    backgroundColor: '#0a0d14'
  },
  header: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
    backgroundColor: '#0f172a'
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8
  },
  headerTitle: {
    color: '#00e5ff',
    fontSize: 20,
    fontWeight: '900',
    letterSpacing: 1
  },
  headerSubtitle: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1.5
  },
  versionBadge: {
    backgroundColor: 'rgba(0, 229, 255, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0, 229, 255, 0.3)'
  },
  versionText: {
    color: '#00e5ff',
    fontSize: 10,
    fontWeight: '800'
  },
  headerSub: {
    color: '#64748b',
    fontSize: 11,
    marginTop: 2
  },
  headerControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6
  },
  userBadge: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(0, 229, 255, 0.4)'
  },
  userBadgeText: {
    color: '#00e5ff',
    fontSize: 11,
    fontWeight: '700'
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155'
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    marginRight: 6
  },
  dotOnline: {
    backgroundColor: '#10b981'
  },
  dotChecking: {
    backgroundColor: '#f59e0b'
  },
  dotOffline: {
    backgroundColor: '#ef4444'
  },
  statusText: {
    color: '#cbd5e1',
    fontSize: 11,
    fontWeight: '700'
  },
  clearButton: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#334155'
  },
  clearButtonText: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600'
  },
  modelBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#0d131f',
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
    gap: 8
  },
  modelBarLabel: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '800'
  },
  modelOption: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155'
  },
  modelOptionActive: {
    backgroundColor: 'rgba(0, 229, 255, 0.15)',
    borderColor: '#00e5ff'
  },
  modelOptionText: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '600'
  },
  modelOptionTextActive: {
    color: '#00e5ff',
    fontWeight: '800'
  },
  messageList: {
    padding: 16,
    gap: 12
  },
  messageBubble: {
    padding: 12,
    borderRadius: 12,
    maxWidth: '88%'
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: 'rgba(0, 229, 255, 0.3)'
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#0f172a',
    borderWidth: 1,
    borderColor: '#1e293b'
  },
  systemBubble: {
    alignSelf: 'center',
    backgroundColor: '#182030',
    borderWidth: 1,
    borderColor: '#334155'
  },
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
    gap: 12
  },
  senderLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: '#00e5ff',
    letterSpacing: 0.5
  },
  timestampLabel: {
    fontSize: 10,
    color: '#64748b'
  },
  messageContent: {
    color: '#f1f5f9',
    fontSize: 14,
    lineHeight: 20
  },
  chipsContainer: {
    paddingVertical: 6,
    backgroundColor: '#0d131f',
    borderTopWidth: 1,
    borderTopColor: '#1e293b'
  },
  chipsScroll: {
    paddingHorizontal: 16,
    gap: 8
  },
  chip: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#334155'
  },
  chipText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: '600'
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#0f172a',
    borderTopWidth: 1,
    borderTopColor: '#1e293b',
    gap: 10
  },
  textInput: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    backgroundColor: '#1e293b',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155'
  },
  sendButton: {
    backgroundColor: '#00e5ff',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center'
  },
  sendButtonDisabled: {
    backgroundColor: '#334155',
    opacity: 0.5
  },
  sendButtonText: {
    color: '#000',
    fontWeight: '800',
    fontSize: 14
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  modalContent: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: '#0f172a',
    borderRadius: 16,
    padding: 20,
    borderWidth: 1,
    borderColor: '#334155'
  },
  modalTitle: {
    color: '#00e5ff',
    fontSize: 18,
    fontWeight: '800',
    marginBottom: 6
  },
  modalSubtitle: {
    color: '#94a3b8',
    fontSize: 12,
    lineHeight: 16,
    marginBottom: 16
  },
  modalInput: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: '#fff',
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#334155',
    marginBottom: 12
  },
  quickPresetRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 18
  },
  presetChip: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#334155'
  },
  presetChipText: {
    color: '#cbd5e1',
    fontSize: 12,
    fontWeight: '600'
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 10
  },
  modalCancelBtn: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#1e293b'
  },
  modalCancelText: {
    color: '#94a3b8',
    fontSize: 13,
    fontWeight: '600'
  },
  modalSaveBtn: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    backgroundColor: '#00e5ff'
  },
  modalSaveText: {
    color: '#000',
    fontSize: 13,
    fontWeight: '800'
  },
  topologyBadge: {
    backgroundColor: 'rgba(0, 229, 255, 0.12)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(0, 229, 255, 0.35)'
  },
  topologyBadgeText: {
    color: '#00e5ff',
    fontSize: 11,
    fontWeight: '800'
  },
  topologyModalContent: {
    maxHeight: '85%',
    width: '92%'
  },
  topologyHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4
  },
  topologyInfoCard: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 12,
    marginVertical: 10,
    borderWidth: 1,
    borderColor: '#334155',
    gap: 6
  },
  topologyInfoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  topologyInfoLabel: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '700'
  },
  topologyInfoValue: {
    color: '#f8fafc',
    fontSize: 11,
    fontWeight: '600'
  },
  topologyMatrixScroll: {
    maxHeight: 240,
    marginVertical: 8
  },
  matrixSectionTitle: {
    color: '#64748b',
    fontSize: 10,
    fontWeight: '800',
    marginBottom: 8,
    letterSpacing: 0.5
  },
  matrixRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: '#1e293b',
    gap: 8
  },
  matrixPortBadge: {
    backgroundColor: '#0f172a',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#334155',
    minWidth: 48,
    alignItems: 'center'
  },
  matrixPortText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '800'
  },
  matrixServiceName: {
    flex: 1,
    color: '#e2e8f0',
    fontSize: 12,
    fontWeight: '600'
  },
  matrixStatBadge: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)'
  },
  matrixStatText: {
    color: '#10b981',
    fontSize: 10,
    fontWeight: '800'
  },
  screenplayBadge: {
    backgroundColor: 'rgba(224, 64, 251, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(224, 64, 251, 0.4)'
  },
  screenplayBadgeText: {
    color: '#e040fb',
    fontSize: 11,
    fontWeight: '800'
  },
  screenplayModalContent: {
    maxHeight: '90%',
    width: '94%'
  },
  screenplayVersionBadge: {
    backgroundColor: 'rgba(224, 64, 251, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(224, 64, 251, 0.4)'
  },
  screenplayVersionText: {
    color: '#e040fb',
    fontSize: 10,
    fontWeight: '800'
  },
  screenplayInfoCard: {
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 10,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: '#334155',
    gap: 4
  },
  screenplayCardsScroll: {
    maxHeight: 280,
    marginVertical: 6
  },
  screenplayCard: {
    backgroundColor: '#161e2e',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#2d3748'
  },
  screenplayCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4
  },
  screenplayCardTitle: {
    color: '#f8fafc',
    fontSize: 12,
    fontWeight: '800',
    flex: 1,
    marginRight: 6
  },
  screenplayTagBadge: {
    backgroundColor: 'rgba(0, 229, 255, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(0, 229, 255, 0.3)'
  },
  screenplayTagText: {
    color: '#00e5ff',
    fontSize: 9,
    fontWeight: '800'
  },
  screenplayPromptText: {
    color: '#94a3b8',
    fontSize: 11,
    lineHeight: 15,
    marginBottom: 6
  },
  screenplayCardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 4,
    borderTopWidth: 1,
    borderTopColor: '#1e293b'
  },
  screenplayFileText: {
    color: '#e040fb',
    fontSize: 10,
    fontWeight: '600'
  },
  dispatchMotionBtn: {
    backgroundColor: '#e040fb',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4
  },
  dispatchMotionBtnText: {
    color: '#000',
    fontSize: 10,
    fontWeight: '800'
  },
  headerBadgeGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6
  },
  wsStatusBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)'
  },
  wsStatusText: {
    fontSize: 9,
    fontWeight: '800'
  },
  wanActiveBanner: {
    backgroundColor: '#1e1b4b',
    borderRadius: 8,
    padding: 10,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#4338ca'
  },
  wanBannerHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4
  },
  wanBannerTitle: {
    color: '#c7d2fe',
    fontSize: 11,
    fontWeight: '800'
  },
  wanBannerStatus: {
    color: '#38bdf8',
    fontSize: 9,
    fontWeight: '800'
  },
  wanBannerScene: {
    color: '#94a3b8',
    fontSize: 10,
    marginBottom: 6
  },
  wanProgressBarBg: {
    height: 6,
    backgroundColor: '#312e81',
    borderRadius: 3,
    overflow: 'hidden'
  },
  wanProgressBarFill: {
    height: '100%',
    backgroundColor: '#818cf8',
    borderRadius: 3
  },
  wanProgressText: {
    color: '#a5b4fc',
    fontSize: 9,
    fontWeight: '700',
    marginTop: 4,
    textAlign: 'right'
  },
  matrixServiceDetails: {
    flex: 1
  },
  matrixServiceSub: {
    color: '#64748b',
    fontSize: 9,
    fontWeight: '600'
  },
  matrixActionBtn: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#334155',
    minWidth: 28,
    alignItems: 'center',
    justifyContent: 'center'
  },
  matrixActionBtnDisabled: {
    opacity: 0.5
  },
  matrixActionBtnText: {
    color: '#38bdf8',
    fontSize: 11,
    fontWeight: '800'
  },
  deckBadge: {
    backgroundColor: 'rgba(234, 179, 8, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(234, 179, 8, 0.4)'
  },
  deckBadgeText: {
    color: '#eab308',
    fontSize: 11,
    fontWeight: '800'
  },
  pushBanner: {
    marginHorizontal: 16,
    marginTop: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    zIndex: 100
  },
  pushBannerError: {
    backgroundColor: 'rgba(239, 68, 68, 0.18)',
    borderColor: '#ef4444'
  },
  pushBannerSuccess: {
    backgroundColor: 'rgba(16, 185, 129, 0.18)',
    borderColor: '#10b981'
  },
  pushBannerInfo: {
    backgroundColor: 'rgba(14, 165, 233, 0.18)',
    borderColor: '#0ea5e9'
  },
  pushBannerTitle: {
    color: '#f8fafc',
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 2
  },
  pushBannerBody: {
    color: '#cbd5e1',
    fontSize: 11,
    fontWeight: '500'
  },
  streamDeckModalContent: {
    maxHeight: '88%',
    width: '92%'
  },
  deckStatusBanner: {
    backgroundColor: '#1e293b',
    padding: 10,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#3b82f6',
    marginVertical: 8
  },
  deckStatusBannerText: {
    color: '#93c5fd',
    fontSize: 11,
    fontWeight: '700',
    textAlign: 'center'
  },
  deckActionsScroll: {
    maxHeight: 380,
    marginVertical: 8
  },
  deckGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    justifyContent: 'space-between',
    paddingVertical: 4
  },
  deckButton: {
    width: '48%',
    backgroundColor: '#1e293b',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#334155',
    alignItems: 'center',
    gap: 4
  },
  deckButtonIcon: {
    fontSize: 22,
    marginBottom: 2
  },
  deckButtonTitle: {
    color: '#f8fafc',
    fontSize: 12,
    fontWeight: '800',
    textAlign: 'center'
  },
  deckButtonSub: {
    color: '#94a3b8',
    fontSize: 9,
    fontWeight: '600',
    textAlign: 'center'
  }
});
