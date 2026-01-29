/**
 * Results Store - Meeting results state management
 */
import { writable, derived } from 'svelte/store';
import { api } from '$lib/api';

export interface TranscriptSegment {
	id: number;
	start: number;
	end: number;
	text: string;
	speaker_label: string | null;
	speaker_name?: string;
	confidence?: number;
}

export interface ActionItem {
	id?: number;
	meeting_id: number;
	agenda_id: number | null;
	assignee_id: number | null;
	assignee_name?: string;
	content: string;
	due_date: string | null;
	priority: 'high' | 'medium' | 'low';
	status: 'pending' | 'in_progress' | 'completed';
	completed_at?: string;
	created_at?: string;
}

export interface MeetingResult {
	id: number;
	meeting_id: number;
	summary: string;
	is_verified: boolean;
	verified_at: string | null;
	version: number;
	created_at: string;
	updated_at: string;
}

export interface ResultVersion {
	version: number;
	created_at: string;
	summary_preview: string;
}

export interface ResultsState {
	currentResult: MeetingResult | null;
	versions: ResultVersion[];
	selectedVersion: number | null;
	actionItems: ActionItem[];
	transcriptSegments: TranscriptSegment[];
	editMode: boolean;
	editedSummary: string;
	isLoading: boolean;
	isGenerating: boolean;
	error: string | null;
}

const initialState: ResultsState = {
	currentResult: null,
	versions: [],
	selectedVersion: null,
	actionItems: [],
	transcriptSegments: [],
	editMode: false,
	editedSummary: '',
	isLoading: false,
	isGenerating: false,
	error: null
};

