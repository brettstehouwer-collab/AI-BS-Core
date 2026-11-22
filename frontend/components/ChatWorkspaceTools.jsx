import { useEffect, useRef, useState } from 'react';

/** A composer tool; opening it never starts a shell or writes a file. */
/** @param {{panel: 'terminal' | 'codebase' | null, onClose: () => void, onInsertText: (text: string) => void, backendUrl: string, hasDraft?: boolean}} props */
export default function ChatWorkspaceTools({panel, onClose, onInsertText, backendUrl, hasDraft=false}) {
  const [shell, setShell] = useState('/ps');
  const [command, setCommand] = useState('');
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState(/** @type {{path: string, line: number, symbol: string}[]} */ ([]));
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const box = useRef(/** @type {HTMLElement | null} */ (null));
  const request = useRef(/** @type {AbortController | null} */ (null));
  useEffect(() => {
    if (!panel) return;
    const previous = document.activeElement;
    const initialFocus=box.current?.querySelector('input, textarea, select, button');
    if(initialFocus instanceof HTMLElement)initialFocus.focus();
    /** @param {KeyboardEvent} event */
const keys = event => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      if (event.key !== 'Tab') return;
      const items = [...(box.current?.querySelectorAll('button, input, textarea, select, a[href]') || [])].filter(el => el instanceof HTMLElement && !('disabled' in el && el.disabled));
      const first=items[0], last=items[items.length-1];
      if (event.shiftKey && document.activeElement===first) {event.preventDefault();if(last instanceof HTMLElement)last.focus();}
      else if (!event.shiftKey && document.activeElement===last) {event.preventDefault();if(first instanceof HTMLElement)first.focus();}
    };
    document.addEventListener('keydown', keys);
    return () => { document.removeEventListener('keydown', keys); request.current?.abort(); if(previous instanceof HTMLElement)previous.focus(); };
  }, [panel, onClose]);
  useEffect(() => {setMatches([]);setStatus('');setBusy(false);request.current?.abort();}, [backendUrl]);
  if (!panel) return null;
  /** @param {string} text */
const insert = text => {onInsertText(text);onClose();};
  /** @param {import("react").FormEvent} event */
const search = async event => {
    event.preventDefault(); if (!query.trim() || busy) return;
    const controller = new AbortController();request.current=controller;
    setBusy(true);setStatus('Searching code symbolsâ€¦');setMatches([]);
    try {
      const response = await fetch(`${backendUrl}/api/executive/run`, {method:'POST', signal:controller.signal,
        headers:{'Content-Type':'application/json','X-Client-ID':'stehouwer_publishing'},
        body:JSON.stringify({command_type:'tool',target:'lookup_symbol',payload:{query:query.trim(),scope:'all',limit:20}})});
      if (!response.ok) throw new Error(response.status===401||response.status===403?'Sign in to search the connected codebase.':`Codebase search unavailable (HTTP ${response.status}).`);
      const data=await response.json(), result=data.result||data;
      if (result.status==='error' || data.status==='error') throw new Error('Codebase search was not completed.');
      if (!Array.isArray(result.matches)) throw new Error('Codebase search returned an invalid response.');
      if (controller.signal.aborted) return;
      setMatches(result.matches.slice(0,20));setStatus(result.matches.length?'Choose a result to add its reference or open the editor.':'No matching symbols. Try a filename, component, or API route.');
    } catch (error) {if (!controller.signal.aborted) setStatus(errorMessage(error)||'Codebase search unavailable.');}
    finally {if (request.current===controller) setBusy(false);}
  };
  return <div className="chat-workspace-backdrop" onClick={onClose}>
    <section ref={box} role="dialog" aria-modal="true" aria-label={panel==='terminal'?'Windows command prompt':'Codebase search'} className="chat-workspace-drawer" onClick={e=>e.stopPropagation()}>
      <header><h2>{panel==='terminal'?'Terminal':'Codebase'}</h2><button type="button" onClick={onClose} aria-label="Close workspace tool">Close</button></header>
      {panel==='terminal'?<form onSubmit={e=>{e.preventDefault();if(command.trim()&&!hasDraft)insert(`${shell} ${command.trim()}`);}}>
        <label>Shell<select value={shell} onChange={e=>setShell(e.target.value)}><option value="/ps">Windows PowerShell</option><option value="/cmd">Windows Command Prompt</option><option value="/wsl">WSL Bash</option></select></label>
        <label>Command<textarea value={command} onChange={e=>setCommand(e.target.value)} placeholder="Enter a command to prepare in chat" rows={5}/></label>
        <p>Commands target the connected Windows PC. Add the command to chat, review it, then send it through the existing execution controls.</p>
        <p role="status">{hasDraft ? "Your existing chat draft is kept. Send or save it before adding a command." : ""}</p>
        <button type="submit" disabled={!command.trim()||hasDraft}>Add command to chat</button>
      </form>:<>
        <form onSubmit={search}><label>Find code<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Component, filename, or API route"/></label><button type="submit" disabled={busy||!query.trim()}>{busy?'Searchingâ€¦':'Search codebase'}</button></form>
        <p role="status">{status||'Search indexed component names and backend routes. File contents are added only when you choose them.'}</p>
        <ul>{matches.map((item,index)=><li key={`${item.path}:${item.line}:${index}`}><strong>{item.symbol}</strong><small>{item.path}:{item.line}</small><div>
          <button type="button" onClick={()=>insert(`Codebase reference: ${item.path}:${item.line} (${item.symbol})`)}>Add reference</button>
          <button type="button" onClick={()=>{window.dispatchEvent(new CustomEvent('aibs-open-ide-editor',{detail:{path:item.path}}));onClose();}}>Open in editor</button>
        </div></li>)}</ul>
      </>}
    </section>
  </div>;
}

/** @param {unknown} error @returns {string} */
function errorMessage(error) {
  if (error instanceof Error) return error.message;
  return typeof error === 'object' && error !== null && 'message' in error ? String(error.message) : String(error);
}
