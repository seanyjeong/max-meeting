import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

describe('auth store', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		localStorage.clear();
	});

	it('should initialize with logged out state', async () => {
		const { auth } = await import('./auth');
		const state = get(auth);

		expect(state.isAuthenticated).toBe(false);
		expect(state.accessToken).toBeNull();
	});
});
