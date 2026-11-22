import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true
  },
  build: {
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('lucide-react')) return 'vendor-lucide';
            if (id.includes('tone')) return 'vendor-tone';
            if (id.includes('flexlayout-react')) return 'vendor-flexlayout';
            if (id.includes('firebase')) return 'vendor-firebase';
            if (id.includes('react-resizable-panels')) return 'vendor-resizable';
            return 'vendor-core';
          }
        }
      }
    }
  }
})
