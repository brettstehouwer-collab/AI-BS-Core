import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { mergeConfig } from 'vite';
import chatConfig from './vite.bs-chat.config.mjs';

const digest = value => createHash('sha256').update(value).digest('hex');

export function driverShellPlugin() {
  return {
    name: 'fe-driver-public-shell', enforce: 'post',
    generateBundle(_options, bundle) {
      const selected = new Set();
      const visit = name => {
        if (selected.has(name)) return;
        const item = bundle[name];
        if (!item) throw new Error(`Missing driver shell dependency: ${name}`);
        selected.add(name);
        if (item.type === 'chunk') {
          for (const dependency of [...item.imports, ...item.dynamicImports,
            ...(item.viteMetadata?.importedCss || []), ...(item.viteMetadata?.importedAssets || [])]) visit(dependency);
        } else if (name.endsWith('.html')) {
          for (const match of String(item.source).matchAll(/(?:src|href)=["']([^"'#?]+)["']/g)) {
            const dependency = match[1].replace(/^\//, '');
            if (bundle[dependency]) visit(dependency);
          }
        }
      };
      visit('driver/index.html');
      const assets = [...selected].sort().map(name => {
        const item = bundle[name];
        return { url: '/' + name, sha256: digest(item.type === 'chunk' ? item.code : item.source) };
      });
      for (const name of ['driver/manifest.webmanifest', 'favicon.ico']) {
        const source = readFileSync(new URL('./public/' + name, import.meta.url));
        assets.push({ url: '/' + name, sha256: digest(source) });
      }
      const version = digest(JSON.stringify(assets));
      this.emitFile({ type: 'asset', fileName: 'driver/asset-manifest.json',
        source: JSON.stringify({ version, entry: '/driver/index.html', assets }) });
      const worker = readFileSync(new URL('./public/driver/sw.js', import.meta.url), 'utf8');
      this.emitFile({ type: 'asset', fileName: 'driver/sw.js', source: worker.replace('__DRIVER_BUILD__', version) });
    },
  };
}

export default mergeConfig(chatConfig, {
  build: { rollupOptions: { input: { driver: 'driver/index.html' } } },
  plugins: [driverShellPlugin()],
});
