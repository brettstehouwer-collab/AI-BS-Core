import React, { useState, useEffect } from 'react';
import JoeyHamilton from './JoeyHamilton.jsx';
import ActionGlass from './ActionGlass.jsx';
import JohnBarr from './JohnBarr.jsx';
import RecreationalDebut from './RecreationalDebut.jsx';
import FEExpressDispatcher from '../components/FEExpressDispatcher.jsx';

export default function ClientsModule({ backendUrl }) {
  const getInitialClient = () => {
    try {
      const params = new URLSearchParams(window.location.search);
      return params.get("client") || "rec_debut";
    } catch {
      return "rec_debut";
    }
  };

  const [selectedClient, setSelectedClient] = useState(getInitialClient);

  const clients = [
    { id: "rec_debut", name: "🏀 Dennis Bell (Recreational Debut - RecDebut.com)" },
    { id: "fe_express", name: "🚚 FE Express (Box Truck Automation Hub)" },
    { id: "john_barr", name: "John Barr (The Simple Chef)" },
    { id: "joey_hamilton", name: "Joey Hamilton" },
    { id: "action_glass", name: "ActionGlass" },
    { id: "new_client", name: "+ Add New Client" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#07101e' }}>
      
      {/* Top Client Selector Bar */}
      <div className="clients-suite-bar" style={{ 
        backgroundColor: '#0A192F', 
        padding: '12px 20px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        flexShrink: 0
      }}>
        <div className="clients-suite-select-wrap" style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h3 className="clients-suite-title" style={{ margin: 0, color: '#F58426', fontSize: '16px', fontWeight: '800', letterSpacing: '0.5px', whiteSpace: 'nowrap' }}>
            CLIENT SUITE:
          </h3>
          <select 
            className="clients-suite-select"
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

        <div className="clients-suite-subtitle" style={{ fontSize: '12px', color: '#94a3b8' }}>
          AI-BS Sovereign Multi-Client CRM &amp; Campaign Matrix
        </div>
      </div>

      {/* Client Workspace Content */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', overflowX: 'hidden' }}>
        {selectedClient === "rec_debut" ? (
          <RecreationalDebut BACKEND_URL={backendUrl} />
        ) : selectedClient === "fe_express" ? (
          <FEExpressDispatcher BACKEND_URL={backendUrl} />
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
