import { useEffect, useRef, useState } from 'react';
import { auth } from '../firebase.js';
import { chatAuthHeaders } from '/src/utils/chatAuth.js';
import OutreachReceipts from './OutreachReceipts.jsx';

const ORIGIN = 'http://127.0.0.1:5191';
const LOCAL_NOTICE = 'Campaign tools run on your AI-BS workstation. Open http://localhost:5173/?tab=campaign_automation there. Remote campaign access has not been configured.';
export function campaignServiceAvailable(origin = globalThis.location?.origin) {
  return origin === 'http://localhost:5173' || origin === 'http://127.0.0.1:5173';
}
const BRANDS = { productions: 'Stehouwer Productions', publishing: 'Stehouwer Publishing' };
const EMAIL_DOMAINS = { productions: 'stehouwerproductions.com', publishing: 'stehouwer-publishing.com' };
export function validateCampaignSes(brand, sender, reply) {
  const domain = EMAIL_DOMAINS[brand];
  if (!domain || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(sender.trim()) || sender.trim().toLowerCase().split('@')[1] !== domain) {
    return `Fix the From address: use an email address on ${domain || 'the selected brand domain'}.`;
  }
  if (!['brett@stehouwerproductions.com', 'footballstar0325@gmail.com'].includes(reply.trim().toLowerCase())) {
    return 'Fix Reply-To: use brett@stehouwerproductions.com (or the previously approved Gmail address).';
  }
  return '';
}

export function campaignValidationDetail(value) {
  const detail = typeof value?.detail === 'string' ? value.detail.slice(0, 300) : '';
  return [
    'Use a sender on the selected brand domain and the approved reply address',
    'SES setup accepts sender metadata only; AWS credentials are never accepted',
    'SES domain, profile and region are fixed by the owned brand setup'
  ].includes(detail) ? detail : '';
}
const inputStyle = { padding: '9px', borderRadius: '5px', border: '1px solid #475569', background: '#0f172a', color: '#f8fafc', maxWidth: '100%', boxSizing: 'border-box' };
const panelStyle = { padding: '18px', background: '#111827', border: '1px solid #334155', borderRadius: '10px', marginBottom: '16px' };

export async function campaignRequest(path, { method = 'GET', body, signal, expectedUid, fetchImpl = globalThis.fetch } = {}) {
  const existingDraftUpdate = method === 'PUT' && /^\/campaigns\/[a-zA-Z0-9_-]+$/.test(path);
  const receiptRead = method === 'GET' && /^\/outreach-records\/(productions|publishing)$/.test(path);
  const existingReadOrCreate = ['GET', 'POST'].includes(method) && /^\/(?:state|connections\/(?:textbee|ses)(?:\/(?:productions|publishing)(?:\/verify)?)?|import|campaigns(?:\/[a-zA-Z0-9_-]+\/prepare)?)$/.test(path);
  if (!existingDraftUpdate && !existingReadOrCreate && !receiptRead) {
    throw new Error('Unsupported campaign operation.');
  }
  if (!campaignServiceAvailable()) throw new Error(LOCAL_NOTICE);
  const user = auth.currentUser;
  const guard = () => {
    if (!user || (expectedUid && user.uid !== expectedUid) || auth.currentUser !== user || signal?.aborted) {
      throw new DOMException('Campaign request cancelled because its account or abort state changed.', 'AbortError');
    }
  };
  guard();
  const headers = await chatAuthHeaders(body === undefined ? {} : { 'Content-Type': 'application/json' }, user.uid);
  guard();
  const requestSignal = signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000);
  const response = await fetchImpl(ORIGIN + '/api/brand-campaigns' + path, {
    method, headers, body: body === undefined ? undefined : JSON.stringify(body),
    signal: requestSignal, credentials: 'omit', cache: 'no-store', redirect: 'error'
  });
  guard();
  if (response.status === 400) {
    let detail = '';
    try { detail = campaignValidationDetail(await response.json()); } catch { /* Ignore non-JSON error pages. */ }
    guard();
    throw new Error(detail ? `Check email settings: ${detail}.` : 'Campaign service rejected these settings (HTTP 400). Check the selected brand and required fields.');
  }
  if (!response.ok) throw new Error([401, 403].includes(response.status)
    ? 'Sign in with an authorized administrator account to manage campaigns.'
    : `Campaign service could not complete this request (HTTP ${response.status}).`);
  const value = await response.json();
  guard();
  return value;
}

