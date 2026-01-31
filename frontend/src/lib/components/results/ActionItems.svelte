<script lang="ts">
	import { resultsStore, type ActionItem } from '$lib/stores/results';
	import Button from '$lib/components/Button.svelte';
	import Badge from '$lib/components/Badge.svelte';
	import { formatDate } from '$lib/utils/format';

	interface Props {
		meetingId: number;
		readonly?: boolean;
	}

	let { meetingId, readonly = false }: Props = $props();

	let showAddForm = $state(false);
	let editingId = $state<number | null>(null);
	let draggedItem = $state<ActionItem | null>(null);
	let dragOverId = $state<number | null>(null);

	// New item form state
	let newItem = $state<Partial<ActionItem>>({
		content: '',
		assignee_name: '',
		due_date: null,
		priority: 'medium',
		status: 'pending'
	});

	const priorityColors = {
		high: 'red',
		medium: 'yellow',
		low: 'gray'
	} as const;

	const statusColors = {
		pending: 'gray',
		in_progress: 'blue',
		completed: 'green'
	} as const;

	function resetForm() {
		newItem = {
			content: '',
			assignee_name: '',
			due_date: null,
			priority: 'medium',
			status: 'pending'
		};
		showAddForm = false;
		editingId = null;
	}

	async function handleAdd() {
		if (!newItem.content?.trim()) return;

		await resultsStore.createActionItem(meetingId, {
			meeting_id: meetingId,
			content: newItem.content,
			due_date: newItem.due_date || null,
			priority: newItem.priority || 'medium',
			status: 'pending'
		});

		resetForm();
	}

	function startEdit(item: ActionItem) {
		editingId = item.id ?? null;
		newItem = { ...item };
	}

	async function handleUpdate() {
		if (!editingId || !newItem.content?.trim()) return;

		await resultsStore.updateActionItem(editingId, {
			content: newItem.content,
			due_date: newItem.due_date,
			priority: newItem.priority,
			status: newItem.status
		});

		resetForm();
	}

	async function handleDelete(itemId: number) {
		if (!confirm('이 실행항목을 삭제하시겠습니까?')) return;
		await resultsStore.deleteActionItem(itemId);
	}

	async function toggleStatus(item: ActionItem) {
		if (readonly || !item.id) return;

		const nextStatus: Record<string, ActionItem['status']> = {
			pending: 'in_progress',
			in_progress: 'completed',
			completed: 'pending'
		};

		await resultsStore.updateActionItem(item.id, {
			status: nextStatus[item.status]
		});
	}

	// Drag and drop handlers
	function handleDragStart(event: DragEvent, item: ActionItem) {
		draggedItem = item;
		if (event.dataTransfer) {
			event.dataTransfer.effectAllowed = 'move';
		}
	}

	function handleDragOver(event: DragEvent, item: ActionItem) {
		event.preventDefault();
		if (draggedItem && draggedItem.id !== item.id) {
			dragOverId = item.id ?? null;
		}
	}

	function handleDragLeave() {
		dragOverId = null;
	}

	function handleDrop(event: DragEvent, targetItem: ActionItem) {
		event.preventDefault();
		dragOverId = null;

		if (!draggedItem || draggedItem.id === targetItem.id) {
			draggedItem = null;
			return;
		}

		// Reorder items
		const items = [...$resultsStore.actionItems];
		const draggedIndex = items.findIndex(i => i.id === draggedItem!.id);
		const targetIndex = items.findIndex(i => i.id === targetItem.id);

		if (draggedIndex !== -1 && targetIndex !== -1) {
			items.splice(draggedIndex, 1);
			items.splice(targetIndex, 0, draggedItem);
			resultsStore.reorderActionItems(items);
		}

		draggedItem = null;
	}

	function isOverdue(dateStr: string | null): boolean {
		if (!dateStr) return false;
		return new Date(dateStr) < new Date();
	}
</script>

