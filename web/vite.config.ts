import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/localhost:8000\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              }
            }
          }
        ]
      },
      manifest: {
        name: 'RAG Chatbot',
        short_name: 'RAG',
        description: 'Retrieval-Augmented Generation Chatbot',
        theme_color: '#000000',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'icons/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      }
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Proxy all API requests to the backend
      '/healthz': 'http://localhost:8000',
      '/readyz': 'http://localhost:8000',
      '/query': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/multimodal': 'http://localhost:8000',
      '/intelligence': 'http://localhost:8000',
      '/summaries': 'http://localhost:8000',
      '/knowledge': 'http://localhost:8000',
      '/analytics': 'http://localhost:8000',
      '/performance': 'http://localhost:8000',
      '/ultra': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/api': 'http://localhost:8000'
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
}) 