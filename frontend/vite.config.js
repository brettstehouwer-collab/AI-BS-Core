import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/',
  plugins: [
    react({
      babel: {
        plugins: ['@babel/plugin-syntax-dynamic-import']
      }
    })
  ],
  server: {
    port: 5173,
    host: '0.0.0.0',
    strictPort: true,
    headers: {
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups'
    },
    proxy: {
      '/ws': {
        target: 'http://localhost:8010',
        ws: true,
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    },
    watch: {
      ignored: ['**/public/media/generated/**', '**/node_modules/**', '**/desktop-build/**', '**/dist/**']
    }
  },

  resolve: {
    dedupe: [
      'firebase',
      'firebase/app',
      'firebase/auth',
      'firebase/firestore',
      'firebase/performance',
      'firebase/ai'
    ]
  },
  optimizeDeps: {
    include: [
      'firebase/app',
      'firebase/auth',
      'firebase/firestore',
      'firebase/performance',
      'firebase/ai'
    ]
  },
  build: {
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      },
      format: {
        comments: false
      }
    },
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      input: {
        main: 'index.html',
        writer: 'writer.html'
      },
      output: {
        manualChunks(id) {
          // Heavy editors/terminals: lazy-loaded chunks
          if (id.includes('monaco-editor')) {
            return 'monaco';
          }
          if (id.includes('xterm')) {
            return 'xterm';
          }
          if (id.includes('react-markdown') || id.includes('react-syntax-highlighter')) {
            return 'markdown';
          }
          // Graph editor
          if (id.includes('@xyflow')) {
            return 'xyflow';
          }
          // Firebase SDKs
          if (id.includes('firebase')) {
            return 'firebase';
          }
          // Icons
          if (id.includes('lucide-react')) {
            return 'icons';
          }
          // Visualization & Charts
          if (id.includes('recharts') || id.includes('d3-')) {
            return 'recharts';
          }
          // Vendor utilities
          if (id.includes('node_modules')) {
            return 'vendor';
          }
        },
        // Optimize file paths
        entryFileNames: 'js/[name].[hash].js',
        chunkFileNames: 'js/[name].[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.');
          const ext = info[info.length - 1];
          if (/png|jpe?g|gif|svg/.test(ext)) {
            return `assets/img/[name].[hash][extname]`;
          } else if (/woff|woff2|eot|ttf|otf/.test(ext)) {
            return `assets/fonts/[name].[hash][extname]`;
          } else if (ext === 'css') {
            return `css/[name].[hash][extname]`;
          }
          return `assets/[name].[hash][extname]`;
        }
      }
    },
    cssCodeSplit: true,
    sourcemap: true,
    brotliSize: true
  }
});
