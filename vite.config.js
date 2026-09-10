import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'url'

// `__dirname` non esiste in un modulo ESM: con "type": "module" nel
// package.json questo file è ESM, quindi la root si ricava da import.meta.url.
const resolveFromRoot = (p) => fileURLToPath(new URL(p, import.meta.url))

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        main: resolveFromRoot('index.html'),
        admin: resolveFromRoot('admin.html'),
      },
    },
  },
})
