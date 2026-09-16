import React from 'react';
import './ChatContextToolbar.css';

export default function ChatContextToolbar({ activeContexts, onToggleContext }) {
  return (
    <div className="chat-context-toolbar">
      <button 
        type="button"
        className={`context-btn ${activeContexts.file ? 'active' : ''}`}
        onClick={() => onToggleContext('file')}
        title="@file Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.terminal ? 'active' : ''}`}
        onClick={() => onToggleContext('terminal')}
        title="@terminal Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.codebase ? 'active' : ''}`}
        onClick={() => onToggleContext('codebase')}
        title="@codebase Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
      </button>

      <button 
        type="button"
        className={`context-btn ${activeContexts.web ? 'active' : ''}`}
        onClick={() => onToggleContext('web')}
        title="@web Context"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="context-icon"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
      </button>
    </div>
  );
}
