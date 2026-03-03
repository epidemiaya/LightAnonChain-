import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/lac-beta\.uk\/api\/(profile|inbox|groups)/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 },
              networkTimeoutSeconds: 3,
            },
          },
          {
            urlPattern: /^https:\/\/lac-beta\.uk\/api\/media\//,
            handler: 'CacheFirst',
            options: {
              cacheName: 'media-cache',
              expiration: { maxEntries: 200, maxAgeSeconds: 300 },
            },
          },
        ],
      },
      manifest: {
        name: 'LAC — LightAnonChain',
        short_name: 'LAC',
        description: 'Privacy-first blockchain messenger',
        start_url: '/',
        display: 'standalone',
        background_color: '#060f0c',
        theme_color: '#10b981',
        orientation: 'portrait',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  optimizeDeps: {
    include: [
      '@noble/hashes/sha256',
      '@noble/hashes/ripemd160',
      '@scure/base',
      '@noble/secp256k1',
    ],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['lucide-react', 'react-hot-toast'],
          crypto: ['@noble/secp256k1', '@noble/hashes', '@scure/base', '@scure/bip32', '@scure/bip39'],
        },
      },
    },
    minify: 'esbuild',
    target: 'es2020',
    chunkSizeWarningLimit: 800,
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:38400',
        changeOrigin: true,
      },
    },
  },
})
