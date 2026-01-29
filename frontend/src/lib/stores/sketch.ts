/**
 * Sketch Store - Sketch/drawing state management
 */
import { writable, derived } from 'svelte/store';
import { api } from '$lib/api';

// Editor type from tldraw - will be available at runtime
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Editor = any;

export interface SketchData {
	id?: number;
	meeting_id: number;
	agenda_id: number | null;
	svg_file_path?: string;
	json_data: any;
	extracted_text?: string;
	thumbnail_path?: string;
	timestamp_seconds: number | null;
	created_at?: string;
	updated_at?: string;
}

export interface SketchState {
	currentTool: 'draw' | 'eraser' | 'select' | 'hand';
	currentColor: string;
	strokeWidth: number;
	sketches: SketchData[];
	activeSketch: SketchData | null;
	isDirty: boolean;
	lastSavedAt: Date | null;
	autoSaveEnabled: boolean;
	editor: Editor | null;
}

const COLORS = {
	black: '#1a1a1a',
	red: '#dc2626',
	blue: '#2563eb',
	green: '#16a34a',
	yellow: '#fbbf24',
	highlightYellow: 'rgba(251, 191, 36, 0.4)',
	highlightGreen: 'rgba(74, 222, 128, 0.4)',
	highlightPink: 'rgba(244, 114, 182, 0.4)'
};

const STROKE_WIDTHS = {
	thin: 1,
	medium: 2,
	thick: 4,
	extraThick: 8
};

const initialState: SketchState = {
	currentTool: 'draw',
	currentColor: COLORS.black,
	strokeWidth: STROKE_WIDTHS.medium,
	sketches: [],
	activeSketch: null,
	isDirty: false,
	lastSavedAt: null,
	autoSaveEnabled: true,
	editor: null
};

function createSketchStore() {
	const { subscribe, set, update } = writable<SketchState>(initialState);
	let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
	const AUTO_SAVE_INTERVAL = 30000; // 30 seconds

	function startAutoSave() {
		if (autoSaveTimer) {
			clearInterval(autoSaveTimer);
		}
		autoSaveTimer = setInterval(() => {
			update((state) => {
				if (state.isDirty && state.autoSaveEnabled && state.activeSketch) {
					saveSketch(state.activeSketch.meeting_id);
				}
				return state;
			});
		}, AUTO_SAVE_INTERVAL);
	}

	function stopAutoSave() {
		if (autoSaveTimer) {
			clearInterval(autoSaveTimer);
			autoSaveTimer = null;
		}
	}

	async function loadSketches(meetingId: number): Promise<void> {
		try {
			const response = await api.get<{ data: SketchData[] }>(
				`/meetings/${meetingId}/sketches`
			);
			update((state) => ({
				...state,
				sketches: response.data || []
			}));
		} catch (error) {
			console.error('Failed to load sketches:', error);
		}
	}

	async function saveSketch(meetingId: number): Promise<void> {
		update((state) => {
			if (!state.editor || !state.isDirty) return state;

			const snapshot = state.editor.store.getSnapshot();

			// Save to backend
			const sketchData: Partial<SketchData> = {
				meeting_id: meetingId,
				agenda_id: state.activeSketch?.agenda_id ?? null,
				json_data: snapshot,
				timestamp_seconds: state.activeSketch?.timestamp_seconds ?? null
			};

			if (state.activeSketch?.id) {
				// Update existing
				api.patch(`/sketches/${state.activeSketch.id}`, sketchData).catch(console.error);
			} else {
				// Create new
				api
					.post<{ data: SketchData }>(`/meetings/${meetingId}/sketches`, sketchData)
					.then((response) => {
						update((s) => ({
							...s,
							activeSketch: response.data,
							sketches: [...s.sketches, response.data]
						}));
					})
					.catch(console.error);
			}

			// Save to localStorage as backup
			try {
				localStorage.setItem(`sketch-${meetingId}`, JSON.stringify(snapshot));
				localStorage.setItem(`sketch-tool-${meetingId}`, state.currentTool);
				localStorage.setItem(`sketch-color-${meetingId}`, state.currentColor);
			} catch {
				console.warn('Failed to save to localStorage');
			}

			return {
				...state,
				isDirty: false,
				lastSavedAt: new Date()
			};
		});
	}

	function loadFromLocalStorage(meetingId: number): any | null {
		try {
			const stored = localStorage.getItem(`sketch-${meetingId}`);
			return stored ? JSON.parse(stored) : null;
		} catch {
			return null;
		}
	}

	function loadLastToolPreferences(meetingId: number) {
		try {
			const tool = localStorage.getItem(`sketch-tool-${meetingId}`) as SketchState['currentTool'];
			const color = localStorage.getItem(`sketch-color-${meetingId}`);
			if (tool || color) {
				update((state) => ({
					...state,
					currentTool: tool || state.currentTool,
					currentColor: color || state.currentColor
				}));
			}
		} catch {
			// Ignore
		}
	}

	return {
		subscribe,
		COLORS,
		STROKE_WIDTHS,

		setTool: (tool: SketchState['currentTool']) =>
			update((state) => ({ ...state, currentTool: tool })),

		setColor: (color: string) =>
			update((state) => ({ ...state, currentColor: color })),

		setStrokeWidth: (width: number) =>
			update((state) => ({ ...state, strokeWidth: width })),

		setEditor: (editor: Editor | null) =>
			update((state) => ({ ...state, editor })),

		markDirty: () =>
			update((state) => ({ ...state, isDirty: true })),

		setActiveSketch: (sketch: SketchData | null) =>
			update((state) => ({ ...state, activeSketch: sketch })),

		loadSketches,
		saveSketch,
		loadFromLocalStorage,
		loadLastToolPreferences,
		startAutoSave,
		stopAutoSave,

		setAutoSaveEnabled: (enabled: boolean) =>
			update((state) => ({ ...state, autoSaveEnabled: enabled })),

		reset: () => {
			stopAutoSave();
			set(initialState);
		}
	};
}

export const sketchStore = createSketchStore();

// Derived store for checking if editor is ready
export const isEditorReady = derived(
	sketchStore,
	($sketch) => $sketch.editor !== null
);
