require('node:test')('candidate',()=>require('node:assert/strict').match(require('node:fs').readFileSync('src/app.js','utf8'),/value = 42/));
