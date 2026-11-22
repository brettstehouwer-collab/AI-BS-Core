import React from 'react';
import{createRoot}from'react-dom/client';
import ComfyWorkspaceTab from '../../src/components/ComfyWorkspaceTab.jsx';
const original=window.fetch.bind(window);let galleryReads=0;let runs=0;const mode=new URLSearchParams(location.search).get("mode");
window.fetch=async(resource,config)=>{
 const url=new URL(resource,location.href);
 if(mode==='denied'&&url.pathname.startsWith('/api/'))return new Response('Forbidden',{status:403});
 if(url.pathname==='/api/comfyui/workspace/capabilities')return Response.json({online:true,templates:[{id:'wan_video',name:'Wan native video',media_type:'video',ready:true,description:'Fixture: actual core-generated clip.'}],checkpoints:[],upscale_models:[],features:{},devices:[]});
 if(url.pathname==='/api/comfyui/workspace/styles')return Response.json([]);
 if(url.pathname==='/api/comfyui/workspace/gallery')return Response.json(++galleryReads>1?[{filename:'AI_BS_Wan_Core_00001_.mp4',subfolder:'',type:'video',width:512,height:384,size_bytes:33851}]:[]);
 if(url.pathname==='/api/comfyui/workspace/run'){const body=JSON.parse(config.body);document.getElementById('fixture-request').textContent=JSON.stringify(body);document.getElementById('fixture-runs').textContent=String(++runs);return Response.json({status:'queued',prompt_id:'fixture-core-video'});}
 if(url.pathname==='/api/comfyui/status/fixture-core-video')return Response.json(mode==='failed'?{status:'failed'}:{status:'completed',outputs:[{filename:'AI_BS_Wan_Core_00001_.mp4',subfolder:'',type:'output'}]});
 if(url.pathname==='/api/comfy/media'&&url.searchParams.get('filename')==='AI_BS_Wan_Core_00001_.mp4')return original('/__tests__/fixtures/media-assets/fixture-generated-core.mp4');
 if(url.origin!==location.origin)throw Error('Fixture refuses production requests');
 return original(resource,config);
};
createRoot(document.getElementById('root')).render(<><output id="fixture-request" style={{display:'none'}}/><output id="fixture-runs" style={{display:'none'}}>0</output><ComfyWorkspaceTab backendUrl="http://127.0.0.1:8000"/></>);
