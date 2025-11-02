import { defineConfig, Plugin } from 'vite'
import react from '@vitejs/plugin-react'

function injectReactDevTools(): Plugin {
  return {
    name: 'inject-react-devtools',
    transformIndexHtml(html) {
      if (process.env.NODE_ENV !== 'development' || process.env.DEVTOOLS_ENABLED === 'false') return html
      const tag = '<script src="http://localhost:8097"></script>'
      // injecte juste avant la fermeture de </head>
      return html.replace('</head>', `${tag}\n</head>`)
    }
  }
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react(), injectReactDevTools()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  define: {
    global: 'globalThis',
    __DEV__: mode === 'development',
    __DEVTOOLS_ENABLED__: mode === 'development'
  },
  server: {
    port: 5173,
    open: false, // Don't automatically open browser
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: 'http://127.0.0.1:8050',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    // Ensure devtools are not included in production builds
    rollupOptions: {
      onwarn(warning, warn) {
        if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && warning.message.includes('react-refresh')) {
          return;
        }
        warn(warning);
      }
    }
  },
}))