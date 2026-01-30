import adapter from '@sveltejs/adapter-vercel';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),

	kit: {
		adapter: adapter({
			// Use serverless with reduced memory for faster cold starts
			memory: 128,
			maxDuration: 10
		}),
		alias: {
			$lib: './src/lib'
		}
	}
};

export default config;
