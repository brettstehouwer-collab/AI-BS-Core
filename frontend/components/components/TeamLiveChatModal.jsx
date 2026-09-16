import React, { useState, useEffect, useRef } from 'react';
import { 
  KNOWN_TEAM_MEMBERS, 
  sendTeamMessage, 
  subscribeToChannelMessages, 
  subscribeToPresence,
  getFriendlyUserName 
} from './collaborationService';
import './TeamLiveChatModal.css';

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
  const messagesEndRef = useRef(null);

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
    const unsubscribe = subscribeToChannelMessages(activeChannel, (msgs) => {
      setMessages(msgs);
      setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    });
    return () => unsubscribe && unsubscribe();
  }, [isOpen, currentUser, activeChannel]);

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    try {
      setIsSending(true);
      await sendTeamMessage({
        channelId: activeChannel,
        senderEmail: currentUser?.email || 'admin@stehouwer.live',
        senderName: currentUser?.displayName || getFriendlyUserName(currentUser?.email),
        text: inputMessage.trim()
      });
      setInputMessage('');
    } catch (err) {
      alert('Failed to send message: ' + err.message);
    } finally {
      setIsSending(false);
    }
  };

  const handleShareCurrentTool = async () => {
    const toolUrl = `${window.location.origin}${window.location.pathname}?tab=${activeTab}`;
    const toolName = activeTab.replace(/_/g, ' ').toUpperCase();
    await sendTeamMessage({
      channelId: activeChannel,
      senderEmail: currentUser?.email || 'admin@stehouwer.live',
      senderName: currentUser?.displayName || getFriendlyUserName(currentUser?.email),
      text: `🚀 I am currently in the ${toolName} workspace. Check it out:`,
      toolLink: { tab: activeTab, url: toolUrl, name: toolName }
    });
  };

  if (!isOpen) return null;

  return (
    <div className="messenger-backdrop" onClick={onClose}>
      <div className="messenger-modal glass-panel" onClick={(e) => e.stopPropagation()}>
        {/* Contacts Sidebar */}
        <div className="messenger-sidebar">
          <div className="messenger-sidebar-header">
            <h3>💬 Stehouwer Team</h3>
            <span className="messenger-online-count">
              {presenceList.filter(p => p.status === 'online').length} Online
            </span>
          </div>

          <div className="messenger-channels-list">
            <div 
              className={`messenger-channel-item ${activeChannel === 'general_team' ? 'active' : ''}`}
              onClick={() => setActiveChannel('general_team')}
            >
              <span className="channel-icon">👥</span>
              <div className="channel-info">
                <span className="channel-name">All Team General</span>
                <span className="channel-meta">Main Chat</span>
              </div>
            </div>

            <div className="messenger-section-divider">DIRECT MESSAGES</div>

            {presenceList.map(member => {
              const isMe = member.email.toLowerCase() === (currentUser?.email || '').toLowerCase();
              const channelKey = [currentUser?.email || 'admin', member.email].sort().join('_').replace(/[^a-zA-Z0-9_]/g, '');

              return (
                <div 
                  key={member.email}
                  className={`messenger-contact-item ${activeChannel === channelKey ? 'active' : ''}`}
                  onClick={() => setActiveChannel(channelKey)}
                >
                  <div className="contact-avatar-wrapper">
                    <span className="contact-avatar">{member.avatar || '👤'}</span>
                    <span className={`status-indicator-dot ${member.status}`}></span>
                  </div>
                  <div className="contact-info">
                    <span className="contact-name">{member.name} {isMe ? '(You)' : ''}</span>
                    <span className="contact-status-text">
                      {member.status === 'online' ? `🟢 Active in ${member.currentTab}` : (member.status === 'away' ? '🟡 Away' : '⚪ Offline')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat Pane */}
        <div className="messenger-chat-pane">
          <div className="messenger-chat-header">
            <div className="chat-header-info">
              <h4>{activeChannel === 'general_team' ? '👥 Stehouwer Publishing General' : '💬 Private Conversation'}</h4>
              <span className="chat-header-subtitle">Real-time sync for all logged-in administrators</span>
            </div>
            <div className="chat-header-actions">
              <button onClick={handleShareCurrentTool} className="messenger-share-tool-btn">
                🔗 Share Tool Link
              </button>
              <button onClick={onClose} className="messenger-close-btn">✕</button>
            </div>
          </div>

          <div className="messenger-messages-feed">
            {messages.length === 0 ? (
              <div className="messenger-empty-state">
                <span className="empty-icon">💬</span>
                <p>No messages yet.</p>
                <span>Say hello or share a screenplay / ad copy link!</span>
              </div>
            ) : (
              messages.map(msg => {
                const isMine = msg.senderEmail?.toLowerCase() === (currentUser?.email || '').toLowerCase();
                return (
                  <div key={msg.id} className={`messenger-message-row ${isMine ? 'mine' : 'theirs'}`}>
                    {!isMine && <span className="msg-sender-avatar">{msg.senderAvatar || '👤'}</span>}
                    <div className="msg-bubble-container">
                      {!isMine && <span className="msg-sender-name">{msg.senderName}</span>}
                      <div className="msg-bubble">
                        <p>{msg.text}</p>
                        {msg.toolLink && (
                          <div 
                            className="msg-tool-card"
                            onClick={() => {
                              if (onNavigateTab) onNavigateTab(msg.toolLink.tab);
                              onClose();
                            }}
                          >
                            <span>🚀 Open {msg.toolLink.name} →</span>
                          </div>
                        )}
                      </div>
                      <span className="msg-timestamp">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="messenger-input-bar">
            <input
              type="text"
              className="messenger-input-field"
              placeholder="Type a message to the team..."
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
            />
            <button type="submit" className="messenger-send-btn" disabled={!inputMessage.trim() || isSending}>
              Send ➤
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
