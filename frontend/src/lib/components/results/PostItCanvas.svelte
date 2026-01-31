<script lang="ts">
	/**
	 * PostItCanvas - Container for draggable PostIt notes
	 * Handles API calls for position, visibility, and note creation
	 */
	import DraggablePostIt from './DraggablePostIt.svelte';
	import { api } from '$lib/api';
	import { logger } from '$lib/utils/logger';
	import { Plus, X } from 'lucide-svelte';

	interface Note {
		id: number;
		agenda_id: number | null;
		content: string;
		position_x: number | null;
		position_y: number | null;
		rotation: number | null;
		is_visible: boolean;
		z_index: number;
		bg_color?: string | null;
		text_color?: string | null;
	}

	interface Props {
		notes: Note[];
		meetingId?: number;
		agendaId?: number;
		agendaIds?: number[];  // 여러 안건 ID를 한번에 필터링 (자식/손자 포함)
		editable?: boolean;
		onupdate?: () => void;
	}

	let { notes = $bindable(), meetingId, agendaId, agendaIds, editable = true, onupdate }: Props = $props();

	// Filter: only visible notes for this agenda(s)
	let visibleNotes = $derived(
		notes.filter((n) => {
			if (!n.is_visible) return false;
			// agendaIds 배열이 있으면 그 안의 ID들로 필터링
			if (agendaIds && agendaIds.length > 0) {
				return agendaIds.includes(n.agenda_id!);
			}
			// 단일 agendaId가 있으면 그걸로 필터링
			if (agendaId !== undefined) {
				return n.agenda_id === agendaId;
			}
			// 둘 다 없으면 모든 메모 표시
			return true;
		})
	);

	// Add note modal state
	let showAddModal = $state(false);
	let newNoteContent = $state('');
	let selectedBgColor = $state('yellow');
	let selectedTextColor = $state('#374151');

	// Color palettes
	const bgColors = [
		{ name: 'yellow', bg: '#fef08a', label: '노랑' },
		{ name: 'pink', bg: '#fbcfe8', label: '분홍' },
		{ name: 'green', bg: '#bbf7d0', label: '초록' },
		{ name: 'blue', bg: '#bfdbfe', label: '파랑' },
		{ name: 'purple', bg: '#ddd6fe', label: '보라' },
		{ name: 'orange', bg: '#fed7aa', label: '주황' }
	];

	const textColors = [
		{ color: '#374151', label: '검정' },
		{ color: '#991b1b', label: '빨강' },
		{ color: '#1e40af', label: '파랑' },
		{ color: '#166534', label: '초록' },
		{ color: '#6b21a8', label: '보라' },
		{ color: '#9a3412', label: '주황' }
	];

	async function handleMove(id: number, x: number, y: number) {
		try {
			await api.patch(`/notes/${id}/position`, {
				position_x: x,
				position_y: y
			});

			notes = notes.map((n) => (n.id === id ? { ...n, position_x: x, position_y: y } : n));
			logger.debug(`Note ${id} moved to (${x.toFixed(1)}, ${y.toFixed(1)})`);
		} catch (error) {
			logger.error('Failed to update note position:', error);
		}
	}

	async function handleDelete(id: number) {
		try {
			await api.patch(`/notes/${id}/visibility`, {
				is_visible: false
			});

			notes = notes.map((n) => (n.id === id ? { ...n, is_visible: false } : n));
			onupdate?.();
			logger.debug(`Note ${id} hidden`);
		} catch (error) {
			logger.error('Failed to hide note:', error);
		}
	}

	async function handleAddNote() {
		if (!newNoteContent.trim() || !meetingId) return;

		try {
			const response = await api.post<Note>(`/meetings/${meetingId}/notes`, {
				content: newNoteContent.trim(),
				agenda_id: agendaId || null,
				bg_color: selectedBgColor,
				text_color: selectedTextColor
			});

			notes = [...notes, response];
			onupdate?.();

			// Reset form
			newNoteContent = '';
			showAddModal = false;
			logger.debug('Note created:', response.id);
		} catch (error) {
			logger.error('Failed to create note:', error);
		}
	}

	function openAddModal() {
		newNoteContent = '';
		selectedBgColor = 'yellow';
		selectedTextColor = '#374151';
		showAddModal = true;
	}
</script>

