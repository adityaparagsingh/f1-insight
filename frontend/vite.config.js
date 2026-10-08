import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// F1 INSIGHT frontend dev server. The backend API base is configured through
// VITE_API_BASE_URL (see .env / .env.example); a dev proxy is provided so the
// SPA can also be served same-origin if preferred.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
