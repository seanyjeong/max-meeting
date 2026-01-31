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

export interface AgendaDiscussion {
	id: number;
	agenda_id: number;
	agenda_title: string;
	agenda_order: string;  // 계층형 순서 (예: "1.2.1")
	summary: string;
	key_points: string[] | null;
}

export interface ResultsState {
	currentResult: MeetingResult | null;
	versions: ResultVersion[];
	selectedVersion: number | null;
	actionItems: ActionItem[];
	agendaDiscussions: AgendaDiscussion[];
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
	agendaDiscussions: [],
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
			const [resultsResponse, actionItemsResponse, discussionsResponse] = await Promise.all([
				api.get<{ data: MeetingResult[] }>(`/meetings/${meetingId}/results`).catch(() => ({ data: [] })),
				api.get<{ data: ActionItem[] }>(`/meetings/${meetingId}/action-items`).catch(() => ({ data: [] })),
				api.get<{ data: AgendaDiscussion[] }>(`/meetings/${meetingId}/discussions`).catch(() => ({ data: [] }))
			]);

			const results = resultsResponse.data || [];
			const latestResult = results.length > 0 ? results[results.length - 1] : null;
			const versions: ResultVersion[] = results.map((r) => ({
				version: r.version,
				created_at: r.created_at,
				summary_preview: r.summary?.slice(0, 100) || ''
			}));

