import React, { useState, useEffect, useRef } from 'react';
import { 
  KNOWN_TEAM_MEMBERS, 
  sendTeamMessage, 
  subscribeToChannelMessages, 
  subscribeToPresence,
  getFriendlyUserName,
  getFriendlyUserRole,
  getFriendlyUserAvatar,
  toggleMessageReaction
} from './collaborationService';
import './TeamLiveChatModal.css';

const TEAM_CHANNELS = [
  { 
    id: 'general_team', 
    name: 'general-chat', 
    label: '# general-chat', 
    desc: 'Main team sync, announcements & live discussion', 
    icon: '💬',
    badge: 'ALL TEAM' 
  },
  { 
    id: 'screenplay_creative', 
    name: 'screenplay-creative', 
    label: '# screenplay-creative', 
    desc: 'Scripts, screenplay pitches, film treatments & ad copy', 
    icon: '🎬',
    badge: 'STUDIO' 
  },
  { 
    id: 'fe_logistics', 
    name: 'logistics-fe-express', 
    label: '# logistics-fe-express', 
    desc: 'Freight dispatch, daily routes & fleet communication', 
    icon: '🚛',
    badge: 'LOGISTICS' 
  },
  { 
    id: 'system_ops', 
    name: 'system-ops-telemetry', 
    label: '# system-ops-telemetry', 
    desc: 'RTX 4090 GPU locks, server nodes & health telemetry', 
    icon: '⚡',
    badge: 'DEV OPS' 
  }
];

const WORKSPACE_OPTIONS = [
  { tab: 'dashboard', name: 'Dashboard Matrix', icon: '📊' },
  { tab: 'fe_express', name: 'FE Express Logistics', icon: '🚛' },
  { tab: 'recdebut', name: 'Recreational Debut', icon: '🏆' },
  { tab: 'screenwriting', name: 'Screenplay Studio', icon: '🎬' },
  { tab: 'terminal', name: 'Direct Host Terminal', icon: '🖥️' },
  { tab: 'bullshit_trainer', name: 'Autonomous Swarm Trainer', icon: '🤖' },
  { tab: 'crypto_swarm', name: 'Crypto & Pearl Engine', icon: '⛏️' }
];

const QUICK_EMOJIS = ['👍', '❤️', '🔥', '🚀', '✨', '😂'];

function playMessageChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    if (ctx.state === 'suspended') {
      ctx.resume().catch(() => {});
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1174.66, ctx.currentTime + 0.08);
    gain.gain.setValueAtTime(0.06, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.22);
  } catch (_) {}
}

