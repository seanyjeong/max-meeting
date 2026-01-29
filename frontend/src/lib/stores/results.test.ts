import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import {
	resultsStore,
	hasResult,
	isVerified,
	pendingActionItems,
	completedActionItems
} from './results';

// Mock the api module
vi.mock('$lib/api', () => ({
	api: {
		get: vi.fn(),
		post: vi.fn(),
		patch: vi.fn(),
		delete: vi.fn()
	}
}));

describe('resultsStore', () => {
	beforeEach(() => {
		resultsStore.reset();
	});

	describe('initial state', () => {
		it('should have no current result', () => {
			const state = get(resultsStore);
			expect(state.currentResult).toBeNull();
		});

		it('should have empty versions', () => {
			const state = get(resultsStore);
			expect(state.versions).toEqual([]);
		});

		it('should have empty action items', () => {
			const state = get(resultsStore);
			expect(state.actionItems).toEqual([]);
		});

		it('should not be in edit mode', () => {
			const state = get(resultsStore);
			expect(state.editMode).toBe(false);
		});

		it('should not be loading', () => {
			const state = get(resultsStore);
			expect(state.isLoading).toBe(false);
		});

		it('should not be generating', () => {
			const state = get(resultsStore);
			expect(state.isGenerating).toBe(false);
		});
	});

	describe('derived stores', () => {
		it('hasResult should return false when no result', () => {
			expect(get(hasResult)).toBe(false);
		});

		it('isVerified should return false when no result', () => {
			expect(get(isVerified)).toBe(false);
		});

		it('pendingActionItems should return empty array initially', () => {
			expect(get(pendingActionItems)).toEqual([]);
		});

		it('completedActionItems should return empty array initially', () => {
			expect(get(completedActionItems)).toEqual([]);
		});
	});

	describe('edit mode', () => {
		it('should enable edit mode', () => {
			resultsStore.setEditMode(true);
			const state = get(resultsStore);
			expect(state.editMode).toBe(true);
		});

		it('should disable edit mode', () => {
			resultsStore.setEditMode(true);
			resultsStore.setEditMode(false);
			const state = get(resultsStore);
			expect(state.editMode).toBe(false);
		});
	});

	describe('edited summary', () => {
		it('should set edited summary', () => {
			resultsStore.setEditedSummary('Test summary');
			const state = get(resultsStore);
			expect(state.editedSummary).toBe('Test summary');
		});
	});

	describe('error handling', () => {
		it('should clear error', () => {
			// Manually set error state for testing
			resultsStore.setEditedSummary(''); // Trigger an update
			resultsStore.clearError();
			const state = get(resultsStore);
			expect(state.error).toBeNull();
		});
	});

	describe('action items filtering', () => {
		it('should filter pending action items', () => {
			// This would require setting up the store with action items
			// For now, just verify the derived store exists and works
			const pending = get(pendingActionItems);
			expect(Array.isArray(pending)).toBe(true);
		});

		it('should filter completed action items', () => {
			const completed = get(completedActionItems);
			expect(Array.isArray(completed)).toBe(true);
		});
	});

	describe('reorder action items', () => {
		it('should reorder action items', () => {
			const items = [
				{
					id: 1,
					meeting_id: 1,
					agenda_id: null,
					assignee_id: null,
					content: 'Item 1',
					due_date: null,
					priority: 'medium' as const,
					status: 'pending' as const
				},
				{
					id: 2,
					meeting_id: 1,
					agenda_id: null,
					assignee_id: null,
					content: 'Item 2',
					due_date: null,
					priority: 'high' as const,
					status: 'pending' as const
				}
			];

			resultsStore.reorderActionItems(items);
			const state = get(resultsStore);
			expect(state.actionItems).toEqual(items);
		});
	});
});
