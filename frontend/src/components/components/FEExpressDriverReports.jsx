/** @jsxRuntime classic */
import React, { useState, useEffect } from '/src/utils/applicationReact.js';

import { usePortalState } from '/src/utils/feExpressWorkspace.jsx';

const today = () => new Date().toLocaleDateString('en-CA');
const emptyDay = () => ({ revision: 0, unit: '', loaded_miles: 0, deadhead_miles: 0, driving_hours: 0, other_duty_hours: 0, fuel_gallons: 0, fuel_cost: 0, other_expenses: 0, notes: '' });
/** @param {string} value */
const monday = value => { const d = new Date(value + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - (d.getUTCDay() + 6) % 7); return d.toISOString().slice(0, 10); };
const emptyShipment = () => ({ revision: 0, load_number: '', pickup_date: today(), delivery_date: today(), origin: '', destination: '', broker: '', agreed_rate: 0, status: 'ASSIGNED', notes: '', dispatch_id: '' });
const dayFields = [['loaded_miles', 'Loaded miles'], ['deadhead_miles', 'Deadhead miles'], ['driving_hours', 'Driving hours'], ['other_duty_hours', 'Other duty hours'], ['fuel_gallons', 'Fuel gallons'], ['fuel_cost', 'Fuel cost ($)'], ['other_expenses', 'Other expenses ($)']];
/** @type {Record<string,string>} */
const labels = { rate_confirmation: 'Rate confirmation', bol: 'Bill of lading (BOL)', pod: 'Proof of delivery', fuel_receipt: 'Fuel / expense receipt', other: 'Other paperwork' };
const panel = { background: '#142033', padding: 18, border: '1px solid #334155', borderRadius: 10, marginBottom: 18 };
/** @type {import("react").CSSProperties} */
const input = { display: 'block', width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5, background: '#0f172a', color: '#f8fafc', border: '1px solid #64748b', borderRadius: 5, minHeight: 42 };
const grid = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,200px),1fr))', gap: 14 };
const button = { background: '#0369a1', color: 'white', padding: '11px 15px', borderRadius: 6, border: '1px solid #38bdf8', cursor: 'pointer', margin: '10px 10px 0 0' };
/** @param {any} value */
const numeric = value => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
/** @param {any} value */
const money = value => value == null ? '—' : '$' + Number(value).toFixed(2);
/** @param {any} record @returns {ReturnType<typeof emptyDay>} */
const dayOnly = record => /** @type {ReturnType<typeof emptyDay>} */ (Object.fromEntries(Object.keys(emptyDay()).map(key => [key, record[key] ?? (/** @type {any} */ (emptyDay()))[key]])));
/** @param {any} record @returns {ReturnType<typeof emptyShipment>} */
const shipmentOnly = record => /** @type {ReturnType<typeof emptyShipment>} */ (Object.fromEntries(Object.keys(emptyShipment()).map(key => [key, record[key] ?? (/** @type {any} */ (emptyShipment()))[key]])));

