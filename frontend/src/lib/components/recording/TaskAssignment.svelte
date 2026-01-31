<script lang="ts">
	import { resultsStore, type ActionItem } from '$lib/stores/results';

	interface Props {
		meetingId: number;
	}

	let { meetingId }: Props = $props();

	let showForm = $state(false);
	let editingId = $state<number | null>(null);
	let newTask = $state({
		content: '',
		assignee_name: '',
		due_date: '',
		priority: 'medium' as 'high' | 'medium' | 'low'
	});

	function resetForm() {
		newTask = {
			content: '',
			assignee_name: '',
			due_date: '',
			priority: 'medium'
		};
		showForm = false;
		editingId = null;
	}

	async function handleSubmit() {
		if (!newTask.content.trim()) return;

		if (editingId) {
			await resultsStore.updateActionItem(editingId, {
				content: newTask.content,
				assignee_name: newTask.assignee_name || undefined,
				due_date: newTask.due_date || null,
				priority: newTask.priority
			});
		} else {
			await resultsStore.createActionItem(meetingId, {
				content: newTask.content,
				assignee_name: newTask.assignee_name || undefined,
				due_date: newTask.due_date || null,
				priority: newTask.priority,
				status: 'pending'
			});
		}

		resetForm();
	}

	function startEdit(item: ActionItem) {
		editingId = item.id ?? null;
		newTask = {
			content: item.content,
			assignee_name: item.assignee_name || '',
			due_date: item.due_date || '',
			priority: item.priority
		};
		showForm = true;
	}

	async function handleDelete(itemId: number) {
		if (!confirm('이 업무를 삭제하시겠습니까?')) return;
		await resultsStore.deleteActionItem(itemId);
	}

	async function toggleComplete(item: ActionItem) {
		if (!item.id) return;
		const newStatus = item.status === 'completed' ? 'pending' : 'completed';
		await resultsStore.updateActionItem(item.id, { status: newStatus });
	}

	const priorityLabels = {
		high: '높음',
		medium: '보통',
		low: '낮음'
	};

	const priorityColors = {
		high: 'bg-red-100 text-red-700',
		medium: 'bg-yellow-100 text-yellow-700',
		low: 'bg-gray-100 text-gray-600'
	};
</script>

