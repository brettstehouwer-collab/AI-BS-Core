// Trusted controlled UI fixture: all exports are intercepted; no application API is contacted.
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import NotosEnterpriseOSTab from '../../frontend/src/components/NotosEnterpriseOSTab.jsx';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
Element.prototype.scrollIntoView = function () {};
const results = [], requests = [], downloads = [];
let unexpectedRequests = 0;
window.alert = () => {};
URL.createObjectURL = () => 'blob:controlled-demo';
URL.revokeObjectURL = () => {};
HTMLAnchorElement.prototype.click = function () { downloads.push(this.download); };
window.fetch = async (url, options = {}) => {
  if (typeof url !== 'string' || !url.startsWith('http://fixture.invalid/')) {
    unexpectedRequests++;
    throw new Error('Only intercepted fixture exports are allowed');
  }
  requests.push({ path: new URL(url).pathname, method: options.method, body: JSON.parse(options.body) });
  return { ok: true, blob: async () => new Blob(['controlled export'], { type: 'application/octet-stream' }) };
};
const host = document.getElementById('component');
let root;
const flush = () => new Promise(resolve => setTimeout(resolve, 0));
const assert = value => { if (!value) throw new Error('assertion'); };
async function check(id, fn) {
  try { await fn(); results.push({ id, passed: true }); }
  catch { results.push({ id, passed: false }); }
}
const buttons = () => [...host.querySelectorAll('button')];
const button = expression => {
  const found = buttons().find(item => expression.test(item.textContent));
  if (!found) throw new Error('control');
  return found;
};
async function click(item) { await act(async () => { item.click(); await flush(); }); }
async function tab(expression) { await click(button(expression)); }
async function type(input, value) {
  const descriptor = Object.getOwnPropertyDescriptor(input instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype, 'value');
  await act(async () => { descriptor.set.call(input, value); input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? 'change' : 'input', { bubbles: true })); await flush(); });
}
function channelState() {
  for (let index = 0; index < localStorage.length; index++) {
    try {
      const value = JSON.parse(localStorage.getItem(localStorage.key(index)));
      if (Array.isArray(value) && value.length && value.every(item => Array.isArray(item.channels))) return value;
    } catch {}
  }
  throw new Error('channel state');
}
const channels = () => channelState().flatMap(department => department.channels);
const messageCount = () => channels().map(channel => channel.messages.length);
const inputForChat = () => [...host.querySelectorAll('input')].find(item => item.placeholder && /message|type/i.test(item.placeholder));
const sendButton = () => inputForChat()?.parentElement.querySelector('button');

