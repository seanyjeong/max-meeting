/**
 * SvelteKit Server Hooks - API Proxy for Production
 *
 * 개발 환경에서는 vite.config.ts의 proxy가 처리하고,
 * 프로덕션 환경에서는 이 hooks가 /api 요청을 백엔드로 프록시함.
 */
import type { Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const BACKEND_URL = env.BACKEND_URL || 'http://localhost:8000';

export const handle: Handle = async ({ event, resolve }) => {
	// /api 경로로 들어오는 요청을 백엔드로 프록시
	if (event.url.pathname.startsWith('/api')) {
		const targetUrl = `${BACKEND_URL}${event.url.pathname}${event.url.search}`;

		try {
			// 원본 요청의 헤더 복사
			const headers = new Headers();
			for (const [key, value] of event.request.headers.entries()) {
				// host는 제외 (백엔드 호스트로 변경됨)
				if (key.toLowerCase() !== 'host') {
					headers.set(key, value);
				}
			}

			const response = await fetch(targetUrl, {
				method: event.request.method,
				headers,
				body: event.request.method !== 'GET' && event.request.method !== 'HEAD'
					? await event.request.arrayBuffer()
					: undefined,
				// @ts-expect-error - Node.js fetch supports duplex
				duplex: 'half'
			});

			// 응답 헤더 복사
			const responseHeaders = new Headers();
			for (const [key, value] of response.headers.entries()) {
				// transfer-encoding 등 hop-by-hop 헤더 제외
				if (!['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) {
					responseHeaders.set(key, value);
				}
			}

			return new Response(response.body, {
				status: response.status,
				statusText: response.statusText,
				headers: responseHeaders
			});
		} catch (error) {
			console.error('[Proxy] Error proxying request:', error);
			return new Response(JSON.stringify({
				error: {
					code: 'PROXY_ERROR',
					message: 'Backend server is unavailable'
				}
			}), {
				status: 502,
				headers: { 'Content-Type': 'application/json' }
			});
		}
	}

	return resolve(event);
};
