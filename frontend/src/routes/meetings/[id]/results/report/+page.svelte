<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Breadcrumb, Button, LoadingSpinner } from '$lib/components';
	import PostItCanvas from '$lib/components/results/PostItCanvas.svelte';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import { resultsStore, hasResult } from '$lib/stores/results';
	import { api } from '$lib/api';
	import { ArrowLeft, Printer, FileText, CheckCircle2 } from 'lucide-svelte';
	import type { MeetingDetail, Agenda } from '$lib/stores/meeting';
	import { formatDateTime } from '$lib/utils/format';
	import { logger } from '$lib/utils/logger';

	// Type definitions
	interface Note {
		id: number;
		agenda_id: number | null;
		content: string;
		position_x: number | null;
		position_y: number | null;
		rotation: number | null;
		is_visible: boolean;
		z_index: number;
		created_at: string;
	}

	let meetingId = $derived(parseInt($page.params.id ?? '0'));
	let notes = $state<Note[]>([]);

	// Breadcrumb
	let breadcrumbItems = $derived([
		{ label: '홈', href: '/' },
		{ label: '회의', href: '/meetings' },
		{ label: $currentMeeting?.title || '회의', href: `/meetings/${meetingId}` },
		{ label: '결과', href: `/meetings/${meetingId}/results` },
		{ label: '회의록' }
	]);

	// PostIt colors by agenda index
	const postItColors: Array<'yellow' | 'pink' | 'green' | 'blue'> = ['yellow', 'pink', 'green', 'blue'];
	function getPostItColor(index: number): 'yellow' | 'pink' | 'green' | 'blue' {
		return postItColors[index % postItColors.length];
	}

	onMount(async () => {
		// Load meeting if not loaded
		if (!$currentMeeting || $currentMeeting.id !== meetingId) {
			$isLoading = true;
			try {
				const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
				$currentMeeting = response;
			} catch (error) {
				logger.error('Failed to load meeting:', error);
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

		// Load notes
		await loadNotes();
	});

	async function loadNotes() {
		try {
			const response = await api.get<{ data: Note[] }>(`/meetings/${meetingId}/notes`);
			notes = response.data || [];
		} catch (error) {
			logger.error('Failed to load notes:', error);
		}
	}

	function getNotesForAgenda(agendaId: number): Note[] {
		return notes.filter(n => n.agenda_id === agendaId);
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

	function getActionItemsForAgenda(agendaId: number) {
		return $resultsStore.actionItems.filter(item => item.agenda_id === agendaId);
	}

	function handlePrint() {
		window.print();
	}

	// Check if agenda has any right-side content (notes only, no sketches)
	function hasRightContent(agendaId: number): boolean {
		return getNotesForAgenda(agendaId).length > 0;
	}

	// Check if agenda has any content at all (including children)
	function agendaHasContent(agenda: Agenda): boolean {
		if (getDiscussion(agenda.id) || hasRightContent(agenda.id)) return true;
		if (agenda.children) {
			return agenda.children.some(child =>
				getDiscussion(child.id) || hasRightContent(child.id)
			);
		}
		return false;
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
							<span class="meta-value">{formatDateTime($currentMeeting.scheduled_at)}</span>
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
					<h2 class="section-title">
						<FileText class="w-5 h-5" />
						회의 요약
					</h2>
					<div class="section-content summary-content">
						{$resultsStore.currentResult.summary}
					</div>
				</section>
			{/if}

			<!-- Agenda Sections with 2-Column Layout -->
			{#if $currentMeeting.agendas && $currentMeeting.agendas.length > 0}
				<section class="report-section">
					<h2 class="section-title">
						<FileText class="w-5 h-5" />
						안건별 상세
					</h2>

					{#each $currentMeeting.agendas as agenda, idx}
						<div class="agenda-block">
							<h3 class="agenda-title">
								<span class="agenda-number">{idx + 1}</span>
								{agenda.title}
							</h3>

							{#if agenda.description}
								<p class="agenda-description">{agenda.description}</p>
							{/if}

							<!-- 2-Column Layout for agenda content -->
							<div class="agenda-content-grid" class:single-column={!hasRightContent(agenda.id) && !(agenda.children?.some(c => hasRightContent(c.id)))}>
								<!-- Left Column: Discussion -->
								<div class="content-left">
									{#if agenda.children && agenda.children.length > 0}
										<!-- Child Agendas -->
										{#each agenda.children as child, childIdx}
											<div class="child-agenda-block">
												<h4 class="child-title">
													{idx + 1}.{childIdx + 1} {child.title}
												</h4>

												{#if child.description}
													<p class="child-description">{child.description}</p>
												{/if}

												<!-- Discussion for child -->
												{#if getDiscussion(child.id)}
													<div class="discussion-block">
														<h5 class="block-label">토론 내용</h5>
														<p>{getDiscussion(child.id)}</p>
														{#if getKeyPoints(child.id).length > 0}
															<ul class="key-points">
																{#each getKeyPoints(child.id) as point}
																	<li>{point}</li>
																{/each}
															</ul>
														{/if}
													</div>
												{/if}

												<!-- Action items for child -->
												{#if getActionItemsForAgenda(child.id).length > 0}
													<div class="action-items-inline">
														<h5 class="block-label">실행 항목</h5>
														{#each getActionItemsForAgenda(child.id) as item}
															<div class="action-item-mini">
																<CheckCircle2 class="w-4 h-4 text-blue-500" />
																<span>{item.title}</span>
																{#if item.assignee}
																	<span class="assignee">({item.assignee})</span>
																{/if}
															</div>
														{/each}
													</div>
												{/if}
											</div>
										{/each}
									{:else}
										<!-- No children - show parent agenda content -->
										{#if getDiscussion(agenda.id)}
											<div class="discussion-block">
												<h5 class="block-label">토론 내용</h5>
												<p>{getDiscussion(agenda.id)}</p>
												{#if getKeyPoints(agenda.id).length > 0}
													<ul class="key-points">
														{#each getKeyPoints(agenda.id) as point}
															<li>{point}</li>
														{/each}
													</ul>
												{/if}
											</div>
										{/if}

										<!-- Action items for parent -->
										{#if getActionItemsForAgenda(agenda.id).length > 0}
											<div class="action-items-inline">
												<h5 class="block-label">실행 항목</h5>
												{#each getActionItemsForAgenda(agenda.id) as item}
													<div class="action-item-mini">
														<CheckCircle2 class="w-4 h-4 text-blue-500" />
														<span>{item.title}</span>
														{#if item.assignee}
															<span class="assignee">({item.assignee})</span>
														{/if}
													</div>
												{/each}
											</div>
										{/if}
									{/if}
								</div>

								<!-- Right Column: Notes -->
								<div class="content-right">
									<!-- Parent agenda notes -->
									{#if getNotesForAgenda(agenda.id).length > 0}
										<div class="notes-section">
											<div class="notes-label">메모</div>
											<PostItCanvas
												bind:notes={notes}
												{meetingId}
												agendaId={agenda.id}
												editable={true}
												onupdate={loadNotes}
											/>
										</div>
									{/if}
									<!-- Child agenda notes -->
									{#if agenda.children && agenda.children.length > 0}
										{#each agenda.children as child}
											{#if getNotesForAgenda(child.id).length > 0}
												<div class="notes-section">
													<div class="notes-label">{child.title} 메모</div>
													<PostItCanvas
														bind:notes={notes}
														{meetingId}
														agendaId={child.id}
														editable={true}
														onupdate={loadNotes}
													/>
												</div>
											{/if}
										{/each}
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</section>
			{/if}

			<!-- Action Items Summary -->
			{#if $resultsStore.actionItems.length > 0}
				<section class="report-section action-items-section">
					<h2 class="section-title">
						<CheckCircle2 class="w-5 h-5" />
						실행 항목 요약
					</h2>
					<div class="action-items-table">
						<table>
							<thead>
								<tr>
									<th>항목</th>
									<th>담당자</th>
									<th>기한</th>
									<th>우선순위</th>
								</tr>
							</thead>
							<tbody>
								{#each $resultsStore.actionItems as item}
									<tr>
										<td>{item.title}</td>
										<td>{item.assignee || '-'}</td>
										<td>{item.due_date ? new Date(item.due_date).toLocaleDateString('ko-KR') : '-'}</td>
										<td>
											<span class="priority priority-{item.priority}">
												{item.priority === 'high' ? '높음' : item.priority === 'medium' ? '중간' : '낮음'}
											</span>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</section>
			{/if}

			<!-- Footer -->
			<footer class="report-footer">
				<p>MAX Meeting으로 생성됨 | {new Date().toLocaleDateString('ko-KR')}</p>
			</footer>
		</main>
	{/if}
</div>

<style>
	.report-page {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		background: #f3f4f6;
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
		padding: 1rem 2rem;
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

	/* Main Report - WIDER! */
	.meeting-report {
		max-width: 1100px;
		margin: 2rem auto;
		padding: 3rem;
		background: white;
		box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
		border-radius: 0.5rem;
	}

	/* Report Header */
	.report-header {
		border-bottom: 3px solid #1d4ed8;
		padding-bottom: 1.5rem;
		margin-bottom: 2rem;
	}

	.report-title {
		font-size: 2rem;
		font-weight: 700;
		color: #111827;
		margin: 0 0 1rem 0;
	}

	.report-meta {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 0.75rem;
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
		margin-bottom: 2.5rem;
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 1.375rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 1.25rem 0;
		padding-bottom: 0.75rem;
		border-bottom: 2px solid #e5e7eb;
	}

	.section-content {
		color: #374151;
		line-height: 1.75;
	}

	.summary-content {
		white-space: pre-wrap;
		background: #f9fafb;
		padding: 1.5rem;
		border-radius: 0.5rem;
		border-left: 4px solid #3b82f6;
	}

	/* Agenda Blocks */
	.agenda-block {
		margin-bottom: 2rem;
		padding: 1.5rem;
		background: #fafafa;
		border-radius: 0.75rem;
		border: 1px solid #e5e7eb;
		page-break-inside: avoid;
	}

	.agenda-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.25rem;
		font-weight: 600;
		color: #111827;
		margin: 0 0 1rem 0;
	}

	.agenda-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: #1d4ed8;
		color: white;
		border-radius: 50%;
		font-size: 1rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.agenda-description {
		color: #6b7280;
		font-size: 0.9375rem;
		margin: 0 0 1rem 2.75rem;
	}

	/* 2-Column Grid Layout */
	.agenda-content-grid {
		display: grid;
		grid-template-columns: 1fr 340px;
		gap: 2rem;
		margin-top: 1rem;
	}

	.agenda-content-grid.single-column {
		grid-template-columns: 1fr;
	}

	.content-left {
		min-width: 0;
	}

	.content-right {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* Child Agenda Blocks */
	.child-agenda-block {
		margin-bottom: 1.5rem;
		padding: 1.25rem;
		background: white;
		border-left: 4px solid #3b82f6;
		border-radius: 0 0.5rem 0.5rem 0;
		box-shadow: 0 1px 3px rgba(0,0,0,0.05);
	}

	.child-title {
		font-size: 1.0625rem;
		font-weight: 600;
		color: #374151;
		margin: 0 0 0.75rem 0;
	}

	.child-description {
		color: #6b7280;
		font-size: 0.875rem;
		margin: 0 0 1rem 0;
	}

	/* Discussion Block */
	.discussion-block {
		margin: 1rem 0;
	}

	.block-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #6b7280;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin: 0 0 0.5rem 0;
	}

	.discussion-block p {
		color: #374151;
		line-height: 1.7;
		margin: 0;
	}

	.key-points {
		margin: 0.75rem 0 0 1.25rem;
		padding: 0;
		list-style-type: disc;
	}

	.key-points li {
		color: #4b5563;
		margin-bottom: 0.375rem;
		line-height: 1.5;
	}

	/* Inline Action Items */
	.action-items-inline {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px dashed #e5e7eb;
	}

	.action-item-mini {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0;
		font-size: 0.875rem;
		color: #374151;
	}

	.action-item-mini .assignee {
		color: #6b7280;
		font-size: 0.8125rem;
	}

	/* Notes Section (Right Column) */
	.notes-section {
		background: #fffbeb;
		padding: 1rem;
		border-radius: 0.5rem;
	}

	.notes-label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #92400e;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		margin-bottom: 0.75rem;
	}

	.postit-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	/* Action Items Table */
	.action-items-section {
		background: #f0fdf4;
		padding: 1.5rem;
		border-radius: 0.75rem;
		margin-top: 2rem;
	}

	.action-items-table {
		overflow-x: auto;
	}

	.action-items-table table {
		width: 100%;
		border-collapse: collapse;
	}

	.action-items-table th,
	.action-items-table td {
		padding: 0.75rem 1rem;
		text-align: left;
		border-bottom: 1px solid #d1fae5;
	}

	.action-items-table th {
		background: #dcfce7;
		font-weight: 600;
		color: #166534;
		font-size: 0.8125rem;
		text-transform: uppercase;
	}

	.action-items-table td {
		color: #374151;
		font-size: 0.9375rem;
	}

	.priority {
		display: inline-block;
		padding: 0.25rem 0.625rem;
		border-radius: 9999px;
		font-size: 0.75rem;
		font-weight: 600;
	}

	.priority-high {
		background: #fee2e2;
		color: #991b1b;
	}

	.priority-medium {
		background: #fef3c7;
		color: #92400e;
	}

	.priority-low {
		background: #dbeafe;
		color: #1e40af;
	}

	/* Footer */
	.report-footer {
		margin-top: 3rem;
		padding-top: 1.5rem;
		border-top: 1px solid #e5e7eb;
		text-align: center;
		color: #9ca3af;
		font-size: 0.875rem;
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
			margin: 0;
			padding: 1cm 1.5cm;
			box-shadow: none;
			border-radius: 0;
		}

		.report-section {
			margin-bottom: 1.5rem;
		}

		.agenda-content-grid {
			grid-template-columns: 1fr 240px;
			gap: 1rem;
		}

		.agenda-block {
			margin-bottom: 1rem;
			padding: 1rem;
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.child-agenda-block {
			margin-bottom: 0.75rem;
			padding: 0.75rem;
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.action-items-section {
			page-break-inside: avoid;
			break-inside: avoid;
		}

		.summary-content {
			padding: 1rem;
		}

		/* Force colors on print */
		.agenda-number,
		.notes-section,
		.action-items-section,
		.priority {
			-webkit-print-color-adjust: exact;
			print-color-adjust: exact;
		}
	}

	/* Responsive */
	@media (max-width: 900px) {
		.agenda-content-grid {
			grid-template-columns: 1fr;
		}

		.content-right {
			border-top: 1px dashed #e5e7eb;
			padding-top: 1rem;
		}
	}
</style>