<div class="task-assignment">
	<div class="header">
		<h3>업무 배치</h3>
		{#if !showForm}
			<button type="button" class="add-btn" onclick={() => (showForm = true)}>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				업무 추가
			</button>
		{/if}
	</div>

	{#if showForm}
		<form class="task-form" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
			<input
				type="text"
				class="form-input"
				placeholder="업무 내용을 입력하세요"
				bind:value={newTask.content}
				required
			/>
			<div class="form-row">
				<input
					type="text"
					class="form-input flex-1"
					placeholder="담당자"
					bind:value={newTask.assignee_name}
				/>
				<input type="date" class="form-input" bind:value={newTask.due_date} />
				<select class="form-select" bind:value={newTask.priority}>
					<option value="high">높음</option>
					<option value="medium">보통</option>
					<option value="low">낮음</option>
				</select>
			</div>
			<div class="form-actions">
				<button type="button" class="btn-cancel" onclick={resetForm}>취소</button>
				<button type="submit" class="btn-submit">{editingId ? '수정' : '추가'}</button>
			</div>
		</form>
	{/if}

	<div class="task-list">
		{#each $resultsStore.actionItems as item (item.id)}
			<div class="task-card" class:completed={item.status === 'completed'}>
				<button
					type="button"
					class="checkbox"
					class:checked={item.status === 'completed'}
					onclick={() => toggleComplete(item)}
				>
					{#if item.status === 'completed'}
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path
								fill-rule="evenodd"
								d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
					{/if}
				</button>

				<div class="task-content">
					<p class="task-text">{item.content}</p>
					<div class="task-meta">
						{#if item.assignee_name}
							<span class="meta-item">
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
									/>
								</svg>
								{item.assignee_name}
							</span>
						{/if}
						{#if item.due_date}
							<span class="meta-item">
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
									/>
								</svg>
								{new Date(item.due_date).toLocaleDateString('ko-KR')}
							</span>
						{/if}
						<span class="priority-badge {priorityColors[item.priority]}">
							{priorityLabels[item.priority]}
						</span>
					</div>
				</div>

				<div class="task-actions">
					<button type="button" class="action-btn" onclick={() => startEdit(item)}>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
							/>
						</svg>
					</button>
					<button
						type="button"
						class="action-btn delete"
						onclick={() => item.id && handleDelete(item.id)}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
							/>
						</svg>
					</button>
				</div>
			</div>
		{:else}
			<div class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
					/>
				</svg>
				<p>배치된 업무가 없습니다</p>
				<p class="text-sm">업무 추가 버튼을 눌러 담당자를 배정하세요</p>
			</div>
		{/each}
	</div>
</div>

<style>
	.task-assignment {
		display: flex;
		flex-direction: column;
		height: 100%;
		padding: 1rem;
		overflow-y: auto;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.header h3 {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.add-btn {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.5rem 0.75rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}

	.add-btn:hover {
		background: #2563eb;
	}

	.task-form {
		padding: 1rem;
		background: #f9fafb;
		border-radius: 0.5rem;
		margin-bottom: 1rem;
	}

	.form-input,
	.form-select {
		padding: 0.5rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		width: 100%;
	}

	.form-input:focus,
	.form-select:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
	}

	.form-row {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	.form-row .form-input,
	.form-row .form-select {
		width: auto;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	.btn-cancel {
		padding: 0.5rem 1rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.btn-cancel:hover {
		background: #f3f4f6;
	}

	.btn-submit {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.btn-submit:hover {
		background: #2563eb;
	}

	.task-list {
		flex: 1;
	}

	.task-card {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 1rem;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		margin-bottom: 0.75rem;
		transition: all 0.15s;
	}

	.task-card:hover {
		border-color: #d1d5db;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
	}

	.task-card.completed {
		opacity: 0.6;
		background: #f9fafb;
	}

	.checkbox {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		flex-shrink: 0;
		margin-top: 2px;
		border: 2px solid #d1d5db;
		border-radius: 0.25rem;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.checkbox:hover {
		border-color: #9ca3af;
	}

	.checkbox.checked {
		background: #22c55e;
		border-color: #22c55e;
		color: white;
	}

	.task-content {
		flex: 1;
		min-width: 0;
	}

	.task-text {
		margin: 0 0 0.25rem;
		font-size: 0.9375rem;
		color: #111827;
		line-height: 1.4;
	}

	.task-card.completed .task-text {
		text-decoration: line-through;
		color: #6b7280;
	}

	.task-meta {
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

	.priority-badge {
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
		font-size: 0.6875rem;
		font-weight: 500;
	}

	.task-actions {
		display: flex;
		gap: 0.25rem;
		opacity: 0;
		transition: opacity 0.15s;
	}

	.task-card:hover .task-actions {
		opacity: 1;
	}

	.action-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 0.25rem;
		background: transparent;
		color: #6b7280;
		cursor: pointer;
		transition: all 0.15s;
	}

	.action-btn:hover {
		background: #f3f4f6;
		color: #374151;
	}

	.action-btn.delete:hover {
		background: #fee2e2;
		color: #dc2626;
	}

	.empty-state {
		padding: 3rem 1rem;
		text-align: center;
		color: #9ca3af;
	}

	.empty-state p {
		margin: 0.5rem 0 0;
	}

	/* Touch-friendly */
	@media (pointer: coarse) {
		.task-card {
			padding: 1.25rem 1rem;
		}

		.checkbox {
			width: 26px;
			height: 26px;
		}

		.task-actions {
			opacity: 1;
		}

		.action-btn {
			width: 40px;
			height: 40px;
		}
	}
</style>
