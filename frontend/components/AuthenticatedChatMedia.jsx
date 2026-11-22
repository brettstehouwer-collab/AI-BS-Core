import { useEffect, useRef, useState } from 'react';
import { loadChatMedia } from '../utils/chatMedia.js';

/** @param {{src?:string,backendUrl:string,alt?:string,linkOnly?:boolean,lazy?:boolean,previewOnly?:boolean,children?:import('react').ReactNode}} props */
export default function AuthenticatedChatMedia({ src, backendUrl, alt = 'Generated media', linkOnly = false, lazy = false, previewOnly = false, children }) {
  const container = useRef(/** @type {HTMLSpanElement|null} */(null));
  const [visible, setVisible] = useState(!lazy);
  const [media, setMedia] = useState(/** @type {null|{kind:string,objectUrl:string,filename:string}} */(null));
  const [error, setError] = useState('');
  useEffect(() => {
    if (visible || !lazy) return;
    if (typeof IntersectionObserver === 'undefined') { setVisible(true); return; }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { setVisible(true); observer.disconnect(); }
    }, { rootMargin:'160px' });
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, [visible, lazy]);
  useEffect(() => {
    if (!visible) return;
    const controller = new AbortController();
    /** @type {string|undefined} */
    let objectUrl;
    let current = true;
    setMedia(null); setError('');
    loadChatMedia(src || '', backendUrl, { signal: controller.signal }).then(result => {
      if (!current) return;
      objectUrl = URL.createObjectURL(result.blob);
      const filename = new URL(result.url).searchParams.get('filename') || new URL(result.url).pathname.split('/').pop() || 'media';
      setMedia({ ...result, objectUrl, filename });
    }).catch(err => { if (current && err.name !== 'AbortError') setError(err.message); });
    return () => { current = false; controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [visible, src, backendUrl]);
  if (error) return <span ref={container} role="alert">{error}</span>;
  if (!media) return <span ref={container} role="status" style={{display:lazy?'block':undefined,minHeight:lazy?100:undefined}}>Loading media…</span>;
  const download = <a href={media.objectUrl} download={media.filename} style={{ color:'#60a5fa' }}>{children || 'Download media'}</a>;
  if (linkOnly) return download;
  /** @type {import('react').CSSProperties} */
  const style = { width:'100%', maxHeight:previewOnly?120:420, objectFit:'contain', borderRadius:12, display:'block' };
  return <span ref={container} style={{ display:'block', margin:previewOnly?0:'12px 0' }}>
    {media.kind === 'image' && <img src={media.objectUrl} alt={alt} style={style} />}
    {media.kind === 'video' && <video src={media.objectUrl} controls={!previewOnly} playsInline preload="metadata" style={style} />}
    {media.kind === 'audio' && <audio src={media.objectUrl} controls preload="metadata" style={{ width:'100%' }} />}
    {!previewOnly && download}
  </span>;
}
