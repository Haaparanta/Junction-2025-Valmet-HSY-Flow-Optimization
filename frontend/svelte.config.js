import adapter from '@sveltejs/adapter-node'
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

/** @type {import('@sveltejs/kit').Config} */
const config = {
  // Consult https://svelte.dev/docs/kit/integrations
  // for more information about preprocessors
  preprocess: vitePreprocess(),

  kit: {
    // adapter-node for production Node.js server deployment
    // See https://svelte.dev/docs/kit/adapter-node for more information
    adapter: adapter({
      out: 'build',
      precompress: true,
      envPrefix: ''
    })
  }
}

export default config
