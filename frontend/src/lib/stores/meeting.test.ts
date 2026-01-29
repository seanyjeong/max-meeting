import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';

describe('meeting store', () => {
	beforeEach(async () => {
		// Reset module between tests
		const { resetMeetingStore } = await import('./meeting');
		resetMeetingStore();
	});

	it('should initialize with empty meetings list', async () => {
		const { meetings } = await import('./meeting');
		const state = get(meetings);

		expect(state).toEqual([]);
	});
});
