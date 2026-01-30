<script lang="ts">
	/**
	 * KeyboardShortcuts - Keyboard shortcut handler and help modal
	 *
	 * Features:
	 * - Global keyboard shortcut handling
	 * - Help modal (press ?)
	 * - Customizable shortcuts per page
	 */
	import { onMount, onDestroy } from 'svelte';
	import { Command, Keyboard } from 'lucide-svelte';

	interface Shortcut {
		key: string;
		modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[];
		description: string;
		action: () => void;
		category?: string;
	}

	interface Props {
		shortcuts?: Shortcut[];
		showHelp?: boolean;
		disabled?: boolean;
	}

	let {
		shortcuts = [],
		showHelp = $bindable(false),
		disabled = false
	}: Props = $props();

	// Default shortcuts
	const defaultShortcuts: Shortcut[] = [
		{
			key: '?',
			description: '단축키 도움말 표시',
			action: () => showHelp = !showHelp,
			category: '일반'
		},
		{
			key: 'Escape',
			description: '모달 닫기',
			action: () => showHelp = false,
			category: '일반'
		}
	];

	const allShortcuts = $derived([...defaultShortcuts, ...shortcuts]);

	// Group shortcuts by category
	const shortcutsByCategory = $derived.by(() => {
		const groups: Record<string, Shortcut[]> = {};
		for (const shortcut of allShortcuts) {
			const category = shortcut.category || '기타';
			if (!groups[category]) groups[category] = [];
			groups[category].push(shortcut);
		}
		return groups;
	});

	function handleKeyDown(e: KeyboardEvent) {
		if (disabled) return;

		// Don't capture shortcuts when typing in inputs
		const target = e.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
			// Allow Escape in inputs
			if (e.key !== 'Escape') return;
		}

		for (const shortcut of allShortcuts) {
			const modifiersMatch =
				(!shortcut.modifiers || shortcut.modifiers.length === 0) ||
				shortcut.modifiers.every(mod => {
					switch (mod) {
						case 'ctrl': return e.ctrlKey;
						case 'alt': return e.altKey;
						case 'shift': return e.shiftKey;
						case 'meta': return e.metaKey;
						default: return false;
					}
				});

			if (e.key === shortcut.key && modifiersMatch) {
				e.preventDefault();
				shortcut.action();
				break;
			}
		}
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);
	});

	// Format shortcut key for display
	function formatKey(shortcut: Shortcut): string {
		const parts: string[] = [];
		if (shortcut.modifiers) {
			if (shortcut.modifiers.includes('meta')) parts.push('⌘');
			if (shortcut.modifiers.includes('ctrl')) parts.push('Ctrl');
			if (shortcut.modifiers.includes('alt')) parts.push('Alt');
			if (shortcut.modifiers.includes('shift')) parts.push('Shift');
		}
		parts.push(shortcut.key.length === 1 ? shortcut.key.toUpperCase() : shortcut.key);
		return parts.join(' + ');
	}
</script>

<!-- Help Modal -->
{#if showHelp}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
		onclick={() => showHelp = false}
		onkeydown={(e) => e.key === 'Escape' && (showHelp = false)}
		role="dialog"
		aria-modal="true"
		aria-labelledby="shortcuts-title"
	>
		<div
			class="bg-white dark:bg-surface rounded-2xl shadow-strong max-w-lg w-full mx-4 max-h-[80vh] overflow-hidden"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="document"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-2">
					<Keyboard class="w-5 h-5 text-gray-500 dark:text-gray-400" />
					<h2 id="shortcuts-title" class="text-lg font-semibold text-gray-900 dark:text-white">
						키보드 단축키
					</h2>
				</div>
				<button
					type="button"
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					onclick={() => showHelp = false}
					aria-label="닫기"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="p-4 overflow-y-auto max-h-[60vh]">
				{#each Object.entries(shortcutsByCategory) as [category, categoryShortcuts]}
					<div class="mb-4 last:mb-0">
						<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
							{category}
						</h3>
						<div class="space-y-2">
							{#each categoryShortcuts as shortcut}
								<div class="flex items-center justify-between py-2">
									<span class="text-sm text-gray-700 dark:text-gray-300">
										{shortcut.description}
									</span>
									<kbd class="inline-flex items-center gap-1 px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700">
										{formatKey(shortcut)}
									</kbd>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			</div>

			<!-- Footer -->
			<div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-base">
				<p class="text-xs text-center text-gray-500 dark:text-gray-400">
					<kbd class="px-1.5 py-0.5 bg-white dark:bg-surface rounded border border-gray-200 dark:border-gray-700">?</kbd>
					를 눌러 이 도움말을 다시 볼 수 있습니다
				</p>
			</div>
		</div>
	</div>
{/if}
