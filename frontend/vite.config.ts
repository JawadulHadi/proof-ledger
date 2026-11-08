import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// The build lands inside Django's static tree so `manage.py collectstatic` ships it
// unchanged. Fixed file names keep templates/core/app.html free of a manifest lookup.
export default defineConfig({
  plugins: [react()],
  base: '/static/app/',
  build: {
    outDir: '../core/static/app',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: 'app.js',
        chunkFileNames: 'chunk-[name].js',
        assetFileNames: (asset) => (asset.name?.endsWith('.css') ? 'app.css' : 'assets/[name][extname]'),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/admin': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
});
