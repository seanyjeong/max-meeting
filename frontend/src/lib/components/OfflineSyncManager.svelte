<script lang="ts">
	/**
	 * OfflineSyncManager - Handles offline sync conflicts
	 * Usage: Add this component to your app layout to automatically handle sync conflicts
	 */
	import { onMount } from 'svelte';
	import { offlineStore, hasConflicts, type ConflictData } from '$lib/stores/offline';
	import SyncConflictDialog from './SyncConflictDialog.svelte';

	let currentConflict: ConflictData | null = $state(null);
	let showDialog = $state(false);

	// 충돌 감지 시 다이얼로그 표시
	$effect(() => {
		if ($hasConflicts && !showDialog) {
			// 첫 번째 충돌을 처리
			currentConflict = $offlineStore.pendingConflicts[0] || null;
			showDialog = !!currentConflict;
		}
	});

	// 충돌 해결 핸들러
	function handleResolve(choice: 'local' | 'server' | 'merge') {
		if (currentConflict === null) return;

		const conflictIndex = $offlineStore.pendingConflicts.findIndex(
			(c) =>
				c.resourceType === currentConflict!.resourceType &&
				c.resourceId === currentConflict!.resourceId
		);

		if (conflictIndex !== -1) {
			offlineStore.resolveConflict(conflictIndex, choice);
		}

		// 다이얼로그 닫기
		showDialog = false;
		currentConflict = null;

		// 다음 충돌이 있으면 표시
		if ($offlineStore.pendingConflicts.length > 0) {
			setTimeout(() => {
				currentConflict = $offlineStore.pendingConflicts[0];
				showDialog = true;
			}, 300);
		}
	}

	// 나중에 결정 핸들러
	function handleCancel() {
		showDialog = false;
		currentConflict = null;
	}

	// 온라인 복귀 시 자동 동기화
	onMount(() => {
		const handleOnline = () => {
			if ($offlineStore.syncQueue.length > 0) {
				offlineStore.syncQueue();
			}
		};

		window.addEventListener('online', handleOnline);

		return () => {
			window.removeEventListener('online', handleOnline);
		};
	});
</script>

<!-- 충돌 해결 다이얼로그 -->
{#if showDialog && currentConflict}
	<SyncConflictDialog
		conflict={currentConflict}
		onResolve={handleResolve}
		onCancel={handleCancel}
	/>
{/if}

<!-- 오프라인 상태 표시 -->
{#if !$offlineStore.isOnline}
	<div class="fixed bottom-4 left-4 z-40 flex items-center gap-2 px-4 py-2 bg-yellow-100 border border-yellow-400 text-yellow-800 rounded-lg shadow-lg">
		<svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
		</svg>
		<span class="text-sm font-medium">오프라인 모드</span>
		{#if $offlineStore.syncQueue.length > 0}
			<span class="text-xs bg-yellow-200 px-2 py-0.5 rounded-full">
				{$offlineStore.syncQueue.length}개 대기 중
			</span>
		{/if}
	</div>
{/if}

<!-- 동기화 진행 중 표시 -->
{#if $offlineStore.isSyncing}
	<div class="fixed bottom-4 left-4 z-40 flex items-center gap-2 px-4 py-2 bg-blue-100 border border-blue-400 text-blue-800 rounded-lg shadow-lg">
		<svg class="w-5 h-5 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
		</svg>
		<span class="text-sm font-medium">동기화 중...</span>
	</div>
{/if}

<!-- 충돌 대기 표시 -->
{#if $hasConflicts && !showDialog}
	<div class="fixed bottom-4 right-4 z-40">
		<button
			class="flex items-center gap-2 px-4 py-2 bg-red-100 border border-red-400 text-red-800 rounded-lg shadow-lg hover:bg-red-200 transition-colors"
			onclick={() => {
				currentConflict = $offlineStore.pendingConflicts[0];
				showDialog = true;
			}}
		>
			<svg class="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
			</svg>
			<span class="text-sm font-medium">
				{$offlineStore.pendingConflicts.length}개의 충돌 해결 필요
			</span>
		</button>
	</div>
{/if}
