import { mergeConfig } from 'vite';
import studioConfig from './vite.config.js';

// Preserve the qualified Studio configuration and add the dedicated chat page.
export default mergeConfig(studioConfig, {
  build: { rollupOptions: { input: { chat: 'bs-chat.html' } } },
});