function createResultsStore() {
	const { subscribe, set, update } = writable<ResultsState>(initialState);

	async function loadResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true, error: null }));

		try {
			const [resultResponse, versionsResponse, actionItemsResponse] = await Promise.all([
				api.get<{ data: MeetingResult }>(`/meetings/${meetingId}/result`).catch(() => null),
				api.get<{ data: ResultVersion[] }>(`/meetings/${meetingId}/result/versions`).catch(() => ({ data: [] })),
				api.get<{ data: ActionItem[] }>(`/meetings/${meetingId}/action-items`).catch(() => ({ data: [] }))
			]);

			update((state) => ({
				...state,
				currentResult: resultResponse?.data ?? null,
				versions: versionsResponse.data || [],
				actionItems: actionItemsResponse.data || [],
				selectedVersion: resultResponse?.data?.version ?? null,
				editedSummary: resultResponse?.data?.summary ?? '',
				isLoading: false
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isLoading: false,
				error: 'Failed to load meeting result'
			}));
		}
	}

	async function loadTranscript(meetingId: number): Promise<void> {
		try {
			const response = await api.get<{ data: { segments: TranscriptSegment[] } }>(
				`/meetings/${meetingId}/transcript`
			);
			update((state) => ({
				...state,
				transcriptSegments: response.data?.segments || []
			}));
		} catch (error) {
			console.error('Failed to load transcript:', error);
		}
	}

	async function loadVersion(meetingId: number, version: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true }));

		try {
			const response = await api.get<{ data: MeetingResult }>(
				`/meetings/${meetingId}/result/versions/${version}`
			);
			update((state) => ({
				...state,
				currentResult: response.data,
				selectedVersion: version,
				editedSummary: response.data.summary,
				isLoading: false
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isLoading: false,
				error: 'Failed to load version'
			}));
		}
	}

	async function saveResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true }));

		try {
			let currentSummary = '';
			update((state) => {
				currentSummary = state.editedSummary;
				return state;
			});

			const response = await api.patch<{ data: MeetingResult }>(
				`/meetings/${meetingId}/result`,
				{ summary: currentSummary }
			);

			update((state) => ({
				...state,
				currentResult: response.data,
				editMode: false,
				isLoading: false,
				versions: [
					...state.versions,
					{
						version: response.data.version,
						created_at: response.data.created_at,
						summary_preview: response.data.summary.slice(0, 100)
					}
				]
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isLoading: false,
				error: 'Failed to save result'
			}));
		}
	}

	async function generateResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isGenerating: true, error: null }));

		try {
			const response = await api.post<{ data: MeetingResult }>(
				`/meetings/${meetingId}/generate-result`
			);

			update((state) => ({
				...state,
				currentResult: response.data,
				editedSummary: response.data.summary,
				isGenerating: false
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isGenerating: false,
				error: 'Failed to generate result'
			}));
		}
	}

	async function regenerateResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isGenerating: true, error: null }));

		try {
			const response = await api.post<{ data: MeetingResult }>(
				`/meetings/${meetingId}/regenerate-result`
			);

			update((state) => ({
				...state,
				currentResult: response.data,
				editedSummary: response.data.summary,
				isGenerating: false
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isGenerating: false,
				error: 'Failed to regenerate result'
			}));
		}
	}

	async function verifyResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true }));

		try {
			const response = await api.post<{ data: MeetingResult }>(
				`/meetings/${meetingId}/result/verify`
			);

			update((state) => ({
				...state,
				currentResult: response.data,
				isLoading: false
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isLoading: false,
				error: 'Failed to verify result'
			}));
		}
	}

	// Action Items CRUD
	async function createActionItem(meetingId: number, item: Partial<ActionItem>): Promise<void> {
		try {
			const response = await api.post<{ data: ActionItem }>(
				`/meetings/${meetingId}/action-items`,
				item
			);

			update((state) => ({
				...state,
				actionItems: [...state.actionItems, response.data]
			}));
		} catch (error) {
			update((state) => ({
				...state,
				error: 'Failed to create action item'
			}));
		}
	}

	async function updateActionItem(itemId: number, updates: Partial<ActionItem>): Promise<void> {
		try {
			const response = await api.patch<{ data: ActionItem }>(
				`/action-items/${itemId}`,
				updates
			);

			update((state) => ({
				...state,
				actionItems: state.actionItems.map((item) =>
					item.id === itemId ? response.data : item
				)
			}));
		} catch (error) {
			update((state) => ({
				...state,
				error: 'Failed to update action item'
			}));
		}
	}

	async function deleteActionItem(itemId: number): Promise<void> {
		try {
			await api.delete(`/action-items/${itemId}`);

			update((state) => ({
				...state,
				actionItems: state.actionItems.filter((item) => item.id !== itemId)
			}));
		} catch (error) {
			update((state) => ({
				...state,
				error: 'Failed to delete action item'
			}));
		}
	}

	function reorderActionItems(items: ActionItem[]): void {
		update((state) => ({
			...state,
			actionItems: items
		}));
	}

	return {
		subscribe,

		loadResult,
		loadTranscript,
		loadVersion,
		saveResult,
		generateResult,
		regenerateResult,
		verifyResult,

		createActionItem,
		updateActionItem,
		deleteActionItem,
		reorderActionItems,

		setEditMode: (enabled: boolean) =>
			update((state) => ({
				...state,
				editMode: enabled,
				editedSummary: enabled ? (state.currentResult?.summary ?? '') : state.editedSummary
			})),

		setEditedSummary: (summary: string) =>
			update((state) => ({ ...state, editedSummary: summary })),

		clearError: () =>
			update((state) => ({ ...state, error: null })),

		reset: () => set(initialState)
	};
}

export const resultsStore = createResultsStore();

// Derived stores
export const hasResult = derived(
	resultsStore,
	($results) => $results.currentResult !== null
);

export const isVerified = derived(
	resultsStore,
	($results) => $results.currentResult?.is_verified ?? false
);

export const pendingActionItems = derived(
	resultsStore,
	($results) => $results.actionItems.filter((item) => item.status === 'pending')
);

export const completedActionItems = derived(
	resultsStore,
	($results) => $results.actionItems.filter((item) => item.status === 'completed')
);
