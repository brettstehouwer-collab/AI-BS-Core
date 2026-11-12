import { readChatHttpResponse } from './chatHttpResponse.js';

/** @typedef {{action:'models'} | {action:'work', model:string, prompt:string, publicInputOnly?:boolean}} OpenCodeWorkerCommand */

/** @param {unknown} command */
export function isOpenCodeWorkerCommand(command) {
  return typeof command === 'string' && /^\s*\/opencode(?:\s|$)/i.test(command);
}

/** @param {string} command @returns {OpenCodeWorkerCommand} */
export function parseOpenCodeWorkerCommand(command) {
  const match = /^\s*\/opencode(?:\s+([\s\S]*))?$/i.exec(command);
  if (!match) throw new Error('Use /opencode models or /opencode <model-id> <coding or review task>.');
  const rest = (match[1] || '').trim();
  if (!rest || rest.toLowerCase() === 'models') return { action: 'models' };
  const task = /^(\S+)\s+([\s\S]+)$/.exec(rest);
  if (!task || !task[2].trim()) throw new Error('Add a coding or review task after the model ID. Use /opencode models to see the workers.');
  const model = task[1].replace(/^opencode\//, '');
  if (!/^[a-z0-9][a-z0-9.-]{0,95}$/.test(model)) throw new Error('Choose an OpenCode worker ID from /opencode models.');
  const publicInputOnly = /^--public(?:\s|$)/.test(task[2]);
  const prompt = (publicInputOnly ? task[2].replace(/^--public(?:\s+|$)/, '') : task[2]).trim();
  if (!prompt) throw new Error('Add a coding or review task after --public.');
  if (new TextEncoder().encode(prompt).length > 32768) throw new Error('The OpenCode task exceeds 32 KiB. Submit a smaller task.');
  return { action: 'work', model, prompt, ...(publicInputOnly ? { publicInputOnly: true } : {}) };
}

/** @param {unknown} models */
function catalogueText(models) {
  if (!Array.isArray(models) || !models.length) throw new Error('OpenCode worker catalogue is unavailable.');
  const rows = models.map(item => {
    if (!item || typeof item.id !== 'string' || !/^[a-z0-9.-]+$/.test(item.id)) throw new Error('OpenCode returned an invalid worker catalogue.');
    const privacy = [typeof item.privacy === 'string' ? item.privacy : item.retention || 'Review the linked model terms before sharing private material.',
      item.limits, item.public_nonconfidential_input_only ? 'Requires --public and public, non-confidential task text.' : ''].filter(Boolean).join(' ');
    return `| ${item.label || item.name || item.id} | \`${item.id}\` | ${String(privacy).replace(/[|\r\n]/g, ' ')} |`;
  });
  return '### Additional OpenCode coding/review workers\n\n' +
    'Stehouwer and your existing providers remain selected as before. These hosted workers receive only the task text after their model ID.\n\n' +
    '| Worker | ID | Data handling |\n|---|---|---|\n' + rows.join('\n') +
    '\n\nUse `/opencode <model-id> <coding or review task>`. NVIDIA trial workers require `/opencode <model-id> --public <task>` to declare that the supplied text is public and non-confidential. Offers and capacity can change; a listed worker is not proof of account access. No paid fallback is used.\n\n' +
    '[OpenCode model terms](https://opencode.ai/docs/console/models/)';
}

/**
 * Explicit extra worker; no history, files, retrieval context or primary selection is sent.
 * @param {{command:string, backendUrl:string, headers?:HeadersInit, signal?:AbortSignal|null,
 *   planOnly?:boolean, fetchImpl?:typeof fetch}} options
 */
export async function requestOpenCodeWorker({ command, backendUrl, headers, signal, planOnly = false, fetchImpl = fetch }) {
  const task = parseOpenCodeWorkerCommand(command);
  if (task.action === 'work' && planOnly) throw new Error('Plan mode: no OpenCode worker was invoked.');
  const url = `${backendUrl.replace(/\/$/, '')}/api/ai/opencode/${task.action === 'models' ? 'models' : 'work'}`;
  const response = await fetchImpl(url, task.action === 'models'
    ? { headers, signal }
    : { method: 'POST', headers, signal, body: JSON.stringify({ model: task.model, prompt: task.prompt,
      ...(task.publicInputOnly ? { public_input_only: true } : {}) }) });
  const data = await readChatHttpResponse(response);
  if (task.action === 'models') return { content: catalogueText(data.models), displayName: 'OpenCode worker catalogue' };
  if (data.status !== 'completed' || typeof data.content !== 'string' || !data.content.trim()
      || data.model !== task.model && data.model !== `opencode/${task.model}`) {
    throw new Error('The selected OpenCode worker did not return a verified complete result. No substitute was requested.');
  }
  return { content: data.content + '\n\n*OpenCode worker proposal. No project file changes or test results are implied.*',
    displayName: `OpenCode worker · ${task.model}`, receipt: data.receipt };
}
