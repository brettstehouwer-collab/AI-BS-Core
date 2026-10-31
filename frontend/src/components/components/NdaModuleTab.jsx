import { useState, useEffect, useRef } from "react";
import { useBackendHealth } from './useBackendHealth.js';

const DEFAULT_NDA_SCHEMA = {
  all_clause_ids: /** @type {string[]} */ ([]),
  total_clauses: 0,
  title: "Master Services, Confidentiality, Intellectual Property, and Security Agreement",
  company: {
    name: "Stehouwer Publishing, LLC",
    address: "1481 Rosewood St., Jenison, Michigan 49428",
    representatives: [
      { name: "Julie A. Stehouwer", role: "CEO / Authorized Representative" },
      { name: "Brett Adam Stehouwer", role: "VP / CTO / Technical Architecture Lead" }
    ]
  },
  sections: [
    {
      id: "recitals",
      title: "Preamble & Recitals",
      summary: "Establishes identity of the parties, engagement scope, and corporate governance.",
      clauses: [
        { id: "recitals_parties", code: "Recitals", title: "Corporate Identification", text: "Confirms Stehouwer Publishing, LLC and Collaborator roles in publishing, AI systems development, and digital media architecture." },
        { id: "recitals_intent", code: "Intent", title: "Protection of Proprietary Systems", text: "Express intent to protect trade secrets, proprietary workflows, and assign IP exclusively to Company." }
      ]
    },
    {
      id: "sec_1",
      title: "Section I: Master Services Agreement (MSA)",
      summary: "Core scope of services, Statement of Work (SOW) requirement, and termination terms.",
      clauses: [
        { id: "c_1_1", code: "1.1", title: "Purpose & Scope", text: "Governs publishing, software systems, AI training pipelines, automation workflows, and technical system evaluation." },
        { id: "c_1_2", code: "1.2", title: "Precedence", text: "Applies to all Company-related collaboration unless superseded by signed written agreement." },
        { id: "c_2_1", code: "2.1", title: "Corporate Authority", text: "Stehouwer Publishing, LLC retains absolute, exclusive authority over all business operations and IP." },
        { id: "c_2_2", code: "2.2", title: "Key Representatives", text: "Julie A. Stehouwer (CEO) and Brett Adam Stehouwer (VP/CTO) manage corporate and technical operations." },
        { id: "c_3_1", code: "3.1", title: "Written SOW Requirement", text: "All paid services must be defined in writing via executed Statement of Work (SOW) prior to performance." },
        { id: "c_3_2", code: "3.2", title: "Consulting Fee Rule", text: "Compensation must be finalized in writing; unauthorized work creates no payment obligation." },
        { id: "c_4_2", code: "4.2", title: "Termination for Cause/Convenience", text: "30 days notice for convenience; immediate termination for security breach or data exfiltration." },
        { id: "c_4_4", code: "4.4", title: "Perpetual Survival", text: "Confidentiality, IP assignment, non-circumvention, and dispute governance survive termination in perpetuity." }
      ]
    },
    {
      id: "sec_2",
      title: "Section II: Confidentiality & Non-Disclosure",
      summary: "Broad definition of confidential assets, non-replication, and perpetual trade secret protection.",
      clauses: [
        { id: "c_5_1", code: "5.1-5.4", title: "Definition of Confidential Information", text: "Protects Creative Assets, Business Information, Technical Information (source code, schemas, prompts, algorithms), and Proprietary Systems." },
        { id: "c_6_1", code: "6.1-6.2", title: "Duty & Standard of Care", text: "Strict confidence, reasonable care, and mandatory active encryption at rest and in transit." },
        { id: "c_6_3", code: "6.3-6.4", title: "Permitted Use & Non-Replication", text: "Used solely for authorized Company services; strictly prohibits copying, reverse-engineering, or decompiling." },
        { id: "c_6_5", code: "6.5", title: "Perpetual Duration for Trade Secrets", text: "Trade secrets and Proprietary Technology survive indefinitely in perpetuity; business info survives 5 years." },
        { id: "c_6_6", code: "6.6", title: "24-Hour Breach Reporting", text: "Immediate written notice to Brett Adam Stehouwer and Julie A. Stehouwer within 24 hours of any leak." },
        { id: "c_7_2", code: "7.2", title: "DTSA Whistleblower Notice", text: "Defend Trade Secrets Act immunity notice under 18 U.S.C. § 1833(b)." }
      ]
    },
    {
      id: "sec_3",
      title: "Section III: Intellectual Property Assignment",
      summary: "Universal assignment of all work product, work-made-for-hire, and company ownership of modifications.",
      clauses: [
        { id: "c_8_0", code: "8.0", title: "Ownership of Work Product", text: "All deliverables, code, algorithms, and documentation developed for Company belong exclusively to Company." },
        { id: "c_9_1", code: "9.1-9.2", title: "Work Made for Hire & Universal Assignment", text: "Under 17 U.S.C. § 101, eligible work is work for hire; all other IP globally and irrevocably assigned to Company." },
        { id: "c_9_3", code: "9.3", title: "Transfer Restrictions", text: "No right to transfer, license, or sublicense Company IP without written consent of Julie or Brett Stehouwer." },
        { id: "c_10_0", code: "10.0", title: "Proprietary Technology Ownership", text: "AI-BS, prompt systems, reasoning frameworks, and datasets represent exclusive Trade Secrets of Company." }
      ]
    },
    {
      id: "sec_4",
      title: "Section IV: Security, Access, and Data Compliance",
      summary: "CTO authorization requirements, technical sandbox boundaries, and regulatory compliance.",
      clauses: [
        { id: "c_12_0", code: "12.0", title: "System Access & CTO Authorization", text: "System access is revocable at will and strictly conditioned on instructions authorized by CTO Brett Adam Stehouwer." },
        { id: "c_13_0", code: "13.0", title: "Technical Security Controls", text: "Prohibits bypassing authentications, extracting database contents, or deploying unauthorized sniffers." },
        { id: "c_14_1", code: "14.1-14.2", title: "Sandbox Integrity & Export Controls", text: "Respect sandbox memory boundaries; strict compliance with US EAR and OFAC export controls." },
        { id: "c_15_1", code: "15.1-15.2", title: "Data Privacy & Indemnity", text: "GDPR, HIPAA, and CCPA compliance; Collaborator assumes sole financial responsibility for regulatory fines caused by breach." }
      ]
    },
    {
      id: "sec_5",
      title: "Section V: Brand & Business Protection",
      summary: "5-year non-circumvention, 3-year non-solicitation, and public communication restrictions.",
      clauses: [
        { id: "c_16_0", code: "16.0", title: "5-Year Non-Circumvention", text: "Collaborator shall not exploit confidential opportunities or build competing business models using Company confidential info." },
        { id: "c_17_0", code: "17.0", title: "3-Year Non-Solicitation", text: "Prohibits soliciting or contracting Company employees, contractors, or active clients." },
        { id: "c_18_0", code: "18.0", title: "Brand & Affiliation Restrictions", text: "No unauthorized public representation, logo usage, or sharing internal communications on public forums." }
      ]
    },
    {
      id: "sec_6",
      title: "Section VI: Legal Governance, Disputes, & Indemnification",
      summary: "Kent County Michigan venue, AAA commercial arbitration, and immediate injunctive relief.",
      clauses: [
        { id: "c_19_1", code: "19.1-19.2", title: "Mediation & Binding Arbitration", text: "Good-faith consultation, non-binding mediation, then binding AAA arbitration in Kent County, Michigan." },
        { id: "c_19_3", code: "19.3", title: "Immediate Injunctive Relief", text: "Company retains absolute right to seek immediate injunctive relief in court to protect IP and security." },
        { id: "c_20_0", code: "20.0-21.0", title: "Remedies & Indemnification", text: "Equitable remedies for irreparable harm; Collaborator indemnifies Company against breach damages and legal fees." }
      ]
    },
    {
      id: "sec_7",
      title: "Section VII & Exhibit A: Technical Scope & Execution",
      summary: "Governing law, CISG exclusion, explicit AI-BS trade secret scope, and execution signatures.",
      clauses: [
        { id: "c_23_27", code: "23-27", title: "Michigan Law & Counterparts", text: "Governed by Michigan law; digital and electronic signatures deemed legally binding originals." },
        { id: "c_exhibit_a", code: "Exhibit A", title: "AI-BS & Hallucination Mitigation Scope", text: "Explicitly locks down AI-BS, reasoning graphs, autograd engines, prompt architectures, and hallucination mitigation pipelines." }
      ]
    }
  ]
};
DEFAULT_NDA_SCHEMA.all_clause_ids = DEFAULT_NDA_SCHEMA.sections.flatMap(s => s.clauses.map( 
c => c.id));
DEFAULT_NDA_SCHEMA.total_clauses = DEFAULT_NDA_SCHEMA.all_clause_ids.length;