			update((state) => ({
				...state,
				currentResult: latestResult,
				versions,
				actionItems: actionItemsResponse.data || [],
				agendaDiscussions: discussionsResponse.data || [],
				selectedVersion: latestResult?.version ?? null,
				editedSummary: latestResult?.summary ?? '',
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
		} catch (error: any) {
			// 404 is expected when no transcript exists - don't log as error
			if (error?.status !== 404 && error?.message !== 'Not Found') {
				console.error('Failed to load transcript:', error);
			}
			// Set empty segments - this is normal when no recording was made
			update((state) => ({
				...state,
				transcriptSegments: []
			}));
		}
	}

	async function loadVersion(meetingId: number, version: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true }));

		try {
			// Get all results and find the one with matching version
			const response = await api.get<{ data: MeetingResult[] }>(
				`/meetings/${meetingId}/results`
			);
			const results = response.data || [];
			const targetResult = results.find((r) => r.version === version);

			if (targetResult) {
				update((state) => ({
					...state,
					currentResult: targetResult,
					selectedVersion: version,
					editedSummary: targetResult.summary,
					isLoading: false
				}));
			} else {
				throw new Error('Version not found');
			}
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
			let resultId: number | null = null;
			update((state) => {
				currentSummary = state.editedSummary;
				resultId = state.currentResult?.id ?? null;
				return state;
			});

			if (!resultId) {
				throw new Error('No result to save');
			}

			const response = await api.patch<MeetingResult>(
				`/results/${resultId}`,
				{ summary: currentSummary }
			);

			update((state) => ({
				...state,
				currentResult: response,
				editMode: false,
				isLoading: false,
				versions: [
					...state.versions,
					{
						version: response.version,
						created_at: response.created_at,
						summary_preview: response.summary.slice(0, 100)
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
			// 1. First create an empty result record
			const createResponse = await api.post<MeetingResult>(
				`/meetings/${meetingId}/results`,
				{ summary: '' }
			);

			update((state) => ({
				...state,
				currentResult: createResponse
			}));

			// 2. Then trigger LLM generation via regenerate endpoint
			console.log('[results] Created result, triggering LLM generation...');
			await api.post(`/results/${createResponse.id}/regenerate`, {});

			// 3. Poll for completion (LLM runs in background via Celery)
			let attempts = 0;
			const maxAttempts = 60; // 3 minutes max (3s * 60)
			const pollInterval = 3000;

			const pollResult = async (): Promise<MeetingResult | null> => {
				while (attempts < maxAttempts) {
					attempts++;
					await new Promise(resolve => setTimeout(resolve, pollInterval));

					try {
						const response = await api.get<{ data: MeetingResult[] }>(
							`/meetings/${meetingId}/results`
						);
						const results = response.data || [];
						const latest = results[results.length - 1];

						// Check if summary is populated (LLM completed)
						if (latest && latest.summary && latest.summary.length > 0) {
							console.log('[results] LLM generation completed');
							return latest;
						}
						console.log(`[results] Waiting for LLM... (${attempts}/${maxAttempts})`);
					} catch (e) {
						console.error('[results] Poll error:', e);
					}
				}
				return null;
			};

			const finalResult = await pollResult();

			if (finalResult) {
				update((state) => ({
					...state,
					currentResult: finalResult,
					editedSummary: finalResult.summary || '',
					isGenerating: false
				}));
			} else {
				update((state) => ({
					...state,
					isGenerating: false,
					error: '회의록 생성 시간이 초과되었습니다. 잠시 후 새로고침해주세요.'
				}));
			}
		} catch (error) {
			console.error('[results] Generate error:', error);
			update((state) => ({
				...state,
				isGenerating: false,
				error: '회의록 생성에 실패했습니다.'
			}));
		}
	}

	async function regenerateResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isGenerating: true, error: null }));

		try {
			let resultId: number | null = null;
			update((state) => {
				resultId = state.currentResult?.id ?? null;
				return state;
			});

			if (!resultId) {
				throw new Error('재생성할 결과가 없습니다');
			}

			// LLM 재생성 트리거 (Celery 백그라운드 작업)
			console.log('[results] Triggering LLM regeneration...');
			await api.post(`/results/${resultId}/regenerate`, {});

			// LLM 완료될 때까지 폴링
			let attempts = 0;
			const maxAttempts = 60; // 최대 3분 (3초 * 60)
			const pollInterval = 3000;

			const pollResult = async (): Promise<MeetingResult | null> => {
				while (attempts < maxAttempts) {
					attempts++;
					await new Promise(resolve => setTimeout(resolve, pollInterval));

					try {
						const response = await api.get<{ data: MeetingResult[] }>(
							`/meetings/${meetingId}/results`
						);
						const results = response.data || [];
						// 가장 최신 버전 가져오기
						const latest = results.sort((a, b) => b.version - a.version)[0];

						// 요약이 있으면 완료
						if (latest && latest.summary && latest.summary.length > 0) {
							console.log('[results] LLM 재생성 완료');
							return latest;
						}
						console.log(`[results] LLM 대기 중... (${attempts}/${maxAttempts})`);
					} catch (e) {
						console.error('[results] 폴링 에러:', e);
					}
				}
				return null;
			};

			const finalResult = await pollResult();

			if (finalResult) {
				update((state) => ({
					...state,
					currentResult: finalResult,
					editedSummary: finalResult.summary || '',
					isGenerating: false
				}));
			} else {
				update((state) => ({
					...state,
					isGenerating: false,
					error: '회의록 재생성 시간이 초과되었습니다. 잠시 후 새로고침해주세요.'
				}));
			}
		} catch (error) {
			console.error('[results] 재생성 에러:', error);
			update((state) => ({
				...state,
				isGenerating: false,
				error: '회의록 재생성에 실패했습니다.'
			}));
		}
	}

	async function verifyResult(meetingId: number): Promise<void> {
		update((state) => ({ ...state, isLoading: true }));

		try {
			let resultId: number | null = null;
			update((state) => {
				resultId = state.currentResult?.id ?? null;
				return state;
			});

			if (!resultId) {
				throw new Error('No result to verify');
			}

			const response = await api.post<MeetingResult>(
				`/results/${resultId}/verify`
			);

			update((state) => ({
				...state,
				currentResult: response,
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
		let resultId: number | null = null;
		update((state) => {
			resultId = state.currentResult?.id ?? null;
			return state;
		});

		if (!resultId) {
			update((state) => ({
				...state,
				error: 'No result found for this meeting'
			}));
			return;
		}

		try {
			const response = await api.post<{ data: ActionItem }>(
				`/results/${resultId}/action-items`,
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
