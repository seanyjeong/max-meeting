<script lang="ts">
	/**
	 * ToastV2 - Enhanced toast notification component
	 *
	 * Features:
	 * - Improved animations (slide + fade)
	 * - Progress bar for auto-dismiss
	 * - Action button support
	 * - Stacking with max visible limit
	 * - Touch swipe to dismiss
	 */
	import { fly, fade } from 'svelte/transition';
	import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-svelte';

	interface Props {
		id: string;
		message: string;
		type?: 'success' | 'error' | 'warning' | 'info';
		duration?: number;
		action?: {
			label: string;
			onClick: () => void;
		};
		onclose?: () => void;
	}

	let {
		id,
		message,
		type = 'info',
		duration = 5000,
		action,
		onclose
	}: Props = $props();

	let progress = $state(100);
	let isPaused = $state(false);
	let startX = $state(0);
	let currentX = $state(0);
	let isDragging = $state(false);

	// Auto dismiss timer
	let intervalId: ReturnType<typeof setInterval> | null = null;

	$effect(() => {
		if (duration > 0 && !isPaused) {
			const step = 100 / (duration / 50);
			intervalId = setInterval(() => {
				progress -= step;
				if (progress <= 0) {
					close();
				}
			}, 50);
		}

		return () => {
			if (intervalId) clearInterval(intervalId);
		};
	});

	// Type configuration
	const typeConfig = {
		success: {
			icon: CheckCircle,
			bg: 'bg-green-50 dark:bg-green-900/30',
			border: 'border-green-200 dark:border-green-800',
			text: 'text-green-800 dark:text-green-200',
			progress: 'bg-green-500'
		},
		error: {
			icon: XCircle,
			bg: 'bg-red-50 dark:bg-red-900/30',
			border: 'border-red-200 dark:border-red-800',
			text: 'text-red-800 dark:text-red-200',
			progress: 'bg-red-500'
		},
		warning: {
			icon: AlertTriangle,
			bg: 'bg-yellow-50 dark:bg-yellow-900/30',
			border: 'border-yellow-200 dark:border-yellow-800',
			text: 'text-yellow-800 dark:text-yellow-200',
			progress: 'bg-yellow-500'
		},
		info: {
			icon: Info,
			bg: 'bg-blue-50 dark:bg-blue-900/30',
			border: 'border-blue-200 dark:border-blue-800',
			text: 'text-blue-800 dark:text-blue-200',
			progress: 'bg-blue-500'
		}
	};

	const config = $derived(typeConfig[type]);

	function close() {
		if (intervalId) clearInterval(intervalId);
		onclose?.();
	}

	function pause() {
		isPaused = true;
		if (intervalId) clearInterval(intervalId);
	}

	function resume() {
		isPaused = false;
	}

	// Touch swipe to dismiss
	function handleTouchStart(e: TouchEvent) {
		startX = e.touches[0].clientX;
		isDragging = true;
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging) return;
		currentX = e.touches[0].clientX - startX;
	}

	function handleTouchEnd() {
		if (Math.abs(currentX) > 100) {
			close();
		}
		currentX = 0;
		isDragging = false;
	}
</script>

<div
	class="toast-item relative overflow-hidden rounded-xl border shadow-medium {config.bg} {config.border}"
	style="transform: translateX({currentX}px); opacity: {1 - Math.abs(currentX) / 200}"
	in:fly={{ y: 20, duration: 200 }}
	out:fade={{ duration: 150 }}
	onmouseenter={pause}
	onmouseleave={resume}
	ontouchstart={handleTouchStart}
	ontouchmove={handleTouchMove}
	ontouchend={handleTouchEnd}
	role="alert"
	aria-live="polite"
>
	<div class="flex items-start gap-3 p-4">
		<!-- Icon -->
		<div class="flex-shrink-0 mt-0.5">
			<svelte:component this={config.icon} class="w-5 h-5 {config.text}" />
		</div>

		<!-- Content -->
		<div class="flex-1 min-w-0">
			<p class="text-sm font-medium {config.text}">{message}</p>

			<!-- Action button -->
			{#if action}
				<button
					type="button"
					class="mt-2 text-sm font-medium {config.text} hover:underline"
					onclick={() => {
						action.onClick();
						close();
					}}
				>
					{action.label}
				</button>
			{/if}
		</div>

		<!-- Close button -->
		<button
			type="button"
			class="flex-shrink-0 p-1 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
			onclick={close}
			aria-label="닫기"
		>
			<X class="w-4 h-4 {config.text}" />
		</button>
	</div>

	<!-- Progress bar -->
	{#if duration > 0}
		<div class="absolute bottom-0 left-0 right-0 h-1 bg-black/10 dark:bg-white/10">
			<div
				class="h-full {config.progress} transition-all duration-50 ease-linear"
				style="width: {progress}%"
			></div>
		</div>
	{/if}
</div>