/** @param {{"backendUrl": string}} props */
export default function NdaModuleTab({ backendUrl: propBackendUrl }) {
  const { backendUrl: healthBackendUrl } = useBackendHealth();
  const backendUrl = propBackendUrl || healthBackendUrl || (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? 'http://127.0.0.1:8080' : 'https://api.stehouwerpublishing.com');

  // Navigation sub-tabs: 'review_and_sign', 'anti_tamper_inspector', 'full_agreement_text'
  const [activeSubTab, setActiveSubTab] = useState('review_and_sign');

  // Schema state initialized with complete default schema
  const [schema, setSchema] = useState(DEFAULT_NDA_SCHEMA);
  const [loadingSchema, setLoadingSchema] = useState(false);

  // Form inputs (Empty by default)
  const [collaboratorName, setCollaboratorName] = useState('');
  const [collaboratorTitle, setCollaboratorTitle] = useState('');
  const [collaboratorCompany, setCollaboratorCompany] = useState('');
  const [collaboratorEmail, setCollaboratorEmail] = useState('');
  const [collaboratorPhone, setCollaboratorPhone] = useState('');
  const [collaboratorAddress, setCollaboratorAddress] = useState('');
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split('T')[0]);

  // Section Cycler state
  const [activeSectionIndex, setActiveSectionIndex] = useState(0);
  const [verifiedClauses, setVerifiedClauses] = useState(new Set());

  // Signature state
  const [signatureMode, setSignatureMode] = useState('draw'); // 'draw' or 'type'
  const [typedSignature, setTypedSignature] = useState('');
  const [attestationAgreed, setAttestationAgreed] = useState(false);
  const [isSigning, setIsSigning] = useState(false);
  const [signError, setSignError] = useState(/** @type {string | null} */ (null));
  const [signedResult, setSignedResult] = useState(/** @type {{"pdf_base64": string, "filename": string, "signer": {"name": string}, "integrity_hash": string} | null} */ (null));
  const [actionNotice, setActionNotice] = useState(/** @type {string | null} */ (null));

  // Canvas ref for drawing signature
  const canvasRef = useRef(/** @type {HTMLCanvasElement | null} */ (null));
  const [isDrawing, setIsDrawing] = useState(false);
  const [hasDrawn, setHasDrawn] = useState(false);

  // Anti-Tamper Inspector state
  const [inspectorFile, setInspectorFile] = useState(/** @type {File | null} */ (null));
  const [inspectorFileName, setInspectorFileName] = useState('');
  const [isInspecting, setIsInspecting] = useState(false);
  const [inspectorResult, setInspectorResult] = useState(/** @type {{"valid": boolean, "message"?: string, "error"?: string, "signer"?: string, "current_sha256"?: string, "embedded_hmac"?: string, "tamper_detected": boolean} | null} */ (null));
  const [isSimulatingTamper, setIsSimulatingTamper] = useState(false);

  // 1. Fetch live schema from backend with fallback
  useEffect(() => {
    fetch(`${backendUrl}/api/v1/nda/schema`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (data && data.sections) {
          setSchema(data);
        }
        setLoadingSchema(false);
      })
      .catch((_err) => {
        // Fallback schema is already active
        setLoadingSchema(false);
      });
  }, [backendUrl]);

  // Canvas drawing handlers
  useEffect(() => {
    if (signatureMode === 'draw' && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#0f2a4a';
    }
  }, [signatureMode, activeSubTab]);

  /** @param {import('react').MouseEvent<HTMLCanvasElement> | import('react').TouchEvent<HTMLCanvasElement>} e */
const startDrawing = ( e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
      if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    const clientX = 'clientX' in e ? e.clientX : (e.touches[0]?.clientX || 0);
    const clientY = 'clientY' in e ? e.clientY : (e.touches[0]?.clientY || 0);
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsDrawing(true);
    setHasDrawn(true);
  };

  /** @param {import('react').MouseEvent<HTMLCanvasElement> | import('react').TouchEvent<HTMLCanvasElement>} e */
