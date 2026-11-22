// Rich FDX data stays XML/text data. No imported markup is inserted as HTML.
const SCHEMA='aibs_rich_fdx_v1';
/** @param {any} node @param {string} [name] @returns {Element[]} */
const children=(node,name)=>Array.from(node.childNodes).filter((/** @type {any} */ child)=>child.nodeType===1&&(!name||child.tagName===name));
/** @param {Element} node */
const attributes=node=>Object.fromEntries(Array.from(node.attributes).map(attr=>[attr.name,attr.value]));
/** @param {Element} node */
const directText=node=>Array.from(node.childNodes).filter(child=>child.nodeType===3||child.nodeType===4).map(child=>child.nodeValue||'').join('');
/** @param {string} xml */
function documentXML(xml){
  if (typeof xml!=='string'||new TextEncoder().encode(xml).length>16*1024*1024||/<!DOCTYPE|<!ENTITY/i.test(xml))throw new Error('Unsupported or oversized FDX XML declarations.');
  const document=new DOMParser().parseFromString(xml,'text/xml');
  if(document.getElementsByTagName('parsererror').length||document.documentElement?.tagName!=='FinalDraft'||children(document.documentElement,'Content').length!==1)throw new Error('Expected one valid Final Draft script Content section.');
  return document;
}
/** @param {Document} document */
function bodyNodes(document){
  /** @type {{node:Element,group:string|null,side:string|null}[]} */const result=[];
  /** @type {string[]} */const warnings=[];
  for(const node of children(children(document.documentElement,'Content')[0])){
    if(node.tagName==='Paragraph')result.push({node,group:null,side:null});
    else if(node.tagName==='DualDialogue'){
      const group=`dual-${result.length}`;let side='left',characters=0;
      for(const paragraph of children(node)){
        if(paragraph.tagName!=='Paragraph'){warnings.push(`Unknown dual-dialogue child retained: ${paragraph.tagName}`);continue;}
        if(paragraph.getAttribute('Type')==='Character'){characters++;if(characters>=2)side='right';}
        result.push({node:paragraph,group,side});
      }
      if(characters!==2)warnings.push('Dual dialogue does not have exactly two character cues; structure is preserved.');
    }else warnings.push(`Unknown body section retained: ${node.tagName}`);
  }
  if(result.length>50000)throw new Error('Too many FDX paragraphs.');
  return {result,warnings};
}
/** @param {string} xml */
export function parseFDXDocument(xml){
  const document=documentXML(xml);const {result,warnings}=bodyNodes(document);
  /** @param {Element} node @param {string} id @param {string|null} [group] @param {string|null} [side] */
  const block=(node,id,group=null,side=null)=>{
    const runs=children(node,'Text').map((run,index)=>({id:`${id}-r${index}`,text:directText(run),attributes:attributes(run)}));
    const notes=children(node,'ScriptNote').map((note,index)=>({id:`${id}-n${index}`,text:note.textContent||'',attributes:attributes(note)}));
    const unknown=children(node).filter(child=>!['Text','ScriptNote'].includes(child.tagName)).map(item=>item.tagName);
    unknown.push(...children(node,'Text').flatMap(run=>children(run).map(child=>'Text/'+child.tagName)));
    if(unknown.length)warnings.push('Unsupported nested paragraph content retained: '+unknown.join(','));
    return {id,type:node.getAttribute('Type')||'General',text:runs.map(run=>run.text).join(''),attributes:attributes(node),runs,notes,
      startsNewPage:node.getAttribute('StartsNewPage')==='Yes',dualGroup:group,dualSide:side,
      dual:side==='right'&&node.getAttribute('Type')==='Character',editable:!unknown.length,edit_operations:/** @type {any[]} */([])};
  };
  const blocks=result.map(({node,group,side},index)=>block(node,`fdx-${index}`,group,side));
  const title_page=children(document.documentElement,'TitlePage').flatMap(page=>children(page,'Content').flatMap(content=>children(content,'Paragraph').map((node,index)=>block(node,`title-${index}`))));
  return {schema:SCHEMA,original_xml:xml,blocks,title_page,
    preserved_sections:children(document.documentElement).filter(node=>!['Content','TitlePage'].includes(node.tagName)).map(node=>node.tagName),
    warnings:[...new Set(warnings)],editing_subset:'existing-paragraph-text-and-type',structural_editing_supported:false};
}
/** @param {string} value */
const scalars=value=>Array.from(value);
/** @param {any} block @param {string} text @param {{start:number,end:number,text:string}} [range] */
export function updateFDXBlockText(block,text,range){
  if(text===block.text)return block;
  if(block.editable===false)throw new Error('This paragraph has unsupported nested content. Preserve the draft as a working copy.');
  const before=scalars(block.text),after=scalars(text);
  if(!range){
    if(block.runs.length>1)throw new Error('Styled text changes require a confirmed edit range.');
    let start=0,suffix=0;while(start<before.length&&start<after.length&&before[start]===after[start])start++;
    while(suffix<before.length-start&&suffix<after.length-start&&before[before.length-1-suffix]===after[after.length-1-suffix])suffix++;
    range={start,end:before.length-suffix,text:after.slice(start,after.length-suffix).join('')};
  }
  const {start,end,text:replacement}=range;
  if(!Number.isInteger(start)||!Number.isInteger(end)||start<0||end<start||end>before.length||before.slice(0,start).join('')+replacement+before.slice(end).join('')!==text)throw new Error('The rich text edit range was not confirmed. Preserve your draft.');
  const runs=/** @type {any[]} */(block.runs);let anchor=runs.at(-1)||{id:`${block.id}-r0`,attributes:{}};let boundary=0;
  for(const run of runs){boundary+=scalars(run.text).length;if(start<boundary){anchor=run;break;}}
  /** @type {any[]} */const next=[];let position=0,inserted=false;
  const insert=()=>{if(replacement){const attrs={...anchor.attributes};delete attrs.RevisionID;next.push({id:anchor.id,text:replacement,attributes:attrs});}inserted=true;};
  for(const run of runs){
    const value=scalars(run.text),finish=position+value.length;
    if(position<start){const prefix=value.slice(0,Math.max(0,Math.min(start,finish)-position)).join('');if(prefix)next.push({...run,text:prefix});}
    if(!inserted&&start<=finish)insert();
    if(finish>end){const suffix=value.slice(Math.max(end-position,0)).join('');if(suffix)next.push({...run,text:suffix});}
    position=finish;
  }
  if(!inserted)insert();
  const operation={id:crypto.randomUUID().replaceAll('-',''),before_text:block.text,start,end,text:replacement};
  return {...block,text,runs:next,edit_operations:[...(block.edit_operations||[]),operation]};
}
/** @param {any} document @param {any[]} [blocks] */
export function serializeFDXDocument(document,blocks=document.blocks){
  if(document.schema!==SCHEMA||typeof document.original_xml!=='string')throw new Error('Original FDX XML is required for preservation export.');
  const parsed=parseFDXDocument(document.original_xml);
  for(const key of /** @type {const} */(['title_page','preserved_sections','warnings','editing_subset','structural_editing_supported']))if(JSON.stringify(document[key])!==JSON.stringify(parsed[key]))throw new Error('Readonly FDX metadata changes require a separate working copy.');
  if(blocks.length!==parsed.blocks.length||blocks.some((block,index)=>block.id!==parsed.blocks[index].id))throw new Error('Structural FDX edits need a separate qualified working copy.');
  const xml=documentXML(document.original_xml),nodes=bodyNodes(xml).result;let changed=false;
  blocks.forEach((block,index)=>{
    const old=parsed.blocks[index];
    for(const key of /** @type {const} */(['notes','startsNewPage','dualGroup','dualSide','dual','editable']))if(JSON.stringify(block[key])!==JSON.stringify(old[key]))throw new Error('Readonly FDX paragraph metadata was changed. Original XML was retained.');
    const attrs={...block.attributes},prior={...old.attributes};delete attrs.Type;delete prior.Type;
    if(JSON.stringify(attrs)!==JSON.stringify(prior))throw new Error('Readonly FDX paragraph attributes were changed.');
    let expected=old;
    for(const operation of block.edit_operations||[]){if(expected.text!==operation.before_text)throw new Error('Rich edit history does not match original XML.');const value=scalars(expected.text);expected=updateFDXBlockText(expected,value.slice(0,operation.start).join('')+operation.text+value.slice(operation.end).join(''),operation);}
    if(expected.text!==block.text||JSON.stringify(expected.runs)!==JSON.stringify(block.runs))throw new Error('FDX text/style edits need qualified range operations. Original XML was retained.');
    if(block.text===old.text&&block.type===old.type)return;
    if(!old.editable||!Array.isArray(block.runs)||block.runs.map((/** @type {any} */ run)=>run.text).join('')!==block.text)throw new Error('Qualified rich text runs are required; original XML was retained.');
    changed=true;const paragraph=nodes[index].node;paragraph.setAttribute('Type',block.type);
    const original=children(paragraph,'Text');
    original.forEach((node,runIndex)=>{
      const id=`${block.id}-r${runIndex}`;
      for(const run of block.runs.filter((/** @type {any} */ item)=>item.id===id)){
        const replacement=xml.createElement('Text');for(const [key,value] of Object.entries(run.attributes))replacement.setAttribute(key,String(value));
        replacement.appendChild(xml.createTextNode(run.text));paragraph.insertBefore(replacement,node);
      }
      paragraph.removeChild(node);
    });
  });
  return changed?new XMLSerializer().serializeToString(xml):document.original_xml;
}
/** @param {any[]} [blocks] @param {any} [metadata] */
export function serializePlainFDX(blocks=[],metadata={}){
  if(metadata.document?.original_xml)return serializeFDXDocument(metadata.document,blocks);
  const xml=new DOMParser().parseFromString('<FinalDraft DocumentType="Script" Template="No" Version="1"><Content/></FinalDraft>','text/xml');
  const root=xml.documentElement,content=children(root,'Content')[0];
  /** @param {Element} parent @param {string} tag @param {Record<string,string>} [attrs] @param {string} [text] */
  const add=(parent,tag,attrs={},text)=>{const node=xml.createElement(tag);for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);if(text!==undefined)node.appendChild(xml.createTextNode(text));parent.appendChild(node);return node;};
  const styles=/** @type {Record<string,string[]>} */({'Scene Heading':['1.50','7.50','0.00','24','Left'],'Action':['1.50','7.50','0.00','12','Left'],'Character':['3.50','7.25','0.00','12','Left'],'Parenthetical':['3.00','5.50','-0.10','0','Left'],'Dialogue':['2.50','6.00','0.00','0','Left'],'Transition':['5.50','7.10','0.00','12','Right']});
  const page=add(root,'PageLayout',{TopMargin:'72',BottomMargin:'72',HeaderMargin:'36',FooterMargin:'36',DocumentLeading:'Normal'});add(page,'PageSize',{Width:'8.50',Height:'11.00'});
  for(const [type,[left,right,indent,space,align]] of Object.entries(styles)){const setting=add(root,'ElementSettings',{Type:type});add(setting,'FontSpec',{Font:'Courier',Size:'12',Style:''});add(setting,'ParagraphSpec',{Type:type,LeftIndent:left,RightIndent:right,FirstIndent:indent,SpaceBefore:space,Spacing:'1',Leading:'Regular',Alignment:align,StartsNewPage:'No'});}
  const hf=add(root,'HeaderAndFooter',{StartingPage:'1',HeaderFirstPage:'No',HeaderVisible:'Yes',FooterVisible:'No'}),header=add(add(hf,'Header'),'Paragraph',{Alignment:'Left',LeftIndent:'1.25',RightIndent:'-1.00',FirstIndent:'0.00'});
  add(header,'Text',{},'\t');add(header,'DynamicLabel',{Type:'Page #',Font:'Courier',Size:'12'});add(header,'Text',{},'.');add(add(header,'Tabstops'),'Tabstop',{Position:'7.25',Type:'Right'});
  const title=add(add(root,'TitlePage'),'Content');add(add(title,'Paragraph',{Type:'Title',Alignment:'Center'}),'Text',{},metadata.title||'UNTITLED SCREENPLAY');add(add(title,'Paragraph',{Type:'Author',Alignment:'Center'}),'Text',{},metadata.author||'AI-BS Suite');
  /** @type {Map<string,Element>} */const groups=new Map();let legacyGroup=0;
  /** @type {string|null} */let activeLegacy=null;
  blocks.forEach((block,index)=>{
    let group=block.dualGroup;
    if(!group&&block.dual){let start=index-1;while(start>=0&&blocks[start].type!=='Character')start--;group=`legacy-dual-${legacyGroup++}`;activeLegacy=group;const dual=add(content,'DualDialogue');for(let position=Math.max(0,start);position<index;position++){const old=children(content,'Paragraph').at(-1);if(old)dual.insertBefore(old,dual.firstChild);}groups.set(group,dual);}
    else if(!group&&activeLegacy&&['Dialogue','Parenthetical'].includes(block.type))group=activeLegacy;
    else if(!group)activeLegacy=null;
    const parent=group?(groups.get(group)||(()=>{const node=add(content,'DualDialogue');groups.set(group,node);return node;})()):content;
    const paragraph=add(parent,'Paragraph',{Type:block.type||'Action',...(block.startsNewPage?{StartsNewPage:'Yes'}:{})});
    for(const run of block.runs||[{text:block.text||'',attributes:{Font:'Courier',Size:'12'}}])add(paragraph,'Text',run.attributes||{},run.text||'');
    for(const note of block.notes||[])add(add(add(paragraph,'ScriptNote',note.attributes||{}),'Paragraph'),'Text',{},note.text||'');
  });
  return '<?xml version="1.0" encoding="UTF-8"?>\n'+new XMLSerializer().serializeToString(xml);
}
