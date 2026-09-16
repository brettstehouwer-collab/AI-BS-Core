import React, { useState, useEffect, useRef } from 'react';
import { collection, query, orderBy, limit, onSnapshot, addDoc, serverTimestamp } from 'firebase/firestore';
import { db, auth } from '../firebase';
import { useAppStore } from './useAppStore';
import { ADMIN_EMAILS } from './accessControl';
import './TeamChatDrawer.css';

export default function TeamChatDrawer({ momMode }) {
  const currentUser = useAppStore((state) => state.currentUser);
  const teamUsers = useAppStore((state) => state.teamUsers);
  const setTeamUsers = useAppStore((state) => state.setTeamUsers);
  const isChatDrawerOpen = useAppStore((state) => state.isChatDrawerOpen);
  const setIsChatDrawerOpen = useAppStore((state) => state.setIsChatDrawerOpen);
  const activeChatChannel = useAppStore((state) => state.activeChatChannel);
  const setActiveChatChannel = useAppStore((state) => state.setActiveChatChannel);

  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  // Presence Listener
  useEffect(() => {
    // Only listen when drawer is actively open and user is authenticated
    if (!isChatDrawerOpen || !db || (auth && !auth.currentUser)) {
      setTeamUsers(ADMIN_EMAILS.map(email => ({
        id: email.toLowerCase(),
        email: email.toLowerCase(),
        displayName: email.split('@')[0],
        isOnline: false,
        activeTab: null
      })));
      return;
    }

    const usersRef = collection(db, 'users');
    const unsubscribe = onSnapshot(usersRef, (snapshot) => {
      // Map Firestore users by email
      const firestoreUsers = {};
      snapshot.forEach((doc) => {
        const data = doc.data();
        if (data.email) {
          firestoreUsers[data.email.toLowerCase()] = { id: doc.id, ...data };
        }
      });

      // Merge all Firestore users and known admins without dropping newly added Firebase users
      const usersMap = new Map();

      // Seed all known admin emails
      ADMIN_EMAILS.forEach(email => {
        const lowerEmail = email.toLowerCase();
        usersMap.set(lowerEmail, {
          id: lowerEmail,
          email: lowerEmail,
          displayName: lowerEmail.split('@')[0],
          isOnline: false,
          activeTab: null
        });
      });

      // Overlay all dynamic Firestore users (includes everyone saved in Firebase)
      Object.entries(firestoreUsers).forEach(([email, uData]) => {
        usersMap.set(email.toLowerCase(), uData);
      });

      const mergedUsers = Array.from(usersMap.values());

      // Sort: Online first, then alphabetical
      mergedUsers.sort((a, b) => {
        if (a.isOnline === b.isOnline) {
          return (a.displayName || '').localeCompare(b.displayName || '');
        }
        return a.isOnline ? -1 : 1;
      });

      setTeamUsers(mergedUsers);
    }, (err) => {
      if (err.code === 'permission-denied' || err.code === 'unauthenticated') return;
      console.warn('[TeamChatDrawer] Users snapshot error:', err.message);
    });
    return () => unsubscribe();
  }, [isChatDrawerOpen, setTeamUsers]);

  // Messages Listener
  useEffect(() => {
    if (!isChatDrawerOpen || !currentUser || !db || (auth && !auth.currentUser)) {
      setMessages([]);
      return;
    }
    
    let messagesRef;
    if (activeChatChannel === 'general') {
      messagesRef = collection(db, 'team_messages');
    } else {
      const channelId = [currentUser.email.toLowerCase(), activeChatChannel.toLowerCase()].sort().join('_');
      messagesRef = collection(db, 'direct_messages', channelId, 'messages');
    }

    const q = query(messagesRef, orderBy('timestamp', 'asc'), limit(100));
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const msgs = [];
      snapshot.forEach((doc) => {
        msgs.push({ id: doc.id, ...doc.data() });
      });
      setMessages(msgs);
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }, (err) => {
      if (err.code === 'permission-denied' || err.code === 'unauthenticated') return;
      console.warn('[TeamChatDrawer] Messages snapshot error:', err.message);
    });
    return () => unsubscribe();
  }, [isChatDrawerOpen, activeChatChannel, currentUser]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputText.trim() || !currentUser) return;

    const msg = inputText.trim();
    setInputText('');
    
    let messagesRef;
    if (activeChatChannel === 'general') {
      messagesRef = collection(db, 'team_messages');
    } else {
      const channelId = [currentUser.email.toLowerCase(), activeChatChannel.toLowerCase()].sort().join('_');
      messagesRef = collection(db, 'direct_messages', channelId, 'messages');
    }

    try {
      await addDoc(messagesRef, {
        text: msg,
        senderId: currentUser.uid,
        senderName: currentUser.displayName || currentUser.email.split('@')[0],
        photoURL: currentUser.photoURL || '',
        timestamp: serverTimestamp(),
      });
    } catch (err) {
      console.error('Failed to send message', err);
    }
  };

  const handleShareTool = () => {
    if (!currentUser) return;
    const currentUrl = window.location.search || '?tab=dashboard';
    const msg = `🚀 Open Active Tool \n${currentUrl}`;
    setInputText(msg);
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const date = timestamp.toDate();
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getInitials = (name) => {
    if (!name) return '?';
    if (name.toLowerCase().includes('julie') || name.toLowerCase().includes('mom')) return '🌸';
    if (name.toLowerCase().includes('brett')) return '👑';
    if (name.toLowerCase().includes('sean')) return '🎬';
    return name.substring(0, 1).toUpperCase();
  };

  const formatLastSeen = (timestamp) => {
    if (!timestamp) return '⚪ Offline';
    try {
      const date = timestamp.toDate ? timestamp.toDate() : new Date(timestamp);
      
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return '⚪ Offline (Just now)';
      if (diffMins < 60) return `⚪ Offline (${diffMins}m ago)`;
      if (diffHours < 24) return `⚪ Offline (${diffHours}h ago)`;
      if (diffDays === 1) return '⚪ Offline (Yesterday)';
      if (diffDays < 7) return `⚪ Offline (${diffDays}d ago)`;
      return `⚪ Offline (${date.toLocaleDateString()})`;
    } catch (e) {
      return '⚪ Offline';
    }
  };

  const activeChannelTitle = activeChatChannel === 'general' 
    ? '👥 Stehouwer Publishing General' 
    : `💬 DM: ${teamUsers.find(u => u.email === activeChatChannel)?.displayName || activeChatChannel}`;

  if (!currentUser) return null;

  return (
    <>
      {/* Floating Action Button */}
      <div 
        className="team-chat-fab" 
        onClick={() => setIsChatDrawerOpen(!isChatDrawerOpen)}
        title="Team Chat"
      >
        <span className="team-chat-fab-icon">💬</span>
      </div>

      {/* Chat Drawer */}
      {isChatDrawerOpen && (
        <div className="team-chat-drawer-container">
          {/* Sidebar */}
          <div className="team-chat-sidebar">
            <div className="team-chat-sidebar-header">
              👥 Contacts & Presence
            </div>
            <div 
              className={`roster-general-row ${activeChatChannel === 'general' ? 'active' : ''}`}
              onClick={() => setActiveChatChannel('general')}
            >
              <div className="roster-general-icon">🌍</div>
              <div className="roster-general-text">General Chat</div>
            </div>
            <div className="team-chat-roster">
              {teamUsers.map(user => (
                <div 
                  key={user.id} 
                  className={`roster-item ${activeChatChannel === user.email ? 'active' : ''}`}
                  onClick={() => setActiveChatChannel(user.email)}
                >
                  <div className="roster-avatar-wrapper">
                    <div className="roster-avatar">{getInitials(user.displayName)}</div>
                    <div className={`presence-dot ${user.isOnline ? 'online' : 'offline'}`} />
                  </div>
                  <div className="roster-info">
                    <div className="roster-name">
                      {user.displayName} {user.id === currentUser.uid ? '(You)' : ''}
                    </div>
                    <div className="roster-badge">
                      {user.isOnline 
                        ? (user.activeTab ? `🟢 Active in ${user.activeTab.replace(/_/g, ' ')}` : '🟢 Online')
                        : formatLastSeen(user.lastSeen)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Main Chat */}
          <div className="team-chat-main">
            <div className="team-chat-main-header">
              <div className="chat-channel-title">{activeChannelTitle}</div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button className="chat-share-btn" onClick={handleShareTool} title="Share your active view into chat">
                  🔗 Share Tool
                </button>
                <button onClick={() => setIsChatDrawerOpen(false)} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: '18px' }}>
                  ✕
                </button>
              </div>
            </div>

            <div className="team-chat-messages">
              {messages.map((msg) => {
                const isSentByMe = msg.senderId === currentUser.uid;
                const isShareLink = msg.text.includes('🚀 Open Active Tool');
                let shareUrl = '';
                let displayMsg = msg.text;

                if (isShareLink) {
                  const parts = msg.text.split('\n');
                  shareUrl = parts[1] || '?tab=dashboard';
                  displayMsg = parts[0];
                }

                return (
                  <div key={msg.id} className={`chat-message-row ${isSentByMe ? 'sent' : 'received'}`}>
                    {!isSentByMe && (
                      <div className="chat-msg-avatar" title={msg.senderName}>
                        {getInitials(msg.senderName)}
                      </div>
                    )}
                    <div className="chat-msg-content">
                      <div className="chat-msg-sender">
                        <span>{msg.senderName}</span>
                        <span className="chat-msg-time">{formatTime(msg.timestamp)}</span>
                      </div>
                      <div className="chat-msg-bubble">
                        {isShareLink ? (
                          <a 
                            href={shareUrl} 
                            className="chat-share-card" 
                            onClick={(e) => {
                              e.preventDefault();
                              setIsChatDrawerOpen(false);
                              const searchParams = new URLSearchParams(shareUrl);
                              const targetTab = searchParams.get('tab');
                              if (targetTab) {
                                window.history.pushState({}, '', shareUrl);
                                window.dispatchEvent(new Event('popstate'));
                              }
                            }}
                          >
                            {displayMsg} →
                          </a>
                        ) : (
                          displayMsg
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            <form className="team-chat-input-area" onSubmit={handleSendMessage}>
              <input 
                type="text" 
                className="team-chat-input" 
                placeholder="Type a message to the team..." 
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
              <button type="submit" className="team-chat-send-btn" disabled={!inputText.trim()}>
                ↑
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
