<script lang="ts">
	/**
	 * EmptyState - Empty state placeholder component
	 *
	 * Use when:
	 * - No data available
	 * - Search returns no results
	 * - User needs to take action
	 */
	import { FileQuestion, Search, Plus, Inbox } from 'lucide-svelte';
	import type { Component } from 'svelte';

	interface Props {
		variant?: 'default' | 'search' | 'create' | 'inbox';
		title?: string;
		description?: string;
		icon?: Component;
		action?: {
			label: string;
			onClick: () => void;
		};
	}

	let {
		variant = 'default',
		title,
		description,
		icon,
		action
	}: Props = $props();

	// Variant defaults
	const variants = {
		default: {
			icon: FileQuestion,
			title: '데이터가 없습니다',
			description: '표시할 내용이 없습니다.'
		},
		search: {
			icon: Search,
			title: '검색 결과 없음',
			description: '다른 검색어로 시도해보세요.'
		},
		create: {
			icon: Plus,
			title: '시작하기',
			description: '새 항목을 만들어보세요.'
		},
		inbox: {
			icon: Inbox,
			title: '목록이 비어있습니다',
			description: '새 항목이 여기에 표시됩니다.'
		}
	};

	const config = $derived(variants[variant]);
	const displayIcon = $derived(icon || config.icon);
	const displayTitle = $derived(title || config.title);
	const displayDescription = $derived(description || config.description);
</script>

<div class="empty-state flex flex-col items-center justify-center py-12 px-6 text-center">
	<!-- Icon -->
	<div class="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
		<svelte:component this={displayIcon} class="w-8 h-8 text-gray-400 dark:text-gray-500" />
	</div>

	<!-- Title -->
	<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
		{displayTitle}
	</h3>

	<!-- Description -->
	<p class="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
		{displayDescription}
	</p>

	<!-- Action button -->
	{#if action}
		<button
			type="button"
			class="btn btn-primary"
			onclick={action.onClick}
		>
			{action.label}
		</button>
	{/if}
</div>
