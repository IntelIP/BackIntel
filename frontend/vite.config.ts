import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiOrigin = process.env.BACKINTEL_WORKSPACE_API_ORIGIN ?? 'http://127.0.0.1:2041'
const apiUrl = new URL(apiOrigin)
if (apiUrl.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(apiUrl.hostname) || apiUrl.username || apiUrl.password || apiUrl.search || apiUrl.hash || apiUrl.pathname !== '/') throw new Error('The workspace API must use a loopback HTTP origin')

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': apiOrigin } },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts', restoreMocks: true },
})