export function parseCampaignCsv(text) {
  if (typeof text !== 'string' || text.length > 2000000) throw new Error('Choose a CSV file smaller than 2 MB.');
  const records = []; let record = []; let value = ''; let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') { value += '"'; index += 1; }
      else if (quoted || value === '') quoted = !quoted;
      else throw new Error('CSV contains an invalid quote.');
    } else if (character === ',' && !quoted) { record.push(value); value = ''; }
    else if ((character === '\n' || character === '\r') && !quoted) {
      if (character === '\r' && text[index + 1] === '\n') index += 1;
      record.push(value); if (record.some(cell => cell.trim())) records.push(record);
      record = []; value = '';
    } else value += character;
    if (records.length > 1000 || value.length > 16000) throw new Error('CSV exceeds the 1000-row or field-size limit.');
  }
  if (quoted) throw new Error('CSV contains an unclosed quote.');
  record.push(value); if (record.some(cell => cell.trim())) records.push(record);
  const headers = (records.shift() || []).map(cell => cell.replace(/^\uFEFF/, '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, ''));
  if (!headers.length || records.some(row => row.length !== headers.length)) throw new Error('CSV column counts do not match the header.');
  if (records.length > 1000) throw new Error('Import at most 1000 rows at a time.');
  return records.map(row => {
    const mapped = Object.fromEntries(headers.map((header, index) => [header, row[index].trim()]));
    return { ...mapped, business: mapped.business || mapped.company || mapped.business_organization || '',
      email: mapped.email || mapped.email_address || '', phone: mapped.phone || mapped.phone_number || '' };
  });
}

export function campaignRecipientOptions(contacts, channel, search = '', page = 0, sourcedOnly = false) {
  const query = search.trim().toLowerCase();
  return contacts.filter(contact => {
    const valid = channel === 'email' ? /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(contact.email || '') : /^\+?[0-9 ()-]{7,25}$/.test(contact.phone || '');
    return valid && (!sourcedOnly || (Array.isArray(contact.research_metadata?.source_urls) && contact.research_metadata.source_urls.length > 0)) &&
      (!query || `${contact.business || ''} ${contact.email || ''} ${contact.phone || ''}`.toLowerCase().includes(query));
  }).slice(Math.max(0, page) * 50, Math.max(0, page) * 50 + 50);
}

export function selectCampaignRecipients(selected, visibleIds) {
  return [...new Set([...selected, ...visibleIds])].slice(0, 1000);
}

export function campaignResearchDetails(contact) {
  const metadata = contact.research_metadata || {};
  const strings = field => Array.isArray(metadata[field]) ? metadata[field].filter(value => typeof value === 'string').slice(0, 10) : [];
  return {
    warnings: [...strings('purpose_restrictions'), ...strings('submission_policies'), ...strings('outreach_eligibility')],
    sources: strings('source_urls').filter(value => {
      try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password; }
      catch { return false; }
    }).slice(0, 5)
  };
}

