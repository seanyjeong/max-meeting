import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		port: 5173,
		allowedHosts: ['meeting.etlab.kr', 'code.etlab.kr', 'localhost'],
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true
			}
		}
	},
	// jspdf SSR 호환성 문제 해결
	ssr: {
		noExternal: ['jspdf']
	}
});
