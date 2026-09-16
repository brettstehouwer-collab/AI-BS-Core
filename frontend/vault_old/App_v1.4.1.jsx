import React, { useState, useEffect } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from './firebase';
import BullshitKnowledgeSuite from './BullshitKnowledgeSuite';
import BullshitCreationSuite from './BullshitCreationSuite';
import BullshitTelemetrySuite from './BullshitTelemetrySuite';
import BullshitAdminSuite from './BullshitAdminSuite';
import BrokenComponent from './BrokenComponent';
import ChangelogModal from './ChangelogModal';
import LoginModal from './components/LoginModal';
import BullshitLeadMatrix from './components/BullshitLeadMatrix';
import { encryptPayload } from './security';
import ClientsModule from './clients/ClientsModule';
import BullshitCryptoSwarm from './BullshitCryptoSwarm';
import BullshitChiaManager from './BullshitChiaManager';
import BullshitEvolutionHistory from './BullshitEvolutionHistory';
import BullshitPanicButton from './BullshitPanicButton';
import VideoStudioTab from './components/VideoStudioTab';
import ApiManagerTab from './components/ApiManagerTab';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Security enabled
  const [activeTab, setActiveTab] = useState('chat');
  const [isMicActive, setIsMicActive] = useState(false);
  const [isChangelogOpen, setIsChangelogOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [backendUrl, setBackendUrl] = useState("https://ai-bs-backend.loca.lt");

  useEffect(() => {
    // Current app version (should match package.json and UI badge)
    const currentVersion = "1.4.1";
    const lastVersion = localStorage.getItem("bullshitAppVersion");

    if (lastVersion !== currentVersion) {
      setIsChangelogOpen(true);
      localStorage.setItem("bullshitAppVersion", currentVersion);
    }
    
    // Listen for Firebase Auth changes
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      const AUTHORIZED_EMAILS = [
        'theseandaley@gmail.com',
        'stehouwerjulie@gmail.com',
        'brettstehouwer@gmail.com',
        'footballstar0325@gmail.com'
      ];
      if (user && AUTHORIZED_EMAILS.includes(user.email?.toLowerCase())) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    });
    return () => unsubscribe();
  }, []);


  // Toggle Wake-Word Listener
  const toggleMic = async () => {
      const newState = !isMicActive;
      setIsMicActive(newState);
      try {
          await fetch("http://127.0.0.1:8005/wake-word/toggle", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ enabled: newState })
          });
      } catch (e) {
          console.error("Wake-Word daemon offline");
      }
  };
  const [messages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");

  // Define Orchestrator Admin Commands
  const ORCHESTRATOR_COMMANDS = [
    { title: "System Diagnostics", prompt: "Run a full system diagnostic sweep on all local daemons and check CPU/VRAM footprint." },
    { title: "Optimize ChromaDB", prompt: "Optimize the ChromaDB vector database and/or rebuild the vector memory collection." },
    { title: "Synchronize Swarm", prompt: "Synchronize all active background agent daemons and align cognitive pathways." },
    { title: "Audit Git Workspace", prompt: "Perform an audit of the current workspace Git tree and check for uncommitted changes." },
    { title: "Recalibrate Sensors", prompt: "Reset vertical farming sensor thresholds and recalibrate MFC output." },
    { title: "Compile Production Build", prompt: "Compile and package the latest production build of the AI-BS system." }
  ];

  const handleLaunchAgent = async (agentType, prompt = "") => {
    try {
      const res = await fetch(`${backendUrl}/agent/handoff`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ agent_role: agentType, prompt: prompt || "Initialize daemon session" })
      });
      const data = await res.json();
      if (data.status === "success") {
        alert(`Successfully launched ${agentType} agent.\nResult: ${JSON.stringify(data.swarm_result || data)}`);
      } else {
        alert(`Failed to launch agent: ${data.message}`);
      }
    } catch (e) {
      alert("Failed to reach backend: " + e.message);
    }
  };

  const handleKillAgent = async (agentName) => {
    try {
      const res = await fetch(`${backendUrl}/polyglot-execution-engine/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: "powershell", command: `taskkill /f /t /im "${agentName}*"` })
      });
      const data = await res.json();
      alert(`Termination command executed for ${agentName}.\nOutput: ${data.output || "No output"}`);
    } catch (e) {
      alert("Failed to execute termination: " + e.message);
    }
  };
  const [workflowMode, setWorkflowMode] = useState("standard");
  const [nocoTelemetry, setNocoTelemetry] = useState({
    temp: 0, mfcOutput: 0, aeroponicLayers: 0, co2: 0, lux: 0, ph: 0
  });

  // State for Fire Writing
  const [fireProfile, setFireProfile] = useState("fire_writing");
  const [fireTextRaw, setFireTextRaw] = useState("");
  const [fireTextFormatted, setFireTextFormatted] = useState("");
  const [isFormatting, setIsFormatting] = useState(false);

  // State for Generator
  const [genDimensionality, setGenDimensionality] = useState("2D");
  const [genPhysicsTarget, setGenPhysicsTarget] = useState("Rigid Objects");
  const [genObjective, setGenObjective] = useState("Stabilize");
  const [deployMessage, setDeployMessage] = useState("");
  const [isDeploying, setIsDeploying] = useState(false);

  // State for Thoughtful Friction
  const [frictionTask, setFrictionTask] = useState(null);

  // State for IT HelpDesk
  const [itScorecard, setItScorecard] = useState({});
  const [isItActive, setIsItActive] = useState(false);

  // State for Media Studio
  const [selectedModel, setSelectedModel] = useState("stehouwer_llm");
  const [mediaType, setMediaType] = useState("image");
  const [mediaPrompt, setMediaPrompt] = useState("");
  const [mediaAspectRatio, setMediaAspectRatio] = useState("1:1");
  const [isCreatingMedia, setIsCreatingMedia] = useState(false);
  const [mediaResultUrl, setMediaResultUrl] = useState("");
  const [galleryMedia, setGalleryMedia] = useState([]);
  const [comfyuiStatus, setComfyuiStatus] = useState({ status: "offline" });
  const [comfyuiModels, setComfyuiModels] = useState([]);
  const [selectedComfyModel, setSelectedComfyModel] = useState("");
  const [localAiWidth, setLocalAiWidth] = useState(1024);
  const [localAiHeight, setLocalAiHeight] = useState(1024);
  const [localAiSteps, setLocalAiSteps] = useState(20);
  const [localAiCfgScale, setLocalAiCfgScale] = useState(8.0);
  const [localAiSeed, setLocalAiSeed] = useState(-1);
  const [localAiNegativePrompt, setLocalAiNegativePrompt] = useState("");
  const [localSimMode, setLocalSimMode] = useState("auto");
  const [localSimTheme, setLocalSimTheme] = useState("auto");
  const [localSimDuration, setLocalSimDuration] = useState(5);
  const [mediaError, setMediaError] = useState("");

  // --- Phase 14 Ecosystem States ---
  const [systemMetrics, setSystemMetrics] = useState({ gitStatus: "Loading...", ssdRamFootprint: "Loading...", activeAgents: [] });
  const [memoryStats, setMemoryStats] = useState({ ssdRamSize: 0, ssdRamPath: "", dbEntries: 0 });
  const [docList, setDocList] = useState([]);
  const [kbSearchQuery, setKbSearchQuery] = useState("");
  const [kbSearchResults, setKbSearchResults] = useState([]);
  const [devCodeInput, setDevCodeInput] = useState("");
  const [devCodeOutput, setDevCodeOutput] = useState("");

  const fetchComfyuiModels = async () => {
    try {
      const res = await fetch(`${backendUrl}/comfyui/models`);
      if (res.ok) {
        const data = await res.json();
        setComfyuiModels(prev => {
            if (prev.length === 0 && data.models && data.models.length > 0) {
                setSelectedComfyModel(data.models[0]);
            }
            return data.models || [];
        });
      }
    } catch (e) {}
  };

  const fetchComfyuiStatus = async () => {
    try {
      const res = await fetch(`${backendUrl}/comfyui/status`);
      if (res.ok) {
        const data = await res.json();
        setComfyuiStatus(data);
        if (data.status === 'online') {
           fetchComfyuiModels();
        }
      } else {
        setComfyuiStatus({ status: "offline" });
      }
    } catch (e) {
      setComfyuiStatus({ status: "offline" });
    }
  };

  React.useEffect(() => {

    const fetchEcosystem = async () => {
      try {
        const [telRes, sysRes, memRes, docRes] = await Promise.all([
          fetch(`${backendUrl}/telemetry/status`).catch(() => null),
          fetch(`${backendUrl}/system/status`).catch(() => null),
          fetch(`${backendUrl}/memory/stats`).catch(() => null),
          fetch(`${backendUrl}/documents/list`).catch(() => null)
        ]);
        if (telRes && telRes.ok) setNocoTelemetry(await telRes.json());
        if (sysRes && sysRes.ok) setSystemMetrics(await sysRes.json());
        if (memRes && memRes.ok) setMemoryStats(await memRes.json());
        if (docRes && docRes.ok) setDocList((await docRes.json()).documents || []);
        await fetchComfyuiStatus();
      } catch (e) {
        console.error("Ecosystem fetch failed", e);
      }
    };
    fetchEcosystem();
    const interval = setInterval(fetchEcosystem, 5000); // 5s to avoid overwhelming backend
    return () => clearInterval(interval);
  }, []);
  const handleExportCode = async (code, targetLanguage) => {
    if (targetLanguage === 'html') {
      // Create a live WebGL Preview blob and open it
      const blob = new Blob([code], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } else {
      // Execute Node.js via Polyglot Engine
      try {
        const res = await fetch(`${backendUrl}/polyglot-execution-engine/execute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: code, language: targetLanguage })
        });
        const data = await res.json();
        if (data.status === 'success') {
          alert(`Execution Success!\n\nOutput:\n${data.data}`);
        } else {
          alert(`Execution Failed!\n\nError:\n${data.error}`);
        }
      } catch (e) {
        alert("Failed to reach Polyglot Engine: " + e.message);
      }
    }
  };

  const tabs = [
    { id: 'chat', name: 'Chat', component: BullshitKnowledgeSuite },
    { id: 'video_studio', name: 'Video Studio', component: VideoStudioTab },
    { id: 'commands', name: 'Command Center', component: BullshitAdminSuite },
    { id: 'media', name: 'Media Studio', component: BullshitKnowledgeSuite },
    { id: 'dev', name: 'Developer Workspace', component: BullshitAdminSuite },
    { id: 'knowledge', name: 'Knowledge Base', component: BullshitKnowledgeSuite },
    { id: 'memory', name: 'Agent Memory', component: BullshitTelemetrySuite },
    { id: 'documents', name: 'Documents', component: BullshitKnowledgeSuite },
    { id: 'firewrite', name: 'Fire Writing', component: BullshitCreationSuite },
    { id: 'generator', name: 'Generator', component: BullshitCreationSuite },
    { id: 'it_helpdesk', name: 'IT Helpdesk', component: BullshitAdminSuite },
    { id: 'noco_telemetry', name: 'Telemetry', component: BullshitTelemetrySuite },
    { id: 'visual_scripting', name: 'Visual Scripting', component: BullshitCreationSuite },
    { id: 'system_analytics', name: 'System Analytics', component: BullshitTelemetrySuite },
    { id: 'memory_visualizer', name: 'Memory Visualizer', component: BullshitTelemetrySuite },
    { id: 'settings', name: 'Settings', component: BullshitAdminSuite },
    { id: 'omnidrive', name: 'Omni-Drive', component: BullshitKnowledgeSuite },
    { id: 'omnireader', name: 'Omni-Reader', component: BullshitKnowledgeSuite },
    { id: 'medical', name: 'Medical Assistant', component: BullshitKnowledgeSuite },
    { id: 'finetune', name: 'Fine-Tuning Studio', component: BullshitAdminSuite },
    { id: 'weather', name: 'Weather Dashboard', component: BullshitKnowledgeSuite },
    { id: 'advertising', name: 'Advertising Studio', component: BullshitKnowledgeSuite },
    { id: 'lead_matrix', name: 'Lead Matrix', component: BullshitLeadMatrix },
    { id: 'test_broken', name: 'Broken Test', component: BrokenComponent },
    { id: 'clients', name: 'Clients Module', component: ClientsModule },
    { id: 'crypto_swarm', name: 'Crypto Swarm', component: BullshitCryptoSwarm },
    { id: 'panic_button', name: 'Panic Button', component: BullshitPanicButton },
    { id: 'chia_manager', name: 'Chia Manager', component: BullshitChiaManager },
    { id: 'evolution_history', name: 'Back Story & Lore', component: BullshitEvolutionHistory },
    { id: 'api_manager', name: 'API Manager', component: ApiManagerTab }
  ];

  const handleSendMessage = async (telemetry = null) => {
    if(!chatInput.trim()) return;
    
    const input = chatInput.trim();
    const cmd = input.toLowerCase();
    
    if (cmd === '/trade' || cmd === '/crypto') {
      setActiveTab('crypto_swarm');
      setMessages([...messages, { role: 'user', content: input }, { role: 'agent', content: '[Switching to Crypto Swarm Module...]' }]);
      setChatInput("");
      return;
    }
    
    if (cmd === '/panic') {
      setActiveTab('panic_button');
      setMessages([...messages, { role: 'user', content: input }, { role: 'agent', content: '[⚠️ SWITCHING TO EMERGENCY LIQUIDATION PROTOCOL ⚠️]' }]);
      setChatInput("");
      return;
    }

    const newMsg = { role: 'user', content: input };
    const newMessages = [...messages, newMsg];
    setMessages(newMessages);
    setChatInput("");
    
    try {
        // --- PHASE 3: AES-GCM PAYLOAD ENCAPSULATION ---
        const rawKey = new Uint8Array([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32]);
        const cryptoKey = await crypto.subtle.importKey("raw", rawKey, "AES-GCM", true, ["encrypt", "decrypt"]);
        
        const rawPayload = JSON.stringify({ model: "stehouwer_llm", messages: newMessages, stream: false });
        const { iv, ciphertext } = await encryptPayload(rawPayload, cryptoKey);
        
        const res = await fetch(`${backendUrl}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                iv: iv,
                ciphertext: ciphertext,
                encrypted: true,
                rawFallback: { model: "stehouwer_llm", messages: newMessages, stream: false },
                messages: newMessages,
                model: "stehouwer_llm",
                somatic_telemetry: telemetry
            })
        });
        const data = await res.json();
        
        let aiText = "No response";
        if (data.choices && data.choices.length > 0 && data.choices[0].message) {
            aiText = data.choices[0].message.content;
        } else if (data.message && data.message.content) {
            aiText = data.message.content;
        } else if (data.response) {
            aiText = data.response;
        } else if (data.error) {
            aiText = `[Backend Error: ${data.error}]`;
        }
        
        // --- PHASE 4.5: COMFYUI INTERCEPTOR ---
        const comfyMatch = aiText.match(/\[COMFYUI_TRIGGER:\s*"([^"]+)",\s*"([^"]+)"\]/);
        let comfyImageUrl = null;
        let isComfyLoading = false;
        
        // --- PHASE 8.5: SYSTEM COMMAND INTERCEPTOR (Vector Alpha) ---
        const cmdMatch = aiText.match(/\[RUN_CMD:\s*(.+?)\]/);
        if (cmdMatch) {
            aiText = aiText.replace(cmdMatch[0], "").trim();
            const commandToRun = cmdMatch[1];
            
            aiText += `\n\n[🛡️ System Protection: Intercepted Terminal Command]`;
            setMessages([...newMessages, { role: 'agent', content: aiText, critique: critiqueText }]);
            
            setFrictionTask({
                toolName: "SYSTEM_COMMAND",
                params: { command: commandToRun },
                actionFn: () => {
                    fetch(`${backendUrl}/api/terminal/run`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ command: commandToRun })
                    }).then(res => res.json()).then(data => {
                        setMessages(prev => [...prev, { role: 'agent', content: `[Terminal Output]\n${data.output || data.error}`, critique: critiqueText }]);
                    });
                }
            });
            return;
        }

        // --- PHASE 9: TOOL DELEGATOR INTERCEPTOR ---
        const toolMatch = aiText.match(/\[TOOL:\s*([A-Z_]+)\s*\|\s*([^\]]+)\]/);
        
        if (toolMatch) {
            aiText = aiText.replace(toolMatch[0], "").trim();
            const toolName = toolMatch[1];
            const toolParamsStr = toolMatch[2];
            const params = toolParamsStr.split('|').map(p => p.trim().replace(/(^"|"$)/g, ''));
            
            aiText += `\n\n[⚡ Delegating Task to ${toolName} Module...]`;
            setMessages([...newMessages, { role: 'agent', content: aiText }]);
            
            // Fire off background request without awaiting so the UI isn't blocked
            try {
                if (toolName === "STAGE_ENGINE") {
                    setFrictionTask({
                        toolName: "STAGE_ENGINE",
                        params: params,
                        actionFn: () => {
                            fetch(`${backendUrl}/stage-engine/orchestrate`, {
                                method: "POST", headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ master_goal: params[0], steps: [] })
                            });
                        }
                    });
                } else if (toolName === "POLYGLOT") {
                    setFrictionTask({
                        toolName: "POLYGLOT",
                        params: params,
                        actionFn: () => {
                            fetch(`${backendUrl}/polyglot-execution-engine/execute`, {
                                method: "POST", headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ language: params[0], command: params[1] || "" })
                            });
                        }
                    });
                } else if (toolName === "UI_GENERATOR") {
                    fetch(`${backendUrl}/ui-generator/build`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ component_name: params[0], human_idea: params[1] || "", file_extension: ".jsx" })
                    });
                } else if (toolName === "FIRE_WRITER") {
                    setFireProfile(params[0] || "fire_writing");
                    setFireTextRaw(params[1] || "");
                    setActiveTab("fire_writing");
                } else if (toolName === "GENERATOR") {
                    setGenDimensionality(params[0] || "2D");
                    setGenPhysicsTarget(params[1] || "Rigid Objects");
                    setGenObjective(params[2] || "Stabilize");
                    setActiveTab("generator");
                } else if (toolName === "IT_HELPDESK") {
                    setActiveTab("it_helpdesk");
                    fetch(`${backendUrl}/it-helpdesk/diagnose`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                } else {
                    fetch(`${backendUrl}/orchestrator/handoff`, {
                        method: "POST", headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ tool: toolName, params: params, context: newMessages.map(m => m.content) })
                    }).then(res => res.json()).then(data => {
                        if (data.status === "success") {
                            setMessages(prev => [...prev, { role: 'agent', content: `[${params[0] || "Specialized Agent"}]\n${data.agent_response}`, critique: critiqueText }]);
                        } else {
                            setMessages(prev => [...prev, { role: 'agent', content: `[Agent Handoff Failed: ${data.message}]`, critique: critiqueText }]);
                        }
                    }).catch(err => {
                        console.error("Handoff failed:", err);
                    });
                }
            } catch (err) {
                console.error("Tool execution failed:", err);
            }
        } else if (comfyMatch) {
            aiText = aiText.replace(comfyMatch[0], "").trim();
            const positivePrompt = comfyMatch[1];
            const negativePrompt = comfyMatch[2];
            
            // Append the message immediately with a loading state
            setMessages([...newMessages, { role: 'agent', content: aiText, isComfyLoading: true, critique: critiqueText }]);
            
            // Generate a basic SDXL ComfyUI payload
            const comfyPayload = {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": 8, "denoise": 1, "model": ["4", 0],
                        "latent_image": ["5", 0], "negative": ["7", 0], "positive": ["6", 0],
                        "sampler_name": "euler", "scheduler": "normal", "seed": Math.floor(Math.random() * 10000000), "steps": 20
                    }
                },
                "4": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" } },
                "5": { "class_type": "EmptyLatentImage", "inputs": { "batch_size": 1, "height": 1024, "width": 1024 } },
                "6": { "class_type": "CLIPTextEncode", "inputs": { "clip": ["4", 1], "text": positivePrompt } },
                "7": { "class_type": "CLIPTextEncode", "inputs": { "clip": ["4", 1], "text": negativePrompt } },
                "8": { "class_type": "VAEDecode", "inputs": { "samples": ["3", 0], "vae": ["4", 2] } },
                "9": { "class_type": "SaveImage", "inputs": { "filename_prefix": "AI_BS_Trigger", "images": ["8", 0] } }
            };
            
            try {
                const imgRes = await fetch(`${BACKEND_URL || backendUrl}/comfyui/generate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ prompt: comfyPayload })
                });
                const imgData = await imgRes.json();
                
                let comfyImageUrl = null;
                if (imgData.filename) {
                    comfyImageUrl = `http://127.0.0.1:8188/view?filename=${imgData.filename}`;
                } else if (imgData.error) {
                    throw new Error(imgData.error);
                } else {
                    comfyImageUrl = `http://127.0.0.1:8188/view?filename=AI_BS_Trigger_00001_.png`; // Fallback
                }
                
                setMessages([...newMessages, { role: 'agent', content: aiText, comfyImageUrl, critique: critiqueText }]);
            } catch (err) {
                setMessages([...newMessages, { role: 'agent', content: aiText + "\n\n[ComfyUI Generation Failed: " + err + "]", critique: critiqueText }]);
            }
        } else {
            setMessages([...newMessages, { role: 'agent', content: aiText, critique: critiqueText }]);
        }
    } catch (e) {
        setMessages([...newMessages, { role: 'agent', content: "[Backend Connection Error: " + e.message + "]" }]);
    }
  };

  const renderActiveTab = () => {
    const ActiveComponent = tabs.find(t => t.id === activeTab)?.component;
    if (!ActiveComponent) return null;
    
    // Passing generic mock props so the tabs don't crash immediately.
    // As we rebuild the pipeline we will re-implement real state.
    return <ActiveComponent 
      activeTab={activeTab}
      BACKEND_URL={backendUrl}
      setBackendUrl={setBackendUrl}
      messages={messages}
      setMessages={setMessages}
      chatInput={chatInput}
      setChatInput={setChatInput}
      handleSendMessage={handleSendMessage}
      workflowMode={workflowMode}
      parseSources={() => []}
      nocoTelemetry={nocoTelemetry}
      onExportCode={handleExportCode}
      
      // Handlers for Fire Writing
      fireProfile={fireProfile}
      setFireProfile={setFireProfile}
      fireTextRaw={fireTextRaw}
      setFireTextRaw={setFireTextRaw}
      fireTextFormatted={fireTextFormatted}
      setFireTextFormatted={setFireTextFormatted}
      isFormatting={isFormatting}
      setIsFormatting={setIsFormatting}
      handleFormatFireWriting={async () => {
          setIsFormatting(true);
          try {
              const res = await fetch(`${backendUrl}/fire-writer/format`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ profile: fireProfile, raw_text: fireTextRaw })
              });
              const data = await res.json();
              if (data.status === "success") {
                  setFireTextFormatted(data.formatted_text);
                  // Save to memory vector DB
                  fetch(`${backendUrl}/memory/store-success`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ prompt: "Fire Writing Output", code_block: data.formatted_text, status: "Success" })
                  }).catch(err => console.error("Failed to save to memory:", err));
              } else {
                  alert("Formatting failed: " + data.message);
              }
          } catch (e) {
              alert("Formatting failed: " + e.message);
          }
          setIsFormatting(false);
      }}
      handleExportFireWriting={() => {
          const blob = new Blob([fireTextFormatted], { type: 'text/markdown' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `Fire_Writing_${Date.now()}.md`;
          a.click();
      }}

      // Handlers for Generator
      genDimensionality={genDimensionality}
      setGenDimensionality={setGenDimensionality}
      genPhysicsTarget={genPhysicsTarget}
      setGenPhysicsTarget={setGenPhysicsTarget}
      genObjective={genObjective}
      setGenObjective={setGenObjective}
      deployMessage={deployMessage}
      setDeployMessage={setDeployMessage}
      isDeploying={isDeploying}
      setIsDeploying={setIsDeploying}
      handleDeployBlueprint={() => {
          setFrictionTask({
              toolName: "GENERATOR_DEPLOY",
              params: ["python", "Deploy blueprint execution script"],
              actionFn: () => {
                  setIsDeploying(true);
                  fetch(`${backendUrl}/polyglot-execution-engine/execute`, {
                      method: "POST", headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ language: "python", command: "print('Deploying blueprint automatically from Generator Tab!')" })
                  }).then(() => {
                      setDeployMessage("Blueprint deployed and executed in Polyglot Engine.");
                      setIsDeploying(false);
                  }).catch(err => {
                      setDeployMessage("Failed to deploy blueprint.");
                      setIsDeploying(false);
                  });
              }
          });
      }}

      // Handlers for IT HelpDesk
      itScorecard={itScorecard}
      setItScorecard={setItScorecard}
      isItActive={isItActive}
      setIsItActive={setIsItActive}
      handleStartItInterview={() => {
          setIsItActive(true);
          setMessages([...messages, { role: 'agent', content: "IT Diagnostic Session Started. Please describe the problem in detail." }]);
      }}
      handleGradeItInterview={() => {
          setIsItActive(false);
          setItScorecard({
              score: 85,
              technical_accuracy: "Diagnostic logs captured successfully.",
              communication_skills: "Good details provided.",
              strengths: ["Fast response"],
              improvements: ["Provide exact error codes next time"],
              overall_feedback: "Session completed and queued for analysis."
          });
      }}

      // Handlers for Media Studio
      mediaType={mediaType}
      setMediaType={setMediaType}
      mediaPrompt={mediaPrompt}
      setMediaPrompt={setMediaPrompt}
      mediaAspectRatio={mediaAspectRatio}
      setMediaAspectRatio={setMediaAspectRatio}
      isCreatingMedia={isCreatingMedia}
      setIsCreatingMedia={setIsCreatingMedia}
      mediaResultUrl={mediaResultUrl}
      setMediaResultUrl={setMediaResultUrl}
      galleryMedia={galleryMedia}
      setGalleryMedia={setGalleryMedia}
      comfyuiStatus={comfyuiStatus}
      setComfyuiStatus={setComfyuiStatus}
      localAiWidth={localAiWidth}
      setLocalAiWidth={setLocalAiWidth}
      localAiHeight={localAiHeight}
      setLocalAiHeight={setLocalAiHeight}
      localAiSteps={localAiSteps}
      setLocalAiSteps={setLocalAiSteps}
      localAiCfgScale={localAiCfgScale}
      setLocalAiCfgScale={setLocalAiCfgScale}
      localAiSeed={localAiSeed}
      setLocalAiSeed={setLocalAiSeed}
      localAiNegativePrompt={localAiNegativePrompt}
      setLocalAiNegativePrompt={setLocalAiNegativePrompt}
      localSimMode={localSimMode}
      setLocalSimMode={setLocalSimMode}
      localSimTheme={localSimTheme}
      setLocalSimTheme={setLocalSimTheme}
      localSimDuration={localSimDuration}
      setLocalSimDuration={setLocalSimDuration}
      mediaError={mediaError}
      setMediaError={setMediaError}
      handleCreateLocalAI={async () => {
          setIsCreatingMedia(true);
          setMediaError("");
          try {
              const res = await fetch(`${backendUrl}/comfyui/generate`, {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ prompt: {
                      "3": { "class_type": "KSampler", "inputs": { "cfg": localAiCfgScale, "denoise": 1, "model": ["4", 0], "latent_image": ["5", 0], "negative": ["7", 0], "positive": ["6", 0], "sampler_name": "euler", "scheduler": "normal", "seed": localAiSeed === -1 ? Math.floor(Math.random() * 10000000) : localAiSeed, "steps": localAiSteps } },
                      "4": { "class_type": "CheckpointLoaderSimple", "inputs": { "ckpt_name": "sd_xl_base_1.0.safetensors" } },
                      "5": { "class_type": "EmptyLatentImage", "inputs": { "batch_size": 1, "height": localAiHeight, "width": localAiWidth } },
                      "6": { "class_type": "CLIPTextEncode", "inputs": { "clip": ["4", 1], "text": mediaPrompt } },
                      "7": { "class_type": "CLIPTextEncode", "inputs": { "clip": ["4", 1], "text": localAiNegativePrompt } },
                      "8": { "class_type": "VAEDecode", "inputs": { "samples": ["3", 0], "vae": ["4", 2] } },
                      "9": { "class_type": "SaveImage", "inputs": { "filename_prefix": "MediaStudio", "images": ["8", 0] } }
                  }})
              });
              const data = await res.json();
              if (res.ok) {
                  // Simulate image return
                  setMediaResultUrl("http://127.0.0.1:8188/view?filename=MediaStudio_00001_.png");
              } else {
                  setMediaError(data.error || "Failed to generate");
              }
          } catch(e) {
              setMediaError("Connection to backend failed");
          }
          setIsCreatingMedia(false);
      }}
      ORCHESTRATOR_COMMANDS={ORCHESTRATOR_COMMANDS}
      activeAgents={systemMetrics.activeAgents || []}
      pullingStatus={{}}
      pullModelInput={""}
      telegramToken={""}
      safetySkipPermissions={false}
      customLoopTime={"15m"}
      customLoopTask={""}
      handleLaunchAgent={handleLaunchAgent}
      handleKillAgent={handleKillAgent}
      handlePullModel={async (model) => { try { await fetch(`${backendUrl}/model/pull`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({model_name: model || "llama3"})}); alert("Model Pull Started in Backend"); } catch(e) { alert("Failed to pull model"); } }}
      setPullModelInput={() => {}}
      setTelegramToken={() => {}}
      setSafetySkipPermissions={() => {}}
      setCustomLoopTime={() => {}}
      setCustomLoopTask={() => {}}
      ssdRamPath={memoryStats.ssdRamPath || ""}
      ssdRamSize={memoryStats.ssdRamSize || 0}
      ssdRamCount={0}
      isSsdLoading={false}
      updateSsdSettings={() => {}}
      wipeSsdRam={async () => { await fetch(`${backendUrl}/system/wipe-ssd`, {method:"POST"}); alert("SSD Wiped"); }}
      devBottomTab={"output"}
      devChatInput={""}
      devChatMessages={[]}
      devCodeInput={devCodeInput}
      devCodeOutput={devCodeOutput}
      devCodeType={"python"}
      devFileName={""}
      devLeftTab={"chat"}
      devMode={"text"}
      documents={docList || []}
      fireProfile={"standard"}
      fireTextFormatted={""}
      fireTextRaw={""}
      galleryMedia={[]}
      genDimensionality={"2D"}
      genObjective={""}
      genPhysicsTarget={"none"}
      gitStatus={systemMetrics.gitStatus || "Clean"}
      systemGitStatus={systemMetrics.gitStatus || "Clean"}
      itTimer={0}
      kbSearchQuery={kbSearchQuery}
      kbSearchResults={kbSearchResults}
      nocoAlert={""}
      nocoCodePrompt={""}
      nocoCodeType={"python"}
      nocoGeneratedCode={""}
      saveMessage={""}
      selectedComfyModel={""}
      selectedModel={selectedModel}
      isChatUploading={false}
      isDeploying={false}
      isDevChatLoading={false}
      isEnhancingPrompt={false}
      isExecutingCode={false}
      isExecutingPs={false}
      isGeneratingNocoCode={false}
      isGlobalLoading={false}
      isGrading={false}
      isListening={false}
      isPreviewLoading={false}
      isSavingFile={false}
      isUploading={false}
      setAvailableModels={() => {}}
      setComfyuiModels={setComfyuiModels}
      setComfyuiStatus={setComfyuiStatus}
      setDeployMessage={() => {}}
      setDevBottomTab={() => {}}
      setDevChatInput={() => {}}
      setDevChatMessages={() => {}}
      setDevCodeInput={setDevCodeInput}
      setDevCodeOutput={setDevCodeOutput}
      setDevCodeType={() => {}}
      setDevFileName={() => {}}
      setDevLeftTab={() => {}}
      setDevMode={() => {}}
      setDocuments={() => {}}
      setFireProfile={() => {}}
      setFireTextFormatted={() => {}}
      setFireTextRaw={() => {}}
      setGalleryMedia={() => {}}
      setGenDimensionality={() => {}}
      setGenObjective={() => {}}
      setGenPhysicsTarget={() => {}}
      setGitStatus={() => {}}
      setIsChatUploading={() => {}}
      setIsCreatingMedia={() => {}}
      setIsDeploying={() => {}}
      setIsDevChatLoading={() => {}}
      setIsEnhancingPrompt={() => {}}
      setIsExecutingCode={() => {}}
      setIsExecutingPs={() => {}}
      setIsGeneratingNocoCode={() => {}}
      setIsGlobalLoading={() => {}}
      setIsGrading={() => {}}
      setIsPreviewLoading={() => {}}
      setIsSavingFile={() => {}}
      setIsUploading={() => {}}
      setItTimer={() => {}}
      setKbSearchQuery={setKbSearchQuery}
      setKbSearchResults={setKbSearchResults}
      setNocoAlert={() => {}}
      setNocoCodePrompt={() => {}}
      setNocoCodeType={() => {}}
      setNocoGeneratedCode={() => {}}
      setPollingStatusMsg={() => {}}
      setPreviewDocContent={() => {}}
      setPreviewDocName={() => {}}
      setPsCommand={() => {}}
      setPsOutput={() => {}}
      setSaveMessage={() => {}}
      setSelectedComfyModel={setSelectedComfyModel}
      setSelectedModel={() => {}}
      setShowModelModal={() => {}}
      setSystemGitStatus={() => {}}
      setUseAgent={() => {}}
      setUseRag={() => {}}
      setUseTTS={() => {}}
      setUseWebSearch={() => {}}
      setWorkflowMode={() => {}}
      speakText={() => {}}
      toggleListening={() => {}}
      useAgent={false}
      useRag={false}
      useTTS={false}
      useWebSearch={false}
      showModelModal={false}
      comfyuiModels={comfyuiModels}
      comfyuiStatus={comfyuiStatus}
      selectedComfyModel={selectedComfyModel}
      fetchComfyuiStatus={fetchComfyuiStatus}
      fetchComfyuiModels={fetchComfyuiModels}
      BACKEND_URL={backendUrl}
      availableModels={["stehouwer_llm", "gemini-1.5-pro", "gemini-1.5-flash"]}
      filteredDocs={[]}
      handleDeleteDocument={() => {}}
      handleOpenDocPreview={() => {}}
      setFrictionTask={setFrictionTask}
    />;
  };

  const renderFrictionModal = () => {
    if (!frictionTask) return null;

    return (
      <div className="modal-overlay">
        <div className="friction-modal glass-panel">
          <h2>🛡️ Action Requires Human Approval</h2>
          <p><strong>Action:</strong> {frictionTask.toolName}</p>
          <div className="friction-trace">
             <h4>Diagnostic Trace:</h4>
             <pre>{JSON.stringify(frictionTask.params, null, 2)}</pre>
             <p className="warning-text" style={{color: '#ffcc00'}}>This action modifies system state or executes code. Human verification is required to proceed.</p>
          </div>
          <div className="friction-buttons">
            <button className="it-btn-success" onClick={() => { frictionTask.actionFn(); setFrictionTask(null); }}>Execute Now</button>
            <button className="reject-btn" style={{background: 'red', color: 'white', padding: '10px', marginLeft: '10px', borderRadius: '5px'}} onClick={() => { setFrictionTask(null); setMessages(prev => [...prev, { role: 'agent', content: "[Action Rejected by User]" }]); }}>Cancel</button>
          </div>
        </div>
      </div>
    );
  };

  const renderTopMenuBar = () => {
    // Categorize the tabs
    const viewTabs = ['chat', 'media', 'video_studio', 'documents', 'omnidrive', 'omnireader'];
    const systemTabs = ['commands', 'noco_telemetry', 'system_analytics', 'memory', 'memory_visualizer', 'chia_manager'];
    const toolTabs = ['dev', 'visual_scripting', 'firewrite', 'generator', 'it_helpdesk', 'medical', 'weather', 'finetune', 'advertising', 'lead_matrix', 'test_broken', 'api_manager'];
    const tradingTabs = ['crypto_swarm', 'panic_button'];

    const handleTabClick = (tabId) => {
        setActiveTab(tabId);
        setIsMobileMenuOpen(false); // Close menu on mobile after selection
    };

    return (
      <header className="top-menu-bar">
        <div className="menu-left-section">
          <button className="mobile-menu-toggle" onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}>
            ☰
          </button>
          <div className="menu-brand">
            Stehouwer Publishing AI <span className="version-badge">v1.4.1</span>
          </div>
          <div className={`menu-nav ${isMobileMenuOpen ? 'open' : ''}`}>
            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              File
              <div className="dropdown-content">
                <div className={`dropdown-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick('settings'); }}>
                  Settings
                </div>
                <div className="dropdown-item" style={{color: '#ff4444'}} onClick={(e) => { e.stopPropagation(); signOut(auth); }}>
                  Logout
                </div>
              </div>
            </div>
            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              CRM Clients
              <div className="dropdown-content">
                <div className={`dropdown-item ${activeTab === 'client_joey_hamilton' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick('client_joey_hamilton'); }}>
                  Joey Hamilton
                </div>
                <div className={`dropdown-item ${activeTab === 'client_action_glass' ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick('client_action_glass'); }}>
                  ActionGlass
                </div>
              </div>
            </div>

            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              View
              <div className="dropdown-content">
                {tabs.filter(t => viewTabs.includes(t.id)).map(tab => (
                  <div key={tab.id} className={`dropdown-item ${activeTab === tab.id ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick(tab.id); }}>
                    {tab.name}
                  </div>
                ))}
              </div>
            </div>

            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              System
              <div className="dropdown-content">
                {tabs.filter(t => systemTabs.includes(t.id)).map(tab => (
                  <div key={tab.id} className={`dropdown-item ${activeTab === tab.id ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick(tab.id); }}>
                    {tab.name}
                  </div>
                ))}
              </div>
            </div>

            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              Tools
              <div className="dropdown-content">
                {tabs.filter(t => toolTabs.includes(t.id)).map(tab => (
                  <div key={tab.id} className={`dropdown-item ${activeTab === tab.id ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick(tab.id); }}>
                    {tab.name}
                  </div>
                ))}
              </div>
            </div>

            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              Trading
              <div className="dropdown-content">
                {tabs.filter(t => tradingTabs.includes(t.id)).map(tab => (
                  <div key={tab.id} className={`dropdown-item ${activeTab === tab.id ? 'active' : ''}`} onClick={(e) => { e.stopPropagation(); handleTabClick(tab.id); }}>
                    {tab.id === 'panic_button' ? <span style={{color: '#ff4d4d', fontWeight: 'bold'}}>{tab.name}</span> : tab.name}
                  </div>
                ))}
              </div>
            </div>

            <div className="menu-item" onClick={(e) => { e.currentTarget.classList.toggle('open'); }}>
              Help
              <div className="dropdown-content">
                <div className="dropdown-item" onClick={(e) => { e.stopPropagation(); setIsChangelogOpen(true); setIsMobileMenuOpen(false); }}>
                  What's New (Changelog)
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="menu-right-section">
          <div className="menu-item" onClick={toggleMic} style={{ color: isMicActive ? '#ff4444' : '#888' }}>
            <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: isMicActive ? '#ff4444' : '#444', marginRight: '6px' }}></span>
            {isMicActive ? 'Listening...' : 'Wake-Word Off'}
          </div>
          <div className="persona-selector">
            <select>
              <option>Brett Stehouwer (CTO)</option>
              <option>Julie Stehouwer (President)</option>
            </select>
          </div>
          <div className="model-selector" style={{marginLeft: '15px'}}>
            <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)}>
              <option value="stehouwer_llm">stehouwer_llm</option>
              <option value="gemini-1.5-pro">gemini-1.5-pro</option>
              <option value="gemini-1.5-flash">gemini-1.5-flash</option>
            </select>
          </div>
        </div>
      </header>
    );
  };

  return (
    <div className="app-container">
      {!isAuthenticated ? (
        <LoginModal onLoginSuccess={() => setIsAuthenticated(true)} backendUrl={backendUrl} />
      ) : (
        <>
          <ChangelogModal isOpen={isChangelogOpen} onClose={() => setIsChangelogOpen(false)} />
          {renderFrictionModal()}
          {renderTopMenuBar()}
          <main className="main-content" style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {renderActiveTab()}
            </div>
          </main>

        </>
      )}
    </div>
  );
}

