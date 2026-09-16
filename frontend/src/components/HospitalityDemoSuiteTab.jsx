import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import UnrealPixelStreamBridge from './UnrealPixelStreamBridge';

export default function HospitalityDemoSuiteTab({ backendUrl }) {
  const baseUrl = backendUrl || import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

  // --- View State ---
  const [activeNotoTab, setActiveNotoTab] = useState('overview');

  // --- Base Demo State ---
  const [isForaging, setIsForaging] = useState(false);
  const [forageLogs, setForageLogs] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('aibs_hospitality_forage_logs') || '[]');
    } catch { return []; }
  });
  
  const [chatHistory, setChatHistory] = useState(() => {
    try {
      const stored = localStorage.getItem('aibs_hospitality_booking_chat');
      if (stored) {
        let parsed = JSON.parse(stored);
        if (parsed.length > 0 && parsed[0].text.includes("Smith & Sons")) {
          parsed[0].text = "Thank you for contacting Noto's! How can we help you today?";
          localStorage.setItem('aibs_hospitality_booking_chat', JSON.stringify(parsed));
        }
        return parsed;
      }
      return [{ role: 'agent', text: "Thank you for contacting Noto's! How can we help you today?" }];
    } catch {
      return [{ role: 'agent', text: "Thank you for contacting Noto's! How can we help you today?" }];
    }
  });
  const [rawHistoryStr, setRawHistoryStr] = useState("Agent: Thank you for contacting Noto's! How can we help you today?\\n");
  const [chatInput, setChatInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isBooked, setIsBooked] = useState(false);
  const [ghostStatus, setGhostStatus] = useState('Idle');

  // --- Noto Apps State ---
  const [etiquetteChat, setEtiquetteChat] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('aibs_hospitality_etiquette_chat') || '[]');
    } catch { return []; }
  });
  const [etiquetteInput, setEtiquetteInput] = useState('');
  const [bocceResult, setBocceResult] = useState('');
  const [cellarWines, setCellarWines] = useState([]);
  const [plateData, setPlateData] = useState([]);
  const [scheduleData, setScheduleData] = useState([]);
  const [chatChannels, setChatChannels] = useState([]);
  const [chatDepartments, setChatDepartments] = useState(() => {
    try {
      const stored = localStorage.getItem('aibs_hospitality_employee_departments');
      if (stored) return JSON.parse(stored);
    } catch {}
    return [];
  });
  const [activeChannelId, setActiveChannelId] = useState('urgent-86');
  const [employeeMessageInput, setEmployeeMessageInput] = useState('');
  const [selectedSenderRole, setSelectedSenderRole] = useState('Tony Noto (Director)');
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [suggestionInput, setSuggestionInput] = useState('');
  const [suggestionName, setSuggestionName] = useState('');
  const [suggestionResult, setSuggestionResult] = useState(null);
  const [nfcResult, setNfcResult] = useState(null);

  const logsEndRef = useRef(null);
  const chatEndRef = useRef(null);
  const employeeChatEndRef = useRef(null);

  // Auto-save local state
  useEffect(() => {
    try { localStorage.setItem('aibs_hospitality_etiquette_chat', JSON.stringify(etiquetteChat)); } catch {}
  }, [etiquetteChat]);

  useEffect(() => {
    try { localStorage.setItem('aibs_hospitality_booking_chat', JSON.stringify(chatHistory)); } catch {}
  }, [chatHistory]);

  useEffect(() => {
    try { localStorage.setItem('aibs_hospitality_forage_logs', JSON.stringify(forageLogs)); } catch {}
  }, [forageLogs]);

  useEffect(() => { if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth' }); }, [forageLogs]);
  useEffect(() => { if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory]);

  // --- Actions ---
  const startLeadForaging = () => {
    setIsForaging(true);
    setForageLogs([]);
    const eventSource = new EventSource(`${baseUrl}/api/v1/demos/lead-forager/stream`);
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') { eventSource.close(); setIsForaging(false); return; }
      try { setForageLogs(prev => [...prev, JSON.parse(event.data)]); } catch(e) {}
    };
    eventSource.onerror = (err) => { eventSource.close(); setIsForaging(false); };
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || isTyping) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    setChatHistory(prev => [...prev, { role: 'user', text: userMsg }]);
    setIsTyping(true);
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/booking/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, history: rawHistoryStr })
      });
      const data = await res.json();
      setChatHistory(prev => [...prev, { role: 'agent', text: data.response }]);
      setRawHistoryStr(data.history);
      if (data.is_confirmed) setIsBooked(true);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: 'agent', text: 'Connection Error' }]);
    } finally { setIsTyping(false); }
  };

  const launchGhost = async () => {
    setGhostStatus('Launching...');
    try {
      await fetch(`${baseUrl}/api/v1/demos/ghost/launch`, { method: 'POST' });
      setGhostStatus('Automation Active (Check Host Display)');
      setTimeout(() => setGhostStatus('Idle'), 5000);
    } catch(e) { setGhostStatus('Failed to launch'); }
  };

  const runEtiquette = async () => {
    if (!etiquetteInput.trim()) return;
    const msg = etiquetteInput;
    setEtiquetteInput('');
    setEtiquetteChat(prev => [...prev, { role: 'user', text: msg }]);
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/etiquette`, { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message: msg})});
      const data = await res.json();
      setEtiquetteChat(prev => [...prev, { role: 'agent', text: data.reply }]);
    } catch(e) {}
  };

  const runBocce = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/bocce-upsell`, { method: 'POST' });
      const data = await res.json();
      setBocceResult(data.message);
    } catch(e) {}
  };

  const runCellar = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/cellar-master`, { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
      const data = await res.json();
      setCellarWines(data.recommendations);
    } catch(e) {}
  };

  const runPlate = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/plate-scraping`);
      const data = await res.json();
      setPlateData(data.data);
    } catch(e) {}
  };

  const runSchedule = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/scheduling`);
      const data = await res.json();
      setScheduleData(data.shifts);
    } catch(e) {}
  };

  const runChat = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/employee-chat`);
      const data = await res.json();
      if (data.departments) {
        setChatDepartments(data.departments);
        localStorage.setItem('aibs_hospitality_employee_departments', JSON.stringify(data.departments));
      } else if (data.channels) {
        setChatChannels(data.channels);
      }
    } catch(e) {}
  };

  // Auto-load position chat channels if not loaded
  useEffect(() => {
    if (chatDepartments.length === 0) {
      runChat();
    }
  }, []);

  useEffect(() => {
    if (employeeChatEndRef.current) {
      employeeChatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatDepartments, activeChannelId]);

  const handleSendEmployeeMessage = () => {
    if (!employeeMessageInput.trim()) return;
    const parts = selectedSenderRole.split(' (');
    const senderName = parts[0] ? parts[0].trim() : 'Staff';
    const cleanRole = parts[1] ? parts[1].replace(')', '').trim() : 'Team Member';
    
    const newMsg = {
      sender: senderName,
      role: cleanRole,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: employeeMessageInput.trim()
    };

    setChatDepartments(prev => {
      const updated = prev.map(dept => ({
        ...dept,
        channels: dept.channels.map(ch => {
          if (ch.id === activeChannelId) {
            return {
              ...ch,
              messages: [...ch.messages, newMsg]
            };
          }
          return ch;
        })
      }));
      try { localStorage.setItem('aibs_hospitality_employee_departments', JSON.stringify(updated)); } catch {}
      return updated;
    });

    setEmployeeMessageInput('');
  };

  const handleBroadcast86 = () => {
    const item = prompt('Enter 86\'d Menu Item or Wine Vintage to broadcast:', 'Chilean Sea Bass');
    if (!item) return;

    const alertMsg = {
      sender: 'Tony Noto',
      role: 'Owner / Director',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      text: `🚨 86 ALERT: ${item} is officially 86'd across all floor POS screens and kitchen stations!`
    };

    setChatDepartments(prev => {
      const updated = prev.map(dept => ({
        ...dept,
        channels: dept.channels.map(ch => {
          if (ch.id === 'urgent-86' || ch.id === 'line-cooks' || ch.id === 'foh-servers') {
            return {
              ...ch,
              messages: [...ch.messages, alertMsg]
            };
          }
          return ch;
        })
      }));
      try { localStorage.setItem('aibs_hospitality_employee_departments', JSON.stringify(updated)); } catch {}
      return updated;
    });
  };

  const runCalendar = async () => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/master-calendar`);
      const data = await res.json();
      setCalendarEvents(data.events);
    } catch(e) {}
  };

  const runSuggestion = async () => {
    if(!suggestionInput.trim()) return;
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/anonymous-suggestion`, { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({suggestion: suggestionInput, name: suggestionName})});
      const data = await res.json();
      setSuggestionResult(data);
      setSuggestionInput('');
      setSuggestionName('');
    } catch(e) {}
  };

  const runNfc = async (lat, lng) => {
    try {
      const res = await fetch(`${baseUrl}/api/v1/demos/noto/nfc-timeclock`, { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({lat, lng})});
      const data = await res.json();
      setNfcResult(data);
    } catch(e) {}
  };

  const [isExportingDocx, setIsExportingDocx] = useState(false);

  const handleExportOperationsWordDoc = async () => {
    setIsExportingDocx(true);
    try {
      const markdownBrief = `# Noto's Old World Italian Dining & Banquets
## Executive Daily Operations & AI Intelligence Brief
*Locations: Grand Rapids & Grand Haven, MI*
*Generated: ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}*

---

### 1. Operations Overview
Noto's hospitality ecosystem combines 25 years of culinary tradition with automated intelligence across both locations.

### 2. Master Event Logistics & Private Dining
- **Grand Rapids Banquets:** Full ballroom capacity configured with automated 3D seat spacing.
- **Grand Haven Waterfront:** Bocce courts active with AI upsell prompts.
- **Synchronized Calendar Events:** ${calendarEvents.length > 0 ? calendarEvents.map(e => `\n  - **${e.title}** (${e.date}) — Location: ${e.location}`).join('') : 'Synced live across locations.'}

### 3. Food Waste & Dish Pit Telemetry
- **Plate Scraping Analysis:** Edge computer-vision monitoring plate returns.
- **Average Side Pasta Waste:** Down 18.4% through dynamic portion scaling.

### 4. Cellar Master Recommendations & Inventory
- **Barolo DOCG:** Prioritized vintage movement for reserve steaks and lamb.
- **Chianti Classico Riserva:** High-margin pairing recommendation for wood-fired entrees.
- **Sicilian Nero d'Avola:** House pairing selection.

### 5. Staffing & Geofenced Timeclock
- **NFC Geofence Security:** Active at both coordinates (Grand Rapids & Grand Haven).
- **Zero Time-Theft Guarantee:** GPS boundary enforcement active.

---
*Report compiled autonomously by AI-BS Enterprise Hospitality Suite.*
`;

      const res = await fetch(`${baseUrl}/api/documents/export_docx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: 'Notos_Hospitality_Operations_Brief',
          content: markdownBrief,
          title: "Noto's Italian Dining — Daily Operations Brief"
        })
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Notos_Hospitality_Operations_Brief.docx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        alert('Could not export Word document.');
      }
    } catch (e) {
      alert(`Export error: ${e.message}`);
    } finally {
      setIsExportingDocx(false);
    }
  };

  // --- Components ---

  const PitchDetail = ({ text }) => (
    <div style={{
      marginTop: '32px',
      padding: '24px',
      backgroundColor: 'rgba(120, 53, 15, 0.2)', // amber-900/20
      border: '1px solid rgba(217, 119, 6, 0.4)', // amber-600/40
      borderRadius: '12px',
      backdropFilter: 'blur(4px)'
    }}>
      <h4 style={{ color: '#f59e0b', fontFamily: 'serif', fontSize: '1.125rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span>💡</span> The Business Value
      </h4>
      <p style={{ color: 'rgba(254, 236, 177, 0.8)', lineHeight: '1.7', fontSize: '0.9rem' }}>{text}</p>
    </div>
  );

  const notoTabs = [
    { id: 'overview', label: 'Dashboard Overview', icon: '🍷' },
    { id: 'etiquette', label: 'AI Etiquette Simulator', icon: '🤵' },
    { id: 'bocce', label: 'Bocce-Vision Engine', icon: '🎥' },
    { id: 'cellar', label: 'Cellar Master AI', icon: '🍾' },
    { id: 'plate', label: 'Plate-Scraping Optimizer', icon: '🍽️' },
    { id: 'schedule', label: 'Intelligent Scheduling', icon: '📅' },
    { id: 'chat', label: 'Structured Team Chat', icon: '💬' },
    { id: 'calendar', label: 'Master Event Calendar', icon: '🗓️' },
    { id: 'suggestion', label: 'Anonymous Feedback', icon: '📫' },
    { id: 'nfc', label: 'Geofenced Timeclock', icon: '📍' },
  ];

  const coreTabs = [
    { id: 'lead-forager', label: 'Lead Machine', icon: '🕵️' },
    { id: 'booking-agent', label: 'Booking Agent', icon: '🤖' },
    { id: 'ghost', label: 'Ghost in the Machine', icon: '👻' },
  ];

  return (
    <div style={{ display: 'flex', width: '100%', minHeight: '85vh', backgroundColor: '#0a0203', color: '#e2e8f0', fontFamily: 'sans-serif' }}>
      
      {/* Sidebar - Explicitly using CSS block/flex models to prevent squishing */}
      <div style={{ 
        width: '320px', 
        minWidth: '320px', 
        flexShrink: 0, 
        backgroundColor: '#160507', 
        borderRight: '1px solid #4c0519', 
        display: 'flex', 
        flexDirection: 'column',
        boxShadow: '4px 0 20px rgba(0,0,0,0.5)'
      }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          
          {/* Noto Suite */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {notoTabs.map(tab => {
              const isActive = activeNotoTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveNotoTab(tab.id)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '16px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    border: isActive ? '1px solid rgba(217,119,6,0.5)' : '1px solid transparent',
                    backgroundColor: isActive ? 'rgba(159,18,57,0.4)' : 'transparent',
                    color: isActive ? '#f59e0b' : 'rgba(254,205,211,0.6)',
                    boxShadow: isActive ? 'inset 0 0 20px rgba(159,18,57,0.3)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    outline: 'none'
                  }}
                  onMouseOver={(e) => {
                    if (!isActive) { e.currentTarget.style.backgroundColor = 'rgba(159,18,57,0.2)'; e.currentTarget.style.color = '#ffe4e6'; }
                  }}
                  onMouseOut={(e) => {
                    if (!isActive) { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'rgba(254,205,211,0.6)'; }
                  }}
                >
                  <span style={{ fontSize: '1.25rem' }}>{tab.icon}</span>
                  <span style={{ fontFamily: 'serif', letterSpacing: '0.05em', fontSize: '0.95rem' }}>{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Core AI-BS Demos */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '16px' }}>
            <div style={{ padding: '0 16px', marginBottom: '8px', borderBottom: '1px solid rgba(159,18,57,0.3)', paddingBottom: '8px' }}>
              <h3 style={{ fontSize: '0.65rem', letterSpacing: '0.15em', color: 'rgba(217,119,6,0.6)', textTransform: 'uppercase', fontWeight: 'bold', margin: 0 }}>Core Enterprise Systems</h3>
            </div>
            {coreTabs.map(tab => {
              const isActive = activeNotoTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveNotoTab(tab.id)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    padding: '16px',
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    border: isActive ? '1px solid rgba(217,119,6,0.5)' : '1px solid transparent',
                    backgroundColor: isActive ? 'rgba(159,18,57,0.4)' : 'transparent',
                    color: isActive ? '#f59e0b' : 'rgba(254,205,211,0.6)',
                    boxShadow: isActive ? 'inset 0 0 20px rgba(159,18,57,0.3)' : 'none',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    outline: 'none'
                  }}
                  onMouseOver={(e) => {
                    if (!isActive) { e.currentTarget.style.backgroundColor = 'rgba(159,18,57,0.2)'; e.currentTarget.style.color = '#ffe4e6'; }
                  }}
                  onMouseOut={(e) => {
                    if (!isActive) { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'rgba(254,205,211,0.6)'; }
                  }}
                >
                  <span style={{ fontSize: '1.25rem' }}>{tab.icon}</span>
                  <span style={{ fontFamily: 'serif', letterSpacing: '0.05em', fontSize: '0.95rem' }}>{tab.label}</span>
                </button>
              )
            })}
          </div>

        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ 
        flex: 1, 
        position: 'relative', 
        display: 'flex',
        flexDirection: 'column',
        overflowY: 'auto'
      }}>
        {/* Background Image Overlay */}
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundImage: 'url(/notos_background.png)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          opacity: 0.2, // increased opacity slightly for premium feel
          zIndex: 0,
          pointerEvents: 'none',
          filter: 'contrast(1.2) brightness(0.7) sepia(0.3) hue-rotate(-15deg)' // warm italian grade
        }}></div>
        
        {/* Dark Vignette over background */}
        <div style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'radial-gradient(ellipse at center, rgba(10,2,3,0.3) 0%, rgba(10,2,3,0.9) 100%)',
          zIndex: 0,
          pointerEvents: 'none'
        }}></div>

        {/* Foreground Content Wrapper */}
        <div style={{ position: 'relative', zIndex: 1, padding: '48px', width: '100%', maxWidth: '1200px', margin: '0 auto' }}>
          
          {/* Card Wrapper for actual tool */}
          <div style={{
            backgroundColor: 'rgba(22, 5, 7, 0.85)',
            backdropFilter: 'blur(16px)',
            border: '1px solid rgba(159, 18, 57, 0.4)',
            borderRadius: '24px',
            padding: '40px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)'
          }}>

            {/* 0. Overview */}
            {activeNotoTab === 'overview' && (
              <div style={{ textAlign: 'center', padding: '40px 0' }}>
                <span style={{ fontSize: '4.5rem', display: 'block', marginBottom: '16px' }}>🍷</span>
                <h2 style={{ fontSize: '3rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '16px', lineHeight: 1.2 }}>Old World Tradition. <br/> New World Intelligence.</h2>
                <p style={{ fontSize: '1.15rem', color: 'rgba(254, 205, 211, 0.8)', lineHeight: '1.8', maxWidth: '700px', margin: '0 auto 36px auto' }}>
                  A unified command center bridging the Grand Rapids and Grand Haven locations. 
                  Replacing fragmented SaaS subscriptions with localized, intelligent operations.
                </p>

                <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', marginBottom: '40px' }}>
                  <button
                    onClick={handleExportOperationsWordDoc}
                    disabled={isExportingDocx}
                    style={{
                      backgroundColor: '#0d9488',
                      color: '#ffffff',
                      border: 'none',
                      padding: '14px 28px',
                      borderRadius: '12px',
                      fontSize: '1rem',
                      fontWeight: 'bold',
                      fontFamily: 'serif',
                      letterSpacing: '0.05em',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      boxShadow: '0 8px 24px rgba(13, 148, 136, 0.3)'
                    }}
                  >
                    {isExportingDocx ? '⏳ Generating Operations Brief...' : '📥 Export Daily Operations Brief (.docx)'}
                  </button>
                </div>

                {/* Quick Launch Cards Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px', textAlign: 'left' }}>
                  <div
                    onClick={() => setActiveNotoTab('etiquette')}
                    style={{ backgroundColor: 'rgba(76,5,25,0.4)', border: '1px solid rgba(159,18,57,0.5)', padding: '20px', borderRadius: '16px', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.borderColor = '#f59e0b'}
                    onMouseOut={e => e.currentTarget.style.borderColor = 'rgba(159,18,57,0.5)'}
                  >
                    <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>🤵</span>
                    <h4 style={{ color: '#f59e0b', fontFamily: 'serif', margin: '0 0 4px 0' }}>AI Etiquette Sim</h4>
                    <p style={{ color: 'rgba(254,205,211,0.6)', fontSize: '0.8rem', margin: 0 }}>Train staff with Tony's 25-yr hospitality curriculum.</p>
                  </div>

                  <div
                    onClick={() => setActiveNotoTab('cellar')}
                    style={{ backgroundColor: 'rgba(76,5,25,0.4)', border: '1px solid rgba(159,18,57,0.5)', padding: '20px', borderRadius: '16px', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.borderColor = '#f59e0b'}
                    onMouseOut={e => e.currentTarget.style.borderColor = 'rgba(159,18,57,0.5)'}
                  >
                    <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>🍾</span>
                    <h4 style={{ color: '#f59e0b', fontFamily: 'serif', margin: '0 0 4px 0' }}>Cellar Master AI</h4>
                    <p style={{ color: 'rgba(254,205,211,0.6)', fontSize: '0.8rem', margin: 0 }}>Psychological wine quizzes & high-margin inventory routing.</p>
                  </div>

                  <div
                    onClick={() => setActiveNotoTab('plate')}
                    style={{ backgroundColor: 'rgba(76,5,25,0.4)', border: '1px solid rgba(159,18,57,0.5)', padding: '20px', borderRadius: '16px', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.borderColor = '#f59e0b'}
                    onMouseOut={e => e.currentTarget.style.borderColor = 'rgba(159,18,57,0.5)'}
                  >
                    <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>🍽️</span>
                    <h4 style={{ color: '#f59e0b', fontFamily: 'serif', margin: '0 0 4px 0' }}>Plate-Scraping Waste</h4>
                    <p style={{ color: 'rgba(254,205,211,0.6)', fontSize: '0.8rem', margin: 0 }}>Edge computer vision food waste telemetry.</p>
                  </div>

                  <div
                    onClick={() => setActiveNotoTab('calendar')}
                    style={{ backgroundColor: 'rgba(76,5,25,0.4)', border: '1px solid rgba(159,18,57,0.5)', padding: '20px', borderRadius: '16px', cursor: 'pointer', transition: 'all 0.2s' }}
                    onMouseOver={e => e.currentTarget.style.borderColor = '#f59e0b'}
                    onMouseOut={e => e.currentTarget.style.borderColor = 'rgba(159,18,57,0.5)'}
                  >
                    <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>🗓️</span>
                    <h4 style={{ color: '#f59e0b', fontFamily: 'serif', margin: '0 0 4px 0' }}>Master Calendar</h4>
                    <p style={{ color: 'rgba(254,205,211,0.6)', fontSize: '0.8rem', margin: 0 }}>Cross-location synchronization for private events.</p>
                  </div>
                </div>
              </div>
            )}

            {/* 1. Etiquette */}
            {activeNotoTab === 'etiquette' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>AI Etiquette Simulator</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Digital roleplay training based on Tony's 25-year curriculum.</p>
                
                <div style={{ height: '320px', backgroundColor: 'rgba(0,0,0,0.6)', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', padding: '24px', overflowY: 'auto', marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {etiquetteChat.map((m, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                      <div style={{ 
                        padding: '16px', 
                        borderRadius: '16px', 
                        maxWidth: '80%', 
                        fontSize: '0.9rem',
                        backgroundColor: m.role === 'user' ? 'rgba(120,53,15,0.4)' : 'rgba(76,5,25,0.6)',
                        border: m.role === 'user' ? '1px solid rgba(146,64,14,0.5)' : '1px solid rgba(159,18,57,0.5)',
                        color: m.role === 'user' ? '#fef3c7' : '#ffe4e6'
                      }}>
                        <strong>{m.role === 'user' ? 'Trainee: ' : 'VIP Guest: '}</strong>{m.text}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <input type="text" value={etiquetteInput} onChange={e => setEtiquetteInput(e.target.value)} placeholder="Apologize to the guest..." 
                    style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.6)', borderRadius: '12px', padding: '16px 24px', color: '#fef3c7', outline: 'none' }} 
                  />
                  <button onClick={runEtiquette} 
                    style={{ backgroundColor: '#b45309', color: 'white', padding: '16px 32px', borderRadius: '12px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', cursor: 'pointer', border: 'none' }}
                  >RESPOND</button>
                </div>
                
                <PitchDetail text="Tony spent 25 years teaching hospitality. This module scales his exact standards, testing new hires' empathy and menu knowledge in simulated high-stress scenarios before they ever touch the dining floor." />
              </div>
            )}

            {/* 2. Bocce */}
            {activeNotoTab === 'bocce' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Bocce-Vision Engine</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Computer vision referee and automated upselling.</p>
                
                <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', padding: '48px', textAlign: 'center', marginBottom: '24px' }}>
                  <button onClick={runBocce} 
                    style={{ backgroundColor: '#881337', color: '#ffe4e6', padding: '20px 40px', borderRadius: '16px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', fontSize: '1.125rem', border: '1px solid #be123c', cursor: 'pointer', boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}
                  >
                    SIMULATE HEATED MATCH
                  </button>
                  {bocceResult && (
                    <div style={{ marginTop: '32px', padding: '24px', backgroundColor: 'rgba(20,83,45,0.4)', border: '1px solid rgba(22,101,52,0.6)', borderRadius: '12px', color: '#4ade80', fontFamily: 'monospace', fontSize: '1.125rem' }}>
                      {bocceResult}
                    </div>
                  )}
                </div>

                <PitchDetail text="AI acts as a digital referee for the bocce courts, measuring millimeter distances. By tracking game intensity, it automatically dispatches SMS prompts to upsell drinks exactly when players are engaged." />
              </div>
            )}


            {/* 4. Cellar */}
            {activeNotoTab === 'cellar' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Cellar Master AI</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Psychological flavor profiling and dynamic inventory routing.</p>
                
                <button onClick={runCellar} 
                  style={{ width: '100%', backgroundColor: '#881337', color: '#ffe4e6', padding: '20px', borderRadius: '16px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', fontSize: '1.125rem', border: '1px solid #be123c', cursor: 'pointer', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', marginBottom: '32px' }}
                >
                  SIMULATE GUEST QR QUIZ
                </button>

                {cellarWines.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {cellarWines.map((w, i) => (
                      <div key={i} style={{ padding: '24px', backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <h4 style={{ color: '#f59e0b', fontFamily: 'serif', fontSize: '1.25rem', margin: '0 0 4px 0' }}>{w.name}</h4>
                          <p style={{ color: 'rgba(254,205,211,0.7)', fontSize: '0.875rem', margin: 0 }}>{w.reason}</p>
                        </div>
                        <div style={{ fontSize: '1.5rem', fontFamily: 'serif', color: '#b45309', fontWeight: 'bold' }}>${w.price}</div>
                      </div>
                    ))}
                  </div>
                )}

                <PitchDetail text="A massive wine list intimidates 95% of guests. The Cellar Master uses a psychological QR quiz to confidently recommend 3 price-tiered wines, while prioritizing specific vintages Tony needs to move from the cellar." />
              </div>
            )}

            {/* 5. Plate */}
            {activeNotoTab === 'plate' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Plate-Scraping Optimizer</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Edge-compute computer vision for food waste telemetry.</p>
                
                <button onClick={runPlate} 
                  style={{ width: '100%', backgroundColor: 'rgba(120,53,15,0.6)', color: '#f59e0b', padding: '20px', borderRadius: '16px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', fontSize: '1.125rem', border: '1px solid #b45309', cursor: 'pointer', marginBottom: '32px' }}
                >
                  FETCH DISHWASHING TELEMETRY
                </button>

                {plateData.length > 0 && (
                  <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', padding: '32px', height: '320px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={plateData} margin={{top: 20, right: 30, left: 0, bottom: 0}}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#4c0519" />
                        <XAxis dataKey="name" stroke="#be123c" />
                        <YAxis stroke="#be123c" />
                        <Tooltip contentStyle={{backgroundColor: '#160507', borderColor: '#881337', color: '#fcd34d'}} />
                        <Line type="monotone" dataKey="waste_percent" stroke="#f59e0b" strokeWidth={4} dot={{r: 6, fill: '#f59e0b'}} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <PitchDetail text="An invisible, edge-compute camera mounted over the dish pit uses YOLO segmentation to analyze returned plates. It aggregates the data so the Executive Chef can dynamically shrink portion sizes of wasted ingredients (like side pasta), saving thousands without guests noticing." />
              </div>
            )}

            {/* 6. Schedule */}
            {activeNotoTab === 'schedule' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Intelligent Scheduling</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Predictive labor modeling based on historical volume.</p>
                
                <button onClick={runSchedule} 
                  style={{ width: '100%', backgroundColor: '#881337', color: '#ffe4e6', padding: '20px', borderRadius: '16px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', fontSize: '1.125rem', border: '1px solid #be123c', cursor: 'pointer', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', marginBottom: '32px' }}
                >
                  ANALYZE WEEKEND VOLUME
                </button>

                {scheduleData.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {scheduleData.map((s, i) => (
                      <div key={i} style={{ padding: '24px', backgroundColor: 'rgba(0,0,0,0.5)', border: s.ai_flag ? '1px solid rgba(217,119,6,0.6)' : '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <h4 style={{ color: '#ffe4e6', fontWeight: 'bold', fontSize: '1.125rem', margin: '0 0 4px 0' }}>{s.employee} <span style={{ fontSize: '0.875rem', fontWeight: 'normal', color: '#fb7185' }}>| {s.role} - {s.location}</span></h4>
                          <p style={{ color: 'rgba(254,205,211,0.7)', fontSize: '0.875rem', fontFamily: 'monospace', margin: 0 }}>{s.time}</p>
                        </div>
                        {s.ai_flag && (
                          <div style={{ backgroundColor: 'rgba(120,53,15,0.4)', color: '#fbbf24', padding: '8px 16px', borderRadius: '4px', border: '1px solid rgba(180,83,9,0.6)', fontSize: '0.875rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span>⚠️</span> AI FLAG: {s.ai_flag}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                <PitchDetail text="Predictive labor staffing replaces guesswork. The AI flags shifts that will be understaffed based on local event data, weather, and historical banquet volume, eliminating overtime panic and burnout." />
              </div>
            )}

            {/* 7. Chat Organized by Positions */}
            {activeNotoTab === 'chat' && (() => {
              const activeChannel = chatDepartments
                .flatMap(d => d.channels || [])
                .find(c => c.id === activeChannelId) || chatDepartments[0]?.channels?.[0];

              const getRoleIcon = (role = '') => {
                if (role.includes('Chef')) return '👨‍🍳';
                if (role.includes('Director') || role.includes('Owner')) return '👔';
                if (role.includes('GM') || role.includes('Manager')) return '📋';
                if (role.includes('Sommelier') || role.includes('Wine')) return '🍷';
                if (role.includes('Bartender') || role.includes('Server')) return '🤵';
                if (role.includes('Host')) return '🛎️';
                if (role.includes('Banquet')) return '🏛️';
                if (role.includes('Steward') || role.includes('Dish')) return '🧼';
                return '👤';
              };

              return (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
                    <div>
                      <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', margin: '0 0 6px 0' }}>
                        Employee Chat by Position & Department
                      </h3>
                      <p style={{ color: 'rgba(254, 205, 211, 0.7)', margin: 0, fontSize: '0.9rem' }}>
                        Role-isolated communication eliminating group-text clutter, noise fatigue, and off-clock disturbance.
                      </p>
                    </div>

                    <div style={{ display: 'flex', gap: '10px' }}>
                      <button
                        onClick={handleBroadcast86}
                        style={{
                          backgroundColor: '#e11d48',
                          color: '#ffffff',
                          border: 'none',
                          padding: '10px 18px',
                          borderRadius: '10px',
                          fontWeight: '700',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          boxShadow: '0 4px 14px rgba(225, 29, 72, 0.4)'
                        }}
                      >
                        🚨 Broadcast 86'd Item
                      </button>
                      <button
                        onClick={runChat}
                        style={{
                          backgroundColor: 'rgba(159, 18, 57, 0.4)',
                          color: '#fda4af',
                          border: '1px solid rgba(159, 18, 57, 0.6)',
                          padding: '10px 16px',
                          borderRadius: '10px',
                          fontWeight: '700',
                          fontSize: '0.85rem',
                          cursor: 'pointer'
                        }}
                      >
                        🔄 Reset Demo Channels
                      </button>
                    </div>
                  </div>

                  {/* Main Position-Organized Chat Hub */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '320px 1fr',
                    gap: '20px',
                    height: '620px',
                    backgroundColor: 'rgba(10, 2, 4, 0.85)',
                    border: '1px solid rgba(159, 18, 57, 0.5)',
                    borderRadius: '20px',
                    overflow: 'hidden',
                    boxShadow: '0 20px 50px rgba(0,0,0,0.7)'
                  }}>
                    {/* Left Column: Department & Position Channels */}
                    <div style={{
                      backgroundColor: 'rgba(20, 4, 8, 0.95)',
                      borderRight: '1px solid rgba(159, 18, 57, 0.4)',
                      padding: '20px 14px',
                      overflowY: 'auto',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '18px'
                    }}>
                      <div style={{ padding: '0 8px', fontSize: '0.75rem', fontWeight: '800', letterSpacing: '0.1em', color: '#f59e0b', textTransform: 'uppercase' }}>
                        POSITION CHANNELS
                      </div>

                      {chatDepartments.map((dept, dIdx) => (
                        <div key={dIdx} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            padding: '6px 8px',
                            color: '#fda4af',
                            fontWeight: '700',
                            fontSize: '0.82rem'
                          }}>
                            <span>{dept.icon}</span>
                            <span>{dept.department}</span>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                            {dept.channels.map(ch => {
                              const isActive = ch.id === activeChannelId;
                              return (
                                <button
                                  key={ch.id}
                                  onClick={() => setActiveChannelId(ch.id)}
                                  style={{
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'flex-start',
                                    width: '100%',
                                    padding: '10px 12px',
                                    borderRadius: '10px',
                                    border: isActive ? '1px solid #f59e0b' : '1px solid transparent',
                                    backgroundColor: isActive ? 'rgba(217, 119, 6, 0.2)' : 'transparent',
                                    color: isActive ? '#ffffff' : '#fda4af',
                                    cursor: 'pointer',
                                    textAlign: 'left',
                                    transition: 'all 0.15s'
                                  }}
                                  onMouseOver={e => { if (!isActive) e.currentTarget.style.backgroundColor = 'rgba(159, 18, 57, 0.2)'; }}
                                  onMouseOut={e => { if (!isActive) e.currentTarget.style.backgroundColor = 'transparent'; }}
                                >
                                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                                    <span style={{ fontWeight: isActive ? '800' : '600', fontSize: '0.88rem' }}>
                                      # {ch.name}
                                    </span>
                                    {ch.unread > 0 && !isActive && (
                                      <span style={{
                                        backgroundColor: '#e11d48',
                                        color: '#ffffff',
                                        fontSize: '0.68rem',
                                        fontWeight: '800',
                                        padding: '2px 6px',
                                        borderRadius: '10px'
                                      }}>
                                        {ch.unread}
                                      </span>
                                    )}
                                  </div>
                                  <span style={{ fontSize: '0.72rem', color: isActive ? '#fef3c7' : 'rgba(254, 205, 211, 0.5)', marginTop: '2px' }}>
                                    👥 {ch.position}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Right Column: Active Channel Chat Stream */}
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      height: '100%',
                      backgroundColor: 'rgba(5, 1, 2, 0.9)'
                    }}>
                      {/* Channel Header */}
                      <div style={{
                        padding: '16px 24px',
                        backgroundColor: 'rgba(20, 4, 8, 0.95)',
                        borderBottom: '1px solid rgba(159, 18, 57, 0.4)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: '#f59e0b', fontSize: '1.2rem', fontWeight: 'bold' }}>#</span>
                            <h4 style={{ margin: 0, color: '#ffffff', fontSize: '1.1rem', fontFamily: 'serif' }}>
                              {activeChannel?.name}
                            </h4>
                          </div>
                          <p style={{ margin: '2px 0 0 0', fontSize: '0.75rem', color: '#fda4af' }}>
                            Assigned Positions: <strong>{activeChannel?.position}</strong>
                          </p>
                        </div>

                        <div style={{ fontSize: '0.78rem', color: 'rgba(254, 205, 211, 0.6)', backgroundColor: 'rgba(159, 18, 57, 0.2)', padding: '4px 10px', borderRadius: '8px', border: '1px solid rgba(159, 18, 57, 0.4)' }}>
                          🔒 Role-Gated Stream
                        </div>
                      </div>

                      {/* Messages Stream */}
                      <div style={{
                        flex: 1,
                        padding: '24px',
                        overflowY: 'auto',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '16px'
                      }}>
                        {activeChannel?.messages?.map((msg, mIdx) => {
                          const isManagementAlert = msg.text.includes('🚨') || msg.role.includes('Director') || msg.role.includes('Executive Chef');
                          return (
                            <div
                              key={mIdx}
                              style={{
                                display: 'flex',
                                gap: '14px',
                                padding: '14px 18px',
                                borderRadius: '14px',
                                backgroundColor: isManagementAlert ? 'rgba(159, 18, 57, 0.25)' : 'rgba(255, 255, 255, 0.03)',
                                border: isManagementAlert ? '1px solid rgba(225, 29, 72, 0.4)' : '1px solid rgba(255, 255, 255, 0.05)'
                              }}
                            >
                              <div style={{
                                width: '38px',
                                height: '38px',
                                borderRadius: '50%',
                                backgroundColor: 'rgba(217, 119, 6, 0.2)',
                                border: '1px solid rgba(217, 119, 6, 0.4)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '1.2rem',
                                flexShrink: 0
                              }}>
                                {getRoleIcon(msg.role)}
                              </div>

                              <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                  <span style={{ fontWeight: '700', color: '#ffffff', fontSize: '0.9rem' }}>
                                    {msg.sender}
                                  </span>
                                  <span style={{
                                    backgroundColor: 'rgba(217, 119, 6, 0.2)',
                                    color: '#f59e0b',
                                    border: '1px solid rgba(217, 119, 6, 0.4)',
                                    padding: '1px 8px',
                                    borderRadius: '10px',
                                    fontSize: '0.68rem',
                                    fontWeight: '700'
                                  }}>
                                    {msg.role}
                                  </span>
                                  <span style={{ fontSize: '0.72rem', color: 'rgba(254, 205, 211, 0.5)', marginLeft: 'auto' }}>
                                    {msg.time}
                                  </span>
                                </div>

                                <div style={{ color: '#ffe4e6', fontSize: '0.88rem', lineHeight: '1.5' }}>
                                  {msg.text}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                        <div ref={employeeChatEndRef} />
                      </div>

                      {/* Compose Input Toolbar */}
                      <div style={{
                        padding: '16px 24px',
                        backgroundColor: 'rgba(20, 4, 8, 0.95)',
                        borderTop: '1px solid rgba(159, 18, 57, 0.4)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#fda4af', fontWeight: '700' }}>Post as:</span>
                          <select
                            value={selectedSenderRole}
                            onChange={e => setSelectedSenderRole(e.target.value)}
                            style={{
                              backgroundColor: '#1c070b',
                              border: '1px solid rgba(159, 18, 57, 0.6)',
                              color: '#fef3c7',
                              padding: '4px 10px',
                              borderRadius: '6px',
                              fontSize: '0.78rem',
                              outline: 'none',
                              cursor: 'pointer'
                            }}
                          >
                            <option value="Tony Noto (Director)">👔 Tony Noto (Director / Owner)</option>
                            <option value="Chef Marco (Executive Chef)">👨‍🍳 Chef Marco (Executive Chef)</option>
                            <option value="Sarah M. (Night GM)">📋 Sarah M. (Night GM)</option>
                            <option value="Matteo V. (Lead Sommelier)">🍷 Matteo V. (Lead Sommelier)</option>
                            <option value="Anna K. (Lead Server)">🤵 Anna K. (Lead Server)</option>
                            <option value="Elena R. (Hostess Lead)">🛎️ Elena R. (Hostess Lead)</option>
                            <option value="Rachel H. (Banquet Captain)">🏛️ Rachel H. (Banquet Captain)</option>
                            <option value="Carlos T. (Steward Lead)">🧼 Carlos T. (Steward Lead)</option>
                          </select>
                        </div>

                        <div style={{ display: 'flex', gap: '10px' }}>
                          <input
                            type="text"
                            value={employeeMessageInput}
                            onChange={e => setEmployeeMessageInput(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') handleSendEmployeeMessage(); }}
                            placeholder={`Message #${activeChannel?.name || 'channel'} as ${selectedSenderRole.split(' (')[0]}...`}
                            style={{
                              flex: 1,
                              backgroundColor: 'rgba(0, 0, 0, 0.6)',
                              border: '1px solid rgba(159, 18, 57, 0.6)',
                              borderRadius: '10px',
                              padding: '12px 18px',
                              color: '#fef3c7',
                              fontSize: '0.88rem',
                              outline: 'none'
                            }}
                          />
                          <button
                            onClick={handleSendEmployeeMessage}
                            style={{
                              backgroundColor: '#b45309',
                              color: '#ffffff',
                              border: 'none',
                              padding: '12px 24px',
                              borderRadius: '10px',
                              fontWeight: '700',
                              fontSize: '0.88rem',
                              cursor: 'pointer'
                            }}
                          >
                            ➤ Send
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>

                  <PitchDetail text="Replaces chaotic, fragmented group texts with role-isolated position channels. Kitchen chefs, floor sommeliers, banquets, and host staff communicate in designated silos, ensuring urgent 86'd items are broadcasted instantly without spamming off-clock staff." />
                </div>
              );
            })()}

            {/* 8. Calendar */}
            {activeNotoTab === 'calendar' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Master Event Calendar</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>A single pane of glass for all cross-location logistics.</p>
                
                <button onClick={runCalendar} 
                  style={{ width: '100%', backgroundColor: '#881337', color: '#ffe4e6', padding: '20px', borderRadius: '16px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', fontSize: '1.125rem', border: '1px solid #be123c', cursor: 'pointer', boxShadow: '0 10px 25px rgba(0,0,0,0.5)', marginBottom: '32px' }}
                >
                  SYNC GRAND RAPIDS & GRAND HAVEN
                </button>

                {calendarEvents.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {calendarEvents.map((e, i) => (
                      <div key={i} style={{ padding: '24px', backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.5)', borderLeft: '4px solid #d97706', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div>
                          <h4 style={{ color: '#ffe4e6', fontWeight: 'bold', fontSize: '1.25rem', margin: '0 0 4px 0' }}>{e.title}</h4>
                          <p style={{ color: '#f59e0b', fontSize: '0.875rem', fontFamily: 'monospace', textTransform: 'uppercase', letterSpacing: '0.1em', margin: 0 }}>{e.date}</p>
                        </div>
                        <div style={{ fontSize: '1.5rem', backgroundColor: 'rgba(76,5,25,0.6)', padding: '16px 24px', borderRadius: '12px', border: '1px solid rgba(159,18,57,0.6)', fontFamily: 'serif', color: '#fecdd3' }}>
                          {e.location}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <PitchDetail text="A single source of truth for Tony's entire empire. Every private event, live music booking, and massive inventory delivery is perfectly synchronized across the Grand Rapids and Grand Haven locations." />
              </div>
            )}

            {/* 9. Suggestion */}
            {activeNotoTab === 'suggestion' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Anonymous Suggestion Box</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Safe, AI-categorized operational feedback routing.</p>
                
                <div style={{ backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.5)', borderRadius: '16px', padding: '32px', marginBottom: '24px' }}>
                  <input type="text" value={suggestionName} onChange={e => setSuggestionName(e.target.value)} placeholder="Name (Leave blank for Anonymous)" 
                    style={{ width: '100%', backgroundColor: 'rgba(76,5,25,0.3)', border: '1px solid rgba(159,18,57,0.6)', borderRadius: '12px', padding: '16px 24px', color: '#fef3c7', outline: 'none', marginBottom: '16px', boxSizing: 'border-box' }} 
                  />
                  <textarea value={suggestionInput} onChange={e => setSuggestionInput(e.target.value)} placeholder="Operational friction report..." 
                    style={{ width: '100%', height: '128px', backgroundColor: 'rgba(76,5,25,0.3)', border: '1px solid rgba(159,18,57,0.6)', borderRadius: '12px', padding: '16px 24px', color: '#fef3c7', outline: 'none', marginBottom: '24px', boxSizing: 'border-box', resize: 'vertical' }} 
                  />
                  
                  <button onClick={runSuggestion} 
                    style={{ width: '100%', backgroundColor: '#b45309', color: 'white', padding: '16px', borderRadius: '12px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', cursor: 'pointer', border: 'none' }}
                  >SUBMIT SECURELY TO MANAGEMENT</button>
                </div>

                {suggestionResult && (
                  <div style={{ padding: '24px', backgroundColor: 'rgba(20,83,45,0.4)', border: '1px solid rgba(22,101,52,0.6)', borderRadius: '12px' }}>
                    <div style={{ color: '#4ade80', fontWeight: 'bold', fontSize: '1.125rem', marginBottom: '8px' }}>{suggestionResult.message}</div>
                    <div style={{ color: 'rgba(187,247,208,0.7)', fontFamily: 'monospace', fontSize: '0.875rem' }}>{suggestionResult.ai_analysis}</div>
                  </div>
                )}

                <PitchDetail text="Improves staff retention and kills toxic culture by allowing dishwashers and servers to report friction points without fear of retaliation. The AI automatically categorizes and prioritizes the feedback for management." />
              </div>
            )}

            {/* 10. NFC */}
            {activeNotoTab === 'nfc' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Geofenced NFC Timeclock</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.6)', marginBottom: '32px' }}>Bring-Your-Own-Device punch system secured by GPS.</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', marginBottom: '32px' }}>
                  <button onClick={() => runNfc(42.92, -85.50)} 
                    style={{ backgroundColor: 'rgba(6,78,59,0.5)', color: '#34d399', border: '1px solid rgba(6,95,70,0.8)', padding: '32px', borderRadius: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', cursor: 'pointer' }}
                  >
                    <span style={{ fontSize: '3rem' }}>✅</span>
                    <span style={{ fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em' }}>TAP INSIDE GEOFENCE</span>
                  </button>
                  <button onClick={() => runNfc(39.92, -85.50)} 
                    style={{ backgroundColor: 'rgba(127,29,29,0.5)', color: '#f87171', border: '1px solid rgba(153,27,27,0.8)', padding: '32px', borderRadius: '16px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', cursor: 'pointer' }}
                  >
                    <span style={{ fontSize: '3rem' }}>🚫</span>
                    <span style={{ fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em' }}>TAP OUTSIDE GEOFENCE</span>
                  </button>
                </div>

                {nfcResult && (
                  <div style={{ padding: '24px', borderRadius: '12px', border: '1px solid', textAlign: 'center', fontFamily: 'monospace', fontSize: '1.125rem', backgroundColor: nfcResult.status === 'success' ? 'rgba(6,78,59,0.3)' : 'rgba(127,29,29,0.3)', borderColor: nfcResult.status === 'success' ? 'rgba(6,95,70,0.6)' : 'rgba(153,27,27,0.6)', color: nfcResult.status === 'success' ? '#34d399' : '#f87171' }}>
                    {nfcResult.message}
                  </div>
                )}

                <PitchDetail text="Eliminates the 4:00 PM shift-change bottleneck at the POS. Employees tap their own phones via NFC, but the strict GPS geofence prevents 'buddy-punching' and time theft from the parking lot. Massive hardware savings." />
              </div>
            )}

            {/* --- CORE AI-BS DEMOS --- */}

            {activeNotoTab === 'lead-forager' && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '32px' }}>
                  <div>
                    <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', margin: '0 0 8px 0' }}>Autonomous Lead Machine</h3>
                    <p style={{ color: 'rgba(254, 205, 211, 0.5)', margin: 0 }}>Core AI-BS Enterprise Module</p>
                  </div>
                  <button onClick={startLeadForaging} disabled={isForaging} 
                    style={{ padding: '16px 32px', borderRadius: '12px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', transition: 'all 0.2s', cursor: isForaging ? 'not-allowed' : 'pointer', border: 'none', backgroundColor: isForaging ? 'rgba(76,5,25,0.8)' : '#b45309', color: isForaging ? '#fb7185' : 'white' }}
                  >
                    {isForaging ? 'FORAGING...' : 'START FORAGING'}
                  </button>
                </div>
                <div style={{ height: '384px', backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.6)', borderRadius: '16px', padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                  {forageLogs.map((log, idx) => (
                    log.type === 'status' 
                      ? <div key={idx} style={{ color: '#f59e0b' }}>{'>'} {log.message}</div>
                      : <div key={idx} style={{ backgroundColor: 'rgba(120,53,15,0.3)', borderLeft: '2px solid #d97706', padding: '12px', color: '#fecdd3' }}>
                          {log.data.lead} ({log.data.industry})
                        </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              </div>
            )}

            {activeNotoTab === 'booking-agent' && (
              <div>
                <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', marginBottom: '8px' }}>Autonomous Booking Agent</h3>
                <p style={{ color: 'rgba(254, 205, 211, 0.5)', marginBottom: '32px' }}>Core AI-BS Enterprise Module</p>
                
                <div style={{ height: '320px', backgroundColor: 'rgba(0,0,0,0.5)', border: '1px solid rgba(159,18,57,0.6)', borderRadius: '16px', padding: '24px', overflowY: 'auto', marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {chatHistory.map((msg, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                      <div style={{ 
                        maxWidth: '80%', padding: '16px', borderRadius: '16px', fontSize: '0.875rem',
                        backgroundColor: msg.role === 'user' ? 'rgba(120,53,15,0.5)' : 'rgba(76,5,25,0.6)',
                        border: msg.role === 'user' ? '1px solid rgba(146,64,14,0.6)' : '1px solid rgba(159,18,57,0.6)',
                        color: msg.role === 'user' ? '#fef3c7' : '#ffe4e6'
                      }}>
                        {msg.text.replace('[SYSTEM: BOOKING CONFIRMED]', '')}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                <div style={{ display: 'flex', gap: '16px' }}>
                  <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && sendChatMessage()} 
                    style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', border: '1px solid rgba(159,18,57,0.7)', borderRadius: '12px', padding: '16px 24px', color: '#fef3c7', outline: 'none' }} 
                  />
                  <button onClick={sendChatMessage} 
                    style={{ backgroundColor: '#b45309', color: 'white', padding: '16px 32px', borderRadius: '12px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', cursor: 'pointer', border: 'none' }}
                  >SEND</button>
                </div>
              </div>
            )}

            {activeNotoTab === 'ghost' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '2.25rem', fontFamily: 'serif', color: '#f59e0b', margin: '0 0 8px 0' }}>👻 Ghost in the Machine</h3>
                  <p style={{ color: 'rgba(254, 205, 211, 0.5)', margin: 0 }}>Autonomous Host Display Controller</p>
                </div>
                <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '1.125rem', color: ghostStatus.includes('Active') ? '#f59e0b' : '#9f1239' }}>{ghostStatus}</span>
                  <button onClick={launchGhost} 
                    style={{ backgroundColor: '#7f1d1d', color: '#fecdd3', padding: '16px 32px', borderRadius: '12px', fontWeight: 'bold', fontFamily: 'serif', letterSpacing: '0.1em', border: '1px solid #b91c1c', cursor: 'pointer', boxShadow: '0 10px 25px rgba(0,0,0,0.5)' }}
                  >
                    DEPLOY GHOST
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}