<div class="postit-canvas">
	{#if visibleNotes.length === 0 && !showAddModal}
		<div class="empty-state">
			<p>메모가 없습니다</p>
			{#if editable && meetingId}
				<button type="button" class="add-first-btn" onclick={openAddModal}>
					<Plus class="w-4 h-4" />
					메모 추가
				</button>
			{/if}
		</div>
	{:else}
		{#each visibleNotes as note (note.id)}
			<DraggablePostIt
				{note}
				{editable}
				onmove={handleMove}
				ondelete={handleDelete}
			/>
		{/each}
	{/if}

	<!-- Add button (floating) -->
	{#if editable && meetingId && visibleNotes.length > 0}
		<button type="button" class="add-btn" onclick={openAddModal} aria-label="메모 추가">
			<Plus class="w-5 h-5" />
		</button>
	{/if}

	<!-- Add Note Modal -->
	{#if showAddModal}
		<div class="modal-overlay" onclick={() => showAddModal = false} role="presentation">
			<div class="modal-content" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
				<div class="modal-header">
					<h3>새 메모 추가</h3>
					<button type="button" class="close-btn" onclick={() => showAddModal = false}>
						<X class="w-5 h-5" />
					</button>
				</div>

				<div class="modal-body">
					<!-- Content -->
					<div class="form-group">
						<label for="note-content">내용</label>
						<textarea
							id="note-content"
							bind:value={newNoteContent}
							placeholder="메모 내용을 입력하세요"
							rows="3"
						></textarea>
					</div>

					<!-- Background Color Palette -->
					<div class="form-group">
						<label>배경색</label>
						<div class="color-palette">
							{#each bgColors as { name, bg, label }}
								<button
									type="button"
									class="color-swatch"
									class:selected={selectedBgColor === name}
									style="background-color: {bg}"
									onclick={() => selectedBgColor = name}
									title={label}
									aria-label={label}
								></button>
							{/each}
						</div>
					</div>

					<!-- Text Color Palette -->
					<div class="form-group">
						<label>글자색</label>
						<div class="color-palette">
							{#each textColors as { color, label }}
								<button
									type="button"
									class="color-swatch text-swatch"
									class:selected={selectedTextColor === color}
									style="background-color: {color}"
									onclick={() => selectedTextColor = color}
									title={label}
									aria-label={label}
								></button>
							{/each}
						</div>
					</div>

					<!-- Preview -->
					<div class="form-group">
						<label>미리보기</label>
						<div
							class="preview-note"
							style="background-color: {bgColors.find(c => c.name === selectedBgColor)?.bg || '#fef08a'}; color: {selectedTextColor}"
						>
							{newNoteContent || '메모 내용'}
						</div>
					</div>
				</div>

				<div class="modal-footer">
					<button type="button" class="btn-cancel" onclick={() => showAddModal = false}>
						취소
					</button>
					<button
						type="button"
						class="btn-add"
						onclick={handleAddNote}
						disabled={!newNoteContent.trim()}
					>
						추가
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.postit-canvas {
		position: relative;
		width: 100%;
		min-height: 400px;
		background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
		border: 2px dashed #cbd5e1;
		border-radius: 0.75rem;
		overflow: hidden;
	}

	.empty-state {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		color: #94a3b8;
		font-size: 0.875rem;
	}

	.add-first-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		cursor: pointer;
		transition: background 0.15s;
	}

	.add-first-btn:hover {
		background: #2563eb;
	}

	.add-btn {
		position: absolute;
		bottom: 1rem;
		right: 1rem;
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 50%;
		box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
		cursor: pointer;
		transition: all 0.2s;
		z-index: 100;
	}

	.add-btn:hover {
		background: #2563eb;
		transform: scale(1.1);
	}

	/* Modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}

	.modal-content {
		background: white;
		border-radius: 1rem;
		width: 90%;
		max-width: 400px;
		box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem 1.25rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.modal-header h3 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.close-btn {
		background: none;
		border: none;
		color: #6b7280;
		cursor: pointer;
		padding: 0.25rem;
		border-radius: 0.25rem;
	}

	.close-btn:hover {
		background: #f3f4f6;
	}

	.modal-body {
		padding: 1.25rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-group:last-child {
		margin-bottom: 0;
	}

	.form-group label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		margin-bottom: 0.5rem;
	}

	.form-group textarea {
		width: 100%;
		padding: 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		resize: none;
	}

	.form-group textarea:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.color-palette {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.color-swatch {
		width: 32px;
		height: 32px;
		border: 2px solid transparent;
		border-radius: 0.5rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.color-swatch:hover {
		transform: scale(1.1);
	}

	.color-swatch.selected {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
	}

	.text-swatch {
		border-radius: 50%;
	}

	.preview-note {
		padding: 0.75rem;
		border-radius: 0.25rem;
		font-size: 0.875rem;
		min-height: 60px;
		box-shadow: 2px 2px 6px rgba(0, 0, 0, 0.1);
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		border-top: 1px solid #e5e7eb;
	}

	.btn-cancel {
		padding: 0.5rem 1rem;
		background: #f3f4f6;
		color: #374151;
		border: none;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.btn-cancel:hover {
		background: #e5e7eb;
	}

	.btn-add {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.5rem;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.btn-add:hover:not(:disabled) {
		background: #2563eb;
	}

	.btn-add:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