/** @param {{baseUrl:string,request?:typeof fetch,activeDispatches?:any[],driverId?:string,onDriverChange?:(id:string)=>void,logRequest?:number,selectedDispatch?:string}} props */
export default function FEExpressDriverReports({ baseUrl, request = fetch, activeDispatches = [], driverId, onDriverChange, logRequest = 0, selectedDispatch = '' }) {
  const [drivers, setDrivers] = useState(/** @type {any[]} */ ([])), [localDriver, setLocalDriver] = useState('OWNER-DEVIN');
  const driver = driverId ?? localDriver;
  const setDriver = onDriverChange || setLocalDriver;
  useEffect(() => {
    if (!logRequest) return;
    requestAnimationFrame(() => { const field = document.getElementById('fe-employee-log-date'); field?.scrollIntoView({ block: 'center' }); field?.focus(); });
  }, [logRequest]);
  const [week, setWeek] = usePortalState('report.week', today()), [logDate, setLogDate] = usePortalState('report.logDate', today());
  const [report, setReport] = useState(/** @type {any} */ (null)), [dayDraft, setDay] = usePortalState(`report.day:${driver}:${logDate}`, /** @type {ReturnType<typeof emptyDay>|null} */ (null));
  const day = dayDraft || dayOnly(report?.driver.driver_id === driver && report?.days.find((/** @type {any} */ d) => d.log_date === logDate) || emptyDay());
  const [shipment, setShipment] = usePortalState(`report.shipment:${driver}:${monday(week)}`, emptyShipment), [shipmentId, setShipmentId] = usePortalState(`report.shipmentId:${driver}:${monday(week)}`, '');
  const [kind, setKind] = usePortalState('report.kind', 'rate_confirmation'), [file, setFile] = useState(/** @type {File|null} */ (null));
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(''), [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [exportFormat, setExportFormat] = usePortalState('report.exportFormat', 'pdf');
  const [sheetDrafts, setSheetDrafts] = usePortalState('report.sheetDrafts', /** @type {Record<string,Record<string,ReturnType<typeof emptyDay>>>} */ ({}));
  const sheetKey = report?.driver.driver_id === driver && report.week_start === monday(week) ? `${driver}:${report.week_start}` : '';
  const sheetRows = sheetDrafts[sheetKey] || {};
  const unsavedDays = Object.values(sheetDrafts).reduce((n, rows) => n + Object.keys(rows).length, 0);
  useEffect(() => {
    if (!unsavedDays) return;
    /** @param {BeforeUnloadEvent} e */
    const warn = e => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [unsavedDays]);
  const [packetRate, setPacketRate] = useState(''), [packetDelivery, setPacketDelivery] = useState('');
  useEffect(() => { setPacketRate(''); setPacketDelivery(''); }, [shipmentId]);
  const generation = React.useRef(0), uploading = React.useRef(/** @type {{key:string,id:string}|null} */ (null));
  const api = `${baseUrl.replace(/\/$/, '')}/api/v1/fe-express/driver-reports`;
  const query = `?driver_id=${encodeURIComponent(driver)}&week=${encodeURIComponent(week)}`;
  /** @param {string} path @param {RequestInit} [options] */
  async function checked(path, options) {
    const response = await request(api + path, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}). Check the entered fields and refresh before saving again.`);
    }
    return response;
  }
  async function refresh() {
    const current = ++generation.current;
    setReady(false);
    try {
      const [d, r] = await Promise.all([checked('/drivers').then(r => r.json()), checked('/weekly' + query).then(r => r.json())]);
      if (current !== generation.current) return;
      setDrivers(d.drivers); setReport(r); setReady(true); setError('');
      return r;
    } catch (e) { if (current === generation.current) { setReport(null); setError((e instanceof Error ? e.message : 'Request failed')); } }
  }
  useEffect(() => { setMessage(''); refresh(); return () => { generation.current++; }; }, [driver, week, api, request]);

  /** @param {()=>Promise<any>} work */
  async function action(work) {
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try { await work(); } catch (e) { setError((e instanceof Error ? e.message : 'Request failed') + ' Refresh to confirm what was saved before retrying.'); setReady(false); }
    finally { setBusy(false); }
  }
  /** @param {import("react").FormEvent} event */
  async function saveDay(event) {
    event.preventDefault();
    await action(async () => {
      await checked(`/days/${encodeURIComponent(driver)}/${logDate}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(day) });
      setDay(null);
      const r = await refresh();
      if (r) setMessage(`Daily log saved for ${logDate}.`);
    });
  }
  /** @param {string} date @param {string} key @param {string|number} value */
  function editSheetDay(date, key, value) {
    const saved = dayOnly(report.days.find((/** @type {any} */ d) => d.log_date === date) || emptyDay());
    setSheetDrafts((/** @type {Record<string,Record<string,ReturnType<typeof emptyDay>>>} */ previous) => ({ ...previous, [sheetKey]: { ...previous[sheetKey], [date]: { ...(previous[sheetKey]?.[date] || saved), [key]: value } } }));
  }
  /** @param {string} context @param {string} date */
  function clearSheetDay(context, date) {
    setSheetDrafts((/** @type {Record<string,Record<string,ReturnType<typeof emptyDay>>>} */ previous) => {
      const rows = { ...previous[context] }; delete rows[date];
      return { ...previous, [context]: rows };
    });
  }
  /** @param {string} date */
  async function saveSheetDay(date) {
    const context = sheetKey, payload = sheetRows[date];
    if (!payload) return;
    await action(async () => {
      await checked(`/days/${encodeURIComponent(driver)}/${date}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      clearSheetDay(context, date);
      const r = await refresh();
      if (r) setMessage(`Spreadsheet day saved for ${date}.`);
    });
  }
  /** @param {import("react").FormEvent} event */
  async function saveShipment(event) {
    event.preventDefault();
    await action(async () => {
      const id = shipmentId || crypto.randomUUID();
      setShipmentId(id); // Retain the attempt identity even if the response is interrupted.
      const saved = await checked(`/shipments/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...shipment, driver_id: driver }) }).then(r => r.json());
      setShipmentId(id); setShipment(shipmentOnly(saved));
      await refresh(); setMessage('Shipment assignment saved. You can now attach its paperwork.');
    });
  }
  async function upload() {
    await action(async () => {
      if (!file || !shipmentId) throw new Error('Save a shipment and select its document first.');
      if (file.size > 10 * 1024 * 1024) throw new Error('Choose a file smaller than 10 MiB.');
      const key = `${shipmentId}:${kind}:${file.name}:${file.size}:${file.lastModified}`;
      if (uploading.current?.key !== key) uploading.current = { key, id: crypto.randomUUID() };
      const receipt = await checked(`/shipments/${shipmentId}/documents/${uploading.current.id}?kind=${kind}`, { method: 'PUT', headers: { 'Content-Type': file.type || (file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'application/octet-stream'), 'X-File-Name': encodeURIComponent(file.name) }, body: file }).then(r => r.json());
      await refresh(); setMessage(`${receipt.filename} saved with an integrity receipt.`); setFile(null); uploading.current = null;
    });
  }
  /** @param {string} path @param {string} name */
  async function download(path, name) {
    await action(async () => {
      const blob = await checked(path).then(r => r.blob());
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = name; document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      setMessage('Download prepared. Check your browser downloads.');
    });
  }
  async function printReport() {
    await action(async () => {
      const markup = await checked('/weekly.html' + query).then(r => r.text());
      const frame = document.createElement('iframe');
      frame.title = 'Weekly report print preview';
      frame.setAttribute('sandbox', 'allow-same-origin allow-modals');
      frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:1000px;height:800px;border:0';
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => { frame.remove(); reject(new Error('Print preview did not load. Download the PDF instead.')); }, 15000);
        frame.onload = () => {
          clearTimeout(timeout);
          try {
            if (!frame.contentWindow) throw new Error('Print preview is unavailable. Download the PDF instead.');
            frame.contentWindow.focus(); frame.contentWindow.print(); resolve(undefined);
          } catch (e) { frame.remove(); reject(e); }
        };
        frame.srcdoc = markup;
        document.body.appendChild(frame);
      });
      setTimeout(() => frame.remove(), 60000);
      setMessage('Print preview requested. Choose your printer or Save as PDF in the print dialog.');
    });
  }
  /** @param {any} s */
  function selectShipment(s) { setShipmentId(s.shipment_id); setShipment(shipmentOnly(s)); setFile(null); setMessage(''); }
  /** @param {string} id */
  function fromDispatch(id) {
    const d = activeDispatches.find((/** @type {any} */ d) => d.dispatch_id === id);
    if (!d) return;
    setShipmentId(''); setShipment({ ...emptyShipment(), dispatch_id: id, load_number: String(d.load_id || id), origin: d.origin || '', destination: d.destination || '', broker: d.broker_name || '', agreed_rate: Number(d.gross_pay || 0) });
  }
  const selected = report?.shipments.find((/** @type {any} */ s) => s.shipment_id === shipmentId);
  const disabled = busy || !ready;
  return <section aria-label="Driver reports" style={{ color: '#e2e8f0', padding: '12px 0', maxWidth: 1300, margin: 'auto' }}>
    <h2>Daily logs &amp; weekly driver reports</h2>
    {selectedDispatch && <aside style={panel}>Selected trip: <strong>{selectedDispatch}</strong>. Copy its details into a new shipment for the selected driver, then review and save. This does not copy mileage or expenses into daily logs.
      <button type="button" style={button} disabled={disabled} onClick={() => { if (window.confirm('Replace the current shipment form with this trip? Unsaved shipment form changes will be replaced.')) fromDispatch(selectedDispatch); }}>Copy selected trip into shipment</button>
    </aside>}
    <p>Keep each shipment’s assigned driver, load number, rate confirmation, BOL and delivery paperwork together. Enter miles and costs once per day.</p>
    <div style={panel}><div style={grid}>
      <label>Report driver<select style={input} value={driver} disabled={busy} onChange={e => setDriver(e.target.value)}>{drivers.length ? drivers.map((/** @type {any} */ d) => <option key={d.driver_id} value={d.driver_id}>{d.full_name}</option>) : <option value="OWNER-DEVIN">Devin (owner)</option>}</select></label>
      <label>Week containing<input style={input} type="date" value={week} disabled={busy} onChange={e => { if (e.target.value) { setWeek(e.target.value); setLogDate(e.target.value); } }} /></label>
    </div><button type="button" style={button} disabled={busy} onClick={() => action(refresh)}>Refresh records</button>
      <button type="button" style={button} disabled={disabled} onClick={() => download('/weekly.zip' + query, `fe-express-week-${report.week_start}.zip`)}>Download weekly file + paperwork</button>
      <label style={{ display: 'inline-block', marginTop: 12 }}>Save report as<select style={input} value={exportFormat} disabled={busy} onChange={e => setExportFormat(e.target.value)}><option value="pdf">PDF (.pdf)</option><option value="xlsx">Excel (.xlsx)</option><option value="csv">Spreadsheet data (.csv)</option><option value="json">Report data (.json)</option><option value="html">Web / printable page (.html)</option></select></label>
      <button type="button" style={button} disabled={disabled} onClick={() => download('/weekly.' + exportFormat + query, `fe-express-week-${report.week_start}.${exportFormat}`)}>Save report</button>
      <button type="button" style={button} disabled={disabled} onClick={printReport}>Print report</button>
      <p>PDF is ready to print. Excel, CSV, JSON and HTML are also available. The weekly paperwork ZIP keeps uploaded files in their original format.</p>
    </div>
    {error && <p role="alert" style={{ background: '#7f1d1d', padding: 12 }}>{error}</p>}
    {message && <p role="status" style={{ background: '#064e3b', padding: 12 }}>{message}</p>}
    {!report && !error && <p role="status">Loading saved records…</p>}
    {report && <div style={panel}><h3>Week: {report.week_start} – {report.week_end}</h3><div style={grid}>
      {[['Total miles', numeric(report.totals.total_miles)], ['Total hours', numeric(report.totals.total_hours)], ['Fuel purchased', `${numeric(report.totals.fuel_gallons)} gal`], ['Fuel cost', money(report.totals.fuel_cost)], ['Average fuel price / gallon', money(report.totals.average_fuel_price)], ['Fuel cost / mile', money(report.totals.fuel_cost_per_mile)], ['Other expenses', money(report.totals.other_expenses)], ['Agreed shipment rates', money(report.totals.agreed_revenue)], ['Revenue less recorded expenses', money(report.totals.revenue_less_recorded_expenses)]].map(([label, value]) => <div key={label}><div style={{ color: '#cbd5e1' }}>{label}</div><strong style={{ fontSize: 22 }}>{value}</strong></div>)}
    </div><p>{report.revenue_basis}</p><p>Days without entries (including days off): {report.missing_log_dates.join(', ') || 'None'}. Save a zero-mile log with a note for a day off.</p></div>}
    {sheetKey && <div style={panel}><h3>Driver spreadsheet — {report.driver.full_name}</h3>
      <p>Enter information in the cells, then save each day. Unsaved cells stay in this open page when you switch drivers or weeks. Closing the page loses unsaved entries. {unsavedDays > 0 && `${unsavedDays} unsaved day(s) across your spreadsheets.`}</p>
      <button type="button" style={button} disabled={disabled} onClick={() => download('/weekly.xlsx' + query, `fe-express-${driver.replace(/[^a-zA-Z0-9_-]/g, '_')}-${report.week_start}.xlsx`)}>Download driver Excel</button>
      <p>Excel includes all seven dates and saved information. You can edit the downloaded file; offline changes do not update the website. Save cells here before downloading. Excel totals show the saved snapshot.</p>
      <div role="region" aria-label="Weekly driver spreadsheet" tabIndex={0} style={{ overflowX: 'auto', marginTop: 12 }}><table style={{ borderCollapse: 'collapse', minWidth: 1600, width: '100%' }}>
        <thead><tr>{['Date', 'Truck / unit', ...dayFields.map(([, label]) => label), 'Notes', 'Save'].map(label => <th key={label} scope="col" style={{ padding: 8, textAlign: 'left' }}>{label}</th>)}</tr></thead>
        <tbody>{Array.from({ length: 7 }, (_, index) => {
          const utc = new Date(report.week_start + 'T00:00:00Z'); utc.setUTCDate(utc.getUTCDate() + index);
          const date = utc.toISOString().slice(0, 10), saved = report.days.find((/** @type {any} */ d) => d.log_date === date);
          const row = sheetRows[date] || dayOnly(saved || emptyDay()), dirty = Boolean(sheetRows[date]);
          return <tr key={date} style={{ borderTop: '1px solid #475569' }}><th scope="row" style={{ padding: 8 }}>{date}<small style={{ display: 'block' }}>{dirty ? 'Unsaved' : saved ? 'Saved' : 'No saved log'}</small></th>
            <td style={{ padding: 4 }}><input aria-label={`Truck / unit ${date}`} style={input} value={row.unit} maxLength={100} disabled={disabled} onChange={e => editSheetDay(date, 'unit', e.target.value)} /></td>
            {dayFields.map(([key, label]) => <td key={key} style={{ padding: 4 }}><input aria-label={`${label} ${date}`} style={input} type="number" min="0" step="0.01" value={(/** @type {any} */ (row))[key]} disabled={disabled} onChange={e => editSheetDay(date, key, e.target.value === '' ? '' : Number(e.target.value))} /></td>)}
            <td style={{ padding: 4 }}><textarea aria-label={`Notes ${date}`} style={{ ...input, minWidth: 220 }} value={row.notes} maxLength={4000} disabled={disabled} onChange={e => editSheetDay(date, 'notes', e.target.value)} /></td>
            <td style={{ padding: 4 }}><button type="button" style={button} aria-label={`Save day ${date}`} disabled={disabled || !dirty} onClick={() => saveSheetDay(date)}>Save day</button>{dirty && <button type="button" style={button} aria-label={`Discard unsaved day ${date}`} disabled={busy} onClick={() => clearSheetDay(sheetKey, date)}>Discard edits</button>}</td>
          </tr>;
        })}</tbody>
      </table></div>
    </div>}
    <form onSubmit={saveDay} style={panel}><h3>Daily driver log</h3><div style={grid}>
      <label>Log date<input id="fe-employee-log-date" style={input} type="date" required value={logDate} min={report?.week_start} max={report?.week_end} disabled={busy} onChange={e => setLogDate(e.target.value)} /></label>
      <label>Truck / unit<input style={input} value={day.unit} maxLength={100} disabled={busy} onChange={e => setDay({ ...day, unit: e.target.value })} /></label>
      {dayFields.map(([key, label]) => <label key={key}>{label}<input style={input} type="number" step="0.01" min="0" required value={(/** @type {any} */ (day))[key]} disabled={busy} onChange={e => setDay({ ...day, [key]: e.target.value === '' ? '' : Number(e.target.value) })} /></label>)}
    </div><label>Daily notes / expense details<textarea style={input} maxLength={4000} value={day.notes} disabled={busy} onChange={e => setDay({ ...day, notes: e.target.value })} /></label>
      <button style={button} disabled={disabled}>Save daily log</button><p>Recorded hours are manually entered; this report is not a certified electronic logbook or payroll calculation.</p>
    </form>
    <div style={panel}><h3>Shipment files for this week</h3><button type="button" style={button} disabled={busy} onClick={() => { setShipmentId(''); setShipment(emptyShipment()); setFile(null); }}>New shipment</button>
      {report?.shipments.length === 0 && <p>No saved shipments for this driver and week.</p>}
      {report?.shipments.map((/** @type {any} */ s) => <div key={s.shipment_id} style={{ borderBottom: '1px solid #475569', padding: '14px 0' }}><strong>{s.load_number}</strong> · {s.origin} → {s.destination} · {s.status} · {money(s.agreed_rate)}<div>Missing required paperwork: {s.missing_documents.map((/** @type {any} */ k) => labels[k]).join(', ') || 'None'}</div><button type="button" style={button} disabled={busy} onClick={() => selectShipment(s)}>Open shipment {s.load_number}</button></div>)}
    </div>
    <form onSubmit={saveShipment} style={panel}><h3>{shipmentId ? 'Edit shipment assignment' : 'New shipment assignment'}</h3><p>Assigned to: {drivers.find((/** @type {any} */ d) => d.driver_id === driver)?.full_name || 'Devin (owner)'}</p>
      {!shipmentId && <label>Optional: copy an existing haul<select style={input} value={shipment.dispatch_id} disabled={busy} onChange={e => fromDispatch(e.target.value)}><option value="">Enter manually</option>{activeDispatches.map((/** @type {any} */ d) => <option key={d.dispatch_id} value={d.dispatch_id}>{d.load_id || d.dispatch_id} — {d.origin} → {d.destination}</option>)}</select></label>}
      <div style={grid}>{[['load_number', 'Load / job number'], ['pickup_date', 'Pickup date'], ['delivery_date', 'Scheduled delivery date'], ['origin', 'Pickup location'], ['destination', 'Delivery location'], ['broker', 'Broker / customer'], ['agreed_rate', 'Agreed rate ($)']].map(([key, label]) => <label key={key}>{label}<input style={input} required={['load_number','pickup_date','delivery_date','agreed_rate'].includes(key)} type={key.endsWith('_date') ? 'date' : key === 'agreed_rate' ? 'number' : 'text'} min={key === 'agreed_rate' ? '0' : undefined} step={key === 'agreed_rate' ? '0.01' : undefined} maxLength={key === 'load_number' ? 100 : 300} value={(/** @type {any} */ (shipment))[key]} disabled={busy} onChange={e => setShipment({ ...shipment, [key]: key === 'agreed_rate' ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value })} /></label>)}
        <label>Shipment status<select style={input} value={shipment.status} disabled={busy} onChange={e => setShipment({ ...shipment, status: e.target.value })}>{['ASSIGNED','IN_TRANSIT','DELIVERED','CANCELLED'].map((/** @type {any} */ s) => <option key={s}>{s}</option>)}</select></label>
      </div><label>Shipment notes<textarea style={input} maxLength={4000} value={shipment.notes} disabled={busy} onChange={e => setShipment({ ...shipment, notes: e.target.value })} /></label><button style={button} disabled={disabled}>Save shipment assignment</button>
    </form>
    {shipmentId && <div style={panel}><h3>Paperwork for {shipment.load_number}</h3><p>PDF, JPEG or PNG. Maximum 10 MiB per file, 20 files / 50 MiB per shipment. Saved uploads are retained as separate documents.</p><div style={grid}>
      <label>Document type<select style={input} value={kind} disabled={busy} onChange={e => setKind(e.target.value)}>{Object.entries(labels).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
      <label>Choose document<input key={file ? 'chosen' : 'empty'} style={input} type="file" accept=".pdf,.jpg,.jpeg,.png" disabled={busy} onChange={e => setFile(e.target.files?.[0] || null)} /></label>
    </div><button type="button" style={button} disabled={disabled || !file} onClick={upload}>Upload to shipment file</button>
      {selected?.documents.map((/** @type {any} */ d) => <div key={d.document_id} style={{ paddingTop: 10 }}>{labels[d.kind]}: {d.filename} ({numeric(d.length / 1024)} KiB) <button type="button" style={button} disabled={busy} onClick={() => download(`/shipments/${shipmentId}/documents/${d.document_id}`, d.filename)}>Download {d.filename}</button></div>)}
      {selected && <p>Missing required paperwork: {selected.missing_documents.map((/** @type {any} */ k) => labels[k]).join(', ') || 'None'}</p>}
      {selected && <div><h4>Printable load packet</h4><p>Select the rate confirmation and the signed BOL or delivery copy you uploaded. Download one black-and-white PDF, rate confirmation first. Original uploads stay available above; this print copy does not verify digital signatures.</p><div style={grid}>
        <label>Packet rate confirmation<select style={input} value={packetRate} disabled={busy} onChange={e => setPacketRate(e.target.value)}><option value="">Choose rate confirmation</option>{selected.documents.filter((/** @type {any} */ d) => d.kind === 'rate_confirmation').map((/** @type {any} */ d) => <option key={d.document_id} value={d.document_id}>{d.filename}</option>)}</select></label>
        <label>Packet signed BOL / delivery copy<select style={input} value={packetDelivery} disabled={busy} onChange={e => setPacketDelivery(e.target.value)}><option value="">Choose uploaded signed copy</option>{selected.documents.filter((/** @type {any} */ d) => ['bol','pod'].includes(d.kind)).map((/** @type {any} */ d) => <option key={d.document_id} value={d.document_id}>{d.filename}</option>)}</select></label>
      </div><button type="button" style={button} disabled={disabled || !packetRate || !packetDelivery} onClick={() => download(`/shipments/${shipmentId}/packet.pdf?rate_confirmation_id=${encodeURIComponent(packetRate)}&signed_delivery_id=${encodeURIComponent(packetDelivery)}`, `shipment-${shipmentId}-print.pdf`)}>Download black-and-white load packet</button></div>}
    </div>}
  </section>;
}
