import React,{useEffect,useState} from 'react';

export default function MultipartExport({client,connection,year,blocked,offer}){
  const [plan,setPlan]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[offered,setOffered]=useState([]),[stale,setStale]=useState(false);
  useEffect(()=>{setPlan(null);setOffered([]);setStale(false);setError('');},[year]);
  const run=async action=>{setBusy(true);setError('');try{await action();}catch(e){if(e.status===409){setStale(true);setError('Source changed. Prepare a new plan and keep parts from only one fingerprint.');}else setError(e.message);}finally{setBusy(false);}};
  const disabled=blocked||busy||connection!=='online'||!/^[1-9]\d{0,3}$/.test(year);
  return <section><h2>Large yearly archive</h2><p>Prepare a plan, save it, then download each part explicitly. All parts must have the same fingerprint. If source records change, prepare a new plan; existing downloaded files stay yours.</p>
    {error&&<p role="alert">{error}</p>}
    <button disabled={disabled} onClick={()=>run(async()=>{const result=await client.request(`/exports/${year}/parts`);if(result?.plan?.version!==3||!Array.isArray(result.plan.parts)||!/^[a-f0-9]{64}$/.test(result.plan.fingerprint))throw Error('Year archive plan is invalid');setPlan(result.plan);setOffered([]);setStale(false);})}>Prepare multipart yearly export</button>
    {plan&&<><p>Year {plan.year} · {plan.files.length} files · {plan.source_bytes} source bytes · {plan.parts.length} parts</p><p>Fingerprint: <code>{plan.fingerprint}</code></p>
      <button disabled={blocked||busy} onClick={()=>offer(new Blob([JSON.stringify(plan,null,2)],{type:'application/json'}),`personal-${plan.year}-${plan.fingerprint.slice(0,12)}-plan.json`)}>Download archive plan</button>
      {plan.parts.map(part=><article key={part.index}><p>Part {part.index+1}: {part.bytes} source bytes</p><button disabled={disabled||stale} onClick={()=>run(async()=>{const blob=await client.request(`/exports/${plan.year}/parts/${plan.fingerprint}/${part.index}.zip`,{},true);offer(blob,`personal-${plan.year}-${plan.fingerprint.slice(0,12)}-part-${String(part.index+1).padStart(4,'0')}.zip`);setOffered(previous=>[...new Set([...previous,part.index])]);})}>Download part {part.index+1} of {plan.parts.length}</button></article>)}
      <p role="status">Downloads offered: {offered.length} of {plan.parts.length}. Confirm the files are saved on your device.</p>
    </>}
  </section>;
}
