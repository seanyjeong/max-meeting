<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'gray' | 'red' | 'yellow' | 'green' | 'blue' | 'purple';
		size?: 'sm' | 'md';
		children: Snippet;
	}

	let {
		variant = 'gray',
		size = 'sm',
		children
	}: Props = $props();

	const variantClasses = {
		gray: 'bg-gray-100 text-gray-800',
		red: 'bg-red-100 text-red-800',
		yellow: 'bg-yellow-100 text-yellow-800',
		green: 'bg-green-100 text-green-800',
		blue: 'bg-blue-100 text-blue-800',
		purple: 'bg-purple-100 text-purple-800'
	};

	const sizeClasses = {
		sm: 'px-2 py-0.5 text-xs',
		md: 'px-2.5 py-1 text-sm'
	};
</script>

<span
	class="inline-flex items-center rounded-full font-medium {variantClasses[variant]} {sizeClasses[size]}"
>
	{@render children()}
</span>
