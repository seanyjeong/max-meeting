<script lang="ts" module>
	export interface AgendaItem {
		id: string;
		title: string;
		description: string;
		children?: AgendaItem[];
	}
</script>

<script lang="ts">
	import { Undo2, Plus, Lightbulb, ClipboardList, ChevronRight, ChevronUp, ChevronDown, ArrowLeft, ArrowRight, FolderClosed, Trash2 } from 'lucide-svelte';

	interface Props {
		items: AgendaItem[];
		onItemsChange: (items: AgendaItem[]) => void;
		disabled?: boolean;
	}

	let { items, onItemsChange, disabled = false }: Props = $props();

	// Internal state - deep copy of items
	let internalItems = $state<AgendaItem[]>([]);

	// Sync internal state when prop changes
	$effect(() => {
		console.log('[AgendaEditor] Syncing from prop, items:', items?.length ?? 0);
		internalItems = JSON.parse(JSON.stringify(items || []));
	});

	// Helper to ensure children array exists
	function getChildren(item: AgendaItem): AgendaItem[] {
		return item.children ?? [];
	}

	// Collapsed state tracking
	let collapsedItems = $state<Set<string>>(new Set());

	// Undo history
	let history = $state<AgendaItem[][]>([]);
	const MAX_HISTORY = 20;

	function saveHistory() {
		history = [...history.slice(-MAX_HISTORY + 1), JSON.parse(JSON.stringify(internalItems))];
	}

	function notifyChange() {
		console.log('[AgendaEditor] notifyChange called, internalItems:', internalItems.length);
		onItemsChange(JSON.parse(JSON.stringify(internalItems)));
	}

	function undo() {
		if (history.length === 0) return;
		const previousState = history[history.length - 1];
		history = history.slice(0, -1);
		internalItems = previousState;
		notifyChange();
	}

	function handleKeyDown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
			e.preventDefault();
			undo();
		}
	}

	function addRootItem() {
		saveHistory();
		const newItem: AgendaItem = {
			id: crypto.randomUUID(),
			title: '',
			description: '',
			children: []
		};
		internalItems = [...internalItems, newItem];
		notifyChange();
	}

	function addChildTo(parentId: string) {
		console.log('[AgendaEditor] addChildTo called, parentId:', parentId);
		saveHistory();
		const newChild: AgendaItem = {
			id: crypto.randomUUID(),
			title: '',
			description: '',
			children: []
		};

		function addChild(itemList: AgendaItem[]): AgendaItem[] {
			return itemList.map((item) => {
				if (item.id === parentId) {
					console.log('[AgendaEditor] Found parent, adding child');
					// Expand parent when adding child
					collapsedItems = new Set([...collapsedItems].filter((x) => x !== parentId));
					return { ...item, children: [...getChildren(item), newChild] };
				}
				if (getChildren(item).length > 0) {
					return { ...item, children: addChild(getChildren(item)) };
				}
				return item;
			});
		}

		internalItems = addChild(internalItems);
		console.log('[AgendaEditor] After addChild, internalItems:', JSON.stringify(internalItems));
		notifyChange();
	}

	function removeItem(targetId: string) {
		saveHistory();

		function remove(itemList: AgendaItem[]): AgendaItem[] {
			return itemList
				.filter((item) => item.id !== targetId)
				.map((item) => ({
					...item,
					children: remove(getChildren(item))
				}));
		}

		internalItems = remove(internalItems);
		notifyChange();
	}

	function updateItem(targetId: string, field: 'title' | 'description', value: string) {
		function update(itemList: AgendaItem[]): AgendaItem[] {
			return itemList.map((item) => {
				if (item.id === targetId) {
					return { ...item, [field]: value };
				}
				if (getChildren(item).length > 0) {
					return { ...item, children: update(getChildren(item)) };
				}
				return item;
			});
		}

		internalItems = update(internalItems);
		notifyChange();
	}

	function toggleCollapse(id: string) {
		if (collapsedItems.has(id)) {
			collapsedItems = new Set([...collapsedItems].filter((x) => x !== id));
		} else {
			collapsedItems = new Set([...collapsedItems, id]);
		}
	}

	function moveUp(targetId: string, parentList: AgendaItem[]): boolean {
		const index = parentList.findIndex((item) => item.id === targetId);
		if (index > 0) {
			saveHistory();
			[parentList[index - 1], parentList[index]] = [parentList[index], parentList[index - 1]];
			internalItems = [...internalItems];
			notifyChange();
			return true;
		}
		return false;
	}

	function moveDown(targetId: string, parentList: AgendaItem[]): boolean {
		const index = parentList.findIndex((item) => item.id === targetId);
		if (index >= 0 && index < parentList.length - 1) {
			saveHistory();
			[parentList[index], parentList[index + 1]] = [parentList[index + 1], parentList[index]];
			internalItems = [...internalItems];
			notifyChange();
			return true;
		}
		return false;
	}

	// Promote: Move item to parent level (become sibling of parent)
	function promoteItem(targetId: string) {
		saveHistory();

		function findAndPromote(
			itemList: AgendaItem[],
			parent: AgendaItem | null,
			grandparentList: AgendaItem[] | null
		): AgendaItem[] {
			for (let i = 0; i < itemList.length; i++) {
				const item = itemList[i];
				if (item.id === targetId && parent && grandparentList) {
					// Remove from current location
					itemList.splice(i, 1);
					// Add after parent in grandparent list
					const parentIndex = grandparentList.findIndex((p) => p.id === parent.id);
					grandparentList.splice(parentIndex + 1, 0, item);
					return itemList;
				}
				if (getChildren(item).length > 0) {
					item.children = findAndPromote(getChildren(item), item, itemList);
				}
			}
			return itemList;
		}

		internalItems = findAndPromote(internalItems, null, null);
		notifyChange();
	}

	// Demote: Make item a child of the previous sibling
	function demoteItem(targetId: string, parentList: AgendaItem[]) {
		const index = parentList.findIndex((item) => item.id === targetId);
		if (index <= 0) return; // Can't demote first item

		saveHistory();
		const item = parentList[index];
		const newParent = parentList[index - 1];

		// Remove from current position
		parentList.splice(index, 1);
		// Add as child of previous sibling
		newParent.children = [...getChildren(newParent), item];
		// Expand the new parent
		collapsedItems = new Set([...collapsedItems].filter((x) => x !== newParent.id));

		internalItems = [...internalItems];
		notifyChange();
	}
