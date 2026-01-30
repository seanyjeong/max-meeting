<script lang="ts">
	/**
	 * ErrorBoundary - Error handling wrapper component
	 *
	 * Catches errors and displays user-friendly error messages
	 * with retry functionality.
	 */
	import { AlertTriangle, RefreshCw, Home } from 'lucide-svelte';

	interface Props {
		error?: Error | null;
		fallback?: boolean;
		onretry?: () => void;
		children?: import('svelte').Snippet;
	}

	let {
		error = null,
		fallback = false,
		onretry,
		children
	}: Props = $props();

	let internalError = $state<Error | null>(null);

	// Use provided error or internal error
	const displayError = $derived(error || internalError);

	function handleRetry() {
		internalError = null;
		onretry?.();
	}

	function goHome() {
		window.location.href = '/';
	}

	// Error categorization for user-friendly messages
	const errorInfo = $derived.by(() => {
		if (!displayError) return null;

		const message = displayError.message.toLowerCase();

		if (message.includes('network') || message.includes('fetch')) {
			return {
				title: '네트워크 오류',
				description: '서버에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.',
				canRetry: true
			};
		}

		if (message.includes('timeout')) {
			return {
				title: '요청 시간 초과',
				description: '서버 응답이 너무 오래 걸립니다. 잠시 후 다시 시도해주세요.',
				canRetry: true
			};
		}

		if (message.includes('unauthorized') || message.includes('401')) {
			return {
				title: '인증 오류',
				description: '로그인이 필요하거나 세션이 만료되었습니다.',
				canRetry: false
			};
		}

		if (message.includes('not found') || message.includes('404')) {
			return {
				title: '페이지를 찾을 수 없음',
				description: '요청하신 페이지가 존재하지 않습니다.',
				canRetry: false
			};
		}

		return {
			title: '오류가 발생했습니다',
			description: '예기치 않은 오류가 발생했습니다. 문제가 지속되면 관리자에게 문의해주세요.',
			canRetry: true
		};
	});
</script>

{#if displayError || fallback}
	<div class="error-boundary flex flex-col items-center justify-center min-h-[300px] p-8 text-center">
		<div class="w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center mb-4">
			<AlertTriangle class="w-8 h-8 text-red-600 dark:text-red-400" />
		</div>

		<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
			{errorInfo?.title || '오류 발생'}
		</h2>

		<p class="text-gray-600 dark:text-gray-400 max-w-md mb-6">
			{errorInfo?.description || '알 수 없는 오류가 발생했습니다.'}
		</p>

		<!-- Technical details (dev only) -->
		{#if import.meta.env.DEV && displayError}
			<details class="w-full max-w-md mb-6 text-left">
				<summary class="text-sm text-gray-500 dark:text-gray-400 cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">
					기술적 세부정보
				</summary>
				<pre class="mt-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg text-xs overflow-auto max-h-32">
{displayError.stack || displayError.message}
				</pre>
			</details>
		{/if}

		<div class="flex gap-3">
			{#if errorInfo?.canRetry && onretry}
				<button
					type="button"
					class="btn btn-primary"
					onclick={handleRetry}
				>
					<RefreshCw class="w-4 h-4 mr-2" />
					다시 시도
				</button>
			{/if}

			<button
				type="button"
				class="btn btn-secondary"
				onclick={goHome}
			>
				<Home class="w-4 h-4 mr-2" />
				홈으로 이동
			</button>
		</div>
	</div>
{:else}
	{@render children?.()}
{/if}
