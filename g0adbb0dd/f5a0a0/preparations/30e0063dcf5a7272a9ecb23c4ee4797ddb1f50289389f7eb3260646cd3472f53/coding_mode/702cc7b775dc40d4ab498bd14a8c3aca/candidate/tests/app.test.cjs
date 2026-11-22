const test=require('node:test'); const assert=require('node:assert/strict');
test('candidate',()=>assert.match(require('node:fs').readFileSync('src/app.js','utf8'),/value = 42/));
