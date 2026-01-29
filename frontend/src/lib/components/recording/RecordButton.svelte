<script lang="ts">
	/**
	 * RecordButton - Large record/stop button with visual feedback
	 *
	 * - 80px size for easy touch on tablet
	 * - Red pulsing when recording
	 * - Vibration feedback
	 */
	import { isRecording, isPaused, recordingTime, formatTime } from '$lib/stores/recording';

	interface Props {
		disabled?: boolean;
		onstart?: () => void;
		onstop?: () => void;
		onpause?: () => void;
		onresume?: () => void;
	}

	let { disabled = false, onstart, onstop, onpause, onresume }: Props = $props();

	function handleClick() {
		if ($isRecording) {
			onstop?.();
		} else if ($isPaused) {
			onresume?.();
		} else {
			onstart?.();
		}
	}

	function handlePauseClick(e: Event) {
		e.stopPropagation();
		if ($isRecording) {
			onpause?.();
		} else if ($isPaused) {
			onresume?.();
		}
	}
</script>

<div class="flex flex-col items-center gap-4">
	<!-- Main Record/Stop Button -->
	<button
		type="button"
		{disabled}
		onclick={handleClick}
		class="relative w-recording h-recording rounded-full focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-red-300 transition-all duration-200 {disabled
			? 'opacity-50 cursor-not-allowed'
			: ''} {$isRecording
			? 'bg-red-600 hover:bg-red-700 animate-pulse-fast'
			: $isPaused
				? 'bg-yellow-500 hover:bg-yellow-600'
				: 'bg-red-500 hover:bg-red-600'}"
		aria-label={$isRecording ? '녹음 중지' : $isPaused ? '녹음 재개' : '녹음 시작'}
	>
		{#if $isRecording}
			<!-- Stop icon -->
			<div class="absolute inset-0 flex items-center justify-center">
				<div class="w-8 h-8 bg-white rounded-sm"></div>
			</div>
		{:else if $isPaused}
			<!-- Resume icon (play) -->
			<div class="absolute inset-0 flex items-center justify-center">
				<svg class="w-10 h-10 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
					<path d="M8 5v14l11-7z" />
				</svg>
			</div>
		{:else}
			<!-- Record icon (circle) -->
			<div class="absolute inset-0 flex items-center justify-center">
				<div class="w-6 h-6 bg-white rounded-full"></div>
			</div>
		{/if}

		<!-- Pulsing ring when recording -->
		{#if $isRecording}
			<span
				class="absolute inset-0 rounded-full border-4 border-red-400 animate-ping opacity-75"
			></span>
		{/if}
	</button>

	<!-- Pause button (only show when recording) -->
	{#if $isRecording || $isPaused}
		<button
			type="button"
			onclick={handlePauseClick}
			class="w-12 h-12 rounded-full bg-gray-200 hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 flex items-center justify-center transition-colors"
			aria-label={$isRecording ? '일시정지' : '재개'}
		>
			{#if $isRecording}
				<!-- Pause icon -->
				<svg class="w-6 h-6 text-gray-700" fill="currentColor" viewBox="0 0 24 24">
					<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
				</svg>
			{:else}
				<!-- Resume icon -->
				<svg class="w-6 h-6 text-gray-700 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
					<path d="M8 5v14l11-7z" />
				</svg>
			{/if}
		</button>
	{/if}

	<!-- Timer display -->
	<div
		class="text-2xl font-mono font-semibold {$isRecording
			? 'text-red-600'
			: $isPaused
				? 'text-yellow-600'
				: 'text-gray-600'}"
		role="timer"
		aria-live="polite"
	>
		{formatTime($recordingTime)}
	</div>

	<!-- Status label -->
	<div
		class="text-sm font-medium {$isRecording
			? 'text-red-600'
			: $isPaused
				? 'text-yellow-600'
				: 'text-gray-500'}"
	>
		{#if $isRecording}
			녹음 중
		{:else if $isPaused}
			일시정지
		{:else}
			대기 중
		{/if}
	</div>
</div>
