/**
 * Notes Store - Per-agenda notes management
 *
 * Handles notes CRUD operations with auto-save functionality.
 * Each note is associated with a specific agenda item.
 */
import { writable, derived, get } from 'svelte/store';
import { api } from '$lib/api';

export interface Note {
	id?: number;
	agendaId: number;
	content: string;
	createdAt?: Date;
	updatedAt?: Date;
}

interface NotesState {
	notes: Map<number, Note>; // agendaId -> note
	dirtyNotes: Set<number>; // agendaIds with unsaved changes
	isLoading: boolean;
	isSaving: boolean;
	error: string | null;
	lastSavedAt: Date | null;
	meetingId: number | null; // Store meetingId for POST endpoint
}

const AUTO_SAVE_INTERVAL_MS = 30 * 1000; // 30 seconds

function createNotesStore() {
	const { subscribe, set, update } = writable<NotesState>({
		notes: new Map(),
		dirtyNotes: new Set(),
		isLoading: false,
		isSaving: false,
		error: null,
		lastSavedAt: null,
		meetingId: null
	});

	let autoSaveInterval: ReturnType<typeof setInterval> | null = null;

	const startAutoSave = () => {
		if (autoSaveInterval) clearInterval(autoSaveInterval);
		autoSaveInterval = setInterval(async () => {
			await autoSave();
		}, AUTO_SAVE_INTERVAL_MS);
	};

	const stopAutoSave = () => {
		if (autoSaveInterval) {
			clearInterval(autoSaveInterval);
			autoSaveInterval = null;
		}
	};

	const autoSave = async () => {
		const state = get({ subscribe });
		if (state.dirtyNotes.size === 0 || state.isSaving || !state.meetingId) {
			return;
		}

		update((s) => ({ ...s, isSaving: true, error: null }));

		const dirtyAgendaIds = Array.from(state.dirtyNotes);
		const savePromises = dirtyAgendaIds.map(async (agendaId) => {
			const note = state.notes.get(agendaId);
			if (!note) return;

			try {
				console.log('[notes] 노트 저장 시작:', {
					agendaId,
					noteId: note.id,
					contentLength: note.content?.length,
					meetingId: state.meetingId
				});
				if (note.id) {
					// Update existing note
					await api.patch<{ data: Note }>(`/notes/${note.id}`, {
						content: note.content
					});
					console.log('[notes] 노트 업데이트 완료:', note.id);
				} else {
					// Create new note - use correct endpoint
					console.log('[notes] 새 노트 생성 요청:', {
						agenda_id: note.agendaId,
						content_length: note.content?.length
					});
					const response = await api.post<{ data: { id: number; agenda_id: number; content: string; created_at: string; updated_at: string } }>(`/meetings/${state.meetingId}/notes`, {
						agenda_id: note.agendaId,
						content: note.content
					});
					console.log('[notes] 새 노트 생성 완료:', response.data?.id);
					// Update with server-generated ID (handle snake_case conversion)
					update((s) => {
						const updatedNotes = new Map(s.notes);
						const existingNote = updatedNotes.get(agendaId);
						if (existingNote) {
							updatedNotes.set(agendaId, {
								...existingNote,
								id: response.data.id,
								createdAt: new Date(response.data.created_at),
								updatedAt: new Date(response.data.updated_at)
							});
						}
						return { ...s, notes: updatedNotes };
					});
				}
			} catch (error) {
				console.error(`Failed to save note for agenda ${agendaId}:`, error);
				throw error;
			}
		});

		try {
			await Promise.all(savePromises);
			update((s) => ({
				...s,
				dirtyNotes: new Set(),
				isSaving: false,
				lastSavedAt: new Date(),
				error: null
			}));
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Failed to save notes';
			update((s) => ({
				...s,
				isSaving: false,
				error: message
			}));
		}
	};

	return {
		subscribe,

		async loadNotes(meetingId: number): Promise<void> {
			update((s) => ({ ...s, isLoading: true, error: null }));

			try {
				// API returns snake_case, map to camelCase
				interface ApiNote {
					id: number;
					agenda_id: number;
					content: string;
					created_at?: string;
					updated_at?: string;
				}
				const response = await api.get<{ data: ApiNote[] }>(`/meetings/${meetingId}/notes`);
				const notesMap = new Map<number, Note>();

				response.data.forEach((note) => {
					notesMap.set(note.agenda_id, {
						id: note.id,
						agendaId: note.agenda_id,
						content: note.content,
						createdAt: note.created_at ? new Date(note.created_at) : undefined,
						updatedAt: note.updated_at ? new Date(note.updated_at) : undefined
					});
				});

				update((s) => ({
					...s,
					notes: notesMap,
					dirtyNotes: new Set(),
					isLoading: false,
					error: null,
					meetingId // Store meetingId for POST endpoint
				}));

				// Start auto-save after loading
				startAutoSave();
			} catch (error) {
				const message = error instanceof Error ? error.message : 'Failed to load notes';
				update((s) => ({
					...s,
					isLoading: false,
					error: message
				}));
			}
		},

		async saveNote(agendaId: number, content: string): Promise<void> {
			update((s) => {
				const updatedNotes = new Map(s.notes);
				const existingNote = updatedNotes.get(agendaId);

				updatedNotes.set(agendaId, {
					...existingNote,
					agendaId,
					content,
					id: existingNote?.id
				});

				const updatedDirty = new Set(s.dirtyNotes);
				updatedDirty.add(agendaId);

				return {
					...s,
					notes: updatedNotes,
					dirtyNotes: updatedDirty
				};
			});
		},

		getNote(agendaId: number): Note | undefined {
			const state = get({ subscribe });
			return state.notes.get(agendaId);
		},

		async forceSave(): Promise<void> {
			await autoSave();
		},

		cleanup(): void {
			stopAutoSave();
			set({
				notes: new Map(),
				dirtyNotes: new Set(),
				isLoading: false,
				isSaving: false,
				error: null,
				lastSavedAt: null,
				meetingId: null
			});
		}
	};
}

export const notesStore = createNotesStore();

// Derived stores for convenience
export const isNotesLoading = derived(notesStore, ($store) => $store.isLoading);
export const isNotesSaving = derived(notesStore, ($store) => $store.isSaving);
export const notesSaveError = derived(notesStore, ($store) => $store.error);
export const lastSavedAt = derived(notesStore, ($store) => $store.lastSavedAt);
export const hasDirtyNotes = derived(notesStore, ($store) => $store.dirtyNotes.size > 0);
