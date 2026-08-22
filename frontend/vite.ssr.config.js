import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Server bundle: build the SSR entry for Node (react-dom/server renderToString).
export default defineConfig({
  plugins: [react()],
  build: {
    ssr: true,
    outDir: 'dist-ssr',
    rollupOptions: {
      input: 'src/ssr-entry.jsx',
      output: {
        entryFileNames: 'ssr-entry.mjs',
        format: 'es',
      },
    },
  },
});