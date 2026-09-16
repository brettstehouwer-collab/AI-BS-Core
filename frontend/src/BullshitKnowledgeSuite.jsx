import React, { useState, useEffect, useRef } from 'react';
import ArtifactRenderer from './components/ArtifactRenderer';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area } from 'recharts';
const DOCS = [
  {
    id: 'architecture', label: 'Technical Architecture Report', icon: '🏗️', subtitle: 'Brett Adam Stehouwer',
    url: '/AI-BS_Technical_Architecture_Report.pdf', description: 'System design, AI architecture, data flow diagrams.', badge: 'ARCHITECTURE', badgeColor: '#7209b7',
  },
  {
    id: 'manual', label: 'User Manual', icon: '📖', subtitle: 'AI-BS Platform Guide',
    url: '/AI-BS_User_Manual.pdf', description: 'Complete end-user documentation.', badge: 'USER GUIDE', badgeColor: '#0077b6',
  },
];

export default function BullshitKnowledgeSuite(props) {
  const { 
    activeTab, BACKEND_URL, messages, setMessages, chatInput, setChatInput, handleSendMessage,
    toggleListening, isListening, useRag, setUseRag, useWebSearch, setUseWebSearch, useAgent, setUseAgent,
    messageFeedRef, parseSources, handleDrop, handleDragOver, handlePaste, workflowMode,
    isUploading, handleFileUpload, kbSearchQuery, setKbSearchQuery, kbSearchResults, filteredDocs, handleOpenDocPreview, handleDeleteDocument,
    mediaType, setMediaType, comfyuiStatus, comfyuiModels, selectedComfyModel, setSelectedComfyModel, mediaPrompt, setMediaPrompt,
    isEnhancingPrompt, handleEnhancePrompt, localAiNegativePrompt, setLocalAiNegativePrompt, localAiWidth, setLocalAiWidth,
    localAiHeight, setLocalAiHeight, localAiSteps, setLocalAiSteps, localAiCfgScale, setLocalAiCfgScale, localAiSeed, setLocalAiSeed,
    localSimMode, setLocalSimMode, localSimDuration, setLocalSimDuration, localSimTheme, setLocalSimTheme, mediaAspectRatio, setMediaAspectRatio,
    handleCreateLocalAI, handleCreateLocalSimulation, handleCreateLocalImage, handleCreateMedia, isCreatingMedia, mediaError,
    canvasRef, pollingStatusMsg, localGenProgress, mediaResultUrl, setMediaResultUrl, handleDownloadMedia, galleryMedia, setFrictionTask
  } = props;

  const fileInputRef = useRef(null);
  const [isChatUploading, setIsChatUploading] = useState(false);
  const [vaultTarget, setVaultTarget] = useState("");
  const [isLocalKbUploading, setIsLocalKbUploading] = useState(false);

  const localHandleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setIsLocalKbUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    if (vaultTarget) {
        formData.append("vault", vaultTarget);
    }
    try {
      const response = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/documents/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      alert(`Success: ${data.message}`);
      // Optionally trigger a re-fetch of documents here if there's a prop for it
    } catch (err) {
      console.error("Upload error:", err);
      alert("Failed to upload document.");
    }
    setIsLocalKbUploading(false);
    event.target.value = null; // reset input
  };

  const handleChatFileUpload = (file) => {
    if (!file) return;
    setIsChatUploading(true);
    
    // Quick frontend file ingestion for text-based files
    const textExtensions = ['.txt', '.md', '.js', '.jsx', '.ts', '.tsx', '.py', '.json', '.csv', '.html', '.css', '.bat', '.sh', '.log', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.env'];
    const isTextFile = file.type.startsWith('text/') || textExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

    if (isTextFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target.result;
        setChatInput(prev => prev + `\n\n--- [FILE: ${file.name}] ---\n${content}\n-----------------------\n`);
        setIsChatUploading(false);
      };
      reader.onerror = () => {
        alert("Could not read the file.");
        setIsChatUploading(false);
      };
      reader.readAsText(file);
    } else {
      alert("For now, only text-based code/data files can be directly ingested into the chat context. Please ensure your file is a valid text format.");
      setIsChatUploading(false);
    }
  };

  // Documents Tab State
  const [activeDoc, setActiveDoc] = useState('architecture');
  const [zoom, setZoom] = useState(100);

  // Medical Tab State
  const [isMedicalListening, setIsMedicalListening] = useState(false);
  const [medicalTranscript, setMedicalTranscript] = useState("");

  // Advertising Tab State
  const [advSubTab, setAdvSubTab] = useState('leads');
  const [leads, setLeads] = useState([]);
  const [businessName, setBusinessName] = useState('');
  const [campaignGoal, setCampaignGoal] = useState('');
  const [generatedCopy, setGeneratedCopy] = useState('');
  const [isAdvGenerating, setIsAdvGenerating] = useState(false);
  const [budgets, setBudgets] = useState([]);
  const [telemetryData, setTelemetryData] = useState({ total_reach: 6539017, platforms: [] });
  
  // Lead Action States
  const [auditResults, setAuditResults] = useState({});
  const [videoResults, setVideoResults] = useState({});

  // Platform Post Generator State
  const [postBizName, setPostBizName] = useState('');
  const [postPromo, setPostPromo] = useState('');
  const [postIndustry, setPostIndustry] = useState('Local Business');
  const [postCounty, setPostCounty] = useState('Ottawa County');
  const [isGeneratingPosts, setIsGeneratingPosts] = useState(false);
  const [generatedPosts, setGeneratedPosts] = useState(null);
  const [copiedPlatform, setCopiedPlatform] = useState(null);

  // AIO Strategy State
  const [aioType, setAioType] = useState('schema'); // 'schema' or 'prompt'
  const [aioInput, setAioInput] = useState('');
  const [aioResult, setAioResult] = useState('');
  const [isGeneratingAio, setIsGeneratingAio] = useState(false);

  const handleGenerateAio = async () => {
    if (!aioInput.trim()) return;
    setIsGeneratingAio(true);
    setAioResult('');
    
    let promptText = '';
    if (aioType === 'schema') {
        promptText = `Generate valid JSON-LD Schema.org markup for the following book/author information. Return ONLY the JSON object, with no markdown formatting or backticks.\n\nInfo: ${aioInput}`;
    } else {
        promptText = `Generate a dense, highly structured Q&A prompt injection block optimized for LLMs and AI search crawlers (like Gemini or ChatGPT) based on the following book/author info. Make it keyword-rich and semantic.\n\nInfo: ${aioInput}`;
    }

    try {
      const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/aio-generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: promptText })
      });
      const data = await res.json();
      if (data.status === 'success') {
          // Attempt to clean markdown if it's supposed to be JSON
          let finalContent = data.content;
          if (aioType === 'schema') {
              const jsonMatch = finalContent.match(/\{[\s\S]*\}/);
              if (jsonMatch) finalContent = jsonMatch[0];
          }
          setAioResult(finalContent);
      } else {
          setAioResult(`Error: ${data.message}`);
      }
    } catch (e) {
      setAioResult(`Error: ${e.message}`);
    }
    setIsGeneratingAio(false);
  };


  const handleGeneratePlatformPosts = async () => {
    if (!postBizName.trim() || !postPromo.trim()) return;
    setIsGeneratingPosts(true);
    setGeneratedPosts(null);
    const prompt = `You are an expert platform-native content strategist and Artificial Intelligence Optimization (AIO) specialist. Generate optimized posts for a local business.
CRITICAL AIO REQUIREMENT: Structure the content so it is highly semantic, keyword-dense, and formatted as clear Question & Answer pairs or bullet points where appropriate so that AI bots (ChatGPT, Gemini) will ingest and recommend it.
Return ONLY a valid JSON object with no markdown formatting, no backticks, no code blocks. Just the raw JSON.

Business: ${postBizName}
Industry: ${postIndustry}
Location: ${postCounty}, West Michigan
Promotion: ${postPromo}

Return this exact JSON structure:
{
  "google": { "schema_title": "...", "meta_description": "...", "local_keywords": ["...", "...", "..."] },
  "facebook": { "headline": "...", "body": "...", "cta": "...", "og_description": "..." },
  "instagram": { "caption_hook": "...", "body": "...", "hashtags": "#tag1 #tag2 #tag3 #tag4 #tag5" },
  "tiktok": { "hook_text": "...", "script": "...", "caption_keywords": "keyword1 keyword2 keyword3" },
  "twitter": { "tweet": "...", "card_title": "...", "card_description": "..." },
  "pinterest": { "pin_title": "...", "pin_description": "...", "rich_pin_price": "..." },
  "yelp": { "business_description": "...", "category_tags": ["...", "..."], "special_offer": "..." }
}`;
    try {
      const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/v2/generate_proxy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: 'stehouwer_llm', messages: [{ role: 'user', content: prompt }], stream: false })
      });
      const data = await res.json();
      const raw = data.message?.content || data.response || data.content || '';
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        setGeneratedPosts(JSON.parse(jsonMatch[0]));
      } else {
        setGeneratedPosts({ error: raw });
      }
    } catch (e) {
      setGeneratedPosts({ error: e.message });
    }
    setIsGeneratingPosts(false);
  };

  const handleCopyPost = (platform, text) => {
    navigator.clipboard.writeText(text);
    setCopiedPlatform(platform);
    setTimeout(() => setCopiedPlatform(null), 2000);
  };
  const [loadingAudits, setLoadingAudits] = useState({});
  const [loadingVideos, setLoadingVideos] = useState({});

  const handleAuditLead = async (leadId, bizName) => {
    setLoadingAudits(prev => ({ ...prev, [leadId]: true }));
    try {
      const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/leads/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ business_name: bizName })
      });
      const data = await res.json();
      setAuditResults(prev => ({ ...prev, [leadId]: data }));
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAudits(prev => ({ ...prev, [leadId]: false }));
    }
  };

  const handleGenerateLeadVideo = async (leadId, bizName) => {
    setLoadingVideos(prev => ({ ...prev, [leadId]: true }));
    try {
      const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/leads/generate-video`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          business_name: bizName,
          prompt: `Create a high-impact social media marketing video for ${bizName} focusing on resolving their visibility deficits.`
        })
      });
      const data = await res.json();
      setVideoResults(prev => ({ ...prev, [leadId]: data }));
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingVideos(prev => ({ ...prev, [leadId]: false }));
    }
  };
  
  // Auto-Tasker Agent State
  const [isAutoAgentRunning, setIsAutoAgentRunning] = useState(false);
  const [autoAgentIndex, setAutoAgentIndex] = useState(0);

  const socialPlatforms = [
    'https://www.google.com/maps/contrib/114475333646636636839/',
    'https://www.facebook.com/professional_dashboard/profile_insights/views/',
    'https://www.instagram.com/',
    'https://x.com/',
    'https://studio.youtube.com/',
    'https://www.linkedin.com/',
    'https://www.tiktok.com/',
    'https://www.pinterest.com/'
  ];

  useEffect(() => {
    let interval;
    if (isAutoAgentRunning) {
      interval = setInterval(() => {
        setAutoAgentIndex((prev) => {
          const nextIndex = (prev + 1) % socialPlatforms.length;
          const nextUrl = socialPlatforms[nextIndex];
          const webview = document.getElementById('ghostWebviewFull');
          const input = document.getElementById('ghostBrowserUrlFull');
          if (webview) webview.src = nextUrl;
          if (input) input.value = nextUrl;
          return nextIndex;
        });
      }, 60000); // 60 seconds
    }
    return () => clearInterval(interval);
  }, [isAutoAgentRunning]);

  // Stehouwer Methodology State
  const [geofence, setGeofence] = useState('Ottawa County');
  const [pricingTier, setPricingTier] = useState('495'); 
  const [temporalCommitment, setTemporalCommitment] = useState('90');
  
  const calculateContractValue = () => {
    let base = parseFloat(pricingTier);
    let months = parseInt(temporalCommitment) / 30; // Approx months
    let total = base * months;
    if (temporalCommitment === '180') total = total * 0.90; // 10% Off
    if (temporalCommitment === '365') total = total * 0.85; // 15% Off
    return total;
  };

  // OmniDrive State
  const [odQuery, setOdQuery] = useState("");
  const [odResults, setOdResults] = useState([]);
  const [odIsSearching, setOdIsSearching] = useState(false);
  const [odDestination, setOdDestination] = useState("");

  // OmniReader State
  const [readerText, setReaderText] = useState("");
  const [isReaderPlaying, setIsReaderPlaying] = useState(false);
  const [readerVoice, setReaderVoice] = useState("brett");
  const [spokenKeys, setSpokenKeys] = useState("");
  const audioRef = useRef(null);

  // Live System State (Adapted for Advertising)
  const [frictionTask, setFrictionTaskLocal] = useState(null);
  const [frictionInput, setFrictionInput] = useState("");
  const [deployResult, setDeployResult] = useState("");

  const handleDeployCampaign = () => {
    if (!generatedCopy) return;
    const value = calculateContractValue();
    setFrictionTaskLocal(`Deploy Advertising Campaign: ${businessName} | Total Value: $${value.toFixed(2)}`);
  };

  const executeFrictionTask = async () => {
    if (frictionInput.trim().toUpperCase() !== "EXECUTE") {
      alert("Authorization Failed. Must type EXECUTE.");
      return;
    }
    const value = calculateContractValue();
    setDeployResult(`Campaign Deployed successfully! Baseline Budget Deducted.`);
    setBudgets([{ id: Date.now(), event: `Campaign Launch: ${businessName}`, spent: value, roi: 0 }, ...budgets]);
    setFrictionTaskLocal(null);
    setFrictionInput("");
  };

  const isInitialMountL = useRef(true);
  const isInitialMountB = useRef(true);

  // Load Initial DB State
  useEffect(() => {
    fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/leads`)
      .then(r => r.json()).then(d => { if(d.status === 'success') setLeads(d.leads) });
    fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/budgets`)
      .then(r => r.json()).then(d => { if(d.status === 'success') setBudgets(d.budgets) });
  }, []);

  // Auto-save logic
  useEffect(() => {
    if (isInitialMountL.current) { isInitialMountL.current = false; return; }
    fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/leads`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(leads)
    });
  }, [leads]);

  useEffect(() => {
    if (isInitialMountB.current) { isInitialMountB.current = false; return; }
    fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/budgets`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(budgets)
    });
  }, [budgets]);

  useEffect(() => {
    let tInterval;
    if (activeTab === 'advertising' && advSubTab === 'telemetry') {
      const fetchTelemetry = async () => {
        try {
          const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/telemetry/shadow/aggregate`);
          const data = await res.json();
          if (data.status === 'success') {
            setTelemetryData({ total_reach: data.total_reach || 6539017, platforms: data.platforms });
          }
        } catch (err) {}
      };
      fetchTelemetry();
      tInterval = setInterval(fetchTelemetry, 3000);
    }
    return () => clearInterval(tInterval);
  }, [activeTab, advSubTab, BACKEND_URL]);

  if (activeTab === 'chat' && workflowMode === 'standard') {
    return (
      <div className="chat-container">
        <div className="message-feed" ref={messageFeedRef}>
          {messages?.map((msg, idx) => {
            const isDeviationAudit = msg.role === 'agent' && msg.content.includes("DEVIATION_AUDIT_TRACE:");
            return (
              <div key={idx} className={`chat-message ${msg.role}`}>
                <div className={`avatar ${msg.role === 'user' ? 'user-avatar' : 'ai-avatar'}`}>{msg.role === 'user' ? 'B' : 'AI'}</div>
                <div className="message-bubble">
                  {isDeviationAudit && (
                    <div className="deviation-audit-alert" style={{ backgroundColor: '#ef444420', border: '1px solid #ef4444', padding: '10px', borderRadius: '8px', marginBottom: '10px' }}>
                      <h4 style={{ color: '#ef4444', marginTop: 0 }}>⚠️ DEVIATION AUDIT REQUIRED</h4>
                      <p style={{ fontSize: '0.9em' }}>The AI has hallucinated a deviation from a verified Known-Good baseline in the Living Learning Memory.</p>
                      <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                        <button onClick={() => alert("Deviation Approved.")} style={{ background: '#ef4444', color: 'white', border: 'none', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' }}>Confirm Deviation</button>
                        <button onClick={() => alert("Deviation Rejected.")} style={{ background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', padding: '5px 10px', borderRadius: '4px', cursor: 'pointer' }}>Reject Deviation</button>
                      </div>
                    </div>
                  )}
                  <div className="message-text"><ArtifactRenderer content={msg.content} /></div>
                  {msg.role === 'agent' && msg.context && (
                    <div className="message-sources">
                      <span className="sources-title">📚 Context Referenced:</span>
                      <div className="sources-list">{parseSources(msg.context).map((src, sIdx) => <span key={sIdx} className="source-tag">{src}</span>)}</div>
                    </div>
                  )}
                  {msg.isComfyLoading && <div className="comfy-inline-loading" style={{ marginTop: '10px', padding: '10px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}><span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⚙️</span> Generating image...</div>}
                  {msg.comfyImageUrl && <div className="comfy-inline-image" style={{ marginTop: '10px' }}><img src={msg.comfyImageUrl?.startsWith('http') || msg.comfyImageUrl?.startsWith('data:') || msg.comfyImageUrl?.startsWith('blob:') ? msg.comfyImageUrl : `${BACKEND_URL || ''}${msg.comfyImageUrl?.startsWith('/') ? '' : '/'}${msg.comfyImageUrl}`} alt="AI Generated" style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid var(--border-glow)' }} /></div>}
                </div>
              </div>
            );
          })}
        </div>
        <div className="chat-input-area" onDrop={handleDrop} onDragOver={handleDragOver}>
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={(e) => { if (e.target.files && e.target.files.length > 0) { handleChatFileUpload(e.target.files[0]); e.target.value = null; } }} />
          <div className="chat-input-row">
            <textarea className="chat-input" placeholder={isChatUploading ? "Uploading file..." : "Send a message or paste a file..."} value={chatInput} onChange={(e) => setChatInput(e.target.value)} onPaste={handlePaste} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage(); } }} disabled={isChatUploading} />
            <button className="mic-button upload-btn" onClick={() => fileInputRef.current?.click()} title="Upload File" disabled={isChatUploading} style={{ marginRight: '8px' }}>📎</button>
            <button className={`mic-button ${isListening ? 'listening' : ''}`} onClick={toggleListening} title="Toggle Dictation" disabled={isChatUploading}>🎙️</button>
          </div>
          <div className="chat-input-controls">
            <div className="tool-toggles-container">
              <button className={`tool-toggle-btn ${useRag ? 'active' : ''}`} onClick={() => setUseRag(!useRag)} title="Search Knowledge Base">📚</button>
              <button className={`tool-toggle-btn ${useWebSearch ? 'active' : ''}`} onClick={() => setUseWebSearch(!useWebSearch)} title="Web Search">🌐</button>
              <button className={`tool-toggle-btn ${useAgent ? 'active' : ''}`} onClick={() => setUseAgent(!useAgent)} title="ReAct Agent Mode">🤖</button>
            </div>
            <button className="send-button" onClick={handleSendMessage}>Send</button>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'knowledge') {
    return (
      <div className="kb-container">
          <div className="upload-box" style={{ padding: '20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
            <div className="upload-icon" onClick={() => document.getElementById('kb-file-input').click()} style={{ cursor: 'pointer' }}>📄</div>
            <h3 onClick={() => document.getElementById('kb-file-input').click()} style={{ cursor: 'pointer', margin: 0 }}>{isLocalKbUploading ? 'Ingesting Document...' : 'Upload Data to Vault (.jsonl, .pdf, .docx, .txt)'}</h3>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '10px' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Target Vault:</label>
              <select 
                value={vaultTarget} 
                onChange={(e) => setVaultTarget(e.target.value)}
                style={{ background: 'var(--bg-main)', color: 'var(--text-primary)', border: '1px solid rgba(255,255,255,0.1)', padding: '5px 10px', borderRadius: '4px' }}
              >
                <option value="">[Root Vault]</option>
                <option value="NoCo_Ventures">NoCo_Ventures/</option>
                <option value="Fire_Writing">Fire_Writing/</option>
                <option value="Marketing">Marketing/</option>
                <option value="AI_Architecture">AI_Architecture/</option>
                <option value="Trading_Algos">Trading_Algos/</option>
                <option value="Personal_Journal">Personal_Journal/</option>
                <option value="Code_Snippets">Code_Snippets/</option>
                <option value="System_Logs">System_Logs/</option>
              </select>
            </div>
            
            <p style={{ color: 'var(--text-muted)', marginTop: '8px', textAlign: 'center' }}>Click the icon or title to select a file to ingest into the local vector database.</p>
            <input type="file" id="kb-file-input" accept=".txt,.pdf,.docx,.md,.jsonl,.json,.csv" style={{ display: 'none' }} onChange={localHandleFileUpload} disabled={isLocalKbUploading} />
          </div>
        <div className="kb-search-panel glass-panel" style={{ padding: '20px', borderRadius: '8px', marginBottom: '20px', borderLeft: '4px solid var(--primary)' }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '1.1rem' }}>🛡️ Sovereign Knowledge Vaults Status</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '15px' }}>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 NoCo_Ventures/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 Fire_Writing/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 Marketing/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 AI_Architecture/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 Trading_Algos/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 Personal_Journal/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 Code_Snippets/</strong></div>
            <div style={{ background: 'var(--bg-main)', padding: '10px', borderRadius: '6px' }}><strong>📁 System_Logs/</strong></div>
          </div>
        </div>
        <div className="kb-search-panel glass-panel" style={{ padding: '20px', borderRadius: '8px', marginBottom: '32px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '1.2rem' }}>🔍</span>
            <input type="text" placeholder="Search document index or search deep text contents..." value={kbSearchQuery} onChange={(e) => setKbSearchQuery(e.target.value)} style={{ flex: 1, padding: '10px 16px', background: 'var(--bg-main)' }} />
          </div>
          {kbSearchResults?.length > 0 && (
            <div className="kb-search-results animate-slide-in" style={{ marginTop: '16px' }}>
              <h4 style={{ color: 'var(--accent-neon)', marginBottom: '10px' }}>Deep Content Matches:</h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {kbSearchResults.map((res, rIdx) => (
                  <div key={rIdx} className="search-result-item" style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', border: '1px solid var(--border-glow)', borderRadius: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                      <strong>Source File: {res.source}</strong><span>Similarity Match: {((1 - res.distance) * 100).toFixed(1)}%</span>
                    </div>
                    <p style={{ fontSize: '0.85rem', fontStyle: 'italic', color: 'var(--text-primary)' }}>"{res.content}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        <h3>Current Indexed Documents</h3>
        <div className="doc-list" style={{ marginTop: '16px' }}>
          {filteredDocs?.length === 0 ? <p style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>No documents uploaded yet.</p> : filteredDocs?.map((doc, idx) => (
            <div key={idx} className="doc-item">
              <span>📄</span>
              <strong className="preview-doc-link" onClick={() => handleOpenDocPreview(doc)} title="Click to preview file" style={{ cursor: 'pointer', color: 'var(--accent-neon)' }}>{doc}</strong>
              <span style={{ marginLeft: 'auto', color: 'var(--success-color)', fontSize: '0.9rem', marginRight: '16px' }}>Indexed</span>
              <button className="delete-doc-button" onClick={() => handleDeleteDocument(doc)} style={{ color: '#ef4444', fontSize: '1.2rem', padding: '0 8px', background: 'transparent', border: 'none', cursor: 'pointer' }}>🗑️</button>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === 'documents') {
    const currentDoc = DOCS.find((d) => d.id === activeDoc) || DOCS[0];
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'linear-gradient(135deg, #0a0a14 0%, #0d0d1a 60%, #0a0f1e 100%)', fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
        <div style={{ padding: '20px 28px 16px', borderBottom: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)', backdropFilter: 'blur(10px)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: 'linear-gradient(135deg, #7209b7, #3f37c9)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📂</div>
            <div><h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#e8e8f0' }}>Documentation Library</h2></div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            {DOCS.map((doc) => (
              <button key={doc.id} onClick={() => setActiveDoc(doc.id)} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', border: activeDoc === doc.id ? `1px solid ${doc.badgeColor}66` : '1px solid rgba(255,255,255,0.08)', borderRadius: 10, background: activeDoc === doc.id ? `linear-gradient(135deg, ${doc.badgeColor}22, ${doc.badgeColor}11)` : 'rgba(255,255,255,0.03)', color: activeDoc === doc.id ? '#e8e8f0' : '#6b7280', cursor: 'pointer' }}>
                <span style={{ fontSize: 18 }}>{doc.icon}</span>
                <div style={{ textAlign: 'left' }}><div style={{ fontSize: '0.82rem', fontWeight: 600 }}>{doc.label}</div></div>
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 28px', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.2)' }}>
          <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}><span style={{ color: '#e8e8f0', fontWeight: 600 }}>{currentDoc.icon} {currentDoc.label}</span></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <button onClick={() => setZoom(z => Math.max(50, z - 10))}>−</button>
              <span style={{ fontSize: '0.78rem', color: '#9ca3af', minWidth: 38, textAlign: 'center' }}>{zoom}%</span>
              <button onClick={() => setZoom(z => Math.min(200, z + 10))}>+</button>
            </div>
            <a href={currentDoc.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', padding: '6px 14px', borderRadius: 8, background: '#3f37c922', border: '1px solid #3f37c955', color: '#e8e8f0', textDecoration: 'none' }}>🔗 Open</a>
          </div>
        </div>
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {DOCS.map((doc) => (
            <div key={doc.id} style={{ position: 'absolute', inset: 0, display: activeDoc === doc.id ? 'flex' : 'none', alignItems: 'center', justifyContent: 'center', background: '#1a1a2e', overflow: 'auto' }}>
              <iframe src={`${doc.url}#zoom=${zoom}&toolbar=1&navpanes=0&scrollbar=1`} title={doc.label} style={{ width: `${zoom}%`, minWidth: zoom < 100 ? '100%' : undefined, height: '100%', border: 'none', background: '#fff', boxShadow: '0 8px 48px rgba(0,0,0,0.6)' }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (activeTab === 'media') {
    return (
      <div className="media-workspace-grid">
        <div className="media-panel creator-panel glass-panel">
          <h3>🎨 Media Studio</h3>
          <p className="subtitle">Generate with Imagen 3, Veo 3.1, or Local AI</p>
          <div className="creator-controls">
            <div className="control-group">
              <label>Generate Type:</label>
              <div className="media-type-toggle" style={{ flexWrap: 'wrap', gap: '8px' }}>
                <button className={`type-btn ${mediaType === 'local_ai' ? 'active' : ''}`} onClick={() => setMediaType('local_ai')} style={{ minWidth: '140px' }}>🤖 Local AI (ComfyUI)</button>
                <button className={`type-btn ${mediaType === 'image' ? 'active' : ''}`} onClick={() => { setMediaType('image'); setMediaAspectRatio('1:1'); }} style={{ minWidth: '140px' }}>🖼️ Image</button>
                <button className={`type-btn ${mediaType === 'video' ? 'active' : ''}`} onClick={() => { setMediaType('video'); setMediaAspectRatio('16:9'); }} style={{ minWidth: '140px' }}>🎬 Video</button>
              </div>
            </div>
            {mediaType === 'local_ai' && comfyuiStatus && comfyuiStatus.status === 'online' && (
              <>
                <div className="control-group">
                  <label>Model:</label>
                  <select value={selectedComfyModel} onChange={(e) => setSelectedComfyModel(e.target.value)}>
                    {comfyuiModels?.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
              </>
            )}
            <div className="control-group">
              <label>Prompt:</label>
              <textarea className="media-prompt-input" placeholder="Describe the image you want..." value={mediaPrompt} onChange={(e) => setMediaPrompt(e.target.value)} />
            </div>
            <button className="generate-media-btn" onClick={mediaType === 'local_ai' ? handleCreateLocalAI : handleCreateMedia} disabled={isCreatingMedia || !mediaPrompt?.trim() || (mediaType === 'local_ai' && comfyuiStatus?.status !== 'online')}>
              {isCreatingMedia ? '🎨 Processing...' : '💾 Generate Media'}
            </button>
          </div>
          {mediaError && <div className="media-error-card animate-slide-in"><strong>Error:</strong> {mediaError}</div>}
        </div>
        <div className="media-panel preview-panel glass-panel">
          <h3>👀 Output Preview</h3>
          <div className="media-display-box">
            {isCreatingMedia ? (
              <div className="media-loading-container"><div className="media-spinner">🎨</div><p>{pollingStatusMsg}</p></div>
            ) : mediaResultUrl ? (
              <div className="completed-media-container animate-slide-in">
                {mediaResultUrl.endsWith('.mp4') ? <video src={`${BACKEND_URL}${mediaResultUrl}`} controls autoPlay loop className="preview-media" /> : <img src={`${BACKEND_URL}${mediaResultUrl}`} alt="Generated Art" className="preview-media" />}
                <div className="media-actions"><button onClick={() => handleDownloadMedia(mediaResultUrl)} className="action-btn-download">📥 Save to Disk</button></div>
              </div>
            ) : (
              <div className="media-placeholder"><p>Enter a prompt on the left to begin generation.</p></div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'medical') {
    return (
      <div className="medical-assistant-container glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '20px' }}>
        <h2>AI Deaf Child Clinical Assistant</h2>
        <div style={{ display: 'flex', gap: '20px' }}>
          <div className="scribe-module glass-panel" style={{ flex: 1, padding: '15px' }}>
            <h3>Real-Time Medical Scribe</h3>
            <button style={{ padding: '10px', background: isMedicalListening ? 'red' : 'green', color: 'white', border: 'none', borderRadius: '5px', marginBottom: '10px' }} onClick={() => { setIsMedicalListening(!isMedicalListening); if(!isMedicalListening) setMedicalTranscript("Doctor: How are you feeling today?\n[AI translating...]"); else setMedicalTranscript(""); }}>{isMedicalListening ? "Stop Scribe" : "Start Live Transcription"}</button>
            <pre style={{ background: '#222', padding: '10px', minHeight: '100px', borderRadius: '5px' }}>{medicalTranscript || "Waiting..."}</pre>
          </div>
          <div className="avatar-module glass-panel" style={{ flex: 1, padding: '15px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#111' }}>
            <h3>Sign Language Avatar</h3>
            <div style={{ width: '200px', height: '200px', border: '2px dashed #555', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>[WebGL Avatar]</div>
          </div>
        </div>
      </div>
    );
  }

  if (activeTab === 'omnidrive') {
    const handleOdSearch = async () => {
      if (!odQuery) return;
      setOdIsSearching(true);
      try {
        const res = await fetch(`${BACKEND_URL || `http://${window.location.hostname}:8000`}/api/omnidrive/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query: odQuery, limit: 50 }) });
        const data = await res.json();
        if (data.status === "success") setOdResults(data.results);
      } catch (e) { console.error(e); }
      setOdIsSearching(false);
    };
    return (
      <div className="tab-pane active glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '20px' }}>
        <h1 className="header-glow">Omni-Drive Explorer</h1>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input type="text" value={odQuery} onChange={e => setOdQuery(e.target.value)} placeholder="Search..." className="ai-input" onKeyDown={(e) => e.key === 'Enter' && handleOdSearch()} style={{ flex: 1 }} />
          <button onClick={handleOdSearch} className="it-btn-primary" disabled={odIsSearching}>{odIsSearching ? "Searching..." : "Omni Search"}</button>
        </div>
        <div style={{ marginBottom: '20px', padding: '15px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', borderLeft: '4px solid #ff3366' }}>
          <h3 style={{ color: '#ff3366', marginBottom: '10px' }}>Thoughtful Friction Relocation System</h3>
          <input type="text" value={odDestination} onChange={e => setOdDestination(e.target.value)} placeholder="Set global relocation destination" className="ai-input" style={{ width: '100%' }} />
        </div>
        <div className="telemetry-grid" style={{ flex: 1, overflowY: 'auto' }}>
          <table style={{ width: '100%', color: 'white', textAlign: 'left', borderCollapse: 'collapse' }}>
            <thead><tr style={{ borderBottom: '1px solid rgba(0, 210, 255, 0.3)' }}><th style={{ padding: '10px' }}>Drive</th><th style={{ padding: '10px' }}>Filename</th><th style={{ padding: '10px' }}>Path</th></tr></thead>
            <tbody>
              {odResults.map((r, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}><td style={{ padding: '10px', color: '#00d2ff' }}>{r.drive}</td><td style={{ padding: '10px' }}>{r.filename}</td><td style={{ padding: '10px', fontSize: '0.8em', opacity: 0.8 }}>{r.filepath}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (activeTab === 'omnireader') {
    const handlePlayTTS = async () => {
      if (isReaderPlaying) { if (audioRef.current) audioRef.current.pause(); setIsReaderPlaying(false); return; }
      if (!readerText.trim()) return;
      setIsReaderPlaying(true);
      try {
        const res = await fetch("http://127.0.0.1:8001/tts/speak", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: readerText, voice: readerVoice }) });
        const data = await res.json();
        if (data.status === "success" && data.audio_url && audioRef.current) {
          audioRef.current.src = data.audio_url; audioRef.current.play(); audioRef.current.onended = () => setIsReaderPlaying(false);
        } else { setIsReaderPlaying(false); }
      } catch (e) { setIsReaderPlaying(false); }
    };
    return (
      <div className="omni-reader-container glass-panel" style={{ padding: '20px' }}>
        <h2>Omni-Reader & Accessibility</h2>
        <audio ref={audioRef} style={{ display: 'none' }} />
        <div className="accessibility-bar" style={{ padding: '10px', background: '#333', color: '#0f0', marginBottom: '10px', borderRadius: '5px' }}><strong>Blind Accessibility Listener:</strong> {spokenKeys || "Type anywhere to test key voicing..."}</div>
        <div className="tts-controls">
          <label>Voice Persona: </label>
          <select value={readerVoice} onChange={e => setReaderVoice(e.target.value)} style={{marginBottom: '10px'}}>
            <option value="brett">Brett Stehouwer</option><option value="julie">Julie Stehouwer</option>
          </select>
        </div>
        <textarea placeholder="Paste text here..." value={readerText} onChange={e => setReaderText(e.target.value)} rows={15} style={{ width: '100%', marginBottom: '10px' }} />
        <button onClick={handlePlayTTS} style={{ padding: '10px 20px', background: isReaderPlaying ? 'red' : '#4CAF50', color: 'white', border: 'none', borderRadius: '5px' }}>{isReaderPlaying ? '⏹ Stop' : '▶ Play'}</button>
      </div>
    );
  }

  if (activeTab === 'advertising') {
    // Calculate KPIs
    const totalLeads = leads.length;
    const totalSpend = budgets.reduce((acc, curr) => acc + Number(curr.spent || 0), 0);
    const totalROI = budgets.reduce((acc, curr) => acc + Number(curr.roi || 0), 0);

    return (
      <div className="advertising-workspace adv-workspace-glass" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>

        
        {/* Thoughtful Friction Modal Overlay */}
        {frictionTask && (
          <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999 }}>
            <div style={{ background: '#1e293b', border: '1px solid #ef4444', padding: '30px', borderRadius: '12px', width: '400px', boxShadow: '0 0 30px rgba(239, 68, 68, 0.4)' }}>
              <h3 style={{ color: '#ef4444', marginTop: 0 }}>⚠️ Awaiting Stehouwer Reality Authorization</h3>
              <p style={{ color: 'var(--text-muted)' }}>Intercepted Action: <strong>{frictionTask}</strong></p>
              <p style={{ fontSize: '0.9em', color: '#ffcc00' }}>Type 'EXECUTE' to activate live runtime and proceed.</p>
              <input 
                type="text" 
                value={frictionInput} 
                onChange={e => setFrictionInput(e.target.value)}
                placeholder="Type EXECUTE"
                style={{ width: '100%', padding: '10px', background: 'rgba(0,0,0,0.5)', color: 'white', border: '1px solid #ef4444', borderRadius: '4px', marginBottom: '15px' }}
              />
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={executeFrictionTask} style={{ flex: 1, padding: '10px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>Confirm</button>
                <button onClick={() => { setFrictionTaskLocal(null); setFrictionInput(""); }} style={{ flex: 1, padding: '10px', background: 'transparent', color: '#ef4444', border: '1px solid #ef4444', borderRadius: '4px', cursor: 'pointer' }}>Abort</button>
              </div>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ margin: 0, color: 'var(--accent-neon)' }}>📈 Stehouwer Advertising Dashboard</h2>
        </div>

        <div className="adv-kpi-bar">
          <div className="adv-kpi-card">
            <span className="kpi-label">Total Leads</span>
            <span className="kpi-value">{totalLeads}</span>
          </div>
          <div className="adv-kpi-card">
            <span className="kpi-label">Total Spend</span>
            <span className="kpi-value">${totalSpend.toLocaleString()}</span>
          </div>
          <div className="adv-kpi-card">
            <span className="kpi-label">Total ROI</span>
            <span className="kpi-value green">${totalROI.toLocaleString()}</span>
          </div>
        </div>

        <div className="adv-tabs">
          <button className={`adv-tab-btn ${advSubTab === 'leads' ? 'active' : ''}`} onClick={() => setAdvSubTab('leads')}>🏢 Secure Leads Vault</button>
          <button className={`adv-tab-btn ${advSubTab === 'campaign' ? 'active' : ''}`} onClick={() => setAdvSubTab('campaign')}>🤖 AI Copywriter</button>
          <button className={`adv-tab-btn ${advSubTab === 'platform-posts' ? 'active' : ''}`} onClick={() => setAdvSubTab('platform-posts')} style={{ background: advSubTab === 'platform-posts' ? 'linear-gradient(135deg, #7c3aed, #4f46e5)' : '' }}>🌐 Platform Post Generator</button>
          <button className={`adv-tab-btn ${advSubTab === 'aio' ? 'active' : ''}`} onClick={() => setAdvSubTab('aio')} style={{ background: advSubTab === 'aio' ? 'linear-gradient(135deg, #10b981, #059669)' : '' }}>🧠 AIO Strategy</button>
          <button className={`adv-tab-btn ${advSubTab === 'telemetry' ? 'active' : ''}`} onClick={() => setAdvSubTab('telemetry')}>📡 Telemetry Sniffer</button>
          <button className={`adv-tab-btn ${advSubTab === 'ghost-browser' ? 'active' : ''}`} onClick={() => setAdvSubTab('ghost-browser')}>👻 Ghost Browser</button>
          <button className={`adv-tab-btn ${advSubTab === 'budget' ? 'active' : ''}`} onClick={() => setAdvSubTab('budget')}>💰 Budget Tracker</button>
          <button className={`adv-tab-btn ${advSubTab === 'licensing' ? 'active' : ''}`} onClick={() => setAdvSubTab('licensing')}>🔑 Licensing Portal</button>
        </div>

        <div className="adv-content" style={{ padding: '20px', minHeight: '60vh', overflowY: 'auto' }}>
          
          {advSubTab === 'aio' && (
            <div className="telemetry-panel">
              <h3 style={{ borderBottom: '1px solid rgba(0, 255, 136, 0.2)', paddingBottom: '10px', color: '#10b981' }}>
                🧠 AI Search Optimization (AIO)
              </h3>
              <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '14px', marginBottom: '20px' }}>
                Optimize your books and author profiles for AI Overviews, ChatGPT, and Gemini. Generate Semantic JSON-LD markup or Prompt Injection content for high-authority placements.
              </p>

              <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                <button 
                  onClick={() => setAioType('schema')}
                  style={{ 
                    flex: 1, 
                    padding: '10px', 
                    background: aioType === 'schema' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.05)',
                    border: `1px solid ${aioType === 'schema' ? '#10b981' : 'transparent'}`,
                    color: '#fff',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  📄 JSON-LD Schema Generator
                </button>
                <button 
                  onClick={() => setAioType('prompt')}
                  style={{ 
                    flex: 1, 
                    padding: '10px', 
                    background: aioType === 'prompt' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255,255,255,0.05)',
                    border: `1px solid ${aioType === 'prompt' ? '#10b981' : 'transparent'}`,
                    color: '#fff',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  💉 Prompt Injection Block
                </button>
              </div>

              <div className="control-group">
                <label>Target Info (Book Title, Author, Genre, ISBN, Themes, etc.)</label>
                <textarea
                  className="matrix-input"
                  rows="4"
                  value={aioInput}
                  onChange={(e) => setAioInput(e.target.value)}
                  placeholder="e.g. Title: 'The Matrix Resurrections', Author: 'Lana Wachowski', Genre: 'Sci-Fi', Themes: 'Free Will, Reality, Love'"
                  style={{ width: '100%', resize: 'vertical' }}
                />
              </div>

              <button 
                className="matrix-btn" 
                onClick={handleGenerateAio} 
                disabled={isGeneratingAio}
                style={{ width: '100%', marginTop: '15px', background: 'linear-gradient(90deg, #10b981, #059669)', color: 'white' }}
              >
                {isGeneratingAio ? '⚙️ GENERATING AIO ASSET...' : '⚡ GENERATE ASSET'}
              </button>

              {aioResult && (
                <div style={{ marginTop: '20px', background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '15px', borderRadius: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <span style={{ color: '#10b981', fontWeight: 'bold' }}>{aioType === 'schema' ? 'Schema.org JSON-LD' : 'Semantic Injection Content'}</span>
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(aioResult);
                        alert("Copied to clipboard!");
                      }}
                      style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: 'white', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
                    >
                      📋 Copy
                    </button>
                  </div>
                  <pre style={{ 
                    whiteSpace: 'pre-wrap', 
                    wordBreak: 'break-word', 
                    fontFamily: 'monospace', 
                    fontSize: '13px', 
                    color: '#a3e635',
                    maxHeight: '400px',
                    overflowY: 'auto'
                  }}>
                    {aioResult}
                  </pre>
                </div>
              )}
            </div>
          )}

          {advSubTab === 'leads' && (
            <div className="adv-panel animate-slide-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0 }}>Active Lead Pipeline</h3>
                <button className="action-btn-download send-button" onClick={() => setLeads([{ id: Date.now(), business: 'New Business', contact: 'Unknown', status: 'New', value: '0' }, ...leads])}>+ Add Lead</button>
              </div>
              <table className="adv-data-table">
                <thead>
                  <tr>
                    <th>Business Name</th>
                    <th>Contact</th>
                    <th>Status</th>
                    <th>Est. Value ($)</th>
                    <th>Social Audit</th>
                    <th>Video Campaign</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {leads.length === 0 && <tr><td colSpan="7" style={{textAlign:'center', color:'var(--text-muted)'}}>No leads found.</td></tr>}
                  {leads.map(lead => {
                    const audit = auditResults[lead.id];
                    const video = videoResults[lead.id];
                    return (
                      <tr key={lead.id}>
                        <td><input type="text" value={lead.business} onChange={e => setLeads(leads.map(l => l.id === lead.id ? {...l, business: e.target.value} : l))} style={{background:'transparent', border:'none', color:'white', width:'100%', outline: 'none'}} /></td>
                        <td><input type="text" value={lead.contact} onChange={e => setLeads(leads.map(l => l.id === lead.id ? {...l, contact: e.target.value} : l))} style={{background:'transparent', border:'none', color:'var(--text-muted)', width:'100%', outline: 'none'}} /></td>
                        <td>
                          <select value={lead.status} onChange={e => setLeads(leads.map(l => l.id === lead.id ? {...l, status: e.target.value} : l))} className={`status-pill ${lead.status === 'New' ? 'new' : lead.status === 'In Negotiations' ? 'negotiations' : 'closed'}`} style={{outline:'none'}}>
                            <option value="New">New</option>
                            <option value="In Negotiations">In Negotiations</option>
                            <option value="Closed">Closed</option>
                          </select>
                        </td>
                        <td><input type="number" value={lead.value} onChange={e => setLeads(leads.map(l => l.id === lead.id ? {...l, value: e.target.value.replace(/[^0-9]/g,'')} : l))} style={{background:'transparent', border:'none', color:'white', width:'100%', outline: 'none'}} /></td>
                        <td>
                          {loadingAudits[lead.id] ? (
                            <span style={{ color: 'var(--accent-neon)' }}>Auditing...</span>
                          ) : audit ? (
                            <span title={audit.visibility_deficits?.join('\n')} style={{ color: audit.visibility_score < 50 ? '#ef4444' : '#10b981', cursor: 'help', fontWeight: 'bold' }}>
                              Score: {audit.visibility_score}/100 ⚠️
                            </span>
                          ) : (
                            <button onClick={() => handleAuditLead(lead.id, lead.business)} style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid #38bdf8', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '0.8rem' }}>
                              🔍 Audit
                            </button>
                          )}
                        </td>
                        <td>
                          {loadingVideos[lead.id] ? (
                            <span style={{ color: 'var(--accent-neon)' }}>Generating...</span>
                          ) : video ? (
                            <a href={`file:///${video.video_path}`} target="_blank" rel="noreferrer" style={{ color: '#10b981', textDecoration: 'none', fontWeight: 'bold' }}>
                              ▶️ Watch Video
                            </a>
                          ) : (
                            <button onClick={() => handleGenerateLeadVideo(lead.id, lead.business)} style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid #10b981', borderRadius: '4px', padding: '4px 8px', cursor: 'pointer', fontSize: '0.8rem' }}>
                              🎬 Create Video
                            </button>
                          )}
                        </td>
                        <td><button onClick={() => setLeads(leads.filter(l => l.id !== lead.id))} style={{background:'transparent', border:'none', color:'#ef4444', cursor:'pointer'}}>🗑️</button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {advSubTab === 'platform-posts' && (() => {
            const platforms = [
              { key: 'google',    label: 'Google Search',  icon: '🔍', color: '#4285F4', content: g => `📌 Title:\n${g?.schema_title || ''}\n\n📝 Meta Description:\n${g?.meta_description || ''}\n\n🔑 Keywords:\n${g?.local_keywords?.join(' · ') || ''}` },
              { key: 'facebook',  label: 'Facebook',       icon: '📘', color: '#1877F2', content: f => `💥 Headline:\n${f?.headline || ''}\n\n📣 Body:\n${f?.body || ''}\n\n👉 CTA: ${f?.cta || ''}` },
              { key: 'instagram', label: 'Instagram',      icon: '📸', color: '#E1306C', content: i => `🪝 Hook:\n${i?.caption_hook || ''}\n\n${i?.body || ''}\n\n${i?.hashtags || ''}` },
              { key: 'tiktok',    label: 'TikTok',         icon: '🎵', color: '#69C9D0', content: t => `🎬 Hook: ${t?.hook_text || ''}\n\n📜 Script:\n${t?.script || ''}\n\n🏷️ Caption: ${t?.caption_keywords || ''}` },
              { key: 'twitter',   label: 'X / Twitter',    icon: '🐦', color: '#1DA1F2', content: t => `${t?.tweet || ''}\n\n🃏 Card: ${t?.card_title || ''} — ${t?.card_description || ''}` },
              { key: 'pinterest', label: 'Pinterest',      icon: '📌', color: '#E60023', content: p => `📌 ${p?.pin_title || ''}\n\n${p?.pin_description || ''}\n\n💲 ${p?.rich_pin_price || ''}` },
              { key: 'yelp',      label: 'Yelp',           icon: '⭐', color: '#FF1A1A', content: y => `${y?.business_description || ''}\n\n🏷️ ${y?.category_tags?.join(', ') || ''}\n\n🎁 ${y?.special_offer || ''}` },
            ];
            return (
              <div style={{ display: 'flex', gap: 0, height: '100%', minHeight: 560 }}>
                {/* LEFT SIDEBAR — FORM */}
                <div style={{ width: 300, minWidth: 300, display: 'flex', flexDirection: 'column', gap: 10, padding: '16px', background: 'rgba(0,0,0,0.35)', borderRadius: '12px 0 0 12px', borderRight: '1px solid rgba(124,58,237,0.3)', flexShrink: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <div style={{ width: 32, height: 32, borderRadius: 8, background: 'linear-gradient(135deg,#7c3aed,#4f46e5)', display:'flex', alignItems:'center', justifyContent:'center', fontSize: 16 }}>🌐</div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'white' }}>Platform Post Generator</div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>1 promo → 7 algorithm-native posts</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Business Name</label>
                    <input type="text" value={postBizName} onChange={e => setPostBizName(e.target.value)} placeholder="e.g. Holland Auto Care" style={{ padding: '7px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, color: 'white', outline: 'none', fontSize: '0.85rem' }} />
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Industry</label>
                    <select value={postIndustry} onChange={e => setPostIndustry(e.target.value)} style={{ padding: '7px 10px', background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, color: 'white', outline: 'none', fontSize: '0.85rem' }}>
                      <option>Local Business</option><option>Restaurant / Food</option><option>Auto Repair</option><option>Real Estate</option><option>Health & Wellness</option><option>Retail / Shop</option><option>Home Services</option><option>Legal / Financial</option><option>Beauty & Salon</option><option>Event Venue</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Target County</label>
                    <select value={postCounty} onChange={e => setPostCounty(e.target.value)} style={{ padding: '7px 10px', background: 'rgba(0,0,0,0.6)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, color: 'white', outline: 'none', fontSize: '0.85rem' }}>
                      <option>Ottawa County</option><option>Kent County</option><option>Muskegon County</option><option>Allegan County</option><option>Kalamazoo County</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1 }}>
                    <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Weekly Promotion</label>
                    <textarea value={postPromo} onChange={e => setPostPromo(e.target.value)} placeholder="e.g. 20% off all oil changes this Saturday. Mention this ad for a free tire rotation." style={{ flex: 1, minHeight: 120, padding: '8px 10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 7, color: 'white', outline: 'none', resize: 'none', fontSize: '0.83rem', lineHeight: 1.5 }} />
                  </div>

                  <button onClick={handleGeneratePlatformPosts} disabled={isGeneratingPosts || !postBizName.trim() || !postPromo.trim()} style={{ padding: '11px', background: isGeneratingPosts ? 'rgba(124,58,237,0.25)' : 'linear-gradient(135deg,#7c3aed,#4f46e5)', border: 'none', borderRadius: 8, color: 'white', fontWeight: 700, cursor: isGeneratingPosts ? 'not-allowed' : 'pointer', fontSize: '0.9rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, transition: 'all 0.2s', boxShadow: isGeneratingPosts ? 'none' : '0 4px 15px rgba(124,58,237,0.4)' }}>
                    {isGeneratingPosts ? <><span style={{ display:'inline-block', animation:'spin 1s linear infinite' }}>⚙️</span> Synthesizing...</> : '⚡ Generate All 7 Platforms'}
                  </button>

                  {/* Platform status badges */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                    {platforms.map(p => (
                      <div key={p.key} style={{ padding: '3px 8px', borderRadius: 20, fontSize: '0.7rem', fontWeight: 600, background: generatedPosts && generatedPosts[p.key] ? `${p.color}33` : 'rgba(255,255,255,0.05)', color: generatedPosts && generatedPosts[p.key] ? p.color : 'var(--text-muted)', border: `1px solid ${generatedPosts && generatedPosts[p.key] ? p.color + '66' : 'rgba(255,255,255,0.08)'}`, transition: 'all 0.3s' }}>
                        {p.icon} {p.label}
                      </div>
                    ))}
                  </div>
                </div>

                {/* RIGHT PANEL — 2-col platform cards grid */}
                <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, padding: '14px', background: 'rgba(0,0,0,0.15)', borderRadius: '0 12px 12px 0', overflowY: 'auto', alignContent: 'start' }}>
                  {isGeneratingPosts && (
                    <div style={{ gridColumn: '1/-1', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 20px', color: 'var(--accent-neon)' }}>
                      <div style={{ fontSize: '2.5rem', animation: 'pulse 1s infinite', marginBottom: 12 }}>🌐</div>
                      <div style={{ fontWeight: 700 }}>Synthesizing native content for all 7 platforms...</div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 6 }}>Your local AI is formatting each post to speak each platform's native algorithm language</div>
                    </div>
                  )}
                  {generatedPosts && generatedPosts.error && (
                    <div style={{ gridColumn: '1/-1', padding: 16, background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: 10, color: '#ef4444', fontSize: '0.85rem' }}>
                      <strong>⚠️ Generation Error:</strong><br/>{generatedPosts.error}
                    </div>
                  )}
                  {platforms.map(({ key, label, icon, color, content }) => {
                    const data = generatedPosts?.[key];
                    const text = data ? content(data) : null;
                    const isEmpty = !data;
                    return (
                      <div key={key} style={{ padding: '14px', background: isEmpty ? 'rgba(255,255,255,0.02)' : `rgba(0,0,0,0.45)`, borderRadius: 10, border: `1px solid ${isEmpty ? 'rgba(255,255,255,0.07)' : color + '55'}`, display: 'flex', flexDirection: 'column', gap: 8, minHeight: 140, transition: 'all 0.3s' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 700, color: isEmpty ? 'var(--text-muted)' : color, fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ fontSize: '1.1rem' }}>{icon}</span> {label}
                          </span>
                          {text && (
                            <button onClick={() => handleCopyPost(key, text)} style={{ padding: '3px 9px', background: copiedPlatform === key ? '#10b981' : `${color}22`, border: `1px solid ${color}66`, borderRadius: 6, color: copiedPlatform === key ? 'white' : color, cursor: 'pointer', fontSize: '0.72rem', fontWeight: 700, transition: 'all 0.2s', whiteSpace: 'nowrap' }}>
                              {copiedPlatform === key ? '✅ Copied!' : '📋 Copy'}
                            </button>
                          )}
                        </div>
                        {isEmpty ? (
                          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.12)', fontSize: '0.78rem', fontStyle: 'italic', textAlign: 'center' }}>
                            Awaiting generation...
                          </div>
                        ) : (
                          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.76rem', color: 'rgba(255,255,255,0.75)', lineHeight: 1.55, flex: 1, overflowY: 'auto', maxHeight: 180 }}>{text}</pre>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}

          {advSubTab === 'campaign' && (
            <div className="adv-grid-2 animate-slide-in" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
              <div className="adv-panel">
                <h3 style={{ marginTop: 0 }}>Stehouwer Methodology Matrix</h3>
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Target Business</label>
                  <input type="text" className="chat-input" placeholder="e.g. Grandville Publishing" value={businessName} onChange={e => setBusinessName(e.target.value)} style={{ width: '100%', boxSizing: 'border-box', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px' }} />
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Geofence Vector</label>
                    <select value={geofence} onChange={e => setGeofence(e.target.value)} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px' }}>
                      <option value="Ottawa County">Ottawa County (Primary)</option>
                      <option value="Kent County">Kent County (Metropolitan)</option>
                      <option value="Muskegon County">Muskegon County (Northern)</option>
                      <option value="Allegan County">Allegan County (Southern)</option>
                      <option value="Kalamazoo & Barry">Kalamazoo & Barry (Runway)</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Decoy Matrix Tier</label>
                    <select value={pricingTier} onChange={e => setPricingTier(e.target.value)} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px' }}>
                      <option value="495">Tier I: Organic Primer ($495)</option>
                      <option value="995">Tier II: Target Baseline ($995)</option>
                      <option value="1495">Tier III: Monopolization ($1495)</option>
                    </select>
                  </div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Temporal Commitment Protocol</label>
                  <select value={temporalCommitment} onChange={e => setTemporalCommitment(e.target.value)} style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '8px' }}>
                    <option value="90">Quarterly Base (90 Days - 0% Off)</option>
                    <option value="180">Biannual Integration (180 Days - 10% Off)</option>
                    <option value="365">Annual Lock (365 Days - 15% Off)</option>
                  </select>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>Campaign Objective</label>
                  <textarea className="chat-input" rows="3" placeholder="Describe the goal of the ad campaign..." value={campaignGoal} onChange={e => setCampaignGoal(e.target.value)} style={{ width: '100%', boxSizing: 'border-box', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '8px' }} />
                </div>
                
                <div style={{ padding: '10px', background: 'rgba(124, 58, 237, 0.1)', border: '1px solid #7c3aed', borderRadius: '8px', marginBottom: '16px', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Calculated Contract Value</span><br/>
                  <strong style={{ fontSize: '1.2rem', color: 'var(--accent-neon)' }}>${calculateContractValue().toFixed(2)}</strong>
                </div>

                <button className="send-button" style={{ width: '100%' }} onClick={async () => { 
                  setIsAdvGenerating(true); 
                  setGeneratedCopy("Initializing Live AI Copywriter...\nApplying Stehouwer Methodology Variables...\n");
                  try {
                    let cv = calculateContractValue();
                    const response = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/generate`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ 
                        businessName, 
                        campaignGoal,
                        geofence,
                        tier: pricingTier,
                        commitment: temporalCommitment,
                        contractValue: cv
                      })
                    });
                    
                    if (!response.body) throw new Error("No response body");
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder("utf-8");
                    let fullText = "";
                    setGeneratedCopy("");
                    
                    while (true) {
                      const { value, done } = await reader.read();
                      if (done) break;
                      const chunk = decoder.decode(value);
                      const lines = chunk.split('\\n').filter(l => l.trim() !== "");
                      for (let line of lines) {
                        try {
                          const data = JSON.parse(line);
                          if (data.error) fullText += `\\n[SYSTEM FAULT]: ${data.error}`;
                          else if (data.message?.content) fullText += data.message.content;
                          else if (data.response) fullText += data.response;
                        } catch(e) {
                          fullText += line;
                        }
                      }
                      setGeneratedCopy(fullText);
                    }
                  } catch (err) {
                    setGeneratedCopy(prev => prev + `\\n\\n[LIVE FAULT] Error contacting backend: ${err.message}`);
                  } finally {
                    setIsAdvGenerating(false);
                  }
                }} disabled={isAdvGenerating || (!businessName && !campaignGoal)}>
                  {isAdvGenerating ? '⚙️ Synthesizing...' : '⚡ Generate High-Converting Copy'}
                </button>
              </div>
              <div className="adv-panel">
                <h3 style={{ marginTop: 0 }}>Execution Output</h3>
                <div className="adv-terminal-output" style={{ minHeight: '150px', marginBottom: '15px' }}>
                  {generatedCopy || "> Awaiting campaign parameters..."}
                </div>
                {generatedCopy && !isAdvGenerating && (
                  <button className="send-button" onClick={handleDeployCampaign} style={{ width: '100%', background: '#ef4444' }}>
                    🚀 Deploy Live Campaign
                  </button>
                )}
                {deployResult && (
                  <div style={{ marginTop: '10px', color: '#10b981', fontSize: '0.9rem' }}>
                    ✅ {deployResult}
                  </div>
                )}
              </div>
            </div>
          )}

          {advSubTab === 'telemetry' && (
            <div className="adv-panel animate-slide-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ margin: 0 }}>Data Visualization Dashboard</h3>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <span style={{ padding: '6px 12px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', border: '1px solid #10b981', borderRadius: '20px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '8px', height: '8px', background: '#10b981', borderRadius: '50%', animation: 'pulse 2s infinite' }}></div>
                    SHADOW AUTO-TASKER ACTIVE
                  </span>
                </div>
              </div>

              {/* Total Reach Counter */}
              <div style={{ textAlign: 'center', marginBottom: '30px', padding: '20px', background: 'rgba(0,0,0,0.4)', borderRadius: '12px', border: '1px solid rgba(124, 58, 237, 0.3)' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '2px' }}>Total Organic Reach</span>
                <div style={{ fontSize: '3.5rem', fontWeight: '900', color: 'var(--accent-neon)', textShadow: '0 0 20px rgba(124, 58, 237, 0.6)' }}>
                  {telemetryData.total_reach.toLocaleString()}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '20px' }}>
                <div style={{ height: '300px', background: 'rgba(0,0,0,0.3)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <h4 style={{ color: '#f472b6', marginBottom: '15px', textAlign: 'center' }}>Platform Reach Breakdown</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={telemetryData.platforms}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                      <XAxis dataKey="source" stroke="var(--text-muted)" tickFormatter={(val) => val.replace('www.', '').replace('.com', '').replace('business.facebook', 'facebook')} />
                      <YAxis stroke="var(--text-muted)" />
                      <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(244, 114, 182, 0.5)', borderRadius: '8px' }} itemStyle={{ color: '#f472b6' }} />
                      <Bar dataKey="organic_reach" fill="#f472b6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div style={{ height: '250px', background: 'rgba(0,0,0,0.3)', padding: '20px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <h4 style={{ color: '#3b82f6', marginBottom: '15px', textAlign: 'center' }}>Engagement Velocity</h4>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={telemetryData.platforms}>
                      <defs>
                        <linearGradient id="colorEngagement" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                      <XAxis dataKey="source" stroke="var(--text-muted)" tickFormatter={(val) => val.replace('www.', '').replace('.com', '').replace('business.facebook', 'facebook')} />
                      <YAxis stroke="var(--text-muted)" />
                      <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(59, 130, 246, 0.5)', borderRadius: '8px' }} itemStyle={{ color: '#3b82f6' }} />
                      <Area type="monotone" dataKey="organic_reach" stroke="#3b82f6" fillOpacity={1} fill="url(#colorEngagement)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}

          {advSubTab === 'ghost-browser' && (
            <div className="adv-panel animate-slide-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: '800px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
                  <h3 style={{ margin: 0, color: '#10b981' }}>👻 Social Command Center</h3>
                  <button 
                    onClick={() => setIsAutoAgentRunning(!isAutoAgentRunning)}
                    style={{ 
                      background: isAutoAgentRunning ? '#ef4444' : '#10b981', 
                      color: '#fff', 
                      border: 'none', 
                      padding: '6px 15px', 
                      borderRadius: '20px', 
                      cursor: 'pointer', 
                      fontWeight: 'bold',
                      fontSize: '0.85rem',
                      boxShadow: isAutoAgentRunning ? '0 0 10px rgba(239, 68, 68, 0.8)' : 'none',
                      animation: isAutoAgentRunning ? 'pulse 2s infinite' : 'none'
                    }}>
                    {isAutoAgentRunning ? '🛑 STOP AUTO-TASKER AGENT' : '🚀 START AUTO-TASKER AGENT'}
                  </button>
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.google.com/maps/contrib/114475333646636636839/'} style={{ background: '#3b82f6', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>📍 Google Maps</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.facebook.com/professional_dashboard/profile_insights/views/'} style={{ background: '#1877f2', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>📘 FB Insights</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.instagram.com/'} style={{ background: '#e1306c', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>📸 Instagram</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://x.com/'} style={{ background: '#000000', color: '#fff', border: '1px solid #333', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>✖️ X</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://studio.youtube.com/'} style={{ background: '#ff0000', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>▶️ YouTube</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.linkedin.com/'} style={{ background: '#0a66c2', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>💼 LinkedIn</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.tiktok.com/'} style={{ background: '#000000', color: '#fff', border: '1px solid #333', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>🎵 TikTok</button>
                  <button onClick={() => document.getElementById('ghostWebviewFull').src = 'https://www.pinterest.com/'} style={{ background: '#e60023', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.85rem' }}>📌 Pinterest</button>
                </div>
              </div>
              
              <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
                <input 
                  type="text" 
                  id="ghostBrowserUrlFull" 
                  defaultValue="https://www.google.com/maps/contrib/114475333646636636839/" 
                  style={{ flex: 1, padding: '10px', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', fontSize: '1rem' }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      document.getElementById('ghostWebviewFull').src = e.target.value;
                    }
                  }}
                />
                <button 
                  onClick={() => document.getElementById('ghostWebviewFull').src = document.getElementById('ghostBrowserUrlFull').value}
                  style={{ background: '#10b981', color: '#fff', border: 'none', padding: '0 25px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold', fontSize: '1rem' }}>
                  GO
                </button>
              </div>
              <div style={{ flex: 1, border: '2px solid #10b981', borderRadius: '8px', overflow: 'hidden', background: '#fff' }}>
                <webview 
                  id="ghostWebviewFull"
                  src="https://www.google.com/maps/contrib/114475333646636636839/"
                  preload="file:///C:/Workspaces/Stehouwer_Server/AI-BS/frontend/public/ghost_preload.js"
                  partition="persist:ghostBrowser"
                  style={{ width: '100%', height: '100%' }}
                ></webview>
              </div>
            </div>
          )}
 
          {advSubTab === 'budget' && (
            <div className="adv-panel animate-slide-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h3 style={{ margin: 0 }}>Event Spend Tracker</h3>
                <button className="action-btn-download send-button" onClick={() => setBudgets([{ id: Date.now(), event: 'New Marketing Event', spent: 0, roi: 0 }, ...budgets])}>+ Add Budget Entry</button>
              </div>
              
              <div className="budget-cards" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {budgets.length === 0 && <p style={{color:'var(--text-muted)'}}>No budget entries.</p>}
                {budgets.map(budget => (
                  <div key={budget.id} className="budget-card-premium">
                    <div style={{ flex: 1, marginRight: '10px' }}>
                      <input type="text" className="event-name" value={budget.event} onChange={(e) => setBudgets(budgets.map(b => b.id === budget.id ? { ...b, event: e.target.value } : b))} style={{width: '100%'}} />
                    </div>
                    <div className="budget-stats">
                      <div className="budget-stat">
                        <label>Spent ($)</label>
                        <input type="number" value={budget.spent} onChange={(e) => setBudgets(budgets.map(b => b.id === budget.id ? { ...b, spent: e.target.value } : b))} style={{background:'transparent', border:'none', color:'white', fontSize:'1.2rem', fontWeight:'700', width:'60px', textAlign:'right', outline:'none'}} />
                      </div>
                      <div className="budget-stat">
                        <label>ROI ($)</label>
                        <input type="number" value={budget.roi} onChange={(e) => setBudgets(budgets.map(b => b.id === budget.id ? { ...b, roi: e.target.value } : b))} style={{background:'transparent', border:'none', color:'var(--success-color)', fontSize:'1.2rem', fontWeight:'700', width:'60px', textAlign:'right', outline:'none'}} />
                      </div>
                    </div>
                    <button onClick={() => setBudgets(budgets.filter(b => b.id !== budget.id))} style={{background:'transparent', border:'none', color:'#ef4444', cursor:'pointer', marginLeft:'15px', fontSize:'1.2rem'}}>×</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {advSubTab === 'licensing' && (
            <div className="adv-panel animate-slide-in">
              <h3>🔑 Stehouwer Publishing License Generator</h3>
              <p style={{ color: 'var(--text-muted)' }}>Generate signed license keys for distributing the Bullshit AI (AI-BS) v1.4.5 package.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <h4>Generate New Key</h4>
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)' }}>Client Email</label>
                    <input type="email" id="gen-email" placeholder="client@example.com" style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '6px' }} />
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)' }}>License Tier</label>
                    <select id="gen-tier" style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '6px' }}>
                      <option value="Basic">Basic Edition</option>
                      <option value="Pro">Pro Edition</option>
                      <option value="Enterprise">Enterprise Sovereignty</option>
                    </select>
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', color: 'var(--text-muted)' }}>Validity (Days)</label>
                    <input type="number" id="gen-days" defaultValue="365" style={{ width: '100%', padding: '8px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '6px' }} />
                  </div>
                  <button onClick={async () => {
                    const email = document.getElementById('gen-email').value;
                    const tier = document.getElementById('gen-tier').value;
                    const days = document.getElementById('gen-days').value;
                    if (!email) return alert('Please enter a client email.');
                    
                    try {
                      const res = await fetch(`${BACKEND_URL || 'https://ai-bs.brettstehouwer.live'}/api/advertising/license/generate`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, tier, expires_days: parseInt(days) })
                      });
                      const data = await res.json();
                      if (data.status === 'success') {
                        document.getElementById('gen-output-key').value = data.license_key;
                      }
                    } catch (e) {
                      alert('Failed to generate license key.');
                    }
                  }} style={{ width: '100%', padding: '10px', background: 'var(--accent-neon)', color: '#0f1115', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>
                    Mint License Key
                  </button>
                </div>
                
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column' }}>
                  <h4>Generated License Output</h4>
                  <textarea id="gen-output-key" readOnly placeholder="Generated key will appear here..." style={{ flex: 1, width: '100%', padding: '10px', background: 'rgba(0,0,0,0.4)', color: '#38bdf8', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '6px', resize: 'none', fontFamily: 'monospace', fontSize: '0.8rem', marginBottom: '10px' }} />
                  <button onClick={() => {
                    const copyText = document.getElementById('gen-output-key');
                    copyText.select();
                    document.execCommand('copy');
                    alert('Copied to clipboard!');
                  }} style={{ padding: '8px', background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '6px', cursor: 'pointer' }}>
                    📋 Copy Key
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (activeTab === 'weather') {
    return (
      <div className="weather-dashboard-tab" style={{ padding: '20px' }}>
        <header><h2>Current Weather</h2></header>
        <main>
          <section><div className="current-weather"><span className="temperature">23°C</span><span className="humidity">60%</span></div></section>
          <section>
            <h3>3-Day Forecast</h3>
            <ul>
              <li><time>Tuesday</time><span>22°C</span><span>Partly Cloudy</span></li>
              <li><time>Wednesday</time><span>24°C</span><span>Sunny</span></li>
              <li><time>Thursday</time><span>21°C</span><span>Cloudy</span></li>
            </ul>
          </section>
        </main>
      </div>
    );
  }

  return null;
}
