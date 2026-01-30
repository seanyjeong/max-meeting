<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Breadcrumb, Button, LoadingSpinner } from '$lib/components';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import { resultsStore, hasResult } from '$lib/stores/results';
	import { api } from '$lib/api';
	import { ArrowLeft, Printer, Download, FileText, Image } from 'lucide-svelte';
	import type { MeetingDetail, Agenda } from '$lib/stores/meeting';

	// Type definitions
	interface Note {
		id: number;
		agenda_id: number;
		content: string;
		created_at: string;
	}

	interface Sketch {
		id: number;
		agenda_id: number;
		snapshot_url?: string;
		thumbnail_url?: string;
		created_at: string;
	}

	let meetingId = $derived(parseInt($page.params.id ?? '0'));
	let notes = $state<Note[]>([]);
	let sketches = $state<Sketch[]>([]);
	let showSketchModal = $state(false);
	let selectedSketchAgendaId = $state<number | null>(null);

	// Breadcrumb
	let breadcrumbItems = $derived([
		{ label: '홈', href: '/' },
		{ label: '회의', href: '/meetings' },
		{ label: $currentMeeting?.title || '회의', href: `/meetings/${meetingId}` },
		{ label: '결과', href: `/meetings/${meetingId}/results` },
		{ label: '회의록' }
	]);

	onMount(async () => {
		// Load meeting if not loaded
		if (!$currentMeeting || $currentMeeting.id !== meetingId) {
			$isLoading = true;
			try {
				const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
				$currentMeeting = response;
			} catch (error) {
				console.error('Failed to load meeting:', error);
				goto('/meetings');
				return;
			} finally {
				$isLoading = false;
			}
		}

		// Load results if not loaded
		if (!$hasResult) {
			await resultsStore.loadResult(meetingId);
		}

		// Load notes and sketches
		await Promise.all([loadNotes(), loadSketches()]);
	});

	async function loadNotes() {
		try {
			const response = await api.get<{ data: Note[] }>(`/meetings/${meetingId}/notes`);
			notes = response.data || [];
		} catch (error) {
			console.error('Failed to load notes:', error);
		}
	}

	async function loadSketches() {
		try {
			const response = await api.get<{ data: Sketch[] }>(`/meetings/${meetingId}/sketches`);
			sketches = response.data || [];
		} catch (error) {
			console.error('Failed to load sketches:', error);
		}
	}

	function getNotesForAgenda(agendaId: number): Note[] {
		return notes.filter(n => n.agenda_id === agendaId);
	}

	function getSketchesForAgenda(agendaId: number): Sketch[] {
		return sketches.filter(s => s.agenda_id === agendaId);
	}

	function getDiscussion(agendaId: number): string | null {
		const discussion = $resultsStore.agendaDiscussions.find(
			d => d.agenda_id === agendaId
		);
		return discussion?.summary || null;
	}

	function getKeyPoints(agendaId: number): string[] {
		const discussion = $resultsStore.agendaDiscussions.find(
			d => d.agenda_id === agendaId
		);
		return discussion?.key_points || [];
	}

	function handlePrint() {
		window.print();
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleString('ko-KR', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			weekday: 'long',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function openSketchModal(agendaId: number) {
		selectedSketchAgendaId = agendaId;
		showSketchModal = true;
	}

	function closeSketchModal() {
		showSketchModal = false;
		selectedSketchAgendaId = null;
	}

	// Get all agendas flattened with parent info for sketch modal
	function getAllAgendaIds(): number[] {
		const ids: number[] = [];
		for (const agenda of $currentMeeting?.agendas || []) {
			ids.push(agenda.id);
			for (const child of agenda.children || []) {
				ids.push(child.id);
			}
		}
		return ids;
	}

	function getAgendaTitle(agendaId: number): string {
		for (const agenda of $currentMeeting?.agendas || []) {
			if (agenda.id === agendaId) return agenda.title;
			for (const child of agenda.children || []) {
				if (child.id === agendaId) return child.title;
			}
		}
		return '알 수 없음';
	}
</script>

<svelte:head>
	<title>회의록 - {$currentMeeting?.title || '회의'} | MAX Meeting</title>
</svelte:head>

<div class="report-page">
	{#if $isLoading || $resultsStore.isLoading}
		<div class="loading-container">
			<LoadingSpinner />
			<p>회의록 로딩 중...</p>
		</div>
	{:else if !$currentMeeting}
		<div class="error-container">
			<p>회의를 찾을 수 없습니다.</p>
			<Button variant="secondary" onclick={() => goto('/meetings')}>
				{#snippet children()}
					<ArrowLeft class="w-4 h-4 mr-1" />
					목록으로
				{/snippet}
			</Button>
		</div>
	{:else}
		<!-- Header (not printed) -->
		<header class="page-header no-print">
			<div class="header-left">
				<Breadcrumb items={breadcrumbItems} />
			</div>
			<div class="header-actions">
				<Button variant="ghost" size="sm" onclick={() => goto(`/meetings/${meetingId}/results`)}>
					{#snippet children()}
						<ArrowLeft class="w-4 h-4 mr-1" />
						결과로 돌아가기
					{/snippet}
				</Button>
				<Button variant="primary" size="sm" onclick={handlePrint}>
					{#snippet children()}
						<Printer class="w-4 h-4 mr-1" />
						인쇄 / PDF 저장
					{/snippet}
				</Button>
			</div>
		</header>

		<!-- Main Report Content -->
		<main class="meeting-report">
			<!-- Report Header -->
			<header class="report-header">
				<h1 class="report-title">{$currentMeeting.title}</h1>
				<div class="report-meta">
					{#if $currentMeeting.scheduled_at}
						<div class="meta-item">
							<span class="meta-label">일시</span>
							<span class="meta-value">{formatDate($currentMeeting.scheduled_at)}</span>
						</div>
					{/if}
					{#if $currentMeeting.location}
						<div class="meta-item">
							<span class="meta-label">장소</span>
							<span class="meta-value">{$currentMeeting.location}</span>
						</div>
					{/if}
					{#if $currentMeeting.attendees && $currentMeeting.attendees.length > 0}
						<div class="meta-item">
							<span class="meta-label">참석자</span>
							<span class="meta-value">
								{$currentMeeting.attendees.map(a => a.contact?.name || '알 수 없음').join(', ')}
							</span>
						</div>
					{/if}
				</div>
			</header>

			<!-- Summary Section -->
			{#if $resultsStore.currentResult?.summary}
				<section class="report-section">
					<h2 class="section-title">회의 요약</h2>
					<div class="section-content summary-content">
						{$resultsStore.currentResult.summary}
					</div>
				</section>
			{/if}

			<!-- Agenda Sections -->
			{#if $currentMeeting.agendas && $currentMeeting.agendas.length > 0}
				<section class="report-section">
					<h2 class="section-title">안건별 상세</h2>

					{#each $currentMeeting.agendas as agenda, idx}
						<div class="agenda-block">
							<h3 class="agenda-title">
								<span class="agenda-number">{idx + 1}</span>
								{agenda.title}
							</h3>

							{#if agenda.description}
								<p class="agenda-description">{agenda.description}</p>
							{/if}

							<!-- Child Agendas -->
							{#if agenda.children && agenda.children.length > 0}
								{#each agenda.children as child, childIdx}
									<div class="child-agenda-block">
										<h4 class="child-title">
											{idx + 1}.{childIdx + 1} {child.title}
										</h4>

										{#if child.description}
											<p class="child-description">{child.description}</p>
										{/if}

										<!-- Discussion for child -->
										{@const childDiscussion = getDiscussion(child.id)}
										{#if childDiscussion}
											<div class="discussion-block">
												<h5 class="block-label">토론 내용</h5>
												<p>{childDiscussion}</p>
												{@const keyPoints = getKeyPoints(child.id)}
												{#if keyPoints.length > 0}
													<ul class="key-points">
														{#each keyPoints as point}
															<li>{point}</li>
														{/each}
													</ul>
												{/if}
											</div>
										{/if}

										<!-- Notes for child -->
										{@const childNotes = getNotesForAgenda(child.id)}
										{#if childNotes.length > 0}
											<div class="notes-block">
												<h5 class="block-label">메모</h5>
												{#each childNotes as note}
													<p class="note-content">{note.content}</p>
												{/each}
											</div>
										{/if}

										<!-- Sketches for child -->
										{@const childSketches = getSketchesForAgenda(child.id)}
										{#if childSketches.length > 0}
											<div class="sketches-block no-print">
												<button
													type="button"
													class="sketch-button"
													onclick={() => openSketchModal(child.id)}
												>
													<Image class="w-4 h-4" />
													필기 보기 ({childSketches.length}개)
												</button>
											</div>
										{/if}
									</div>
								{/each}
							{:else}
								<!-- No children - show parent agenda content -->
								{@const discussion = getDiscussion(agenda.id)}
								{#if discussion}
									<div class="discussion-block">
										<h5 class="block-label">토론 내용</h5>
										<p>{discussion}</p>
										{@const keyPoints = getKeyPoints(agenda.id)}
										{#if keyPoints.length > 0}
											<ul class="key-points">
												{#each keyPoints as point}
													<li>{point}</li>
												{/each}
											</ul>
										{/if}
									</div>
								{/if}

								<!-- Notes for parent agenda -->
								{@const agendaNotes = getNotesForAgenda(agenda.id)}
								{#if agendaNotes.length > 0}
									<div class="notes-block">
										<h5 class="block-label">메모</h5>
										{#each agendaNotes as note}
											<p class="note-content">{note.content}</p>
										{/each}
									</div>
								{/if}

								<!-- Sketches for parent agenda -->
								{@const agendaSketches = getSketchesForAgenda(agenda.id)}
								{#if agendaSketches.length > 0}
									<div class="sketches-block no-print">
										<button
											type="button"
											class="sketch-button"
											onclick={() => openSketchModal(agenda.id)}
										>
											<Image class="w-4 h-4" />
											필기 보기 ({agendaSketches.length}개)
										</button>
									</div>
								{/if}
							{/if}
						</div>
					{/each}
				</section>
			{/if}

			<!-- Action Items Section -->
			{#if $resultsStore.actionItems.length > 0}
				<section class="report-section">
					<h2 class="section-title">실행 항목</h2>
					<div class="action-items-list">
						{#each $resultsStore.actionItems as item, idx}
							<div class="action-item">
								<span class="action-checkbox">☐</span>
								<span class="action-content">{item.content}</span>
								{#if item.assignee_name}
									<span class="action-assignee">- {item.assignee_name}</span>
								{/if}
								{#if item.due_date}
									<span class="action-due">(마감: {new Date(item.due_date).toLocaleDateString('ko-KR')})</span>
								{/if}
							</div>
						{/each}
					</div>
				</section>
			{/if}

			<!-- Footer -->
			<footer class="report-footer">
				<p>MAX Meeting으로 생성됨 - {new Date().toLocaleDateString('ko-KR')}</p>
			</footer>
		</main>
	{/if}
</div>

<!-- Sketch Modal -->
{#if showSketchModal && selectedSketchAgendaId}
	<div class="modal-overlay" onclick={closeSketchModal} role="presentation">
		<div class="modal-content" onclick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
			<header class="modal-header">
				<h3>필기 내용 - {getAgendaTitle(selectedSketchAgendaId)}</h3>
				<button type="button" class="modal-close" onclick={closeSketchModal}>×</button>
			</header>
			<div class="modal-body">
				{@const modalSketches = getSketchesForAgenda(selectedSketchAgendaId)}
				{#if modalSketches.length === 0}
					<p class="empty-sketches">필기 내용이 없습니다.</p>
				{:else}
					<div class="sketch-gallery">
						{#each modalSketches as sketch, idx}
							<div class="sketch-item">
								<span class="sketch-number">{idx + 1}</span>
								{#if sketch.snapshot_url}
									<img src={sketch.snapshot_url} alt="필기 {idx + 1}" class="sketch-image" />
								{:else if sketch.thumbnail_url}
									<img src={sketch.thumbnail_url} alt="필기 {idx + 1}" class="sketch-image" />
								{:else}
									<div class="sketch-placeholder">
										<FileText class="w-8 h-8" />
										<span>미리보기 없음</span>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.report-page {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
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

	/* Header (screen only) */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem;
		background: white;
		border-bottom: 1px solid #e5e7eb;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-actions {
		display: flex;
		gap: 0.5rem;
	}

	/* Main Report */
	.meeting-report {
		max-width: 800px;
		margin: 0 auto;
		padding: 2rem;
		background: white;
	}

	/* Report Header */
	.report-header {
		border-bottom: 2px solid #1d4ed8;
		padding-bottom: 1.5rem;
		margin-bottom: 2rem;
	}

	.report-title {
		font-size: 1.75rem;
		font-weight: 700;
		color: #111827;
		margin: 0 0 1rem 0;
	}

	.report-meta {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.meta-item {
		display: flex;
		gap: 0.75rem;
	}

	.meta-label {
		font-weight: 600;
		color: #374151;
		min-width: 60px;
	}

	.meta-value {
		color: #4b5563;
	}

	/* Sections */
	.report-section {
		margin-bottom: 2rem;
	}

	.section-title {
		font-size: 1.25rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 1rem 0;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.section-content {
		color: #374151;
		line-height: 1.75;
	}

	.summary-content {
		white-space: pre-wrap;
	}

	/* Agenda Blocks */
	.agenda-block {
		margin-bottom: 1.5rem;
		padding: 1rem;
		background: #f9fafb;
		border-radius: 0.5rem;
		page-break-inside: avoid;
	}

	.agenda-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.125rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 0.75rem 0;
	}

	.agenda-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: #1d4ed8;
		color: white;
		border-radius: 50%;
		font-size: 0.875rem;
		font-weight: 700;
	}

	.agenda-description {
		color: #6b7280;
		font-size: 0.875rem;
		margin: 0 0 1rem 0;
		padding-left: 2.5rem;
	}

	/* Child Agenda Blocks */
	.child-agenda-block {
		margin: 1rem 0 1rem 2.5rem;
		padding: 1rem;
		background: white;
		border-left: 3px solid #3b82f6;
		border-radius: 0 0.375rem 0.375rem 0;
	}

	.child-title {
		font-size: 1rem;
		font-weight: 600;
		color: #374151;
		margin: 0 0 0.5rem 0;
	}

	.child-description {
		color: #6b7280;
		font-size: 0.875rem;
		margin: 0 0 0.75rem 0;
	}

	/* Discussion Block */
	.discussion-block {
		margin: 0.75rem 0;
	}

	.block-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		margin: 0 0 0.5rem 0;
	}

	.discussion-block p {
		color: #374151;
		line-height: 1.625;
		margin: 0;
	}

	.key-points {
		margin: 0.75rem 0 0 1.25rem;
		padding: 0;
		list-style-type: disc;
	}

	.key-points li {
		color: #4b5563;
		margin-bottom: 0.25rem;
	}

	/* Notes Block */
	.notes-block {
		margin: 0.75rem 0;
		padding: 0.75rem;
		background: #fef3c7;
		border-radius: 0.375rem;
	}

	.note-content {
		color: #92400e;
		margin: 0.25rem 0;
		white-space: pre-wrap;
	}

	/* Sketches Block */
	.sketches-block {
		margin: 0.75rem 0;
	}

	.sketch-button {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		color: #4b5563;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.sketch-button:hover {
		background: #f3f4f6;
		border-color: #9ca3af;
	}

	/* Action Items */
	.action-items-list {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.action-item {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		padding: 0.75rem;
		background: #f9fafb;
		border-radius: 0.375rem;
	}

	.action-checkbox {
		font-size: 1.125rem;
		color: #9ca3af;
	}

	.action-content {
		flex: 1;
		color: #374151;
	}

	.action-assignee {
		color: #6b7280;
		font-size: 0.875rem;
	}

	.action-due {
		color: #dc2626;
		font-size: 0.75rem;
	}

	/* Footer */
	.report-footer {
		margin-top: 3rem;
		padding-top: 1rem;
		border-top: 1px solid #e5e7eb;
		text-align: center;
		font-size: 0.75rem;
		color: #9ca3af;
	}

	/* Modal */
	.modal-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 50;
	}

	.modal-content {
		background: white;
		border-radius: 0.75rem;
		width: 90%;
		max-width: 800px;
		max-height: 90vh;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.modal-header h3 {
		font-size: 1.125rem;
		font-weight: 600;
		margin: 0;
	}

	.modal-close {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 1.5rem;
		color: #6b7280;
		background: transparent;
		border: none;
		border-radius: 0.25rem;
		cursor: pointer;
	}

	.modal-close:hover {
		background: #f3f4f6;
	}

	.modal-body {
		padding: 1rem;
		overflow-y: auto;
	}

	.empty-sketches {
		text-align: center;
		color: #6b7280;
		padding: 2rem;
	}

	.sketch-gallery {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 1rem;
	}

	.sketch-item {
		position: relative;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.sketch-number {
		position: absolute;
		top: 0.5rem;
		left: 0.5rem;
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.6);
		color: white;
		font-size: 0.75rem;
		font-weight: 600;
		border-radius: 50%;
	}

	.sketch-image {
		width: 100%;
		height: auto;
		display: block;
	}

	.sketch-placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 2rem;
		color: #9ca3af;
		gap: 0.5rem;
	}

	/* Print Styles */
	@media print {
		.no-print {
			display: none !important;
		}

		.report-page {
			background: white;
		}

		.meeting-report {
			max-width: none;
			padding: 0;
			font-size: 11pt;
			line-height: 1.5;
		}

		.report-header {
			border-bottom-width: 2px;
		}

		.agenda-block {
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.child-agenda-block {
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.action-item {
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.report-section {
			page-break-inside: avoid;
		}
	}
</style>
