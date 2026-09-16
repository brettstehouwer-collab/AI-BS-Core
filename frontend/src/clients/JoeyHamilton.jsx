import React, { useState, useEffect } from 'react';

export default function JoeyHamilton({ BACKEND_URL: propBackendUrl, backendUrl: propLowerBackendUrl }) {
  const BACKEND_URL = propBackendUrl || propLowerBackendUrl || `${window.location.protocol}//${window.location.hostname}:8000`;
  const [activeTab, setActiveTab] = useState("marketing");
  const [rapidApiKey, setRapidApiKey] = useState("");

  // -- Marketing State --
  const [bulkMarketingLocation, setBulkMarketingLocation] = useState("");
  const [isMarketingLoading, setIsMarketingLoading] = useState(false);
  const [marketingResultsArray, setMarketingResultsArray] = useState([]);
  const [marketingHistory, setMarketingHistory] = useState([]);

  // -- Search State --
  const [searchLocation, setSearchLocation] = useState("Grand Rapids, MI");
  const [isSearchLoading, setIsSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState(null);

  // -- Vault State --
  const [vaultNote, setVaultNote] = useState("");
  const [vaultTags, setVaultTags] = useState("");
  const [isVaultLoading, setIsVaultLoading] = useState(false);
  const [vaultNotes, setVaultNotes] = useState([]);

  // -- Enrichment State --
  const [bulkData, setBulkData] = useState("");
  const [isEnriching, setIsEnriching] = useState(false);
  const [enrichedLeads, setEnrichedLeads] = useState([]);

  // -- Database State --
  const [databaseLocations, setDatabaseLocations] = useState("");
  const [isScraping, setIsScraping] = useState(false);
  const [masterDatabase, setMasterDatabase] = useState([]);

  // -- Telecom State --
  const [leadName, setLeadName] = useState("");
  const [leadPhone, setLeadPhone] = useState("");
  const [propertyInterest, setPropertyInterest] = useState("");
  const [isWhispering, setIsWhispering] = useState(false);

  // -- Reactivation State --
  const [csvContent, setCsvContent] = useState("");
  const [isReactivating, setIsReactivating] = useState(false);
  const [reactivationCampaigns, setReactivationCampaigns] = useState([]);

  // -- Virtual Staging State --
  const [stagingImage, setStagingImage] = useState(null);
  const [stagingStyle, setStagingStyle] = useState("Modern Farmhouse");
  const [stagingRoom, setStagingRoom] = useState("Living Room");
  const [stagingCustomPrompt, setStagingCustomPrompt] = useState("A bright, inviting modern farmhouse living room. A plush, white linen sectional sofa facing the large center window. A rustic natural wood coffee table resting on a subtle, textured cream area rug over the hardwood floors. Minimalist, tasteful decor with a tall potted olive tree in the corner to complement the natural sunlight. High-end, photorealistic 8k architectural photography.");
  const [isStaging, setIsStaging] = useState(false);
  const [stagedResultUrl, setStagedResultUrl] = useState("");
  const [generationMode, setGenerationMode] = useState("Image");
  const [stagedVideoUrl, setStagedVideoUrl] = useState("");
  const [telemetryLogs, setTelemetryLogs] = useState([]);

  // -- Spaces State --
  const [spaces, setSpaces] = useState([
    { id: 1, name: "123 Main St Listing", files: [] },
    { id: 2, name: "Spring Reactivation", files: [] }
  ]);
  const [activeSpaceId, setActiveSpaceId] = useState(1);
  const [newSpaceName, setNewSpaceName] = useState("");

  // -- Directory State --
  const [directorySearch, setDirectorySearch] = useState("");
  const [directoryCategory, setDirectoryCategory] = useState("linkedin");

  useEffect(() => {
    fetchMarketingHistory();
    fetchVaultNotes();
    fetchEnrichedLeads();
    fetchMasterDatabase();
    const savedKey = localStorage.getItem("rapidApiKey");
    if (savedKey) setRapidApiKey(savedKey);

    // Telemetry WebSocket
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const backendHost = BACKEND_URL.replace(/^https?:\/\//, '');
    const ws = new WebSocket(`${wsProtocol}//${backendHost}/ws/telemetry`);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'telemetry') {
          setTelemetryLogs(prev => {
            const next = [...prev, data];
            if (next.length > 50) return next.slice(next.length - 50);
            return next;
          });
        }
      } catch(e){}
    };
    return () => ws.close();
  }, [BACKEND_URL]);

  const fetchMarketingHistory = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/marketing`);
      const data = await res.json();
      if (data.history) setMarketingHistory(data.history);
    } catch (e) {
      console.error("Failed to fetch marketing history", e);
    }
  };

  const fetchVaultNotes = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/secure-memory`);
      const data = await res.json();
      if (data.notes) setVaultNotes(data.notes);
    } catch (e) {
      console.error("Failed to fetch vault notes", e);
    }
  };

  const fetchEnrichedLeads = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/enrich`);
      const data = await res.json();
      if (data.success) setEnrichedLeads(data.leads);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMasterDatabase = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/database/properties`);
      const data = await res.json();
      if (data.success) setMasterDatabase(data.properties);
    } catch (e) {
      console.error(e);
    }
  };

  const generateMarketing = async () => {
    if (!bulkMarketingLocation.trim() || !rapidApiKey.trim()) {
      alert("Please enter a City/Zip and your RapidAPI Key.");
      return;
    }
    
    localStorage.setItem("rapidApiKey", rapidApiKey);
    setIsMarketingLoading(true);
    setMarketingResultsArray([]);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/marketing/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: bulkMarketingLocation, rapid_api_key: rapidApiKey })
      });
      const data = await res.json();
      if (data.success) {
        setMarketingResultsArray(data.bulk_data);
        fetchMarketingHistory();
      } else {
        alert("Failed to generate: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsMarketingLoading(false);
  };

  const runPropertySearch = async () => {
    if (!rapidApiKey.trim() || !searchLocation.trim()) {
      alert("Please enter both a location and your RapidAPI Key.");
      return;
    }
    
    localStorage.setItem("rapidApiKey", rapidApiKey);
    setIsSearchLoading(true);
    setSearchResults(null);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/listings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ location: searchLocation, rapid_api_key: rapidApiKey })
      });
      const data = await res.json();
      if (data.success) {
        setSearchResults(data.properties);
      } else {
        alert("Search failed: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsSearchLoading(false);
  };

  const saveVaultNote = async () => {
    if (!vaultNote.trim()) {
      alert("Please enter a note to save.");
      return;
    }
    
    setIsVaultLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/secure-memory`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: vaultNote, tags: vaultTags })
      });
      const data = await res.json();
      if (data.success) {
        setVaultNote("");
        setVaultTags("");
        fetchVaultNotes();
      } else {
        alert("Failed to save note: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsVaultLoading(false);
  };

  const enrichLead = async () => {
    if (!bulkData.trim() || !rapidApiKey.trim()) {
      alert("Please paste your bulk data (domain, linkedin_url) and provide your RapidAPI Key.");
      return;
    }

    // Parse the CSV-style bulk data
    const lines = bulkData.split('\n');
    const parsedLeads = [];
    for (let line of lines) {
      if (!line.trim()) continue;
      const parts = line.split(',');
      if (parts.length >= 2) {
        parsedLeads.push({
          domain: parts[0].trim(),
          linkedin_url: parts[1].trim()
        });
      }
    }

    if (parsedLeads.length === 0) {
      alert("Could not parse any leads. Make sure you use the format: domain.com, https://linkedin.com/...");
      return;
    }

    localStorage.setItem("rapidApiKey", rapidApiKey);
    setIsEnriching(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/enrich`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          leads: parsedLeads,
          rapid_api_key: rapidApiKey
        })
      });
      const data = await res.json();
      if (data.success) {
        setBulkData("");
        fetchEnrichedLeads();
      } else {
        alert("Bulk Enrichment failed: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsEnriching(false);
  };

  const scrapeDatabase = async () => {
    if (!databaseLocations.trim() || !rapidApiKey.trim()) {
      alert("Please paste locations (cities/zips) and provide your RapidAPI Key.");
      return;
    }

    const locations = databaseLocations.split('\n').filter(l => l.trim().length > 0);
    if (locations.length === 0) return;

    localStorage.setItem("rapidApiKey", rapidApiKey);
    setIsScraping(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/database/scrape`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          locations: locations,
          rapid_api_key: rapidApiKey
        })
      });
      const data = await res.json();
      if (data.success) {
        setDatabaseLocations("");
        alert(`Successfully scraped and saved ${data.saved_count} properties to the Master Database!`);
        fetchMasterDatabase();
      } else {
        alert("Scraping failed: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsScraping(false);
  };

  const triggerCallWhisper = async () => {
    if (!leadName.trim() || !leadPhone.trim()) {
      alert("Please enter at least a name and phone number.");
      return;
    }
    
    setIsWhispering(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/telecom/lead-capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          lead_name: leadName,
          lead_phone: leadPhone,
          property_interest: propertyInterest || "General Inquiry"
        })
      });
      const data = await res.json();
      if (res.ok) {
        alert("Call Whisper Triggered! Check backend terminal for mock Twilio logs.");
        setLeadName("");
        setLeadPhone("");
        setPropertyInterest("");
      } else {
        alert("Failed: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsWhispering(false);
  };

  const handleCsvUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setCsvContent(evt.target.result);
      };
      reader.readAsText(file);
    }
  };

  const runReactivation = async () => {
    if (!csvContent.trim()) {
      alert("Please upload a CSV file or paste CSV content first.");
      return;
    }
    
    setIsReactivating(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/clients/joey_hamilton/reactivation/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv_content: csvContent })
      });
      const data = await res.json();
      if (data.success) {
        setReactivationCampaigns(data.campaigns);
      } else {
        alert("Reactivation failed: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsReactivating(false);
  };

  const handleStagingUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        setStagingImage(evt.target.result);
      };
      reader.readAsDataURL(file); // Needs base64 for API
    }
  };

  const runVirtualStaging = async () => {
    if (!stagingImage) {
      alert("Please upload a photo of an empty room first.");
      return;
    }
    
    setIsStaging(true);
    setStagedResultUrl("");
    setStagedVideoUrl("");
    
    try {
      const endpoint = generationMode === "Video" 
        ? `${backendUrl}/api/clients/joey_hamilton/virtual-staging/video-tour`
        : `${backendUrl}/api/clients/joey_hamilton/virtual-staging/generate`;

      const payload = generationMode === "Video" 
        ? {
            image_base64: stagingImage.split(",")[1] || stagingImage,
            custom_prompt: stagingCustomPrompt
          }
        : { 
            image_base64: stagingImage.split(",")[1] || stagingImage, 
            style: stagingStyle,
            room_type: stagingRoom,
            custom_prompt: stagingCustomPrompt
          };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.success) {
        if (generationMode === "Video") {
          setStagedVideoUrl(data.staged_video_url);
        } else {
          setStagedResultUrl(data.staged_image_url);
        }
      } else {
        alert("Virtual staging failed: " + (data.error || data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("API Error: " + e.message);
    }
    setIsStaging(false);
  };

  const tabStyle = (id) => ({
    padding: '8px 15px',
    cursor: 'pointer',
    backgroundColor: activeTab === id ? '#D4AF37' : '#2a2a35',
    color: activeTab === id ? '#000' : '#fff',
    borderRadius: '4px 4px 0 0',
    fontWeight: 'bold',
    border: 'none',
    fontSize: '13px',
    transition: 'background-color 0.2s',
    marginRight: '2px',
    whiteSpace: 'nowrap'
  });

  return (
    <div style={{ padding: '15px', fontFamily: 'Arial, sans-serif', color: '#333', height: '100%', overflowY: 'auto', backgroundColor: '#f0f2f5', display: 'flex', flexDirection: 'column' }}>
      
      {/* Condensed Brand Header & API Key */}
      <div style={{ backgroundColor: '#1a1a2e', color: '#D4AF37', padding: '10px 15px', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '15px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }}>Joey Hamilton</h1>
          <span style={{ color: '#555', fontSize: '14px' }}>|</span>
          <h3 style={{ margin: 0, fontSize: '14px', color: '#ccc', fontWeight: 'normal' }}>Master CRM Workspace</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
             <span style={{ fontSize: '12px', color: '#999' }}>RapidAPI:</span>
             <input 
              type="password"
              value={rapidApiKey}
              onChange={(e) => setRapidApiKey(e.target.value)}
              placeholder="API Key..."
              style={{ width: '130px', padding: '4px 8px', borderRadius: '4px', border: '1px solid #444', backgroundColor: '#222', color: '#fff', fontSize: '12px' }}
            />
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ display: 'flex', borderBottom: '2px solid #D4AF37', marginBottom: '15px', overflowX: 'auto', flexShrink: 0 }}>
        <button onClick={() => setActiveTab('spaces')} style={tabStyle('spaces')}>Project Spaces</button>
        <button onClick={() => setActiveTab('directory')} style={tabStyle('directory')}>Lead Directory</button>
        <button onClick={() => setActiveTab('marketing')} style={tabStyle('marketing')}>Marketing</button>
        <button onClick={() => setActiveTab('virtual_staging')} style={tabStyle('virtual_staging')}>AI Staging</button>
        <button onClick={() => setActiveTab('database')} style={tabStyle('database')}>Database</button>
        <button onClick={() => setActiveTab('search')} style={tabStyle('search')}>Discovery</button>
        <button onClick={() => setActiveTab('vault')} style={tabStyle('vault')}>Vault</button>
        <button onClick={() => setActiveTab('enrichment')} style={tabStyle('enrichment')}>Enrichment</button>
        <button onClick={() => setActiveTab('reactivation')} style={tabStyle('reactivation')}>Reactivation</button>
        <button onClick={() => setActiveTab('telecom')} style={tabStyle('telecom')}>Telecom</button>
      </div>

      {/* TAB: SPACES (NEW) */}
      {activeTab === 'spaces' && (
        <div style={{ display: 'flex', gap: '15px', flex: 1, minHeight: '500px' }}>
          {/* Sidebar */}
          <div style={{ width: '240px', backgroundColor: '#fff', borderRadius: '6px', padding: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ margin: '0 0 15px 0', fontSize: '14px', color: '#1a1a2e', textTransform: 'uppercase' }}>Workspaces</h3>
            <div style={{ display: 'flex', gap: '5px', marginBottom: '15px' }}>
              <input type="text" value={newSpaceName} onChange={e => setNewSpaceName(e.target.value)} placeholder="New project space..." style={{ flex: 1, padding: '6px 8px', fontSize: '12px', border: '1px solid #ddd', borderRadius: '4px' }} />
              <button onClick={() => { if(newSpaceName) { setSpaces([...spaces, {id: Date.now(), name: newSpaceName, files: []}]); setNewSpaceName(""); } }} style={{ padding: '6px 10px', backgroundColor: '#1a1a2e', color: '#D4AF37', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>+</button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {spaces.map(sp => (
                <div key={sp.id} onClick={() => setActiveSpaceId(sp.id)} style={{ padding: '8px 10px', backgroundColor: activeSpaceId === sp.id ? '#f4f6f8' : 'transparent', borderLeft: activeSpaceId === sp.id ? '3px solid #D4AF37' : '3px solid transparent', cursor: 'pointer', borderRadius: '0 4px 4px 0', marginBottom: '2px', fontSize: '13px', fontWeight: activeSpaceId === sp.id ? 'bold' : 'normal', color: activeSpaceId === sp.id ? '#000' : '#555' }}>
                  📁 {sp.name}
                </div>
              ))}
            </div>
          </div>
          
          {/* Main Work Area */}
          <div style={{ flex: 1, backgroundColor: '#fff', borderRadius: '6px', padding: '15px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', borderBottom: '1px solid #f0f0f0', paddingBottom: '10px' }}>
              <h2 style={{ margin: 0, color: '#1a1a2e', fontSize: '18px' }}>{spaces.find(s => s.id === activeSpaceId)?.name || "Select a Workspace"}</h2>
              <button style={{ padding: '6px 12px', backgroundColor: '#D4AF37', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer', fontSize: '12px', color: '#1a1a2e' }}>Upload File</button>
            </div>
            <div style={{ flex: 1, border: '2px dashed #ddd', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#fafbfc' }}>
               <div style={{ textAlign: 'center', color: '#999' }}>
                 <div style={{ fontSize: '32px', marginBottom: '10px', opacity: 0.5 }}>📥</div>
                 <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#666' }}>Drag & Drop files here</div>
                 <div style={{ fontSize: '12px', marginTop: '5px' }}>Photos, Documents, generated AI Collateral</div>
                 <div style={{ fontSize: '11px', marginTop: '8px', fontStyle: 'italic' }}>Files map directly to local backend: AI-BS/data/joey_spaces/</div>
               </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB: MARKETING */}
      {activeTab === 'marketing' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ flex: '0 0 350px', backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Mass Generate Collateral</h2>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>Enter a city below. The AI will automatically find the newest listings and write Facebook ads, LinkedIn posts, and MLS descriptions for all of them.</p>
            <input 
              type="text" 
              value={bulkMarketingLocation}
              onChange={(e) => setBulkMarketingLocation(e.target.value)}
              placeholder="e.g. Grandville, MI" 
              style={{ width: '100%', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '15px', boxSizing: 'border-box' }} 
            />
            <button 
              onClick={generateMarketing} 
              disabled={isMarketingLoading}
              style={{ width: '100%', padding: '15px', backgroundColor: '#D4AF37', color: '#000', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: isMarketingLoading ? 'wait' : 'pointer' }}
            >
              {isMarketingLoading ? 'Generating Pipeline...' : 'Run Mass Marketing Pipeline'}
            </button>
            {isMarketingLoading && <p style={{fontSize: '12px', color: '#d35400', marginTop: '10px', textAlign: 'center'}}>Discovering properties and running AI LLM... This may take a minute.</p>}

            <h3 style={{ marginTop: '30px', borderTop: '1px solid #eee', paddingTop: '15px' }}>Campaign History</h3>
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {marketingHistory.length === 0 ? <p style={{ color: '#999', fontSize: '14px' }}>No campaigns yet.</p> : marketingHistory.map((item, idx) => (
                <div key={idx} style={{ padding: '10px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{item.property_address}</div>
                  <div style={{ fontSize: '12px', color: '#999' }}>{new Date(item.created_at * 1000).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', maxHeight: '800px', paddingRight: '10px' }}>
            {marketingResultsArray.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {marketingResultsArray.map((campaign, idx) => (
                  <div key={idx} style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                    <h2 style={{ margin: '0 0 5px 0' }}>{campaign.property_address}</h2>
                    <a href={campaign.zillow_url} target="_blank" rel="noreferrer" style={{ display: 'inline-block', marginBottom: '15px', fontSize: '12px', color: '#D4AF37', textDecoration: 'none', fontWeight: 'bold' }}>View Property on Zillow</a>
                    
                    <h3 style={{ fontSize: '14px', marginBottom: '5px', color: '#1a1a2e' }}>Zillow / MLS Description</h3>
                    <div style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '5px', fontSize: '14px', whiteSpace: 'pre-wrap', marginBottom: '20px', borderLeft: '3px solid #1a1a2e' }}>
                      {campaign.results.zillow}
                    </div>

                    <h3 style={{ fontSize: '14px', marginBottom: '5px', color: '#1877F2' }}>Facebook Ad</h3>
                    <div style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '5px', fontSize: '14px', whiteSpace: 'pre-wrap', marginBottom: '20px', borderLeft: '3px solid #1877F2' }}>
                      {campaign.results.facebook}
                    </div>

                    <h3 style={{ fontSize: '14px', marginBottom: '5px', color: '#0077B5' }}>LinkedIn Investor Post</h3>
                    <div style={{ backgroundColor: '#f9f9f9', padding: '15px', borderRadius: '5px', fontSize: '14px', whiteSpace: 'pre-wrap', borderLeft: '3px solid #0077B5' }}>
                      {campaign.results.linkedin}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ backgroundColor: '#fff', padding: '40px', borderRadius: '10px', textAlign: 'center', color: '#999', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
                Results will appear here.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: SEARCH */}
      {activeTab === 'search' && (
        <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
          <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Property Discovery Pipeline</h2>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
            <input 
              type="text" 
              value={searchLocation}
              onChange={(e) => setSearchLocation(e.target.value)}
              placeholder="e.g. Grandville, MI" 
              style={{ flex: 1, padding: '12px', borderRadius: '5px', border: '1px solid #ccc' }} 
            />
            <button 
              onClick={runPropertySearch} 
              disabled={isSearchLoading}
              style={{ padding: '12px 30px', backgroundColor: '#1a1a2e', color: '#D4AF37', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: isSearchLoading ? 'wait' : 'pointer' }}
            >
              {isSearchLoading ? 'Searching...' : 'Search MLS'}
            </button>
          </div>

          {searchResults && (
            <div>
              <h3 style={{ borderBottom: '2px solid #f0f0f0', paddingBottom: '10px' }}>Found {searchResults.length} active listings</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px', marginTop: '20px' }}>
                {searchResults.map((prop, idx) => (
                  <div key={idx} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '15px', backgroundColor: '#fafafa', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ fontWeight: 'bold', fontSize: '16px', marginBottom: '10px', color: '#1a1a2e' }}>
                      {prop.address || "Unknown Address"}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '14px' }}>
                      <span style={{ color: '#27ae60', fontWeight: 'bold' }}>{prop.price ? `$${prop.price.toLocaleString()}` : "Price N/A"}</span>
                      <span>{prop.status}</span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '15px' }}>
                      {prop.beds} Beds • {prop.baths} Baths • {prop.sqft} SqFt <br/>
                      {prop.propertyType}
                    </div>
                    <div style={{ marginTop: 'auto' }}>
                      <a href={prop.zillow_url} target="_blank" rel="noreferrer" style={{ display: 'block', textAlign: 'center', backgroundColor: '#e9ecef', color: '#333', padding: '8px', borderRadius: '4px', textDecoration: 'none', fontSize: '13px', fontWeight: 'bold' }}>
                        View on Zillow
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB: VAULT */}
      {activeTab === 'vault' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#27ae60', borderRadius: '50%', boxShadow: '0 0 5px #27ae60' }}></div>
              <h2 style={{ margin: 0, color: '#1a1a2e' }}>Secure Client Vault (ChromaDB)</h2>
            </div>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
              Notes and preferences saved here are stored in an isolated, encrypted vector database exclusively for Joey Hamilton.
            </p>
            
            <textarea 
              value={vaultNote}
              onChange={(e) => setVaultNote(e.target.value)}
              placeholder="Enter secure client note, lead details, or preferences..." 
              style={{ width: '100%', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '10px', height: '120px', resize: 'vertical', boxSizing: 'border-box' }} 
            />
            <input 
              type="text" 
              value={vaultTags}
              onChange={(e) => setVaultTags(e.target.value)}
              placeholder="Tags (e.g., lead, budget, urgent)" 
              style={{ width: '100%', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '15px', boxSizing: 'border-box' }} 
            />
            <button 
              onClick={saveVaultNote} 
              disabled={isVaultLoading}
              style={{ padding: '12px 30px', backgroundColor: '#27ae60', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: isVaultLoading ? 'wait' : 'pointer' }}
            >
              {isVaultLoading ? 'Encrypting...' : 'Save to Secure Vault'}
            </button>
          </div>

          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
             <h3 style={{ margin: '0 0 15px 0' }}>Stored Memories</h3>
             <div style={{ flex: 1, overflowY: 'auto', maxHeight: '400px', paddingRight: '10px' }}>
               {vaultNotes.length === 0 ? <p style={{ color: '#999' }}>No secure notes saved.</p> : vaultNotes.map((note, idx) => (
                 <div key={idx} style={{ backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '8px', marginBottom: '15px', borderLeft: '4px solid #27ae60' }}>
                   <div style={{ fontSize: '14px', whiteSpace: 'pre-wrap', marginBottom: '10px' }}>{note.note}</div>
                   <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                     <span style={{ color: '#999' }}>{note.metadata?.tags ? `Tags: ${note.metadata.tags}` : 'No tags'}</span>
                     <span style={{ color: '#ccc' }}>{note.metadata?.timestamp ? new Date(note.metadata.timestamp * 1000).toLocaleString() : ''}</span>
                   </div>
                 </div>
               ))}
             </div>
          </div>
        </div>
      )}

      {/* TAB: ENRICHMENT */}
      {activeTab === 'enrichment' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Form Side */}
          <div style={{ flex: '0 0 350px', backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Bulk Data Pull</h2>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>Paste a mass list of domains and LinkedIn URLs. The engine will automatically extract names, logos, and activity.</p>
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>Format (One per line):</p>
            <p style={{ fontSize: '11px', color: '#999', margin: '0 0 10px 0', fontStyle: 'italic' }}>apple.com, https://linkedin.com/in/elsa...</p>

            <textarea 
              value={bulkData} onChange={(e) => setBulkData(e.target.value)}
              placeholder="apple.com, https://www.linkedin.com/in/elsa-jaubert-bb726b134/&#10;microsoft.com, https://www.linkedin.com/in/williamhgates/" 
              style={{ width: '100%', height: '150px', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '15px', boxSizing: 'border-box', fontFamily: 'monospace', whiteSpace: 'pre' }} 
            />
            <button 
              onClick={enrichLead} disabled={isEnriching}
              style={{ width: '100%', padding: '12px', backgroundColor: '#0077B5', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: isEnriching ? 'wait' : 'pointer' }}
            >
              {isEnriching ? 'Running Mass Data Pull...' : 'Run Bulk Pipeline'}
            </button>
            {isEnriching && <p style={{fontSize: '12px', color: '#d35400', marginTop: '10px', textAlign: 'center'}}>Extracting data (respecting API limits)... Please wait.</p>}
          </div>

          {/* Database Viewer Side */}
          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflowY: 'auto', maxHeight: '800px' }}>
            <h2 style={{ margin: '0 0 15px 0' }}>Enriched Leads Database</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', maxHeight: '600px', paddingRight: '10px' }}>
              {enrichedLeads.length === 0 ? <p style={{ color: '#999' }}>No leads enriched yet.</p> : enrichedLeads.map((lead, idx) => (
                <div key={idx} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '20px', backgroundColor: '#fafafa' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '15px', borderBottom: '1px solid #eee', paddingBottom: '15px' }}>
                    {lead.logo_url && (
                      <img src={lead.logo_url} alt="Logo" style={{ width: '60px', height: '60px', objectFit: 'contain', borderRadius: '8px', backgroundColor: '#fff', padding: '5px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }} />
                    )}
                    <div>
                      <h3 style={{ margin: 0, color: '#1a1a2e', fontSize: '20px' }}>{lead.name}</h3>
                      <div style={{ color: '#666', fontSize: '14px' }}>{lead.domain}</div>
                      <a href={lead.linkedin_url} target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: '#0077B5', textDecoration: 'none', fontWeight: 'bold' }}>View LinkedIn Profile</a>
                    </div>
                  </div>
                  
                  <div>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '14px', color: '#333' }}>Recent LinkedIn Activity:</h4>
                    {lead.comments && lead.comments.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {lead.comments.slice(0, 3).map((comment, cidx) => (
                          <div key={cidx} style={{ backgroundColor: '#fff', padding: '12px', borderRadius: '6px', fontSize: '13px', borderLeft: '3px solid #0077B5', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                            <div style={{ fontStyle: 'italic', color: '#444' }}>"{comment.comment || "Comment text..."}"</div>
                            <div style={{ marginTop: '8px', fontSize: '11px', color: '#999', display: 'flex', justifyContent: 'space-between' }}>
                              <span>{comment.timestamp || "Recent"}</span>
                              {comment.post_url && <a href={comment.post_url} target="_blank" rel="noreferrer" style={{ color: '#0077B5' }}>View Post</a>}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ fontSize: '13px', color: '#999', fontStyle: 'italic' }}>No recent activity found.</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB: DATABASE */}
      {activeTab === 'database' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Scraper Side */}
          <div style={{ flex: '0 0 350px', backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Mass Data Scraper</h2>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>Paste a list of zip codes or cities. The engine will download massive blocks of properties into the local SQLite database.</p>
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>Format (One per line):</p>
            <textarea 
              value={databaseLocations} onChange={(e) => setDatabaseLocations(e.target.value)}
              placeholder="Grand Rapids, MI&#10;Wyoming, MI&#10;49503" 
              style={{ width: '100%', height: '150px', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '15px', boxSizing: 'border-box', fontFamily: 'monospace', whiteSpace: 'pre' }} 
            />
            <button 
              onClick={scrapeDatabase} disabled={isScraping}
              style={{ width: '100%', padding: '12px', backgroundColor: '#0077B5', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: isScraping ? 'wait' : 'pointer' }}
            >
              {isScraping ? 'Scraping Market...' : 'Run Mass Scraper'}
            </button>
            {isScraping && <p style={{fontSize: '12px', color: '#d35400', marginTop: '10px', textAlign: 'center'}}>Downloading hundreds of properties... Please wait.</p>}
          </div>

          {/* Database Viewer Side */}
          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflowY: 'auto', maxHeight: '800px' }}>
            <h2 style={{ margin: '0 0 15px 0' }}>West Michigan Master Database</h2>
            <p style={{ fontSize: '12px', color: '#666', marginBottom: '20px' }}>Total Saved Properties: {masterDatabase.length}</p>
            
            {masterDatabase.length === 0 ? (
              <p style={{ color: '#999' }}>No properties in database. Run the Mass Data Scraper.</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #eee' }}>
                      <th style={{ padding: '10px' }}>Address</th>
                      <th style={{ padding: '10px' }}>Price</th>
                      <th style={{ padding: '10px' }}>Beds/Baths</th>
                      <th style={{ padding: '10px' }}>Status</th>
                      <th style={{ padding: '10px' }}>Agent</th>
                      <th style={{ padding: '10px' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {masterDatabase.map((prop, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{ padding: '10px', fontWeight: 'bold' }}>
                          <a href={prop.zillowUrl} target="_blank" rel="noreferrer" style={{color: '#1a1a2e', textDecoration: 'none'}}>{prop.address}</a>
                        </td>
                        <td style={{ padding: '10px' }}>${prop.price?.toLocaleString()}</td>
                        <td style={{ padding: '10px' }}>{prop.bedrooms} / {prop.bathrooms}</td>
                        <td style={{ padding: '10px' }}>{prop.listingStatus}</td>
                        <td style={{ padding: '10px', fontStyle: 'italic' }}>{prop.agentName}</td>
                        <td style={{ padding: '10px' }}>
                          <button 
                            onClick={() => {
                              setActiveTab('marketing');
                              setBulkMarketingLocation(prop.address); 
                            }}
                            style={{ padding: '5px 10px', backgroundColor: '#D4AF37', border: 'none', borderRadius: '3px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px' }}>
                            Generate Marketing
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: TELECOM */}
      {activeTab === 'telecom' && (
        <div style={{ display: 'flex', gap: '20px', justifyContent: 'center' }}>
          <div style={{ flex: '0 0 450px', backgroundColor: '#fff', padding: '30px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
              <div style={{ width: '12px', height: '12px', backgroundColor: '#e74c3c', borderRadius: '50%', boxShadow: '0 0 5px #e74c3c', animation: isWhispering ? 'pulse 1s infinite' : 'none' }}></div>
              <h2 style={{ margin: 0, color: '#1a1a2e' }}>Call Whisper Simulator</h2>
            </div>
            
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>
              Simulate a lead submitting a form on Joe's website. This will trigger the backend Twilio integration to speed-dial Joe and brief him.
            </p>
            
            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '5px' }}>Lead Name</label>
              <input type="text" value={leadName} onChange={(e) => setLeadName(e.target.value)} placeholder="e.g. David Smith" style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ccc', boxSizing: 'border-box' }} />
            </div>

            <div style={{ marginBottom: '15px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '5px' }}>Lead Phone Number</label>
              <input type="text" value={leadPhone} onChange={(e) => setLeadPhone(e.target.value)} placeholder="e.g. 555-0199" style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ccc', boxSizing: 'border-box' }} />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '5px' }}>Property of Interest</label>
              <input type="text" value={propertyInterest} onChange={(e) => setPropertyInterest(e.target.value)} placeholder="e.g. 20 Acres Vacant Land" style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ccc', boxSizing: 'border-box' }} />
            </div>

            <button 
              onClick={triggerCallWhisper} disabled={isWhispering}
              style={{ width: '100%', padding: '15px', backgroundColor: '#e74c3c', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: isWhispering ? 'wait' : 'pointer', boxShadow: '0 4px 6px rgba(231, 76, 60, 0.3)' }}
            >
              {isWhispering ? 'Routing Call to Joe...' : 'Submit Lead & Trigger Whisper'}
            </button>
          </div>
        </div>
      )}

      {/* TAB: REACTIVATION */}
      {activeTab === 'reactivation' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Form Side */}
          <div style={{ flex: '0 0 350px', backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Past Client Reactivation</h2>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>Upload a CSV of your past clients. The AI will find ripe targets and generate personalized SMS messages to pull referral listings out of thin air.</p>
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>Upload CSV File:</p>
            <input type="file" accept=".csv" onChange={handleCsvUpload} style={{ marginBottom: '15px' }} />
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>Or Paste CSV Content:</p>
            <textarea 
              value={csvContent} onChange={(e) => setCsvContent(e.target.value)}
              placeholder="Name, Phone, Email, PurchaseDate, PurchasePrice&#10;David Smith, 555-0199, david@test.com, 2018-05-12, $250000" 
              style={{ width: '100%', height: '100px', padding: '12px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '15px', boxSizing: 'border-box', fontFamily: 'monospace', whiteSpace: 'pre', fontSize: '11px' }} 
            />
            <button 
              onClick={runReactivation} disabled={isReactivating}
              style={{ width: '100%', padding: '12px', backgroundColor: '#D4AF37', color: '#000', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: isReactivating ? 'wait' : 'pointer' }}
            >
              {isReactivating ? 'Running AI Engine...' : 'Run Reactivation Engine'}
            </button>
            {isReactivating && <p style={{fontSize: '12px', color: '#d35400', marginTop: '10px', textAlign: 'center'}}>Analyzing CSV and generating LLM texts...</p>}
          </div>

          {/* Results Viewer Side */}
          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', overflowY: 'auto', maxHeight: '800px' }}>
            <h2 style={{ margin: '0 0 15px 0' }}>Generated Campaigns</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', overflowY: 'auto', maxHeight: '700px', paddingRight: '10px' }}>
              {reactivationCampaigns.length === 0 ? <p style={{ color: '#999' }}>Upload a CSV and run the engine to see generated SMS campaigns.</p> : reactivationCampaigns.map((camp, idx) => (
                <div key={idx} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '20px', backgroundColor: '#fafafa' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
                    <div>
                      <h3 style={{ margin: 0, color: '#1a1a2e', fontSize: '18px' }}>{camp.name}</h3>
                      <div style={{ color: '#666', fontSize: '13px' }}>{camp.phone} • Bought: {camp.purchase_date}</div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 style={{ margin: '0 0 10px 0', fontSize: '12px', color: '#333', textTransform: 'uppercase' }}>AI Generated SMS:</h4>
                    <div style={{ backgroundColor: '#e8f4f8', padding: '15px', borderRadius: '15px 15px 15px 0', fontSize: '14px', color: '#1a1a2e', borderLeft: '4px solid #3498db', whiteSpace: 'pre-wrap', marginBottom: '15px' }}>
                      {camp.sms_generated}
                    </div>
                    
                    <button style={{ padding: '8px 15px', backgroundColor: '#27ae60', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}>
                      Send via Twilio
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB: VIRTUAL STAGING */}
      {activeTab === 'virtual_staging' && (
        <div style={{ display: 'flex', gap: '20px' }}>
          {/* Controls Side */}
          <div style={{ flex: '0 0 350px', backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)' }}>
            <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>AI Virtual Staging</h2>
            <p style={{ fontSize: '14px', color: '#666', marginBottom: '20px' }}>Upload a photo of a vacant room. The AI will instantly furnish and decorate it in your chosen style to maximize buyer interest.</p>
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>1. Upload Empty Room Photo:</p>
            <input type="file" accept="image/*" onChange={handleStagingUpload} style={{ marginBottom: '20px' }} />
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>2. Select Output Type:</p>
            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
              <button 
                onClick={() => setGenerationMode("Image")}
                style={{ flex: 1, padding: '10px', backgroundColor: generationMode === "Image" ? '#1a1a2e' : '#eee', color: generationMode === "Image" ? '#fff' : '#333', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}>
                Still Image
              </button>
              <button 
                onClick={() => setGenerationMode("Video")}
                style={{ flex: 1, padding: '10px', backgroundColor: generationMode === "Video" ? '#1a1a2e' : '#eee', color: generationMode === "Video" ? '#fff' : '#333', border: '1px solid #ccc', borderRadius: '5px', cursor: 'pointer', fontWeight: 'bold' }}>
                Video Tour
              </button>
            </div>
            
            {generationMode === "Image" && (
              <>
                <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>3. Select Room Type:</p>
                <select value={stagingRoom} onChange={(e) => setStagingRoom(e.target.value)} style={{ width: '100%', padding: '10px', marginBottom: '20px', borderRadius: '5px', border: '1px solid #ccc' }}>
                  <option value="Living Room">Living Room</option>
                  <option value="Master Bedroom">Master Bedroom</option>
                  <option value="Dining Room">Dining Room</option>
                  <option value="Home Office">Home Office</option>
                </select>
                
                <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>4. Select Furniture Style:</p>
                <select value={stagingStyle} onChange={(e) => setStagingStyle(e.target.value)} style={{ width: '100%', padding: '10px', marginBottom: '20px', borderRadius: '5px', border: '1px solid #ccc' }}>
                  <option value="Modern Farmhouse">Modern Farmhouse</option>
                  <option value="Mid-Century Modern">Mid-Century Modern</option>
                  <option value="Contemporary Minimalist">Contemporary Minimalist</option>
                  <option value="Traditional Elegance">Traditional Elegance</option>
                </select>
              </>
            )}
            
            <p style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 5px 0' }}>{generationMode === "Image" ? "5." : "3."} Custom Description (Optional):</p>
            <textarea 
              value={stagingCustomPrompt} onChange={(e) => setStagingCustomPrompt(e.target.value)}
              placeholder={generationMode === "Image" ? "e.g. Add a red velvet couch, lots of plants..." : "e.g. Cinematic slow pan around a modern farmhouse living room..."} 
              style={{ width: '100%', height: '60px', padding: '10px', borderRadius: '5px', border: '1px solid #ccc', marginBottom: '25px', boxSizing: 'border-box', fontFamily: 'inherit', resize: 'vertical' }} 
            />
            
            <button 
              onClick={runVirtualStaging} disabled={isStaging || !stagingImage}
              style={{ width: '100%', padding: '12px', backgroundColor: (isStaging || !stagingImage) ? '#ccc' : '#D4AF37', color: (isStaging || !stagingImage) ? '#666' : '#000', border: 'none', borderRadius: '5px', fontWeight: 'bold', fontSize: '16px', cursor: (isStaging || !stagingImage) ? 'not-allowed' : 'pointer' }}
            >
              {isStaging ? (generationMode === "Video" ? 'Rendering Video (This takes a while)...' : 'AI is Furnishing...') : (generationMode === "Video" ? 'Generate Video Tour' : 'Generate Staged Photo')}
            </button>
            {isStaging && <p style={{fontSize: '12px', color: '#d35400', marginTop: '10px', textAlign: 'center'}}>{generationMode === "Video" ? "Using Wan2.2 14B Image-to-Video Engine..." : "Analyzing room geometry and rendering 3D furniture..."}</p>}
          </div>

          {/* Viewer Side */}
          <div style={{ flex: 1, backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', display: 'flex', flexDirection: 'column' }}>
            <h2 style={{ margin: '0 0 15px 0' }}>Staging Results</h2>
            <div style={{ flex: 1, display: 'flex', gap: '20px' }}>
              {/* Before */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '10px', textAlign: 'center' }}>BEFORE (Vacant)</h3>
                <div style={{ flex: 1, backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px dashed #ccc', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                  {stagingImage ? (
                    <img src={stagingImage?.startsWith('http') || stagingImage?.startsWith('data:') || stagingImage?.startsWith('blob:') ? stagingImage : `${BACKEND_URL}${stagingImage?.startsWith('/') ? '' : '/'}${stagingImage}`} alt="Empty Room" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                  ) : (
                    <span style={{ color: '#aaa' }}>No image uploaded</span>
                  )}
                </div>
              </div>
              
              {/* After */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ fontSize: '14px', color: '#666', marginBottom: '10px', textAlign: 'center' }}>AFTER (AI Generated)</h3>
                <div style={{ flex: 1, backgroundColor: '#f5f5f5', borderRadius: '8px', border: '1px dashed #ccc', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', position: 'relative' }}>
                  {stagedVideoUrl ? (
                    <video src={stagedVideoUrl?.startsWith('http') || stagedVideoUrl?.startsWith('data:') || stagedVideoUrl?.startsWith('blob:') ? stagedVideoUrl : `${BACKEND_URL}${stagedVideoUrl?.startsWith('/') ? '' : '/'}${stagedVideoUrl}`} controls autoPlay loop style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                  ) : stagedResultUrl ? (
                    <img src={stagedResultUrl?.startsWith('http') || stagedResultUrl?.startsWith('data:') || stagedResultUrl?.startsWith('blob:') ? stagedResultUrl : `${BACKEND_URL}${stagedResultUrl?.startsWith('/') ? '' : '/'}${stagedResultUrl}`} alt="Staged Room" style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                  ) : isStaging ? (
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                      <div className="spinner" style={{ width: '40px', height: '40px', border: '4px solid #f3f3f3', borderTop: '4px solid #D4AF37', borderRadius: '50%', animation: 'spin 1s linear infinite', marginBottom: '10px' }}></div>
                      <span style={{ color: '#D4AF37', fontWeight: 'bold' }}>{generationMode === "Video" ? "Synthesizing Video..." : "Rendering..."}</span>
                      <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
                    </div>
                  ) : (
                    <span style={{ color: '#aaa' }}>Awaiting generation</span>
                  )}
                </div>
              </div>
            </div>
            
            {/* Live Telemetry Overlay */}
            {isStaging && (
              <div style={{ marginTop: '20px', backgroundColor: '#000', padding: '15px', borderRadius: '8px', border: '1px solid #333', color: '#0f0', fontFamily: 'monospace', fontSize: '11px', maxHeight: '150px', overflowY: 'auto' }}>
                <div style={{ color: '#fff', borderBottom: '1px solid #333', paddingBottom: '5px', marginBottom: '10px', fontWeight: 'bold' }}>LIVE SYSTEM TELEMETRY</div>
                {telemetryLogs.map((log, idx) => (
                  <div key={idx} style={{ marginBottom: '4px' }}>
                    <span style={{ color: '#888' }}>[{new Date(log.timestamp).toLocaleTimeString()}]</span> 
                    <span style={{ color: '#fff', marginLeft: '5px' }}>{log.agent}:</span> 
                    <span style={{ marginLeft: '5px' }}>{log.details}</span>
                  </div>
                ))}
                {telemetryLogs.length === 0 && <div style={{ color: '#888' }}>Awaiting pipeline hooks...</div>}
              </div>
            )}

            {(stagedResultUrl || stagedVideoUrl) && (
               <div style={{ marginTop: '20px', textAlign: 'center' }}>
                 <button style={{ padding: '10px 20px', backgroundColor: '#2c3e50', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer', marginRight: '10px' }}>
                   Download High-Res
                 </button>
                 <button style={{ padding: '10px 20px', backgroundColor: '#27ae60', color: '#fff', border: 'none', borderRadius: '5px', fontWeight: 'bold', cursor: 'pointer' }}>
                   Push to MLS / Zillow
                 </button>
               </div>
            )}
          </div>
        </div>
      )}

      {/* TAB: DIRECTORY */}
      {activeTab === 'directory' && (
        <div style={{ backgroundColor: '#fff', padding: '20px', borderRadius: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)', flex: 1, display: 'flex', flexDirection: 'column', minHeight: '500px' }}>
          <h2 style={{ margin: '0 0 15px 0', color: '#1a1a2e' }}>Lead Directory</h2>
          
          <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', backgroundColor: '#eee', borderRadius: '5px', overflow: 'hidden' }}>
              <button 
                onClick={() => setDirectoryCategory('linkedin')}
                style={{ padding: '10px 20px', border: 'none', backgroundColor: directoryCategory === 'linkedin' ? '#0077b5' : 'transparent', color: directoryCategory === 'linkedin' ? '#fff' : '#555', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Enriched LinkedIn Leads ({enrichedLeads.length})
              </button>
              <button 
                onClick={() => setDirectoryCategory('zillow')}
                style={{ padding: '10px 20px', border: 'none', backgroundColor: directoryCategory === 'zillow' ? '#006aff' : 'transparent', color: directoryCategory === 'zillow' ? '#fff' : '#555', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Zillow Agent Leads ({masterDatabase.length})
              </button>
            </div>
            
            <input 
              type="text" 
              value={directorySearch}
              onChange={(e) => setDirectorySearch(e.target.value)}
              placeholder="Search leads by name, domain, or address..." 
              style={{ flex: 1, padding: '10px', borderRadius: '5px', border: '1px solid #ccc', boxSizing: 'border-box' }} 
            />
          </div>

          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '10px' }}>
            {directoryCategory === 'linkedin' ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' }}>
                {enrichedLeads.filter(l => (l.name || '').toLowerCase().includes(directorySearch.toLowerCase()) || (l.domain || '').toLowerCase().includes(directorySearch.toLowerCase())).map(lead => (
                  <div key={lead.id} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '15px', backgroundColor: '#fafafa', boxShadow: '0 1px 3px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '15px', borderBottom: '1px solid #eee', paddingBottom: '10px' }}>
                      {lead.logo_url ? <img src={lead.logo_url} alt="Logo" style={{ width: '40px', height: '40px', borderRadius: '4px' }} /> : <div style={{ width: '40px', height: '40px', backgroundColor: '#ccc', borderRadius: '4px' }}></div>}
                      <div>
                        <h3 style={{ margin: 0, fontSize: '16px', color: '#1a1a2e' }}>{lead.name}</h3>
                        <a href={lead.linkedin_url} target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: '#0077b5', textDecoration: 'none', fontWeight: 'bold' }}>{lead.domain}</a>
                      </div>
                    </div>
                    <div style={{ flex: 1 }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '12px', color: '#666', textTransform: 'uppercase' }}>Recent Activity & Comments</h4>
                      {lead.comments && lead.comments.length > 0 ? lead.comments.slice(0,2).map((c, i) => (
                         <div key={i} style={{ backgroundColor: '#fff', borderLeft: '3px solid #D4AF37', padding: '10px', marginBottom: '10px', fontSize: '12px', color: '#444' }}>
                           <span style={{ fontStyle: 'italic' }}>"{c.comment}"</span>
                           <div style={{ marginTop: '5px', textAlign: 'right' }}><a href={c.post_url} target="_blank" rel="noreferrer" style={{ color: '#0077b5', textDecoration: 'none' }}>View Post</a></div>
                         </div>
                      )) : <p style={{ fontSize: '12px', color: '#999', fontStyle: 'italic' }}>No recent comments found.</p>}
                    </div>
                    <button style={{ width: '100%', padding: '10px', backgroundColor: '#D4AF37', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer', marginTop: '15px' }}>
                      Generate Icebreaker Email
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {masterDatabase.filter(p => (p.agentName || '').toLowerCase().includes(directorySearch.toLowerCase()) || (p.address || '').toLowerCase().includes(directorySearch.toLowerCase())).map((prop, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: '#fff', padding: '15px', borderRadius: '5px', border: '1px solid #eee', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '16px', color: '#1a1a2e' }}>{prop.agentName || "Unknown Agent"}</h3>
                      <div style={{ fontSize: '13px', color: '#666', marginTop: '5px' }}>{prop.address}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 'bold', color: '#27ae60', fontSize: '16px' }}>${prop.price?.toLocaleString()}</div>
                      <a href={prop.zillowUrl} target="_blank" rel="noreferrer" style={{ fontSize: '12px', color: '#006aff', textDecoration: 'none', display: 'inline-block', marginTop: '5px' }}>View Zillow</a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
