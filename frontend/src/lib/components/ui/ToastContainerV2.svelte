<script lang="ts">
	/**
	 * ToastContainerV2 - Enhanced toast container
	 *
	 * Features:
	 * - Stacked toasts with max visible limit
	 * - Position variants
	 * - Grouped notifications
	 */
	import { toast, type ToastMessage } from '$lib/stores/toast';
	import ToastV2 from './ToastV2.svelte';
	import { flip } from 'svelte/animate';

	interface Props {
		position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center' | 'bottom-center';
		maxVisible?: number;
	}

	let {
		position = 'bottom-right',
		maxVisible = 5
	}: Props = $props();

	let toasts = $derived($toast);
	let visibleToasts = $derived(toasts.slice(-maxVisible));
	let hiddenCount = $derived(Math.max(0, toasts.length - maxVisible));

	// Position classes
	const positionClasses = {
		'top-right': 'top-4 right-4',
		'top-left': 'top-4 left-4',
		'bottom-right': 'bottom-4 right-4',
		'bottom-left': 'bottom-4 left-4',
		'top-center': 'top-4 left-1/2 -translate-x-1/2',
		'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2'
	};
</script>

<div
	class="fixed z-50 flex flex-col gap-2 w-full max-w-sm pointer-events-none {positionClasses[position]}"
	aria-live="polite"
	aria-atomic="false"
>
	<!-- Hidden count indicator -->
	{#if hiddenCount > 0}
		<div class="text-xs text-center text-gray-500 dark:text-gray-400 pointer-events-auto">
			+{hiddenCount}개의 알림이 더 있습니다
		</div>
	{/if}

	<!-- Toast list -->
	{#each visibleToasts as toastMessage (toastMessage.id)}
		<div class="pointer-events-auto" animate:flip={{ duration: 200 }}>
			<ToastV2
				id={toastMessage.id}
				message={toastMessage.message}
				type={toastMessage.type}
				duration={toastMessage.duration}
				onclose={() => toast.dismiss(toastMessage.id)}
			/>
		</div>
	{/each}
</div>
