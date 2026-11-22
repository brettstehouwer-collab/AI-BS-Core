import { validateScreenplayHandoff, screenplayErrorMessage } from './screenplayHandoff.js';

/** Explicit saved-project launch only; no automatic retries, paths or process IDs.
 * @param {{backendUrl:string,handoff:any,getFreshHeaders:()=>Promise<Record<string,string>>,isCurrent?:()=>boolean,fetchImpl?:typeof fetch}} options
 */
export async function launchNativeScreenplay({backendUrl,handoff,getFreshHeaders,isCurrent=()=>true,fetchImpl=globalThis.fetch}) {
  const expected=validateScreenplayHandoff(handoff);
  if(typeof getFreshHeaders!=='function'||!isCurrent())throw Error('The screenplay context changed. Your project remains open.');
  const headers=await getFreshHeaders();
  if(!/^Bearer \S+$/.test(headers?.Authorization||'')||!isCurrent())throw Error('Sign in again from the current project to open the native writer.');
  const response=await fetchImpl(`${backendUrl}/api/screenwriting/native/launch`,{
    method:'POST',headers:{...headers,'Content-Type':'application/json'},
    body:JSON.stringify({project_name:expected.project,expected_revision:expected.revision,expected_source_sha256:expected.source_sha256})
  });
  const data=await response.json().catch(()=>({}));
  if(!isCurrent())throw Error('The screenplay context changed after the launch request. Your drafts remain retained.');
  if(response.status!==202||data.status!=='starting'||data.project!==expected.project){
    throw Error(screenplayErrorMessage(data,'Native launch was not confirmed. Your saved project remains open.'));
  }
  return {status:'starting',project:expected.project};
}
