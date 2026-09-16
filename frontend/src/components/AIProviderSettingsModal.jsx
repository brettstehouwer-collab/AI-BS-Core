import React, { useState, useEffect } from 'react';

export default function AIProviderSettingsModal({
  isOpen,
  onClose,
  backendUrl = 'http://127.0.0.1:8000',
  onProviderChange
}) {
  const [providers, setProviders] = useState([]);
  const [activeProvider, setActiveProvider] = useState('local');
  const [selectedProviderTab, setSelectedProviderTab] = useState('local');
  const [keysState, setKeysState] = useState({});
  const [modelsState, setModelsState] = useState({});
  const [showKeyMap, setShowKeyMap] = useState({});
  const [testingStatus, setTestingStatus] = useState({}); // { [id]: { status: 'idle'|'testing'|'valid'|'error', msg: '' } }
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  // Fetch current provider configuration
  useEffect(() => {
    if (!isOpen) return;

    const fetchConfig = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/ai/providers`);
        if (res.ok) {
          const data = await res.json();
          setProviders(data.providers || []);
          setActiveProvider(data.active_provider || 'local');
          setSelectedProviderTab(data.active_provider || 'local');

          // Initialize keys and models from local storage or server
          const initialKeys = {};
          const initialModels = {};
          const localKeys = JSON.parse(localStorage.getItem('aibs_custom_ai_keys') || '{}');

          (data.providers || []).forEach(p => {
            initialKeys[p.id] = localKeys[p.id] || p.masked_key || '';
            initialModels[p.id] = p.saved_model || (p.models && p.models[0]) || '';
          });

          setKeysState(initialKeys);
          setModelsState(initialModels);
        }
      } catch (err) {
        console.error('Failed to fetch AI provider config:', err);
      }
    };

    fetchConfig();
  }, [isOpen, backendUrl]);

  if (!isOpen) return null;

  const currentProvider = providers.find(p => p.id === selectedProviderTab) || providers[0] || {
    id: 'local',
    name: 'Local AI Engine',
    icon: '🖥️',
    description: '',
    models: [],
    requires_key: false
  };

  const handleKeyChange = (providerId, val) => {
    setKeysState(prev => ({ ...prev, [providerId]: val }));
    // Reset test status if key changes
    setTestingStatus(prev => ({ ...prev, [providerId]: { status: 'idle', msg: '' } }));
  };

  const handleModelChange = (providerId, val) => {
    setModelsState(prev => ({ ...prev, [providerId]: val }));
  };

  const toggleShowKey = (providerId) => {
    setShowKeyMap(prev => ({ ...prev, [providerId]: !prev[providerId] }));
  };

  // Test live connection with provider
  const handleTestConnection = async (providerId) => {
    setTestingStatus(prev => ({ ...prev, [providerId]: { status: 'testing', msg: 'Testing connection...' } }));
    try {
      const apiKey = keysState[providerId] || '';
      const res = await fetch(`${backendUrl}/api/ai/validate-key`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          api_key: apiKey,
          model: modelsState[providerId]
        })
      });

      const data = await res.json();
      if (res.ok && data.status === 'valid') {
        setTestingStatus(prev => ({
          ...prev,
          [providerId]: { status: 'valid', msg: data.message || 'Authenticated successfully!' }
        }));
      } else {
        setTestingStatus(prev => ({
          ...prev,
          [providerId]: { status: 'error', msg: data.message || 'Validation failed. Check API key.' }
        }));
      }
    } catch (err) {
      setTestingStatus(prev => ({
        ...prev,
        [providerId]: { status: 'error', msg: 'Network error connecting to validation endpoint.' }
      }));
    }
  };

  // Save Settings
  const handleSaveSettings = async () => {
    setSaving(true);
    setSaveMessage('');
    try {
      // Save unmasked keys to browser localStorage
      const cleanKeys = {};
      Object.keys(keysState).forEach(k => {
        if (keysState[k] && !keysState[k].includes('...')) {
          cleanKeys[k] = keysState[k];
        }
      });
      localStorage.setItem('aibs_custom_ai_keys', JSON.stringify(cleanKeys));
      localStorage.setItem('aibs_active_ai_provider', activeProvider);

      // Save to backend configuration
      const providerPayload = {};
      providers.forEach(p => {
        providerPayload[p.id] = {
          api_key: keysState[p.id] || '',
          model: modelsState[p.id] || (p.models && p.models[0]) || ''
        };
      });

      const res = await fetch(`${backendUrl}/api/ai/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          active_provider: activeProvider,
          providers: providerPayload
        })
      });

      if (res.ok) {
        setSaveMessage('✅ Settings saved! Active Engine updated.');
        if (onProviderChange) {
          onProviderChange(activeProvider, modelsState[activeProvider]);
        }
        setTimeout(() => {
          onClose();
        }, 1200);
      } else {
        alert('Failed to save settings on backend.');
      }
    } catch (err) {
      console.error(err);
      alert('Error saving AI provider configuration.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.8)',
        zIndex: 99999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '10px',
          width: '840px',
          maxWidth: '95vw',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 12px 36px rgba(0,0,0,0.6)',
          overflow: 'hidden'
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 24px',
            backgroundColor: '#0d1117',
            borderBottom: '1px solid #30363d',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🤖</span> AI Engine & Custom API Key Accounts
            </h2>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#8b949e' }}>
              Use your own OpenAI, Anthropic, Gemini, Groq, or DeepSeek accounts with the AI-BS interface, or run 100% locally on your RTX 4090.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ backgroundColor: 'transparent', border: 'none', color: '#8b949e', fontSize: '20px', cursor: 'pointer' }}
          >
            ✕
          </button>
        </div>

        {/* Body: Split Sidebar & Content */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          
          {/* Provider Tabs Sidebar */}
          <div
            style={{
              width: '240px',
              backgroundColor: '#0d1117',
              borderRight: '1px solid #30363d',
              padding: '12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              overflowY: 'auto'
            }}
          >
            <div style={{ fontSize: '11px', fontWeight: 'bold', color: '#8b949e', textTransform: 'uppercase', padding: '6px 8px' }}>
              Select AI Engine
            </div>

            {providers.map(p => {
              const isSelected = selectedProviderTab === p.id;
              const isActive = activeProvider === p.id;
              const hasKey = Boolean(keysState[p.id]) || p.id === 'local';

              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedProviderTab(p.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    borderRadius: '6px',
                    border: isSelected ? '1px solid #58a6ff' : '1px solid transparent',
                    backgroundColor: isSelected ? '#1f6feb22' : 'transparent',
                    color: isSelected ? '#ffffff' : '#c9d1d9',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '16px' }}>{p.icon}</span>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '600' }}>{p.name.split(' ')[0]} {p.name.split(' ')[1] || ''}</div>
                      <div style={{ fontSize: '10px', color: '#8b949e' }}>
                        {p.id === 'local' ? 'Local RTX' : (hasKey ? '🔑 Configured' : 'No Key')}
                      </div>
                    </div>
                  </div>

                  {isActive && (
                    <span style={{ fontSize: '10px', padding: '2px 6px', backgroundColor: '#238636', color: '#ffffff', borderRadius: '10px', fontWeight: 'bold' }}>
                      ACTIVE
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Active Tab Configuration Panel */}
          <div style={{ flex: 1, padding: '24px', backgroundColor: '#161b22', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Engine Overview & Active Switch */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: '16px', borderBottom: '1px solid #30363d' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', color: '#f0f6fc', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>{currentProvider.icon}</span> {currentProvider.name}
                </h3>
                <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: '#8b949e', maxWidth: '420px', lineHeight: '1.4' }}>
                  {currentProvider.description}
                </p>
              </div>

              {/* Set as Active Engine Button */}
              <button
                onClick={() => setActiveProvider(currentProvider.id)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: activeProvider === currentProvider.id ? '#238636' : '#21262d',
                  color: activeProvider === currentProvider.id ? '#ffffff' : '#c9d1d9',
                  border: activeProvider === currentProvider.id ? '1px solid #2ea043' : '1px solid #30363d',
                  borderRadius: '6px',
                  fontWeight: '600',
                  fontSize: '12px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  transition: 'all 0.2s'
                }}
              >
                <span>{activeProvider === currentProvider.id ? '⭐' : '⚪'}</span>
                {activeProvider === currentProvider.id ? 'Active Primary Engine' : 'Set as Active'}
              </button>
            </div>

            {/* Model Selection */}
            <div>
              <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#f0f6fc', display: 'block', marginBottom: '6px' }}>
                Default Model
              </label>
              <select
                value={modelsState[currentProvider.id] || (currentProvider.models && currentProvider.models[0]) || ''}
                onChange={(e) => handleModelChange(currentProvider.id, e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  backgroundColor: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '6px',
                  color: '#c9d1d9',
                  fontSize: '13px',
                  outline: 'none'
                }}
              >
                {(currentProvider.models || []).map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>

            {/* API Key Input (if required) */}
            {currentProvider.requires_key ? (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#f0f6fc' }}>
                    Personal API Key
                  </label>
                  <span style={{ fontSize: '11px', color: '#8b949e' }}>
                    Hint: starts with <code>{currentProvider.key_hint || 'sk-...'}</code>
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <div style={{ position: 'relative', flex: 1 }}>
                    <input
                      type={showKeyMap[currentProvider.id] ? 'text' : 'password'}
                      value={keysState[currentProvider.id] || ''}
                      onChange={(e) => handleKeyChange(currentProvider.id, e.target.value)}
                      placeholder={`Enter your ${currentProvider.name} API Key`}
                      style={{
                        width: '100%',
                        padding: '8px 40px 8px 12px',
                        backgroundColor: '#0d1117',
                        border: '1px solid #30363d',
                        borderRadius: '6px',
                        color: '#c9d1d9',
                        fontSize: '13px',
                        fontFamily: 'monospace'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowKey(currentProvider.id)}
                      style={{
                        position: 'absolute',
                        right: '8px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        background: 'transparent',
                        border: 'none',
                        color: '#8b949e',
                        cursor: 'pointer',
                        fontSize: '13px'
                      }}
                    >
                      {showKeyMap[currentProvider.id] ? '🙈' : '👁️'}
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleTestConnection(currentProvider.id)}
                    disabled={testingStatus[currentProvider.id]?.status === 'testing' || !keysState[currentProvider.id]}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#21262d',
                      border: '1px solid #30363d',
                      borderRadius: '6px',
                      color: '#58a6ff',
                      fontWeight: '600',
                      fontSize: '12px',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {testingStatus[currentProvider.id]?.status === 'testing' ? 'Testing...' : '🧪 Test Key'}
                  </button>
                </div>

                {/* Validation Status Feedback */}
                {testingStatus[currentProvider.id]?.status === 'valid' && (
                  <div style={{ marginTop: '8px', padding: '8px 12px', backgroundColor: 'rgba(35,134,54,0.15)', border: '1px solid #238636', borderRadius: '6px', fontSize: '12px', color: '#3fb950', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>🟢</span> {testingStatus[currentProvider.id].msg}
                  </div>
                )}
                {testingStatus[currentProvider.id]?.status === 'error' && (
                  <div style={{ marginTop: '8px', padding: '8px 12px', backgroundColor: 'rgba(248,81,73,0.15)', border: '1px solid #f85149', borderRadius: '6px', fontSize: '12px', color: '#f85149', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span>🔴</span> {testingStatus[currentProvider.id].msg}
                  </div>
                )}

                <div style={{ marginTop: '12px', fontSize: '11px', color: '#8b949e', lineHeight: '1.4' }}>
                  🔒 <strong>Privacy Guarantee:</strong> Your API keys are encrypted client-side in your browser session and transmitted only via direct HTTPS requests to the respective provider.
                </div>
              </div>
            ) : (
              <div style={{ padding: '16px', backgroundColor: '#0d1117', borderRadius: '8px', border: '1px solid #30363d' }}>
                <div style={{ fontSize: '13px', color: '#3fb950', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>🟢</span> Local Offline Mode Ready
                </div>
                <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
                  This engine connects directly to your local Ollama instance on port 11434 with zero external API calls, zero latency delays, and no API billing.
                </p>
                <button
                  type="button"
                  onClick={() => handleTestConnection('local')}
                  style={{
                    marginTop: '12px',
                    padding: '6px 12px',
                    backgroundColor: '#21262d',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    color: '#58a6ff',
                    fontSize: '12px',
                    cursor: 'pointer'
                  }}
                >
                  🧪 Test Local Ollama
                </button>
                {testingStatus['local']?.status === 'valid' && (
                  <span style={{ marginLeft: '10px', fontSize: '12px', color: '#3fb950' }}>🟢 Local Ollama Online!</span>
                )}
              </div>
            )}

          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            padding: '14px 24px',
            backgroundColor: '#0d1117',
            borderTop: '1px solid #30363d',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}
        >
          <div style={{ fontSize: '12px', color: '#3fb950', fontWeight: 'bold' }}>
            {saveMessage}
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 16px',
                backgroundColor: '#21262d',
                border: '1px solid #30363d',
                borderRadius: '6px',
                color: '#c9d1d9',
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveSettings}
              disabled={saving}
              style={{
                padding: '8px 20px',
                backgroundColor: '#238636',
                border: 'none',
                borderRadius: '6px',
                color: '#ffffff',
                fontWeight: 'bold',
                fontSize: '13px',
                cursor: saving ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {saving ? 'Saving...' : '💾 Save & Activate Engine'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
