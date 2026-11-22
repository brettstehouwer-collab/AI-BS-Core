import { useRef, useState } from 'react';
import { updateFDXBlockText } from '../../utils/fdxDocumentFormat.js';
import { confirmedRichEdit, richBlockHistory, recordRichBlockHistory, restoreRichBlockHistory } from '../utils/richFdxDraft.js';
const TYPES=['Scene Heading','Action','Character','Dialogue','Parenthetical','Transition','General','Shot'];
/** Imported styles are an allowlist; XML/CSS/notes remain inert text. @param {any} run */
export function richRunStyle(run){
  const values=new Set(String(run.attributes?.Style||'').split(/[+, ]+/));
  return {fontWeight:values.has('Bold')?'bold':'normal',fontStyle:values.has('Italic')?'italic':'normal',textDecoration:[values.has('Underline')?'underline':'',values.has('Strikeout')?'line-through':''].filter(Boolean).join(' ')||'none'};
}
/** @param {{blocks:any[],baselineBlocks:any[],revision:string,onChange:(blocks:any[])=>void,onUnqualified:(blocks:any[],message:string)=>void,onQualified?:()=>void}} props */
export default function RichFDXEditor({blocks,baselineBlocks,revision,onChange,onUnqualified,onQualified}){
  const selections=useRef(/** @type {Record<string,{from:number,to:number,inputType:string}>} */({}));
  const histories=useRef(/** @type {any} */({entries:{}}));
  const pendingDrafts=useRef(/** @type {Record<string,string>} */({}));
  const [pending,setPending]=useState(/** @type {Record<string,string>} */({}));
  /** @param {any} event @param {any} block @param {string} [inputType] */
  const capture=(event,block,inputType='')=>{selections.current[block.id]={from:event.currentTarget.selectionStart,to:event.currentTarget.selectionEnd,inputType:inputType||event.nativeEvent?.inputType||selections.current[block.id]?.inputType||''};};
  /** @param {any} event @param {any} block */
  const edit=(event,block)=>{
    const text=event.currentTarget.value;pendingDrafts.current[block.id]=text;setPending(previous=>({...previous,[block.id]:text}));
    try{
      const selected=selections.current[block.id],inputType=event.nativeEvent?.inputType||selected?.inputType||'';
      const history=richBlockHistory(histories.current,baselineBlocks.find(value=>value.id===block.id)||block,block,revision);
      let changed;
      if(['historyUndo','historyRedo'].includes(inputType))changed=restoreRichBlockHistory(history,text,inputType);
      else{
        if(!selected)throw new Error('No verified selection was captured for this edit.');
        const range=confirmedRichEdit(block.text,text,selected.from,selected.to,inputType);
        changed=updateFDXBlockText(block,text,range);recordRichBlockHistory(history,changed);
      }
      const nextBlocks=blocks.map(value=>value.id===block.id?changed:value);onChange(nextBlocks);
      delete pendingDrafts.current[block.id];
      setPending(previous=>{const next={...previous};delete next[block.id];return next;});
      if(!Object.keys(pendingDrafts.current).length)onQualified?.();
      else onUnqualified(nextBlocks.map(value=>Object.hasOwn(pendingDrafts.current,value.id)?{...value,text:pendingDrafts.current[value.id]}:value),'Other unqualified paragraph edits remain visible and retained. Return to known states or create a separate working copy before saving.');
    }catch(error){onUnqualified(blocks.map(value=>Object.hasOwn(pendingDrafts.current,value.id)?{...value,text:pendingDrafts.current[value.id]}:value),`${error instanceof Error?error.message:String(error)} Original FDX and this unsaved text were retained; create a separate working copy for this change.`);}
  };
  return <section aria-label="Preserved FDX paragraph editor" style={{maxWidth:900,margin:'12px auto',padding:18,color:'#e2e8f0',background:'#111827'}}>
    <p>Rich FDX mode preserves the imported XML, styles, title, author, notes and dual-dialogue groups. Edit existing paragraph text or type below. Paragraph creation, reorder, note/style/title editing and other structural changes require a separate working copy. This view does not measure Final Draft pagination.</p>
    {blocks.map(block=><article key={block.id} data-fdx-block={block.id} style={{borderTop:'1px solid #334155',padding:'12px 0'}}>
      {block.startsNewPage&&<div style={{color:'#94a3b8'}}>Retained manual page break</div>}
      <label>Paragraph type <select aria-label={`Type for ${block.id}`} value={block.type} disabled={block.editable===false} onChange={event=>onChange(blocks.map(value=>value.id===block.id?{...value,type:event.target.value}:value))}>
        {!TYPES.includes(block.type)&&<option value={block.type}>{block.type} (retained)</option>}{TYPES.map(type=><option key={type}>{type}</option>)}
      </select></label>{block.dualGroup&&<span style={{marginLeft:12}}>Retained dual dialogue · {block.dualSide}</span>}
      <div aria-label={`Styled preview ${block.id}`} style={{fontFamily:'Courier New,monospace',whiteSpace:'pre-wrap',margin:'8px 0'}}>{block.runs.map((/** @type {any} */ run,/** @type {number} */ index)=><span key={index} style={richRunStyle(run)}>{run.text}</span>)}</div>
      <textarea aria-label={`Edit ${block.type} ${block.id}`} disabled={block.editable===false} value={pending[block.id]??block.text} rows={Math.min(12,Math.max(2,Math.ceil(block.text.length/85)))}
        onSelect={event=>capture(event,block)} onKeyDown={event=>capture(event,block,(event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'?(event.shiftKey?'historyRedo':'historyUndo'):(event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='y'?'historyRedo':event.key==='Backspace'?'deleteContentBackward':event.key==='Delete'?'deleteContentForward':'')}
        onBeforeInput={event=>capture(event,block)} onPaste={event=>capture(event,block,'insertFromPaste')} onChange={event=>edit(event,block)}
        style={{width:'100%',boxSizing:'border-box',fontFamily:'Courier New,monospace',fontSize:'12pt',whiteSpace:'pre-wrap',background:'#0f172a',color:'#f8fafc',padding:8}}/>
      {block.notes?.map((/** @type {any} */ note)=><aside key={note.id} aria-label="Retained script note" style={{color:'#c4b5fd',whiteSpace:'pre-wrap'}}>Script note (read only): {note.text}</aside>)}
      {block.editable===false&&<p>This paragraph has unsupported nested content. Original XML is retained; edit a separate working copy.</p>}
    </article>)}
  </section>;
}
