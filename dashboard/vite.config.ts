import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    'process.env': {},
    global: 'globalThis',
  },
  resolve: {
    alias: {
      buffer: 'buffer/',
      '@landing': path.resolve(__dirname, '../landing/src'),
    },
  },
  optimizeDeps: {
    include: ['buffer'],
  },
  // Allow Vite to serve files from the sibling landing/ directory
  server: {
    fs: {
      allow: ['..'],
    },
  },
})
