import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { sketchStore, isEditorReady } from './sketch';

// Mock the api module
vi.mock('$lib/api', () => ({
	api: {
		get: vi.fn(),
		post: vi.fn(),
		patch: vi.fn()
	}
}));

describe('sketchStore', () => {
	beforeEach(() => {
		sketchStore.reset();
	});

	describe('initial state', () => {
		it('should have default tool as draw', () => {
			const state = get(sketchStore);
			expect(state.currentTool).toBe('draw');
		});

		it('should have default color as black', () => {
			const state = get(sketchStore);
			expect(state.currentColor).toBe(sketchStore.COLORS.black);
		});

		it('should have no active sketch', () => {
			const state = get(sketchStore);
			expect(state.activeSketch).toBeNull();
		});

		it('should have autoSave enabled by default', () => {
			const state = get(sketchStore);
			expect(state.autoSaveEnabled).toBe(true);
		});
	});

	describe('tool selection', () => {
		it('should set current tool', () => {
			sketchStore.setTool('eraser');
			const state = get(sketchStore);
			expect(state.currentTool).toBe('eraser');
		});
	});

	describe('color selection', () => {
		it('should set current color', () => {
			sketchStore.setColor(sketchStore.COLORS.red);
			const state = get(sketchStore);
			expect(state.currentColor).toBe(sketchStore.COLORS.red);
		});
	});

	describe('stroke width', () => {
		it('should set stroke width', () => {
			sketchStore.setStrokeWidth(4);
			const state = get(sketchStore);
			expect(state.strokeWidth).toBe(4);
		});
	});

	describe('dirty state', () => {
		it('should mark as dirty', () => {
			sketchStore.markDirty();
			const state = get(sketchStore);
			expect(state.isDirty).toBe(true);
		});
	});

	describe('editor ready', () => {
		it('should indicate editor not ready initially', () => {
			expect(get(isEditorReady)).toBe(false);
		});

		it('should indicate editor ready when set', () => {
			const mockEditor = {} as any;
			sketchStore.setEditor(mockEditor);
			expect(get(isEditorReady)).toBe(true);
		});
	});

	describe('auto save toggle', () => {
		it('should toggle auto save', () => {
			sketchStore.setAutoSaveEnabled(false);
			const state = get(sketchStore);
			expect(state.autoSaveEnabled).toBe(false);
		});
	});

	describe('COLORS constant', () => {
		it('should have expected colors', () => {
			expect(sketchStore.COLORS.black).toBeDefined();
			expect(sketchStore.COLORS.red).toBeDefined();
			expect(sketchStore.COLORS.blue).toBeDefined();
			expect(sketchStore.COLORS.green).toBeDefined();
			expect(sketchStore.COLORS.highlightYellow).toBeDefined();
		});
	});

	describe('STROKE_WIDTHS constant', () => {
		it('should have expected stroke widths', () => {
			expect(sketchStore.STROKE_WIDTHS.thin).toBe(1);
			expect(sketchStore.STROKE_WIDTHS.medium).toBe(2);
			expect(sketchStore.STROKE_WIDTHS.thick).toBe(4);
			expect(sketchStore.STROKE_WIDTHS.extraThick).toBe(8);
		});
	});
});
