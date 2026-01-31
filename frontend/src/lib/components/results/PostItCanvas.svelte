<script lang="ts">
	/**
	 * PostItCanvas - Container for draggable PostIt notes
	 * Handles API calls for position and visibility updates
	 */
	import DraggablePostIt from './DraggablePostIt.svelte';
	import { api } from '$lib/api';
	import { logger } from '$lib/utils/logger';

	interface Note {
		id: number;
		agenda_id: number | null;
		content: string;
		position_x: number | null;
		position_y: number | null;
		rotation: number | null;
		is_visible: boolean;
		z_index: number;
	}

	interface Props {
		notes: Note[];
		agendaId?: number;
		editable?: boolean;
		onupdate?: () => void;
	}

	let { notes = $bindable(), agendaId, editable = true, onupdate }: Props = $props();

	// Filter: only visible notes for this agenda
	let visibleNotes = $derived(
		notes.filter((n) => n.is_visible && (agendaId !== undefined ? n.agenda_id === agendaId : true))
	);

	// Color palette
	const colors: Array<'yellow' | 'pink' | 'green' | 'blue'> = ['yellow', 'pink', 'green', 'blue'];

	function getColor(index: number): 'yellow' | 'pink' | 'green' | 'blue' {
		return colors[index % colors.length];
	}

	async function handleMove(id: number, x: number, y: number) {
		try {
			await api.patch(`/notes/${id}/position`, {
				position_x: x,
				position_y: y
			});

			// Update local state
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

			// Update local state (hide the note)
			notes = notes.map((n) => (n.id === id ? { ...n, is_visible: false } : n));

			onupdate?.();
			logger.debug(`Note ${id} hidden`);
		} catch (error) {
			logger.error('Failed to hide note:', error);
		}
	}
</script>

<div class="postit-canvas">
	{#if visibleNotes.length === 0}
		<div class="empty-state">
			<p>메모가 없습니다</p>
		</div>
	{:else}
		{#each visibleNotes as note, idx (note.id)}
			<DraggablePostIt
				{note}
				color={getColor(idx)}
				{editable}
				onmove={handleMove}
				ondelete={handleDelete}
			/>
		{/each}
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
		align-items: center;
		justify-content: center;
		color: #94a3b8;
		font-size: 0.875rem;
	}
</style>
