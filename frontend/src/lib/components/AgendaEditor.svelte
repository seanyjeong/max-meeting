<script lang="ts">
	import { dndzone, type DndEvent } from 'svelte-dnd-action';
	import { flip } from 'svelte/animate';

	export interface AgendaItem {
		id: string;
		title: string;
		description: string;
	}

	interface Props {
		items: AgendaItem[];
		onItemsChange: (items: AgendaItem[]) => void;
		disabled?: boolean;
	}

	let { items = [], onItemsChange, disabled = false }: Props = $props();

	// Local state for drag-and-drop
	let localItems = $state<AgendaItem[]>([...items]);
	let dragDisabled = $state(true);

	// Expanded items tracking
	let expandedItems = $state<Set<string>>(new Set());

	// Selected items for merging
	let selectedItems = $state<Set<string>>(new Set());

	// Undo history (last 20 states)
	let history = $state<AgendaItem[][]>([]);
	const MAX_HISTORY = 20;

	// Sync items prop with local state
	$effect(() => {
		localItems = [...items];
	});

	// Save state to history before modifications
	function saveHistory() {
		history = [...history.slice(-MAX_HISTORY + 1), [...localItems]];
	}

	// Undo last action
	function undo() {
		if (history.length === 0) return;
		const previousState = history[history.length - 1];
		history = history.slice(0, -1);
		localItems = [...previousState];
		onItemsChange(localItems);
	}

	// Handle keyboard shortcuts
	function handleKeyDown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
			e.preventDefault();
			undo();
		}
	}

	// Drag-and-drop handler
	function handleDndConsider(e: CustomEvent<DndEvent<AgendaItem>>) {
		localItems = e.detail.items as AgendaItem[];
	}

	function handleDndFinalize(e: CustomEvent<DndEvent<AgendaItem>>) {
		saveHistory();
		localItems = e.detail.items as AgendaItem[];
		onItemsChange(localItems);
		dragDisabled = true;
	}

	// Add new item
	function addItem() {
		saveHistory();
		const newItem: AgendaItem = {
			id: crypto.randomUUID(),
			title: '',
			description: ''
		};
		localItems = [...localItems, newItem];
		onItemsChange(localItems);
	}

	// Remove item
	function removeItem(id: string) {
		saveHistory();
		localItems = localItems.filter((item) => item.id !== id);
		expandedItems.delete(id);
		selectedItems.delete(id);
		onItemsChange(localItems);
	}

	// Toggle expanded state
	function toggleExpanded(id: string) {
		if (expandedItems.has(id)) {
			expandedItems.delete(id);
		} else {
			expandedItems.add(id);
		}
		expandedItems = expandedItems;
	}

	// Toggle selection
	function toggleSelection(id: string) {
		if (selectedItems.has(id)) {
			selectedItems.delete(id);
		} else {
			selectedItems.add(id);
		}
		selectedItems = selectedItems;
	}

	// Merge selected items
	function mergeSelected() {
		if (selectedItems.size < 2) return;

		saveHistory();

		const selected = localItems.filter((item) => selectedItems.has(item.id));
		const mergedTitle = selected.map((item) => item.title).join(' + ');
		const mergedDescription = selected
			.map((item) => item.description)
			.filter((desc) => desc.trim())
			.join('\n\n');

		const mergedItem: AgendaItem = {
			id: crypto.randomUUID(),
			title: mergedTitle,
			description: mergedDescription
		};

		// Replace first selected item with merged, remove others
		const firstSelectedIndex = localItems.findIndex((item) => selectedItems.has(item.id));
		localItems = [
			...localItems.slice(0, firstSelectedIndex),
			mergedItem,
			...localItems.slice(firstSelectedIndex + 1).filter((item) => !selectedItems.has(item.id))
		];

		selectedItems.clear();
		selectedItems = selectedItems;
		onItemsChange(localItems);
	}

	// Split item by description lines
	function splitItem(id: string) {
		saveHistory();

		const item = localItems.find((i) => i.id === id);
		if (!item || !item.description.trim()) return;

		const lines = item.description
			.split('\n')
			.map((line) => line.trim())
			.filter((line) => line);

		if (lines.length <= 1) return;

		const newItems = lines.map((line) => ({
			id: crypto.randomUUID(),
			title: line.substring(0, 50),
			description: line
		}));

		const index = localItems.findIndex((i) => i.id === id);
		localItems = [...localItems.slice(0, index), ...newItems, ...localItems.slice(index + 1)];

		onItemsChange(localItems);
	}

	// Update item field
	function updateItem(id: string, field: keyof AgendaItem, value: string) {
		const index = localItems.findIndex((item) => item.id === id);
		if (index === -1) return;

		localItems[index] = { ...localItems[index], [field]: value };
		onItemsChange(localItems);
	}

	// Start dragging
	function startDrag(e: MouseEvent | TouchEvent) {
		if (disabled) return;
		e.preventDefault();
		dragDisabled = false;
	}
