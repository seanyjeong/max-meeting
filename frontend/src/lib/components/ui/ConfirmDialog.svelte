<script lang="ts">
	import { AlertTriangle, Trash2, X } from 'lucide-svelte';

	interface Props {
		open: boolean;
		title?: string;
		message: string;
		confirmText?: string;
		cancelText?: string;
		variant?: 'danger' | 'warning' | 'info';
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open = false,
		title = '확인',
		message,
		confirmText = '확인',
		cancelText = '취소',
		variant = 'danger',
		onConfirm,
		onCancel
	}: Props = $props();

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onCancel();
		}
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onCancel();
		}
	}

	const iconClass = $derived(
		variant === 'danger'
			? 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400'
			: variant === 'warning'
				? 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
				: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
	);

	const confirmBtnClass = $derived(
		variant === 'danger'
			? 'btn-danger'
			: variant === 'warning'
				? 'bg-yellow-600 text-white hover:bg-yellow-700'
				: 'btn-primary'
	);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in"
		onclick={handleBackdropClick}
		role="dialog"
		aria-modal="true"
		aria-labelledby="dialog-title"
	>
		<!-- Dialog -->
		<div
			class="bg-white dark:bg-surface rounded-2xl shadow-strong max-w-md w-full p-6 animate-slide-up"
			role="document"
		>
			<!-- Icon & Title -->
			<div class="flex items-start gap-4">
				<div class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center {iconClass}">
					{#if variant === 'danger'}
						<Trash2 class="w-5 h-5" />
					{:else}
						<AlertTriangle class="w-5 h-5" />
					{/if}
				</div>
				<div class="flex-1">
					<h3 id="dialog-title" class="text-lg font-semibold text-gray-900 dark:text-text">
						{title}
					</h3>
					<p class="mt-2 text-sm text-gray-600 dark:text-text-muted">
						{message}
					</p>
				</div>
				<button
					type="button"
					onclick={onCancel}
					class="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-surface-light dark:hover:text-text transition-colors"
					aria-label="닫기"
				>
					<X class="w-5 h-5" />
				</button>
			</div>

			<!-- Actions -->
			<div class="flex justify-end gap-3 mt-6">
				<button type="button" onclick={onCancel} class="btn btn-secondary">
					{cancelText}
				</button>
				<button type="button" onclick={onConfirm} class="btn {confirmBtnClass}">
					{confirmText}
				</button>
			</div>
		</div>
	</div>
{/if}
