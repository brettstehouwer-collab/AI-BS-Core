import React,{useEffect,useState} from 'react';
export default function OfflineShell(){
  const [status,setStatus]=useState('Offline page not installed'),[waiting,setWaiting]=useState(null);
  useEffect(()=>{
    let current=true;
    if(!('serviceWorker'in navigator))return;
    navigator.serviceWorker.register('/personal/sw.js',{scope:'/personal/'}).then(registration=>{
      const show=()=>{if(!current)return;setWaiting(registration.waiting);setStatus(registration.active?'Offline public page installed':'Installing offline public page…');};
      show();registration.addEventListener('updatefound',()=>{registration.installing?.addEventListener('statechange',show);});
      navigator.serviceWorker.ready.then(show);
    }).catch(()=>{if(current)setStatus('Offline page installation unavailable; local drafts remain separate');});
    return()=>{current=false;};
  },[]);
  return <aside><p role="status">{status}</p>{waiting&&<p>A page update is ready. Finish saving drafts, then close personal-finance tabs and reopen to use it. Saved originals remain on this device.</p>}</aside>;
}
