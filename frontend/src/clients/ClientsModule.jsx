import React, { useState } from 'react';
import JoeyHamilton from './JoeyHamilton.jsx';
import ActionGlass from './ActionGlass.jsx';
import JohnBarr from './JohnBarr.jsx';

export default function ClientsModule({ backendUrl }) {
  const [selectedClient, setSelectedClient] = useState("john_barr");

  const clients = [
    { id: "john_barr", name: "John Barr (The Simple Chef)" },
    { id: "joey_hamilton", name: "Joey Hamilton" },
    { id: "action_glass", name: "ActionGlass" },
    { id: "new_client", name: "+ Add New Client" }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', backgroundColor: '#f0f2f5' }}>
      
      {/* Top Client Selector Bar */}
      <div style={{ 
        backgroundColor: '#1a1a2e', 
        padding: '15px 20px', 
        display: 'flex', 
        alignItems: 'center', 
        gap: '15px',
        borderBottom: '1px solid #333'
      }}>
        <h3 style={{ margin: 0, color: '#fff', fontSize: '18px' }}>Active Client:</h3>
        <select 
          value={selectedClient} 
          onChange={(e) => setSelectedClient(e.target.value)}
          style={{
            padding: '8px 12px',
            fontSize: '16px',
            borderRadius: '5px',
            border: '1px solid #444',
            backgroundColor: '#2a2a3e',
            color: '#fff',
            outline: 'none',
            cursor: 'pointer',
            minWidth: '280px'
          }}
        >
          {clients.map(client => (
            <option key={client.id} value={client.id}>
              {client.name}
            </option>
          ))}
        </select>
      </div>

      {/* Client Workspace Content */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {selectedClient === "john_barr" ? (
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
