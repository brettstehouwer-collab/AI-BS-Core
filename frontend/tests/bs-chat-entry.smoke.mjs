import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { transform } from 'esbuild';
import { mergeConfig } from 'vite';

const source = await readFile(new URL('../bs-chat.jsx', import.meta.url), 'utf8');
const html = await readFile(new URL('../bs-chat.html', import.meta.url), 'utf8');
const configSource = await readFile(new URL('../vite.bs-chat.config.mjs', import.meta.url), 'utf8');
let checks = 0;
const check = (name, run) => { run(); checks++; console.log(`ok ${checks} - ${name}`); };
check('dedicated HTML entry with mobile viewport', () => {
  assert.match(html, /viewport-fit=cover/);
  assert.match(html, /src="\/bs-chat\.jsx"/);
  assert.doesNotMatch(html, /src="\/main\.jsx"/);
});
await transform(source, { loader: 'jsx', format: 'esm' });
check('entry JSX compiles', () => assert.ok(source.includes('ReactDOM.createRoot')));
check('Studio shell is excluded', () => assert.doesNotMatch(source, /from ['"]\.\/(?:App|main)\.jsx['"]/));
check('existing chat and login components reused', () => {
  assert.match(source, /from '\.\/components\/MobileStehouwerChat\.jsx'/);
  assert.match(source, /from '\.\/components\/LoginModal\.jsx'/);
});
check('Firebase observer owns admission and account store', () => {
  assert.match(source, /onAuthStateChanged\(auth, user =>/);
  assert.match(source, /setCurrentUser\(admitted\)/);
  assert.match(source, /if \(!currentUser\) return/);
});
check('verified allowlist required without synthetic identity', () => {
  assert.match(source, /user && user\.emailVerified/);
  assert.match(source, /ADMIN_EMAILS\.includes/);
  assert.match(source, /ADMIN_UIDS\.includes/);
  assert.doesNotMatch(source, /local_admin|aibs_cached_user|firebase\/firestore/);
});
check('local backend constrained to desktop loopback HTTP', () => {
  assert.match(source, /window\.location\.protocol === 'http:'/);
  assert.match(source, /\['localhost', '127\.0\.0\.1'\]\.includes\(window\.location\.hostname\)/);
  assert.match(source, /localDesktop \? 'http:\/\/127\.0\.0\.1:8000' : getApiBase\(\)/);
});
check('owned fetch requires current account and guards redirects', () => {
  assert.match(source, /auth\.currentUser !== user \|\| authGeneration !== generation/);
  assert.match(source, /redirect: 'error'/);
  assert.match(source, /await user\.getIdToken\(\)/);
});
check('provider configuration is read using existing authenticated helper', () => {
  assert.match(source, /headers: await chatAuthHeaders\(\{\}, uid\)/);
  assert.match(source, /readBSChatProviderConfig\(await response\.json\(\)\)/);
  assert.doesNotMatch(source, /method: ['"]POST['"]/);
});
check('browser fallback states session boundary', () => {
  assert.match(source, /href="https:\/\/ai-bs-dashboard\.web\.app\/chat"/);
  assert.match(source, /Browser and app sign-in sessions are separate/);
});
check('account switch remounts chat without Studio navigation', () => {
  assert.match(source, /key=\{currentUser\.uid\}/);
  assert.match(source, /window\.location\.assign\('\/chat'\)/);
});
check('additive build retains existing entry points', () => {
  assert.match(configSource, /import studioConfig from '\.\/vite\.config\.js'/);
  const merged = mergeConfig({ build: { rollupOptions: { input: { main: 'index.html', writer: 'writer.html' } } } },
    { build: { rollupOptions: { input: { chat: 'bs-chat.html' } } } });
  assert.deepEqual(merged.build.rollupOptions.input, { main: 'index.html', writer: 'writer.html', chat: 'bs-chat.html' });
});
console.log(JSON.stringify({ status: 'passed', checks }));