const draw = ( e) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
      if (!ctx) return;
    const rect = canvas.getBoundingClientRect();
    const clientX = 'clientX' in e ? e.clientX : (e.touches[0]?.clientX || 0);
    const clientY = 'clientY' in e ? e.clientY : (e.touches[0]?.clientY || 0);
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const clearSignatureCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
      if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setHasDrawn(false);
  };

  // Quick Preset for Robert Costner
  const applyPresetRobertCostner = () => {
    setCollaboratorName('Robert Costner');
    setCollaboratorTitle('AI Development & Business Systems Advisor');
    setCollaboratorCompany('Costner AI Ventures');
    setCollaboratorEmail('robert.costner@gmail.com');
    setCollaboratorPhone('+1 (404) 555-0188');
    setCollaboratorAddress('Atlanta, Georgia');
    setTypedSignature('Robert Costner');
    setAttestationAgreed(true);
    setSignError(null);
    setActionNotice('Preset applied: Robert Costner loaded.');
    setTimeout(() => setActionNotice(null), 3000);
  };

  // Clear all fields completely
  const clearForm = () => {
    setCollaboratorName('');
    setCollaboratorTitle('');
    setCollaboratorCompany('');
    setCollaboratorEmail('');
    setCollaboratorPhone('');
    setCollaboratorAddress('');
    setTypedSignature('');
    setAttestationAgreed(false);
    setVerifiedClauses(new Set());
    clearSignatureCanvas();
    setSignedResult(null);
    setSignError(null);
    setActionNotice('Form cleared: All fields and signatures have been reset.');
    setTimeout(() => setActionNotice(null), 3000);
  };

  // Toggle clause verification
  /** @param {string} clauseId */
const toggleClause = ( clauseId) => {
    setVerifiedClauses((prev) => {
      const next = new Set(prev);
      if (next.has(clauseId)) {
        next.delete(clauseId);
      } else {
        next.add(clauseId);
      }
      return next;
    });
  };

  // Verify all in active section
  const verifyCurrentSection = () => {
    if (!schema || !schema.sections[activeSectionIndex]) return;
    const currentSectionClauses = schema.sections[activeSectionIndex].clauses.map(
( c) => c.id);
    setVerifiedClauses((prev) => {
      const next = new Set(prev);
      currentSectionClauses.forEach((id) => next.add(id));
      return next;
    });
  };

  // Fast-track: Verify all clauses in the entire NDA
  const verifyAllClauses = () => {
    if (!schema) return;
    setVerifiedClauses(new Set(schema.all_clause_ids || []));
  };

  // Check if current section is 100% verified
  /** @param {{"clauses": Array<{"id": string}>}} sec */
