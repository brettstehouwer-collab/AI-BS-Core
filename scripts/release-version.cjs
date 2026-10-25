#!/usr/bin/env node
'use strict';

// Deliberately bounded: no source sweeps, user documents, credentials, or binaries.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const PACKAGE_PATHS = ['package.json', 'frontend/package.json', 'BroadcastStudioApp/package.json'];
const LOCK_PATHS = PACKAGE_PATHS.map(name => name.replace('package.json', 'package-lock.json'));
const MODULE_PATHS = [
  'frontend/version.js', 'frontend/src/version.js',
  'frontend/components/version.js', 'frontend/components/components/version.js',
  'frontend/src/components/version.js', 'frontend/src/components/components/version.js',
  'BroadcastStudioApp/src/version.js',
];
const RELEASE_FILE = 'release.json';
const PUBLIC_FILE = 'frontend/public/version.json';
const REPO_ROOT = path.resolve(__dirname, '..');
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex');
const today = () => new Date().toISOString().slice(0, 10);

function normalizeVersion(value) {
  const result = String(value).trim().replace(/^v/, '');
  if (!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(result)) {
    throw new Error('Version must be a numeric MAJOR.MINOR.PATCH value.');
  }
  if (result.split('.').some(part => !Number.isSafeInteger(Number(part)))) {
    throw new Error('Version component exceeds safe integer range.');
  }
  return result;
}

function compareVersions(left, right) {
  const a = normalizeVersion(left).split('.').map(Number);
  const b = normalizeVersion(right).split('.').map(Number);
  for (let i = 0; i < 3; i += 1) if (a[i] !== b[i]) return a[i] > b[i] ? 1 : -1;
  return 0;
}

function location(root, relative) {
  const rootReal = fs.realpathSync(root);
  const target = path.resolve(rootReal, relative);
  if (!target.startsWith(rootReal + path.sep)) throw new Error(`Path outside repository: ${relative}`);
  let ancestor = target;
  while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
  const resolved = fs.realpathSync(ancestor);
  if (resolved !== rootReal && !resolved.startsWith(rootReal + path.sep)) {
    throw new Error(`Linked path outside repository: ${relative}`);
  }
  return target;
}

function read(root, relative, optional = false) {
  const file = location(root, relative);
  try { return fs.readFileSync(file); }
  catch (error) { if (optional && error.code === 'ENOENT') return null; throw error; }
}

function json(raw, relative) {
  try { return JSON.parse(raw.toString('utf8').replace(/^\uFEFF/, '')); }
  catch { throw new Error(`Invalid JSON in ${relative}`); }
}

function jsonBytes(value) { return Buffer.from(JSON.stringify(value, null, 2) + '\n'); }

function moduleBytes(version, date) {
  return Buffer.from([
    '// Generated from repository version.txt by scripts/release-version.cjs.',
    '// Run npm run version:check before building; do not edit this mirror by hand.',
    `export const SYSTEM_VERSION = 'v${version}';`,
    `export const SYSTEM_VERSION_NUM = '${version}';`,
    `export const RELEASE_DATE = '${date}';`,
    `export const RELEASE_TAG = 'v${version}';`,
    'export default SYSTEM_VERSION;',
    '',
  ].join('\n'));
}

function plan(root, options = {}) {
  const current = normalizeVersion(read(root, 'version.txt').toString('utf8'));
  if (options.bump && options.version) throw new Error('Choose a patch bump or an explicit version, not both.');
  let version = current;
  if (options.bump) {
    if (options.bump !== 'patch') throw new Error('Only automatic patch bumps are supported.');
    const parts = current.split('.').map(Number);
    parts[2] += 1;
    version = normalizeVersion(parts.join('.'));
  } else if (options.version) version = normalizeVersion(options.version);
  if ((options.bump || options.version) && compareVersions(version, current) <= 0) {
    throw new Error('A new release version must be greater than the current authority.');
  }

  const priorRaw = read(root, RELEASE_FILE, true);
  const prior = priorRaw ? json(priorRaw, RELEASE_FILE) : null;
  const date = options.date || (prior && prior.version === version ? prior.release_date : today());
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isFinite(Date.parse(date)) || new Date(date).toISOString().slice(0, 10) !== date) {
    throw new Error('Release date must be a real YYYY-MM-DD date.');
  }
  const rows = [];
  const add = (relative, after, optional = false) => rows.push({
    path: relative, before: read(root, relative, optional), after,
  });
  for (const relative of PACKAGE_PATHS) {
    const data = json(read(root, relative), relative);
    if (compareVersions(data.version, version) > 0) {
      throw new Error(`${relative} has a newer version than the requested authority; review it before syncing.`);
    }
    data.version = version;
    add(relative, jsonBytes(data));
  }
  for (const relative of LOCK_PATHS) {
    const data = json(read(root, relative), relative);
    if (!data.packages || !data.packages['']) throw new Error(`Missing root package record in ${relative}`);
    if (compareVersions(data.version, version) > 0 || compareVersions(data.packages[''].version, version) > 0) {
      throw new Error(`${relative} has a newer version than the requested authority; review it before syncing.`);
    }
    data.version = version;
    data.packages[''].version = version;
    add(relative, jsonBytes(data));
  }
  const metadata = {
    schema_version: 1,
    version,
    release_tag: `v${version}`,
    release_date: date,
    version_authority: 'version.txt',
    artifact_scope: 'application-source',
  };
  add(RELEASE_FILE, jsonBytes(metadata), true);
  add(PUBLIC_FILE, jsonBytes({ ...metadata, version: `v${version}` }), true);
  for (const relative of MODULE_PATHS) add(relative, moduleBytes(version, date), true);
  // Write the authority last; an interrupted update will fail the next check.
  add('version.txt', Buffer.from(`v${version}\n`));
  return {
    current, version, date, rows,
    changes: rows.filter(row => row.before === null || !row.before.equals(row.after)),
  };
}

