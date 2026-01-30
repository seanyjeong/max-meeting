<script lang="ts">
	import { onDestroy } from 'svelte';
	import TldrawWrapper from '$lib/components/sketch/TldrawWrapper.svelte';

	interface Props {
		activeTab: 'text' | 'sketch';
		textContent: string;
		sketchSnapshot: any;
		onTabChange: (tab: 'text' | 'sketch') => void;
		onTextChange: (content: string) => void;
		onSketchChange: (snapshot: any) => void;
	}

	let {
		activeTab = $bindable(),
		textContent = '',
		sketchSnapshot,
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
	function switchTab(tab: 'text' | 'sketch') {
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

	// Auto-switch to sketch tab when pencil detected
	function handlePencilDetected() {
		if (activeTab !== 'sketch') {
			switchTab('sketch');
		}
	}

	// Tab button classes
	function getTabButtonClass(tab: 'text' | 'sketch'): string {
		const baseClass =
			'flex-1 h-11 flex items-center justify-center text-sm font-medium transition-all duration-200 relative';
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
			onclick={() => switchTab('text')}
			class={getTabButtonClass('text')}
			aria-selected={activeTab === 'text'}
			role="tab"
		>
			텍스트
		</button>
		<button
			type="button"
			onclick={() => switchTab('sketch')}
			class={getTabButtonClass('sketch')}
			aria-selected={activeTab === 'sketch'}
			role="tab"
		>
			스케치
		</button>
	</div>

	<!-- Tab content -->
	<div class="flex-1 min-h-0 overflow-hidden" role="tabpanel">
		{#if activeTab === 'text'}
			<!-- Text tab -->
			<textarea
				value={textContent}
				oninput={handleTextInput}
				placeholder="회의 노트를 작성하세요..."
				class="w-full h-full p-4 text-base text-gray-900 placeholder-gray-400 border-0 resize-none focus:ring-0 focus:outline-none"
				style="line-height: 1.75; overflow-y: auto;"
			></textarea>
		{:else if activeTab === 'sketch'}
			<!-- Sketch tab -->
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
