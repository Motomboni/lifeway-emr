import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'build',
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
      },
      '/ohif': {
        target: 'http://127.0.0.1:8042',
        changeOrigin: true,
        secure: false,
        headers: {
          Authorization: 'Basic b3J0aGFuYzpvcnRoYW5j',
        },
      },
      '/orthanc': {
        target: 'http://127.0.0.1:8042',
        changeOrigin: true,
        secure: false,
        headers: {
          Authorization: 'Basic b3J0aGFuYzpvcnRoYW5j',
        },
        rewrite: (path) => path.replace(/^\/orthanc/, ''),
      },
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
