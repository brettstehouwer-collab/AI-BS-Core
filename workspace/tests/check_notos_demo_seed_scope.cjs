// Trusted static scope/privacy check. Private originals are read only; no original literals are logged.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const { createRequire } = require('node:module');
const req = createRequire('C:/AI-BS/frontend/package.json'), parser = req('@babel/parser');
const checkpoint = process.argv[2];
if (!/^C:\\AI-BS\\backups\\notos_demo_seed_\d{8}T\d{6,}Z$/.test(checkpoint) || !fs.statSync(checkpoint).isDirectory()) throw Error('Fixed private checkpoint required');
const root = 'C:/AI-BS', paths = ['frontend/components/NotosEnterpriseOSTab.jsx', 'frontend/src/components/NotosEnterpriseOSTab.jsx', 'frontend/components/components/NotosEnterpriseOSTab.jsx', 'frontend/src/components/components/NotosEnterpriseOSTab.jsx'];
const parse = text => parser.parse(text, { sourceType: 'module', plugins: ['jsx'] });
const hash = buffer => crypto.createHash('sha256').update(buffer).digest('hex').toUpperCase();
const original = fs.readFileSync(path.join(checkpoint, 'original_1.jsx'), 'utf8'), current = fs.readFileSync(path.join(root, paths[1]), 'utf8');
const seedNames = ['cellarInventory', 'beoList', 'eightySixItems', 'shiftLogs', 'employeeChatDepts', 'selectedPostingRole'];
function literal(node) {
  if (['StringLiteral', 'NumericLiteral', 'BooleanLiteral'].includes(node.type)) return node.value;
  if (node.type === 'ArrayExpression') return node.elements.map(literal);
  if (node.type === 'ObjectExpression') return Object.fromEntries(node.properties.map(item => [item.key.name || item.key.value, literal(item.value)]));
  throw Error('Static seed data expected');
}
function collect(ast) {
  const states = {}, options = [], contacts = {}, marker = [];
  function visit(node, inExport = false) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'VariableDeclarator' && node.id?.name === 'handleExportBeoDocx') inExport = true;
    if (node.type === 'VariableDeclarator' && node.init?.callee?.name === 'useState' && seedNames.includes(node.id?.elements?.[0]?.name)) {
      const name = node.id.elements[0].name, argument = node.init.arguments[0];
      states[name] = argument.type === 'ArrowFunctionExpression' ? argument.body.body.find(item => item.type === 'ReturnStatement').argument : argument;
    }
    if (node.type === 'JSXElement' && node.openingElement.name.name === 'option') options.push(node);
    if (node.type === 'JSXElement' && node.openingElement.attributes?.some(item => item.name?.name === 'role' && item.value?.value === 'note')) marker.push(node);
    if (inExport && node.type === 'ObjectProperty' && ['contact_email', 'contact_phone', 'special_requests'].includes(node.key.name)) contacts[node.key.name] = node.value;
    for (const [key, value] of Object.entries(node)) {
      if (['loc', 'start', 'end'].includes(key)) continue;
      if (Array.isArray(value)) value.forEach(item => visit(item, inExport));
      else if (value && typeof value === 'object') visit(value, inExport);
    }
  }
  visit(ast); return { states, options, contacts, marker };
}
function normalize(ast, info) {
  const placeholders = new Set([...Object.values(info.states), ...Object.values(info.contacts)]);
  const optionNodes = new Set(info.options), markerNodes = new Set(info.marker);
  function transform(value) {
    if (value === null || typeof value !== 'object') return value;
    if (placeholders.has(value)) return { type: 'StringLiteral', value: 'ALLOWED_DEMO_DATA_CHANGE' };
    if (Array.isArray(value)) return value.filter(item => !markerNodes.has(item) && !(item?.type === 'JSXText' && !item.value.trim())).map(transform);
    const output = {};
    for (const [key, child] of Object.entries(value)) {
      if (['loc', 'start', 'end', 'extra', 'comments', 'leadingComments', 'trailingComments', 'innerComments', 'tokens'].includes(key)) continue;
      output[key] = optionNodes.has(value) && key === 'children' ? [{ type: 'JSXText', value: 'ALLOWED_DEMO_POSTING_ROLE' }] : transform(child);
    }
    return output;
  }
  return JSON.stringify(transform(ast));
}
const beforeAst = parse(original), afterAst = parse(current), before = collect(beforeAst), after = collect(afterAst);
const oldData = Object.fromEntries(Object.entries(before.states).map(([name, node]) => [name, literal(node)])), data = Object.fromEntries(Object.entries(after.states).map(([name, node]) => [name, literal(node)]));
const results = [];
const check = (id, passed) => results.push({ id, passed: Boolean(passed) });
const oldChannels = oldData.employeeChatDepts.flatMap(item => item.channels), newChannels = data.employeeChatDepts.flatMap(item => item.channels);
check('only_declared_data_and_marker_changed', normalize(beforeAst, before) === normalize(afterAst, after));
check('all_four_mirrors_identical', new Set(paths.map(relative => hash(fs.readFileSync(path.join(root, relative))))).size === 1);
check('all_original_mirrors_preserved', paths.every((_, index) => fs.existsSync(path.join(checkpoint, 'original_' + index + '.jsx'))));
check('all_six_seed_states_present', Object.keys(after.states).length === 6);
check('channel_ids_and_breadth_unchanged', oldChannels.length === 6 && newChannels.length === 6 && oldChannels.every((channel, index) => channel.id === newChannels[index].id) && data.employeeChatDepts.length === oldData.employeeChatDepts.length);
check('event_location_and_status_enums_unchanged', data.beoList.length === oldData.beoList.length && data.beoList.every((item, index) => item.location === oldData.beoList[index].location && item.status === oldData.beoList[index].status));
check('stock_regions_and_count_unchanged', data.cellarInventory.length === oldData.cellarInventory.length && data.cellarInventory.every((item, index) => item.region === oldData.cellarInventory[index].region));
check('shift_location_keys_unchanged', JSON.stringify(Object.keys(data.shiftLogs)) === JSON.stringify(Object.keys(oldData.shiftLogs)));
check('seed_record_schemas_preserved', ['cellarInventory', 'beoList', 'eightySixItems'].every(name => data[name].every(item => JSON.stringify(Object.keys(item).sort()) === JSON.stringify(Object.keys(oldData[name][0]).sort()))));
check('numeric_record_values_are_finite', data.cellarInventory.every(item => ['vintage', 'bottles', 'wholesale', 'menuPrice'].every(key => Number.isFinite(item[key]))) && data.beoList.every(item => ['guests', 'total', 'deposit', 'balance'].every(key => Number.isFinite(item[key]))));
check('data_explicitly_demo_or_fictional', data.cellarInventory.every(item => item.name.startsWith('Demo ')) && data.beoList.every(item => item.client.startsWith('Demo ') && item.name.startsWith('Demo ')) && data.eightySixItems.every(item => item.item.startsWith('Demo ')) && Object.values(data.shiftLogs).every(item => /Fictional demo/.test(item.managerNotes)) && newChannels.every(channel => channel.messages.every(message => message.sender.startsWith('Demo ') && /Fictional demo/.test(message.text))));
check('posting_default_and_all_options_are_demo', data.selectedPostingRole.startsWith('Demo ') && after.options.length === 7 && after.options.every(item => item.children.filter(child => child.type === 'JSXText').map(child => child.value).join('').trim().startsWith('Demo ')));
check('export_contacts_neutralized', after.contacts.contact_email.value === '' && after.contacts.contact_phone.value === '' && /Fictional demo/.test(after.contacts.special_requests.value));
check('visible_marker_static_and_singular', after.marker.length === 1 && after.marker[0].children.every(child => child.type === 'JSXText') && after.marker[0].children.some(child => child.value.includes('Demo workspace')) && !after.marker[0].openingElement.attributes.some(item => /^on/.test(item.name?.name || '')));
check('no_evidence_or_test_imports_in_product', !/backups\/|original_[0-9]|synthetic_business_seed_candidate|workspace\/tests/.test(current));
const receipt = { createdAt: new Date().toISOString(), originalRecordProvenance: 'unknown', privateOriginalsRetained: true, results, total: results.length, passed: results.filter(row => row.passed).length, sourceHash: hash(Buffer.from(current)), mirrors: paths.map(relative => ({ path: relative, sha256: hash(fs.readFileSync(path.join(root, relative))) })) };
fs.writeFileSync(path.join(checkpoint, 'scope_verification.json'), JSON.stringify(receipt, null, 2), { flag: 'wx' });
console.log(JSON.stringify({ total: receipt.total, passed: receipt.passed, failed: results.filter(row => !row.passed).length }));
if (receipt.passed !== receipt.total) process.exitCode = 1;
