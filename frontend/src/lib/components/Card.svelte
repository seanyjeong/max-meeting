<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		padding?: boolean;
		class?: string;
		children: Snippet;
	}

	let {
		padding = true,
		class: className = '',
		children
	}: Props = $props();
</script>

<div class="bg-white rounded-lg shadow-sm {padding ? 'p-6' : ''} {className}">
	{@render children()}
</div>
