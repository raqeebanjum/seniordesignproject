import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: '.',
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/upload': 'http://localhost:5001',
      '/get-ai-audio': 'http://localhost:5001'
    }
  }
})