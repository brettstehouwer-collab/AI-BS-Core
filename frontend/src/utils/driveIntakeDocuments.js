function intakeOriginalMatch(path) {
  return String(path || '').replace(/\\/g, '/').match(/^(.*(?:^|\/)Documents\/Drive_Intake\/[^/]+\/)(?:Originals|Previous_Versions)(?:\/(.*))?$/i);
}

export function isDriveIntakeOriginal(path) {
  return !!intakeOriginalMatch(path);
}

export function driveIntakeWorkingCopyPath(path, extension, id) {
  const match = intakeOriginalMatch(path);
  if (!match || !match[2]) throw new Error('Select a downloaded original first.');
  const filename = match[2].split('/').pop();
  const folders = match[2].split('/').slice(0, -1).join('/');
  const stem = filename.replace(/\.[^.]+$/, '');
  if (!/^[a-z0-9]+$/i.test(extension) || !/^[a-z0-9-]+$/i.test(id)) throw new Error('Invalid working-copy name.');
  return `${match[1]}Working_Copies/${folders ? folders + '/' : ''}${stem}-${id}.${extension}`;
}

// Make an explicitly requested copy. The original is read only and remains at its
// existing path. DOCX conversion extracts paragraphs; it is not a layout roundtrip.
export async function createIntakeWorkingCopy({ backendUrl, path, fetcher = fetch, id = crypto.randomUUID() }) {
  if (!isDriveIntakeOriginal(path)) throw new Error('Select a downloaded original first.');
  const extension = path.split('.').pop().toLowerCase();
  let content;
  if (extension === 'docx') {
    const response = await fetcher(`${backendUrl}/api/drive/download?path=${encodeURIComponent(path)}`);
    if (!response.ok) throw new Error('Could not read the original DOCX. It has not been changed.');
    const form = new FormData();
    form.append('file', await response.blob(), path.replace(/\\/g, '/').split('/').pop());
    const parsed = await fetcher(`${backendUrl}/api/documents/import_docx`, { method: 'POST', body: form });
    const result = await parsed.json();
    if (!parsed.ok || typeof result.content !== 'string') throw new Error(result.detail || 'DOCX text conversion failed.');
    content = result.content;
  } else if (['txt', 'md', 'markdown', 'fountain', 'fdx'].includes(extension)) {
    const response = await fetcher(`${backendUrl}/api/read?filepath=${encodeURIComponent(path)}`);
    const result = await response.json();
    if (!response.ok || typeof result.content !== 'string') throw new Error(result.detail || 'Could not read the original text.');
    content = result.content;
  } else {
    throw new Error('Download this original to open it in its native application.');
  }
  const destination = driveIntakeWorkingCopyPath(path, extension === 'docx' ? 'md' : extension, id);
  const saved = await fetcher(`${backendUrl}/api/save`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: destination, content, create_only: true }),
  });
  const result = await saved.json();
  if (!saved.ok || !result.path) throw new Error(result.detail || 'Working copy could not be saved. The original is unchanged.');
  return result.path;
}
