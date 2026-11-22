/** Coding mode is opt-in at build time; opening ordinary chat never starts work. */
/** @param {unknown} value */
export function codingModeEnabled(value) { return value === '1'; }

/** @param {unknown} value */
export function codingIdentifier(value) {
  if (typeof value !== 'string' || !/^[a-f0-9]{32}$/.test(value)) throw new Error('Select a retained coding record first.');
  return value;
}

/** @param {{execution_id?:string,state?:string,verification_status?:string,execution_authorized?:boolean,apply_authorized?:boolean,can_apply?:boolean,review_token?:string,execution_mode?:string,execution_backend?:string,application?:{state?:string},blocked_reason?:string,reason?:string,review_diff?:string,static_checks?:{path:string,kind:string,status:string,reason?:string}[],checks?:{argv?:string[],status?:string,returncode?:number|null,stdout?:string,stderr?:string,error?:string}[]}} value @param {string} id */
export function validateCodingExecution(value, id) {
  codingIdentifier(id);
  if (!value || value.execution_id !== id || !['RUNNING','VERIFIED','FAILED','CANCELLED','INTERRUPTED','BLOCKED','INCOMPLETE'].includes(value.state || '')
      || !['not_run','passed','failed'].includes(value.verification_status || '') || typeof value.execution_authorized !== 'boolean'
      || typeof value.apply_authorized !== 'boolean') throw new Error('Coding execution response did not match the selected record.');
  return value;
}