export default function BrandCampaignManager({ currentUser }) {
  const [brand, setBrand] = useState('productions');
  const [savedState, setState] = useState(null);
  const [savedConnection, setConnection] = useState(null);
  const [loadedScope, setLoadedScope] = useState('');
  const [preview, setPreview] = useState(null);
  const [name, setName] = useState('');
  const [channel, setChannel] = useState('email');
  const [subject, setSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [editingDraft, setEditingDraft] = useState(null);
  const [selectedContacts, setSelectedContacts] = useState([]);
  const [recipientSearch, setRecipientSearch] = useState('');
  const [recipientPage, setRecipientPage] = useState(0);
  const [sourcedOnly, setSourcedOnly] = useState(false);
  const [senderEmail, setSenderEmail] = useState('julie@stehouwerproductions.com');
  const [replyTo, setReplyTo] = useState('brett@stehouwerproductions.com');
  const [apiKey, setApiKey] = useState('');
  const [deviceId, setDeviceId] = useState('6af8f93fdeaa343f04cdf43d');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const active = useRef(null);
  const generation = useRef(0);
  const editChannelLoad = useRef(false);
  const owner = currentUser?.uid || '';
  const serviceAvailable = campaignServiceAvailable();
  const scope = JSON.stringify([owner, brand]);
  const state = loadedScope === scope ? savedState : null;
  const connection = loadedScope === scope ? savedConnection : null;

  async function perform(action, success = '') {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    const version = ++generation.current;
    setBusy(true); setError(''); setMessage('');
    const request = (path, options = {}) => campaignRequest(path, { ...options, signal: controller.signal, expectedUid: owner });
    try {
      const result = await action(request);
      if (controller.signal.aborted || version !== generation.current) return;
      const nextState = await request('/state');
      if (!['contacts', 'imports', 'campaigns', 'brands'].every(field => Array.isArray(nextState?.[field]))) throw new Error('Campaign service returned invalid saved data.');
      const nextConnection = result?.provider !== 'aws_ses' && (result?.device_id || result?.api_key_verified !== undefined) ? result : await request(`/connections/textbee/${brand}`);
      if (controller.signal.aborted || version !== generation.current) return;
      setState(nextState); setConnection(nextConnection); setLoadedScope(scope);
      if (nextConnection.device_id) setDeviceId(nextConnection.device_id);
      const emailConnection = nextState.providers?.[brand]?.email;
      if (emailConnection?.sender_email) setSenderEmail(emailConnection.sender_email);
      if (emailConnection?.reply_to) setReplyTo(emailConnection.reply_to);
      if (controller.signal.aborted || version !== generation.current) return;
      setMessage(success || 'Campaign settings refreshed.');
      return result;
    } catch (failure) {
      if (!controller.signal.aborted && version === generation.current) setError(failure.message || 'Campaign service is unavailable.');
    } finally {
      if (version === generation.current) setBusy(false);
    }
  }

  useEffect(() => {
    active.current?.abort(); generation.current += 1;
    setState(null); setConnection(null); setApiKey(''); setPreview(null); setError(''); setMessage('');
    setName(''); setSubject(''); setDraftBody('');
    setEditingDraft(null);
    setSelectedContacts([]); setRecipientSearch('');
    setSenderEmail(brand === 'productions' ? 'julie@stehouwerproductions.com' : 'julie@stehouwer-publishing.com');
    setReplyTo('brett@stehouwerproductions.com');
    if (owner && serviceAvailable) perform(async () => {}, '');
    return () => { active.current?.abort(); generation.current += 1; };
  }, [owner, brand, serviceAvailable]);

  useEffect(() => {
    if (editChannelLoad.current) editChannelLoad.current = false;
    else setSelectedContacts([]);
    setRecipientSearch('');
  }, [owner, brand, channel]);
  useEffect(() => { setRecipientPage(0); }, [owner, brand, channel, recipientSearch, sourcedOnly, savedState]);

  const provider = connection ? { ...connection, ...connection.last_verification } : null;
  const emailProvider = state?.providers?.[brand]?.email;
  const sesValidation = validateCampaignSes(brand, senderEmail, replyTo);
  const emailVerification = emailProvider ? { ...emailProvider, ...emailProvider.last_verification } : null;
  const brandRows = field => Array.isArray(state?.[field]) ? state[field].filter(row => row.brand === brand) : [];
  const contacts = brandRows('contacts');
  const campaigns = brandRows('campaigns');
  const imports = brandRows('imports');
  const recipientOptions = campaignRecipientOptions(contacts, channel, recipientSearch, recipientPage, sourcedOnly);
  const nextRecipientOptions = campaignRecipientOptions(contacts, channel, recipientSearch, recipientPage + 1, sourcedOnly);
  const matchingRecipientCount = contacts.filter(contact => campaignRecipientOptions([contact], channel, recipientSearch, 0, sourcedOnly).length).length;
  const saveDraftCopy = contactIds => perform(async request => {
    const result = await request(editingDraft ? `/campaigns/${editingDraft.id}` : '/campaigns', {
      method: editingDraft ? 'PUT' : 'POST', body: { brand, channel, name: name.trim(), subject: subject.trim(), body: draftBody,
        contact_ids: contactIds, ...(editingDraft ? { revision: editingDraft.revision } : {}) }
    });
    if (editingDraft && result?.campaign) setEditingDraft({ id: result.campaign.id, revision: result.campaign.revision });
    return result;
  }, contactIds.length ? 'Draft saved. Prepare it to review recipients; no messages were sent.' : 'Copy saved for review with no recipients. No messages were sent.');
  async function previewCsv(file) {
    if (!file) return;
    const version = generation.current;
    const user = auth.currentUser;
    setError(''); setPreview(null);
    try {
      if (file.size > 2000000) throw new Error('Choose a CSV file smaller than 2 MB.');
      const text = await file.text();
      const rows = parseCampaignCsv(text);
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
      const source_sha256 = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
      if (generation.current !== version || auth.currentUser !== user) return;
      setPreview({ rows, source_name: file.name.slice(0, 160), source_sha256 });
    } catch (failure) { setError(failure.message || 'CSV could not be read.'); }
  }
  if (!serviceAvailable) return <section style={{ color: '#f8fafc', padding: '16px', maxWidth: '1100px' }}>
    <h2>Email &amp; SMS Campaigns</h2>
    <p role="status">{LOCAL_NOTICE}</p>
  </section>;
  return <section style={{ color: '#f8fafc', padding: '16px', maxWidth: '1100px' }}>
    <h2>Email &amp; SMS Campaigns</h2>
    <p>Keep Productions and Publishing contacts, drafts and provider connections separate.</p>
    <label>Brand <select style={inputStyle} value={brand} onChange={event => { if (event.target.value === brand) return; setSelectedContacts([]); setRecipientSearch(''); setApiKey(''); setDeviceId(event.target.value === 'productions' ? '6af8f93fdeaa343f04cdf43d' : ''); setState(null); setConnection(null); setPreview(null); setBrand(event.target.value); }}>
      {Object.entries(BRANDS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </select></label>
    <button disabled={busy || !owner} onClick={() => perform(async () => {})}>Refresh</button>
    {!owner && <p role="alert">Sign in with an authorized administrator account.</p>}
    {error && <p role="alert" style={{ color: '#fca5a5' }}>{error}</p>}
    {message && <p role="status" style={{ color: '#86efac' }}>{message}</p>}
    <OutreachReceipts key={scope} owner={owner} brand={brand} request={campaignRequest} />

    <form style={{ ...panelStyle, marginTop: '16px' }} onSubmit={event => {
      event.preventDefault();
      const validation = validateCampaignSes(brand, senderEmail, replyTo);
      if (validation) { setError(validation); return; }
      perform(request => request('/connections/ses', { method: 'POST', body: { brand, sender_email: senderEmail.trim(), reply_to: replyTo.trim() } }), 'Pending AWS SES email settings saved. Verify AWS SES to read the current domain status. No message was sent.');
    }}>
      <h3>Email delivery — AWS SES</h3>
      <p>These AWS SES settings are separate from the IONOS outreach receipts above. Saving or verifying them does not change messages already sent through IONOS.</p>
      <p>Set the proposed From address for {BRANDS[brand]} and the address where replies should arrive. Saving these settings does not create Julie’s mailbox or enable delivery.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
        <label>Proposed From address<br /><input style={inputStyle} type="email" required value={senderEmail} onChange={event => setSenderEmail(event.target.value)} /></label>
        <label>Reply-To address<br /><input style={inputStyle} type="email" required value={replyTo} onChange={event => setReplyTo(event.target.value)} /></label>
      </div>
      <p>Brett’s Reply-To defaults to brett@stehouwerproductions.com. Julie’s sender mailbox and Brett’s reply mailbox have not been checked. Saving does not create either mailbox or forwarding.</p>
      <p>For {BRANDS[brand]}, From must end with @{EMAIL_DOMAINS[brand]}. Approved Reply-To: brett@stehouwerproductions.com.</p>
      {sesValidation && <p role="alert" style={{ color: '#fca5a5' }}>{sesValidation}</p>}
      <button disabled={busy || !owner || !!sesValidation} type="submit">Save pending email settings</button>{' '}
      <button disabled={busy || !owner} type="button" onClick={() => perform(request => request(`/connections/ses/${brand}/verify`, { method: 'POST', body: {} }), 'AWS SES status checked. This read-only verification did not send email or enable dispatch.')}>Verify AWS SES</button>
      {!emailVerification ? <p>AWS email status has not loaded.</p> : <div>
        <p>Saved From: {emailProvider.sender_email || 'Not configured'} · Reply-To: {emailProvider.reply_to || 'Not configured'} · Region: {emailProvider.region || 'Not checked'}.</p>
        <p>Domain identity: {emailVerification.domain_verification_status || (emailVerification.domain_identity_verified === true ? 'Verified' : 'Not verified')} · DKIM: {emailVerification.dkim_status || 'Not checked'} · SES sandbox: {emailVerification.sandbox === true ? 'Yes' : emailVerification.sandbox === false ? 'No' : 'Unknown'}.</p>
        <p>Sending quota: {emailVerification.quota?.max_24_hour_send ?? 'Not checked'} per 24 hours · Rate: {emailVerification.quota?.max_send_rate ?? 'Not checked'} per second · Sent in last 24 hours: {emailVerification.quota?.sent_last_24_hours ?? 'Not checked'}.</p>
        <p>Dispatch: {emailProvider.held === true ? 'Held' : 'Not qualified'}. {emailProvider.hold_reason} Identity/DKIM verification is not permission to send.</p>
      </div>}
    </form>

    <form style={{ ...panelStyle, marginTop: '16px' }} onSubmit={event => {
      event.preventDefault();
      const submittedKey = apiKey; setApiKey('');
      perform(request => request('/connections/textbee', { method: 'POST', body: { brand, api_key: submittedKey, device_id: deviceId.trim() } }), 'TextBee connection saved locally. Verify the device next.');
    }}>
      <h3>Connect TextBee for {BRANDS[brand]}</h3>
      <p>Create a new API key in your own TextBee account, then paste it here locally. Do not send it in chat. The key is write-only and clears when you save.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
        <label>New TextBee API key{provider?.configured ? ' (leave empty to keep the saved key)' : ''}<br /><input style={inputStyle} type="password" autoComplete="new-password" value={apiKey} onChange={event => setApiKey(event.target.value)} required={!provider?.configured} /></label>
        <label>Device ID<br /><input style={inputStyle} value={deviceId} onChange={event => setDeviceId(event.target.value)} required /></label>
      </div>
      <p>Use the device ID registered to this brand in your TextBee account. Keep that phone powered on and connected for the gateway to work.</p>
      <button type="submit" disabled={busy || !owner || (!apiKey.trim() && !provider?.configured) || !/^[a-fA-F0-9]{24}$/.test(deviceId.trim())}>Save connection</button>{' '}
      <button type="button" disabled={busy || !owner} onClick={() => perform(request => request(`/connections/textbee/${brand}/verify`, { method: 'POST', body: {} }), 'TextBee verification completed. Check the connection status below.')}>Verify device</button>
      <p>Connection: {provider?.configured === true ? 'Configured' : provider?.configured === false ? 'Not configured' : 'Not yet checked'}. Device: {provider?.online === true ? 'Online' : provider?.online === false ? 'Offline' : 'Not yet verified'}.</p>
      {provider?.verified && <dl><dt>Verified device</dt><dd>{provider.device_name || 'Name unavailable'}</dd><dt>App version</dt><dd>{provider.app_version || 'Unavailable'}{provider.app_build ? ` (build ${provider.app_build})` : ''}</dd><dt>Device enabled</dt><dd>{provider.enabled === true ? 'Yes' : provider.enabled === false ? 'No' : 'Unknown'}</dd><dt>Last checked</dt><dd>{provider.checked_at || 'Unavailable'}</dd><dt>Last heartbeat</dt><dd>{provider.last_heartbeat || 'Unavailable'}</dd></dl>}
      <p>Saving and verifying a connection does not send a text message. Recipients still need documented SMS consent.</p>
      {state?.providers?.[brand] && <div><p>Email provider: {state.providers[brand].email?.configured ? 'Sender configured' : 'Not configured'}; {state.providers[brand].email?.connection_verified ? 'verified' : 'connection not verified'}. {state.providers[brand].email?.hold_reason}</p><p>SMS dispatch: {state.providers[brand].sms?.held ? 'Held' : 'Not reported'}. {state.providers[brand].sms?.hold_reason}</p></div>}
    </form>
    <div style={panelStyle}>
      <h3>{BRANDS[brand]} contacts</h3>
      {state ? <p>{contacts.length} saved contacts · {contacts.filter(contact => contact.email).length} with an email address · {imports.length} recorded imports.</p> : <p>Saved contact counts are unavailable until the campaign service responds.</p>}
      <p>An email address or phone number alone is not consent. Imported data does not establish SMS permission.</p>
      <label>Preview a CSV file <input type="file" accept=".csv,text/csv" disabled={busy || !owner} onChange={event => { previewCsv(event.target.files?.[0]); event.target.value = ''; }} /></label>
      {preview && <div><p>{preview.source_name}: {preview.rows.length} rows ready for review. Import records the source filename and SHA-256 provenance; it does not create a campaign or send messages.</p>
        <div style={{ overflow: 'auto', maxHeight: '180px' }}><table><thead><tr>{Object.keys(preview.rows[0] || {}).slice(0, 8).map(key => <th key={key}>{key}</th>)}</tr></thead><tbody>{preview.rows.slice(0, 5).map((row, index) => <tr key={index}>{Object.values(row).slice(0, 8).map((cell, column) => <td key={column} style={{ padding: '6px' }}>{String(cell).slice(0, 100)}</td>)}</tr>)}</tbody></table></div>
        <button disabled={busy || !preview.rows.length} onClick={() => perform(request => request('/import', { method: 'POST', body: { brand, ...preview } }), 'Contact import recorded. Review the saved contacts before preparing a draft.').then(() => setPreview(null))}>Import reviewed rows for {BRANDS[brand]}</button>
      </div>}
      {imports.slice(0, 5).map((entry, index) => <p key={entry.id || index}>Source: {entry.source_name || 'Recorded import'}{entry.source_sha256 ? ` · SHA-256 ${entry.source_sha256}` : ''}</p>)}
    </div>
    <form style={panelStyle} onSubmit={event => { event.preventDefault(); if (!selectedContacts.length || selectedContacts.length > 1000) return; saveDraftCopy(selectedContacts); }}>
      <h3>{editingDraft ? `Editing copy · revision ${editingDraft.revision}` : 'Create a draft'}</h3>
      {editingDraft && <button type="button" onClick={() => { setEditingDraft(null); setName(''); setSubject(''); setDraftBody(''); setSelectedContacts([]); }}>Cancel editing</button>}
      <p>This draft belongs only to {BRANDS[brand]}. Preparing recipients does not send messages.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
        <label>Draft name<br /><input required style={inputStyle} value={name} maxLength={160} onChange={event => setName(event.target.value)} /></label>
        <label>Channel<br /><select style={inputStyle} value={channel} onChange={event => { setSelectedContacts([]); setRecipientSearch(''); setChannel(event.target.value); }}><option value="email">Email</option><option value="sms">SMS</option></select></label>
        {channel === 'email' && <label>Subject<br /><input required style={inputStyle} value={subject} maxLength={200} onChange={event => setSubject(event.target.value)} /></label>}
      </div>
      <label>Message<br /><textarea required style={{ ...inputStyle, width: '100%', minHeight: '120px', marginTop: '8px' }} value={draftBody} maxLength={10000} onChange={event => setDraftBody(event.target.value)} /></label>
      <fieldset style={{ border: '1px solid #475569', margin: '12px 0', padding: '12px' }}>
        <legend>Review and select recipients</legend>
        <p>No contacts are included automatically. Review personal and RecDebut contacts before selecting them for this brand. Selection does not establish consent; the service applies channel consent and provider checks during preparation.</p>
        <label>Search name or address <input style={inputStyle} value={recipientSearch} onChange={event => setRecipientSearch(event.target.value)} /></label>
        <p><label><input type="checkbox" checked={sourcedOnly} onChange={event => setSourcedOnly(event.target.checked)} /> Show sourced business contacts only</label></p>
        <p>{selectedContacts.length} selected / 1000 maximum. {matchingRecipientCount} matching contacts with a valid {channel === 'email' ? 'email address' : 'phone number'}; page {recipientPage + 1}, up to 50 per page.</p>
        <button type="button" disabled={recipientPage === 0} onClick={() => setRecipientPage(previous => Math.max(0, previous - 1))}>Previous 50</button>{' '}
        <button type="button" disabled={!nextRecipientOptions.length} onClick={() => setRecipientPage(previous => previous + 1)}>Next 50</button>{' '}
        <button type="button" disabled={busy || selectedContacts.length >= 1000} onClick={() => setSelectedContacts(previous => selectCampaignRecipients(previous, recipientOptions.map(contact => contact.id)))}>Select visible</button>{' '}
        <button type="button" onClick={() => setSelectedContacts([])}>Clear selection</button>
        <div style={{ maxHeight: '280px', overflowY: 'auto', marginTop: '10px' }}>
          {recipientOptions.length ? recipientOptions.map(contact => <div key={contact.id} style={{ padding: '7px', borderBottom: '1px solid #334155' }}><label style={{ display: 'block' }}>
            <input type="checkbox" checked={selectedContacts.includes(contact.id)} disabled={busy || (!selectedContacts.includes(contact.id) && selectedContacts.length >= 1000)} onChange={event => setSelectedContacts(previous => event.target.checked ? selectCampaignRecipients(previous, [contact.id]) : previous.filter(id => id !== contact.id))} />{' '}
            {contact.business || 'Unnamed contact'} — {channel === 'email' ? contact.email : contact.phone}
          </label><ContactResearch contact={contact} /></div>) : <p>No matching contacts with a valid address.</p>}
        </div>
      </fieldset>
      <button disabled={busy || !owner || !state || !selectedContacts.length || selectedContacts.length > 1000} type="submit">Save draft</button>
      {' '}<button type="button" disabled={busy || !owner || !state || !name.trim() || !draftBody.trim() || (channel === 'email' && !subject.trim())} onClick={() => saveDraftCopy([])}>Save copy for review (no recipients)</button>
    </form>
    <div style={panelStyle}>
      <h3>Saved drafts and delivery records</h3>
      {!state ? <p>Saved drafts are unavailable.</p> : !campaigns.length ? <p>No campaigns have been saved for this brand.</p> : campaigns.map(campaign => <article key={campaign.id} style={{ borderTop: '1px solid #334155', padding: '12px 0' }}>
        <strong>{campaign.name}</strong><p>{campaign.channel} · {campaign.status || 'draft'} · revision {campaign.revision}</p>
        <button type="button" disabled={busy || !owner} onClick={() => { editChannelLoad.current = campaign.channel !== channel; setEditingDraft({ id: campaign.id, revision: campaign.revision }); setName(campaign.name); setChannel(campaign.channel); setSubject(campaign.subject || ''); setDraftBody(campaign.body); setSelectedContacts(Array.isArray(campaign.contact_ids) ? campaign.contact_ids.slice(0, 1000) : []); setRecipientSearch(''); }}>Edit copy</button>
        <p>{campaign.subject}</p><p style={{ whiteSpace: 'pre-wrap' }}>{campaign.body}</p>
        <p>Prepared: {campaign.counters?.prepared ?? 'Not reported'} · Blocked: {campaign.counters?.blocked ?? 'Not reported'} · Provider accepted: {campaign.counters?.provider_accepted ?? 'Not reported'} · Delivered: {campaign.counters?.delivered ?? 'Not reported'}</p>
        {campaign.utm_url && <p>Campaign attribution link: <code>{campaign.utm_url}</code></p>}
        {campaign.hold_reason && <p>{campaign.hold_reason}</p>}
        <button disabled={busy || !owner} onClick={() => perform(request => request(`/campaigns/${campaign.id}/prepare`, { method: 'POST', body: { revision: campaign.revision } }), 'Recipient preparation completed. Review the draft and provider holds; no messages were sent.')}>Prepare recipients</button>
      </article>)}
      <p>Delivery is not enabled in this screen. No send action is connected.</p>
    </div>
  </section>;
}

function ContactResearch({ contact }) {
  const research = campaignResearchDetails(contact);
  if (!research.warnings.length && !research.sources.length) return <p style={{ margin: '3px 0', color: '#cbd5e1', fontSize: '12px' }}>No research restrictions recorded here; review the source before selecting. Consent is not inferred.</p>;
  return <div style={{ fontSize: '12px', marginTop: '4px' }}>
    {research.warnings.map((warning, index) => <p key={index} style={{ margin: '3px 0', color: '#fde68a' }}>{warning === 'manual_review_required' ? 'Manual review required before outreach.' : warning}</p>)}
    {research.sources.map((url, index) => <p key={index} style={{ margin: '3px 0' }}><a href={url} target="_blank" rel="noopener noreferrer" style={{ color: '#7dd3fc' }}>Research source {index + 1}: {url}</a></p>)}
    <p style={{ margin: '3px 0' }}>Research does not select this contact or establish consent.</p>
  </div>;
}
