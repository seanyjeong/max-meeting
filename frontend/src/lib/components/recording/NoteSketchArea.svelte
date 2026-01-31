<script lang="ts">
	import { onDestroy } from 'svelte';
	import TldrawWrapper from '$lib/components/sketch/TldrawWrapper.svelte';
	import TaskAssignment from './TaskAssignment.svelte';

	interface Props {
		activeTab: 'memo' | 'pen' | 'task';
		textContent: string;
		sketchSnapshot: any;
		meetingId: number;
		onTabChange: (tab: 'memo' | 'pen' | 'task') => void;
		onTextChange: (content: string) => void;
		onSketchChange: (snapshot: any) => void;
	}

	let {
		activeTab = $bindable(),
		textContent = '',
		sketchSnapshot,
		meetingId,
		onTabChange,
		onTextChange,
		onSketchChange
	}: Props = $props();

	let tldrawRef: TldrawWrapper | null = null;
	let textDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	// Cleanup on destroy
	onDestroy(() => {
		if (textDebounceTimer) {
			clearTimeout(textDebounceTimer);
		}
	});

	// Handle tab switching
	function switchTab(tab: 'memo' | 'pen' | 'task') {
		activeTab = tab;
		onTabChange(tab);
	}

	// Handle text input with debounce
	function handleTextInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		const content = target.value;

		// Clear existing timer
		if (textDebounceTimer) {
			clearTimeout(textDebounceTimer);
		}

		// Debounce text save (500ms)
		textDebounceTimer = setTimeout(() => {
			onTextChange(content);
			textDebounceTimer = null;
		}, 500);
	}

	// Handle sketch changes
	function handleSketchChange() {
		if (!tldrawRef) return;
		const snapshot = tldrawRef.getSnapshot();
		if (snapshot) {
			onSketchChange(snapshot);
		}
	}

	// Auto-switch to pen tab when pencil detected
	function handlePencilDetected() {
		if (activeTab !== 'pen') {
			switchTab('pen');
		}
	}

	// Tab button classes
	function getTabButtonClass(tab: 'memo' | 'pen' | 'task'): string {
		const baseClass =
			'flex-1 h-11 flex items-center justify-center gap-1.5 text-sm font-medium transition-all duration-200 relative';
		const activeClass =
			'text-blue-600 after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-blue-600';
		const inactiveClass = 'text-gray-600 hover:text-gray-900 hover:bg-gray-50';

		return `${baseClass} ${activeTab === tab ? activeClass : inactiveClass}`;
	}
</script>

<div class="flex flex-col h-full min-h-0 bg-white">
	<!-- Tab buttons -->
	<div class="flex border-b border-gray-200">
		<button
			type="button"
			onclick={() => switchTab('memo')}
			class={getTabButtonClass('memo')}
			aria-selected={activeTab === 'memo'}
			role="tab"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
			</svg>
			메모
		</button>
		<button
			type="button"
			onclick={() => switchTab('pen')}
			class={getTabButtonClass('pen')}
			aria-selected={activeTab === 'pen'}
			role="tab"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
			</svg>
			필기
		</button>
		<button
			type="button"
			onclick={() => switchTab('task')}
			class={getTabButtonClass('task')}
			aria-selected={activeTab === 'task'}
			role="tab"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
			</svg>
			업무배치
		</button>
	</div>

	<!-- Tab content -->
	<div class="flex-1 min-h-0 overflow-hidden" role="tabpanel">
		{#if activeTab === 'memo'}
			<!-- Memo tab -->
			<textarea
				value={textContent}
				oninput={handleTextInput}
				placeholder="회의 메모를 작성하세요..."
				class="w-full h-full p-4 text-base text-gray-900 placeholder-gray-400 border-0 resize-none focus:ring-0 focus:outline-none"
				style="line-height: 1.75; overflow-y: auto;"
			></textarea>
		{:else if activeTab === 'pen'}
			<!-- Pen/Sketch tab -->
			<div class="w-full h-full">
				<TldrawWrapper
					bind:this={tldrawRef}
					height="100%"
					width="100%"
					initialSnapshot={sketchSnapshot}
					onEditorChange={handleSketchChange}
					onPencilDetected={handlePencilDetected}
					autoFocus={true}
				/>
			</div>
		{:else if activeTab === 'task'}
			<!-- Task Assignment tab -->
			<TaskAssignment {meetingId} />
		{/if}
	</div>
</div>

<style>
	/* Ensure textarea fills container properly */
	textarea {
		display: block;
		line-height: 1.5;
	}

	/* Tab button active indicator */
	button[aria-selected='true']::after {
		content: '';
	}

	/* Touch-friendly tap targets */
	button[role='tab'] {
		min-height: 44px;
		-webkit-tap-highlight-color: transparent;
	}

	/* Prevent text selection on tab buttons */
	button[role='tab'] {
		user-select: none;
		-webkit-user-select: none;
	}
</style>