</script>

<svelte:window onkeydown={handleKeyDown} />

<div class="agenda-editor w-full max-w-4xl mx-auto">
	<!-- Toolbar -->
	<div class="flex items-center gap-3 p-4 bg-slate-100 border-b-2 border-slate-200 rounded-t-xl">
		<button
			type="button"
			onclick={undo}
			disabled={disabled || history.length === 0}
			class="px-3 py-2 bg-white border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 disabled:opacity-40 transition-all"
			title="되돌리기 (Ctrl+Z)"
		>
			<Undo2 class="w-4 h-4 inline mr-1" />
			되돌리기
		</button>

		<button
			type="button"
			onclick={addRootItem}
			{disabled}
			class="px-4 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-all"
		>
			<Plus class="w-4 h-4 inline mr-1" />
			안건 추가
		</button>

		<div class="ml-auto text-sm text-slate-500 flex items-center gap-1">
			<Lightbulb class="w-4 h-4" />
			하위 항목은 각 안건의 "+하위" 버튼으로 추가
		</div>
	</div>

	<!-- Tree View -->
	<div class="bg-white border-2 border-t-0 border-slate-200 rounded-b-xl p-4 min-h-[300px]">
		{#if internalItems.length === 0}
			<div class="flex flex-col items-center justify-center py-16 text-slate-400">
				<ClipboardList class="w-12 h-12 mb-4" />
				<p class="text-lg font-medium">안건이 없습니다</p>
				<p class="text-sm mt-2">위의 "안건 추가" 버튼을 눌러 시작하세요</p>
			</div>
		{:else}
			{#each internalItems as item, index (item.id)}
				{@render treeNode(item, internalItems, 0, index, `${index + 1}`)}
			{/each}
		{/if}
	</div>
</div>

{#snippet treeNode(item: AgendaItem, parentList: AgendaItem[], depth: number, index: number, numberPrefix: string)}
	{@const children = getChildren(item)}
	<div class="tree-item" style="--depth: {depth}">
		<!-- Main Item -->
		<div
			class="item-box mb-2 rounded-lg border-2 transition-all {depth === 0
				? 'border-slate-300 bg-white shadow-sm'
				: 'border-blue-200 bg-blue-50/50'}"
		>
			<!-- Header Row -->
			<div class="flex items-center gap-2 p-3">
				<!-- Collapse Toggle (if has children) -->
				{#if children.length > 0}
					<button
						type="button"
						onclick={() => toggleCollapse(item.id)}
						class="w-6 h-6 flex items-center justify-center text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded transition-all"
						title={collapsedItems.has(item.id) ? '펼치기' : '접기'}
					>
						<ChevronRight
							class="w-4 h-4 transform transition-transform {collapsedItems.has(item.id)
								? 'rotate-0'
								: 'rotate-90'}"
						/>
					</button>
				{:else}
					<div class="w-6 h-6 flex items-center justify-center text-slate-300">
						{#if depth > 0}└{:else}•{/if}
					</div>
				{/if}

				<!-- Number Badge -->
				<span
					class="flex-shrink-0 px-2 py-0.5 text-sm font-bold rounded {depth === 0
						? 'bg-slate-700 text-white'
						: 'bg-blue-100 text-blue-700'}"
				>
					{numberPrefix}.
				</span>

				<!-- Title Input -->
				<input
					type="text"
					value={item.title}
					oninput={(e) => updateItem(item.id, 'title', e.currentTarget.value)}
					placeholder={depth === 0 ? '안건 제목을 입력하세요' : '하위 항목 제목'}
					{disabled}
					class="flex-1 px-3 py-1.5 text-base font-medium bg-transparent border border-transparent rounded-lg focus:border-blue-400 focus:bg-white focus:outline-none transition-all"
				/>

				<!-- Action Buttons -->
				<div class="flex items-center gap-1">
					<!-- Move Up -->
					<button
						type="button"
						onclick={() => moveUp(item.id, parentList)}
						disabled={disabled || index === 0}
						class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded disabled:opacity-30 transition-all"
						title="위로 이동"
					>
						<ChevronUp class="w-4 h-4" />
					</button>

					<!-- Move Down -->
					<button
						type="button"
						onclick={() => moveDown(item.id, parentList)}
						disabled={disabled || index === parentList.length - 1}
						class="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded disabled:opacity-30 transition-all"
						title="아래로 이동"
					>
						<ChevronDown class="w-4 h-4" />
					</button>

					<!-- Promote (move to parent level) -->
					{#if depth > 0}
						<button
							type="button"
							onclick={() => promoteItem(item.id)}
							{disabled}
							class="p-1.5 text-blue-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-all"
							title="상위 레벨로 이동"
						>
							<ArrowLeft class="w-4 h-4" />
						</button>
					{/if}

					<!-- Demote (make child of previous sibling) -->
					{#if index > 0}
						<button
							type="button"
							onclick={() => demoteItem(item.id, parentList)}
							{disabled}
							class="p-1.5 text-blue-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-all"
							title="이전 항목의 하위로 이동"
						>
							<ArrowRight class="w-4 h-4" />
						</button>
					{/if}

					<!-- Add Child -->
					<button
						type="button"
						onclick={() => addChildTo(item.id)}
						{disabled}
						class="px-2 py-1 text-xs font-semibold text-green-600 hover:text-green-700 hover:bg-green-50 rounded transition-all"
						title="하위 항목 추가"
					>
						<Plus class="w-3 h-3 inline mr-0.5" />하위
					</button>

					<!-- Delete -->
					<button
						type="button"
						onclick={() => removeItem(item.id)}
						{disabled}
						class="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded transition-all"
						title="삭제"
					>
						<Trash2 class="w-4 h-4" />
					</button>
				</div>
			</div>

			<!-- Description (always visible, collapsible) -->
			<div class="px-3 pb-3">
				<textarea
					value={item.description}
					oninput={(e) => updateItem(item.id, 'description', e.currentTarget.value)}
					placeholder="상세 설명 (선택사항)"
					{disabled}
					rows="2"
					class="w-full px-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:border-blue-400 focus:bg-white focus:outline-none transition-all resize-none"
				></textarea>
			</div>
		</div>

		<!-- Children (nested) -->
		{#if children.length > 0 && !collapsedItems.has(item.id)}
			<div class="children-container ml-6 pl-4 border-l-2 border-blue-200">
				{#each children as child, childIndex (child.id)}
					{@render treeNode(child, children, depth + 1, childIndex, `${numberPrefix}.${childIndex + 1}`)}
				{/each}
			</div>
		{/if}

		<!-- Collapsed indicator -->
		{#if children.length > 0 && collapsedItems.has(item.id)}
			<div class="ml-8 mb-2 text-sm text-slate-400 italic flex items-center gap-1">
				<FolderClosed class="w-4 h-4" />
				{children.length}개 하위 항목 (클릭하여 펼치기)
			</div>
		{/if}
	</div>
{/snippet}

<style>
	.agenda-editor {
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif;
	}

	.tree-item {
		position: relative;
	}

	.children-container {
		position: relative;
	}

	/* Tree line effect */
	.children-container::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0;
		bottom: 0;
		width: 2px;
		background: linear-gradient(to bottom, #bfdbfe, #dbeafe);
	}

	button:focus-visible,
	input:focus-visible,
	textarea:focus-visible {
		outline: 2px solid #3b82f6;
		outline-offset: 2px;
	}

	/* iPad touch targets */
	@media (hover: none) and (pointer: coarse) {
		button {
			min-height: 44px;
			min-width: 44px;
		}
	}
</style>
