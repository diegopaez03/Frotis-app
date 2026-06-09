import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * vite.config.ts — Frotis AI
 * Configuración del bundler para desarrollo y producción.
 */
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // Proxy para evitar CORS en desarrollo local
    proxy: {
      '/auth':     { target: 'http://localhost:8000', changeOrigin: true },
      '/users':    { target: 'http://localhost:8000', changeOrigin: true },
      '/predict':  { target: 'http://localhost:8000', changeOrigin: true },
      '/analyze':  { target: 'http://localhost:8000', changeOrigin: true },
      '/analysis': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },

  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        // Vite 8 usa Rolldown como bundler: manualChunks debe ser función, no objeto.
        manualChunks(id: string) {
          if (id.includes('react-dom') || id.includes('react/jsx'))  return 'vendor';
          if (id.includes('react-router'))                            return 'router';
          if (id.includes('axios'))                                   return 'http';
        },
      },
    },
  },
});
