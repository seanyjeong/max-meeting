<script lang="ts">
	/**
	 * OfflineIndicator - Network status indicator
	 *
	 * Shows:
	 * - Online/offline status
	 * - Sync status
	 * - Pending changes count
	 */
	import { onMount, onDestroy } from 'svelte';
	import { Wifi, WifiOff, Cloud, CloudOff, RefreshCw } from 'lucide-svelte';
	import { isOffline as checkOffline } from '$lib/stores/offlineCache';

	interface Props {
		pendingChanges?: number;
		isSyncing?: boolean;
		showAlways?: boolean;
	}

	let {
		pendingChanges = 0,
		isSyncing = false,
		showAlways = false
	}: Props = $props();

	let isOnline = $state(true);
	let showBanner = $state(false);

	function updateOnlineStatus() {
		isOnline = navigator.onLine;
		showBanner = !isOnline || showAlways;
	}

	onMount(() => {
		updateOnlineStatus();
		window.addEventListener('online', updateOnlineStatus);
		window.addEventListener('offline', updateOnlineStatus);
	});

	onDestroy(() => {
		window.removeEventListener('online', updateOnlineStatus);
		window.removeEventListener('offline', updateOnlineStatus);
	});

	// Status configuration
	const statusConfig = $derived.by(() => {
		if (!isOnline) {
			return {
				icon: WifiOff,
				bg: 'bg-yellow-50 dark:bg-yellow-900/30',
				border: 'border-yellow-200 dark:border-yellow-800',
				text: 'text-yellow-800 dark:text-yellow-200',
				label: '오프라인 모드'
			};
		}

		if (isSyncing) {
			return {
				icon: RefreshCw,
				bg: 'bg-blue-50 dark:bg-blue-900/30',
				border: 'border-blue-200 dark:border-blue-800',
				text: 'text-blue-800 dark:text-blue-200',
				label: '동기화 중...'
			};
		}

		if (pendingChanges > 0) {
			return {
				icon: Cloud,
				bg: 'bg-orange-50 dark:bg-orange-900/30',
				border: 'border-orange-200 dark:border-orange-800',
				text: 'text-orange-800 dark:text-orange-200',
				label: `${pendingChanges}개 변경사항 대기 중`
			};
		}

		return {
			icon: Wifi,
			bg: 'bg-green-50 dark:bg-green-900/30',
			border: 'border-green-200 dark:border-green-800',
			text: 'text-green-800 dark:text-green-200',
			label: '온라인'
		};
	});
</script>

{#if showBanner || !isOnline || pendingChanges > 0}
	<div
		class="offline-indicator flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-all duration-200 {statusConfig.bg} {statusConfig.border}"
		role="status"
		aria-live="polite"
	>
		<svelte:component
			this={statusConfig.icon}
			class="w-4 h-4 {statusConfig.text} {isSyncing ? 'animate-spin' : ''}"
		/>
		<span class="font-medium {statusConfig.text}">{statusConfig.label}</span>

		{#if !isOnline}
			<span class="text-xs {statusConfig.text} opacity-75">
				(일부 기능이 제한됨)
			</span>
		{/if}
	</div>
{/if}