</script>

<svelte:window onkeydown={handleKeyDown} />

<div
	class="agenda-editor w-full max-w-5xl mx-auto"
	role="region"
	aria-label="Agenda Editor"
>
	<!-- Toolbar -->
	<div
		class="toolbar flex items-center justify-between gap-4 p-4 bg-gradient-to-br from-slate-50 to-slate-100 border-b-2 border-slate-200 shadow-sm"
	>
		<div class="flex items-center gap-3">
			<!-- Undo Button -->
			<button
				type="button"
				onclick={undo}
				disabled={disabled || history.length === 0}
				class="px-4 py-2 bg-white border-2 border-slate-300 text-slate-700 font-semibold rounded-lg hover:bg-slate-50 hover:border-slate-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow active:scale-95"
				aria-label="Undo last action"
				title="Undo (Ctrl+Z)"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2.5"
						d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
					/>
				</svg>
			</button>

			<!-- Add Item Button -->
			<button
				type="button"
				onclick={addItem}
				{disabled}
				class="px-5 py-2 bg-primary-600 text-white font-bold rounded-lg hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg active:scale-95"
				aria-label="Add new agenda item"
			>
				<span class="flex items-center gap-2">
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2.5"
							d="M12 4v16m8-8H4"
						/>
					</svg>
					<span>항목 추가</span>
				</span>
			</button>
		</div>

		<!-- Merge Button -->
		<button
			type="button"
			onclick={mergeSelected}
			disabled={disabled || selectedItems.size < 2}
			class="px-5 py-2 bg-amber-500 text-white font-bold rounded-lg hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg active:scale-95"
			aria-label="Merge selected items"
		>
			<span class="flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2.5"
						d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
					/>
				</svg>
				<span>병합 ({selectedItems.size})</span>
			</span>
		</button>
	</div>

	<!-- Items List -->
	<div
		class="items-container p-6 bg-white min-h-[400px]"
		use:dndzone={{ items: localItems, dragDisabled, flipDurationMs: 200 }}
		onconsider={handleDndConsider}
		onfinalize={handleDndFinalize}
	>
		{#each localItems as item (item.id)}
			<div
				class="item-card group relative mb-4 last:mb-0 bg-white border-2 border-slate-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all duration-200"
				animate:flip={{ duration: 200 }}
			>
				<!-- Main Item Row -->
				<div class="flex items-start gap-3 p-4 bg-gradient-to-r from-slate-50 to-white">
					<!-- Drag Handle -->
					<button
						type="button"
						class="drag-handle flex-shrink-0 mt-2 p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg cursor-grab active:cursor-grabbing transition-all touch-none"
						aria-label="Drag to reorder"
						onmousedown={startDrag}
						ontouchstart={startDrag}
						tabindex={disabled ? -1 : 0}
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2.5"
								d="M4 6h16M4 12h16M4 18h16"
							/>
						</svg>
					</button>

					<!-- Checkbox -->
					<label class="flex items-center flex-shrink-0 mt-2 cursor-pointer">
						<input
							type="checkbox"
							checked={selectedItems.has(item.id)}
							onchange={() => toggleSelection(item.id)}
							{disabled}
							class="w-5 h-5 text-primary-600 border-2 border-slate-300 rounded focus:ring-2 focus:ring-primary-500 cursor-pointer"
							aria-label="Select item for merging"
						/>
					</label>

					<!-- Title Input -->
					<input
						type="text"
						value={item.title}
						oninput={(e) => updateItem(item.id, 'title', e.currentTarget.value)}
						placeholder="안건 제목을 입력하세요"
						{disabled}
						class="flex-1 px-4 py-2 text-lg font-semibold text-slate-800 bg-transparent border-2 border-transparent rounded-lg focus:border-primary-500 focus:bg-white focus:ring-2 focus:ring-primary-200 transition-all placeholder:text-slate-400"
						aria-label="Item title"
					/>

					<!-- Action Buttons -->
					<div class="flex items-center gap-2 flex-shrink-0">
						<!-- Split Button -->
						<button
							type="button"
							onclick={() => splitItem(item.id)}
							{disabled}
							title="설명을 여러 항목으로 분할"
							class="px-3 py-2 text-sm font-medium text-slate-600 bg-white border-2 border-slate-300 rounded-lg hover:bg-slate-50 hover:border-slate-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm"
							aria-label="Split item into multiple items"
						>
							분할
						</button>

						<!-- Remove Button -->
						<button
							type="button"
							onclick={() => removeItem(item.id)}
							{disabled}
							class="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
							aria-label="Remove item"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2.5"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</div>
				</div>

				<!-- Description Toggle & Content -->
				<div class="description-section">
					<!-- Toggle Button -->
					<button
						type="button"
						onclick={() => toggleExpanded(item.id)}
						class="w-full px-6 py-2 text-left text-sm font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-50 transition-all border-t-2 border-slate-200"
						aria-expanded={expandedItems.has(item.id)}
						aria-label="Toggle description"
					>
						<span class="flex items-center gap-2">
							<svg
								class="w-4 h-4 transition-transform duration-200"
								style="transform: rotate({expandedItems.has(item.id) ? 90 : 0}deg)"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2.5"
									d="M9 5l7 7-7 7"
								/>
							</svg>
							<span>설명 {expandedItems.has(item.id) ? '숨기기' : '보기'}</span>
						</span>
					</button>

					<!-- Description Textarea (Expandable) -->
					{#if expandedItems.has(item.id)}
						<div
							class="description-content p-6 bg-slate-50 border-t-2 border-slate-200 animate-slide-down"
						>
							<textarea
								value={item.description}
								oninput={(e) => updateItem(item.id, 'description', e.currentTarget.value)}
								placeholder="상세 설명을 입력하세요..."
								{disabled}
								rows="4"
								class="w-full px-4 py-3 text-slate-700 bg-white border-2 border-slate-300 rounded-lg focus:border-primary-500 focus:ring-2 focus:ring-primary-200 transition-all placeholder:text-slate-400 resize-vertical"
								aria-label="Item description"
							></textarea>
						</div>
					{/if}
				</div>
			</div>
		{/each}

		{#if localItems.length === 0}
			<div
				class="empty-state flex flex-col items-center justify-center py-16 text-slate-400"
			>
				<svg class="w-20 h-20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="1.5"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
					/>
				</svg>
				<p class="text-lg font-medium">안건이 없습니다</p>
				<p class="text-sm mt-2">상단의 "항목 추가" 버튼을 눌러 안건을 추가하세요</p>
			</div>
		{/if}
	</div>
</div>

<style>
	.agenda-editor {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
	}

	.item-card {
		transition:
			transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
			box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1);
	}

	.item-card:hover {
		transform: translateY(-2px);
	}

	.drag-handle {
		touch-action: none;
		-webkit-user-drag: none;
		user-select: none;
	}

	.drag-handle:active {
		transform: scale(1.1);
	}

	@keyframes slide-down {
		from {
			opacity: 0;
			max-height: 0;
		}
		to {
			opacity: 1;
			max-height: 500px;
		}
	}

	.animate-slide-down {
		animation: slide-down 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}

	/* Touch-friendly adjustments */
	@media (hover: none) and (pointer: coarse) {
		.item-card {
			margin-bottom: 1rem;
		}

		button {
			min-height: 44px;
			min-width: 44px;
		}

		.drag-handle {
			padding: 0.75rem;
		}
	}

	/* Focus styles for accessibility */
	button:focus-visible,
	input:focus-visible,
	textarea:focus-visible {
		outline: 3px solid #3b82f6;
		outline-offset: 2px;
	}

	/* Smooth transitions for drag state */
	.item-card:global(.dragging) {
		opacity: 0.5;
		transform: rotate(2deg) scale(1.02);
	}
</style>
