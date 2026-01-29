<script lang="ts">
	/**
	 * CompactRecordingBar - Professional recording UI component
	 *
	 * Compact 56px fixed bar with recording controls and status.
	 * Industrial/brutalist aesthetic with technical precision.
	 *
	 * Visual states:
	 * - Recording: red accent border, pulsing button, animated waveform
	 * - Paused: yellow accent border, static waveform
	 * - Idle: neutral gray, minimal UI
	 */
	import { formatTime } from '$lib/stores/recording';

	interface Props {
		isRecording: boolean;
		isPaused: boolean;
		recordingTime: number;
		currentAgenda: string;
		visualizationData: Uint8Array;
		onStart?: () => void;
		onStop?: () => void;
		onPause?: () => void;
		onResume?: () => void;
	}

	let {
		isRecording = false,
		isPaused = false,
		recordingTime = 0,
		currentAgenda = '',
		visualizationData = new Uint8Array(8),
		onStart,
		onStop,
		onPause,
		onResume
	}: Props = $props();

	// Derived state for UI
	const isActive = $derived(isRecording || isPaused);
	const statusColor = $derived(
		isRecording ? 'border-red-600' : isPaused ? 'border-yellow-500' : 'border-gray-200'
	);
	const buttonBgColor = $derived(
		isRecording ? 'bg-red-600' : isPaused ? 'bg-yellow-500' : 'bg-gray-400'
	);
	const timerColor = $derived(
		isRecording ? 'text-red-600' : isPaused ? 'text-yellow-600' : 'text-gray-500'
	);

	// Calculate waveform bar heights (8 bars, normalized to 0-32px)
	const waveformBars = $derived.by(() => {
		if (visualizationData.length === 0) return Array(8).fill(4);

		const barCount = 8;
		const step = Math.floor(visualizationData.length / barCount);
		const bars: number[] = [];

		for (let i = 0; i < barCount; i++) {
			let sum = 0;
			for (let j = 0; j < step; j++) {
				sum += visualizationData[i * step + j] || 0;
			}
			const average = sum / step;
			// Normalize to 4-32px range
			const height = Math.max(4, Math.min(32, (average / 255) * 32));
			bars.push(height);
		}

		return bars;
	});

	function handleRecordButtonClick() {
		if (isRecording) {
			onStop?.();
		} else if (isPaused) {
			onResume?.();
		} else {
			onStart?.();
		}
	}

	function handlePauseClick() {
		if (isRecording) {
			onPause?.();
		} else if (isPaused) {
			onResume?.();
		}
	}
</script>

<div
	class="fixed top-0 left-0 right-0 z-50 h-14 bg-white dark:bg-gray-900 border-b-2 {statusColor} transition-colors duration-200"
	role="region"
	aria-label="녹음 컨트롤 바"
>
	<div class="h-full max-w-screen-2xl mx-auto px-4 flex items-center justify-between gap-4">
		<!-- LEFT: Record button, timer, waveform -->
		<div class="flex items-center gap-3">
			<!-- Record/Stop Button -->
			<button
				type="button"
				onclick={handleRecordButtonClick}
				class="relative w-12 h-12 rounded-full {buttonBgColor} hover:opacity-90 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 flex items-center justify-center group"
				aria-label={isRecording ? '녹음 중지' : isPaused ? '녹음 재개' : '녹음 시작'}
			>
				{#if isRecording}
					<!-- Stop icon -->
					<div class="w-4 h-4 bg-white rounded-sm"></div>
					<!-- Pulsing ring -->
					<span
						class="absolute inset-0 rounded-full border-2 border-red-400 animate-ping opacity-50"
					></span>
				{:else if isPaused}
					<!-- Resume icon (play) -->
					<svg class="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{:else}
					<!-- Record icon (filled circle) -->
					<div class="w-3 h-3 bg-white rounded-full"></div>
				{/if}
			</button>

			<!-- Timer Display -->
			<div
				class="text-lg font-mono font-bold {timerColor} tracking-wider min-w-[84px]"
				role="timer"
				aria-live="polite"
			>
				{formatTime(recordingTime)}
			</div>

			<!-- Mini Waveform Bars -->
			<div class="flex items-center gap-0.5 h-8" aria-hidden="true">
				{#each waveformBars as barHeight, i}
					<div
						class="w-1 rounded-full transition-all duration-150 {isRecording
							? 'bg-red-500'
							: isPaused
								? 'bg-yellow-500'
								: 'bg-gray-300'}"
						style="height: {barHeight}px;"
						style:transition-delay="{i * 20}ms"
					></div>
				{/each}
			</div>
		</div>

		<!-- CENTER: Pause/Resume button (only when active) -->
		{#if isActive}
			<button
				type="button"
				onclick={handlePauseClick}
				class="w-10 h-10 rounded-full bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 flex items-center justify-center"
				aria-label={isRecording ? '일시정지' : '재개'}
			>
				{#if isRecording}
					<!-- Pause icon (two bars) -->
					<svg class="w-5 h-5 text-gray-700 dark:text-gray-200" fill="currentColor" viewBox="0 0 24 24">
						<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
					</svg>
				{:else}
					<!-- Play icon -->
					<svg class="w-5 h-5 text-gray-700 dark:text-gray-200 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{/if}
			</button>
		{/if}

		<!-- RIGHT: Current agenda label -->
		<div class="flex items-center gap-2 min-w-0 flex-1 justify-end">
			{#if currentAgenda}
				<span class="text-sm font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">
					현재 안건:
				</span>
				<span
					class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate max-w-[400px]"
					title={currentAgenda}
				>
					{currentAgenda}
				</span>
			{:else}
				<span class="text-sm text-gray-400 dark:text-gray-500 italic">
					안건이 설정되지 않음
				</span>
			{/if}
		</div>
	</div>
</div>

<style>
	/* Custom pulse animation for recording state */
	@keyframes ping {
		75%,
		100% {
			transform: scale(1.5);
			opacity: 0;
		}
	}
</style>
