import {mergeConfig} from 'vite';
import driverConfig from './vite.driver.config.mjs';
import {personalShellPlugin} from './vite.personal.config.mjs';

// Keep existing Studio/writer/chat/driver entries and add the personal page once.
export default mergeConfig(driverConfig, {
  build:{rollupOptions:{input:{personal:'personal/index.html'}}},
  plugins:[personalShellPlugin()],
});
