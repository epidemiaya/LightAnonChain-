import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['/favicon.ico', '/robots.txt', '/apple-touch-icon.png'],
      manifest: {
        name: 'LAC Mobile',
        short_name: 'LAC',
        description: 'Light Anonymous Chain — mobile testnet console',
        theme_color: '#111827',
        background_color: '#0b1020',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
    }),
  ],
  // ✅ FIX: avoid subpath specifiers that are not exported by @noble/hashes@2.0.1
  optimizeDeps: {
    include: [
      '@noble/hashes',
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
});