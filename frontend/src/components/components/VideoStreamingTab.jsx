import React, { useEffect, useRef, useState } from 'react';
import { 
  Video, VideoOff, Mic, MicOff, Monitor, StopCircle, PhoneOff, 
  Calendar, Clock, Users, Plus, Mail, Copy, Check, MessageSquare, 
  Sparkles, ExternalLink, ShieldCheck, Share2, Circle
} from 'lucide-react';
import { useBackendHealth } from './useBackendHealth';
import { db } from '../firebase';
import { collection, onSnapshot, query, orderBy } from 'firebase/firestore';

const TEAM_MEMBERS = [
  { name: 'Brett Stehouwer', email: 'brett@StehouwerPublishing.com', role: 'Executive Founder / CEO' },
  { name: 'Sean Stehouwer', email: 'sean@StehouwerPublishing.com', role: 'Chief Strategy Officer' },
  { name: 'Julie Stehouwer', email: 'julie@StehouwerPublishing.com', role: 'Operations Director' }
];

export default function VideoStreamingTab() {
  const { backendUrl } = useBackendHealth();
  
  // Call State
  const [inCall, setInCall] = useState(false);
  const [roomCode, setRoomCode] = useState('');
  const [activeTitle, setActiveTitle] = useState('Executive Business Review');
  const [micMuted, setMicMuted] = useState(false);
  const [camMuted, setCamMuted] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  // WebRTC State
  const wsRef = useRef(null);
  const peersRef = useRef({});
  const [remoteStreams, setRemoteStreams] = useState({});
  const [isHost, setIsHost] = useState(false);

  // In-Meeting Chat
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');

  // Scheduled Meetings State
  const [scheduledMeetings, setScheduledMeetings] = useState([
    {
      id: 'meet-001',
      title: 'Stehouwer Publishing Q3 Executive Strategy',
      host: 'Brett Stehouwer (brett@StehouwerPublishing.com)',
      date: '2026-08-20',
      time: '02:00 PM',
      duration: '45 mins',
      roomCode: 'meet-928-401-382',
      invitees: ['brett@StehouwerPublishing.com', 'sean@StehouwerPublishing.com', 'julie@StehouwerPublishing.com'],
      agenda: 'Review Q3 revenue targets, OSINT LeadEngine deployment, and Cloudflare Email Worker integration.'
    }
  ]);

  // Schedule Modal Form State
  const [isScheduleOpen, setIsScheduleOpen] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formDate, setFormDate] = useState(new Date().toISOString().split('T')[0]);
  const [formTime, setFormTime] = useState('14:00');
  const [formDuration, setFormDuration] = useState('30 mins');
  const [formHost, setFormHost] = useState('brett@StehouwerPublishing.com');
  const [selectedInvitees, setSelectedInvitees] = useState([
    'brett@StehouwerPublishing.com',
    'sean@StehouwerPublishing.com',
    'julie@StehouwerPublishing.com'
  ]);
  const [customInvitee, setCustomInvitee] = useState('');
  const [formAgenda, setFormAgenda] = useState('');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleStatus, setScheduleStatus] = useState('');

  // Media Refs
  const localVideoRef = useRef(null);
  const localStreamRef = useRef(null);
  const screenStreamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);

  // Check URL query parameters for direct room joining
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const roomParam = params.get('room');
    if (roomParam) {
      setRoomCode(roomParam);
    }
  }, []);

  // Listen to scheduled meetings from Firestore
  useEffect(() => {
    try {
      const q = query(collection(db, 'scheduled_meetings'));
      const unsub = onSnapshot(q, (snapshot) => {
        const meets = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        if (meets.length > 0) {
          setScheduledMeetings(prev => {
            const combined = [...meets, ...prev.filter(p => !meets.some(m => m.id === p.id))];
            return combined;
          });
        }
      }, (err) => console.warn("Firestore scheduled_meetings fallback:", err));
      return () => unsub();
    } catch (err) {
      console.warn("Firestore meetings setup error:", err);
    }
  }, []);

  // Start Video Call
  const startCall = async (codeToUse, titleToUse) => {
    const isNewRoom = !codeToUse;
    const code = codeToUse || `meet-${Math.floor(100 + Math.random() * 900)}-${Math.floor(100 + Math.random() * 900)}-${Math.floor(100 + Math.random() * 900)}`;
    setRoomCode(code);
    setActiveTitle(titleToUse || (isNewRoom ? 'Executive Business Review' : 'Joined Business Meeting'));
    setInCall(true);
    setIsHost(isNewRoom);
    
    const myClientId = isNewRoom ? code : Math.random().toString(36).substring(7);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      localStreamRef.current = stream;
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }
      setChatMessages([
        { sender: 'System', text: `Welcome to Room ${code}. WebRTC Encrypted Stream Active.`, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
      ]);

      // Connect to WebRTC Signaling Server
      wsRef.current = new WebSocket(`ws://127.0.0.1:8006/ws/webrtc/${myClientId}`);
      
      wsRef.current.onmessage = async (event) => {
         const msg = JSON.parse(event.data);
         const { sender, type, payload } = msg;
         
         if (type === 'join' && isNewRoom) {
            const pc = createPeerConnection(sender, stream, myClientId);
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            wsRef.current.send(JSON.stringify({ target: sender, type: 'offer', payload: offer }));
         } 
         else if (type === 'offer') {
            const pc = createPeerConnection(sender, stream, myClientId);
            await pc.setRemoteDescription(new RTCSessionDescription(payload));
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            wsRef.current.send(JSON.stringify({ target: sender, type: 'answer', payload: answer }));
         }
         else if (type === 'answer') {
            const pc = peersRef.current[sender];
            if (pc) {
               await pc.setRemoteDescription(new RTCSessionDescription(payload));
            }
         }
         else if (type === 'ice-candidate') {
            const pc = peersRef.current[sender];
            if (pc && payload) {
               await pc.addIceCandidate(new RTCIceCandidate(payload));
            }
         }
      };

      wsRef.current.onopen = () => {
         if (!isNewRoom) {
            wsRef.current.send(JSON.stringify({ target: code, type: 'join', payload: {} }));
         }
      };
      
    } catch (err) {
      console.warn("Camera/Mic access warning:", err);
    }
  };

  const createPeerConnection = (peerId, localStream, myClientId) => {
     const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
     peersRef.current[peerId] = pc;
     
     localStream.getTracks().forEach(track => pc.addTrack(track, localStream));
     
     pc.onicecandidate = (event) => {
        if (event.candidate && wsRef.current) {
           wsRef.current.send(JSON.stringify({ target: peerId, type: 'ice-candidate', payload: event.candidate }));
        }
     };
     
     pc.ontrack = (event) => {
        setRemoteStreams(prev => ({ ...prev, [peerId]: event.streams[0] }));
     };
     
     pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed' || pc.connectionState === 'closed') {
           setRemoteStreams(prev => {
              const newState = { ...prev };
              delete newState[peerId];
              return newState;
           });
           delete peersRef.current[peerId];
        }
     };
     
     return pc;
  };

  // End Video Call
  const endCall = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (screenStreamRef.current) {
      screenStreamRef.current.getTracks().forEach(track => track.stop());
    }
    if (isRecording && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    Object.values(peersRef.current).forEach(pc => pc.close());
    peersRef.current = {};
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setRemoteStreams({});
    setInCall(false);
    setIsScreenSharing(false);
    setIsRecording(false);
  };

  // Toggle Mic
  const toggleMic = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getAudioTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setMicMuted(!micMuted);
    }
  };

  // Toggle Camera
  const toggleCam = () => {
    if (localStreamRef.current) {
      localStreamRef.current.getVideoTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setCamMuted(!camMuted);
    }
  };

  // Toggle Screen Sharing
  const toggleScreenShare = async () => {
    if (isScreenSharing) {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach(track => track.stop());
      }
      if (localVideoRef.current && localStreamRef.current) {
        localVideoRef.current.srcObject = localStreamRef.current;
      }
      setIsScreenSharing(false);
    } else {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
        screenStreamRef.current = screenStream;
        if (localVideoRef.current) {
          localVideoRef.current.srcObject = screenStream;
        }
        screenStream.getVideoTracks()[0].onended = () => {
          setIsScreenSharing(false);
          if (localVideoRef.current && localStreamRef.current) {
            localVideoRef.current.srcObject = localStreamRef.current;
          }
        };
        setIsScreenSharing(true);
      } catch (err) {
        console.warn("Screen share cancelled:", err);
      }
    }
  };

  // Toggle Recording
  const toggleRecording = () => {
    if (isRecording) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
      setIsRecording(false);
    } else {
      const streamToRecord = screenStreamRef.current || localStreamRef.current;
      if (!streamToRecord) return;
      recordedChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(streamToRecord, { mimeType: 'video/webm' });
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunksRef.current, { type: 'video/webm' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Stehouwer-Meeting-${roomCode}-${new Date().toISOString().slice(0,10)}.webm`;
        a.click();
      };
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
    }
  };

  // Send In-Meeting Chat
  const handleSendChat = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    setChatMessages(prev => [
      ...prev,
      { sender: 'You', text: chatInput.trim(), time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
    ]);
    setChatInput('');
  };

  // Copy Room Link
  const copyMeetingLink = () => {
    const link = `https://ai-bs-dashboard.web.app/?tab=video_agent&room=${roomCode}`;
    navigator.clipboard.writeText(link);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  // Toggle Invitee Selection
  const toggleInvitee = (email) => {
    setSelectedInvitees(prev => prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email]);
  };

  // Add Custom External Invitee
  const addCustomInvitee = () => {
    if (customInvitee.trim() && customInvitee.includes('@')) {
      if (!selectedInvitees.includes(customInvitee.trim())) {
        setSelectedInvitees(prev => [...prev, customInvitee.trim()]);
      }
      setCustomInvitee('');
    }
  };

  // Handle Schedule & Send Invites Form
  const handleScheduleMeeting = async (e) => {
    e.preventDefault();
    if (!formTitle.trim()) return;
    setIsScheduling(true);
    setScheduleStatus('');

    const newCode = `meet-${Math.floor(100 + Math.random() * 900)}-${Math.floor(100 + Math.random() * 900)}-${Math.floor(100 + Math.random() * 900)}`;
    const joinUrl = `https://ai-bs-dashboard.web.app/?tab=video_agent&room=${newCode}`;

    const newMeeting = {
      title: formTitle.trim(),
      host: formHost,
      date: formDate,
      time: formTime,
      duration: formDuration,
      roomCode: newCode,
      invitees: selectedInvitees,
      agenda: formAgenda.trim() || 'Business Executive Discussion & Action Items',
      createdAt: new Date().toISOString()
    };

    // 1. Save to Firestore scheduled_meetings
    try {
      await fetch("https://firestore.googleapis.com/v1/projects/ai-bs-dashboard/databases/(default)/documents/scheduled_meetings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fields: {
            title: { stringValue: newMeeting.title },
            host: { stringValue: newMeeting.host },
            date: { stringValue: newMeeting.date },
            time: { stringValue: newMeeting.time },
            duration: { stringValue: newMeeting.duration },
            roomCode: { stringValue: newMeeting.roomCode },
            agenda: { stringValue: newMeeting.agenda },
            createdAt: { stringValue: newMeeting.createdAt }
          }
        })
      });
    } catch (err) {
      console.warn("Firestore scheduled_meetings write error:", err);
    }

    // 2. Dispatch Formal Email Invites to All Invitees via Firestore /documents/emails
    for (const invitee of selectedInvitees) {
      const emailBody = `You have been invited to a Stehouwer Publishing Executive Video Meeting!

📅 Date: ${formDate}
⏰ Time: ${formTime} (${formDuration})
👤 Host: ${formHost}

📋 Agenda:
${newMeeting.agenda}

🔗 Join Link:
${joinUrl}

Room Code: ${newCode}`;

      try {
        await fetch("https://firestore.googleapis.com/v1/projects/ai-bs-dashboard/databases/(default)/documents/emails", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            fields: {
              account: { stringValue: invitee },
              sender: { stringValue: formHost.split('@')[0] },
              email: { stringValue: invitee },
              subject: { stringValue: `🗓️ Video Meeting Invite: ${newMeeting.title}` },
              snippet: { stringValue: emailBody },
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              date: new Date().toISOString().split('T')[0],
              category: { stringValue: "Primary" },
              folder: { stringValue: "Inbox" },
              starred: { booleanValue: true },
              read: { booleanValue: false },
              label: { stringValue: `[Imap]/${invitee.split('@')[0]}` }
            }
          })
        });
      } catch (err) {
        console.warn("Email dispatch error:", err);
      }
    }

    setScheduledMeetings(prev => [newMeeting, ...prev]);
    setScheduleStatus('✅ Meeting scheduled & email invites dispatched live!');

    setTimeout(() => {
      setIsScheduling(false);
      setIsScheduleOpen(false);
      setFormTitle('');
      setFormAgenda('');
      setScheduleStatus('');
    }, 1500);
  };

  return (
    <div style={styles.container}>
      {/* LOBBY / DASHBOARD VIEW */}
      {!inCall ? (
        <div style={styles.lobbyContainer}>
          {/* TOP HERO HUD */}
          <div style={styles.heroHud} className="glass-panel">
            <div style={{ flex: 1 }}>
              <div style={styles.heroBadge}>
                <Video size={14} style={{ marginRight: '6px' }} /> Stehouwer Enterprise WebRTC Video Suite
              </div>
              <h2 style={styles.heroTitle}>Business Meetings & Video Conferencing</h2>
              <p style={styles.heroSub}>
                Host encrypted HD video calls, schedule team reviews, stream desktops, and dispatch instant email invitations across Stehouwer Publishing.
              </p>
            </div>

            <div style={styles.heroActions}>
              <button style={styles.instantStartBtn} onClick={() => startCall(null, 'Instant Executive Strategy Call')}>
                <Video size={18} style={{ marginRight: '8px' }} /> Start Instant Meeting
              </button>

              <button style={styles.scheduleOpenBtn} onClick={() => setIsScheduleOpen(true)}>
                <Calendar size={18} style={{ marginRight: '8px' }} /> Schedule & Send Invites
              </button>
            </div>
          </div>

          {/* JOIN ROOM BY CODE STRIP */}
          <div style={styles.joinStrip} className="glass-panel">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
              <Share2 size={18} color="#38bdf8" />
              <input 
                type="text" 
                placeholder="Enter 9-digit Room Code (e.g. meet-928-401-382)..." 
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value)}
                style={styles.joinInput}
              />
            </div>
            <button style={styles.joinBtn} onClick={() => startCall(roomCode || null, 'Joined Business Meeting')}>
              Join Meeting
            </button>
          </div>

          {/* SCHEDULED MEETINGS GRID */}
          <div style={styles.meetingsHeader}>
            <h3 style={{ color: '#f0f6fc', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={20} color="#58a6ff" /> Upcoming Business Meetings ({scheduledMeetings.length})
            </h3>
          </div>

          <div style={styles.meetingsGrid}>
            {scheduledMeetings.map(m => (
              <div key={m.id || m.roomCode} style={styles.meetingCard} className="glass-panel">
                <div style={styles.cardHeader}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={styles.dateTag}>{m.date}</span>
                    <span style={styles.timeTag}>{m.time} ({m.duration})</span>
                  </div>
                  <span style={styles.roomCodeBadge}>{m.roomCode}</span>
                </div>

                <h4 style={styles.cardTitle}>{m.title}</h4>
                <p style={styles.cardAgenda}>{m.agenda}</p>

                <div style={styles.cardMeta}>
                  <div style={{ fontSize: '0.8rem', color: '#8b949e' }}>
                    Host: <strong style={{ color: '#c9d1d9' }}>{m.host}</strong>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#8b949e', marginTop: '4px' }}>
                    Invitees: <span style={{ color: '#38bdf8' }}>{m.invitees?.length || 0} Team Members</span>
                  </div>
                </div>

                <div style={styles.cardFooter}>
                  <button style={styles.joinCardBtn} onClick={() => startCall(m.roomCode, m.title)}>
                    <Video size={14} style={{ marginRight: '6px' }} /> Join Meeting Room
                  </button>
                  <button 
                    style={styles.copyCardBtn} 
                    onClick={() => {
                      navigator.clipboard.writeText(`https://ai-bs-dashboard.web.app/?tab=video_agent&room=${m.roomCode}`);
                      alert(`Copied meeting link for ${m.title}`);
                    }}
                  >
                    <Copy size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* LIVE WEBRTC CALL STUDIO HUD */
        <div style={styles.callStudio}>
          {/* CALL TOP BAR */}
          <div style={styles.callTopBar}>
            <div>
              <h3 style={{ color: '#f0f6fc', margin: 0, fontSize: '1.1rem' }}>{activeTitle}</h3>
              <div style={{ fontSize: '0.78rem', color: '#8b949e', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ color: '#34d399', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Circle size={8} fill="#34d399" /> LIVE Encrypted
                </span>
                <span>•</span>
                <span>Room Code: <strong>{roomCode}</strong></span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button style={styles.linkShareBtn} onClick={copyMeetingLink}>
                {copiedLink ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
                <span>{copiedLink ? 'Copied Link!' : 'Share Room Link'}</span>
              </button>

              <button style={styles.chatToggleBtn} onClick={() => setIsChatOpen(!isChatOpen)}>
                <MessageSquare size={16} />
                <span>Chat</span>
              </button>
            </div>
          </div>

          {/* VIDEO GRID AREA */}
          <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
            <div style={styles.videoGrid}>
              {/* LOCAL VIDEO CARD */}
              <div style={styles.videoCard}>
                <video ref={localVideoRef} autoPlay playsInline muted style={styles.videoElement} />
                <div style={styles.participantName}>
                  <span>You ({isHost ? 'Host' : 'Guest'})</span>
                  {micMuted && <MicOff size={12} color="#f87171" />}
                </div>
              </div>

              {/* REMOTE WEBRTC PARTICIPANTS */}
              {Object.entries(remoteStreams).map(([peerId, stream]) => (
                <div key={peerId} style={styles.videoCard}>
                  <video 
                    autoPlay 
                    playsInline 
                    style={styles.videoElement} 
                    ref={el => { if (el) el.srcObject = stream; }} 
                  />
                  <div style={styles.participantName}>
                    <span>Guest: {peerId}</span>
                  </div>
                </div>
              ))}

              {/* MOCK PLACEHOLDERS IF NO GUESTS (just to keep the UI looking full for the demo if alone) */}
              {Object.keys(remoteStreams).length === 0 && (
                <div style={styles.videoCardPlaceholder}>
                  <div style={styles.avatarCircle}>Waiting...</div>
                  <span style={{ color: '#8b949e', fontSize: '0.9rem', marginTop: '12px' }}>Waiting for guests to join Room {roomCode}</span>
                </div>
              )}
            </div>

            {/* SIDE CHAT DRAWER */}
            {isChatOpen && (
              <div style={styles.chatDrawer} className="glass-panel">
                <div style={styles.chatHeader}>
                  <h4 style={{ color: '#f0f6fc', margin: 0 }}>In-Meeting Chat</h4>
                  <button style={{ background: 'none', border: 'none', color: '#8b949e', cursor: 'pointer' }} onClick={() => setIsChatOpen(false)}>✕</button>
                </div>

                <div style={styles.chatMessagesList}>
                  {chatMessages.map((msg, i) => (
                    <div key={i} style={styles.chatBubble}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: '#38bdf8', marginBottom: '2px' }}>
                        <span>{msg.sender}</span>
                        <span style={{ color: '#64748b' }}>{msg.time}</span>
                      </div>
                      <div style={{ color: '#e2e8f0', fontSize: '0.85rem' }}>{msg.text}</div>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleSendChat} style={styles.chatInputForm}>
                  <input 
                    type="text" 
                    placeholder="Type a message..." 
                    value={chatInput} 
                    onChange={(e) => setChatInput(e.target.value)}
                    style={styles.chatInputField}
                  />
                </form>
              </div>
            )}
          </div>

          {/* CALL CONTROL TOOLBAR */}
          <div style={styles.controlToolbar}>
            <button 
              style={{ ...styles.ctrlBtn, backgroundColor: micMuted ? '#ef4444' : '#1e293b' }} 
              onClick={toggleMic}
              title={micMuted ? "Unmute Microphone" : "Mute Microphone"}
            >
              {micMuted ? <MicOff size={20} color="#ffffff" /> : <Mic size={20} color="#f8fafc" />}
            </button>

            <button 
              style={{ ...styles.ctrlBtn, backgroundColor: camMuted ? '#ef4444' : '#1e293b' }} 
              onClick={toggleCam}
              title={camMuted ? "Turn On Camera" : "Turn Off Camera"}
            >
              {camMuted ? <VideoOff size={20} color="#ffffff" /> : <Video size={20} color="#f8fafc" />}
            </button>

            <button 
              style={{ ...styles.ctrlBtn, backgroundColor: isScreenSharing ? '#0284c7' : '#1e293b' }} 
              onClick={toggleScreenShare}
              title="Share Screen / Window"
            >
              <Monitor size={20} color="#f8fafc" />
            </button>

            <button 
              style={{ ...styles.ctrlBtn, backgroundColor: isRecording ? '#dc2626' : '#1e293b' }} 
              onClick={toggleRecording}
              title={isRecording ? "Stop Recording" : "Record Meeting MP4"}
            >
              <StopCircle size={20} color="#f8fafc" />
            </button>

            <button 
              style={styles.endCallBtn} 
              onClick={endCall}
              title="End Meeting"
            >
              <PhoneOff size={20} style={{ marginRight: '8px' }} /> End Call
            </button>
          </div>
        </div>
      )}

      {/* SCHEDULE MEETING MODAL */}
      {isScheduleOpen && (
        <div style={styles.modalOverlay} onClick={() => setIsScheduleOpen(false)}>
          <div style={styles.modalContent} className="glass-panel" onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <h3 style={{ color: '#f0f6fc', margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Calendar size={20} color="#58a6ff" /> Schedule Business Meeting & Send Email Invites
              </h3>
            </div>

            <form onSubmit={handleScheduleMeeting} style={{ marginTop: '16px' }}>
              <div style={styles.formGroup}>
                <label style={styles.label}>Meeting Title</label>
                <input 
                  type="text" 
                  placeholder="e.g. Stehouwer Publishing Q3 Strategy & Review" 
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  required
                  style={styles.input}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Date</label>
                  <input 
                    type="date" 
                    value={formDate}
                    onChange={(e) => setFormDate(e.target.value)}
                    style={styles.input}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Time</label>
                  <input 
                    type="time" 
                    value={formTime}
                    onChange={(e) => setFormTime(e.target.value)}
                    style={styles.input}
                  />
                </div>

                <div style={styles.formGroup}>
                  <label style={styles.label}>Duration</label>
                  <select 
                    value={formDuration}
                    onChange={(e) => setFormDuration(e.target.value)}
                    style={styles.input}
                  >
                    <option value="15 mins">15 mins</option>
                    <option value="30 mins">30 mins</option>
                    <option value="45 mins">45 mins</option>
                    <option value="60 mins">60 mins</option>
                    <option value="90 mins">90 mins</option>
                  </select>
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Host Account</label>
                <select 
                  value={formHost}
                  onChange={(e) => setFormHost(e.target.value)}
                  style={styles.input}
                >
                  <option value="brett@StehouwerPublishing.com">Brett Stehouwer (brett@StehouwerPublishing.com)</option>
                  <option value="sean@StehouwerPublishing.com">Sean Stehouwer (sean@StehouwerPublishing.com)</option>
                  <option value="julie@StehouwerPublishing.com">Julie Stehouwer (julie@StehouwerPublishing.com)</option>
                </select>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Invite Team Members (Dispatches Live Email Invites)</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '6px', border: '1px solid #334155' }}>
                  {TEAM_MEMBERS.map(m => (
                    <label key={m.email} style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#e2e8f0', cursor: 'pointer', fontSize: '0.88rem' }}>
                      <input 
                        type="checkbox" 
                        checked={selectedInvitees.includes(m.email)}
                        onChange={() => toggleInvitee(m.email)}
                      />
                      <span><strong>{m.name}</strong> ({m.email})</span>
                    </label>
                  ))}
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Add External Client Email Invitee</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input 
                    type="email" 
                    placeholder="client@externalcompany.com" 
                    value={customInvitee}
                    onChange={(e) => setCustomInvitee(e.target.value)}
                    style={styles.input}
                  />
                  <button type="button" onClick={addCustomInvitee} style={styles.addInviteeBtn}>
                    <Plus size={16} /> Add
                  </button>
                </div>
              </div>

              <div style={styles.formGroup}>
                <label style={styles.label}>Agenda / Discussion Notes</label>
                <textarea 
                  rows={3} 
                  placeholder="Detail meeting goals, action items, and topic outlines..." 
                  value={formAgenda}
                  onChange={(e) => setFormAgenda(e.target.value)}
                  style={{ ...styles.input, resize: 'vertical' }}
                />
              </div>

              {scheduleStatus && (
                <div style={{ color: '#34d399', fontSize: '0.88rem', fontWeight: '600', marginBottom: '12px' }}>
                  {scheduleStatus}
                </div>
              )}

              <div style={styles.modalFooter}>
                <button type="button" onClick={() => setIsScheduleOpen(false)} style={styles.cancelBtn}>
                  Cancel
                </button>

                <button type="submit" disabled={isScheduling} style={styles.submitScheduleBtn}>
                  <Mail size={16} style={{ marginRight: '6px' }} /> {isScheduling ? 'Dispatching Invites...' : 'Schedule & Send Invites'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    padding: '24px',
    backgroundColor: '#0d1117',
    minHeight: '100vh',
    color: '#c9d1d9',
    fontFamily: 'Inter, system-ui, sans-serif'
  },
  lobbyContainer: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '20px'
  },
  heroHud: {
    background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.9) 100%)',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    borderRadius: '12px',
    padding: '28px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '24px',
    boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
  },
  heroBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    background: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    fontSize: '0.75rem',
    fontWeight: '700',
    padding: '4px 10px',
    borderRadius: '20px',
    marginBottom: '12px'
  },
  heroTitle: {
    color: '#f8fafc',
    fontSize: '1.6rem',
    fontWeight: '800',
    margin: '0 0 8px 0'
  },
  heroSub: {
    color: '#94a3b8',
    fontSize: '0.92rem',
    margin: 0,
    maxWidth: '700px',
    lineHeight: '1.5'
  },
  heroActions: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    flexShrink: 0
  },
  instantStartBtn: {
    background: 'linear-gradient(90deg, #10b981 0%, #059669 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '12px 20px',
    borderRadius: '8px',
    fontWeight: '700',
    fontSize: '0.9rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)'
  },
  scheduleOpenBtn: {
    background: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.4)',
    padding: '12px 20px',
    borderRadius: '8px',
    fontWeight: '700',
    fontSize: '0.9rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  joinStrip: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '10px',
    padding: '12px 18px',
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  joinInput: {
    flex: 1,
    background: '#0d1117',
    border: '1px solid #30363d',
    color: '#f0f6fc',
    padding: '10px 14px',
    borderRadius: '6px',
    fontSize: '0.9rem',
    outline: 'none'
  },
  joinBtn: {
    background: '#238636',
    color: '#ffffff',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '6px',
    fontWeight: '700',
    fontSize: '0.88rem',
    cursor: 'pointer'
  },
  meetingsHeader: {
    marginTop: '12px'
  },
  meetingsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '16px'
  },
  meetingCard: {
    background: '#161b22',
    border: '1px solid #30363d',
    borderRadius: '10px',
    padding: '18px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px'
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  dateTag: {
    background: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    fontSize: '0.72rem',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '4px'
  },
  timeTag: {
    color: '#94a3b8',
    fontSize: '0.75rem',
    fontWeight: '600'
  },
  roomCodeBadge: {
    fontFamily: 'monospace',
    fontSize: '0.75rem',
    color: '#e2e8f0',
    background: '#0f172a',
    padding: '2px 8px',
    borderRadius: '4px',
    border: '1px solid #334155'
  },
  cardTitle: {
    color: '#f8fafc',
    fontSize: '1.05rem',
    fontWeight: '700',
    margin: 0
  },
  cardAgenda: {
    color: '#94a3b8',
    fontSize: '0.85rem',
    margin: 0,
    lineHeight: '1.4'
  },
  cardMeta: {
    background: '#0f172a',
    padding: '10px',
    borderRadius: '6px',
    border: '1px solid #1e293b'
  },
  cardFooter: {
    display: 'flex',
    gap: '10px',
    marginTop: '4px'
  },
  joinCardBtn: {
    flex: 1,
    background: 'linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '8px 12px',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '0.85rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  copyCardBtn: {
    background: '#1e293b',
    color: '#94a3b8',
    border: '1px solid #334155',
    padding: '8px 12px',
    borderRadius: '6px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  callStudio: {
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - 80px)',
    background: '#090d16',
    borderRadius: '12px',
    overflow: 'hidden',
    border: '1px solid #1e293b'
  },
  callTopBar: {
    background: '#0f172a',
    borderBottom: '1px solid #1e293b',
    padding: '12px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  linkShareBtn: {
    background: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  chatToggleBtn: {
    background: '#1e293b',
    color: '#f8fafc',
    border: '1px solid #334155',
    padding: '6px 12px',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  videoGrid: {
    flex: 1,
    padding: '16px',
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '16px',
    alignItems: 'center',
    justifyContent: 'center'
  },
  videoCard: {
    position: 'relative',
    background: '#1e293b',
    borderRadius: '12px',
    overflow: 'hidden',
    aspectRatio: '16/9',
    boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
    border: '2px solid #0284c7'
  },
  videoElement: {
    width: '100%',
    height: '100%',
    objectFit: 'cover'
  },
  videoCardPlaceholder: {
    position: 'relative',
    background: '#1e293b',
    borderRadius: '12px',
    aspectRatio: '16/9',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #334155'
  },
  avatarCircle: {
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    background: '#0f172a',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '2rem',
    border: '2px solid #38bdf8'
  },
  participantName: {
    position: 'absolute',
    bottom: '12px',
    left: '12px',
    background: 'rgba(15, 23, 42, 0.8)',
    color: '#ffffff',
    fontSize: '0.75rem',
    fontWeight: '600',
    padding: '4px 10px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    gap: '6px'
  },
  chatDrawer: {
    width: '320px',
    background: '#0f172a',
    borderLeft: '1px solid #1e293b',
    display: 'flex',
    flexDirection: 'column'
  },
  chatHeader: {
    padding: '12px 16px',
    borderBottom: '1px solid #1e293b',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  chatMessagesList: {
    flex: 1,
    padding: '16px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px'
  },
  chatBubble: {
    background: '#1e293b',
    padding: '8px 12px',
    borderRadius: '8px',
    border: '1px solid #334155'
  },
  chatInputForm: {
    padding: '12px',
    borderTop: '1px solid #1e293b'
  },
  chatInputField: {
    width: '100%',
    background: '#090d16',
    border: '1px solid #334155',
    color: '#ffffff',
    padding: '8px 12px',
    borderRadius: '6px',
    fontSize: '0.85rem',
    outline: 'none'
  },
  controlToolbar: {
    background: '#0f172a',
    borderTop: '1px solid #1e293b',
    padding: '16px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '16px'
  },
  ctrlBtn: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease'
  },
  endCallBtn: {
    background: '#dc2626',
    color: '#ffffff',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '30px',
    fontWeight: '700',
    fontSize: '0.9rem',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
    backdropFilter: 'blur(4px)'
  },
  modalContent: {
    backgroundColor: '#161b22',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    borderRadius: '12px',
    padding: '24px',
    width: '650px',
    maxWidth: '90vw',
    maxHeight: '85vh',
    overflowY: 'auto'
  },
  modalHeader: {
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    paddingBottom: '12px'
  },
  formGroup: {
    marginBottom: '16px'
  },
  label: {
    display: 'block',
    color: '#f0f6fc',
    fontSize: '0.85rem',
    fontWeight: '600',
    marginBottom: '6px'
  },
  input: {
    width: '100%',
    background: '#0d1117',
    border: '1px solid #30363d',
    color: '#f0f6fc',
    padding: '8px 12px',
    borderRadius: '6px',
    fontSize: '0.88rem',
    outline: 'none'
  },
  addInviteeBtn: {
    background: '#238636',
    color: '#ffffff',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '12px',
    marginTop: '20px',
    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
    paddingTop: '16px'
  },
  cancelBtn: {
    background: 'transparent',
    color: '#8b949e',
    border: '1px solid #30363d',
    padding: '8px 16px',
    borderRadius: '6px',
    cursor: 'pointer'
  },
  submitScheduleBtn: {
    background: 'linear-gradient(90deg, #2563eb 0%, #1d4ed8 100%)',
    color: '#ffffff',
    border: 'none',
    padding: '8px 20px',
    borderRadius: '6px',
    fontWeight: '700',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center'
  }
};
