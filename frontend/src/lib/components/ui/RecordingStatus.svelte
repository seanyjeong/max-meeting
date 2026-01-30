<script lang="ts">
	/**
	 * RecordingStatus - Enhanced recording status indicator
	 *
	 * Shows:
	 * - Recording state with visual feedback
	 * - Elapsed time with hours support
	 * - File size estimation
	 * - Battery status warning
	 * - Auto-save indicator
	 */
	import { Mic, MicOff, Pause, Play, Square, Battery, BatteryLow, BatteryWarning, Save } from 'lucide-svelte';

	interface Props {
		state: 'idle' | 'recording' | 'paused' | 'stopped';
		elapsedTime: number;
		batteryLevel?: number | null;
		batteryCharging?: boolean;
		lastSavedAt?: Date | null;
		estimatedSize?: number;
	}

	let {
		state = 'idle',
		elapsedTime = 0,
		batteryLevel = null,
		batteryCharging = false,
		lastSavedAt = null,
		estimatedSize = 0
	}: Props = $props();

	// Format time as HH:MM:SS or MM:SS
	const formattedTime = $derived.by(() => {
		const hours = Math.floor(elapsedTime / 3600);
		const minutes = Math.floor((elapsedTime % 3600) / 60);
		const seconds = elapsedTime % 60;

		if (hours > 0) {
			return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
		}
		return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
	});

	// Format file size
	const formattedSize = $derived.by(() => {
		if (estimatedSize < 1024) return `${estimatedSize} B`;
		if (estimatedSize < 1024 * 1024) return `${(estimatedSize / 1024).toFixed(1)} KB`;
		return `${(estimatedSize / (1024 * 1024)).toFixed(1)} MB`;
	});

	// Battery status
	const batteryStatus = $derived.by(() => {
		if (batteryLevel === null) return null;
		if (batteryCharging) return 'charging';
		if (batteryLevel <= 10) return 'critical';
		if (batteryLevel <= 20) return 'low';
		return 'normal';
	});

	// State colors
	const stateConfig = $derived.by(() => {
		switch (state) {
			case 'recording':
				return {
					color: 'text-red-600 dark:text-red-400',
					bg: 'bg-red-100 dark:bg-red-900/30',
					border: 'border-red-300 dark:border-red-700',
					pulse: true,
					label: '녹음 중'
				};
			case 'paused':
				return {
					color: 'text-yellow-600 dark:text-yellow-400',
					bg: 'bg-yellow-100 dark:bg-yellow-900/30',
					border: 'border-yellow-300 dark:border-yellow-700',
					pulse: false,
					label: '일시정지'
				};
			case 'stopped':
				return {
					color: 'text-gray-600 dark:text-gray-400',
					bg: 'bg-gray-100 dark:bg-gray-800',
					border: 'border-gray-300 dark:border-gray-600',
					pulse: false,
					label: '중지됨'
				};
			default:
				return {
					color: 'text-gray-500 dark:text-gray-400',
					bg: 'bg-gray-50 dark:bg-gray-800',
					border: 'border-gray-200 dark:border-gray-700',
					pulse: false,
					label: '대기 중'
				};
		}
	});

	// Time since last save
	const timeSinceLastSave = $derived.by(() => {
		if (!lastSavedAt) return null;
		const diff = Math.floor((Date.now() - lastSavedAt.getTime()) / 1000);
		if (diff < 60) return '방금 전';
		if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
		return `${Math.floor(diff / 3600)}시간 전`;
	});
</script>

<div
	class="recording-status flex items-center gap-4 p-3 rounded-xl border {stateConfig.bg} {stateConfig.border} transition-all duration-200"
	role="status"
	aria-live="polite"
>
	<!-- State indicator -->
	<div class="flex items-center gap-2">
		<div class="relative">
			{#if state === 'recording'}
				<Mic class="w-5 h-5 {stateConfig.color}" />
				<span class="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse"></span>
			{:else if state === 'paused'}
				<Pause class="w-5 h-5 {stateConfig.color}" />
			{:else if state === 'stopped'}
				<Square class="w-5 h-5 {stateConfig.color}" />
			{:else}
				<MicOff class="w-5 h-5 {stateConfig.color}" />
			{/if}
		</div>
		<span class="text-sm font-medium {stateConfig.color}">{stateConfig.label}</span>
	</div>

	<!-- Timer -->
	<div class="flex-1 text-center">
		<span
			class="text-2xl font-mono font-bold {stateConfig.color} tabular-nums"
			class:animate-pulse={state === 'recording'}
		>
			{formattedTime}
		</span>
	</div>

	<!-- Right side info -->
	<div class="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400">
		<!-- File size -->
		{#if estimatedSize > 0}
			<span class="hidden sm:inline">{formattedSize}</span>
		{/if}

		<!-- Auto-save indicator -->
		{#if lastSavedAt && state === 'recording'}
			<div class="flex items-center gap-1 text-green-600 dark:text-green-400" title="마지막 저장: {timeSinceLastSave}">
				<Save class="w-4 h-4" />
				<span class="hidden sm:inline text-xs">{timeSinceLastSave}</span>
			</div>
		{/if}

		<!-- Battery -->
		{#if batteryLevel !== null}
			<div
				class="flex items-center gap-1"
				class:text-red-600={batteryStatus === 'critical'}
				class:dark:text-red-400={batteryStatus === 'critical'}
				class:text-yellow-600={batteryStatus === 'low'}
				class:dark:text-yellow-400={batteryStatus === 'low'}
				class:text-green-600={batteryStatus === 'charging'}
				class:dark:text-green-400={batteryStatus === 'charging'}
				title="배터리: {batteryLevel}%"
			>
				{#if batteryStatus === 'critical'}
					<BatteryWarning class="w-4 h-4" />
				{:else if batteryStatus === 'low'}
					<BatteryLow class="w-4 h-4" />
				{:else}
					<Battery class="w-4 h-4" />
				{/if}
				<span class="text-xs">{batteryLevel}%</span>
			</div>
		{/if}
	</div>
</div>

<style>
	.tabular-nums {
		font-variant-numeric: tabular-nums;
	}
</style>
