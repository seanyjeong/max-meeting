/**
 * Offline Store - Offline sync and conflict resolution
 */
import { writable, derived } from 'svelte/store';
import { api } from '$lib/api';

export interface ConflictData {
	resourceType: 'meeting' | 'note' | 'sketch';
	resourceId: number;
	localData: unknown;
	serverData: unknown;
	localUpdatedAt: Date;
	serverUpdatedAt: Date;
}

export interface OfflineQueueItem {
	id: string;
	type: 'create' | 'update' | 'delete';
	resourceType: 'meeting' | 'note' | 'sketch';
	resourceId?: number;
	data: unknown;
	timestamp: Date;
	retryCount: number;
}

export interface OfflineState {
	isOnline: boolean;
	isSyncing: boolean;
	pendingConflicts: ConflictData[];
	syncQueue: OfflineQueueItem[];
	lastSyncAt: Date | null;
	syncError: string | null;
}

const initialState: OfflineState = {
	isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
	isSyncing: false,
	pendingConflicts: [],
	syncQueue: [],
	lastSyncAt: null,
	syncError: null
};

const STORAGE_KEY = 'offline-sync-queue';
const CONFLICT_STORAGE_KEY = 'offline-pending-conflicts';

function createOfflineStore() {
	const { subscribe, set, update } = writable<OfflineState>(initialState);

	// 로컬스토리지에서 큐 복원
	function loadFromStorage(): void {
		if (typeof localStorage === 'undefined') return;

		try {
			const queueData = localStorage.getItem(STORAGE_KEY);
			const conflictData = localStorage.getItem(CONFLICT_STORAGE_KEY);

			update((state) => ({
				...state,
				syncQueue: queueData ? JSON.parse(queueData, reviveDate) : [],
				pendingConflicts: conflictData ? JSON.parse(conflictData, reviveDate) : []
			}));
		} catch (error) {
			console.error('Failed to load offline data from storage:', error);
		}
	}

	// 로컬스토리지에 큐 저장
	function saveToStorage(state: OfflineState): void {
		if (typeof localStorage === 'undefined') return;

		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(state.syncQueue));
			localStorage.setItem(CONFLICT_STORAGE_KEY, JSON.stringify(state.pendingConflicts));
		} catch (error) {
			console.error('Failed to save offline data to storage:', error);
		}
	}

	// Date 객체 복원을 위한 reviver 함수
	function reviveDate(_key: string, value: unknown): unknown {
		if (typeof value === 'string') {
			const datePattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
			if (datePattern.test(value)) {
				return new Date(value);
			}
		}
		return value;
	}

	// 큐에 작업 추가
	function addToQueue(item: Omit<OfflineQueueItem, 'id' | 'timestamp' | 'retryCount'>): void {
		const queueItem: OfflineQueueItem = {
			...item,
			id: crypto.randomUUID(),
			timestamp: new Date(),
			retryCount: 0
		};

		update((state) => {
			const newState = {
				...state,
				syncQueue: [...state.syncQueue, queueItem]
			};
			saveToStorage(newState);
			return newState;
		});
	}

	// 충돌 감지 및 추가 (서버 데이터와 비교)
	async function checkAndAddConflict(
		resourceType: ConflictData['resourceType'],
		resourceId: number,
		localData: unknown,
		localUpdatedAt: Date
	): Promise<boolean> {
		try {
			let endpoint = '';
			switch (resourceType) {
				case 'meeting':
					endpoint = `/meetings/${resourceId}`;
					break;
				case 'sketch':
					endpoint = `/sketches/${resourceId}`;
					break;
				case 'note':
					endpoint = `/notes/${resourceId}`;
					break;
			}

			const response = await api.get<{ data: { updated_at: string; [key: string]: unknown } }>(
				endpoint
			);
			const serverData = response.data;
			const serverUpdatedAt = new Date(serverData.updated_at);

			// 서버 데이터가 더 최신인 경우 충돌로 간주
			if (serverUpdatedAt > localUpdatedAt) {
				const conflict: ConflictData = {
					resourceType,
					resourceId,
					localData,
					serverData,
					localUpdatedAt,
					serverUpdatedAt
				};

				update((state) => {
					const newState = {
						...state,
						pendingConflicts: [...state.pendingConflicts, conflict]
					};
					saveToStorage(newState);
					return newState;
				});

				return true; // 충돌 발생
			}

			return false; // 충돌 없음
		} catch (error) {
			console.error('Failed to check for conflicts:', error);
			return false;
		}
	}

	// 충돌 해결
	async function resolveConflict(
		conflictIndex: number,
		choice: 'local' | 'server' | 'merge'
	): Promise<void> {
		update((state) => {
			const conflict = state.pendingConflicts[conflictIndex];
			if (!conflict) return state;

			let dataToSync: unknown;
			switch (choice) {
				case 'local':
					dataToSync = conflict.localData;
					break;
				case 'server':
					dataToSync = conflict.serverData;
					break;
				case 'merge':
					// 병합 로직은 리소스 타입에 따라 다를 수 있음
					// 여기서는 간단히 로컬 데이터를 선택
					dataToSync = conflict.localData;
					break;
			}

			// 선택된 데이터로 서버에 업데이트
			if (choice === 'local') {
				// 로컬 데이터를 서버에 푸시
				let endpoint = '';
				switch (conflict.resourceType) {
					case 'meeting':
						endpoint = `/meetings/${conflict.resourceId}`;
						break;
					case 'sketch':
						endpoint = `/sketches/${conflict.resourceId}`;
						break;
					case 'note':
						endpoint = `/notes/${conflict.resourceId}`;
						break;
				}

				api.patch(endpoint, dataToSync).catch((error) => {
					console.error('Failed to sync conflict resolution:', error);
				});
			}
			// 서버 데이터를 선택한 경우 로컬 스토어를 업데이트하는 것은
			// 각 리소스별 스토어에서 처리해야 합니다

			// 충돌 목록에서 제거
			const newConflicts = state.pendingConflicts.filter((_, i) => i !== conflictIndex);
			const newState = {
				...state,
				pendingConflicts: newConflicts
			};
			saveToStorage(newState);
			return newState;
		});
	}

	// 큐의 모든 작업 동기화
	async function syncQueue(): Promise<void> {
		update((state) => ({ ...state, isSyncing: true, syncError: null }));

		try {
			// Get current state synchronously to avoid race condition
			let currentState: OfflineState = initialState;
			const unsubscribe = subscribe((state) => {
				currentState = state;
			});
			unsubscribe(); // Immediately unsubscribe after getting the state

			// 큐의 각 항목 처리
			for (const item of currentState.syncQueue) {
				try {
					await processSyncItem(item);

					// 성공한 항목 제거
					update((state) => {
						const newQueue = state.syncQueue.filter((i) => i.id !== item.id);
						const newState = { ...state, syncQueue: newQueue };
						saveToStorage(newState);
						return newState;
					});
				} catch (error) {
					console.error('Failed to sync item:', item, error);

					// 재시도 횟수 증가
					update((state) => {
						const newQueue = state.syncQueue.map((i) =>
							i.id === item.id ? { ...i, retryCount: i.retryCount + 1 } : i
						);
						const newState = { ...state, syncQueue: newQueue };
						saveToStorage(newState);
						return newState;
					});
				}
			}

			update((state) => ({
				...state,
				isSyncing: false,
				lastSyncAt: new Date()
			}));
		} catch (error) {
			update((state) => ({
				...state,
				isSyncing: false,
				syncError: error instanceof Error ? error.message : 'Unknown error'
			}));
		}
	}

	// 개별 동기화 항목 처리
	async function processSyncItem(item: OfflineQueueItem): Promise<void> {
		let endpoint = '';
		switch (item.resourceType) {
			case 'meeting':
				endpoint = item.resourceId ? `/meetings/${item.resourceId}` : '/meetings';
				break;
			case 'sketch':
				endpoint = item.resourceId ? `/sketches/${item.resourceId}` : '/sketches';
				break;
			case 'note':
				endpoint = item.resourceId ? `/notes/${item.resourceId}` : '/notes';
				break;
		}

		switch (item.type) {
			case 'create':
				await api.post(endpoint, item.data);
				break;
			case 'update':
				await api.patch(endpoint, item.data);
				break;
			case 'delete':
				await api.delete(endpoint);
				break;
		}
	}

	// 온라인/오프라인 상태 리스너 설정
	function setupOnlineListener(): void {
		if (typeof window === 'undefined') return;

		window.addEventListener('online', () => {
			update((state) => ({ ...state, isOnline: true }));
			// 온라인 복귀 시 자동 동기화
			syncQueue();
		});

		window.addEventListener('offline', () => {
			update((state) => ({ ...state, isOnline: false }));
		});
	}

	// 초기화
	loadFromStorage();
	setupOnlineListener();

	return {
		subscribe,

		addToQueue,
		checkAndAddConflict,
		resolveConflict,
		syncQueue,

		// 충돌 제거 (사용자가 나중에 결정하기를 선택한 경우)
		dismissConflict: (index: number) =>
			update((state) => {
				const newConflicts = state.pendingConflicts.filter((_, i) => i !== index);
				const newState = { ...state, pendingConflicts: newConflicts };
				saveToStorage(newState);
				return newState;
			}),

		// 모든 충돌 제거
		clearAllConflicts: () =>
			update((state) => {
				const newState = { ...state, pendingConflicts: [] };
				saveToStorage(newState);
				return newState;
			}),

		// 큐 초기화
		clearQueue: () =>
			update((state) => {
				const newState = { ...state, syncQueue: [] };
				saveToStorage(newState);
				return newState;
			}),

		// 에러 초기화
		clearError: () => update((state) => ({ ...state, syncError: null }))
	};
}

export const offlineStore = createOfflineStore();

// 파생 스토어: 충돌이 있는지 여부
export const hasConflicts = derived(
	offlineStore,
	($offline) => $offline.pendingConflicts.length > 0
);

// 파생 스토어: 대기 중인 동기화 항목이 있는지 여부
export const hasPendingSync = derived(
	offlineStore,
	($offline) => $offline.syncQueue.length > 0
);
