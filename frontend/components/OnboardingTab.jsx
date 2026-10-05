import React, { useState, useEffect } from 'react';
import { collection, addDoc, onSnapshot, query, orderBy, limit } from 'firebase/firestore';
import { db } from '../firebase';
import { 
  FileText, Send, User, Briefcase, Target, Database, CheckCircle, 
  Clock, Shield, Sparkles, Building, Layers, ArrowRight, Zap, RefreshCw
} from 'lucide-react';

const TIER_OPTIONS = [
  { id: 'starter', name: 'Phase 1 MVP', desc: 'Fast MVP Prototype & Architecture Audit', price: '$2,500' },
  { id: 'growth', name: 'Autonomous Pipeline', desc: 'Full AI-BS Autonomous Agent Swarm Integration', price: '$7,500' },
  { id: 'enterprise', name: 'Sovereign Cluster', desc: 'Dedicated Local RTX 4090 GPU & Tailscale Node', price: '$15,000' }
];

export default function OnboardingTab() {
  const [formData, setFormData] = useState({
    clientName: '',
    companyName: '',
    email: '',
    tier: 'growth',
    primaryObjective: '',
    techStack: 'Python / React / FastAPI',
    deploymentPreference: 'Firebase Hosting + Cloudflare Workers',
    slaRequirements: '24/7 Agent Monitoring'
  });
  const [status, setStatus] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [recentClients, setRecentClients] = useState([]);

  useEffect(() => {
    try {
      const q = query(collection(db, 'clients'), orderBy('createdAt', 'desc'), limit(5));
      const unsub = onSnapshot(q, (snapshot) => {
        const list = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
        setRecentClients(list);
      }, (err) => console.warn('Clients listener fallback', err));
      return () => unsub();
    } catch (e) {
      console.warn('Clients init error', e);
    }
  }, []);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleApplyTemplate = (type) => {
    if (type === 'ai_pipeline') {
      setFormData({
        clientName: 'Sarah Jenkins',
        companyName: 'Apex Media Dynamics',
        email: 'sarah@apexmediadynamics.com',
        tier: 'growth',
        primaryObjective: 'Automate 4K video rendering and Demucs audio stem separation via local RTX 4090 ComfyUI engine.',
        techStack: 'Python / PyTorch / ComfyUI / React',
        deploymentPreference: 'Local Workstation + Cloudflare Tunnel',
        slaRequirements: '< 2min Turnaround on Shorts'
      });
    } else if (type === 'hospitality') {
      setFormData({
        clientName: 'Marcus Bell',
        companyName: 'Notō Restaurant Group',
        email: 'marcus@notobar.com',
        tier: 'enterprise',
        primaryObjective: 'Deploy multi-bar stock replenishment, real-time barback dispatch, and MLCC distributor order automation.',
        techStack: 'FastAPI / SQLite / React / Tailwind',
        deploymentPreference: 'Local LAN Kiosk + Cloud Sync',
        slaRequirements: 'Sub-second POS Order Routing'
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setStatus({ type: 'info', text: 'Transmitting client dossier to database...' });

    try {
      await addDoc(collection(db, 'clients'), {
        clientName: formData.clientName,
        companyName: formData.companyName,
        email: formData.email,
        tier: formData.tier,
        primaryObjective: formData.primaryObjective,
        techStack: formData.techStack,
        deploymentPreference: formData.deploymentPreference,
        slaRequirements: formData.slaRequirements,
        status: 'Active Pipeline',
        createdAt: new Date().toISOString()
      });

      setStatus({ type: 'success', text: `✅ Success: ${formData.companyName} onboarded and routed to Clients Tab.` });
      setFormData({
        clientName: '',
        companyName: '',
        email: '',
        tier: 'growth',
        primaryObjective: '',
        techStack: 'Python / React / FastAPI',
        deploymentPreference: 'Firebase Hosting + Cloudflare Workers',
        slaRequirements: '24/7 Agent Monitoring'
      });
    } catch (error) {
      setStatus({ type: 'error', text: `❌ Error: ${error.message}` });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      padding: '24px 32px',
      background: '#090d13',
      color: '#f0f6fc',
      minHeight: '100%',
      boxSizing: 'border-box'
    }}>
      {/* HEADER STRIP */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #21262d',
        paddingBottom: '16px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #1f6feb 0%, #38bdf8 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(56, 189, 248, 0.3)'
          }}>
            <Building size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: '20px', fontWeight: '800', letterSpacing: '-0.02em', color: '#f0f6fc' }}>
              Client Onboarding Portal & Pipeline Gateway
            </h1>
            <p style={{ margin: 0, fontSize: '12px', color: '#8b949e' }}>
              Provision client repositories, bind SLA contracts, and stage production agent workspaces.
            </p>
          </div>
        </div>

        {/* Quick Templates */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#8b949e', fontWeight: '600' }}>Starter Presets:</span>
          <button
            onClick={() => handleApplyTemplate('ai_pipeline')}
            style={{
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#38bdf8',
              padding: '6px 12px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            ⚡ Apex Media AI
          </button>
          <button
            onClick={() => handleApplyTemplate('hospitality')}
            style={{
              background: '#161b22',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#34d399',
              padding: '6px 12px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            🍸 Notō Hospitality
          </button>
        </div>
      </div>

      {/* DUAL COLUMN WORKSPACE */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(480px, 1.25fr) minmax(360px, 1fr)',
        gap: '24px',
        alignItems: 'start'
      }}>
        {/* LEFT COLUMN: ONBOARDING FORM */}
        <div style={{
          background: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          display: 'flex',
          flexDirection: 'column',
          gap: '18px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid #21262d', paddingBottom: '12px' }}>
            <FileText size={18} color="#58a6ff" />
            <span style={{ fontWeight: '700', fontSize: '15px' }}>Client Profile & Deployment Configuration</span>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px' }}>
                  <User size={13} color="#58a6ff" /> Primary Contact Name
                </label>
                <input
                  type="text"
                  name="clientName"
                  value={formData.clientName}
                  onChange={handleChange}
                  required
                  placeholder="e.g. John Doe"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px' }}>
                  <Briefcase size={13} color="#58a6ff" /> Company / Organization
                </label>
                <input
                  type="text"
                  name="companyName"
                  value={formData.companyName}
                  onChange={handleChange}
                  required
                  placeholder="e.g. Acme Corporation"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Email & SLA */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px', display: 'block' }}>
                  Official Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="contact@company.com"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px', display: 'block' }}>
                  SLA / Uptime Objective
                </label>
                <input
                  type="text"
                  name="slaRequirements"
                  value={formData.slaRequirements}
                  onChange={handleChange}
                  placeholder="e.g. 99.9% Uptime, Sub-Second"
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Service Tier Selector */}
            <div>
              <label style={{ fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '8px', display: 'block' }}>
                Engagement Service Tier
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                {TIER_OPTIONS.map((tier) => (
                  <div
                    key={tier.id}
                    onClick={() => setFormData({ ...formData, tier: tier.id })}
                    style={{
                      border: formData.tier === tier.id ? '1px solid #38bdf8' : '1px solid #30363d',
                      background: formData.tier === tier.id ? 'rgba(56, 189, 248, 0.12)' : '#0d1117',
                      borderRadius: '8px',
                      padding: '10px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '12px', fontWeight: '700', color: formData.tier === tier.id ? '#38bdf8' : '#e6edf3' }}>
                        {tier.name}
                      </span>
                      <span style={{ fontSize: '11px', fontWeight: '800', color: '#3fb950' }}>{tier.price}</span>
                    </div>
                    <div style={{ fontSize: '10px', color: '#8b949e', lineHeight: 1.3 }}>{tier.desc}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Primary Objective */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px' }}>
                <Target size={13} color="#58a6ff" /> Mission Scope & Architecture Objective
              </label>
              <textarea
                name="primaryObjective"
                value={formData.primaryObjective}
                onChange={handleChange}
                required
                rows={4}
                placeholder="Describe the technical requirements, models to deploy, or business workflows..."
                style={{
                  width: '100%',
                  boxSizing: 'border-box',
                  background: '#0d1117',
                  border: '1px solid #30363d',
                  borderRadius: '8px',
                  padding: '10px 12px',
                  color: '#f0f6fc',
                  fontSize: '13px',
                  outline: 'none',
                  resize: 'vertical'
                }}
              />
            </div>

            {/* Tech Stack & Infrastructure */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px' }}>
                  <Database size={13} color="#58a6ff" /> Architecture Stack
                </label>
                <select
                  name="techStack"
                  value={formData.techStack}
                  onChange={handleChange}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                >
                  <option value="Python / React / FastAPI">Python / React / FastAPI</option>
                  <option value="Node.js / Firebase / Vite">Node.js / Firebase / Vite</option>
                  <option value="Go Matrix Gateway / IPC">Go Matrix Gateway / IPC</option>
                  <option value="PyTorch / ComfyUI / CUDA">PyTorch / ComfyUI / CUDA</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: '600', color: '#8b949e', marginBottom: '6px' }}>
                  <Layers size={13} color="#58a6ff" /> Deployment Target
                </label>
                <select
                  name="deploymentPreference"
                  value={formData.deploymentPreference}
                  onChange={handleChange}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    background: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    color: '#f0f6fc',
                    fontSize: '13px',
                    outline: 'none'
                  }}
                >
                  <option value="Firebase Hosting + Cloudflare Workers">Firebase Hosting + Cloudflare</option>
                  <option value="Dedicated Windows 11 Host + WSL2">Dedicated Windows 11 Host + WSL2</option>
                  <option value="Local Kiosk & Offline SQLite">Local Kiosk & Offline SQLite</option>
                  <option value="Vast.ai / Clore Mining Node">Vast.ai / Clore Mining Node</option>
                </select>
              </div>
            </div>

            {/* Submission Button */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' }}>
              <button
                type="submit"
                disabled={isSubmitting}
                style={{
                  background: 'linear-gradient(135deg, #1f6feb 0%, #238636 100%)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '12px 24px',
                  fontSize: '13px',
                  fontWeight: '700',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  boxShadow: '0 0 16px rgba(35, 134, 54, 0.4)'
                }}
              >
                <Send size={16} />
                {isSubmitting ? 'Provisioning Dossier...' : 'Complete Onboarding & Route to Clients'}
              </button>

              {status && (
                <div style={{
                  padding: '8px 14px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: '600',
                  background: status.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                  border: `1px solid ${status.type === 'error' ? '#ef4444' : '#10b981'}`,
                  color: status.type === 'error' ? '#f87171' : '#34d399'
                }}>
                  {status.text}
                </div>
              )}
            </div>
          </form>
        </div>

        {/* RIGHT COLUMN: PIPELINE SUMMARY & ROSTER */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Onboarding SLA Checklist */}
          <div style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Shield size={18} color="#34d399" />
              <span style={{ fontWeight: '700', fontSize: '14px', color: '#f0f6fc' }}>Automated Onboarding Stages</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <CheckCircle size={16} color="#3fb950" style={{ marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#e6edf3' }}>1. Database Staging & Vault Sync</div>
                  <div style={{ fontSize: '11px', color: '#8b949e' }}>Writes client dossier directly to Firestore & SQLite master ledger.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <CheckCircle size={16} color="#3fb950" style={{ marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#e6edf3' }}>2. Client CRM Workspace Binding</div>
                  <div style={{ fontSize: '11px', color: '#8b949e' }}>Auto-generates dedicated CRM board in Clients Tab.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <CheckCircle size={16} color="#3fb950" style={{ marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#e6edf3' }}>3. NDA & Mutual Protection Module</div>
                  <div style={{ fontSize: '11px', color: '#8b949e' }}>Binds e-signature agreement template via NDA Signer router.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <Zap size={16} color="#38bdf8" style={{ marginTop: '2px' }} />
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#38bdf8' }}>4. Autonomous Agent Dispatch</div>
                  <div style={{ fontSize: '11px', color: '#8b949e' }}>Hooks into Stehouwer Swarm for continuous background deliverables.</div>
                </div>
              </div>
            </div>
          </div>

          {/* Active Pipeline Roster */}
          <div style={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Clock size={16} color="#f59e0b" />
                <span style={{ fontWeight: '700', fontSize: '14px', color: '#f0f6fc' }}>Recent Pipeline Intakes</span>
              </div>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>Live Sync</span>
            </div>

            {recentClients.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 0', color: '#8b949e', fontSize: '12px' }}>
                No clients in pipeline. Fill out intake form to initialize.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {recentClients.map((c) => (
                  <div
                    key={c.id}
                    style={{
                      background: '#0d1117',
                      border: '1px solid #21262d',
                      borderRadius: '8px',
                      padding: '10px 12px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: '700', color: '#f0f6fc' }}>{c.companyName}</div>
                      <div style={{ fontSize: '11px', color: '#8b949e' }}>{c.clientName} • {c.techStack}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span style={{
                        fontSize: '10px',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        background: 'rgba(56, 189, 248, 0.15)',
                        color: '#38bdf8',
                        fontWeight: '700'
                      }}>
                        {c.tier ? c.tier.toUpperCase() : 'ACTIVE'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
