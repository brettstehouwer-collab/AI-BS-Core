// Trusted static release check; no browser, network, project code or file writes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const file = 'C:/AI-BS/frontend/index.html';
const text = fs.readFileSync(file, 'utf8');
const tag = [...text.matchAll(/<meta\b[^>]*>/gi)].map(x => x[0]).find(x => /http-equiv\s*=\s*["']Content-Security-Policy["']/i.test(x));
assert(tag, 'CSP must remain present');
const content = /\bcontent\s*=\s*"([^"]*)"/i.exec(tag)?.[1];
assert(content, 'CSP content must remain present');
const privateIp = ip => {
  const [a,b] = ip.split('.').map(Number);
  return a === 10 || a === 192 && b === 168 || a === 172 && b >= 16 && b <= 31 || a === 100 && b >= 64 && b <= 127 || a === 169 && b === 254;
};
const ips = [...content.matchAll(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g)].map(x => x[0]);
assert.equal(ips.filter(privateIp).length, 0, 'Public HTML must not bake private LAN/VPN addresses into CSP');
assert(/(?:localhost|127\.0\.0\.1)/.test(content), 'Keep the existing local bridge origins');
assert(content.includes('https://api.brettstehouwer.live'), 'Keep the established hosted API origin');
assert(content.includes('googleapis.com') && content.includes('gstatic.com'), 'Keep Firebase/Google runtime origins');
assert(!/<script\b[^>]*\bsrc\s*=\s*["']\/?analytics\.js["']/i.test(text), 'Do not automatically load the custom detailed tracking script');
const entry = fs.readFileSync('C:/AI-BS/frontend/main.jsx', 'utf8');
assert(!entry.includes('AIBSAnalytics') || /if\s*\(\s*window\.AIBSAnalytics/.test(entry) || /window\.AIBSAnalytics\?\./.test(entry), 'Any optional analytics calls must remain guarded');
console.log('PASS public CSP preserves required origins without private addresses; detailed tracking is not automatically loaded.');
