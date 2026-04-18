import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Strip crossorigin attrs for file:// compatibility (pywebview)
function stripCrossorigin() {
  return {
    name: 'strip-crossorigin',
    transformIndexHtml(html) {
      return html.replace(/ crossorigin/g, '')
    },
  }
}

export default defineConfig({
  plugins: [vue(), stripCrossorigin()],
  base: './',
  build: {
    outDir: '../src/anime_game_afk/ui/web',
    emptyOutDir: true,
    modulePreload: false,
    rollupOptions: {
      output: {
        entryFileNames: 'app.js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name][extname]',
      },
    },
  },
})