function check(root = REPO_ROOT) {
  const expected = plan(root);
  return { ok: expected.changes.length === 0, version: expected.version, drift: expected.changes.map(row => row.path) };
}

function atomicWrite(root, relative, bytes) {
  const target = location(root, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const temporary = `${target}.release-${process.pid}-${crypto.randomUUID()}.tmp`;
  const descriptor = fs.openSync(temporary, 'wx');
  try { fs.writeFileSync(descriptor, bytes); fs.fsyncSync(descriptor); }
  finally { fs.closeSync(descriptor); }
  try { fs.renameSync(temporary, target); }
  catch (error) { fs.unlinkSync(temporary); throw error; }
}

function update(root = REPO_ROOT, options = {}) {
  const label = options.label || (options.bump || options.version ? 'release' : 'sync');
  if (!/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$/.test(label)) throw new Error('Checkpoint label must contain only letters, digits, hyphens, and underscores.');
  const proposed = plan(root, options);
  if (!proposed.changes.length) return { version: proposed.version, changed: [], checkpoint: null };
  const parentRelative = 'backups/release_versioning';
  const parent = location(root, parentRelative);
  fs.mkdirSync(parent, { recursive: true });
  const lockPath = path.join(parent, '.release.lock');
  const lock = fs.openSync(lockPath, 'wx');
  let checkpoint;
  const written = [];
  try {
    fs.writeFileSync(lock, JSON.stringify({ pid: process.pid, created_utc: new Date().toISOString() }));
    for (const row of proposed.rows) {
      const actual = read(root, row.path, true);
      if ((actual === null) !== (row.before === null) || (actual && !actual.equals(row.before))) {
        throw new Error(`Concurrent change detected in ${row.path}; rerun after reviewing it.`);
      }
    }
    const stamp = new Date().toISOString().replace(/[-:]/g, '').replace('.', '');
    const relative = `${parentRelative}/${stamp}_${label}_${crypto.randomUUID().slice(0, 8)}`;
    checkpoint = location(root, relative);
    fs.mkdirSync(checkpoint);
    const manifest = {
      created_utc: new Date().toISOString(),
      label,
      scope: 'release metadata only; no documents, secrets, or installed binaries',
      from_version: proposed.current,
      to_version: proposed.version,
      files: proposed.changes.map(row => ({
        path: row.path,
        existed_before: row.before !== null,
        before_sha256: row.before === null ? null : sha256(row.before),
        after_sha256: sha256(row.after),
      })),
    };
    for (const row of proposed.changes) {
      if (row.before === null) continue;
      const backup = path.join(checkpoint, 'before', row.path);
      fs.mkdirSync(path.dirname(backup), { recursive: true });
      fs.writeFileSync(backup, row.before, { flag: 'wx' });
      if (sha256(fs.readFileSync(backup)) !== sha256(row.before)) throw new Error(`Backup verification failed: ${row.path}`);
    }
    fs.writeFileSync(path.join(checkpoint, 'manifest.json'), jsonBytes(manifest), { flag: 'wx' });
    for (const row of proposed.changes) {
      const actual = read(root, row.path, true);
      if ((actual === null) !== (row.before === null) || (actual && !actual.equals(row.before))) {
        throw new Error(`Concurrent change detected in ${row.path}; original copies are in ${checkpoint}`);
      }
      atomicWrite(root, row.path, row.after);
      written.push(row.path);
    }
    const verification = check(root);
    if (!verification.ok) throw new Error(`Post-write version drift: ${verification.drift.join(', ')}`);
    fs.writeFileSync(path.join(checkpoint, 'verified.json'), jsonBytes({ verified_utc: new Date().toISOString(), ...verification }), { flag: 'wx' });
    return { version: proposed.version, changed: written, checkpoint };
  } catch (error) {
    // Do not replace a concurrently edited file or delete new metadata during recovery.
    // The checkpoint contains exact originals and the completed-file list for review.
    if (checkpoint) fs.writeFileSync(path.join(checkpoint, 'incomplete.json'), jsonBytes({ written, error: error.message }), { flag: 'wx' });
    throw error;
  } finally {
    fs.closeSync(lock);
    fs.unlinkSync(lockPath);
  }
}

function main(args) {
  const command = args.shift() || 'check';
  const options = {};
  while (args.length) {
    const option = args.shift();
    if (option === '--patch') options.bump = 'patch';
    else if (['--version', '--date', '--label'].includes(option)) {
      const value = args.shift();
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${option}`);
      options[option.slice(2)] = value;
    } else throw new Error(`Unknown option: ${option}`);
  }
  if (!['check', 'sync', 'bump'].includes(command)) throw new Error('Use check, sync, or bump.');
  if (command === 'check' && Object.keys(options).length) throw new Error('check is read-only and accepts no update options.');
  if (command === 'sync' && (options.bump || options.version)) throw new Error('Use bump to change the authoritative version.');
  if (command === 'bump' && !options.bump && !options.version) options.bump = 'patch';
  const result = command === 'check' ? check() : update(REPO_ROOT, options);
  console.log(JSON.stringify(result, null, 2));
  if (result.ok === false) process.exitCode = 1;
}

module.exports = { PACKAGE_PATHS, LOCK_PATHS, MODULE_PATHS, normalizeVersion, plan, check, update };
if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(`Release version check failed: ${error.message}`); process.exitCode = 1; }
}
