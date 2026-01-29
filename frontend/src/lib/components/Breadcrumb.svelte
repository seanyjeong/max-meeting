<script lang="ts">
	interface BreadcrumbItem {
		label: string;
		href?: string;
	}

	interface Props {
		items: BreadcrumbItem[];
	}

	let { items }: Props = $props();

	function isLastItem(index: number): boolean {
		return index === items.length - 1;
	}
</script>

<nav class="text-sm text-gray-600" aria-label="Breadcrumb">
	<ol class="flex items-center space-x-1 sm:space-x-2">
		<!-- Home item -->
		<li class="flex items-center">
			<a href="/" class="inline-flex items-center gap-1.5 hover:text-gray-900 transition-colors">
				<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
					<path
						d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"
					/>
				</svg>
				<span class="hidden sm:inline">Home</span>
			</a>
		</li>

		<!-- Breadcrumb items -->
		{#each items as item, index (index)}
			<li class="flex items-center">
				<span class="mx-1 sm:mx-2 text-gray-400">/</span>
				{#if item.href && !isLastItem(index)}
					<a
						href={item.href}
						class="text-gray-600 hover:text-gray-900 transition-colors truncate"
						title={item.label}
					>
						{item.label}
					</a>
				{:else}
					<span
						class={isLastItem(index) ? 'text-gray-900 font-medium truncate' : 'text-gray-600 truncate'}
						title={item.label}
					>
						{item.label}
					</span>
				{/if}
			</li>
		{/each}
	</ol>
</nav>
