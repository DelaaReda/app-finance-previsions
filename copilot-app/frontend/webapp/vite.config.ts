import { defineConfig, Plugin } from 'vite'
import react from '@vitejs/plugin-react'

function injectReactDevTools(devtoolsEnabled: boolean): Plugin {
  return {
    name: 'inject-react-devtools',
    transformIndexHtml(html) {
      if (!devtoolsEnabled) return html
      const tag = '<script src="http://localhost:8097"></script>'
      return html.replace('</head>', `${tag}\n</head>`)
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const devtoolsEnabled =
    mode === 'development' &&
    ['1', 'true', 'yes'].includes((process.env.VITE_ENABLE_REACT_DEVTOOLS ?? '').toLowerCase())

  return {
    plugins: [react(), injectReactDevTools(devtoolsEnabled)],
    resolve: {
      alias: {
        '@': '/src',
      },
    },
    define: {
      global: 'globalThis',
      __DEV__: mode === 'development',
      __DEVTOOLS_ENABLED__: devtoolsEnabled,
    },
    server: {
      port: 5173,
      open: false,
      proxy: {
        '/api': {
          target: process.env.VITE_PROXY_TARGET || 'http://localhost:8050',
          changeOrigin: true,
          secure: false,
        },
        '/health': {
          target: process.env.VITE_PROXY_TARGET || 'http://localhost:8050',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        onwarn(warning, warn) {
          if (warning.code === 'MODULE_LEVEL_DIRECTIVE' && warning.message.includes('react-refresh')) {
            return
          }
          warn(warning)
        },
      },
    },
  }
})
