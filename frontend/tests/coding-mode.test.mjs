import test from 'node:test';
import assert from 'node:assert/strict';
import { codingModeEnabled, codingIdentifier, validateCodingExecution } from '../src/utils/codingMode.js';

const id = 'a'.repeat(32);
test('coding mode requires explicit build-time opt-in', () => {
  for (const value of [undefined, null, '', '0', 'false', 'true', true, 1]) assert.equal(codingModeEnabled(value), false);
  assert.equal(codingModeEnabled('1'), true);
});
test('saved execution IDs reject paths and malformed references', () => {
  assert.equal(codingIdentifier(id), id);
  for (const value of ['', '../saved_data', 'A'.repeat(32), id + '/review', null]) assert.throws(() => codingIdentifier(value));
});
test('execution evidence must match the selected task and include authority fields', () => {
  const evidence = {execution_id:id, state:'BLOCKED', verification_status:'not_run', execution_authorized:false, apply_authorized:false};
  assert.deepEqual(validateCodingExecution(evidence, id), evidence);
  assert.throws(() => validateCodingExecution({...evidence, execution_id:'b'.repeat(32)}, id));
  assert.throws(() => validateCodingExecution({...evidence, apply_authorized:undefined}, id));
  assert.throws(() => validateCodingExecution({...evidence, execution_authorized:'false'}, id));
});
