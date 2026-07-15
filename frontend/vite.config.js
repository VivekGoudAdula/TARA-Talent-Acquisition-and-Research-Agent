import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    hmr: {
      host: 'localhost',
      port: 5173,
    },
    proxy: {
      // Proxy all /api calls to FastAPI backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes, req) => {
            if (req.url?.includes('/conversations/stream')) {
              proxyRes.headers['content-type'] = 'text/event-stream';
              proxyRes.headers['cache-control'] = 'no-cache';
            }
          });
        },
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
