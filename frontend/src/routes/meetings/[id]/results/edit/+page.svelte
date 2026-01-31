<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Breadcrumb, Button, Card, LoadingSpinner } from '$lib/components';
	import SummaryEditor from '$lib/components/results/SummaryEditor.svelte';
	import ActionItems from '$lib/components/results/ActionItems.svelte';
	import TranscriptViewer from '$lib/components/results/TranscriptViewer.svelte';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import { resultsStore, hasResult } from '$lib/stores/results';
	import { api } from '$lib/api';
	import type { MeetingDetail } from '$lib/stores/meeting';

	let meetingId = $derived(parseInt($page.params.id ?? '0'));
	let hasUnsavedChanges = $state(false);
	let originalSummary = $state('');

	// Breadcrumb items
	let breadcrumbItems = $derived([
		{ label: '홈', href: '/' },
		{ label: '회의', href: '/meetings' },
		{
			label: $currentMeeting?.title || '회의',
			href: `/meetings/${meetingId}`
		},
		{ label: '결과', href: `/meetings/${meetingId}/results` },
		{ label: '수정' }
	]);

	onMount(async () => {
		// Load meeting if not already loaded
		if (!$currentMeeting || $currentMeeting.id !== meetingId) {
			$isLoading = true;
			try {
				const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
				$currentMeeting = response;
			} catch {
				goto('/meetings');
				return;
			} finally {
				$isLoading = false;
			}
		}

		// Load results if not already loaded
		if (!$hasResult) {
			await resultsStore.loadResult(meetingId);
			await resultsStore.loadTranscript(meetingId);
		}

		// Store original summary for comparison
		originalSummary = $resultsStore.currentResult?.summary || '';
		resultsStore.setEditMode(true);
	});

	// Track unsaved changes
	$effect(() => {
		hasUnsavedChanges = $resultsStore.editedSummary !== originalSummary;
	});

	// Warn before leaving with unsaved changes
	function handleBeforeUnload(event: BeforeUnloadEvent) {
		if (hasUnsavedChanges) {
			event.preventDefault();
			return '';
		}
	}

	async function handleSave() {
		await resultsStore.saveResult(meetingId);
		originalSummary = $resultsStore.editedSummary;
		goto(`/meetings/${meetingId}/results`);
	}

	function handleCancel() {
		if (hasUnsavedChanges) {
			if (!confirm('저장되지 않은 변경사항이 있습니다. 나가시겠습니까?')) {
				return;
			}
		}
		resultsStore.setEditMode(false);
		goto(`/meetings/${meetingId}/results`);
	}

	function handleSegmentClick(segment: any) {
		// Insert timestamp reference into editor
		const timeStr = formatTime(segment.start);
		const insertion = `[${timeStr}] `;
		resultsStore.setEditedSummary($resultsStore.editedSummary + insertion);
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}
</script>

<svelte:window onbeforeunload={handleBeforeUnload} />

<svelte:head>
	<title>결과 수정 - {$currentMeeting?.title || '회의'} | MAX Meeting</title>
</svelte:head>

<div class="edit-page">
	{#if $isLoading || $resultsStore.isLoading}
		<div class="loading-container">
			<LoadingSpinner />
			<p>결과 로딩 중...</p>
		</div>
	{:else if !$hasResult}
		<div class="error-container">
			<p>수정할 결과가 없습니다. 먼저 결과를 생성하세요.</p>
			<Button variant="primary" onclick={() => goto(`/meetings/${meetingId}/results`)}>
				{#snippet children()}결과로 돌아가기{/snippet}
			</Button>
		</div>
	{:else}
		<!-- Header -->
		<header class="page-header">
			<div class="header-left">
				<Breadcrumb items={breadcrumbItems} />
			</div>

			<div class="header-actions">
				{#if hasUnsavedChanges}
					<span class="unsaved-indicator">저장되지 않은 변경사항</span>
				{/if}

				<Button variant="secondary" size="sm" onclick={handleCancel}>
					{#snippet children()}취소{/snippet}
				</Button>

				<Button variant="primary" size="sm" onclick={handleSave} loading={$resultsStore.isLoading}>
					{#snippet children()}
						<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
						</svg>
						저장
					{/snippet}
				</Button>
			</div>
		</header>

		<!-- Main Content: Side by side view -->
		<main class="edit-content">
			<!-- Left: Editor -->
			<div class="editor-panel">
				<Card>
					{#snippet children()}
						<div class="panel-header">
							<h2>요약 편집기</h2>
							<span class="hint">마크다운으로 서식 지정</span>
						</div>
						<SummaryEditor />
					{/snippet}
				</Card>

				<div class="action-items-section">
					<ActionItems {meetingId} />
				</div>
			</div>

			<!-- Right: Transcript Reference -->
			<div class="transcript-panel">
				<Card padding={false}>
					{#snippet children()}
						<div class="panel-header padded">
							<h2>원본 대화 내용</h2>
							<span class="hint">클릭하여 타임스탬프 삽입</span>
						</div>
						<TranscriptViewer onSegmentClick={handleSegmentClick} />
					{/snippet}
				</Card>
			</div>
		</main>

		<!-- Keyboard shortcuts help -->
		<aside class="shortcuts-help" aria-label="키보드 단축키">
			<span class="shortcut"><kbd>Cmd</kbd>+<kbd>S</kbd> 저장</span>
			<span class="shortcut"><kbd>Cmd</kbd>+<kbd>B</kbd> 굵게</span>
			<span class="shortcut"><kbd>Cmd</kbd>+<kbd>I</kbd> 기울임</span>
		</aside>
	{/if}
</div>

<style>
	.edit-page {
		display: flex;
		flex-direction: column;
		min-height: calc(100vh - 64px);
	}

	.loading-container,
	.error-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 300px;
		gap: 1rem;
		color: #6b7280;
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
		flex-wrap: wrap;
		gap: 1rem;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.unsaved-indicator {
		padding: 0.25rem 0.5rem;
		background: #fef3c7;
		color: #d97706;
		font-size: 0.75rem;
		border-radius: 9999px;
	}

	.edit-content {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1rem;
		flex: 1;
	}

	.editor-panel {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.transcript-panel {
		display: flex;
		flex-direction: column;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.75rem;
	}

	.panel-header.padded {
		padding: 0.75rem 1rem;
		margin-bottom: 0;
		border-bottom: 1px solid #e5e7eb;
	}

	.panel-header h2 {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.hint {
		font-size: 0.75rem;
		color: #9ca3af;
	}

	.action-items-section {
		flex-shrink: 0;
	}

	.shortcuts-help {
		display: flex;
		justify-content: center;
		gap: 1.5rem;
		padding: 0.75rem;
		background: #f9fafb;
		border-top: 1px solid #e5e7eb;
		margin-top: 1rem;
	}

	.shortcut {
		font-size: 0.75rem;
		color: #6b7280;
	}

	.shortcut kbd {
		display: inline-block;
		padding: 0.125rem 0.375rem;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 0.25rem;
		font-family: ui-monospace, monospace;
		font-size: 0.625rem;
	}

	/* Responsive */
	@media (max-width: 1023px) {
		.edit-content {
			grid-template-columns: 1fr;
		}

		.transcript-panel {
			order: -1;
			max-height: 300px;
		}
	}
</style>
