import React,{useState} from 'react';
import {createRoot} from 'react-dom/client';
import {MobileFormattedContent} from '../../src/components/MobileStehouwerChat.jsx';
const original=window.fetch.bind(window);let count=0;
window.fetch=async(resource,config)=>{
 const url=new URL(resource,location.href);
 if(url.pathname==='/api/comfy/media'&&url.searchParams.get('filename')==='fixture-image.png'){
  count++;document.getElementById('fetch-count').textContent=String(count);
  return original('/__tests__/fixtures/media-assets/fixture-image.png',config);
 }
 if(url.origin!==location.origin)throw new Error('Fixture refuses production requests');
 return original(resource,config);
};
function Fixture(){const[tick,setTick]=useState(0);return <main style={{padding:12}}><h1>Chat image stability fixture</h1><button onClick={()=>setTick(v=>v+1)}>Refresh parent</button><p>Parent updates: {tick}</p><p>Media fetches: <output id="fetch-count">0</output></p><MobileFormattedContent role="assistant" content={'A completed test image.\n\n![Synthetic blue cup](/api/comfy/media?filename=fixture-image.png)\n\n[Download image](/api/comfy/media?filename=fixture-image.png)'} onImageClick={()=>{}}/></main>;}
createRoot(document.getElementById('root')).render(<Fixture/>);