function getDayKey(timestamp) {
  if (!timestamp) return '';
  const d = new Date(timestamp);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function formatDayLabel(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const msgDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (msgDate.getTime() === today.getTime()) {
    return 'Today';
  } else if (msgDate.getTime() === yesterday.getTime()) {
    return 'Yesterday';
  } else {
    return date.toLocaleDateString(undefined, { 
      weekday: 'long', 
      month: 'short', 
      day: 'numeric', 
      year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined 
    });
  }
}

export default function TeamLiveChatModal({ 
  isOpen, 
  onClose, 
  currentUser, 
  activeTab = 'dashboard',
  onNavigateTab 
}) {
  const [activeChannel, setActiveChannel] = useState('general_team');
  const [messages, setMessages] = useState([]);
  const [presenceList, setPresenceList] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [mobileView, setMobileView] = useState('chat'); // 'channels' | 'chat'
  const [activeReactionMsgId, setActiveReactionMsgId] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const prevMessagesCountRef = useRef(0);

  const getMyMemberId = () => {
    const myEmail = (currentUser?.email || '').toLowerCase().trim();
    const found = KNOWN_TEAM_MEMBERS.find(m => (m.aliases || [m.email]).some(a => a.toLowerCase() === myEmail));
    return found ? found.id : myEmail.replace(/[^a-zA-Z0-9]/g, '_') || 'admin';
  };

  const isUserMine = (msg) => {
    const myEmail = (currentUser?.email || '').toLowerCase().trim();
    const senderEmail = (msg.senderEmail || '').toLowerCase().trim();
    if (!myEmail) return false;
    if (senderEmail === myEmail) return true;
    const foundMember = KNOWN_TEAM_MEMBERS.find(m => (m.aliases || [m.email]).some(a => a.toLowerCase() === myEmail));
    if (foundMember && (foundMember.aliases || [foundMember.email]).some(a => a.toLowerCase() === senderEmail)) {
      return true;
    }
    return false;
  };

  useEffect(() => {
    if (!isOpen || !currentUser) {
      setPresenceList(KNOWN_TEAM_MEMBERS.map(m => ({ ...m, status: 'offline', currentTab: 'Offline' })));
      return;
    }
    const unsubscribe = subscribeToPresence((list) => {
      setPresenceList(list);
    });
    return () => unsubscribe && unsubscribe();
  }, [isOpen, currentUser]);

  useEffect(() => {
    if (!isOpen || !currentUser) {
      setMessages([]);
      return;
    }
    prevMessagesCountRef.current = 0;
    const unsubscribe = subscribeToChannelMessages(activeChannel, (msgs) => {
      // Audio notification if new incoming message from someone else
      if (prevMessagesCountRef.current > 0 && msgs.length > prevMessagesCountRef.current) {
        const lastMsg = msgs[msgs.length - 1];
        if (lastMsg && !isUserMine(lastMsg) && soundEnabled) {
          playMessageChime();
        }
      }
      prevMessagesCountRef.current = msgs.length;
      setMessages(msgs);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    });
    return () => unsubscribe && unsubscribe();
  }, [isOpen, currentUser, activeChannel, soundEnabled]);

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    const isMobileDevice = typeof window !== 'undefined' && (
      window.innerWidth < 768 || 
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    );

    try {
      setIsSending(true);
      await sendTeamMessage({
        channelId: activeChannel,
        senderEmail: currentUser?.email || 'admin@stehouwer.live',
        senderName: currentUser?.displayName || getFriendlyUserName(currentUser?.email),
        senderDevice: isMobileDevice ? 'Mobile' : 'Desktop',
        text: inputMessage.trim()
      });
      setInputMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    } catch (err) {
      alert('Failed to send message: ' + err.message);
    } finally {
      setIsSending(false);
    }
  };

  const handleShareWorkspace = async (targetTab, targetName, targetIcon) => {
    const tabKey = targetTab || activeTab;
    const tabName = (targetName || tabKey.replace(/_/g, ' ')).toUpperCase();
    const toolUrl = `${window.location.origin}${window.location.pathname}?tab=${tabKey}`;
    const icon = targetIcon || '🚀';
    
    await sendTeamMessage({
      channelId: activeChannel,
      senderEmail: currentUser?.email || 'admin@stehouwer.live',
      senderName: currentUser?.displayName || getFriendlyUserName(currentUser?.email),
      text: `${icon} I am sharing the ${tabName} workspace. Tap to open:`,
      toolLink: { tab: tabKey, url: toolUrl, name: tabName, icon: icon }
    });
    setShowWorkspaceMenu(false);
  };

  const handleToggleReaction = async (messageId, emoji) => {
    const userEmail = currentUser?.email || 'admin@stehouwer.live';
    try {
      await toggleMessageReaction(messageId, emoji, userEmail);
    } catch (_) {}
    setActiveReactionMsgId(null);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleInputResize = (e) => {
    setInputMessage(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const getChannelDetails = () => {
    const channel = TEAM_CHANNELS.find(c => c.id === activeChannel);
    if (channel) {
      return {
        title: `${channel.icon} ${channel.name}`,
        subtitle: channel.desc,
        isChannel: true,
        badge: channel.badge
      };
    }
    if (activeChannel.startsWith('saved_notes_')) {
      return {
        title: '⭐ Saved Notes & Cloud Clipboard',
        subtitle: 'Personal sync between your Desktop and Mobile sessions',
        isChannel: false,
        badge: 'PERSONAL'
      };
    }
    const myId = getMyMemberId();
    const otherMember = presenceList.find(m => {
      const channelKey = `dm_${[myId, m.id].sort().join('_')}`;
      return channelKey === activeChannel;
    });
    if (otherMember) {
      return {
        title: `${otherMember.avatar} ${otherMember.name}`,
        subtitle: `${otherMember.role} · ${otherMember.deviceBadge || (otherMember.status === 'online' ? '🟢 Online' : '⚪ Offline')}`,
        isChannel: false,
        badge: otherMember.role,
        avatar: otherMember.avatar,
        status: otherMember.status
      };
    }
    return {
      title: '💬 Private Conversation',
      subtitle: 'Real-time encrypted team bridge',
      isChannel: false
    };
  };

  if (!isOpen) return null;

  const currentChannelDetails = getChannelDetails();
  const myId = getMyMemberId();
  const onlineCount = presenceList.filter(p => p.status === 'online').length;

  const filteredChannels = TEAM_CHANNELS.filter(c => 
    !searchFilter || c.name.toLowerCase().includes(searchFilter.toLowerCase()) || c.desc.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const filteredMembers = presenceList.filter(m =>
    !searchFilter || m.name.toLowerCase().includes(searchFilter.toLowerCase()) || m.role.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <div className="messenger-backdrop" onClick={onClose}>
      <div 
        className={`messenger-modal glass-panel mobile-view-${mobileView}`} 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Contacts Sidebar */}
        <div className="messenger-sidebar">
          <div className="messenger-sidebar-header">
            <div className="sidebar-title-group">
              <span className="sidebar-logo">💬</span>
              <div>
                <h3>Stehouwer Team</h3>
                <span className="sidebar-sub">Ecosystem Messenger</span>
              </div>
            </div>
            <div className="messenger-online-pill">
              <span className="online-pulse-dot" />
              <span>{onlineCount} Online</span>
            </div>
          </div>

          {/* Quick Search */}
          <div className="messenger-search-bar">
            <span className="search-icon">🔍</span>
            <input 
              type="text" 
              placeholder="Search channels & team..." 
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
            {searchFilter && (
              <button className="clear-search-btn" onClick={() => setSearchFilter('')}>✕</button>
            )}
          </div>

          <div className="messenger-channels-list">
            {/* Team Channels Header */}
            <div className="messenger-section-divider">CHANNELS</div>

            {filteredChannels.map(channel => (
              <div 
                key={channel.id}
                className={`messenger-channel-item ${activeChannel === channel.id ? 'active' : ''}`}
                onClick={() => {
                  setActiveChannel(channel.id);
                  setMobileView('chat');
                }}
              >
                <span className="channel-icon">{channel.icon}</span>
                <div className="channel-info">
                  <div className="channel-title-row">
                    <span className="channel-name">{channel.label}</span>
                    <span className="channel-badge">{channel.badge}</span>
                  </div>
                  <span className="channel-meta">{channel.desc}</span>
                </div>
              </div>
            ))}

            {/* Direct Messages Section */}
            <div className="messenger-section-divider">DIRECT MESSAGES</div>

            {/* Saved Notes for Self */}
            <div 
              className={`messenger-contact-item ${activeChannel === `saved_notes_${myId}` ? 'active' : ''}`}
              onClick={() => {
                setActiveChannel(`saved_notes_${myId}`);
                setMobileView('chat');
              }}
            >
              <div className="contact-avatar-wrapper saved-notes-avatar">
                <span className="contact-avatar">⭐</span>
              </div>
              <div className="contact-info">
                <div className="contact-title-row">
                  <span className="contact-name">Saved Notes</span>
                  <span className="you-pill">Cloud Clip</span>
                </div>
                <span className="contact-status-text">Notes, links & device sync</span>
              </div>
            </div>

            {filteredMembers.map(member => {
              const isMe = member.id === myId;
              const channelKey = isMe 
                ? `saved_notes_${myId}` 
                : `dm_${[myId, member.id].sort().join('_')}`;

              return (
                <div 
                  key={member.id}
                  className={`messenger-contact-item ${activeChannel === channelKey ? 'active' : ''}`}
                  onClick={() => {
                    setActiveChannel(channelKey);
                    setMobileView('chat');
                  }}
                >
                  <div className="contact-avatar-wrapper">
                    <span className="contact-avatar" style={{ borderColor: member.color || '#38bdf8' }}>
                      {member.avatar || '👤'}
                    </span>
                    <span className={`status-indicator-dot ${member.status}`} />
                  </div>
                  <div className="contact-info">
                    <div className="contact-title-row">
                      <span className="contact-name">{member.name}</span>
                      {isMe && <span className="you-pill">You</span>}
                    </div>
                    <span className="contact-status-text">
                      {member.deviceBadge 
                        ? member.deviceBadge 
                        : (member.status === 'online' ? `🟢 Active in ${member.currentTab}` : (member.status === 'away' ? '🟡 Away' : '⚪ Offline'))}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat Pane */}
        <div className="messenger-chat-pane">
          {/* Header */}
          <div className="messenger-chat-header">
            <div className="chat-header-main-row">
              {/* Mobile Back Button */}
              <button 
                className="mobile-back-btn"
                onClick={() => setMobileView('channels')}
                title="Back to Channels"
              >
                ‹ Channels
              </button>

              <div className="chat-header-title-box">
                <div className="chat-header-title-row">
                  <h4>{currentChannelDetails.title}</h4>
                  {currentChannelDetails.badge && (
                    <span className="header-badge">{currentChannelDetails.badge}</span>
                  )}
                </div>
                <span className="chat-header-subtitle">{currentChannelDetails.subtitle}</span>
              </div>

              {/* Close Button for Mobile Header Row */}
              <button onClick={onClose} className="messenger-close-btn mobile-close-trigger" title="Close Messenger">✕</button>

              <div className="chat-header-actions">
                {/* Share Tool / Workspace Selector */}
                <div className="share-workspace-wrapper">
                  <button 
                    onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)} 
                    className="messenger-share-tool-btn"
                    title="Share current or selected workspace link with the team"
                  >
                    🚀 Share Workspace ▾
                  </button>
                  {showWorkspaceMenu && (
                    <div className="workspace-dropdown-menu">
                      <div className="dropdown-header">Select Workspace to Share</div>
                      {WORKSPACE_OPTIONS.map(opt => (
                        <div 
                          key={opt.tab}
                          className="dropdown-item"
                          onClick={() => handleShareWorkspace(opt.tab, opt.name, opt.icon)}
                        >
                          <span>{opt.icon}</span>
                          <span>{opt.name}</span>
                          {opt.tab === activeTab && <span className="active-tag">Current</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Sound Toggle */}
                <button 
                  onClick={() => setSoundEnabled(!soundEnabled)} 
                  className={`messenger-action-btn ${soundEnabled ? 'active' : ''}`}
                  title={soundEnabled ? 'Mute incoming chime' : 'Enable incoming chime'}
                >
                  {soundEnabled ? '🔔' : '🔕'}
                </button>

                {/* Desktop Close Button */}
                <button onClick={onClose} className="messenger-close-btn desktop-close-trigger" title="Close Messenger">✕</button>
              </div>
            </div>
          </div>

          {/* Messages Feed */}
          <div className="messenger-messages-feed" onClick={() => { setActiveReactionMsgId(null); setShowWorkspaceMenu(false); }}>
            {messages.length === 0 ? (
              <div className="messenger-empty-state">
                <span className="empty-icon">💬</span>
                <h4>Welcome to {currentChannelDetails.title}</h4>
                <p>No messages yet in this conversation.</p>
                <div className="empty-quick-pills">
                  <button onClick={() => handleShareWorkspace(activeTab, null, '🚀')}>
                    🚀 Share {activeTab.replace(/_/g, ' ').toUpperCase()}
                  </button>
                  <button onClick={() => setInputMessage('👋 Hello team! Checking in.')}>
                    👋 Say Hello
                  </button>
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isMine = isUserMine(msg);
                const prevMsg = messages[index - 1];
                const currentDayKey = getDayKey(msg.timestamp);
                const prevDayKey = prevMsg ? getDayKey(prevMsg.timestamp) : null;
                const isNewDay = currentDayKey !== prevDayKey;
                
                const sameSenderAsPrev = !isNewDay && prevMsg && 
                  prevMsg.senderEmail?.toLowerCase() === msg.senderEmail?.toLowerCase() &&
                  (msg.timestamp - (prevMsg.timestamp || 0)) < 3 * 60 * 1000;

                const timeFormatted = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                return (
                  <React.Fragment key={msg.id || index}>
                    {/* Day Divider */}
                    {isNewDay && (
                      <div className="msg-date-divider">
                        <div className="divider-line" />
                        <span className="divider-label">{formatDayLabel(msg.timestamp)}</span>
                        <div className="divider-line" />
                      </div>
                    )}

                    <div className={`messenger-message-row ${isMine ? 'mine' : 'theirs'} ${sameSenderAsPrev ? 'grouped' : ''}`}>
                      {!isMine && !sameSenderAsPrev && (
                        <div className="msg-sender-avatar-wrapper">
                          <span className="msg-sender-avatar">
                            {msg.senderAvatar || getFriendlyUserAvatar(msg.senderEmail)}
                          </span>
                        </div>
                      )}
                      
                      <div className="msg-bubble-container">
                        {!sameSenderAsPrev && (
                          <div className="msg-header-row">
                            <span className="msg-sender-name">
                              {msg.senderName || getFriendlyUserName(msg.senderEmail)}
                              {isMine && <span className="sender-you-tag"> (You)</span>}
                            </span>
                            {msg.senderRole && (
                              <span className="msg-sender-role">{msg.senderRole}</span>
                            )}
                            {msg.senderDevice && (
                              <span className="msg-sender-device">
                                {msg.senderDevice === 'Mobile' ? '📱 Mobile' : '🖥️ PC'}
                              </span>
                            )}
                            <span className="msg-header-time">{timeFormatted}</span>
                          </div>
                        )}

                        <div className="msg-bubble-wrap">
                          <div className="msg-bubble">
                            <p className="msg-text">{msg.text}</p>
                            
                            {/* Rich Tool / Workspace Card */}
                            {msg.toolLink && (
                              <div 
                                className="msg-tool-card"
                                onClick={() => {
                                  if (onNavigateTab) onNavigateTab(msg.toolLink.tab);
                                  onClose();
                                }}
                              >
                                <div className="tool-card-icon">{msg.toolLink.icon || '🚀'}</div>
                                <div className="tool-card-content">
                                  <span className="tool-card-title">{msg.toolLink.name} Workspace</span>
                                  <span className="tool-card-action">Tap to Open Workspace →</span>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Quick Reaction Button Trigger */}
                          <button 
                            className="msg-add-reaction-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveReactionMsgId(activeReactionMsgId === msg.id ? null : msg.id);
                            }}
                            title="Add reaction"
                          >
                            😀
                          </button>

                          {/* Reaction Picker Popover */}
                          {activeReactionMsgId === msg.id && (
                            <div className="reaction-popover" onClick={(e) => e.stopPropagation()}>
                              {QUICK_EMOJIS.map(emoji => (
                                <button 
                                  key={emoji}
                                  className="reaction-popover-item"
                                  onClick={() => handleToggleReaction(msg.id, emoji)}
                                >
                                  {emoji}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Reaction Badges */}
                        {msg.reactions && Object.keys(msg.reactions).length > 0 && (
                          <div className="msg-reactions-row">
                            {Object.entries(msg.reactions).map(([emoji, users]) => {
                              if (!users || users.length === 0) return null;
                              const hasReacted = users.includes(currentUser?.email?.toLowerCase());
                              return (
                                <button 
                                  key={emoji}
                                  className={`reaction-pill ${hasReacted ? 'active' : ''}`}
                                  onClick={() => handleToggleReaction(msg.id, emoji)}
                                >
                                  <span>{emoji}</span>
                                  <span className="reaction-count">{users.length}</span>
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {sameSenderAsPrev && (
                          <span className="msg-grouped-timestamp">{timeFormatted}</span>
                        )}
                      </div>
                    </div>
                  </React.Fragment>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Reaction Pill Bar */}
          <div className="quick-reactions-ribbon">
            <span className="ribbon-label">Quick Reactions:</span>
            {QUICK_EMOJIS.map(emoji => (
              <button 
                key={emoji} 
                className="quick-emoji-btn"
                onClick={() => setInputMessage(prev => prev ? `${prev} ${emoji}` : emoji)}
                title={`Insert ${emoji}`}
              >
                {emoji}
              </button>
            ))}
          </div>

          {/* Input Bar */}
          <form onSubmit={handleSendMessage} className="messenger-input-bar">
            <textarea
              ref={textareaRef}
              rows={1}
              className="messenger-input-field"
              placeholder={`Message ${currentChannelDetails.title}... (Enter to send, Shift+Enter for new line)`}
              value={inputMessage}
              onChange={handleInputResize}
              onKeyDown={handleKeyDown}
            />
            <button 
              type="submit" 
              className="messenger-send-btn" 
              disabled={!inputMessage.trim() || isSending}
            >
              <span>Send</span>
              <span>➤</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