<div class="action-items">
	<div class="header">
		<h3 class="title">업무 배치</h3>
		{#if !readonly}
			<Button
				variant="primary"
				size="sm"
				onclick={() => showAddForm = true}
			>
				{#snippet children()}
					<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					항목 추가
				{/snippet}
			</Button>
		{/if}
	</div>

	<!-- Add/Edit Form -->
	{#if showAddForm || editingId}
		<form class="item-form" onsubmit={(e) => { e.preventDefault(); editingId ? handleUpdate() : handleAdd(); }}>
			<div class="form-row">
				<input
					type="text"
					class="form-input flex-1"
					placeholder="실행할 내용을 입력하세요..."
					bind:value={newItem.content}
					required
				/>
			</div>

			<div class="form-row">
				<input
					type="text"
					class="form-input"
					placeholder="담당자"
					bind:value={newItem.assignee_name}
				/>

				<input
					type="date"
					class="form-input"
					bind:value={newItem.due_date}
				/>

				<select class="form-select" bind:value={newItem.priority}>
					<option value="high">높음</option>
					<option value="medium">보통</option>
					<option value="low">낮음</option>
				</select>

				{#if editingId}
					<select class="form-select" bind:value={newItem.status}>
						<option value="pending">대기</option>
						<option value="in_progress">진행중</option>
						<option value="completed">완료</option>
					</select>
				{/if}
			</div>

			<div class="form-actions">
				<Button variant="secondary" size="sm" onclick={resetForm}>
					{#snippet children()}취소{/snippet}
				</Button>
				<Button variant="primary" size="sm" type="submit">
					{#snippet children()}{editingId ? '수정' : '추가'}{/snippet}
				</Button>
			</div>
		</form>
	{/if}

	<!-- Items List -->
	<ul class="items-list" role="list">
		{#each $resultsStore.actionItems as item (item.id)}
			<li
				class="item"
				class:completed={item.status === 'completed'}
				class:drag-over={dragOverId === item.id}
				draggable={!readonly}
				ondragstart={(e) => handleDragStart(e, item)}
				ondragover={(e) => handleDragOver(e, item)}
				ondragleave={handleDragLeave}
				ondrop={(e) => handleDrop(e, item)}
			>
				<button
					type="button"
					class="status-checkbox"
					class:checked={item.status === 'completed'}
					onclick={() => toggleStatus(item)}
					disabled={readonly}
					aria-label={item.status === 'completed' ? 'Mark as pending' : 'Mark as completed'}
				>
					{#if item.status === 'completed'}
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
						</svg>
					{/if}
				</button>

				<div class="item-content">
					<p class="item-text">{item.content}</p>

					<div class="item-meta">
						{#if item.assignee_name}
							<span class="meta-item">
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
								</svg>
								{item.assignee_name}
							</span>
						{/if}

						{#if item.due_date}
							<span class="meta-item" class:overdue={isOverdue(item.due_date) && item.status !== 'completed'}>
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
								</svg>
								{formatDate(item.due_date)}
							</span>
						{/if}

						<Badge variant={priorityColors[item.priority]}>{item.priority}</Badge>
						<Badge variant={statusColors[item.status]}>{item.status.replace('_', ' ')}</Badge>
					</div>
				</div>

				{#if !readonly}
					<div class="item-actions">
						<button
							type="button"
							class="action-btn"
							onclick={() => startEdit(item)}
							aria-label="Edit"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
							</svg>
						</button>
						<button
							type="button"
							class="action-btn delete"
							onclick={() => item.id && handleDelete(item.id)}
							aria-label="Delete"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
							</svg>
						</button>
					</div>
				{/if}

				<!-- Drag handle -->
				{#if !readonly}
					<div class="drag-handle" aria-hidden="true">
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
						</svg>
					</div>
				{/if}
			</li>
		{:else}
			<li class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
				</svg>
				<p>No action items yet</p>
			</li>
		{/each}
	</ul>
</div>

<style>
	.action-items {
		background: white;
		border-radius: 0.5rem;
		border: 1px solid #e5e7eb;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.title {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.item-form {
		padding: 1rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.form-row {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.form-input,
	.form-select {
		padding: 0.5rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	.form-input:focus,
	.form-select:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
	}

	.items-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.item {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #e5e7eb;
		transition: background 0.15s;
	}

	.item:last-child {
		border-bottom: none;
	}

	.item:hover {
		background: #f9fafb;
	}

	.item.completed {
		opacity: 0.6;
	}

	.item.drag-over {
		background: #dbeafe;
	}

	.status-checkbox {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		flex-shrink: 0;
		margin-top: 2px;
		border: 2px solid #d1d5db;
		border-radius: 0.25rem;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.status-checkbox:hover:not(:disabled) {
		border-color: #9ca3af;
	}

	.status-checkbox.checked {
		background: #22c55e;
		border-color: #22c55e;
		color: white;
	}

	.item-content {
		flex: 1;
		min-width: 0;
	}

	.item-text {
		margin: 0 0 0.25rem;
		font-size: 0.875rem;
		color: #111827;
	}

	.item.completed .item-text {
		text-decoration: line-through;
	}

	.item-meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.meta-item.overdue {
		color: #dc2626;
	}

	.item-actions {
		display: flex;
		gap: 0.25rem;
		opacity: 0;
		transition: opacity 0.15s;
	}

	.item:hover .item-actions {
		opacity: 1;
	}

	.action-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border: none;
		border-radius: 0.25rem;
		background: transparent;
		color: #6b7280;
		cursor: pointer;
		transition: all 0.15s;
	}

	.action-btn:hover {
		background: #e5e7eb;
		color: #374151;
	}

	.action-btn.delete:hover {
		background: #fee2e2;
		color: #dc2626;
	}

	.drag-handle {
		display: flex;
		align-items: center;
		padding: 0 0.25rem;
		color: #d1d5db;
		cursor: grab;
	}

	.drag-handle:active {
		cursor: grabbing;
	}

	.empty-state {
		padding: 2rem;
		text-align: center;
		color: #9ca3af;
	}

	.empty-state p {
		margin-top: 0.5rem;
		font-size: 0.875rem;
	}

	/* Touch-friendly adjustments */
	@media (pointer: coarse) {
		.item {
			padding: 1rem;
		}

		.status-checkbox {
			width: 24px;
			height: 24px;
		}

		.item-actions {
			opacity: 1;
		}

		.action-btn {
			width: 36px;
			height: 36px;
		}
	}
</style>
