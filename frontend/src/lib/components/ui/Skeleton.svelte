<script lang="ts">
	/**
	 * Skeleton - Loading placeholder component
	 *
	 * Variants:
	 * - text: Single line of text
	 * - circle: Avatar or icon placeholder
	 * - rect: Rectangle for images or cards
	 * - card: Full card skeleton
	 * - list: List item skeleton
	 */

	interface Props {
		variant?: 'text' | 'circle' | 'rect' | 'card' | 'list';
		width?: string;
		height?: string;
		lines?: number;
		animate?: boolean;
		class?: string;
	}

	let {
		variant = 'text',
		width = '100%',
		height = 'auto',
		lines = 1,
		animate = true,
		class: className = ''
	}: Props = $props();

	// Default dimensions based on variant
	const dimensions = $derived.by(() => {
		switch (variant) {
			case 'circle':
				return { w: '48px', h: '48px' };
			case 'rect':
				return { w: width, h: height || '120px' };
			case 'card':
				return { w: '100%', h: 'auto' };
			case 'list':
				return { w: '100%', h: 'auto' };
			default:
				return { w: width, h: '16px' };
		}
	});
</script>

{#if variant === 'text'}
	<div class="flex flex-col gap-2" style="width: {width}">
		{#each Array(lines) as _, i}
			<div
				class="skeleton rounded {className}"
				class:animate-pulse={animate}
				style="height: {height || '16px'}; width: {i === lines - 1 && lines > 1 ? '75%' : '100%'}"
			></div>
		{/each}
	</div>

{:else if variant === 'circle'}
	<div
		class="skeleton rounded-full {className}"
		class:animate-pulse={animate}
		style="width: {width || dimensions.w}; height: {height || dimensions.h}"
	></div>

{:else if variant === 'rect'}
	<div
		class="skeleton rounded-lg {className}"
		class:animate-pulse={animate}
		style="width: {dimensions.w}; height: {dimensions.h}"
	></div>

{:else if variant === 'card'}
	<div class="bg-white dark:bg-surface rounded-2xl shadow-soft p-6 {className}">
		<!-- Header -->
		<div class="flex items-center gap-3 mb-4">
			<div
				class="skeleton rounded-full"
				class:animate-pulse={animate}
				style="width: 40px; height: 40px"
			></div>
			<div class="flex-1 space-y-2">
				<div
					class="skeleton rounded"
					class:animate-pulse={animate}
					style="height: 14px; width: 60%"
				></div>
				<div
					class="skeleton rounded"
					class:animate-pulse={animate}
					style="height: 12px; width: 40%"
				></div>
			</div>
		</div>

		<!-- Content -->
		<div class="space-y-3">
			<div
				class="skeleton rounded"
				class:animate-pulse={animate}
				style="height: 16px; width: 100%"
			></div>
			<div
				class="skeleton rounded"
				class:animate-pulse={animate}
				style="height: 16px; width: 90%"
			></div>
			<div
				class="skeleton rounded"
				class:animate-pulse={animate}
				style="height: 16px; width: 75%"
			></div>
		</div>

		<!-- Footer -->
		<div class="flex gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
			<div
				class="skeleton rounded-lg"
				class:animate-pulse={animate}
				style="height: 36px; width: 80px"
			></div>
			<div
				class="skeleton rounded-lg"
				class:animate-pulse={animate}
				style="height: 36px; width: 80px"
			></div>
		</div>
	</div>

{:else if variant === 'list'}
	<div class="flex items-center gap-3 p-4 {className}">
		<div
			class="skeleton rounded-full flex-shrink-0"
			class:animate-pulse={animate}
			style="width: 40px; height: 40px"
		></div>
		<div class="flex-1 min-w-0 space-y-2">
			<div
				class="skeleton rounded"
				class:animate-pulse={animate}
				style="height: 14px; width: 70%"
			></div>
			<div
				class="skeleton rounded"
				class:animate-pulse={animate}
				style="height: 12px; width: 50%"
			></div>
		</div>
		<div
			class="skeleton rounded flex-shrink-0"
			class:animate-pulse={animate}
			style="width: 60px; height: 24px"
		></div>
	</div>
{/if}

<style>
	.skeleton {
		@apply bg-gray-200 dark:bg-surface-light;
	}
</style>
