import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy só em desenvolvimento — em produção o nginx faz o proxy
    proxy: {
      '/modelo': 'http://localhost:8000',
    },
  },
})
