// JS and TS entry points share one rich-preserving runtime.
export {serializePlainFDX as serializeFDX,serializeFDXDocument} from './fdxDocumentFormat.js';
export interface ASTBlock {id:string;type:string;text:string;dual?:boolean;startsNewPage?:boolean;
  dualGroup?:string|null;dualSide?:string|null;runs?:{id?:string;text:string;attributes:Record<string,string>}[];
  notes?:{id?:string;text:string;attributes?:Record<string,string>}[]}
export interface FDXMetadata {title?:string;author?:string;description?:string;document?:unknown}
