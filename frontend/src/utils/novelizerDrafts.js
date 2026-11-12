// Owner/project/chapter-bound browser recovery. Nothing here writes a host file.
/** @param {{getItem:(key:string)=>string|null|undefined,setItem:(key:string,value:string)=>void}|null} storage */
export function createNovelizerDraftStore(storage) {
  const buffers = new Map();
  let clock = 0;
  /** @param {string} scope @param {string} project @param {number} chapter */
  const key = (scope, project, chapter) => `novelizer-recovery-v1:${JSON.stringify([scope, project, chapter])}`;
  /** @param {any} buffer */
  const persist = buffer => {
    try { storage?.setItem(buffer.key, JSON.stringify(buffer)); buffer.recoveryError = ''; }
    catch { buffer.recoveryError = 'Browser recovery is unavailable; keep this editor open or copy the draft.'; }
  };
  /** @param {string} scope @param {string} project @param {number} chapter */
  function get(scope, project, chapter) {
    const id = key(scope, project, chapter);
    if (!buffers.has(id)) {
      let retained;
      try { retained = JSON.parse(storage?.getItem(id) || 'null'); } catch { retained = null; }
      const valid = retained && typeof retained.text === 'string' && retained.text.length <= 2000000;
      buffers.set(id, { title:'', text:'', savedText:'', revision:'missing',
        dirty:false, editVersion:0, pending:null, candidate:'', remote:null, recovery:[],
        ...(valid ? retained : {}), key:id, scope, project, chapter, lastMutation:0 });
    }
    return buffers.get(id);
  }
  /** @param {any} buffer */
  const mutate = buffer => { buffer.lastMutation = ++clock; persist(buffer); return buffer; };
  /** @param {string} scope @param {string} project @param {number} chapter @param {string} title @param {string} text */
  function edit(scope, project, chapter, title, text) {
    const buffer = get(scope, project, chapter);
    Object.assign(buffer, { title, text, dirty:true, editVersion:buffer.editVersion+1 });
    return mutate(buffer);
  }
  /** @param {string} scope @param {string} project @param {any} saved @param {number} ticket */
  function mergeSaved(scope, project, saved, ticket) {
    if (!Number.isInteger(saved.chapter_number) || typeof saved.prose_content !== 'string'
        || typeof saved.chapter_title !== 'string' || !/^[a-f0-9]{64}$/.test(saved.revision || ''))
      throw new Error('The saved chapter response is incomplete. The local draft was retained.');
    const buffer = get(scope, project, saved.chapter_number);
    if (buffer.lastMutation > ticket) return buffer;
    if (buffer.dirty) { buffer.remote = saved; persist(buffer); return buffer; }
    Object.assign(buffer, { title:saved.chapter_title, text:saved.prose_content, savedText:saved.prose_content,
      revision:saved.revision, remote:null });
    persist(buffer); return buffer;
  }
  /** @param {string} scope @param {string} project @param {number} chapter @param {string} title */
  function beginSave(scope, project, chapter, title) {
    const buffer = get(scope, project, chapter);
    const fingerprint = JSON.stringify([buffer.text, title, buffer.revision]);
    if (buffer.pending?.fingerprint === fingerprint) return buffer.pending;
    const snapshot = { scope, project, chapter, title, text:buffer.text, expected_revision:buffer.revision,
      editVersion:buffer.editVersion, fingerprint, request_id:crypto.randomUUID().replaceAll('-', '') };
    buffer.pending = snapshot; mutate(buffer); return snapshot;
  }
  /** @param {any} snapshot @param {any} data */
  function ack(snapshot, data) {
    if (data.status !== 'saved' || data.project_name !== snapshot.project || data.chapter_number !== snapshot.chapter
        || data.request_id !== snapshot.request_id || !/^[a-f0-9]{64}$/.test(data.revision || ''))
      throw new Error('The save acknowledgement did not match this chapter. Keep the draft and retry.');
    const buffer = get(snapshot.scope, snapshot.project, snapshot.chapter);
    buffer.revision = data.revision; buffer.savedText = snapshot.text;
    buffer.dirty = buffer.text !== snapshot.text || buffer.editVersion !== snapshot.editVersion;
    if (buffer.pending?.request_id === snapshot.request_id) buffer.pending = null;
    return mutate(buffer);
  }
  /** @param {string} scope @param {string} project @param {number} chapter @param {string} title */
  function beginConversion(scope, project, chapter, title) {
    const buffer = get(scope, project, chapter);
    return { scope, project, chapter, title, editVersion:buffer.editVersion, dirty:buffer.dirty };
  }
  /** @param {any} snapshot @param {string} prose @param {boolean} allowApply */
  function generated(snapshot, prose, allowApply) {
    const buffer = get(snapshot.scope, snapshot.project, snapshot.chapter);
    if (!allowApply || snapshot.dirty || buffer.editVersion !== snapshot.editVersion) buffer.candidate = prose;
    else { buffer.text = prose; buffer.title = snapshot.title; buffer.dirty = true; buffer.editVersion++; }
    return mutate(buffer);
  }
  /** @param {string} scope @param {string} project @param {number} chapter @param {any} saved */
  function useSaved(scope, project, chapter, saved) {
    const buffer = get(scope, project, chapter);
    if (buffer.dirty) buffer.recovery.push({ text:buffer.text, title:buffer.title });
    Object.assign(buffer, { text:saved.prose_content, title:saved.chapter_title, revision:saved.revision,
      savedText:saved.prose_content, dirty:false, remote:null, pending:null, editVersion:buffer.editVersion+1 });
    return mutate(buffer);
  }
  /** @param {string} scope @param {string} project @param {number} chapter */
  function restore(scope, project, chapter) {
    const buffer = get(scope, project, chapter); const previous = buffer.recovery.pop();
    if (previous) edit(scope, project, chapter, previous.title, previous.text);
    return buffer;
  }
  return { get, edit, mergeSaved, beginSave, ack, beginConversion, generated, useSaved, restore, stamp:() => clock };
}