(async () => {
  localStorage.clear();
  await act(async () => { root = createRoot(host); root.render(<NotosEnterpriseOSTab backendUrl="http://fixture.invalid" />); await flush(); });
  await check('publication_demo_indicator', async () => assert(/Demo workspace/.test(host.textContent)));
  await tab(/Cellar/);
  await check('publication_inventory_fictional_rows', async () => assert((host.textContent.match(/Demo Cellar Sample/g) || []).length === 6));
  await check('inventory_numeric_formatting_survives', async () => assert(!/NaN|undefined/.test(host.textContent) && /\$/.test(host.textContent) && host.querySelector('input')));

  await tab(/Banquets & BEOs/);
  await check('publication_event_fictional_record', async () => assert(/Demo Event/.test(host.textContent) && /Demo Client/.test(host.textContent)));
  await check('event_export_complete_numeric_payload', async () => {
    await click(button(/Export Word BEO/i));
    const request = requests.at(-1), data = request?.body;
    assert(request?.method === 'POST' && data && ['guest_count', 'subtotal', 'service_charge', 'tax', 'total', 'deposit_paid', 'balance_due'].every(key => Number.isFinite(data[key])));
    assert(data.total === data.deposit_paid + data.balance_due && downloads.length === 1);
  });
  await check('publication_export_only_demo_contacts_and_event', async () => {
    const data = requests.at(-1)?.body;
    assert(data?.event_name.startsWith('Demo Event') && data.client_name.startsWith('Demo Client') && data.contact_email === '' && data.contact_phone === '' && /demo/i.test(data.special_requests));
  });
  await click(button(/Grand Haven/));
  await check('event_location_enum_preserved', async () => assert(/Demo Event/.test(host.textContent)));

  await tab(/Position & Staff Chat/);
  await check('chat_department_channel_breadth_preserved', async () => assert(channelState().length === 5 && channels().length === 6));
  await check('publication_chat_seed_is_fictional', async () => assert(channels().every(channel => channel.name.startsWith('Demo ') && channel.messages.length > 0 && channel.messages.every(message => message.sender.startsWith('Demo ') && /fictional|demo/i.test(message.text)))));
  await check('initial_active_channel_remains_usable', async () => assert(inputForChat() && !inputForChat().disabled && sendButton() && !sendButton().disabled));
  const posting = host.querySelector('select');
  await check('publication_posting_roles_are_fictional', async () => assert(posting && posting.options.length === 7 && [...posting.options].every(option => option.value.startsWith('Demo ')) && posting.value.startsWith('Demo ')));
  await check('chat_trimmed_send_only_changes_active_channel', async () => {
    const before = messageCount();
    await type(inputForChat(), '  controlled demo note  ');
    await click(sendButton());
    const after = messageCount();
    assert(after.filter((count, index) => count === before[index] + 1).length === 1 && after.filter((count, index) => count !== before[index]).length === 1);
    assert(channels().some(channel => channel.messages.at(-1).text === 'controlled demo note') && inputForChat().value === '');
  });
  await check('chat_role_change_and_enter_send', async () => {
    await type(posting, posting.options[1].value);
    const expected = posting.value.split('(')[0].trim(), before = messageCount().reduce((a, b) => a + b, 0);
    await type(inputForChat(), 'controlled second demo note');
    await act(async () => { inputForChat().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true })); await flush(); });
    assert(messageCount().reduce((a, b) => a + b, 0) === before + 1 && channels().some(channel => channel.messages.at(-1).sender === expected && channel.messages.at(-1).text === 'controlled second demo note'));
  });

  await tab(/Kitchen.*Board/);
  await check('publication_initial_86_is_fictional', async () => assert(/Demo Pantry Sample/.test(host.textContent)));
  await check('broadcast_adds_item_and_fixed_channel_alert', async () => {
    const before = messageCount(), fields = [...host.querySelectorAll('input')];
    assert(fields.length === 2);
    await type(fields[0], '  Controlled pantry item  ');
    await type(fields[1], '  controlled reason  ');
    await click(button(/Broadcast 86/));
    const after = messageCount();
    assert(/Controlled pantry item/.test(host.textContent) && fields.every(field => field.value === ''));
    assert(after.filter((count, index) => count === before[index] + 1).length === 1 && channels().some(channel => /Controlled pantry item/.test(channel.messages.at(-1).text) && /controlled reason/.test(channel.messages.at(-1).text)));
  });
  await check('restock_removes_only_selected_86', async () => {
    const clear = buttons().filter(item => /Restock \/ Clear 86/.test(item.textContent));
    assert(clear.length === 2);
    await click(clear[0]);
    assert(!/Controlled pantry item/.test(host.textContent) && buttons().filter(item => /Restock \/ Clear 86/.test(item.textContent)).length === 1);
  });

  await tab(/Daily GM Shift Handoff/);
  await check('handoff_export_control_remains_available', async () => assert(!button(/Export.*Brief.*Word/i).disabled));
  await check('location_specific_briefs_use_both_shift_records', async () => {
    await click(button(/Grand Rapids/));
    await click(button(/Export.*Brief.*Word/i));
    const first = requests.at(-1)?.body;
    await click(button(/Grand Haven/));
    await click(button(/Export.*Brief.*Word/i));
    const second = requests.at(-1)?.body;
    assert(first && second && first.content !== second.content && /Fictional demo shift GR/.test(first.content) && /Fictional demo shift GH/.test(second.content));
    assert(downloads.length === 3);
  });
  await check('demo_indicator_survives_actions_and_location_switch', async () => assert(/Demo workspace/.test(host.textContent)));
  await check('only_controlled_exports_requested', async () => assert(unexpectedRequests === 0 && requests.length === 3 && requests.every(request => request.method === 'POST')));
  await act(async () => { root.unmount(); await flush(); });
  window.__notosFixtureReport = { results, unexpectedRequests, interceptedExports: requests.length, fixtureStorageOnly: true, realBackendRequests: 0, modelRequests: 0, vmOperations: 0 };
})().catch(() => { window.__notosFixtureReport = { results, fixtureFailure: true, unexpectedRequests, realBackendRequests: 0, modelRequests: 0, vmOperations: 0 }; });
