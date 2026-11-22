// Exercise real browser blob rendering with synthetic bytes, never real auth.
import React from 'react';
import {createRoot} from 'react-dom/client';
import AuthenticatedChatMedia from '../../src/components/AuthenticatedChatMedia.jsx';
const originalFetch=window.fetch.bind(window);
window.fetch=async(url,options)=>{
  const target=new URL(url,location.href);
  if(target.origin==='https://api.brettstehouwer.live'&&target.pathname==='/api/comfy/media'){
    const filename=target.searchParams.get('filename');
    if(filename==='fixture-denied.png')return new Response('Unauthorized',{status:401});
    if(['fixture-image.png','fixture-audio.wav','fixture-video.mp4'].includes(filename))return originalFetch('/__tests__/fixtures/media-assets/'+filename,options);
    throw new Error('Fixture refuses production media requests');
  }
  return originalFetch(url,options);
};
createRoot(document.getElementById('root')).render(<main style={{padding:12,fontFamily:'sans-serif'}}>
 <h1>Protected media UI fixture</h1>
 <section aria-label="Image fixture"><AuthenticatedChatMedia src="/api/comfy/media?filename=fixture-image.png" backendUrl="https://api.brettstehouwer.live" alt="Synthetic blue cup"/></section>
 <section aria-label="Audio fixture"><AuthenticatedChatMedia src="/api/comfy/media?filename=fixture-audio.wav" backendUrl="https://api.brettstehouwer.live"/></section>
 <section aria-label="Video fixture"><AuthenticatedChatMedia src="/api/comfy/media?filename=fixture-video.mp4" backendUrl="https://api.brettstehouwer.live"/></section>
 <section aria-label="Denied fixture"><AuthenticatedChatMedia src="/api/comfy/media?filename=fixture-denied.png" backendUrl="https://api.brettstehouwer.live"/></section>
</main>);
