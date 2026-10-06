import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    proxy: {
      // dev server forwards API calls to the FastAPI backend
      '/api': 'http://localhost:8000',
    },
  },
})
