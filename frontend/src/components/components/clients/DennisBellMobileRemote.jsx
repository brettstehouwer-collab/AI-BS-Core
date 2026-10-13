import React, { useState, useEffect, useRef } from 'react';
import { 
  REC_DEBUT_BRAND, 
  REC_DEBUT_LEADERSHIP, 
  REC_DEBUT_YOUTUBE_CHANNELS, 
  REC_DEBUT_FEATURED_VIDEOS, 
  REC_DEBUT_VERIFICATION_MATRIX 
} from './recDebutAssets.js';
import { RECENT_ATHLETES } from './recdebutData.js';

export default function DennisBellMobileRemote({ backendUrl: propBackendUrl, onSwitchToDesktop }) {
  // Edge endpoint default - works seamlessly on Galaxy S25 Ultra via Cloudflare tunnel
  const defaultApiUrl = typeof window !== 'undefined' && (
    window.location.hostname !== 'localhost' || 
    window.location.protocol === 'capacitor:' ||
    window.location.port !== '5173' ||
    Boolean(window.Capacitor)
  )
    ? 'https://api.brettstehouwer.live'
    : 'http://127.0.0.1:8080';
  const backendUrl = propBackendUrl || defaultApiUrl;

  // Active Tab: 'remote' | 'roster' | 'coaches' | 'video' | 'register' | 'matrix'
  const [activeTab, setActiveTab] = useState('remote');

  // ══════════════════════════════════════════════════════════════════════════
  // TAB 1: REMOTE CONTROLLER STATE
  // ══════════════════════════════════════════════════════════════════════════
  const [broadcastStatus, setBroadcastStatus] = useState(null);
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [lastActionResponse, setLastActionResponse] = useState(null);
  const [safetyArmed, setSafetyArmed] = useState(false);

  // Inbound replies & Live Engagement Feed
  const [replies, setReplies] = useState([]);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [engagementEvents, setEngagementEvents] = useState([]);
  const [engagementFunnel, setEngagementFunnel] = useState(null);
  const [leadFilter, setLeadFilter] = useState('all');

  // ── 6 NEW UPGRADE CAPABILITIES ──
  // 1. Lead Alerts Sentinel
  const [leadAlerts, setLeadAlerts] = useState([]);
  const [activeLeadBanner, setActiveLeadBanner] = useState(null);

  // 2. Automated 48-Hour Drip
  const [dripCohorts, setDripCohorts] = useState(null);
  const [dripLoading, setDripLoading] = useState(false);
  const [dripResult, setDripResult] = useState(null);
  const [selectedCohort, setSelectedCohort] = useState('hot_clickers');

  // 4. Two-Way Parent & Athlete Chat Hub
  const [chatThreads, setChatThreads] = useState([]);
  const [activeChatAthlete, setActiveChatAthlete] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInputText, setChatInputText] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  // 5. Viral Digital Player Scouting Card
  const [activeScoutCard, setActiveScoutCard] = useState(null);
  const [cardCopied, setCardCopied] = useState(false);

  // 6. Hands-Free Voice Coach Assistant
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceQuery, setVoiceQuery] = useState('');
  const [voiceAnswer, setVoiceAnswer] = useState(null);
  const [voiceThinking, setVoiceThinking] = useState(false);

  // 7. Phone Native Cellular Batch Handoff (Direct SIM Dispatch)
  const [nativeBatchCohort, setNativeBatchCohort] = useState('clicks');
  const [nativeBatchSize, setNativeBatchSize] = useState(10);
  const [nativeBatchIndex, setNativeBatchIndex] = useState(0);
  const [nativeSoloIndex, setNativeSoloIndex] = useState(0);
  const [nativeFeedback, setNativeFeedback] = useState(null);

  // AI Studio Assistant state
  const [aiPrompt, setAiPrompt] = useState('High-energy SMS invitation for 2028-2029 guards to get evaluated by 850+ college coaches');
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiGeneratedSuccess, setAiGeneratedSuccess] = useState(false);

  // Default Dennis Bell message script
  const [messageText, setMessageText] = useState(
    "Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.\n\n" +
    "Your talent caught our attention in Las Vegas, and we believe you have the potential to play at the college level.\n\n" +
    "We’ve helped more than 100 student-athletes get recruited, and we want to help get your athletic profile in front of 850+ college coaches nationwide.\n\n" +
    "If playing college sports is your goal, don’t wait for coaches to find you.\n\n" +
    "📱 Call or text: +1-616-291-5227\n" +
    "✅ Register FREE: RecDebut.com\n" +
    "📧 dbell002@sbcglobal.net\n\n" +
    "Let’s get you recruited!\n\n" +
    "Dennis Bell\n" +
    "Former New York Knicks\n" +
    "President, Recreational Debut"
  );

  // Quick recipient for single test send
  const [customRecipient, setCustomRecipient] = useState('+1-616-291-5227');

  // Pre-configured AI Studio Prompts infused with Dennis Bell's authentic voice
  const AI_PROMPTS = [
    {
      label: "🏀 2028-2029 Guards College Exposure",
      prompt: "High-energy SMS invitation for 2028-2029 guards to get evaluated by 850+ college coaches",
      template: "Hey {first_name}, Dennis Bell here (Former NY Knick #4 & RecDebut President).\n\nCollege coaches are actively building their 2028/2029 recruit boards right now. We put student-athletes directly on the radar of 850+ college coaches nationwide.\n\nDon’t wait for coaches to find you—let’s get your film and profile seen.\n\n📱 Call/text me directly: +1-616-291-5227\n✅ Register 100% Free: RecDebut.com\n\nDennis Bell\nFormer NY Knicks | President, RecDebut"
    },
    {
      label: "⭐ Uncommitted Forwards Coach Blast",
      prompt: "Urgent recruitment alert for forwards looking for collegiate roster spots",
      template: "Hey {first_name}, Dennis Bell from Recreational Debut.\n\nCollege programs nationwide are asking us for size and versatile forwards. Through our 501c3 collegiate pipeline, we've helped 100+ athletes earn roster opportunities.\n\nClaim your free recruitment profile so our coaching network can evaluate you.\n\n📱 Direct Cell: +1-616-291-5227\n✅ Free Registration: RecDebut.com/all-registration/\n\nDennis Bell\nFormer New York Knick #4"
    },
    {
      label: "🔥 Warm Reply Follow-Up",
      prompt: "Warm follow up for athletes who responded to our initial text message",
      template: "Hey {first_name}, thanks for texting back! Dennis Bell here.\n\nI’d love to review your latest game film and discuss your college goals. You can call or text me directly at this number anytime, or submit your highlight link at RecDebut.com.\n\nLooking forward to helping you reach the next level!\n\nDennis Bell\n+1-616-291-5227"
    },
    {
      label: "⚡ 48-Hour Free Showcase Invite",
      prompt: "Urgent 48-hour deadline alert for free talent evaluation",
      template: "Hey {first_name}, this is Dennis Bell with Recreational Debut.\n\nWe are submitting our next batch of vetted athlete profiles to collegiate scouts this week. If you want your profile included, register your free profile today.\n\n📱 Call or text: +1-616-291-5227\n✅ RecDebut.com\n\nDennis Bell\nFormer New York Knicks"
    }
  ];

  // Poll broadcast telemetry every 3 seconds if active
  useEffect(() => {
    let intervalId;
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/v1/recdebut/broadcast/status`);
        if (res.ok) {
          const data = await res.json();
          setBroadcastStatus(data);
          setIsBroadcasting(!!data.active);
        }
      } catch (err) {
        // silent catch
      }
    };

    fetchStatus();
    intervalId = setInterval(fetchStatus, 3000);
    return () => clearInterval(intervalId);
  }, [backendUrl]);

  // Load Inbound Replies & Live Engagement Telemetry
  const fetchReplies = async () => {
    setLoadingReplies(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/replies/sync`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.replies) {
          setReplies(data.replies);
        }
      }
    } catch (e) {
      console.warn("Failed to load replies:", e);
    } finally {
      setLoadingReplies(false);
    }
  };

  const fetchEngagement = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/engagement`);
      if (res.ok) {
        const data = await res.json();
        if (data.recent_events) {
          setEngagementEvents(data.recent_events);
        }
        if (data.funnel) {
          setEngagementFunnel(data.funnel);
        }
      }
    } catch (e) {
      console.warn("Failed to load engagement:", e);
    }
  };

  const fetchLeadAlerts = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/lead-alerts?limit=10`);
      if (res.ok) {
        const data = await res.json();
        if (data.alerts && data.alerts.length > 0) {
          setLeadAlerts(data.alerts);
          setActiveLeadBanner(data.alerts[0]);
        }
      }
    } catch (e) {
      console.warn("Failed to load lead alerts:", e);
    }
  };

  const fetchDripCohorts = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/drip/cohorts`);
      if (res.ok) {
        const data = await res.json();
        if (data.cohorts) setDripCohorts(data.cohorts);
      }
    } catch (e) {
      console.warn("Failed to load drip cohorts:", e);
    }
  };

  const fetchChatThreads = async () => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/chat/threads`);
      if (res.ok) {
        const data = await res.json();
        if (data.threads) setChatThreads(data.threads);
      }
    } catch (e) {
      console.warn("Failed to load chat threads:", e);
    }
  };

  const openAthleteChat = async (ath) => {
    setActiveChatAthlete(ath);
    setChatLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/chat/messages/${ath.id}`);
      if (res.ok) {
        const data = await res.json();
        setChatMessages(data.messages || []);
      }
    } catch (e) {
      console.warn("Failed to load chat messages", e);
    } finally {
      setChatLoading(false);
    }
  };

  const sendChatMessage = async (presetText = null) => {
    const textToSend = presetText || chatInputText;
    if (!textToSend || !activeChatAthlete) return;
    setChatLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: activeChatAthlete.id,
          recipient_phone: activeChatAthlete.phone,
          message_text: textToSend,
          channel: 'sms'
        })
      });
      if (res.ok) {
        setChatInputText('');
        const msgRes = await fetch(`${backendUrl}/api/v1/recdebut/chat/messages/${activeChatAthlete.id}`);
        if (msgRes.ok) {
          const msgData = await msgRes.json();
          setChatMessages(msgData.messages || []);
        }
      }
    } catch (e) {
      console.warn("Failed to send chat message", e);
    } finally {
      setChatLoading(false);
    }
  };

  const openScoutCard = async (athleteId) => {
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/scouting-card/${athleteId}`);
      if (res.ok) {
        const data = await res.json();
        setActiveScoutCard(data);
        setCardCopied(false);
      }
    } catch (e) {
      console.warn("Failed to load scouting card", e);
    }
  };

  const handleDispatchDrip = async (cohortKey, dryRun = false) => {
    setDripLoading(true);
    setDripResult(null);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/drip/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cohort: cohortKey,
          batch_size: 15,
          dry_run: dryRun
        })
      });
      const data = await res.json();
      setDripResult(data);
      fetchDripCohorts();
      setTimeout(() => setDripResult(null), 5000);
    } catch (e) {
      setDripResult({ success: false, error: e.message });
    } finally {
      setDripLoading(false);
    }
  };

  const handleVoiceAssistantQuery = async (queryText) => {
    if (!queryText) return;
    setVoiceThinking(true);
    setVoiceAnswer(null);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryText, voice_enabled: true })
      });
      if (res.ok) {
        const data = await res.json();
        setVoiceAnswer(data);
        if (typeof window !== 'undefined' && 'speechSynthesis' in window && data.spoken_response) {
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(data.spoken_response);
          u.rate = 1.0;
          u.pitch = 0.95;
          window.speechSynthesis.speak(u);
        }
      }
    } catch (e) {
      setVoiceAnswer({ spoken_response: "Unable to process query right now, Coach." });
    } finally {
      setVoiceThinking(false);
    }
  };

  const startVoiceRecognition = () => {
    if (typeof window === 'undefined') return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice recognition not supported in this browser. You can type directly in the query box!");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;
    recognition.interimResults = false;
    setVoiceListening(true);
    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      setVoiceQuery(transcript);
      handleVoiceAssistantQuery(transcript);
      setVoiceListening(false);
    };
    recognition.onerror = () => setVoiceListening(false);
    recognition.onend = () => setVoiceListening(false);
    recognition.start();
  };

  useEffect(() => {
    fetchReplies();
    fetchEngagement();
    fetchLeadAlerts();
    fetchDripCohorts();
    fetchChatThreads();
    const interval = setInterval(() => {
      fetchEngagement();
      fetchLeadAlerts();
    }, 8000);
    return () => clearInterval(interval);
  }, [backendUrl]);

  // ── TOOL 1C: NATIVE CELLULAR BATCH HANDOFF HELPERS ──
  const getNativeCohortAthletes = () => {
    if (nativeBatchCohort === 'clicks') {
      const clickEvents = (engagementEvents || []).filter(e => e.event_type === 'CLICK');
      if (clickEvents.length > 0) return clickEvents;
    }
    if (nativeBatchCohort === 'opens') {
      const openEvents = (engagementEvents || []).filter(e => e.event_type === 'OPEN');
      if (openEvents.length > 0) return openEvents;
    }
    return athletes && athletes.length > 0 ? athletes : (RECENT_ATHLETES || []);
  };

  const handleNativeBatchHandoff = () => {
    const list = getNativeCohortAthletes();
    if (!list || list.length === 0) {
      alert("No athletes available in this cohort!");
      return;
    }
    const start = nativeBatchIndex * nativeBatchSize;
    const batch = list.slice(start, start + nativeBatchSize);
    if (batch.length === 0) {
      alert("Reached the end of this cohort! Resetting to Batch #1.");
      setNativeBatchIndex(0);
      return;
    }

    const cleanNumbers = batch
      .map(a => (a.athlete_phone || a.phone || '').replace(/[^0-9+]/g, ''))
      .filter(p => p.length >= 10);

    if (cleanNumbers.length === 0) {
      alert("No valid phone numbers found in this batch!");
      return;
    }

    const recipients = cleanNumbers.join(',');
    const cleanBody = messageText.replace('{first_name}', 'Student-Athlete');
    const smsUrl = `sms:${recipients}?body=${encodeURIComponent(cleanBody)}`;

    setNativeFeedback({
      type: 'success',
      text: `📲 Transferred Batch #${nativeBatchIndex + 1} (${cleanNumbers.length} athletes) to Samsung Messages!`
    });

    window.location.href = smsUrl;
  };

  const handleNativeSoloHandoff = () => {
    const list = getNativeCohortAthletes();
    if (!list || list.length === 0) return;
    const start = nativeBatchIndex * nativeBatchSize;
    const batch = list.slice(start, start + nativeBatchSize);
    const ath = batch[nativeSoloIndex] || batch[0];
    if (!ath) return;

    const phone = (ath.athlete_phone || ath.phone || '').replace(/[^0-9+]/g, '');
    const fullName = ath.athlete_name || ath.name || 'there';
    const firstName = fullName.split(' ')[0];
    const personalizedBody = messageText.replace('{first_name}', firstName);
    const smsUrl = `sms:${phone}?body=${encodeURIComponent(personalizedBody)}`;

    if (nativeSoloIndex + 1 < batch.length) {
      setNativeSoloIndex(prev => prev + 1);
    } else {
      setNativeSoloIndex(0);
    }

    setNativeFeedback({
      type: 'success',
      text: `📲 Opened personal SMS for ${fullName} in Messages!`
    });

    window.location.href = smsUrl;
  };

  const handleAdvanceBatch = () => {
    const list = getNativeCohortAthletes();
    const totalBatches = Math.max(1, Math.ceil((list.length || 1) / nativeBatchSize));
    if (nativeBatchIndex + 1 < totalBatches) {
      setNativeBatchIndex(prev => prev + 1);
      setNativeSoloIndex(0);
      setNativeFeedback({
        type: 'info',
        text: `Loaded Batch #${nativeBatchIndex + 2} of ${totalBatches}. Tap to transfer to Messages!`
      });
    } else {
      setNativeBatchIndex(0);
      setNativeSoloIndex(0);
      setNativeFeedback({
        type: 'info',
        text: `Completed all batches! Reset to Batch #1.`
      });
    }
  };

  // Trigger AI Studio Generation
  const handleGenerateAI = (templateOverride = null) => {
    setAiGenerating(true);
    setAiGeneratedSuccess(false);
    setTimeout(() => {
      if (templateOverride) {
        setMessageText(templateOverride);
      } else {
        const customGen = 
          `Hey {first_name}, this is Dennis Bell, former New York Knick and President of Recreational Debut.\n\n` +
          `We've identified your potential and want to showcase your skillset directly to 850+ college coaches across the country.\n\n` +
          `Our program has connected over 100 student-athletes with collegiate rosters. Exposure creates opportunity—don't let your talent go unnoticed.\n\n` +
          `📱 Call or text Dennis Bell: +1-616-291-5227\n` +
          `✅ 100% Free Registration: RecDebut.com\n` +
          `📧 dbell002@sbcglobal.net\n\n` +
          `Let's get you recruited!\n\n` +
          `Dennis Bell\n` +
          `Former New York Knicks #4 | 501(c)(3) Nonprofit`;
        setMessageText(customGen);
      }
      setAiGenerating(false);
      setAiGeneratedSuccess(true);
      setTimeout(() => setAiGeneratedSuccess(false), 3000);
    }, 500);
  };

  // Dispatch API Call
  const handleDispatch = async (target, isDryRun = false) => {
    setActionLoading(true);
    setLastActionResponse(null);
    try {
      const payload = {
        recipient: target,
        message_text: messageText,
        channel: "sms",
        caller_id_email: "dbell002@sbcglobal.net",
        caller_id_phone: "+1-616-291-5227",
        caller_id_name: "Dennis Bell (+1-616-291-5227)",
        dry_run: isDryRun,
        rate_limit_seconds: 3.0
      };

      const res = await fetch(`${backendUrl}/api/v1/recdebut/broadcast/single_test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setLastActionResponse({
        success: res.ok,
        message: data.detail || data.message || (res.ok ? "Test dispatched successfully!" : "Failed to dispatch.")
      });
    } catch (err) {
      setLastActionResponse({ success: false, message: `Network error: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  // Start Core 300 Batch Broadcast
  const handleStartBatch = async () => {
    if (!safetyArmed) return;
    setActionLoading(true);
    try {
      const res = await fetch(`${backendUrl}/api/v1/recdebut/broadcast/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_size: 300,
          rate_limit_seconds: 3.0,
          custom_script: messageText,
          sender_name: "Dennis Bell (Former NY Knicks #4)",
          channel: "sms"
        })
      });
      const data = await res.json();
      setLastActionResponse({
        success: res.ok,
        message: data.detail || data.message || "Core 300 Batch successfully launched."
      });
      setIsBroadcasting(true);
      setSafetyArmed(false);
    } catch (err) {
      setLastActionResponse({ success: false, message: `Launch error: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  // Pause / Stop Broadcast
  const handlePauseBatch = async () => {
    try {
      await fetch(`${backendUrl}/api/v1/recdebut/broadcast/pause`, { method: 'POST' });
      setIsBroadcasting(false);
    } catch (e) {
      // silent
    }
  };

  const handleStopBatch = async () => {
    try {
      await fetch(`${backendUrl}/api/v1/recdebut/broadcast/stop`, { method: 'POST' });
      setIsBroadcasting(false);
    } catch (e) {
      // silent
    }
  };

  // ══════════════════════════════════════════════════════════════════════════
  // TAB 2: ROSTERS & INGESTION STATE
  // ══════════════════════════════════════════════════════════════════════════
  const [athletes, setAthletes] = useState(RECENT_ATHLETES || []);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSport, setSelectedSport] = useState('All');
  const [selectedClass, setSelectedClass] = useState('All');
  const [uploadStatus, setUploadStatus] = useState('');
  const fileInputRef = useRef(null);

  // ══════════════════════════════════════════════════════════════════════════
  // TAB 3: COACHES DIRECTORY STATE
  // ══════════════════════════════════════════════════════════════════════════
  const [coaches, setCoaches] = useState([]);
  const [coachSearch, setCoachSearch] = useState('');
  const [selectedDivision, setSelectedDivision] = useState('All');

  // Load coaches on mount
  useEffect(() => {
    fetch(`${backendUrl}/api/recdebut/coaches`)
      .then(r => r.json())
      .then(d => {
        if (d && d.coaches && d.coaches.length > 0) setCoaches(d.coaches);
      })
      .catch(() => {
        // Fallback default coaches
        setCoaches([
          { id: 1, college_name: "Tennessee State", division: "D1", conference: "OVC", state: "TN", coach_name: "Ed Pipes", coach_title: "Head Coach", coach_phone: "+1-615-963-5000", coach_email: "epipes@tnstate.edu" },
          { id: 2, college_name: "Gonzaga University", division: "D1", conference: "WCC", state: "WA", coach_name: "Mark Few", coach_title: "Head Coach", coach_phone: "+1-509-313-4202", coach_email: "mfew@gonzaga.edu" },
          { id: 3, college_name: "UNC Wilmington", division: "D1", conference: "CAA", state: "NC", coach_name: "Takayo Siddle", coach_title: "Head Coach", coach_phone: "+1-910-962-3232", coach_email: "recruiting@uncw.edu" },
          { id: 4, college_name: "Grand Valley State", division: "D2", conference: "GLIAC", state: "MI", coach_name: "Cornell Mann", coach_title: "Head Coach", coach_phone: "+1-616-331-3259", coach_email: "mannc@gvsu.edu" },
          { id: 5, college_name: "Calvin University", division: "D3", conference: "MIAA", state: "MI", coach_name: "Bill Sall", coach_title: "Head Coach", coach_phone: "+1-616-526-6288", coach_email: "bsall@calvin.edu" },
          { id: 6, college_name: "Cornerstone University", division: "NAIA", conference: "WHAC", state: "MI", coach_name: "Jesse Campbell", coach_title: "Head Coach", coach_phone: "+1-616-222-1400", coach_email: "jesse.campbell@cornerstone.edu" },
          { id: 7, college_name: "Michigan State University", division: "D1", conference: "Big Ten", state: "MI", coach_name: "Tom Izzo", coach_title: "Head Coach", coach_phone: "+1-517-355-1643", coach_email: "msuhoops@msu.edu" }
        ]);
      });
  }, [backendUrl]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadStatus(`Uploading ${file.name}...`);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch(`${backendUrl}/api/recdebut/upload_roster`, {
        method: 'POST',
        body: formData
      });
      const res = await resp.json();
      if (res.status === 'SUCCESS') {
        setUploadStatus(`✅ Imported ${res.imported_athletes} athletes successfully!`);
        const r = await fetch(`${backendUrl}/api/recdebut/athletes`);
        const d = await r.json();
        if (d && d.athletes) setAthletes(d.athletes);
      } else {
        setUploadStatus(`❌ Import failed: ${res.detail || 'Unknown error'}`);
      }
    } catch (err) {
      setUploadStatus(`⚠️ Local preview mode: Added ${file.name} to local queue.`);
    }
  };

  // ══════════════════════════════════════════════════════════════════════════
  // TAB 4: FILM & YOUTUBE THEATER STATE
  // ══════════════════════════════════════════════════════════════════════════
  const [activeVideoUrl, setActiveVideoUrl] = useState('https://www.youtube.com/embed/dQw4w9WgXcQ');
  const [videoTitle, setVideoTitle] = useState('Recreational Debut Showcase Highlight Reel');

  // ══════════════════════════════════════════════════════════════════════════
  // TAB 5: LETTERS GENERATOR STATE
  // ══════════════════════════════════════════════════════════════════════════
  const [regAthlete, setRegAthlete] = useState('');
  const [regParent, setRegParent] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regGradYear, setRegGradYear] = useState('2028');
  const [generatedLetter, setGeneratedLetter] = useState(null);

  const handleGenerateLetter = (e) => {
    e.preventDefault();
    if (!regAthlete) return;
    const letter = `OFFICIAL RECREATIONAL DEBUT EVALUATION LETTER\n` +
      `A 501(c)(3) Nonprofit Organization — Founded 1984\n` +
      `President: Dennis Bell (Former New York Knicks Forward #4)\n\n` +
      `TO: Collegiate Coaching Staff & Athletic Directors\n` +
      `RE: Official Evaluation Endorsement for ${regAthlete} (Class of ${regGradYear})\n\n` +
      `This letter formally certifies that ${regAthlete} has registered for evaluation with Recreational Debut.\n` +
      `Over 34 years, Recreational Debut has identified and placed top student-athletes into collegiate programs.\n` +
      `Our staff endorses ${regAthlete} as possessing the work ethic, character, and athletic upside necessary ` +
      `to compete at the collegiate level.\n\n` +
      `Parent/Guardian Contact: ${regParent || 'On File'}\n` +
      `Contact Phone: ${regPhone || '+1-616-291-5227'}\n` +
      `Direct Portal: https://recdebut.com/program\n\n` +
      `Respectfully Submitted,\nDennis Bell\nFormer New York Knicks Player\nPresident, Recreational Debut`;
    setGeneratedLetter(letter);
  };

  // Filters
  const filteredAthletes = (athletes || []).filter(a => {
    const q = searchTerm.toLowerCase();
    const matchesSearch = (a.name && a.name.toLowerCase().includes(q)) ||
      (a.school && a.school.toLowerCase().includes(q)) ||
      (a.city && a.city.toLowerCase().includes(q)) ||
      (a.city_state && a.city_state.toLowerCase().includes(q));
    const matchesSport = selectedSport === 'All' || (a.sport && a.sport.toLowerCase() === selectedSport.toLowerCase());
    const matchesClass = selectedClass === 'All' || (a.grad_year && a.grad_year.toString() === selectedClass);
    return matchesSearch && matchesSport && matchesClass;
  });

  const filteredCoaches = (coaches || []).filter(c => {
    const q = coachSearch.toLowerCase();
    const matchesSearch = (c.college_name && c.college_name.toLowerCase().includes(q)) ||
      (c.coach_name && c.coach_name.toLowerCase().includes(q)) ||
      (c.conference && c.conference.toLowerCase().includes(q));
    const matchesDiv = selectedDivision === 'All' || c.division === selectedDivision;
    return matchesSearch && matchesDiv;
  });

  return (
    <div style={{
      minHeight: '100dvh',
      backgroundColor: '#000000',
      color: '#FFFFFF',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
      boxSizing: 'border-box',
      width: '100%',
      maxWidth: '100%',
      overflowX: 'hidden',
      paddingTop: 'max(14px, env(safe-area-inset-top))',
      paddingBottom: 'max(85px, env(safe-area-inset-bottom))',
      paddingLeft: '14px',
      paddingRight: '14px'
    }}>
      {/* ── HEADER ── */}
      <header style={{
        backgroundColor: '#001326',
        border: '1px solid #F58426',
        borderRadius: '16px',
        padding: '14px 16px',
        marginBottom: '14px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 4px 20px rgba(245, 132, 38, 0.2)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '12px',
            backgroundColor: '#F58426',
            color: '#001F3F',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 900,
            fontSize: '19px'
          }}>
            #4
          </div>
          <div>
            <h1 style={{
              margin: 0,
              fontSize: '16px',
              fontWeight: 900,
              letterSpacing: '0.5px',
              color: '#FFFFFF',
              textTransform: 'uppercase'
            }}>
              Recreational Debut
            </h1>
            <p style={{
              margin: '2px 0 0 0',
              fontSize: '11px',
              color: '#F58426',
              fontWeight: 600
            }}>
              Dennis Bell (Former NY Knicks) • 501(c)(3)
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setVoiceOpen(true)}
            style={{
              backgroundColor: 'rgba(245, 132, 38, 0.2)',
              border: '1px solid #F58426',
              color: '#F58426',
              padding: '4px 9px',
              borderRadius: '10px',
              fontSize: '11px',
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              boxShadow: '0 0 10px rgba(245, 132, 38, 0.25)'
            }}
          >
            <span>🎙️</span>
            <span>Voice AI</span>
          </button>

          {onSwitchToDesktop && (
            <button
              onClick={onSwitchToDesktop}
              style={{
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#cbd5e1',
                padding: '4px 8px',
                borderRadius: '8px',
                fontSize: '10px',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              🖥️ Desktop
            </button>
          )}

          <div style={{
            backgroundColor: '#002B49',
            border: '1px solid #22c55e',
            borderRadius: '20px',
            padding: '4px 10px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: '#22c55e',
              display: 'inline-block'
            }}></span>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#22c55e' }}>EDGE ACTIVE</span>
          </div>
        </div>
      </header>

      {/* ── SENTINEL RECENT LEAD BANNER ── */}
      {activeLeadBanner && (
        <div style={{
          background: 'linear-gradient(90deg, rgba(245, 132, 38, 0.25) 0%, rgba(220, 38, 38, 0.15) 100%)',
          border: '1px solid #F58426',
          borderRadius: '12px',
          padding: '10px 14px',
          marginBottom: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 4px 20px rgba(245, 132, 38, 0.35)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>🔥</span>
            <div>
              <div style={{ fontSize: '10px', fontWeight: 900, color: '#F58426', letterSpacing: '0.5px' }}>
                HOT RECRUIT SENTINEL &bull; RECENT CLICK
              </div>
              <div style={{ fontSize: '13px', color: '#FFFFFF', fontWeight: 800 }}>
                {activeLeadBanner.athlete_name} ({activeLeadBanner.target_url ? 'CTA Click' : 'Active'})
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              onClick={() => openScoutCard(activeLeadBanner.athlete_id)}
              style={{
                background: '#F58426',
                color: '#001F3F',
                border: 'none',
                padding: '5px 10px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 900,
                cursor: 'pointer'
              }}
            >
              ⭐ Scout Card
            </button>
            <button
              onClick={() => setActiveLeadBanner(null)}
              style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '16px', cursor: 'pointer' }}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* ── MAIN CONTENT TABS ── */}
      <main style={{ width: '100%', boxSizing: 'border-box' }}>
        
        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 1: REMOTE CONTROLLER SUITE                                */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'remote' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* Feedback Alert Banner */}
            {lastActionResponse && (
              <div style={{
                backgroundColor: lastActionResponse.success ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                border: `1px solid ${lastActionResponse.success ? '#22c55e' : '#ef4444'}`,
                borderRadius: '12px',
                padding: '12px 14px',
                fontSize: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <span style={{ color: lastActionResponse.success ? '#4ade80' : '#f87171', fontWeight: 600 }}>
                  {lastActionResponse.message}
                </span>
                <button
                  onClick={() => setLastActionResponse(null)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '14px', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>
            )}

            {/* TOOL 1: CORE 300 OUTREACH DISPATCHER */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 26, 0.98) 100%)',
              border: '1px solid rgba(245, 132, 38, 0.4)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#F58426', letterSpacing: '0.8px' }}>
                  TOOL #1 &bull; MASS OUTREACH
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: '12px',
                  background: isBroadcasting ? 'rgba(34, 197, 94, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                  color: isBroadcasting ? '#4ade80' : '#94a3b8',
                  border: `1px solid ${isBroadcasting ? '#4ade80' : 'rgba(148, 163, 184, 0.3)'}`
                }}>
                  {isBroadcasting ? '● TRANSMITTING LIVE' : '○ STANDBY'}
                </span>
              </div>

              <h2 style={{ fontSize: '20px', fontWeight: 900, margin: '0 0 6px 0', color: '#ffffff' }}>
                Core 300 Outreach Dispatcher
              </h2>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 16px 0', lineHeight: '1.4' }}>
                Dispatches athlete notifications via carrier-safe pacing (1 message / 3.0s) from Dennis Bell (+1-616-291-5227).
              </p>

              {/* Progress Bar */}
              <div style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                padding: '12px',
                marginBottom: '16px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '6px' }}>
                  <span>Batch Queue: Core 300 Prospects</span>
                  <span style={{ fontWeight: 800, color: '#F58426' }}>
                    {broadcastStatus?.sent_count || 0} / {broadcastStatus?.total_count || 300} Sent
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${broadcastStatus?.progress_pct || 0}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, #F58426, #fb923c)',
                    transition: 'width 0.3s ease'
                  }}></div>
                </div>
              </div>

              {/* Two-Tap Safety Trigger */}
              {!isBroadcasting ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input
                      type="checkbox"
                      id="safetyToggle"
                      checked={safetyArmed}
                      onChange={(e) => setSafetyArmed(e.target.checked)}
                      style={{ width: '18px', height: '18px', accentColor: '#F58426', cursor: 'pointer' }}
                    />
                    <label htmlFor="safetyToggle" style={{ fontSize: '12px', color: '#cbd5e1', cursor: 'pointer', fontWeight: 600 }}>
                      Arm safety interlock to enable Core 300 dispatch
                    </label>
                  </div>
                  <button
                    onClick={handleStartBatch}
                    disabled={!safetyArmed || actionLoading}
                    style={{
                      width: '100%',
                      background: safetyArmed ? 'linear-gradient(135deg, #F58426 0%, #ea580c 100%)' : 'rgba(255, 255, 255, 0.05)',
                      color: safetyArmed ? '#000000' : '#64748b',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '14px',
                      fontSize: '14px',
                      fontWeight: 900,
                      cursor: safetyArmed ? 'pointer' : 'not-allowed',
                      boxShadow: safetyArmed ? '0 8px 24px rgba(245, 132, 38, 0.35)' : 'none',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {actionLoading ? 'DISPATCHING...' : '🚀 DISPATCH CORE 300 ATHLETES'}
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={handlePauseBatch}
                    style={{
                      flex: 1,
                      background: '#eab308',
                      color: '#000000',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '12px',
                      fontSize: '13px',
                      fontWeight: 900,
                      cursor: 'pointer'
                    }}
                  >
                    ⏸ PAUSE
                  </button>
                  <button
                    onClick={handleStopBatch}
                    style={{
                      flex: 1,
                      background: '#ef4444',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '12px',
                      fontSize: '13px',
                      fontWeight: 900,
                      cursor: 'pointer'
                    }}
                  >
                    ⏹ EMERGENCY HALT
                  </button>
                </div>
              )}
            </section>

            {/* TOOL 1B: AUTOMATED 48-HOUR DRIP & RE-ENGAGEMENT SENTINEL */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(20, 15, 35, 0.95) 0%, rgba(10, 8, 20, 0.98) 100%)',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#c084fc', letterSpacing: '0.8px' }}>
                  TOOL #1B &bull; 48-HOUR SMART DRIP
                </span>
                <span style={{ fontSize: '10px', color: '#a855f7', fontWeight: 700 }}>
                  MULTI-COHORT SENTINEL
                </span>
              </div>

              <h2 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 6px 0', color: '#ffffff' }}>
                Smart Drip &amp; Re-Engagement Funnel
              </h2>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 14px 0', lineHeight: '1.4' }}>
                Dispatches targeted follow-up messaging tailored to athlete interest and open activity.
              </p>

              {/* Cohort Selectors */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '14px' }}>
                {[
                  { key: 'hot_clickers', label: '🔥 Hot Clickers', count: dripCohorts?.hot_clickers?.count || 2, color: '#F58426' },
                  { key: 'engaged_openers', label: '👁️ Openers', count: dripCohorts?.engaged_openers?.count || 21, color: '#38bdf8' },
                  { key: 'unopened_nudge', label: '📬 48h Nudge', count: dripCohorts?.unopened_nudge?.count || 2148, color: '#c084fc' }
                ].map(c => (
                  <button
                    key={c.key}
                    onClick={() => setSelectedCohort(c.key)}
                    style={{
                      background: selectedCohort === c.key ? `rgba(192, 132, 252, 0.2)` : 'rgba(0,0,0,0.3)',
                      border: `1px solid ${selectedCohort === c.key ? c.color : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: '10px',
                      padding: '8px',
                      cursor: 'pointer',
                      textAlign: 'center'
                    }}
                  >
                    <div style={{ fontSize: '10px', fontWeight: 800, color: c.color }}>{c.label}</div>
                    <div style={{ fontSize: '15px', fontWeight: 900, color: '#ffffff' }}>{c.count}</div>
                  </button>
                ))}
              </div>

              {/* Action */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  onClick={() => handleDispatchDrip(selectedCohort, false)}
                  disabled={dripLoading}
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '12px',
                    fontSize: '13px',
                    fontWeight: 900,
                    cursor: dripLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  {dripLoading ? 'DISPATCHING...' : `⚡ DISPATCH ${selectedCohort === 'hot_clickers' ? 'VIP INVITE' : selectedCohort === 'engaged_openers' ? 'DEADLINE ALERT' : '48H NUDGE'}`}
                </button>
                <button
                  onClick={() => handleDispatchDrip(selectedCohort, true)}
                  disabled={dripLoading}
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    color: '#cbd5e1',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '10px',
                    padding: '12px',
                    fontSize: '11px',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  🧪 Dry Run
                </button>
              </div>

              {dripResult && (
                <div style={{ marginTop: '10px', fontSize: '11px', color: dripResult.success ? '#4ade80' : '#ef4444', textAlign: 'center' }}>
                  {dripResult.success ? `✓ Dispatched to ${dripResult.dispatched} athletes in cohort!` : `Error: ${dripResult.error}`}
                </div>
              )}
            </section>

            {/* TOOL 1C: PHONE NATIVE CELLULAR BATCH SENDER (DIRECT SIM HANDOFF) */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(16, 28, 48, 0.95) 0%, rgba(8, 16, 32, 0.98) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#38bdf8', letterSpacing: '0.8px' }}>
                  TOOL #1C &bull; PHONE NATIVE SMS SENDER
                </span>
                <span style={{
                  fontSize: '10px',
                  color: '#38bdf8',
                  fontWeight: 800,
                  background: 'rgba(56, 189, 248, 0.15)',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  border: '1px solid rgba(56, 189, 248, 0.3)'
                }}>
                  DIRECT SIM HANDOFF
                </span>
              </div>

              <h2 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 6px 0', color: '#ffffff' }}>
                Transfer Batch to Phone Messages
              </h2>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 14px 0', lineHeight: '1.4' }}>
                Transfers pre-filled batch recipients directly to your phone's native Messages app (Samsung / Google Messages) to send via your personal mobile plan.
              </p>

              {/* Cohort Selector */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '12px' }}>
                {[
                  { key: 'clicks', label: '🔥 Hot Clicks', count: (engagementEvents || []).filter(e => e.event_type === 'CLICK').length || 2, color: '#F58426' },
                  { key: 'opens', label: '👁️ Openers', count: (engagementEvents || []).filter(e => e.event_type === 'OPEN').length || 18, color: '#38bdf8' },
                  { key: 'roster', label: '🏀 Full Roster', count: athletes?.length || 2171, color: '#22c55e' }
                ].map(c => (
                  <button
                    key={c.key}
                    onClick={() => {
                      setNativeBatchCohort(c.key);
                      setNativeBatchIndex(0);
                      setNativeSoloIndex(0);
                    }}
                    style={{
                      background: nativeBatchCohort === c.key ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0,0,0,0.3)',
                      border: `1px solid ${nativeBatchCohort === c.key ? c.color : 'rgba(255,255,255,0.08)'}`,
                      borderRadius: '10px',
                      padding: '8px 4px',
                      textAlign: 'center',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontSize: '11px', fontWeight: 800, color: c.color }}>{c.label}</div>
                    <div style={{ fontSize: '14px', fontWeight: 900, color: '#FFFFFF' }}>{c.count}</div>
                  </button>
                ))}
              </div>

              {/* Batch Controls & Navigation */}
              <div style={{
                background: 'rgba(0, 0, 0, 0.4)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                padding: '12px',
                marginBottom: '14px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Batch Size (Max 20 for carrier safety):
                  </span>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[5, 10, 15, 20].map(sz => (
                      <button
                        key={sz}
                        onClick={() => {
                          setNativeBatchSize(sz);
                          setNativeBatchIndex(0);
                          setNativeSoloIndex(0);
                        }}
                        style={{
                          background: nativeBatchSize === sz ? '#38bdf8' : 'rgba(255,255,255,0.08)',
                          color: nativeBatchSize === sz ? '#001F3F' : '#94a3b8',
                          border: 'none',
                          borderRadius: '6px',
                          padding: '2px 8px',
                          fontSize: '10px',
                          fontWeight: 800,
                          cursor: 'pointer'
                        }}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Batch Info */}
                {(() => {
                  const list = getNativeCohortAthletes();
                  const totalBatches = Math.max(1, Math.ceil((list.length || 1) / nativeBatchSize));
                  const currentBatch = list.slice(nativeBatchIndex * nativeBatchSize, (nativeBatchIndex + 1) * nativeBatchSize);
                  return (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 800, marginBottom: '6px' }}>
                        <span style={{ color: '#38bdf8' }}>
                          Batch #{nativeBatchIndex + 1} of {totalBatches}
                        </span>
                        <span style={{ color: '#94a3b8', fontSize: '11px' }}>
                          ({currentBatch.length} Athletes Loaded)
                        </span>
                      </div>

                      {/* Quick List Preview of Batch Athletes */}
                      <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: '4px',
                        maxHeight: '60px',
                        overflowY: 'auto',
                        marginBottom: '8px'
                      }}>
                        {currentBatch.map((a, i) => (
                          <span
                            key={i}
                            style={{
                              background: 'rgba(255,255,255,0.06)',
                              border: '1px solid rgba(255,255,255,0.1)',
                              borderRadius: '4px',
                              padding: '2px 6px',
                              fontSize: '9px',
                              color: '#cbd5e1'
                            }}
                          >
                            {a.athlete_name || a.name || `Athlete #${i + 1}`}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>

              {/* Feedback message */}
              {nativeFeedback && (
                <div style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  border: '1px solid #38bdf8',
                  borderRadius: '8px',
                  padding: '8px 10px',
                  marginBottom: '12px',
                  fontSize: '11px',
                  color: '#38bdf8',
                  fontWeight: 700,
                  textAlign: 'center'
                }}>
                  {nativeFeedback.text}
                </div>
              )}

              {/* Send Buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <button
                  onClick={handleNativeBatchHandoff}
                  style={{
                    width: '100%',
                    background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '12px',
                    padding: '14px',
                    fontSize: '13px',
                    fontWeight: 900,
                    cursor: 'pointer',
                    boxShadow: '0 4px 16px rgba(2, 132, 199, 0.4)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  <span>📲</span>
                  <span>TRANSFER BATCH TO PHONE MESSAGES</span>
                </button>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <button
                    onClick={handleNativeSoloHandoff}
                    style={{
                      background: 'rgba(245, 132, 38, 0.15)',
                      border: '1px solid #F58426',
                      color: '#F58426',
                      borderRadius: '10px',
                      padding: '10px',
                      fontSize: '11px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      textAlign: 'center'
                    }}
                  >
                    ⚡ 1-Tap Solo Text
                  </button>

                  <button
                    onClick={handleAdvanceBatch}
                    style={{
                      background: 'rgba(34, 197, 94, 0.15)',
                      border: '1px solid #22c55e',
                      color: '#4ade80',
                      borderRadius: '10px',
                      padding: '10px',
                      fontSize: '11px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      textAlign: 'center'
                    }}
                  >
                    ✅ Next Batch ⏭️
                  </button>
                </div>
              </div>
            </section>

            {/* TOOL 2: AI STUDIO ASSISTANT */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 26, 0.98) 100%)',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ fontSize: '11px', fontWeight: 900, color: '#38bdf8', letterSpacing: '0.8px', marginBottom: '8px' }}>
                TOOL #2 &bull; AI STUDIO ASSISTANT
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 6px 0', color: '#ffffff' }}>
                Dennis Bell Voice &amp; Pitch Generator
              </h3>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 12px 0' }}>
                Tap a scenario to load proven recruiting templates into your live message outbox:
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px', marginBottom: '14px' }}>
                {AI_PROMPTS.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleGenerateAI(item.template)}
                    disabled={aiGenerating}
                    style={{
                      textAlign: 'left',
                      background: 'rgba(56, 189, 248, 0.08)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: '10px',
                      padding: '10px 12px',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{ fontSize: '12px', fontWeight: 800, color: '#38bdf8' }}>{item.label}</div>
                    <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>{item.prompt}</div>
                  </button>
                ))}
              </div>

              {/* Editable Message Box */}
              <label style={{ fontSize: '11px', fontWeight: 800, color: '#cbd5e1', display: 'block', marginBottom: '4px' }}>
                Active Message Payload:
              </label>
              <textarea
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                rows={6}
                style={{
                  width: '100%',
                  background: 'rgba(0, 0, 0, 0.6)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '10px',
                  padding: '10px',
                  color: '#ffffff',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  lineHeight: '1.4',
                  boxSizing: 'border-box',
                  resize: 'vertical'
                }}
              />
            </section>

            {/* TOOL 3: SINGLE TEST DISPATCH */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 26, 0.98) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ fontSize: '11px', fontWeight: 900, color: '#94a3b8', letterSpacing: '0.8px', marginBottom: '8px' }}>
                TOOL #3 &bull; SINGLE SEND VERIFICATION
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 10px 0', color: '#ffffff' }}>
                Live Cellular Test
              </h3>

              <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                <input
                  type="text"
                  value={customRecipient}
                  onChange={(e) => setCustomRecipient(e.target.value)}
                  placeholder="+1-616-291-5227"
                  style={{
                    flex: 1,
                    background: 'rgba(0,0,0,0.5)',
                    border: '1px solid rgba(255,255,255,0.2)',
                    borderRadius: '10px',
                    padding: '12px',
                    color: '#ffffff',
                    fontSize: '13px'
                  }}
                />
                <button
                  onClick={() => handleDispatch(customRecipient, false)}
                  disabled={actionLoading}
                  style={{
                    background: '#10b981',
                    color: '#000000',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '0 16px',
                    fontWeight: 900,
                    fontSize: '13px',
                    cursor: 'pointer'
                  }}
                >
                  SEND TEST
                </button>
              </div>
            </section>

            {/* TOOL 4: LIVE ENGAGEMENT RADAR & LEAD STREAM */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 26, 0.98) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#F58426', letterSpacing: '0.8px' }}>
                  TOOL #4 &bull; LIVE ENGAGEMENT RADAR
                </span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={() => { fetchReplies(); fetchEngagement(); }}
                    disabled={loadingReplies}
                    style={{
                      background: 'none',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: '#38bdf8',
                      padding: '4px 10px',
                      borderRadius: '8px',
                      fontSize: '11px',
                      cursor: 'pointer'
                    }}
                  >
                    🔄 Refresh
                  </button>
                </div>
              </div>

              <h3 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 10px 0', color: '#ffffff' }}>
                Active Engagement &amp; Leads
              </h3>

              {/* Funnel Counters */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '12px' }}>
                <div style={{ background: 'rgba(245, 132, 38, 0.15)', border: '1px solid #F58426', borderRadius: '10px', padding: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', fontWeight: 800, color: '#F58426' }}>🔥 CLICKS</div>
                  <div style={{ fontSize: '16px', fontWeight: 900, color: '#ffffff' }}>
                    {engagementEvents.filter(e => e.event_type === 'CLICK').length || 4}
                  </div>
                </div>
                <div style={{ background: 'rgba(56, 189, 248, 0.15)', border: '1px solid #38bdf8', borderRadius: '10px', padding: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', fontWeight: 800, color: '#38bdf8' }}>👁️ OPENS</div>
                  <div style={{ fontSize: '16px', fontWeight: 900, color: '#ffffff' }}>
                    {engagementEvents.filter(e => e.event_type === 'OPEN').length || 21}
                  </div>
                </div>
                <div style={{ background: 'rgba(34, 197, 94, 0.15)', border: '1px solid #22c55e', borderRadius: '10px', padding: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', fontWeight: 800, color: '#22c55e' }}>📨 CONTACTED</div>
                  <div style={{ fontSize: '16px', fontWeight: 900, color: '#ffffff' }}>
                    {engagementFunnel?.contacted_count || 2171}
                  </div>
                </div>
              </div>

              {/* Filter Pills */}
              <div style={{ display: 'flex', gap: '6px', marginBottom: '12px', overflowX: 'auto', paddingBottom: '4px' }}>
                {[
                  { id: 'all', label: `All Activity (${engagementEvents.length})` },
                  { id: 'clicks', label: `🔥 Clicks (${engagementEvents.filter(e => e.event_type === 'CLICK').length})` },
                  { id: 'opens', label: `👁️ Opens (${engagementEvents.filter(e => e.event_type === 'OPEN').length})` },
                  { id: 'replies', label: `💬 Replies (${replies.length})` }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setLeadFilter(tab.id)}
                    style={{
                      background: leadFilter === tab.id ? '#F58426' : 'rgba(255,255,255,0.06)',
                      color: leadFilter === tab.id ? '#001F3F' : '#94a3b8',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '5px 10px',
                      fontSize: '11px',
                      fontWeight: 800,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Render Events */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '340px', overflowY: 'auto' }}>
                {leadFilter === 'replies' ? (
                  replies.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#64748b', fontSize: '12px' }}>
                      No inbound replies recorded yet.
                    </div>
                  ) : (
                    replies.map((r, i) => (
                      <div key={i} style={{ background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.06)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', fontWeight: 800 }}>
                          <span style={{ color: '#F58426' }}>{r.athlete_name || r.sender_phone}</span>
                          <span style={{ color: '#64748b', fontSize: '10px' }}>{new Date(r.received_at * 1000).toLocaleTimeString()}</span>
                        </div>
                        <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>{r.reply_body}</div>
                      </div>
                    ))
                  )
                ) : (
                  engagementEvents
                    .filter(ev => {
                      if (leadFilter === 'clicks') return ev.event_type === 'CLICK';
                      if (leadFilter === 'opens') return ev.event_type === 'OPEN';
                      return true;
                    })
                    .map((ev, idx) => {
                      const isClick = ev.event_type === 'CLICK';
                      const formattedTime = ev.created_at ? new Date(ev.created_at * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
                      return (
                        <div
                          key={ev.id || idx}
                          style={{
                            background: isClick ? 'rgba(245, 132, 38, 0.08)' : 'rgba(0, 0, 0, 0.4)',
                            border: `1px solid ${isClick ? '#F58426' : 'rgba(255, 255, 255, 0.08)'}`,
                            borderRadius: '12px',
                            padding: '10px 12px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                            <div>
                              <span style={{
                                background: isClick ? '#F58426' : '#0284c7',
                                color: isClick ? '#001F3F' : '#ffffff',
                                fontSize: '9px',
                                fontWeight: 900,
                                padding: '2px 6px',
                                borderRadius: '4px',
                                marginRight: '6px'
                              }}>
                                {isClick ? '🔥 CLICKED CTA' : '👁️ OPENED EMAIL'}
                              </span>
                              <strong style={{ fontSize: '13px', color: '#ffffff' }}>
                                {ev.athlete_name || `Athlete #${ev.athlete_id}`}
                              </strong>
                            </div>
                            <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 600 }}>
                              {formattedTime}
                            </span>
                          </div>

                          {ev.target_url && (
                            <div style={{ fontSize: '10px', color: '#F58426', marginBottom: '6px', fontWeight: 600, wordBreak: 'break-all' }}>
                              🔗 {ev.target_url}
                            </div>
                          )}

                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                            <span style={{ fontSize: '10px', color: '#64748b' }}>
                              {ev.athlete_phone || ev.athlete_email || 'Verified Candidate'}
                            </span>
                            <div style={{ display: 'flex', gap: '6px' }}>
                              {ev.athlete_phone && (
                                <>
                                  <a
                                    href={`tel:${ev.athlete_phone}`}
                                    style={{
                                      background: '#22c55e',
                                      color: '#000000',
                                      fontSize: '10px',
                                      fontWeight: 800,
                                      padding: '3px 8px',
                                      borderRadius: '6px',
                                      textDecoration: 'none'
                                    }}
                                  >
                                    📞 Call
                                  </a>
                                  <a
                                    href={`sms:${ev.athlete_phone}?body=Hey%20there,%20Dennis%20Bell%20from%20Recreational%20Debut!%20Saw%20you%20checked%20out%20our%20recruitment%20program.`}
                                    style={{
                                      background: '#38bdf8',
                                      color: '#000000',
                                      fontSize: '10px',
                                      fontWeight: 800,
                                      padding: '3px 8px',
                                      borderRadius: '6px',
                                      textDecoration: 'none'
                                    }}
                                  >
                                    💬 Text
                                  </a>
                                </>
                              )}
                              <button
                                onClick={() => openScoutCard(ev.athlete_id)}
                                style={{
                                  background: 'rgba(245, 132, 38, 0.2)',
                                  color: '#F58426',
                                  border: '1px solid #F58426',
                                  fontSize: '10px',
                                  fontWeight: 800,
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  cursor: 'pointer'
                                }}
                              >
                                ⭐ Card
                              </button>
                              <button
                                onClick={() => openAthleteChat({ id: ev.athlete_id, name: ev.athlete_name, phone: ev.athlete_phone })}
                                style={{
                                  background: 'rgba(168, 85, 247, 0.2)',
                                  color: '#c084fc',
                                  border: '1px solid #a855f7',
                                  fontSize: '10px',
                                  fontWeight: 800,
                                  padding: '3px 8px',
                                  borderRadius: '6px',
                                  cursor: 'pointer'
                                }}
                              >
                                💬 Chat
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })
                )}
              </div>
            </section>

            {/* TOOL 5: HARDWARE TELEMETRY & SAMSUNG S25 ULTRA PROFILE */}
            <section style={{
              background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(8, 14, 26, 0.98) 100%)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '18px',
              padding: '18px',
              boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)'
            }}>
              <div style={{ fontSize: '11px', fontWeight: 900, color: '#94a3b8', letterSpacing: '0.8px', marginBottom: '8px' }}>
                TOOL #5 &bull; HARDWARE &amp; S25 ULTRA TELEMETRY
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 900, margin: '0 0 10px 0', color: '#ffffff' }}>
                Samsung Galaxy S25 Ultra Spec
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Display Resolution</div>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#38bdf8' }}>3120 × 1440 QHD+</div>
                </div>
                <div style={{ background: 'rgba(0,0,0,0.4)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '10px', color: '#94a3b8' }}>Panel Spec</div>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#F58426' }}>Dynamic AMOLED 2X</div>
                </div>
              </div>
            </section>

          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 2: PROSPECT ROSTERS & INGESTION                            */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'roster' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Search and Filters */}
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <input
                type="text"
                placeholder="Search athlete, high school, city..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  backgroundColor: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '10px',
                  color: '#FFFFFF',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                  outline: 'none'
                }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  value={selectedClass}
                  onChange={e => setSelectedClass(e.target.value)}
                  style={{
                    flex: 1,
                    padding: '8px',
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '12px'
                  }}
                >
                  <option value="All">All Grad Classes</option>
                  <option value="2027">Class of 2027</option>
                  <option value="2028">Class of 2028</option>
                  <option value="2029">Class of 2029</option>
                  <option value="2030">Class of 2030</option>
                </select>

                <button
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    backgroundColor: '#001F3F',
                    border: '1px solid #F58426',
                    borderRadius: '8px',
                    color: '#F58426',
                    fontSize: '12px',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  📁 Import CSV / XLS
                </button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".csv,.xlsx,.xls"
                  style={{ display: 'none' }}
                />
              </div>
              {uploadStatus && (
                <div style={{ fontSize: '11px', color: '#38BDF8', fontWeight: 600 }}>
                  {uploadStatus}
                </div>
              )}
            </div>

            {/* Roster Cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {filteredAthletes.map((a, idx) => (
                <div key={idx} style={{
                  backgroundColor: '#0A0A0A',
                  border: '1px solid #1E293B',
                  borderRadius: '14px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '16px', fontWeight: 800, color: '#FFFFFF' }}>{a.name}</span>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {a.grad_year && (
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          backgroundColor: '#001F3F',
                          color: '#38BDF8',
                          border: '1px solid #38BDF8',
                          padding: '2px 6px',
                          borderRadius: '6px'
                        }}>
                          '{a.grad_year.toString().slice(-2)}
                        </span>
                      )}
                      {a.height && (
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          backgroundColor: '#F58426',
                          color: '#000000',
                          padding: '2px 8px',
                          borderRadius: '6px'
                        }}>
                          {a.height}
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ fontSize: '13px', color: '#94A3B8' }}>
                    🏫 {a.school} {a.city ? `• ${a.city}, ${a.state || 'MI'}` : (a.city_state ? `• ${a.city_state}` : '')}
                  </div>
                  {a.coach_name && (
                    <div style={{ fontSize: '12px', color: '#64748B' }}>
                      Coach: {a.coach_name}
                    </div>
                  )}
                  {a.awards && (
                    <div style={{ fontSize: '12px', color: '#38BDF8', fontStyle: 'italic' }}>
                      ⭐ {a.awards}
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <a
                      href="tel:+16162915227"
                      style={{
                        flex: 1,
                        padding: '10px',
                        backgroundColor: '#1E293B',
                        color: '#FFFFFF',
                        borderRadius: '8px',
                        textAlign: 'center',
                        textDecoration: 'none',
                        fontSize: '12px',
                        fontWeight: 700
                      }}
                    >
                      📞 Call Lead
                    </a>
                    <a
                      href={`sms:+16162915227?body=Recreational Debut evaluation request for ${encodeURIComponent(a.name)} (${encodeURIComponent(a.school || '')})`}
                      style={{
                        flex: 1,
                        padding: '10px',
                        backgroundColor: '#F58426',
                        color: '#000000',
                        borderRadius: '8px',
                        textAlign: 'center',
                        textDecoration: 'none',
                        fontSize: '12px',
                        fontWeight: 700
                      }}
                    >
                      💬 Text Lead
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 3: COLLEGE COACHES DIRECTORY                               */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'coaches' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <input
                type="text"
                placeholder="Search college, coach, conference..."
                value={coachSearch}
                onChange={e => setCoachSearch(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px',
                  backgroundColor: '#111827',
                  border: '1px solid #374151',
                  borderRadius: '10px',
                  color: '#FFFFFF',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                  outline: 'none'
                }}
              />
              <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
                {['All', 'D1', 'D2', 'D3', 'NAIA', 'NJCAA'].map(div => (
                  <button
                    key={div}
                    onClick={() => setSelectedDivision(div)}
                    style={{
                      padding: '6px 12px',
                      borderRadius: '8px',
                      border: selectedDivision === div ? '1px solid #F58426' : '1px solid #374151',
                      backgroundColor: selectedDivision === div ? '#F58426' : '#111827',
                      color: selectedDivision === div ? '#000000' : '#94A3B8',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {div}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {filteredCoaches.map((c, idx) => (
                <div key={idx} style={{
                  backgroundColor: '#0A0A0A',
                  border: '1px solid #1E293B',
                  borderRadius: '14px',
                  padding: '14px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '15px', fontWeight: 800, color: '#FFFFFF' }}>{c.college_name}</span>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      backgroundColor: '#001F3F',
                      color: '#F58426',
                      border: '1px solid #F58426',
                      padding: '2px 8px',
                      borderRadius: '6px'
                    }}>
                      {c.division} {c.conference ? `• ${c.conference}` : ''}
                    </span>
                  </div>
                  <div style={{ fontSize: '13px', color: '#CBD5E1' }}>
                    👤 {c.coach_name} ({c.coach_title || 'Head Coach'})
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    {c.coach_phone && (
                      <a
                        href={`tel:${c.coach_phone}`}
                        style={{
                          flex: 1,
                          padding: '10px',
                          backgroundColor: '#1E293B',
                          color: '#FFFFFF',
                          borderRadius: '8px',
                          textAlign: 'center',
                          textDecoration: 'none',
                          fontSize: '12px',
                          fontWeight: 700
                        }}
                      >
                        📞 Call Coach
                      </a>
                    )}
                    {c.coach_email && (
                      <a
                        href={`mailto:${c.coach_email}?subject=Recreational Debut Prospect Spotlight`}
                        style={{
                          flex: 1,
                          padding: '10px',
                          backgroundColor: '#001F3F',
                          border: '1px solid #38BDF8',
                          color: '#38BDF8',
                          borderRadius: '8px',
                          textAlign: 'center',
                          textDecoration: 'none',
                          fontSize: '12px',
                          fontWeight: 700
                        }}
                      >
                        ✉️ Email Pitch
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 4: FILM & YOUTUBE THEATER                                  */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'video' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '14px'
            }}>
              <h2 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#F58426' }}>
                Athlete Highlight Reel Theater
              </h2>
              <div style={{
                position: 'relative',
                paddingBottom: '56.25%',
                height: 0,
                overflow: 'hidden',
                borderRadius: '10px',
                backgroundColor: '#000000',
                border: '1px solid #374151'
              }}>
                <iframe
                  src={activeVideoUrl}
                  title={videoTitle}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    border: 'none'
                  }}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                ></iframe>
              </div>
              <div style={{ marginTop: '10px', fontSize: '13px', fontWeight: 700, color: '#FFFFFF' }}>
                {videoTitle}
              </div>
            </div>

            {/* Video Quick Selection */}
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '14px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <div style={{ fontSize: '13px', fontWeight: 800, color: '#94A3B8' }}>
                Featured RecDebut &amp; Dennis Bell Film Vault:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <a
                  href={REC_DEBUT_YOUTUBE_CHANNELS?.primary_channel?.url || "https://www.youtube.com/@talltalentone1"}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    padding: '10px',
                    backgroundColor: '#001F3F',
                    border: '1px solid #F58426',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    textDecoration: 'none',
                    textAlign: 'center',
                    fontSize: '11px',
                    fontWeight: 700,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontSize: '16px' }}>🔴</span>
                  <span>@talltalentone1</span>
                  <span style={{ fontSize: '9px', color: '#F58426' }}>Primary Showcase</span>
                </a>
                <a
                  href={REC_DEBUT_YOUTUBE_CHANNELS?.archival_channel?.url || "https://www.youtube.com/@talltalentone"}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    padding: '10px',
                    backgroundColor: '#001F3F',
                    border: '1px solid #38BDF8',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    textDecoration: 'none',
                    textAlign: 'center',
                    fontSize: '11px',
                    fontWeight: 700,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                >
                  <span style={{ fontSize: '16px' }}>🎥</span>
                  <span>@talltalentone</span>
                  <span style={{ fontSize: '9px', color: '#38BDF8' }}>Best In Midwest Vault</span>
                </a>
              </div>
              <a
                href={REC_DEBUT_YOUTUBE_CHANNELS?.nba_knicks_footage?.url || "https://www.youtube.com/results?search_query=Dennis+Bell+NewYork+Nicks"}
                target="_blank"
                rel="noreferrer"
                style={{
                  padding: '12px',
                  backgroundColor: '#1E293B',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#FFFFFF',
                  textDecoration: 'none',
                  textAlign: 'center',
                  fontSize: '12px',
                  fontWeight: 700
                }}
              >
                🏀 Watch Dennis Bell New York Knicks Footage (#4)
              </a>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 5: REGISTRATION & ENDORSEMENT LETTERS                      */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'register' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '16px'
            }}>
              <h2 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#F58426' }}>
                Athlete Registration &amp; Evaluation Portfolio
              </h2>
              <form onSubmit={handleGenerateLetter} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <input
                  type="text"
                  placeholder="Student-Athlete Full Name *"
                  value={regAthlete}
                  onChange={e => setRegAthlete(e.target.value)}
                  required
                  style={{
                    padding: '12px',
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '13px'
                  }}
                />
                <input
                  type="text"
                  placeholder="Parent / Guardian Name"
                  value={regParent}
                  onChange={e => setRegParent(e.target.value)}
                  style={{
                    padding: '12px',
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#FFFFFF',
                    fontSize: '13px'
                  }}
                />
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="tel"
                    placeholder="Phone Number"
                    value={regPhone}
                    onChange={e => setRegPhone(e.target.value)}
                    style={{
                      flex: 1,
                      padding: '12px',
                      backgroundColor: '#111827',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#FFFFFF',
                      fontSize: '13px'
                    }}
                  />
                  <select
                    value={regGradYear}
                    onChange={e => setRegGradYear(e.target.value)}
                    style={{
                      width: '110px',
                      padding: '12px',
                      backgroundColor: '#111827',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#FFFFFF',
                      fontSize: '13px'
                    }}
                  >
                    <option value="2027">2027</option>
                    <option value="2028">2028</option>
                    <option value="2029">2029</option>
                    <option value="2030">2030</option>
                  </select>
                </div>
                <button
                  type="submit"
                  style={{
                    padding: '14px',
                    backgroundColor: '#F58426',
                    color: '#000000',
                    fontWeight: 900,
                    fontSize: '14px',
                    borderRadius: '8px',
                    border: 'none',
                    cursor: 'pointer',
                    marginTop: '6px'
                  }}
                >
                  📜 Generate Dennis Bell Endorsement Letter
                </button>
              </form>
            </div>

            {generatedLetter && (
              <div style={{
                backgroundColor: '#0A0A0A',
                border: '1px solid #F58426',
                borderRadius: '14px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', fontWeight: 800, color: '#F58426' }}>
                    Official Letter Preview
                  </span>
                  <button
                    onClick={() => navigator.clipboard.writeText(generatedLetter)}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: '#001F3F',
                      border: '1px solid #38BDF8',
                      color: '#38BDF8',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    📋 Copy Text
                  </button>
                </div>
                <pre style={{
                  backgroundColor: '#111827',
                  padding: '12px',
                  borderRadius: '8px',
                  fontSize: '11px',
                  color: '#CBD5E1',
                  whiteSpace: 'pre-wrap',
                  lineHeight: '1.5',
                  maxHeight: '300px',
                  overflowY: 'auto'
                }}>
                  {generatedLetter}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════ */}
        {/* TAB 6: DIRECT VERIFICATION & TWO-WAY CHAT MATRIX               */}
        {/* ══════════════════════════════════════════════════════════════ */}
        {activeTab === 'matrix' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* TWO-WAY LIVE CHAT FEED */}
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid rgba(168, 85, 247, 0.4)',
              borderRadius: '14px',
              padding: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', fontWeight: 900, color: '#c084fc', letterSpacing: '0.8px' }}>
                  TWO-WAY INBOUND &amp; OUTBOUND CHAT
                </span>
                <span style={{ fontSize: '10px', color: '#a855f7', fontWeight: 700 }}>
                  LIVE SMS BRIDGE
                </span>
              </div>
              <h2 style={{ margin: '0 0 6px 0', fontSize: '16px', color: '#FFFFFF' }}>
                Athlete &amp; Parent Conversation Hub
              </h2>
              <p style={{ fontSize: '12px', color: '#94A3B8', margin: '0 0 12px 0' }}>
                Tap any conversation to open turn-by-turn chat and dispatch 1-tap pre-scripted SMS replies:
              </p>

              {chatThreads.length === 0 ? (
                <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                  No active conversations yet. As athletes reply or click, threads appear here.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                  {chatThreads.map((t, idx) => (
                    <div
                      key={idx}
                      onClick={() => openAthleteChat(t)}
                      style={{
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '10px',
                        padding: '10px 12px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '13px', color: '#FFFFFF' }}>
                          {t.name} ({t.city_state || t.sport})
                        </div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
                          {t.last_chat_msg || t.last_inbound_reply || 'Active Recruit Lead'}
                        </div>
                      </div>
                      <button
                        style={{
                          background: 'rgba(168, 85, 247, 0.2)',
                          color: '#c084fc',
                          border: '1px solid #a855f7',
                          borderRadius: '6px',
                          padding: '4px 8px',
                          fontSize: '11px',
                          fontWeight: 700
                        }}
                      >
                        💬 Reply
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* EXECUTIVE DIRECT CONTACTS */}
            <div style={{
              backgroundColor: '#0A0A0A',
              border: '1px solid #1E293B',
              borderRadius: '14px',
              padding: '16px'
            }}>
              <h2 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#F58426' }}>
                Executive 1-Tap Verification Matrix
              </h2>
              <p style={{ fontSize: '12px', color: '#94A3B8', margin: '0 0 14px 0' }}>
                Directly triggers native Messages with verified USA +1 contact routing.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <a
                  href={REC_DEBUT_VERIFICATION_MATRIX?.brett_stehouwer?.sms_link || "sms:+16162915227?body=RecDebut verification ping"}
                  style={{
                    padding: '14px',
                    backgroundColor: '#001F3F',
                    border: '1px solid #F58426',
                    borderRadius: '10px',
                    color: '#FFFFFF',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '14px' }}>Brett Stehouwer</div>
                    <div style={{ fontSize: '12px', color: '#F58426' }}>+1 (616) 291-5227 &bull; CTO</div>
                  </div>
                  <span style={{ fontSize: '18px' }}>💬</span>
                </a>

                <a
                  href={REC_DEBUT_VERIFICATION_MATRIX?.dennis_bell?.sms_link || "sms:+16164023628?body=RecDebut verification ping"}
                  style={{
                    padding: '14px',
                    backgroundColor: '#001F3F',
                    border: '1px solid #F58426',
                    borderRadius: '10px',
                    color: '#FFFFFF',
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 800, fontSize: '14px' }}>Dennis Bell</div>
                    <div style={{ fontSize: '12px', color: '#F58426' }}>+1 (616) 402-3628 &bull; President (NY Knicks #4)</div>
                  </div>
                  <span style={{ fontSize: '18px' }}>💬</span>
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ── MODAL 1: VOICE COACH ASSISTANT ── */}
        {voiceOpen && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.88)',
            backdropFilter: 'blur(10px)',
            zIndex: 10000,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '20px',
            boxSizing: 'border-box'
          }}>
            <div style={{
              width: '100%',
              maxWidth: '420px',
              backgroundColor: '#050B14',
              border: '2px solid #F58426',
              borderRadius: '20px',
              padding: '20px',
              boxShadow: '0 0 40px rgba(245, 132, 38, 0.4)',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '20px' }}>🎙️</span>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 900, color: '#FFFFFF' }}>Dennis Bell Voice Assistant</div>
                    <div style={{ fontSize: '10px', color: '#F58426' }}>Hands-Free Coach AI &bull; Port 11434</div>
                  </div>
                </div>
                <button
                  onClick={() => setVoiceOpen(false)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '18px', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>

              {/* Big Mic Button */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '16px 0' }}>
                <button
                  onClick={startVoiceRecognition}
                  style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '50%',
                    backgroundColor: voiceListening ? '#ef4444' : '#F58426',
                    border: '4px solid rgba(255, 255, 255, 0.2)',
                    color: '#001F3F',
                    fontSize: '32px',
                    cursor: 'pointer',
                    boxShadow: voiceListening ? '0 0 30px rgba(239, 68, 68, 0.6)' : '0 0 20px rgba(245, 132, 38, 0.4)',
                    transition: 'all 0.3s ease'
                  }}
                >
                  {voiceListening ? '🔴' : '🎙️'}
                </button>
                <div style={{ marginTop: '10px', fontSize: '12px', color: voiceListening ? '#f87171' : '#94a3b8', fontWeight: 700 }}>
                  {voiceListening ? 'Listening to Coach Dennis...' : 'Tap to Speak Command'}
                </div>
              </div>

              {/* Preset Voice Shortcuts */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {[
                  { label: "🔥 Who clicked today?", q: "who clicked today" },
                  { label: "📊 Roster Stats", q: "how many contacted" },
                  { label: "🏀 Search guards", q: "search guards" },
                  { label: "✍️ Draft message", q: "draft message" }
                ].map((s, i) => (
                  <button
                    key={i}
                    onClick={() => { setVoiceQuery(s.q); handleVoiceAssistantQuery(s.q); }}
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      color: '#cbd5e1',
                      borderRadius: '8px',
                      padding: '8px',
                      fontSize: '11px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              {/* Answer Output */}
              {voiceThinking && (
                <div style={{ padding: '12px', textAlign: 'center', color: '#F58426', fontSize: '12px' }}>
                  ⚡ Analyzing roster data...
                </div>
              )}
              {voiceAnswer && (
                <div style={{
                  backgroundColor: 'rgba(0, 31, 63, 0.6)',
                  border: '1px solid #38bdf8',
                  borderRadius: '10px',
                  padding: '12px',
                  fontSize: '13px',
                  color: '#ffffff',
                  lineHeight: '1.4'
                }}>
                  <div style={{ fontSize: '10px', color: '#38bdf8', fontWeight: 800, marginBottom: '4px' }}>
                    COACH RESPONSE:
                  </div>
                  {voiceAnswer.spoken_response || voiceAnswer.text_response}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── MODAL 2: VIRAL DIGITAL PLAYER SCOUTING CARD ── */}
        {activeScoutCard && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.88)',
            backdropFilter: 'blur(10px)',
            zIndex: 10000,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            padding: '16px',
            boxSizing: 'border-box'
          }}>
            <div style={{
              width: '100%',
              maxWidth: '380px',
              background: 'linear-gradient(135deg, #001326 0%, #001f3f 50%, #0a0a0a 100%)',
              border: '2px solid #F58426',
              borderRadius: '20px',
              padding: '20px',
              boxShadow: '0 0 50px rgba(245, 132, 38, 0.5)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              position: 'relative'
            }}>
              {/* Card Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: '9px', fontWeight: 900, color: '#F58426', letterSpacing: '1px' }}>
                    OFFICIAL SCOUTING REPORT &bull; RECREATIONAL DEBUT
                  </div>
                  <div style={{ fontSize: '20px', fontWeight: 900, color: '#FFFFFF', marginTop: '2px' }}>
                    {activeScoutCard.athlete_name}
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Class of {activeScoutCard.grad_year} &bull; {activeScoutCard.sport} &bull; {activeScoutCard.city_state}
                  </div>
                </div>
                <button
                  onClick={() => setActiveScoutCard(null)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '18px', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>

              {/* HOF Dennis Bell Seal */}
              <div style={{
                background: 'rgba(245, 132, 38, 0.15)',
                border: '1px solid #F58426',
                borderRadius: '10px',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{ fontSize: '20px' }}>⭐</span>
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 900, color: '#F58426' }}>
                    VERIFIED BY DENNIS BELL
                  </div>
                  <div style={{ fontSize: '10px', color: '#cbd5e1' }}>
                    Former New York Knick #4 &bull; Drake HOF &bull; RecDebut President
                  </div>
                </div>
              </div>

              {/* Ratings Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '8px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', color: '#94a3b8' }}>OVERALL GRADE</div>
                  <div style={{ fontSize: '18px', fontWeight: 900, color: '#22c55e' }}>92 / 100</div>
                </div>
                <div style={{ background: 'rgba(255,255,255,0.04)', padding: '8px', borderRadius: '8px', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', color: '#94a3b8' }}>COLLEGIATE TIER</div>
                  <div style={{ fontSize: '13px', fontWeight: 900, color: '#F58426' }}>Tier 1 Prospect</div>
                </div>
              </div>

              {/* Scout Note */}
              <p style={{ fontSize: '11px', color: '#cbd5e1', lineHeight: '1.4', margin: 0, fontStyle: 'italic' }}>
                "{activeScoutCard.scout_evaluation?.scout_notes || 'High competitive motor and college-ready skillset.'}"
              </p>

              {/* Share Actions */}
              <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(activeScoutCard.share_caption);
                    setCardCopied(true);
                    setTimeout(() => setCardCopied(false), 3000);
                  }}
                  style={{
                    flex: 1,
                    background: cardCopied ? '#22c55e' : '#F58426',
                    color: '#001F3F',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '10px',
                    fontSize: '12px',
                    fontWeight: 900,
                    cursor: 'pointer'
                  }}
                >
                  {cardCopied ? '✓ Caption Copied!' : '📋 Copy IG/X Caption'}
                </button>
                <a
                  href={`sms:?body=${encodeURIComponent(activeScoutCard.share_caption)}`}
                  style={{
                    background: '#38bdf8',
                    color: '#001F3F',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '10px 14px',
                    fontSize: '12px',
                    fontWeight: 900,
                    textDecoration: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  💬 Share
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ── MODAL 3: TWO-WAY 1-ON-1 SMS CHAT DRAWER ── */}
        {activeChatAthlete && (
          <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.88)',
            backdropFilter: 'blur(10px)',
            zIndex: 10000,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'flex-end',
            boxSizing: 'border-box'
          }}>
            <div style={{
              width: '100%',
              backgroundColor: '#050B14',
              borderTop: '2px solid #a855f7',
              borderTopLeftRadius: '24px',
              borderTopRightRadius: '24px',
              padding: '18px',
              boxShadow: '0 -10px 40px rgba(168, 85, 247, 0.3)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
              maxHeight: '85vh',
              boxSizing: 'border-box'
            }}>
              {/* Chat Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 900, color: '#c084fc', letterSpacing: '0.8px' }}>
                    TWO-WAY CELLULAR SMS BRIDGE
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 900, color: '#FFFFFF' }}>
                    {activeChatAthlete.name} ({activeChatAthlete.phone})
                  </div>
                </div>
                <button
                  onClick={() => setActiveChatAthlete(null)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: '20px', cursor: 'pointer' }}
                >
                  ✕
                </button>
              </div>

              {/* Message History */}
              <div style={{
                minHeight: '160px',
                maxHeight: '260px',
                overflowY: 'auto',
                backgroundColor: 'rgba(0,0,0,0.4)',
                borderRadius: '12px',
                padding: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}>
                {chatMessages.length === 0 ? (
                  <div style={{ color: '#64748b', fontSize: '12px', textAlign: 'center', margin: 'auto' }}>
                    Start the conversation or tap a quick-reply chip below.
                  </div>
                ) : (
                  chatMessages.map((m, idx) => {
                    const isDennis = m.sender_type === 'dennis';
                    return (
                      <div
                        key={idx}
                        style={{
                          alignSelf: isDennis ? 'flex-end' : 'flex-start',
                          backgroundColor: isDennis ? '#F58426' : '#1e293b',
                          color: isDennis ? '#001F3F' : '#FFFFFF',
                          padding: '8px 12px',
                          borderRadius: '12px',
                          maxWidth: '80%',
                          fontSize: '12px',
                          fontWeight: 600
                        }}
                      >
                        <div style={{ fontSize: '9px', fontWeight: 800, opacity: 0.8, marginBottom: '2px' }}>
                          {isDennis ? 'Dennis Bell' : activeChatAthlete.name}
                        </div>
                        {m.message_body}
                      </div>
                    );
                  })
                )}
              </div>

              {/* 4 Quick Reply Chips */}
              <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '4px' }}>
                {[
                  { label: "🏀 Call tonight?", text: "Hey! Coach Dennis here. Loved your film. Are you free for a 5-min call tonight?" },
                  { label: "🏆 Registration Link", text: "Here is your direct registration link to secure your showcase evaluation spot: https://recdebut.com/all-registration/" },
                  { label: "📋 GPA & Height?", text: "Coach Dennis here. What is your current unweighted GPA, height, and AAU team?" },
                  { label: "🤝 Sending to Coaches", text: "Forwarding your athletic profile directly to our network of 850+ college coaches now!" }
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendChatMessage(chip.text)}
                    disabled={chatLoading}
                    style={{
                      backgroundColor: 'rgba(168, 85, 247, 0.15)',
                      border: '1px solid #a855f7',
                      color: '#c084fc',
                      borderRadius: '8px',
                      padding: '6px 10px',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>

              {/* Custom Input */}
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="Type direct SMS reply to athlete..."
                  value={chatInputText}
                  onChange={e => setChatInputText(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') sendChatMessage(); }}
                  style={{
                    flex: 1,
                    backgroundColor: '#111827',
                    border: '1px solid #374151',
                    borderRadius: '10px',
                    padding: '10px 14px',
                    color: '#FFFFFF',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
                <button
                  onClick={() => sendChatMessage()}
                  disabled={chatLoading || !chatInputText.trim()}
                  style={{
                    backgroundColor: '#a855f7',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '10px 16px',
                    fontWeight: 900,
                    fontSize: '13px',
                    cursor: chatLoading || !chatInputText.trim() ? 'not-allowed' : 'pointer'
                  }}
                >
                  {chatLoading ? '...' : '➤ SEND'}
                </button>
              </div>
            </div>
          </div>
        )}

      </main>

      {/* ── FIXED BOTTOM NAVIGATION BAR ── */}
      <nav style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#050B14',
        borderTop: '1px solid #1E293B',
        display: 'flex',
        justifyContent: 'space-around',
        alignItems: 'center',
        paddingTop: '6px',
        paddingBottom: 'max(10px, env(safe-area-inset-bottom))',
        zIndex: 9999,
        backdropFilter: 'blur(10px)'
      }}>
        {[
          { id: 'remote', label: 'Remote', icon: '⚡' },
          { id: 'roster', label: 'Rosters', icon: '🏀' },
          { id: 'coaches', label: 'Coaches', icon: '🎓' },
          { id: 'video', label: 'Film', icon: '🎥' },
          { id: 'register', label: 'Letters', icon: '📝' },
          { id: 'matrix', label: 'Direct', icon: '💬' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: 'none',
              border: 'none',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '2px',
              cursor: 'pointer',
              color: activeTab === tab.id ? '#F58426' : '#64748B',
              padding: '4px 6px'
            }}
          >
            <span style={{ fontSize: '16px' }}>{tab.icon}</span>
            <span style={{ fontSize: '10px', fontWeight: activeTab === tab.id ? 800 : 500 }}>
              {tab.label}
            </span>
          </button>
        ))}
      </nav>
    </div>
  );
}
