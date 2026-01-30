<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Breadcrumb, Button, Card, LoadingSpinner, Badge } from '$lib/components';
	import SummaryEditor from '$lib/components/results/SummaryEditor.svelte';
	import ActionItems from '$lib/components/results/ActionItems.svelte';
	import TranscriptViewer from '$lib/components/results/TranscriptViewer.svelte';
	import SpeakerMapper from '$lib/components/results/SpeakerMapper.svelte';
	import { Tabs, Skeleton, KeyboardShortcuts, EmptyState } from '$lib/components/ui';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import { resultsStore, hasResult, isVerified } from '$lib/stores/results';
	import { toast } from '$lib/stores/toast';
	import { api } from '$lib/api';
	import { exportToPdf, copyToClipboard } from '$lib/utils/exportPdf';
	import { FileText, ClipboardCopy, Download, RefreshCw, Pencil, Check, ListTodo, FileAudio, Mic, Loader2 } from 'lucide-svelte';
	import type { MeetingDetail } from '$lib/stores/meeting';

	// Recording status types
	interface Recording {
		id: number;
		status: 'pending' | 'uploaded' | 'processing' | 'completed' | 'failed';
		error_message?: string | null;
	}

	let meetingId = $derived(parseInt($page.params.id ?? '0'));
	let activeTab = $state<'summary' | 'actions' | 'transcript'>('summary');
	let speakerMapping = $state<Record<string, number>>({});
	let showShortcutsHelp = $state(false);

	// Recording status state
	let recordings = $state<Recording[]>([]);
	let recordingsLoading = $state(true);
	let statusPollInterval: ReturnType<typeof setInterval> | null = null;

	// Computed status
	let processingStatus = $derived.by(() => {
		if (recordingsLoading) return 'loading';
		if (recordings.length === 0) return 'no_recordings';

		const hasProcessing = recordings.some(r => r.status === 'processing');
		const hasUploaded = recordings.some(r => r.status === 'uploaded');
		const hasCompleted = recordings.some(r => r.status === 'completed');
		const hasFailed = recordings.some(r => r.status === 'failed');

		if (hasProcessing) return 'processing';
		if (hasUploaded) return 'uploaded';
		if (hasFailed && !hasCompleted) return 'failed';
		if (hasCompleted) return 'ready';
		return 'unknown';
	});

	// Status messages for users
	const statusMessages: Record<string, { title: string; description: string; color: string }> = {
		loading: { title: '상태 확인 중...', description: '', color: 'gray' },
		no_recordings: { title: '녹음이 없습니다', description: '안건과 메모만으로 회의록을 생성하거나, 녹음을 추가할 수 있습니다.', color: 'gray' },
		uploaded: { title: '녹음 업로드 완료', description: '음성을 텍스트로 변환하려면 아래 버튼을 눌러주세요.', color: 'blue' },
		processing: { title: '음성을 텍스트로 변환 중...', description: '잠시만 기다려주세요. 완료되면 자동으로 업데이트됩니다.', color: 'yellow' },
		ready: { title: '변환 완료!', description: '회의록을 생성할 수 있습니다.', color: 'green' },
		failed: { title: '변환 실패', description: '녹음 변환 중 오류가 발생했습니다. 다시 시도해주세요.', color: 'red' },
		unknown: { title: '상태 확인 필요', description: '녹음 상태를 확인할 수 없습니다.', color: 'gray' }
	};

	async function loadRecordingsStatus() {
		try {
			const response = await api.get<{ data: Recording[]; meta: { total: number } }>(
				`/meetings/${meetingId}/recordings`
			);
			recordings = response.data;
		} catch (error) {
			console.error('Failed to load recordings status:', error);
		} finally {
			recordingsLoading = false;
		}
	}

	async function triggerSTT() {
		// Find the most recent uploaded recording
		const uploadedRecording = recordings.find(r => r.status === 'uploaded');
		if (!uploadedRecording) {
			toast.error('변환할 녹음이 없습니다.');
			return;
		}

		try {
			// Trigger STT processing
			await api.post(`/recordings/${uploadedRecording.id}/process`, {});
			toast.success('음성 변환을 시작했습니다.');
			// Reload status
			await loadRecordingsStatus();
		} catch (error) {
			console.error('Failed to trigger STT:', error);
			toast.error('변환 시작에 실패했습니다.');
		}
	}

	// Tab configuration
	const tabConfig = $derived([
		{ id: 'summary', label: '요약', icon: FileText },
		{ id: 'actions', label: '실행 항목', icon: ListTodo, badge: $resultsStore.actionItems.length || undefined },
		{ id: 'transcript', label: '대화 내용', icon: FileAudio }
	]);

	// Keyboard shortcuts (typed for KeyboardShortcuts component)
	const shortcuts: Array<{
		key: string;
		modifiers?: ('ctrl' | 'alt' | 'shift' | 'meta')[];
		description: string;
		action: () => void;
		category?: string;
	}> = [
		{ key: '1', description: '요약 탭', action: () => { activeTab = 'summary' }, category: '탭 전환' },
		{ key: '2', description: '실행 항목 탭', action: () => { activeTab = 'actions' }, category: '탭 전환' },
		{ key: '3', description: '대화 내용 탭', action: () => { activeTab = 'transcript' }, category: '탭 전환' },
		{ key: 'p', modifiers: ['ctrl'], description: 'PDF 내보내기', action: () => { handleExportPdf() }, category: '내보내기' },
		{ key: 'c', modifiers: ['ctrl', 'shift'], description: '클립보드에 복사', action: () => { handleCopyToClipboard() }, category: '내보내기' },
		{ key: 'e', description: '수정 모드', action: () => { handleEdit() }, category: '편집' },
		{ key: 'r', description: '재생성', action: () => { handleRegenerate() }, category: '편집' }
	];

	// PDF export handler
	async function handleExportPdf() {
		if (!$currentMeeting || !$hasResult) return;

		exportToPdf({
			title: $currentMeeting.title,
			date: $currentMeeting.scheduled_at ? new Date($currentMeeting.scheduled_at).toLocaleDateString('ko-KR') : undefined,
			location: $currentMeeting.location || undefined,
			attendees: $currentMeeting.attendees?.map(a => ({
				name: a.contact?.name || '알 수 없음',
				role: a.contact?.role || undefined
			})),
			summary: $resultsStore.currentResult?.summary,
			actionItems: $resultsStore.actionItems.map(item => ({
				content: item.content,
				assignee: item.assignee_name,
				dueDate: item.due_date ? new Date(item.due_date).toLocaleDateString('ko-KR') : undefined,
				priority: item.priority,
				status: item.status
			})),
			transcriptSegments: $resultsStore.transcriptSegments.map(seg => ({
				speaker: seg.speaker_name || seg.speaker_label || undefined,
				text: seg.text,
				timestamp: seg.start
			}))
		});
	}

	// Copy to clipboard handler
	async function handleCopyToClipboard() {
		if (!$currentMeeting || !$hasResult) return;

		const success = await copyToClipboard({
			title: $currentMeeting.title,
			date: $currentMeeting.scheduled_at ? new Date($currentMeeting.scheduled_at).toLocaleDateString('ko-KR') : undefined,
			summary: $resultsStore.currentResult?.summary,
			actionItems: $resultsStore.actionItems.map(item => ({
				content: item.content,
				assignee: item.assignee_name
			}))
		});

		if (success) {
			toast.success('클립보드에 복사되었습니다');
		} else {
			toast.error('복사에 실패했습니다');
		}
	}

	// Extract unique speakers from transcript
	let uniqueSpeakers = $derived(
		Array.from(
			new Set(
				$resultsStore.transcriptSegments
					.map((segment) => segment.speaker_label)
					.filter((label): label is string => label !== null && label !== undefined)
			)
		).sort()
	);

	// Breadcrumb items
	let breadcrumbItems = $derived([
		{ label: '홈', href: '/' },
		{ label: '회의', href: '/meetings' },
		{
			label: $currentMeeting?.title || '회의',
			href: `/meetings/${meetingId}`
		},
		{ label: '결과' }
	]);

	onMount(async () => {
		// Load meeting if not already loaded
		const meetingPromise = (!$currentMeeting || $currentMeeting.id !== meetingId)
			? (async () => {
				$isLoading = true;
				try {
					const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
					$currentMeeting = response;
				} catch (error) {
					console.error('Failed to load meeting:', error);
					goto('/meetings');
					throw error;
				} finally {
					$isLoading = false;
				}
			})()
			: Promise.resolve();

		// Load results, transcript, and recordings status in parallel
		await Promise.all([
			meetingPromise,
			resultsStore.loadResult(meetingId),
			resultsStore.loadTranscript(meetingId),
			loadRecordingsStatus()
		]);

		// Start polling if processing
		if (processingStatus === 'processing') {
			statusPollInterval = setInterval(async () => {
				await loadRecordingsStatus();
				// Also reload transcript when processing completes
				if (processingStatus === 'ready') {
					await resultsStore.loadTranscript(meetingId);
					if (statusPollInterval) {
						clearInterval(statusPollInterval);
						statusPollInterval = null;
					}
				}
			}, 5000); // Poll every 5 seconds
		}
	});

	onDestroy(() => {
		if (statusPollInterval) {
			clearInterval(statusPollInterval);
		}
	});

	async function handleGenerate() {
		await resultsStore.generateResult(meetingId);
	}

	async function handleRegenerate() {
		if (confirm('회의 결과의 새 버전을 생성합니다. 계속하시겠습니까?')) {
			await resultsStore.regenerateResult(meetingId);
		}
	}

	async function handleVerify() {
		if (confirm('이 회의 결과를 검증 완료로 표시하시겠습니까? 내용이 검토되고 승인되었음을 나타냅니다.')) {
			await resultsStore.verifyResult(meetingId);
		}
	}

	function handleEdit() {
		goto(`/meetings/${meetingId}/results/edit`);
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleString('ko-KR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<svelte:head>
	<title>결과 - {$currentMeeting?.title || '회의'} | MAX Meeting</title>
</svelte:head>

<!-- Keyboard shortcuts handler -->
<KeyboardShortcuts {shortcuts} bind:showHelp={showShortcutsHelp} />

<div class="results-page">
	{#if $isLoading || $resultsStore.isLoading}
		<div class="loading-container">
			<LoadingSpinner />
			<p>결과 로딩 중...</p>
		</div>
	{:else}
		<!-- Header -->
		<header class="page-header">
			<div class="header-left">
				<Breadcrumb items={breadcrumbItems} />
			</div>

			<div class="header-actions">
				{#if $isVerified}
					<Badge variant="green">검증 완료</Badge>
				{/if}

				{#if $hasResult}
					<!-- Export buttons -->
					<Button variant="ghost" size="sm" onclick={handleCopyToClipboard} title="클립보드에 복사 (Ctrl+Shift+C)">
						{#snippet children()}
							<ClipboardCopy class="w-4 h-4" />
						{/snippet}
					</Button>

					<Button variant="ghost" size="sm" onclick={handleExportPdf} title="PDF로 내보내기 (Ctrl+P)">
						{#snippet children()}
							<Download class="w-4 h-4" />
						{/snippet}
					</Button>

					<Button variant="secondary" size="sm" onclick={handleRegenerate} loading={$resultsStore.isGenerating}>
						{#snippet children()}
							<RefreshCw class="w-4 h-4 mr-1" />
							재생성
						{/snippet}
					</Button>

					<Button variant="secondary" size="sm" onclick={handleEdit}>
						{#snippet children()}
							<Pencil class="w-4 h-4 mr-1" />
							수정
						{/snippet}
					</Button>

					{#if !$isVerified}
						<Button variant="primary" size="sm" onclick={handleVerify}>
							{#snippet children()}
								<Check class="w-4 h-4 mr-1" />
								검증
							{/snippet}
						</Button>
					{/if}
				{:else}
					<Button variant="primary" size="sm" onclick={handleGenerate} loading={$resultsStore.isGenerating}>
						{#snippet children()}
							<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							결과 생성
						{/snippet}
					</Button>
				{/if}
			</div>
		</header>

		<!-- Error message -->
		{#if $resultsStore.error}
			<div class="error-banner">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<span>{$resultsStore.error}</span>
				<button type="button" onclick={() => resultsStore.clearError()} aria-label="Dismiss error">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		{/if}

		<!-- Generating indicator -->
		{#if $resultsStore.isGenerating}
			<div class="generating-banner">
				<LoadingSpinner />
				<span>회의 결과 생성 중... 잠시 기다려 주세요.</span>
			</div>
		{/if}

		<!-- Main Content -->
		<main class="results-content">
			{#if $hasResult}
				<!-- Tabs -->
				<div class="tabs" role="tablist">
					<button
						type="button"
						class="tab"
						class:active={activeTab === 'summary'}
						role="tab"
						aria-selected={activeTab === 'summary'}
						onclick={() => activeTab = 'summary'}
					>
						요약
					</button>
					<button
						type="button"
						class="tab"
						class:active={activeTab === 'actions'}
						role="tab"
						aria-selected={activeTab === 'actions'}
						onclick={() => activeTab = 'actions'}
					>
						실행 항목
						{#if $resultsStore.actionItems.length > 0}
							<span class="tab-badge">{$resultsStore.actionItems.length}</span>
						{/if}
					</button>
					<button
						type="button"
						class="tab"
						class:active={activeTab === 'transcript'}
						role="tab"
						aria-selected={activeTab === 'transcript'}
						onclick={() => activeTab = 'transcript'}
					>
						대화 내용
					</button>
				</div>

				<!-- Tab Content -->
				<div class="tab-content">
					{#if activeTab === 'summary'}
						<Card>
							{#snippet children()}
								<div class="summary-header">
									<h2>회의 요약</h2>
									{#if $resultsStore.currentResult}
										<div class="summary-meta">
											<span>버전 {$resultsStore.currentResult.version}</span>
											<span>업데이트 {formatDate($resultsStore.currentResult.updated_at)}</span>
										</div>
									{/if}
								</div>

								<!-- Version selector -->
								{#if $resultsStore.versions.length > 1}
									<div class="version-selector">
										<label for="version-select">버전:</label>
										<select
											id="version-select"
											value={$resultsStore.selectedVersion}
											onchange={(e) => {
												const version = parseInt((e.target as HTMLSelectElement).value);
												resultsStore.loadVersion(meetingId, version);
											}}
										>
											{#each $resultsStore.versions as version}
												<option value={version.version}>
													v{version.version} - {formatDate(version.created_at)}
												</option>
											{/each}
										</select>
									</div>
								{/if}

								<SummaryEditor readonly />
							{/snippet}
						</Card>
					{:else if activeTab === 'actions'}
						<ActionItems {meetingId} readonly />
					{:else if activeTab === 'transcript'}
						<!-- Speaker Mapper -->
						{#if uniqueSpeakers.length > 0 && $currentMeeting && $currentMeeting.attendees && $currentMeeting.attendees.length > 0}
							<div class="mb-4">
								<SpeakerMapper
									speakers={uniqueSpeakers}
									attendees={$currentMeeting.attendees}
									bind:mapping={speakerMapping}
								/>
							</div>
						{/if}

						<!-- Transcript Viewer -->
						<TranscriptViewer />
					{/if}
				</div>
			{:else}
				<!-- No results state - Show recording/processing status -->
				<Card>
					{#snippet children()}
						<div class="empty-state">
							{#if processingStatus === 'no_recordings'}
								<!-- No recordings - but can still generate from notes -->
								<FileText class="w-16 h-16 mx-auto text-gray-400" />
								<h3>{statusMessages.no_recordings.title}</h3>
								<p>{statusMessages.no_recordings.description}</p>
								<div class="flex gap-2 justify-center mt-4">
									<Button variant="primary" onclick={handleGenerate} loading={$resultsStore.isGenerating}>
										{#snippet children()}
											<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
											</svg>
											메모로 회의록 생성
										{/snippet}
									</Button>
									<Button variant="secondary" onclick={() => goto(`/meetings/${meetingId}/record`)}>
										{#snippet children()}
											<Mic class="w-4 h-4 mr-1" />
											녹음하기
										{/snippet}
									</Button>
								</div>
								<p class="text-xs text-gray-400 mt-3">
									녹음 없이 생성하면 안건과 메모를 기반으로 요약합니다
								</p>
							{:else if processingStatus === 'uploaded'}
								<!-- Uploaded but not processed -->
								<FileAudio class="w-16 h-16 mx-auto text-blue-400" />
								<h3>{statusMessages.uploaded.title}</h3>
								<p>{statusMessages.uploaded.description}</p>
								<Button variant="primary" onclick={triggerSTT}>
									{#snippet children()}
										<RefreshCw class="w-4 h-4 mr-1" />
										텍스트 변환 시작
									{/snippet}
								</Button>
							{:else if processingStatus === 'processing'}
								<!-- Processing STT -->
								<div class="processing-animation">
									<Loader2 class="w-16 h-16 mx-auto text-yellow-500 animate-spin" />
								</div>
								<h3>{statusMessages.processing.title}</h3>
								<p>{statusMessages.processing.description}</p>
								<div class="text-sm text-gray-400 mt-2">
									자동으로 새로고침됩니다...
								</div>
							{:else if processingStatus === 'ready'}
								<!-- Ready to generate -->
								<svg class="w-16 h-16 mx-auto text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								<h3>{statusMessages.ready.title}</h3>
								<p>{statusMessages.ready.description}</p>
								<Button variant="primary" onclick={handleGenerate} loading={$resultsStore.isGenerating}>
									{#snippet children()}
										<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
										</svg>
										회의록 생성
									{/snippet}
								</Button>
							{:else if processingStatus === 'failed'}
								<!-- Failed -->
								<svg class="w-16 h-16 mx-auto text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								<h3>{statusMessages.failed.title}</h3>
								<p>{statusMessages.failed.description}</p>
								<Button variant="primary" onclick={triggerSTT}>
									{#snippet children()}
										<RefreshCw class="w-4 h-4 mr-1" />
										다시 시도
									{/snippet}
								</Button>
							{:else}
								<!-- Loading or unknown -->
								<LoadingSpinner />
								<h3>상태 확인 중...</h3>
							{/if}
						</div>
					{/snippet}
				</Card>
			{/if}
		</main>
	{/if}
</div>

<style>
	.results-page {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.loading-container {
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

	.error-banner,
	.generating-banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border-radius: 0.5rem;
	}

	.error-banner {
		background: #fef2f2;
		color: #dc2626;
	}

	.error-banner button {
		margin-left: auto;
		padding: 0.25rem;
		border: none;
		background: transparent;
		cursor: pointer;
	}

	.generating-banner {
		background: #eff6ff;
		color: #1d4ed8;
	}

	.results-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.tabs {
		display: flex;
		gap: 0.25rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.tab {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.75rem 1rem;
		border: none;
		background: transparent;
		font-size: 0.875rem;
		font-weight: 500;
		color: #6b7280;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		transition: all 0.15s;
	}

	.tab:hover {
		color: #374151;
	}

	.tab.active {
		color: #1d4ed8;
		border-bottom-color: #1d4ed8;
	}

	.tab-badge {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 20px;
		height: 20px;
		padding: 0 0.375rem;
		font-size: 0.75rem;
		font-weight: 600;
		background: #e5e7eb;
		border-radius: 9999px;
	}

	.tab.active .tab-badge {
		background: #dbeafe;
		color: #1d4ed8;
	}

	.tab-content {
		min-height: 400px;
	}

	.summary-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.summary-header h2 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.summary-meta {
		display: flex;
		gap: 0.75rem;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.version-selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.version-selector label {
		font-size: 0.875rem;
		color: #6b7280;
	}

	.version-selector select {
		padding: 0.375rem 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 3rem 1rem;
		text-align: center;
	}

	.empty-state h3 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.empty-state p {
		color: #6b7280;
		margin: 0;
	}
</style>