const isSectionComplete = ( sec) => {
    if (!sec || !sec.clauses) return false;
    return sec.clauses.every(
( c) => verifiedClauses.has(c.id));
  };

  // Generate Base64 signature image
  const getSignatureDataUrl = () => {
    if (signatureMode === 'draw') {
      if (!canvasRef.current || !hasDrawn) return null;
      return canvasRef.current.toDataURL('image/png');
    } else {
      if (!typedSignature.trim()) return null;
      // Render typed text onto hidden canvas to produce genuine image data URL
      const offscreen = document.createElement('canvas');
      offscreen.width = 480;
      offscreen.height = 120;
      const ctx = offscreen.getContext('2d');
      if (!ctx) return null;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, offscreen.width, offscreen.height);
      ctx.font = 'italic 34px "Dancing Script", "Brush Script MT", cursive, sans-serif';
      ctx.fillStyle = '#0f2a4a';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(typedSignature.trim(), offscreen.width / 2, 50);

      // Add digital certification sub-line
      ctx.font = '9px monospace';
      ctx.fillStyle = '#64748b';
      ctx.fillText(`DIGITALLY CERTIFIED • ${new Date().toISOString()}`, offscreen.width / 2, 95);
      return offscreen.toDataURL('image/png');
    }
  };

  // Handle "Agree & Sign" action
  const handleAgreeAndSign = async () => {
    setSignError(null);

    // Validation
    if (!collaboratorName.trim()) {
      setSignError('Please enter the Collaborator Full Name.');
      return;
    }
    if (!collaboratorEmail.trim()) {
      setSignError('Please enter a valid Collaborator Email address.');
      return;
    }
    if (!attestationAgreed) {
      setSignError('You must check the legal attestation checkbox confirming your agreement.');
      return;
    }

    const totalClauses = schema?.all_clause_ids?.length || 32;
    if (verifiedClauses.size < totalClauses) {
      setSignError(`Please review and verify all ${totalClauses} clauses across all sections before executing.`);
      return;
    }

    const sigUrl = getSignatureDataUrl();
    if (!sigUrl) {
      setSignError(signatureMode === 'draw' ? 'Please draw your signature in the signature box.' : 'Please type your legal signature.');
      return;
    }

    setIsSigning(true);

    try {
      const payload = {
        collaborator_name: collaboratorName.trim(),
        collaborator_title: collaboratorTitle.trim() || 'Collaborator / Advisor',
        collaborator_company: collaboratorCompany.trim() || 'Independent',
        collaborator_email: collaboratorEmail.trim(),
        collaborator_phone: collaboratorPhone.trim(),
        collaborator_address: collaboratorAddress.trim(),
        effective_date: effectiveDate,
        signature_data_url: sigUrl,
        signature_type: signatureMode,
        ip_address: '127.0.0.1',
        verified_sections: Array.from(verifiedClauses),
      };

      const res = await fetch(`${backendUrl}/api/v1/nda/generate-signed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      setSignedResult(data);
    } catch (err) {
      console.error('Execution failed:', err);
      setSignError((err instanceof Error ? err.message : String(err)) || 'Failed to generate signed NDA.');
    } finally {
      setIsSigning(false);
    }
  };

  // Trigger browser download of the signed PDF
  const downloadSignedPdf = () => {
    if (!signedResult || !signedResult.pdf_base64) return;
    const byteCharacters = atob(signedResult.pdf_base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'application/pdf' });
    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = signedResult.filename || 'Master_NDA_Agreement_Protected.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  };

  // Anti-Tamper Inspector: inspect uploaded or selected file
  /** @param {File | null} [fileToInspect] */
const runAntiTamperInspection = async ( fileToInspect) => {
    const targetFile = fileToInspect || inspectorFile;
    if (!targetFile) return;

    setIsInspecting(true);
    setInspectorResult(null);

    try {
      const formData = new FormData();
      formData.append('file', targetFile);

      const res = await fetch(`${backendUrl}/api/v1/nda/verify-integrity`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      setInspectorResult(data);
    } catch (err) {
      console.error('Integrity inspection error:', err);
      setInspectorResult({
        valid: false,
        tamper_detected: true,
        error: `Inspection failed: ${(err instanceof Error ? err.message : String(err))}`,
      });
    } finally {
      setIsInspecting(false);
    }
  };

  // Load the newly signed PDF directly into the inspector
  const loadSignedPdfIntoInspector = () => {
    if (!signedResult || !signedResult.pdf_base64) return;
    const byteCharacters = atob(signedResult.pdf_base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const file = new File([byteArray], signedResult.filename || 'signed_nda.pdf', { type: 'application/pdf' });
    setInspectorFile(file);
    setInspectorFileName(file.name);
    setActiveSubTab('anti_tamper_inspector');
    runAntiTamperInspection(file);
  };

  // Simulate a live tamper attack to demonstrate anti-tamper self-corruption
  const simulateTamperAttack = async () => {
    if (!inspectorFile) return;

    setIsSimulatingTamper(true);
    try {
      const formData = new FormData();
      formData.append('file', inspectorFile);

      const res = await fetch(`${backendUrl}/api/v1/nda/simulate-tamper`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) throw new Error('Failed to simulate tamper attack.');
      const data = await res.json();

      // Convert tampered b64 into a new file and run it through the verifier
      const byteCharacters = atob(data.tampered_pdf_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const tamperedFile = new File([byteArray], `TAMPERED_${inspectorFileName}`, { type: 'application/pdf' });

      setInspectorFile(tamperedFile);
      setInspectorFileName(tamperedFile.name);
      await runAntiTamperInspection(tamperedFile);
    } catch (err) {
      alert(`Tamper simulation error: ${(err instanceof Error ? err.message : String(err))}`);
    } finally {
      setIsSimulatingTamper(false);
    }
  };

  const totalClauses = schema?.all_clause_ids?.length || 32;
  const verifiedCount = verifiedClauses.size;
  const percentComplete = Math.round((verifiedCount / totalClauses) * 100);

  return (
    <div style={{ padding: '24px', maxWidth: '1280px', margin: '0 auto', color: '#f1f5f9', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* MASTER HEADER */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.9))',
        border: '1px solid rgba(56, 189, 248, 0.25)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span style={{ fontSize: '28px' }}>📜</span>
              <h1 style={{ margin: 0, fontSize: '1.65rem', fontWeight: 800, letterSpacing: '-0.02em', background: 'linear-gradient(to right, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                SOVEREIGN NDA & ANTI-TAMPER SUITE
              </h1>
              <span style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '3px 10px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: 700, border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                v5.327.0
              </span>
            </div>
            <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.92rem', maxWidth: '850px' }}>
              Stehouwer Publishing, LLC • Master Services, Confidentiality, Intellectual Property Assignment & Cryptographic Digital Anti-Tamper Engine.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '5px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600 }}>
              🛡️ SHA-256 HMAC Sealed
            </span>
            <span style={{ background: 'rgba(129, 140, 248, 0.15)', color: '#818cf8', border: '1px solid rgba(129, 140, 248, 0.3)', padding: '5px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600 }}>
              ⚖️ Kent County, MI Venue
            </span>
            <span style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#eab308', border: '1px solid rgba(234, 179, 8, 0.3)', padding: '5px 12px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600 }}>
              ⚡ Dynamic Watermark
            </span>
          </div>
        </div>

        {/* NOTIFICATION TOAST */}
        {actionNotice && (
          <div style={{
            marginTop: '12px',
            background: 'rgba(56, 189, 248, 0.15)',
            border: '1px solid rgba(56, 189, 248, 0.4)',
            color: '#38bdf8',
            borderRadius: '8px',
            padding: '8px 14px',
            fontSize: '0.85rem',
            fontWeight: 600
          }}>
            ℹ️ {actionNotice}
          </div>
        )}

        {/* NAVIGATION SUB-TABS */}
        <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: '16px' }}>
          <button
            onClick={() => setActiveSubTab('review_and_sign')}
            style={{
              background: activeSubTab === 'review_and_sign' ? '#2563eb' : 'rgba(30, 41, 59, 0.8)',
              color: '#ffffff',
              border: activeSubTab === 'review_and_sign' ? '1px solid #60a5fa' : '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>✍️</span> 1. Interactive Fill & Sign
          </button>

          <button
            onClick={() => setActiveSubTab('anti_tamper_inspector')}
            style={{
              background: activeSubTab === 'anti_tamper_inspector' ? '#0d9488' : 'rgba(30, 41, 59, 0.8)',
              color: '#ffffff',
              border: activeSubTab === 'anti_tamper_inspector' ? '1px solid #2dd4bf' : '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>🛡️</span> 2. Anti-Tamper & Corruption Inspector
          </button>

          <button
            onClick={() => setActiveSubTab('full_agreement_text')}
            style={{
              background: activeSubTab === 'full_agreement_text' ? '#4f46e5' : 'rgba(30, 41, 59, 0.8)',
              color: '#ffffff',
              border: activeSubTab === 'full_agreement_text' ? '1px solid #818cf8' : '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '0.9rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            <span>📑</span> 3. Full Agreement Legal Reference
          </button>
        </div>
      </div>

      {/* SUB-TAB 1: REVIEW AND SIGN */}
      {activeSubTab === 'review_and_sign' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 420px) 1fr', gap: '24px', alignItems: 'start' }}>
          
          {/* LEFT COLUMN: SIGNATORY FORM & QUICK ACTIONS */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Quick Actions Card */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '12px',
              padding: '18px',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{ fontSize: '0.82rem', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 700, marginBottom: '10px', letterSpacing: '0.05em' }}>
                ⚡ Fast-Track Signatory Presets
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={applyPresetRobertCostner}
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '9px 12px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    boxShadow: '0 2px 8px rgba(2, 132, 199, 0.3)'
                  }}
                >
                  ⚡ Preset: Robert Costner
                </button>
                <button
                  onClick={clearForm}
                  style={{
                    background: 'rgba(239, 68, 68, 0.15)',
                    color: '#f87171',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '8px',
                    padding: '9px 12px',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  🧹 Clear All Fields
                </button>
              </div>
            </div>

            {/* Parties Summary Card */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '12px',
              padding: '18px',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{ fontSize: '0.82rem', textTransform: 'uppercase', color: '#38bdf8', fontWeight: 700, marginBottom: '10px', letterSpacing: '0.05em' }}>
                🏢 Disclosing Company
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>Stehouwer Publishing, LLC</div>
              <div style={{ fontSize: '0.83rem', color: '#94a3b8', marginTop: '2px' }}>1481 Rosewood St., Jenison, MI 49428</div>
              <div style={{ marginTop: '10px', fontSize: '0.8rem', color: '#cbd5e1', lineHeight: '1.4' }}>
                • <b>Julie A. Stehouwer</b> — CEO & Executive Officer<br />
                • <b>Brett Adam Stehouwer</b> — VP, CTO & Technical Lead
              </div>
            </div>

            {/* Collaborator Details Form */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.75)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '12px',
              padding: '20px',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div style={{ fontSize: '0.82rem', textTransform: 'uppercase', color: '#a78bfa', fontWeight: 700, letterSpacing: '0.05em' }}>
                  ✍️ Recipient / Collaborator Details
                </div>
                {(collaboratorName || collaboratorEmail || typedSignature) && (
                  <button
                    onClick={clearForm}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#f87171',
                      fontSize: '0.75rem',
                      cursor: 'pointer',
                      textDecoration: 'underline'
                    }}
                  >
                    Reset Form
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Legal Full Name *
                  </label>
                  <input
                    type="text"
                    value={collaboratorName}
                    onChange={
( e) => setCollaboratorName(e.target.value)}
                    placeholder="Enter recipient's full legal name..."
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Professional Title / Role
                  </label>
                  <input
                    type="text"
                    value={collaboratorTitle}
                    onChange={
( e) => setCollaboratorTitle(e.target.value)}
                    placeholder="Enter title or role (e.g. Advisor, Engineer)..."
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Company / Organization
                  </label>
                  <input
                    type="text"
                    value={collaboratorCompany}
                    onChange={
( e) => setCollaboratorCompany(e.target.value)}
                    placeholder="Enter company name or Independent..."
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Email Address *
                  </label>
                  <input
                    type="email"
                    value={collaboratorEmail}
                    onChange={
( e) => setCollaboratorEmail(e.target.value)}
                    placeholder="collaborator@example.com"
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Phone Number
                  </label>
                  <input
                    type="text"
                    value={collaboratorPhone}
                    onChange={
( e) => setCollaboratorPhone(e.target.value)}
                    placeholder="+1 (555) 000-0000 (Optional)"
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Physical Address
                  </label>
                  <input
                    type="text"
                    value={collaboratorAddress}
                    onChange={
( e) => setCollaboratorAddress(e.target.value)}
                    placeholder="City, State / Physical address (Optional)"
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '4px', fontWeight: 500 }}>
                    Effective Agreement Date
                  </label>
                  <input
                    type="date"
                    value={effectiveDate}
                    onChange={
( e) => setEffectiveDate(e.target.value)}
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '6px',
                      padding: '8px 12px',
                      color: '#ffffff',
                      fontSize: '0.9rem',
                      boxSizing: 'border-box'
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: INTERACTIVE SECTION CYCLER & SIGNATURE TOOL */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            
            {/* PROGRESS & CYCLING HEADER */}
            <div style={{
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '14px',
              padding: '20px',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <div>
                  <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
                    Interactive Clause Verification Progress
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: percentComplete === 100 ? '#10b981' : '#38bdf8' }}>
                    {verifiedCount} of {totalClauses} Clauses Verified ({percentComplete}%)
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={verifyAllClauses}
                    style={{
                      background: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      border: '1px solid rgba(56, 189, 248, 0.3)',
                      borderRadius: '8px',
                      padding: '6px 14px',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    ✓ Verify All 32 Clauses
                  </button>
                </div>
              </div>

              {/* Progress Track */}
              <div style={{ width: '100%', height: '8px', background: '#0f172a', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${percentComplete}%`,
                    height: '100%',
                    background: percentComplete === 100 ? 'linear-gradient(to right, #10b981, #059669)' : 'linear-gradient(to right, #38bdf8, #818cf8)',
                    transition: 'width 0.3s ease'
                  }}
                />
              </div>

              {/* SECTION STEP BUTTONS */}
              {schema && (
                <div style={{ display: 'flex', gap: '6px', marginTop: '16px', overflowX: 'auto', paddingBottom: '4px' }}>
                  {schema.sections.map(
( sec, idx) => {
                    const isComplete = isSectionComplete(sec);
                    const isActive = activeSectionIndex === idx;
                    return (
                      <button
                        key={sec.id}
                        onClick={() => setActiveSectionIndex(idx)}
                        style={{
                          background: isActive
                            ? 'rgba(56, 189, 248, 0.25)'
                            : isComplete
                            ? 'rgba(16, 185, 129, 0.15)'
                            : 'rgba(15, 23, 42, 0.6)',
                          color: isActive ? '#38bdf8' : isComplete ? '#10b981' : '#94a3b8',
                          border: isActive
                            ? '1px solid #38bdf8'
                            : isComplete
                            ? '1px solid rgba(16, 185, 129, 0.4)'
                            : '1px solid rgba(255, 255, 255, 0.08)',
                          borderRadius: '8px',
                          padding: '6px 12px',
                          fontSize: '0.78rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px'
                        }}
                      >
                        <span>{isComplete ? '✓' : `${idx + 1}`}</span>
                        <span>{sec.title.split(':')[0]}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* ACTIVE SECTION CLAUSE CHECKLIST */}
            {loadingSchema ? (
              <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>Loading NDA Agreement Schema...</div>
            ) : schema && schema.sections[activeSectionIndex] ? (
              (() => {
                const currentSec = schema.sections[activeSectionIndex];
                const isComplete = isSectionComplete(currentSec);

                return (
                  <div style={{
                    background: 'rgba(30, 41, 59, 0.85)',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '14px',
                    padding: '24px',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '16px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '14px' }}>
                      <div>
                        <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Section {activeSectionIndex + 1} of {schema.sections.length}
                        </div>
                        <h2 style={{ margin: '4px 0 6px 0', fontSize: '1.28rem', fontWeight: 700, color: '#f8fafc' }}>
                          {currentSec.title}
                        </h2>
                        <p style={{ margin: 0, fontSize: '0.88rem', color: '#94a3b8' }}>
                          {currentSec.summary}
                        </p>
                      </div>

                      <button
                        onClick={verifyCurrentSection}
                        style={{
                          background: isComplete ? 'rgba(16, 185, 129, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                          color: isComplete ? '#10b981' : '#38bdf8',
                          border: isComplete ? '1px solid rgba(16, 185, 129, 0.4)' : '1px solid rgba(56, 189, 248, 0.4)',
                          borderRadius: '8px',
                          padding: '6px 14px',
                          fontSize: '0.8rem',
                          fontWeight: 700,
                          cursor: 'pointer'
                        }}
                      >
                        {isComplete ? '✓ Section Verified' : 'Check All In This Section'}
                      </button>
                    </div>

                    {/* CLAUSES CHECKBOX LIST */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {currentSec.clauses.map((clause) => {
                        const checked = verifiedClauses.has(clause.id);
                        return (
                          <div
                            key={clause.id}
                            onClick={() => toggleClause(clause.id)}
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '14px',
                              background: checked ? 'rgba(56, 189, 248, 0.08)' : 'rgba(15, 23, 42, 0.6)',
                              border: checked ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid rgba(255, 255, 255, 0.07)',
                              borderRadius: '10px',
                              padding: '14px 16px',
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => {}} // handled by parent onClick
                              style={{
                                marginTop: '3px',
                                width: '18px',
                                height: '18px',
                                cursor: 'pointer',
                                accentColor: '#38bdf8'
                              }}
                            />
                            <div style={{ flex: 1 }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                <span style={{
                                  background: checked ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                  color: checked ? '#38bdf8' : '#cbd5e1',
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  fontSize: '0.72rem',
                                  fontWeight: 800
                                }}>
                                  {clause.code}
                                </span>
                                <span style={{ fontSize: '0.92rem', fontWeight: 700, color: checked ? '#ffffff' : '#e2e8f0' }}>
                                  {clause.title}
                                </span>
                              </div>
                              <div style={{ fontSize: '0.84rem', color: '#94a3b8', lineHeight: '1.45' }}>
                                {clause.text}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* SECTION NAVIGATION BUTTONS */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: '16px' }}>
                      <button
                        onClick={() => setActiveSectionIndex((prev) => Math.max(0, prev - 1))}
                        disabled={activeSectionIndex === 0}
                        style={{
                          background: 'rgba(255, 255, 255, 0.05)',
                          color: activeSectionIndex === 0 ? '#64748b' : '#cbd5e1',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                          padding: '8px 16px',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          cursor: activeSectionIndex === 0 ? 'not-allowed' : 'pointer'
                        }}
                      >
                        ← Previous Section
                      </button>

                      <button
                        onClick={() => setActiveSectionIndex((prev) => Math.min(schema.sections.length - 1, prev + 1))}
                        disabled={activeSectionIndex === schema.sections.length - 1}
                        style={{
                          background: 'linear-gradient(135deg, #2563eb, #1d4ed8)',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '8px',
                          padding: '8px 20px',
                          fontSize: '0.85rem',
                          fontWeight: 700,
                          cursor: activeSectionIndex === schema.sections.length - 1 ? 'not-allowed' : 'pointer',
                          opacity: activeSectionIndex === schema.sections.length - 1 ? 0.5 : 1
                        }}
                      >
                        Next Section →
                      </button>
                    </div>
                  </div>
                );
              })()
            ) : null}

            {/* DIGITAL SIGNATURE TOOL & EXECUTION BOX */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9))',
              border: '1px solid rgba(56, 189, 248, 0.3)',
              borderRadius: '14px',
              padding: '24px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Final Execution Stage
                  </div>
                  <h3 style={{ margin: '2px 0 0 0', fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc' }}>
                    ✍️ Digital Signature & Cryptographic Seal
                  </h3>
                </div>

                {/* Mode Selector */}
                <div style={{ display: 'flex', gap: '6px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px', borderRadius: '8px' }}>
                  <button
                    onClick={() => setSignatureMode('draw')}
                    style={{
                      background: signatureMode === 'draw' ? '#38bdf8' : 'transparent',
                      color: signatureMode === 'draw' ? '#0f172a' : '#94a3b8',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '4px 12px',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Draw Pad
                  </button>
                  <button
                    onClick={() => setSignatureMode('type')}
                    style={{
                      background: signatureMode === 'type' ? '#38bdf8' : 'transparent',
                      color: signatureMode === 'type' ? '#0f172a' : '#94a3b8',
                      border: 'none',
                      borderRadius: '6px',
                      padding: '4px 12px',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      cursor: 'pointer'
                    }}
                  >
                    Type Signature
                  </button>
                </div>
              </div>

              {/* SIGNATURE PAD OR TYPED INPUT */}
              {signatureMode === 'draw' ? (
                <div>
                  <div style={{ position: 'relative', background: '#ffffff', borderRadius: '8px', border: '2px dashed #94a3b8', overflow: 'hidden' }}>
                    <canvas
                      ref={canvasRef}
                      width={600}
                      height={130}
                      onMouseDown={startDrawing}
                      onMouseMove={draw}
                      onMouseUp={stopDrawing}
                      onMouseLeave={stopDrawing}
                      onTouchStart={startDrawing}
                      onTouchMove={draw}
                      onTouchEnd={stopDrawing}
                      style={{ width: '100%', height: '130px', display: 'block', cursor: 'crosshair' }}
                    />
                    {!hasDrawn && (
                      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', color: '#94a3b8', fontSize: '0.9rem', fontStyle: 'italic' }}>
                        Draw your authorized signature here with mouse or stylus
                      </div>
                    )}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '6px' }}>
                    <button
                      onClick={clearSignatureCanvas}
                      style={{
                        background: 'transparent',
                        color: '#94a3b8',
                        border: 'none',
                        fontSize: '0.78rem',
                        cursor: 'pointer',
                        textDecoration: 'underline'
                      }}
                    >
                      Clear Pad
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <input
                    type="text"
                    value={typedSignature}
                    onChange={
( e) => setTypedSignature(e.target.value)}
                    placeholder="Type full legal name to sign..."
                    style={{
                      width: '100%',
                      background: '#0f172a',
                      border: '1px solid rgba(255, 255, 255, 0.2)',
                      borderRadius: '8px',
                      padding: '12px 16px',
                      color: '#ffffff',
                      fontSize: '1rem',
                      boxSizing: 'border-box'
                    }}
                  />
                  {typedSignature && (
                    <div style={{
                      marginTop: '10px',
                      padding: '12px 16px',
                      background: '#ffffff',
                      borderRadius: '8px',
                      textAlign: 'center'
                    }}>
                      <span style={{
                        fontFamily: 'italic "Dancing Script", "Brush Script MT", cursive, sans-serif',
                        fontSize: '28px',
                        color: '#0f2a4a'
                      }}>
                        {typedSignature}
                      </span>
                      <div style={{ fontSize: '9px', color: '#64748b', marginTop: '4px', letterSpacing: '0.05em' }}>
                        AUTHENTICATED ELECTRONIC SIGNATURE • STEHOUWER PUBLISHING CERTIFIED
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ATTESTATION CHECKBOX */}
              <div style={{
                marginTop: '18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                padding: '12px 14px'
              }}>
                <input
                  type="checkbox"
                  id="attestation"
                  checked={attestationAgreed}
                  onChange={
( e) => setAttestationAgreed(e.target.checked)}
                  style={{ width: '18px', height: '18px', marginTop: '2px', accentColor: '#10b981', cursor: 'pointer' }}
                />
                <label htmlFor="attestation" style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.45', cursor: 'pointer' }}>
                  I declare under penalty of perjury under the laws of the State of Michigan and the United States that I have reviewed, understood, and agreed to all 32 clauses of this Master Agreement, and that my electronic signature represents my legally binding execution.
                </label>
              </div>

              {/* ERROR NOTICE */}
              {signError && (
                <div style={{ marginTop: '14px', background: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.4)', borderRadius: '8px', padding: '10px 14px', color: '#fca5a5', fontSize: '0.85rem' }}>
                  ⚠️ {signError}
                </div>
              )}

              {/* EXECUTE BUTTON */}
              <button
                onClick={handleAgreeAndSign}
                disabled={isSigning}
                style={{
                  marginTop: '18px',
                  width: '100%',
                  background: isSigning
                    ? 'rgba(16, 185, 129, 0.4)'
                    : 'linear-gradient(135deg, #10b981, #059669)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '14px',
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  cursor: isSigning ? 'wait' : 'pointer',
                  boxShadow: '0 4px 20px rgba(16, 185, 129, 0.35)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '10px',
                  transition: 'all 0.2s'
                }}
              >
                {isSigning ? (
                  <>⚡ Generating Cryptographic Anti-Tamper Master PDF...</>
                ) : (
                  <>✍️ AGREE & SIGN MASTER NDA (GENERATE WATERMARKED ANTI-TAMPER PDF)</>
                )}
              </button>
            </div>

            {/* SIGNED RESULT SUCCESS BANNER */}
            {signedResult && (
              <div style={{
                background: 'linear-gradient(135deg, rgba(6, 78, 59, 0.9), rgba(15, 23, 42, 0.95))',
                border: '1px solid #10b981',
                borderRadius: '14px',
                padding: '24px',
                boxShadow: '0 8px 32px rgba(16, 185, 129, 0.25)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                  <span style={{ fontSize: '24px' }}>🎉</span>
                  <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 800, color: '#34d399' }}>
                    MASTER NDA EXECUTED & CRYPTOGRAPHICALLY SEALED
                  </h3>
                </div>

                <p style={{ margin: '0 0 14px 0', color: '#e2e8f0', fontSize: '0.9rem' }}>
                  The Agreement has been rendered with full legal watermarks, embedded dynamic anti-tamper seals, and signed by <b>{signedResult.signer?.name}</b>.
                </p>

                <div style={{ background: 'rgba(0, 0, 0, 0.4)', borderRadius: '8px', padding: '12px', fontSize: '0.8rem', fontFamily: 'monospace', color: '#a7f3d0', marginBottom: '16px' }}>
                  <div><b>File:</b> {signedResult.filename}</div>
                  <div style={{ wordBreak: 'break-all', marginTop: '4px' }}>
                    <b>SHA-256 HMAC:</b> {signedResult.integrity_hash}
                  </div>
                  <div style={{ marginTop: '4px' }}>
                    <b>Saved To:</b> Documents/signed_ndas/ &amp; User Desktop
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <button
                    onClick={downloadSignedPdf}
                    style={{
                      background: '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '8px',
                      padding: '10px 18px',
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    ⬇️ Download Master NDA PDF
                  </button>

                  <button
                    onClick={loadSignedPdfIntoInspector}
                    style={{
                      background: 'rgba(56, 189, 248, 0.2)',
                      color: '#38bdf8',
                      border: '1px solid rgba(56, 189, 248, 0.4)',
                      borderRadius: '8px',
                      padding: '10px 18px',
                      fontSize: '0.9rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}
                  >
                    🛡️ Open in Anti-Tamper Inspector
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-TAB 2: ANTI-TAMPER INSPECTOR */}
      {activeSubTab === 'anti_tamper_inspector' && (
        <div style={{
          background: 'rgba(30, 41, 59, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '16px',
          padding: '28px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
        }}>
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <span style={{ fontSize: '42px' }}>🛡️</span>
              <h2 style={{ margin: '8px 0 4px 0', fontSize: '1.5rem', fontWeight: 800, color: '#f8fafc' }}>
                Digital Anti-Tamper &amp; Integrity Inspector
              </h2>
              <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.92rem' }}>
                Inspects any PDF for authentic Stehouwer Publishing cryptographic seals and flags any post-signature corruption or clause alteration.
              </p>
            </div>

            {/* DROPZONE / FILE SELECTOR */}
            <div style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '2px dashed rgba(56, 189, 248, 0.35)',
              borderRadius: '12px',
              padding: '32px',
              textAlign: 'center',
              marginBottom: '20px'
            }}>
              <input
                type="file"
                id="nda-upload"
                accept="application/pdf"
                onChange={
( e) => {
                  if (e.target.files && e.target.files[0]) {
                    const f = e.target.files[0];
                    setInspectorFile(f);
                    setInspectorFileName(f.name);
                    runAntiTamperInspection(f);
                  }
                }}
                style={{ display: 'none' }}
              />
              <label
                htmlFor="nda-upload"
                style={{
                  cursor: 'pointer',
                  display: 'inline-block',
                  background: 'linear-gradient(135deg, #0284c7, #0369a1)',
                  color: 'white',
                  padding: '10px 24px',
                  borderRadius: '8px',
                  fontSize: '0.95rem',
                  fontWeight: 700,
                  marginBottom: '10px'
                }}
              >
                📁 Select or Drop PDF to Verify Integrity
              </label>

              <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
                {inspectorFileName ? `Selected File: ${inspectorFileName}` : 'Accepts any signed Master NDA or externally modified document.'}
              </div>
            </div>

            {/* SIMULATE TAMPER ATTACK DEMONSTRATION BUTTON */}
            {inspectorFile && (
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginBottom: '24px' }}>
                <button
                  onClick={() => runAntiTamperInspection()}
                  disabled={isInspecting}
                  style={{
                    background: '#2563eb',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 18px',
                    fontSize: '0.88rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  {isInspecting ? 'Inspecting...' : '🔄 Re-Verify File'}
                </button>

                <button
                  onClick={simulateTamperAttack}
                  disabled={isSimulatingTamper}
                  style={{
                    background: 'linear-gradient(135deg, #b91c1c, #991b1b)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 18px',
                    fontSize: '0.88rem',
                    fontWeight: 700,
                    cursor: isSimulatingTamper ? 'wait' : 'pointer',
                    boxShadow: '0 2px 10px rgba(185, 28, 28, 0.4)'
                  }}
                >
                  {isSimulatingTamper ? 'Simulating Attack...' : '⚡ Test Tamper Attack (Simulate Clause Modification)'}
                </button>
              </div>
            )}

            {/* VERIFICATION REPORT CARD */}
            {inspectorResult && (
              <div style={{
                background: inspectorResult.valid
                  ? 'linear-gradient(135deg, rgba(6, 78, 59, 0.95), rgba(15, 23, 42, 0.95))'
                  : 'linear-gradient(135deg, rgba(127, 29, 29, 0.95), rgba(15, 23, 42, 0.95))',
                border: inspectorResult.valid ? '2px solid #10b981' : '2px solid #ef4444',
                borderRadius: '12px',
                padding: '24px',
                boxShadow: inspectorResult.valid ? '0 8px 32px rgba(16, 185, 129, 0.3)' : '0 8px 32px rgba(239, 68, 68, 0.3)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                  <span style={{ fontSize: '32px' }}>{inspectorResult.valid ? '✅' : '🚨'}</span>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.3rem', fontWeight: 800, color: inspectorResult.valid ? '#34d399' : '#f87171' }}>
                      {inspectorResult.valid ? 'AUTHENTIC & UNTOUCHED' : 'FILE CORRUPTED & TAMPER DETECTED'}
                    </h3>
                    <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginTop: '2px' }}>
                      {inspectorResult.valid ? 'Cryptographic Anti-Tamper Container Verified' : 'Cryptographic Integrity Hash Mismatch'}
                    </div>
                  </div>
                </div>

                <p style={{ fontSize: '0.92rem', color: '#f1f5f9', lineHeight: '1.5', margin: '0 0 16px 0' }}>
                  {inspectorResult.message || inspectorResult.error}
                </p>

                <div style={{ background: 'rgba(0, 0, 0, 0.5)', borderRadius: '8px', padding: '14px', fontSize: '0.82rem', fontFamily: 'monospace', color: '#e2e8f0', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div><b>Signatory / Author:</b> {inspectorResult.signer || 'N/A'}</div>
                  <div><b>Seal Type:</b> SHA-256 HMAC Active Watermarked Container</div>
                  {inspectorResult.current_sha256 && (
                    <div style={{ wordBreak: 'break-all' }}><b>Current SHA-256:</b> {inspectorResult.current_sha256}</div>
                  )}
                  {inspectorResult.embedded_hmac && (
                    <div style={{ wordBreak: 'break-all' }}><b>Embedded Token:</b> {inspectorResult.embedded_hmac}</div>
                  )}
                  <div>
                    <b>Legal Status:</b>{' '}
                    <span style={{ color: inspectorResult.valid ? '#34d399' : '#f87171', fontWeight: 800 }}>
                      {inspectorResult.valid ? 'ENFORCEABLE & SEALED ORIGINAL' : 'VOID AB INITIO / REJECTED'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-TAB 3: FULL AGREEMENT TEXT REFERENCE */}
      {activeSubTab === 'full_agreement_text' && (
        <div style={{
          background: 'rgba(30, 41, 59, 0.8)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: '16px',
          padding: '28px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
        }}>
          <div style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', paddingBottom: '14px', marginBottom: '20px' }}>
            <h2 style={{ margin: '0 0 6px 0', fontSize: '1.4rem', fontWeight: 800, color: '#f8fafc' }}>
              Master Services, Confidentiality, Intellectual Property, and Security Agreement
            </h2>
            <div style={{ color: '#94a3b8', fontSize: '0.88rem' }}>
              Comprehensive 32-clause sovereign corporate agreement governing all collaborations with Stehouwer Publishing, LLC.
            </div>
          </div>

          {schema && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {schema.sections.map(
( sec, sIdx) => (
                <div key={sec.id} style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '12px', padding: '18px' }}>
                  <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 800, textTransform: 'uppercase' }}>
                    Section {sIdx + 1}
                  </div>
                  <h3 style={{ margin: '2px 0 6px 0', fontSize: '1.15rem', color: '#f8fafc' }}>{sec.title}</h3>
                  <p style={{ margin: '0 0 14px 0', color: '#94a3b8', fontSize: '0.85rem' }}>{sec.summary}</p>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {sec.clauses.map(
( c) => (
                      <div key={c.id} style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '8px' }}>
                        <div style={{ fontWeight: 700, color: '#e2e8f0', fontSize: '0.88rem', marginBottom: '2px' }}>
                          <span style={{ color: '#38bdf8', marginRight: '6px' }}>[{c.code}]</span> {c.title}
                        </div>
                        <div style={{ color: '#94a3b8', fontSize: '0.83rem', lineHeight: '1.4' }}>{c.text}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
