import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * vite.config.ts — Frotis AI
 * Configuración del bundler para desarrollo y producción.
 */
export default defineConfig({
  plugins: [react()],
  envDir: '../',

  server: {
    port: 5173,
    // Proxy para evitar CORS en desarrollo local
    proxy: {
      '/auth':    { target: 'http://localhost:8000', changeOrigin: true },
      '/users':   { target: 'http://localhost:8000', changeOrigin: true },
      '/predict': { target: 'http://localhost:8000', changeOrigin: true },
      '/analyze': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          http:   ['axios'],
        },
      },
    },
  },
});
