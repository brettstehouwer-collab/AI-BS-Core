import { mergeConfig } from 'vite';
import studioConfig from './vite.config.js';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
export function personalShellPlugin(){
  return {name:'personal-public-shell',enforce:'post',generateBundle(_options,bundle){
    const selected=new Set();
    const visit=name=>{if(selected.has(name))return;const item=bundle[name];if(!item)throw Error('Missing personal asset '+name);selected.add(name);if(item.type==='chunk')for(const dependency of [...item.imports,...item.dynamicImports,...(item.viteMetadata?.importedCss||[])])visit(dependency);else if(name.endsWith('.html'))for(const match of String(item.source).matchAll(/(?:src|href)=["']([^"'#?]+)["']/g)){const dependency=match[1].replace(/^\//,'');if(bundle[dependency])visit(dependency);}};
    visit('personal/index.html');
    const assets=[...selected].sort().map(name=>{const item=bundle[name],data=Buffer.from(item.type==='chunk'?item.code:item.source);return{url:'/'+name,bytes:data.length,sha256:createHash('sha256').update(data).digest('hex')};});
    const version=createHash('sha256').update(JSON.stringify(assets)).digest('hex');
    this.emitFile({type:'asset',fileName:'personal/asset-manifest.json',source:JSON.stringify({version,entry:'/personal/index.html',assets})});
    this.emitFile({type:'asset',fileName:'personal/sw.js',source:readFileSync(new URL('./public/personal/sw.js',import.meta.url),'utf8').replace('__PERSONAL_BUILD__',version)});
  }};
}
// A dedicated build profile; existing Studio, chat and driver profiles stay intact.
const config = mergeConfig(studioConfig, { publicDir: false, plugins: [personalShellPlugin()],
  build: { rollupOptions: { input: { personal: 'personal/index.html' } } } });
config.build.rollupOptions.input = { personal: 'personal/index.html' };
export default config;
