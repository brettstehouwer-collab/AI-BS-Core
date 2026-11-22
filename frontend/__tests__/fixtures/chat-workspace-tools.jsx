import React,{useState,useCallback} from 'react';
import{createRoot}from'react-dom/client';
import ChatContextToolbar from '../../src/components/ChatContextToolbar.jsx';
import ArtifactsAndToolsModal from '../../src/components/ArtifactsAndToolsModal.jsx';
import ChatWorkspaceTools from '../../src/components/ChatWorkspaceTools.jsx';
const original=window.fetch.bind(window);let requests=0;
window.fetch=async(resource,config)=>{
 const url=new URL(resource,location.href);
 if(url.pathname==='/api/artifacts/live') return Response.json({tasks:[{name:'Synthetic task.md',path:'fixture/task.md',size_bytes:42,preview:'Retained synthetic task artifact.'}],plans:[],manuals:[],media:[],programs:[],timestamp:'Fixture only'});
 if(url.pathname==='/api/memory/personal')return Response.json({memories:[]});
 if(url.pathname.startsWith('/api/memory/personal/activity'))return Response.json({events:[]});
 if(url.pathname==='/api/executive/run'){
  const body=JSON.parse(config.body);if(body.target!=='lookup_symbol')throw Error('Fixture refuses execution');
  document.getElementById('search-requests').textContent=String(++requests);
  return new Response(JSON.stringify({status:'success',result:{status:'success',matches:[{symbol:'ChatTab.jsx',path:'C:\\AI-BS\\frontend\\src\\components\\ChatTab.jsx',line:1}]}}),{headers:{'Content-Type':'application/json'}});
 }
 if(url.origin!==location.origin)throw new Error('Fixture refuses production requests');
 return original(resource,config);
};
function Fixture(){const[web,setWeb]=useState(false);const[panel,setPanel]=useState(null);const[draft,setDraft]=useState('');const[action,setAction]=useState('None');const[artifacts,setArtifacts]=useState(false);const close=useCallback(()=>setPanel(null),[]);return <main style={{padding:12}}><h1>Chat workspace controls</h1><ChatContextToolbar activeContexts={{web}} onToggleContext={()=>setWeb(v=>!v)} onOpenArtifacts={()=>{setAction('Artifacts drawer');setArtifacts(true);}} onOpenTerminal={()=>setPanel('terminal')} onOpenCodebase={()=>setPanel('codebase')}/><ArtifactsAndToolsModal isOpen={artifacts} onClose={()=>setArtifacts(false)} backendUrl={location.origin} onInsertText={text=>setDraft(v=>v+text)}/><output>{action}</output><p>Search requests: <output id="search-requests">0</output></p><label>Chat draft<textarea aria-label="Chat draft" value={draft} onChange={e=>setDraft(e.target.value)}/></label><ChatWorkspaceTools panel={panel} onClose={close} backendUrl={location.origin} hasDraft={!!draft.trim()} onInsertText={text=>setDraft(previous=>previous?`${previous}\n${text}`:text)}/></main>};
createRoot(document.getElementById('root')).render(<Fixture/>);
