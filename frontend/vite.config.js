import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vercel migration: the browser app is a normal static Vite SPA. Python owns
// only /api/* through api/index.py; there is no runtime Node SSR worker.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
