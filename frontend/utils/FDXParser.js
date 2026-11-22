import {parseFDXDocument,updateFDXBlockText} from './fdxDocumentFormat.js';
export {parseFDXDocument,updateFDXBlockText};
/** Backward-compatible body AST view; rich callers retain the full document. @param {string} xml */
export function parseFDX(xml){
  const document=parseFDXDocument(xml);
  return document.blocks.length?document.blocks:[{id:crypto.randomUUID(),type:'Action',text:''}];
}
/** Derived compatibility view, not the rich preservation master. @param {string} xml */
export function fdxTitlePageFountain(xml){
  const lines=parseFDXDocument(xml).title_page;
  if(!lines.length)return '';
  const metadata=[`Title: ${lines[0].text.replace(/\n/g,'\n    ')}`];
  const authors=lines.slice(1).filter(line=>line.type==='Author').map(line=>line.text);
  const notes=lines.slice(1).filter(line=>line.type!=='Author').map(line=>line.text);
  if(authors.length)metadata.push(`Author: ${authors.join('\n').replace(/\n/g,'\n    ')}`);
  if(notes.length)metadata.push(`Notes: ${notes.join('\n').replace(/\n/g,'\n    ')}`);
  return metadata.join('\n')+'\n\n';
}
