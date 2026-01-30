<script lang="ts">
	/**
	 * Tabs - Accessible tab component for Phase 4
	 *
	 * Features:
	 * - Keyboard navigation (arrow keys)
	 * - ARIA roles and attributes
	 * - Animated indicator
	 * - Badge support
	 */
	import { tick } from 'svelte';

	interface Tab {
		id: string;
		label: string;
		badge?: number | string;
		icon?: any;
		disabled?: boolean;
	}

	interface Props {
		tabs: Tab[];
		activeTab?: string;
		variant?: 'default' | 'pills' | 'underline';
		size?: 'sm' | 'md' | 'lg';
		onchange?: (tabId: string) => void;
	}

	let {
		tabs,
		activeTab = $bindable(tabs[0]?.id ?? ''),
		variant = 'underline',
		size = 'md',
		onchange
	}: Props = $props();

	let tabRefs: HTMLButtonElement[] = $state([]);
	let indicatorStyle = $state('');

	// Size classes
	const sizeClasses = {
		sm: 'text-sm px-3 py-1.5',
		md: 'text-base px-4 py-2',
		lg: 'text-lg px-5 py-3'
	};

	// Handle tab change
	function selectTab(tabId: string) {
		if (tabs.find(t => t.id === tabId)?.disabled) return;
		activeTab = tabId;
		onchange?.(tabId);
		updateIndicator();
	}

	// Keyboard navigation
	function handleKeyDown(e: KeyboardEvent, index: number) {
		let newIndex = index;

		switch (e.key) {
			case 'ArrowLeft':
			case 'ArrowUp':
				e.preventDefault();
				newIndex = index === 0 ? tabs.length - 1 : index - 1;
				break;
			case 'ArrowRight':
			case 'ArrowDown':
				e.preventDefault();
				newIndex = index === tabs.length - 1 ? 0 : index + 1;
				break;
			case 'Home':
				e.preventDefault();
				newIndex = 0;
				break;
			case 'End':
				e.preventDefault();
				newIndex = tabs.length - 1;
				break;
			default:
				return;
		}

		// Skip disabled tabs
		while (tabs[newIndex]?.disabled && newIndex !== index) {
			if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
				newIndex = newIndex === 0 ? tabs.length - 1 : newIndex - 1;
			} else {
				newIndex = newIndex === tabs.length - 1 ? 0 : newIndex + 1;
			}
		}

		tabRefs[newIndex]?.focus();
		selectTab(tabs[newIndex].id);
	}

	// Update indicator position
	async function updateIndicator() {
		await tick();
		const activeIndex = tabs.findIndex(t => t.id === activeTab);
		const activeRef = tabRefs[activeIndex];

		if (activeRef && variant === 'underline') {
			indicatorStyle = `left: ${activeRef.offsetLeft}px; width: ${activeRef.offsetWidth}px;`;
		}
	}

	$effect(() => {
		activeTab;
		updateIndicator();
	});
</script>

<div
	class="tabs-container relative"
	class:tabs-underline={variant === 'underline'}
	class:tabs-pills={variant === 'pills'}
	class:tabs-default={variant === 'default'}
>
	<div
		class="tabs-list flex"
		class:gap-1={variant === 'pills'}
		class:border-b={variant === 'underline'}
		class:border-gray-200={variant === 'underline'}
		class:dark:border-gray-700={variant === 'underline'}
		role="tablist"
		aria-orientation="horizontal"
	>
		{#each tabs as tab, index (tab.id)}
			<button
				bind:this={tabRefs[index]}
				type="button"
				role="tab"
				id="tab-{tab.id}"
				aria-selected={activeTab === tab.id}
				aria-controls="tabpanel-{tab.id}"
				tabindex={activeTab === tab.id ? 0 : -1}
				disabled={tab.disabled}
				class="tab-button relative flex items-center gap-2 font-medium transition-colors duration-200 {sizeClasses[size]}"
				class:tab-active={activeTab === tab.id}
				class:opacity-50={tab.disabled}
				class:cursor-not-allowed={tab.disabled}
				onclick={() => selectTab(tab.id)}
				onkeydown={(e) => handleKeyDown(e, index)}
			>
				{#if tab.icon}
					<svelte:component this={tab.icon} class="w-4 h-4" />
				{/if}
				<span>{tab.label}</span>
				{#if tab.badge !== undefined}
					<span class="tab-badge min-w-[20px] h-5 px-1.5 text-xs font-semibold rounded-full flex items-center justify-center">
						{tab.badge}
					</span>
				{/if}
			</button>
		{/each}
	</div>

	<!-- Animated indicator for underline variant -->
	{#if variant === 'underline'}
		<div
			class="tab-indicator absolute bottom-0 h-0.5 bg-primary-600 dark:bg-primary-400 transition-all duration-200"
			style={indicatorStyle}
		></div>
	{/if}
</div>

<style>
	/* Underline variant */
	.tabs-underline .tab-button {
		@apply text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100;
		@apply border-b-2 border-transparent -mb-px;
	}
	.tabs-underline .tab-button.tab-active {
		@apply text-primary-600 dark:text-primary-400;
	}
	.tabs-underline .tab-badge {
		@apply bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300;
	}
	.tabs-underline .tab-button.tab-active .tab-badge {
		@apply bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300;
	}

	/* Pills variant */
	.tabs-pills .tab-button {
		@apply rounded-lg text-gray-600 dark:text-gray-400;
		@apply hover:bg-gray-100 dark:hover:bg-gray-800;
	}
	.tabs-pills .tab-button.tab-active {
		@apply bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300;
	}
	.tabs-pills .tab-badge {
		@apply bg-white dark:bg-gray-800;
	}

	/* Default variant */
	.tabs-default .tab-button {
		@apply text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100;
	}
	.tabs-default .tab-button.tab-active {
		@apply text-gray-900 dark:text-gray-100 font-semibold;
	}
</style>
