import React,{useEffect,useRef,useState} from 'react';
const blank=()=>({document_date:'',filing_year:'',source:'',document_type:'other_financial',notes:''});

export default function FinancialFilings({client,connection,blocked,offer}) {
  const [draft,setDraft]=useState(blank),[pending,setPending]=useState(false),[rows,setRows]=useState([]),[selected,setSelected]=useState('');
  const [files,setFiles]=useState([]),[originals,setOriginals]=useState([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[status,setStatus]=useState('Opening filings…');
  const [ready,setReady]=useState(false);
  const queue=useRef(Promise.resolve()),alive=useRef(true);
  const refresh=async()=>{const records=client.mode==='offline'?{filings:[]}:await client.request('/filings'),uploads=await client.uploads();if(alive.current){setRows(records.filings);setFiles(uploads.filter(row=>row.target==='filing'));}};
  useEffect(()=>{if(connection==='online')refresh().catch(e=>{if(alive.current)setError(e.message);});},[connection]);
  useEffect(()=>{alive.current=true;let current=true;(async()=>{const saved=await client.filingDraft();if(!current)return;setDraft(saved.fields||blank());setPending(Boolean(saved.pending));await refresh();if(current){setStatus(saved.pending?'Filing retry saved':'Filing draft ready');setReady(true);}})().catch(e=>{if(current)setError(e.message);});return()=>{current=false;alive.current=false;};},[client]);
  useEffect(()=>{let current=true;setOriginals([]);if(selected)client.request(`/filings/${selected}/originals`).then(data=>{if(current)setOriginals(data.documents);}).catch(e=>{if(current)setError(e.message);});return()=>{current=false;};},[client,selected]);
  const edit=(key,value)=>{const next={...draft,[key]:value};setDraft(next);setStatus('Saving filing on this device…');queue.current=queue.current.catch(()=>{}).then(()=>client.saveFilingDraft(next)).then(()=>{if(alive.current)setStatus('Filing draft saved on this device');}).catch(e=>{if(alive.current){setError(e.message);setStatus('Filing draft not saved');}throw e;});queue.current.catch(()=>{});};
  const run=async action=>{setBusy(true);setError('');try{await queue.current;await action();}catch(e){if(alive.current){setError(e.message);const saved=await client.filingDraft().catch(()=>null);if(saved)setPending(Boolean(saved.pending));}}finally{if(alive.current)setBusy(false);}};
  return <section><h2>Financial document filing</h2><p>No payment record is required. Choose the source, document type and filing year yourself; these labels do not verify tax treatment.</p><p role="status">{status}</p>{error&&<p role="alert">{error}</p>}
    <fieldset disabled={!ready||blocked||busy||pending}>
      <label>Document date<input type="date" value={draft.document_date} onChange={e=>edit('document_date',e.target.value)}/></label>
      <label>Filing year (you choose)<input type="number" min="1" max="9999" value={draft.filing_year} onChange={e=>edit('filing_year',e.target.value)}/></label>
      <label>Document source<input value={draft.source} onChange={e=>edit('source',e.target.value)}/></label>
      <label>Document type<select aria-label="Document type" value={draft.document_type} onChange={e=>edit('document_type',e.target.value)}>{['pay_statement','receipt','ledger','tax_document','other_financial'].map(kind=><option key={kind} value={kind}>{kind.replaceAll('_',' ')}</option>)}</select></label>
      <label>Filing notes<textarea aria-label="Filing notes" value={draft.notes} onChange={e=>edit('notes',e.target.value)}/></label>
    </fieldset>
    <button disabled={!ready||blocked||busy||connection!=='online'} onClick={()=>run(async()=>{const result=await client.submitFiling();setDraft(blank());setPending(false);setSelected(String(result.id));await refresh();if(alive.current)setStatus('Filing recorded');})}>{pending?'Retry saved filing':'Record saved filing'}</button>
    <label>Filing for originals<select aria-label="Filing for originals" value={selected} disabled={busy||blocked} onChange={e=>setSelected(e.target.value)}><option value="">Choose a filing</option>{rows.map(row=><option key={row.id} value={row.id}>{row.filing_year} · {row.source} · {row.document_type}</option>)}</select></label>
    <label>Save filing original on this device<input type="file" disabled={!selected||busy||blocked} onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file)run(async()=>{await client.retainFilingFile(Number(selected),file);await refresh();if(alive.current)setStatus('Filing original saved on this device');});}}/></label>
    {files.map(row=><article key={row.id}><span>{row.name} · filing {row.filingId} · saved locally</span><button disabled={busy||blocked} onClick={()=>run(async()=>{await client.sendFile(row.id);await refresh();if(alive.current){if(String(row.filingId)===selected)setOriginals((await client.request(`/filings/${selected}/originals`)).documents);setStatus('Filing original uploaded');}})}>Upload filing {row.name}</button></article>)}
    {originals.map(row=><article key={row.document_id}><span>{row.filename} · {row.size} bytes</span><button disabled={busy||blocked} onClick={()=>run(async()=>offer(await client.downloadFiling(Number(selected),row),row.filename))}>Download filing {row.filename}</button></article>)}
    {rows.map(row=><article key={row.id}><strong>{row.filing_year} · {row.source}</strong><p>{row.document_date} · {row.document_type.replaceAll('_',' ')}</p><p>{row.notes}</p></article>)}
  </section>;
}
