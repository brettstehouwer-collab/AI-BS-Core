// Isolated synthetic document + in-memory API. Never contacts the real writer.
import React from 'react';
import {createRoot} from 'react-dom/client';
import ScreenwritingTab from '../../src/components/ScreenwritingTab.jsx';
import '../../style.css';
import '../../responsive-fixes.css';
let text='Title: Mobile Layout Fixture\nAuthor: Codex Test\n\nINT. TEST ROOM - DAY\n\nA blue cup rests on the table.\n\nTESTER\nThis synthetic draft stays in the fixture.\n';
let revision='fixture-1';
let saves=0;
const request=window.fetch.bind(window);
window.fetch=async(resource,config={})=>{
  const url=new URL(typeof resource==='string'?resource:resource.url,location.href);
  if(url.hostname!=='writer-fixture.invalid') return request(resource,config);
  let body={};try{body=JSON.parse(config.body||'{}');}catch{}
  let result={};
  if(url.pathname.endsWith('/projects'))result={projects:['Mobile Layout Fixture'],current_project:'Mobile Layout Fixture'};
  else if(url.pathname.endsWith('/read'))result={status:'success',project:'Mobile Layout Fixture',content:text,revision,metadata:{current_branch:'main'}};
  else if(url.pathname.endsWith('/write')){text=body.content;saves++;revision=`fixture-${saves+1}`;result={status:'success',project:'Mobile Layout Fixture',content:text,revision};}
  else if(url.pathname.endsWith('/branches'))result={branches:['main'],current:'main'};
  else if(url.pathname.endsWith('/parse'))result={beats:[{id:'fixture-scene',heading:'INT. TEST ROOM - DAY',page:1}],characters:['TESTER']};
  else if(url.pathname.endsWith('/sprints'))result={sprints:[],active_sprint:null};
  else if(url.pathname.endsWith('/characters'))result={characters:[]};
  return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json'}});
};
function Fixture(){return <><div className="app-shell" style={{height:'100dvh',display:'flex',flexDirection:'column'}}>
  <header className="mobile-top-navbar" style={{height:52}}>Fixture app header</header>
  <main className="main-panel" style={{flex:1,minHeight:0}}><div className="content-area" style={{height:'100%'}}><div className="tab-subinterface unified_creation-subinterface" style={{height:'100%'}}><div className="subinterface-content" style={{height:'100%'}}>
    <div style={{display:'flex',height:'100%'}}><aside style={{width:60,flexShrink:0}}>Fixture rail</aside><div style={{position:'relative',height:'100%',width:'calc(100% - 60px)',overflow:'hidden'}}><ScreenwritingTab backendUrl="https://writer-fixture.invalid"/></div></div>
  </div></div></div></main>
  <nav className="mobile-bottom-nav-container" style={{position:'fixed',bottom:0,height:60,zIndex:1000}}>Fixture app navigation</nav>
  </div><output id="fixture-state" style={{position:'fixed',bottom:0,left:0,zIndex:99999,fontSize:10,pointerEvents:'none',background:'#fff'}}/></>;}
createRoot(document.getElementById('root')).render(<Fixture/>);
// Explicit fixture-only snapshot control; never calls production APIs.
const inspect=document.createElement('button');inspect.textContent='Inspect fixture';inspect.style.cssText='position:fixed;right:0;bottom:0;z-index:99999;font-size:10px';inspect.onclick=()=>{document.getElementById('fixture-state').textContent=JSON.stringify({text,revision,saves});};document.body.append(inspect);
