import React, { useState } from 'react';
import JoeyHamilton from './JoeyHamilton.jsx';
import ActionGlass from './ActionGlass.jsx';
import JohnBarr from './JohnBarr.jsx';
import RecreationalDebut from './RecreationalDebut.jsx';

export default function ClientsModule({ backendUrl }) {
  const [selectedClient, setSelectedClient] = useState("rec_debut");

  const clients = [
    { id: "rec_debut", name: "🏀 Dennis Bell (Recreational Debut - RecDebut.com)" },
    { id: "john_barr", name: "John Barr (The Simple Chef)" },
    { id: "joey_hamilton", name: "Joey Hamilton" },
    { id: "action_glass", name: "ActionGlass" },
    { id: "new_client", name: "+ Add New Client" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#07101e' }}>
      
      {/* Top Client Selector Bar */}
      <div style={{ 
        backgroundColor: '#0A192F', 
        padding: '12px 20px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h3 style={{ margin: 0, color: '#F58426', fontSize: '16px', fontWeight: '800', letterSpacing: '0.5px' }}>
            CLIENT SUITE:
          </h3>
          <select 
            value={selectedClient} 
            onChange={(e) => setSelectedClient(e.target.value)}
            style={{
              padding: '8px 14px',
              fontSize: '14px',
              fontWeight: '700',
              borderRadius: '6px',
              border: '1px solid #F58426',
              backgroundColor: '#07101e',
              color: '#fff',
              outline: 'none',
              cursor: 'pointer',
              minWidth: '380px'
            }}
          >
            {clients.map(client => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        </div>

        <div style={{ fontSize: '12px', color: '#94a3b8' }}>
          AI-BS Sovereign Multi-Client CRM & Campaign Matrix
        </div>
      </div>

      {/* Client Workspace Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {selectedClient === "rec_debut" ? (
          <RecreationalDebut BACKEND_URL={backendUrl} />
        ) : selectedClient === "john_barr" ? (
          <JohnBarr BACKEND_URL={backendUrl} />
        ) : selectedClient === "joey_hamilton" ? (
          <JoeyHamilton BACKEND_URL={backendUrl} />
        ) : selectedClient === "action_glass" ? (
          <ActionGlass BACKEND_URL={backendUrl} />
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666' }}>
            <div style={{ textAlign: 'center' }}>
              <h2 style={{ color: '#1a1a2e' }}>New Client Setup</h2>
              <p>Client onboarding module will go here.</p>
            </div>
          </div>
        )}
      </div>

    </div>
  );
}
