/// <reference lib="webworker" />
import { build, files, version } from '$service-worker';

declare const self: ServiceWorkerGlobalScope;

// Cache names
const CACHE_NAME = `max-meeting-cache-${version}`;
const STATIC_CACHE = `static-${version}`;
const API_CACHE = 'api-cache';

// Files to cache on install
const STATIC_ASSETS = [...build, ...files];

// API routes to cache with NetworkFirst strategy
const CACHEABLE_API_ROUTES = [
	'/api/v1/meetings',
	'/api/v1/contacts',
	'/api/v1/meeting-types',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
	event.waitUntil(
		caches.open(STATIC_CACHE).then((cache) => {
			return cache.addAll(STATIC_ASSETS);
		})
	);
	// Activate immediately
	self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
	event.waitUntil(
		caches.keys().then((keys) => {
			return Promise.all(
				keys
					.filter((key) => key !== STATIC_CACHE && key !== API_CACHE && key !== CACHE_NAME)
					.map((key) => caches.delete(key))
			);
		})
	);
	// Claim all clients immediately
	self.clients.claim();
});

// Fetch event - handle caching strategies
self.addEventListener('fetch', (event) => {
	const { request } = event;
	const url = new URL(request.url);

	// Skip non-GET requests
	if (request.method !== 'GET') {
		return;
	}

	// Handle static assets with CacheFirst
	if (STATIC_ASSETS.includes(url.pathname)) {
		event.respondWith(cacheFirst(request));
		return;
	}

	// Handle API routes with NetworkFirst
	if (url.pathname.startsWith('/api/v1/') && shouldCacheApiRoute(url.pathname)) {
		event.respondWith(networkFirst(request));
		return;
	}

	// Handle navigation requests with NetworkFirst (for SPA)
	if (request.mode === 'navigate') {
		event.respondWith(networkFirst(request));
		return;
	}

	// Default: network only
	event.respondWith(fetch(request));
});

// Check if API route should be cached
function shouldCacheApiRoute(pathname: string): boolean {
	return CACHEABLE_API_ROUTES.some((route) => pathname.startsWith(route));
}

// CacheFirst strategy - for static assets
async function cacheFirst(request: Request): Promise<Response> {
	const cache = await caches.open(STATIC_CACHE);
	const cached = await cache.match(request);
	if (cached) {
		return cached;
	}
	const response = await fetch(request);
	if (response.ok) {
		cache.put(request, response.clone());
	}
	return response;
}

// NetworkFirst strategy - for API and navigation
async function networkFirst(request: Request): Promise<Response> {
	const cache = await caches.open(API_CACHE);

	try {
		const response = await fetch(request);
		if (response.ok) {
			// Cache successful responses
			cache.put(request, response.clone());
		}
		return response;
	} catch (error) {
		// Network failed, try cache
		const cached = await cache.match(request);
		if (cached) {
			return cached;
		}
		// Return offline page or error
		return new Response(
			JSON.stringify({
				error: 'offline',
				message: 'You are offline and this content is not cached.',
			}),
			{
				status: 503,
				headers: { 'Content-Type': 'application/json' },
			}
		);
	}
}

// Background sync for offline mutations
self.addEventListener('sync', (event) => {
	if (event.tag === 'sync-offline-data') {
		event.waitUntil(syncOfflineData());
	}
});

// Sync offline data when back online
async function syncOfflineData(): Promise<void> {
	// This would sync data stored in IndexedDB when online
	// Implementation depends on the offline store structure
	console.log('[SW] Syncing offline data...');

	// Notify all clients that sync is happening
	const clients = await self.clients.matchAll();
	clients.forEach((client) => {
		client.postMessage({
			type: 'SYNC_STARTED',
		});
	});
}

// Handle messages from main thread
self.addEventListener('message', (event) => {
	if (event.data?.type === 'SKIP_WAITING') {
		self.skipWaiting();
	}

	if (event.data?.type === 'CACHE_URLS') {
		const urls = event.data.urls as string[];
		caches.open(API_CACHE).then((cache) => {
			urls.forEach((url) => {
				fetch(url)
					.then((response) => {
						if (response.ok) {
							cache.put(url, response);
						}
					})
					.catch(() => {
						// Ignore cache errors
					});
			});
		});
	}
});

// Push notification handling (for future use)
self.addEventListener('push', (event) => {
	const data = event.data?.json() ?? {};
	const title = data.title ?? 'MAX Meeting';
	const options: NotificationOptions = {
		body: data.body ?? '',
		icon: '/favicon.png',
		badge: '/favicon.png',
		tag: data.tag ?? 'default',
		data: data.url ?? '/',
	};

	event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
	event.notification.close();

	const url = event.notification.data ?? '/';

	event.waitUntil(
		self.clients.matchAll({ type: 'window' }).then((clients) => {
			// Focus existing window if available
			for (const client of clients) {
				if (client.url === url && 'focus' in client) {
					return client.focus();
				}
			}
			// Open new window
			if (self.clients.openWindow) {
				return self.clients.openWindow(url);
			}
		})
	);
});
