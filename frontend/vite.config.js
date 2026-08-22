import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Client build: produce a hydration bundle with stable asset names so the
// Python server can reference them without knowing the hashed filenames.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: 'src/entry-client.jsx',
      output: {
        entryFileNames: 'assets/client.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/[name][extname]',
      },
    },
  },
});