import React, { useState, useEffect, useRef } from 'react';

const UnifiedChat = ({ isOverlay = false }) => {
  const [messages, setMessages] = useState([]);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://127.0.0.1:8006/ws/chat');
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => {
        const newMsgs = [...prev, data];
        // Keep only last 100 messages
        if (newMsgs.length > 100) newMsgs.shift();
        return newMsgs;
      });
    };

    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const getPlatformIcon = (platform) => {
    switch(platform) {
      case 'twitch': return 'â—¥';
      case 'youtube': return 'â–¶';
      case 'kick': return 'â—¡';
      case 'facebook': return 'f';
      default: return 'â€¢';
    }
  };

  const getPlatformColor = (platform) => {
    switch(platform) {
      case 'twitch': return '#9146FF';
      case 'youtube': return '#FF0000';
      case 'kick': return '#53FC18';
      case 'facebook': return '#1877F2';
      default: return '#888';
    }
  };

  return (
    <div style={{
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      backgroundColor: isOverlay ? 'transparent' : '#0f172a',
      color: '#fff',
      fontFamily: 'Inter, sans-serif',
      fontSize: '13px',
      overflow: 'hidden'
    }}>
      {!isOverlay && (
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #1e293b', fontWeight: 'bold', fontSize: '14px', color: '#cbd5e1', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>AI-BS Unified Chat</span>
          <button 
            onClick={() => window.open('http://127.0.0.1:8006/auth/twitch/login', '_blank')}
            style={{
              background: '#9146FF', color: 'white', border: 'none', borderRadius: '4px',
              padding: '4px 8px', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: '4px'
            }}
          >
            Connect Twitch Chat
          </button>
        </div>
      )}
      
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ 
            padding: '6px 10px', 
            borderRadius: '6px', 
            backgroundColor: msg.type === 'alert' ? 'rgba(83, 252, 24, 0.1)' : (isOverlay ? 'rgba(0,0,0,0.5)' : 'transparent'),
            borderLeft: msg.type === 'alert' ? `3px solid #53FC18` : 'none',
            animation: 'fadeIn 0.3s ease-out'
          }}>
            {msg.type === 'alert' ? (
              <div style={{ color: '#53FC18', fontWeight: 'bold' }}>ðŸŽ‰ {msg.message}</div>
            ) : (
              <div>
                <span style={{ 
                  display: 'inline-block', 
                  width: '16px', 
                  height: '16px', 
                  textAlign: 'center', 
                  lineHeight: '16px',
                  borderRadius: '3px',
                  backgroundColor: getPlatformColor(msg.platform),
                  color: msg.platform === 'kick' ? '#000' : '#fff',
                  fontSize: '10px',
                  marginRight: '6px',
                  fontWeight: 'bold'
                }}>
                  {getPlatformIcon(msg.platform)}
                </span>
                <span style={{ fontWeight: 'bold', color: msg.color || '#38bdf8', marginRight: '6px' }}>
                  {msg.username}
                </span>
                <span style={{ color: '#f8fafc', wordBreak: 'break-word' }}>
                  {msg.message}
                </span>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default UnifiedChat;
