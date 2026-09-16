import React, { useState, useEffect } from 'react';
import { useAppStore } from './useAppStore.js';
import './CommandCenterTab.css';

const RapidApiReconTab = ({ backendUrl: propBackendUrl }) => {
  const backendUrl = propBackendUrl || import.meta.env.VITE_BACKEND_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '');
  
  const [inputText, setInputText] = useState('');
  const [detectedAction, setDetectedAction] = useState(null);

  const {
    rapidApiIsFetching: isFetching,
    rapidApiResultData: resultData,
    rapidApiError: errorMsg,
    runRapidApiRecon,
    osintVaultItems
  } = useAppStore();

  // All available actions as fallbacks
  const ALL_ACTIONS = [
    { type: 'rapidapi_weather', label: '🌤️ Weather & Geocoding', icon: '🌤️' },
    { type: 'rapidapi_google_trends', label: '📈 Google Trends Bitcoin', icon: '📈' },
    { type: 'rapidapi_google_ads', label: '📢 Google Ads Transparency Center', icon: '📢' },
    { type: 'rapidapi_ebay_feedback', label: '🛒 eBay Seller Feedback & E-Commerce Data', icon: '🛒' },
    { type: 'rapidapi_perplexity', label: '🤖 Perplexity AI Live Search', icon: '🤖' },
    { type: 'rapidapi_math_symbolic', label: '🧮 Math Symbolic Manipulator', icon: '🧮' },
    { type: 'rapidapi_seo_mastermind', label: '🔍 SEO Mastermind Meta Title Generator', icon: '🔍' },
    { type: 'rapidapi_realtor_scraping', label: '🏠 Realtor Agent Scraping & Email Recon', icon: '🏠' },
    { type: 'rapidapi_b2b_leads', label: '🎯 Targeted Local B2B Lead Extractor', icon: '🎯' },
    { type: 'rapidapi_thumbtack', label: '📌 Thumbtack Business Profile Scraper', icon: '📌' },
    { type: 'rapidapi_yellowbot', label: '🟡 Yellowbot Local Business Search', icon: '🟡' },
    { type: 'rapidapi_leadengine', label: '🤖 LeadEngine AI Chatbot Widget Config', icon: '🤖' },
    { type: 'facebook_group_videos', label: 'FB Group Videos', icon: '👥' },
    { type: 'facebook_user_search', label: 'FB User Search', icon: '👤' },
    { type: 'tiktok_oldest_posts', label: 'TikTok Oldest', icon: '🎵' },
    { type: 'yahoo_finance', label: 'Yahoo Finance Quote', icon: '📈' },
    { type: 'crypto_market_data', label: 'Crypto.com Quote', icon: '₿' },
    { type: 'instagram_followings', label: 'IG Followings', icon: '📸' },
    { type: 'subdomain_finder', label: 'Subdomain Finder', icon: '🌐' },
    { type: 'skip_tracing_email', label: 'Skip Tracing (Email)', icon: '📧' },
    { type: 'google_search', label: 'Google Search', icon: '🔍' }
  ];

  // Auto-detect engine
  useEffect(() => {
    const text = inputText.trim();
    if (!text) {
      setDetectedAction(null);
      return;
    }

    let match = null;

    // 1. Facebook Group URL
    const fbGroupMatch = text.match(/facebook\.com\/groups\/(\d+)/i);
    if (fbGroupMatch) {
      match = { taskType: 'facebook_group_videos', target: fbGroupMatch[1], label: `Fetch FB Group Videos: ${fbGroupMatch[1]}` };
    }
    
    // 2. Email Address (Skip Tracing)
    else if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) {
      match = { taskType: 'skip_tracing_email', target: text, label: `Run Skip Tracing on Email: ${text}` };
    }
    
    // 3. Stock Ticker ($AAPL or AAPL)
    else if (/^\$?[A-Za-z]{1,5}$/.test(text) && text.length <= 6) {
      const cleanTicker = text.replace('$', '').toUpperCase();
      match = { taskType: 'yahoo_finance', target: cleanTicker, label: `Get Stock Quote: ${cleanTicker}` };
    }
    
    // 4. Crypto Ticker (BTC_USD)
    else if (/^[A-Za-z]+_[A-Za-z]+$/.test(text)) {
      match = { taskType: 'crypto_market_data', target: text.toUpperCase(), label: `Get Crypto Data: ${text.toUpperCase()}` };
    }
    
    // 5. Domain Name
    else if (/^(?!:\/\/)([a-zA-Z0-9-_]+\.)+[a-zA-Z]{2,11}?$/.test(text)) {
      match = { taskType: 'subdomain_finder', target: text, label: `Find Subdomains for: ${text}` };
    }
    
    // 6. Instagram/TikTok Username (@username)
    else if (text.startsWith('@')) {
      const cleanUsername = text.replace('@', '');
      match = { taskType: 'instagram_followings', target: cleanUsername, label: `Fetch IG Followings: @${cleanUsername}` };
    }

    setDetectedAction(match);
  }, [inputText]);

  const handleFetch = async (taskType, target) => {
    if (!target) {
      useAppStore.setState({ rapidApiError: 'Target cannot be empty.' });
      return;
    }
    await runRapidApiRecon(taskType, target, '');
  };

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h2 style={{ color: '#00f0ff', marginBottom: '8px' }}>🌐 RapidAPI Recon Dashboard</h2>
      <p style={{ color: '#94a3b8', marginBottom: '24px' }}>Smart Paste: Paste a URL, email, domain, or ticker below and the system will auto-detect the OSINT action.</p>

      <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
        <input 
          type="text" 
          value={inputText} 
          onChange={e => setInputText(e.target.value)}
          placeholder="Paste anything here... (e.g. facebook.com/groups/12345, test@example.com, $TSLA, example.com)"
          onKeyDown={e => {
            if (e.key === 'Enter' && detectedAction) {
              handleFetch(detectedAction.taskType, detectedAction.target);
            }
          }}
          style={{ 
            width: '100%', 
            padding: '16px 20px', 
            background: 'rgba(0,0,0,0.6)', 
            border: '2px solid rgba(255,255,255,0.2)', 
            color: 'white', 
            borderRadius: '12px', 
            fontSize: '1.2rem',
            boxSizing: 'border-box',
            marginBottom: '16px',
            outline: 'none',
            transition: 'border-color 0.2s ease'
          }}
          onFocus={(e) => e.target.style.borderColor = '#00f0ff'}
          onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.2)'}
        />

        {detectedAction ? (
          <button 
            onClick={() => handleFetch(detectedAction.taskType, detectedAction.target)}
            disabled={isFetching}
            style={{
              width: '100%',
              padding: '16px',
              background: isFetching ? '#475569' : 'linear-gradient(135deg, #10b981, #059669)',
              border: 'none',
              borderRadius: '8px',
              color: 'white',
              fontWeight: 'bold',
              fontSize: '1.1rem',
              cursor: isFetching ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px'
            }}
          >
            {isFetching ? '⚡ Executing Request...' : `✨ ${detectedAction.label}`}
          </button>
        ) : (
          <div style={{ marginTop: '16px' }}>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: '12px' }}>Or manually run an action on the text above:</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px' }}>
              {ALL_ACTIONS.map(action => (
                <button
                  key={action.type}
                  onClick={() => handleFetch(action.type, inputText.trim())}
                  disabled={isFetching || !inputText.trim()}
                  style={{
                    padding: '12px',
                    background: (isFetching || !inputText.trim()) ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.1)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '8px',
                    color: (isFetching || !inputText.trim()) ? '#64748b' : 'white',
                    cursor: (isFetching || !inputText.trim()) ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    textAlign: 'left'
                  }}
                >
                  <span>{action.icon}</span> {action.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="glass-panel" style={{ flex: 1, overflowY: 'auto', padding: '20px', position: 'relative' }}>
        <h4 style={{ margin: '0 0 16px 0', color: '#f8fafc' }}>Results</h4>
        
        {errorMsg && (
          <div style={{ padding: '12px', background: 'rgba(239,68,68,0.2)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '6px', marginBottom: '16px' }}>
            ⚠ Error: {errorMsg}
          </div>
        )}

        {isFetching && (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px', color: '#94a3b8' }}>
            <div style={{ animation: 'pulse 1.5s infinite' }}>Analyzing target and fetching API...</div>
          </div>
        )}

        {!isFetching && resultData && (
          <div>
            <div style={{ marginBottom: '16px', fontSize: '0.85rem', color: '#38bdf8' }}>
              ✓ Target acquired. Data has been automatically saved to the OSINT Data Vault.
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
              {(() => {
                let itemsToRender = [];
                const res = resultData;
                
                if (res.data && res.data.videos) itemsToRender = res.data.videos;
                else if (res.data && Array.isArray(res.data)) itemsToRender = res.data;
                else if (res.videos) itemsToRender = res.videos;
                else if (res.records && Array.isArray(res.records)) itemsToRender = res.records;
                else if (res.results && Array.isArray(res.results)) itemsToRender = res.results;
                else if (res.result && Array.isArray(res.result)) itemsToRender = res.result;
                else if (res.data) itemsToRender = [res.data];
                else if (res.record) itemsToRender = [res.record];
                else if (res.result) itemsToRender = [res.result];
                else itemsToRender = [res];

                if (itemsToRender.length === 0) return <div style={{ color: '#94a3b8' }}>No visual items to display. See Data Vault for raw output.</div>;
                
                return itemsToRender.map((item, idx) => (
                  <div key={idx} style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', padding: '16px', wordBreak: 'break-word' }}>
                    {Object.entries(item).slice(0, 15).map(([key, val]) => (
                      <div key={key} style={{ marginBottom: '8px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', display: 'block' }}>{key}</span>
                        <span style={{ fontSize: '0.9rem', color: '#e2e8f0' }}>{typeof val === 'object' ? JSON.stringify(val) : String(val).substring(0, 200)}{String(val).length > 200 ? '...' : ''}</span>
                      </div>
                    ))}
                  </div>
                ));
              })()}
            </div>
          </div>
        )}

        {!isFetching && !resultData && !errorMsg && (
          <div style={{ color: '#64748b', fontStyle: 'italic' }}>
            Awaiting input...
          </div>
        )}

        {/* Historical Vault Data */}
        <div style={{ marginTop: '40px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '20px' }}>
          <h4 style={{ margin: '0 0 16px 0', color: '#94a3b8' }}>Saved Recon Data (from Vault)</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '16px' }}>
            {osintVaultItems
              .filter(item => item.category === 'RapidAPI')
              .map(item => (
                <div key={item.id} style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(51, 65, 85, 0.5)', borderRadius: '8px', padding: '16px', wordBreak: 'break-word' }}>
                  <div style={{ marginBottom: '12px', paddingBottom: '8px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <span style={{ fontSize: '0.7rem', color: '#10b981', textTransform: 'uppercase', display: 'block' }}>{item.source}</span>
                    <span style={{ fontSize: '0.7rem', color: '#64748b' }}>{new Date(item.timestamp).toLocaleString()}</span>
                  </div>
                  {item.data ? Object.entries(item.data).slice(0, 10).map(([key, val]) => (
                    <div key={key} style={{ marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase', display: 'block' }}>{key}</span>
                      <span style={{ fontSize: '0.9rem', color: '#cbd5e1' }}>{typeof val === 'object' ? JSON.stringify(val) : String(val).substring(0, 150)}{String(val).length > 150 ? '...' : ''}</span>
                    </div>
                  )) : (
                    <div style={{ color: '#64748b', fontSize: '0.8rem' }}>No structured data found.</div>
                  )}
                </div>
              ))}
            {osintVaultItems.filter(item => item.category === 'RapidAPI').length === 0 && (
              <div style={{ color: '#64748b', fontSize: '0.85rem' }}>No historical data saved yet.</div>
            )}
          </div>
        </div>

        {/* ══════════ VAULTED API CODE SNIPPETS & LLM TRAINING DATASET ══════════ */}
        <div className="glass-panel" style={{ marginTop: '20px', padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h4 style={{ margin: 0, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '8px' }}>
              📚 Vaulted API Code Snippets & LLM Training Dataset
            </h4>
            <span style={{ fontSize: '0.75rem', color: '#34d399', backgroundColor: 'rgba(52, 211, 153, 0.15)', padding: '4px 10px', borderRadius: '6px', border: '1px solid rgba(52, 211, 153, 0.3)' }}>
              ✓ Automatically Synced to AI-BS_Knowledge_Vaults/
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {/* Snippet 1: Reverse Geocoding & Weather */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🌤️ Reverse Geocoding & Weather API</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>geocoding-reverse-geocoding-and-weather.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "io"
    "net/http"
)

func main() {
    url := "https://geocoding-reverse-geocoding-and-weather.p.rapidapi.com/weather?lat=42.9634&lon=-85.6681"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "geocoding-reverse-geocoding-and-weather.p.rapidapi.com")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>

            {/* Snippet 2: Google Trends Keywords */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>📈 Google Trends Keywords API (YouTube Bitcoin Interest)</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>google-trends-keywords-api.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "io"
    "net/http"
)

func main() {
    url := "https://google-trends-keywords-api.p.rapidapi.com/api/googletrends/interest?page=1&limit=50&geo=US&property=youtube&category=finance&q=bitcoin&timeframe=12m"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "google-trends-keywords-api.p.rapidapi.com")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>

            {/* Snippet 3: Google Ads Transparency Center */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>📢 Google Ads Library API Transparency Center</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>google-ads-library-api-transparency-center.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "io"
    "net/http"
)

func main() {
    url := "https://google-ads-library-api-transparency-center.p.rapidapi.com/advertiser?region=US&id=AR16735076323512287233"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "google-ads-library-api-transparency-center.p.rapidapi.com")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 4: Real-Time E-Commerce (eBay Seller Feedback) */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🛒 Real-Time E-Commerce Data API (eBay Seller Feedback)</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>real-time-e-commerce-data.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "io"
    "net/http"
)

func main() {
    url := "https://real-time-e-commerce-data.p.rapidapi.com/ebay/seller-feedback?page=1&seller_id=wireless-source&domain=com&product_id=287062440001"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "real-time-e-commerce-data.p.rapidapi.com")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 5: Perplexity 2 AI Live Web Search */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🤖 Perplexity 2 AI Live Web Search & News API</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>perplexity2.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "strings"
    "net/http"
    "io"
)

func main() {
    url := "https://perplexity2.p.rapidapi.com/"
    payload := strings.NewReader("{\\"content\\":\\"What is todays news in america?\\"}")
    req, _ := http.NewRequest("POST", url, payload)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "perplexity2.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 6: Math Symbolic Expression Manipulator */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🧮 Math Symbolic Expression Manipulator (IsValidExpression)</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>mathematical-symbolic-expression-manipulator.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "net/http"
    "io"
)

func main() {
    url := "https://mathematical-symbolic-expression-manipulator.p.rapidapi.com/IsValidExpression"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "mathematical-symbolic-expression-manipulator.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 7: SEO Mastermind AI Keyword & Meta Title Generator */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🔍 SEO Mastermind AI Keyword & Meta Title Generator</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>seo-mastermind-ai-keyword-meta-title-generator.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "strings"
    "net/http"
    "io"
)

func main() {
    url := "https://seo-mastermind-ai-keyword-meta-title-generator.p.rapidapi.com/seo"
    payload := strings.NewReader("{\"topic\":\"How to lose weight fast\"}")
    req, _ := http.NewRequest("POST", url, payload)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "seo-mastermind-ai-keyword-meta-title-generator.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 8: Realtor Agent Scraping Email */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🏠 Realtor Agent Scraping Email API (Profile ID Search)</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>realtor-agent-scraping-email1.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "net/http"
    "io"
)

func main() {
    url := "https://realtor-agent-scraping-email1.p.rapidapi.com/?profile_id=605ed9640fb522001268bcdc"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "realtor-agent-scraping-email1.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 9: Targeted Local B2B Lead Extractor */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🎯 Targeted Local B2B Lead Extractor API</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>targeted-local-b2b-lead-extractor1.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "net/http"
    "io"
)

func main() {
    url := "https://targeted-local-b2b-lead-extractor1.p.rapidapi.com/v1/leads"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "targeted-local-b2b-lead-extractor1.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    req.Header.Add("keyword", "Dentist")
    req.Header.Add("location", "Austin, TX")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 10: Thumbtack Business Profile Scraper */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>📌 Thumbtack Business Profile Scraper API</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>thumbtack-api.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "strings"
    "net/http"
    "io"
)

func main() {
    url := "https://thumbtack-api.p.rapidapi.com/scrapers/api/thumbtack/business/get-by-url"
    payload := strings.NewReader("{\"url\":\"https://www.thumbtack.com/ca/san-mateo/house-cleaning/micheles-clean-pro/service/527617736799977497\"}")
    req, _ := http.NewRequest("POST", url, payload)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "thumbtack-api.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    fmt.Println(string(body))
}`}</pre>
            </div>
            {/* Snippet 11: Yellowbot Local Business Search */}
            <div style={{ backgroundColor: 'rgba(8, 13, 26, 0.8)', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '10px', padding: '16px' }}>
              <strong style={{ color: '#ffffff', fontSize: '0.9rem', display: 'block', marginBottom: '4px' }}>🟡 Yellowbot Local Business Search API</strong>
              <span style={{ fontSize: '0.72rem', color: '#38bdf8', fontFamily: 'monospace' }}>yellowbot-api.p.rapidapi.com</span>
              <pre style={{ backgroundColor: '#050811', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px', padding: '10px', fontSize: '0.75rem', color: '#34d399', overflowX: 'auto', marginTop: '8px', maxHeight: '160px' }}>{`package main

import (
    "fmt"
    "net/http"
    "io"
)

func main() {
    url := "https://yellowbot-api.p.rapidapi.com/scrapers/api/yellowbot/business/search?page=1&keyword=pizza"
    req, _ := http.NewRequest("GET", url, nil)
    req.Header.Add("x-rapidapi-key", "715331f921msh08fd118bc6cfcdbp1fd3bfjsn995142bec639")
    req.Header.Add("x-rapidapi-host", "yellowbot-api.p.rapidapi.com")
    req.Header.Add("Content-Type", "application/json")
    res, _ := http.DefaultClient.Do(req)
    defer res.Body.Close()
    body, _ := io.ReadAll(res.Body)
    fmt.Println(string(body))
}`}</pre>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default RapidApiReconTab;
