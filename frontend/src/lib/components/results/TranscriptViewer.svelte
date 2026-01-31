<script lang="ts">
	import { resultsStore, type TranscriptSegment } from '$lib/stores/results';
	import type { Agenda } from '$lib/stores/meeting';
	import { currentMeeting } from '$lib/stores/meeting';
	import { api } from '$lib/api';
	import DOMPurify from 'dompurify';

	interface SegmentSuggestion {
		segment_index: number;
		segment_text: string;
		current_agenda_id: number | null;
		current_agenda_title: string | null;
		suggested_agenda_id: number | null;
		suggested_agenda_title: string | null;
		confidence: number;
		reason: string;
	}

	interface Props {
		agendas?: Agenda[];
		onSegmentClick?: (segment: TranscriptSegment) => void;
		highlightText?: string;
	}

	let { agendas = [], onSegmentClick, highlightText = '' }: Props = $props();

	// Segment analysis state
	let suggestions = $state<SegmentSuggestion[]>([]);
	let isAnalyzing = $state(false);
	let analysisError = $state<string | null>(null);
	let analysisComplete = $state(false);
	let showSuggestions = $state(true);

	// Filter to only root-level agendas (parent_id is null/undefined)
	let rootAgendas = $derived(agendas.filter(a => a.parent_id === null || a.parent_id === undefined));

	let searchQuery = $state('');
	let filterSpeaker = $state<string | null>(null);
	let selectedAgendaId = $state<number | 'all'>('all');
	let selectedChildId = $state<number | 'all'>('all');
	let showChildDropdown = $state<number | null>(null);
	let dropdownPosition = $state({ top: 0, left: 0 });

	// Get unique speakers
	let speakers = $derived(
		[...new Set($resultsStore.transcriptSegments
			.map(s => s.speaker_label || s.speaker_name)
			.filter(Boolean)
		)] as string[]
	);

	// Check if segment is within agenda's time ranges
	function isSegmentInAgenda(segment: TranscriptSegment, agenda: Agenda): boolean {
		if (agenda.time_segments && agenda.time_segments.length > 0) {
			return agenda.time_segments.some(
				ts => segment.start >= ts.start && segment.start < (ts.end ?? Infinity)
			);
		}
		// Fallback to started_at_seconds (legacy)
		if (agenda.started_at_seconds !== null) {
			// Find next agenda for end boundary
			const sortedAgendas = agendas
				.filter(a => a.started_at_seconds !== null)
				.sort((a, b) => (a.started_at_seconds ?? 0) - (b.started_at_seconds ?? 0));
			const idx = sortedAgendas.findIndex(a => a.id === agenda.id);
			const startTime = agenda.started_at_seconds;
			const endTime = idx >= 0 && idx + 1 < sortedAgendas.length
				? sortedAgendas[idx + 1].started_at_seconds ?? Infinity
				: Infinity;
			return segment.start >= startTime && segment.start < endTime;
		}
		return false;
	}

	// 재귀적으로 안건과 모든 자손 안건을 체크
	function isSegmentInAgendaRecursive(segment: TranscriptSegment, agenda: Agenda): boolean {
		// 현재 안건 체크
		if (isSegmentInAgenda(segment, agenda)) {
			return true;
		}
		// 자식안건들 재귀 체크
		if (agenda.children && agenda.children.length > 0) {
			for (const child of agenda.children) {
				if (isSegmentInAgendaRecursive(segment, child)) {
					return true;
				}
			}
		}
		return false;
	}

	// Filter segments
	let filteredSegments = $derived(
		$resultsStore.transcriptSegments.filter(segment => {
			const matchesSearch = !searchQuery ||
				segment.text.toLowerCase().includes(searchQuery.toLowerCase());
			const matchesSpeaker = !filterSpeaker ||
				segment.speaker_label === filterSpeaker ||
				segment.speaker_name === filterSpeaker;

			// Agenda filter
			let matchesAgenda = true;
			if (selectedAgendaId !== 'all' && rootAgendas.length > 0) {
				const agenda = rootAgendas.find(a => a.id === selectedAgendaId);
				if (agenda) {
					// 자식/손자안건 필터 적용
					if (selectedChildId !== 'all' && agenda.children) {
						// 먼저 자식안건에서 찾기
						let child = agenda.children.find(c => c.id === selectedChildId);
						// 자식안건에서 못 찾으면 손자안건에서 찾기
						if (!child) {
							for (const c of agenda.children) {
								if (c.children) {
									const grandchild = c.children.find(gc => gc.id === selectedChildId);
									if (grandchild) {
										child = grandchild;
										break;
									}
								}
							}
						}
						if (child) {
							// 재귀적으로 하위 안건 포함
							matchesAgenda = isSegmentInAgendaRecursive(segment, child);
						} else {
							matchesAgenda = false;
						}
					} else {
						// 대안건 전체 (자식안건 + 손자안건 모두 포함)
						matchesAgenda = isSegmentInAgendaRecursive(segment, agenda);
					}
				}
			}

			return matchesSearch && matchesSpeaker && matchesAgenda;
		})
	);

	function selectAgenda(agendaId: number | 'all', childId: number | 'all' = 'all') {
		selectedAgendaId = agendaId;
		selectedChildId = childId;
		showChildDropdown = null;
	}

	function toggleChildDropdown(agendaId: number, event: MouseEvent) {
		if (showChildDropdown === agendaId) {
			showChildDropdown = null;
		} else {
			// 버튼 위치 기반으로 드롭다운 위치 계산
			const button = event.currentTarget as HTMLElement;
			const rect = button.getBoundingClientRect();
			dropdownPosition = {
				top: rect.bottom + 4,
				left: rect.left
			};
			showChildDropdown = agendaId;
		}
	}

	// Calculate total duration for an agenda
	function getAgendaDuration(agenda: Agenda): number {
		if (agenda.time_segments && agenda.time_segments.length > 0) {
			return agenda.time_segments.reduce((sum, seg) => {
				const end = seg.end ?? 0;
				return sum + Math.max(0, end - seg.start);
			}, 0);
		}
		return 0;
	}

	function formatDuration(seconds: number): string {
		if (seconds === 0) return '';
		const mins = Math.floor(seconds / 60);
		const secs = seconds % 60;
		if (mins === 0) return `${secs}초`;
		return `${mins}분`;
	}

	function truncate(text: string, maxLen: number): string {
		if (text.length <= maxLen) return text;
		return text.slice(0, maxLen - 1) + '…';
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}

	function highlightSearchText(text: string): string {
		const query = searchQuery || highlightText;
		if (!query || !text) return DOMPurify.sanitize(text);

		const escapedText = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#39;');

		const escapedQuery = escapeRegex(query);
		const regex = new RegExp(`(${escapedQuery})`, 'gi');
		const highlighted = escapedText.replace(regex, '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>');

		return DOMPurify.sanitize(highlighted);
	}

	function escapeRegex(str: string): string {
		return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function getSpeakerColor(speaker: string | null): string {
		if (!speaker) return '#6b7280';
		const colors = [
			'#3b82f6', '#22c55e', '#f59e0b', '#ef4444',
			'#8b5cf6', '#ec4899', '#06b6d4', '#f97316'
		];
		const index = speakers.indexOf(speaker);
		return colors[index % colors.length];
	}

	function handleSegmentClick(segment: TranscriptSegment) {
		onSegmentClick?.(segment);
	}

	// 외부 클릭 시 드롭다운 닫기
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.agenda-tab-wrapper') && !target.closest('.child-dropdown')) {
			showChildDropdown = null;
		}
	}

	$effect(() => {
		if (showChildDropdown !== null) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});

	// Get suggestion for a segment by index
	function getSuggestion(segmentIndex: number): SegmentSuggestion | undefined {
		return suggestions.find(s => s.segment_index === segmentIndex);
	}

	// Analyze segments for mismatches
	async function analyzeSegments() {
		const meetingId = $currentMeeting?.id;
		if (!meetingId) return;

		isAnalyzing = true;
		analysisError = null;
		analysisComplete = false;

		try {
			const response = await api.post(`/meetings/${meetingId}/analyze-segments`, {
				force_reanalyze: false
			}) as { suggestions: SegmentSuggestion[] };
			suggestions = response.suggestions || [];
			analysisComplete = true;
		} catch (error: any) {
			analysisError = error.message || '분석에 실패했습니다';
		} finally {
			isAnalyzing = false;
		}
	}

	// Accept a suggestion and move segment
	async function acceptSuggestion(suggestion: SegmentSuggestion) {
		const meetingId = $currentMeeting?.id;
		if (!meetingId || !suggestion.suggested_agenda_id) return;

		try {
			await api.patch(`/meetings/${meetingId}/segments/${suggestion.segment_index}/move`, {
				target_agenda_id: suggestion.suggested_agenda_id,
				accept_suggestion: true
			});
			// Remove from suggestions list
			suggestions = suggestions.filter(s => s.segment_index !== suggestion.segment_index);
		} catch (error: any) {
			alert('세그먼트 이동에 실패했습니다: ' + (error.message || ''));
		}
	}

	// Reject a suggestion
	async function rejectSuggestion(suggestion: SegmentSuggestion) {
		const meetingId = $currentMeeting?.id;
		if (!meetingId) return;

		try {
			await api.patch(`/meetings/${meetingId}/segments/${suggestion.segment_index}/move`, {
				target_agenda_id: suggestion.current_agenda_id || 0,
				accept_suggestion: false
			});
			// Remove from suggestions list
			suggestions = suggestions.filter(s => s.segment_index !== suggestion.segment_index);
		} catch {
			// Silently fail
		}
	}
</script>

<div class="transcript-viewer">
	<!-- Agenda Tabs with Child Dropdown -->
	{#if rootAgendas.length > 0}
		<div class="agenda-tabs">
			<button
				type="button"
				class="agenda-tab {selectedAgendaId === 'all' ? 'active' : ''}"
				onclick={() => selectAgenda('all')}
			>
				전체
			</button>
			{#each rootAgendas as agenda (agenda.id)}
				{@const duration = getAgendaDuration(agenda)}
				{@const hasSegments = agenda.time_segments?.length || agenda.started_at_seconds !== null}
				{@const hasChildren = agenda.children && agenda.children.length > 0}
				<div class="agenda-tab-wrapper">
					<button
						type="button"
						class="agenda-tab {selectedAgendaId === agenda.id ? 'active' : ''} {!hasSegments && !hasChildren ? 'disabled' : ''}"
						onclick={(e) => hasChildren ? toggleChildDropdown(agenda.id, e) : (hasSegments && selectAgenda(agenda.id))}
						disabled={!hasSegments && !hasChildren}
					>
						<span class="agenda-num">{agenda.order_num}.</span>
						<span class="agenda-title">{truncate(agenda.title, 8)}</span>
						{#if hasChildren}
							<svg class="w-3 h-3 ml-1 transition-transform {showChildDropdown === agenda.id ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
							</svg>
						{:else if duration > 0}
							<span class="agenda-duration">({formatDuration(duration)})</span>
						{/if}
					</button>

					<!-- 자식안건 드롭다운 -->
					{#if hasChildren && showChildDropdown === agenda.id}
						<div class="child-dropdown" style="top: {dropdownPosition.top}px; left: {dropdownPosition.left}px;">
							<button
								type="button"
								class="child-item {selectedAgendaId === agenda.id && selectedChildId === 'all' ? 'active' : ''}"
								onclick={() => selectAgenda(agenda.id, 'all')}
							>
								전체 ({agenda.order_num})
							</button>
							{#each agenda.children as child, idx (child.id)}
								{@const childHasSegments = child.time_segments?.length || child.started_at_seconds !== null}
								{@const hasGrandchildren = child.children && child.children.length > 0}
								<button
									type="button"
									class="child-item {selectedChildId === child.id ? 'active' : ''} {!childHasSegments && !hasGrandchildren ? 'disabled' : ''}"
									onclick={() => (childHasSegments || hasGrandchildren) && selectAgenda(agenda.id, child.id)}
									disabled={!childHasSegments && !hasGrandchildren}
								>
									{agenda.order_num}.{idx + 1} {truncate(child.title, 12)}
								</button>
								<!-- 손자안건 (Grandchildren) -->
								{#if hasGrandchildren}
									{#each child.children as grandchild, gidx (grandchild.id)}
										{@const gcHasSegments = grandchild.time_segments?.length || grandchild.started_at_seconds !== null}
										<button
											type="button"
											class="child-item grandchild-item {selectedChildId === grandchild.id ? 'active' : ''} {!gcHasSegments ? 'disabled' : ''}"
											onclick={() => gcHasSegments && selectAgenda(agenda.id, grandchild.id)}
											disabled={!gcHasSegments}
										>
											{agenda.order_num}.{idx + 1}.{gidx + 1} {truncate(grandchild.title, 10)}
										</button>
									{/each}
								{/if}
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{/if}

	<!-- Analysis Controls -->
	<div class="analysis-controls">
		<button
			type="button"
			class="analyze-btn"
			onclick={analyzeSegments}
			disabled={isAnalyzing}
		>
			{#if isAnalyzing}
				<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				분석 중...
			{:else}
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
				</svg>
				안건 재매칭 분석
			{/if}
		</button>

		{#if suggestions.length > 0}
			<span class="suggestion-count">
				{suggestions.length}개 제안
			</span>
			<button
				type="button"
				class="toggle-suggestions"
				onclick={() => showSuggestions = !showSuggestions}
			>
				{showSuggestions ? '제안 숨기기' : '제안 표시'}
			</button>
		{:else if analysisComplete}
			<span class="analysis-success">✓ 모든 세그먼트가 올바르게 매칭됨</span>
		{/if}

		{#if analysisError}
			<span class="analysis-error">{analysisError}</span>
		{/if}
	</div>

	<!-- Header / Filters -->
	<div class="viewer-header">
		<h3 class="title">대화 내용</h3>

		<div class="filters">
			<!-- Search -->
			<div class="search-box">
				<svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					type="text"
					class="search-input"
					placeholder="검색..."
					bind:value={searchQuery}
				/>
				{#if searchQuery}
					<button
						type="button"
						class="clear-btn"
						onclick={() => searchQuery = ''}
						aria-label="Clear search"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				{/if}
			</div>

			<!-- Speaker Filter -->
			{#if speakers.length > 0}
				<select
					class="speaker-filter"
					bind:value={filterSpeaker}
				>
					<option value={null}>전체 화자</option>
					{#each speakers as speaker}
						<option value={speaker}>{speaker}</option>
					{/each}
				</select>
			{/if}
		</div>
	</div>

	<!-- Speaker Legend -->
	{#if speakers.length > 0}
		<div class="speaker-legend">
			{#each speakers as speaker}
				<button
					type="button"
					class="legend-item"
					class:active={filterSpeaker === speaker}
					onclick={() => filterSpeaker = filterSpeaker === speaker ? null : speaker}
				>
					<span
						class="legend-dot"
						style="background-color: {getSpeakerColor(speaker)}"
					></span>
					<span class="legend-name">{speaker}</span>
				</button>
			{/each}
		</div>
	{/if}

	<!-- Segments List -->
	<div class="segments-container">
		{#if filteredSegments.length > 0}
			<ul class="segments-list" role="list">
				{#each filteredSegments as segment, index (segment.id || index)}
					{@const globalIndex = $resultsStore.transcriptSegments.findIndex(s => s === segment)}
					{@const suggestion = getSuggestion(globalIndex)}
					<li class="segment {suggestion && showSuggestions ? 'has-suggestion' : ''}">
						<button
							type="button"
							class="segment-btn"
							onclick={() => handleSegmentClick(segment)}
						>
							<span class="segment-time">
								{formatTime(segment.start)}
							</span>

							{#if segment.speaker_label || segment.speaker_name}
								<span
									class="segment-speaker"
									style="color: {getSpeakerColor(segment.speaker_label || segment.speaker_name || null)}"
								>
									{segment.speaker_name || segment.speaker_label}
								</span>
							{/if}

							<span class="segment-text">
								{@html highlightSearchText(segment.text)}
							</span>

							{#if segment.confidence !== undefined && segment.confidence < 0.7}
								<span class="confidence-warning" title="Low confidence: {Math.round(segment.confidence * 100)}%">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
									</svg>
								</span>
							{/if}
						</button>

						<!-- Suggestion Badge -->
						{#if suggestion && showSuggestions}
							<div class="suggestion-badge">
								<div class="suggestion-info">
									<span class="suggestion-icon">💡</span>
									<span class="suggestion-text">
										이 대화는 <strong>[{suggestion.suggested_agenda_title}]</strong>에 해당하는 것 같습니다
										<span class="suggestion-confidence">({Math.round(suggestion.confidence * 100)}%)</span>
									</span>
								</div>
								<div class="suggestion-actions">
									<button
										type="button"
										class="suggestion-accept"
										onclick={() => acceptSuggestion(suggestion)}
									>
										이동
									</button>
									<button
										type="button"
										class="suggestion-reject"
										onclick={() => rejectSuggestion(suggestion)}
									>
										유지
									</button>
								</div>
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{:else if $resultsStore.transcriptSegments.length === 0}
			<div class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
				</svg>
				<p class="text-gray-600 font-medium">대화 내용이 없습니다</p>
				<p class="text-sm text-gray-400">녹음이 없거나 인식된 음성이 없습니다</p>
			</div>
		{:else}
			<div class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p>검색 결과가 없습니다</p>
			</div>
		{/if}
	</div>

	<!-- Stats footer -->
	{#if $resultsStore.transcriptSegments.length > 0}
		<div class="viewer-footer">
			<span class="stat">
				{filteredSegments.length} / {$resultsStore.transcriptSegments.length} 세그먼트
			</span>
			{#if speakers.length > 0}
				<span class="stat">{speakers.length}명 화자</span>
			{/if}
		</div>
	{/if}
</div>

<style>
	.transcript-viewer {
		display: flex;
		flex-direction: column;
		background: white;
		border-radius: 0.5rem;
		border: 1px solid #e5e7eb;
		/* overflow: hidden 제거 - 드롭다운이 밖으로 나올 수 있도록 */
		position: relative;
	}

	/* Agenda Tabs */
	.agenda-tabs {
		display: flex;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: #f0f9ff;
		border-bottom: 1px solid #e5e7eb;
		overflow-x: auto;
		overflow-y: visible;
		-webkit-overflow-scrolling: touch;
		position: relative;
		z-index: 20;
	}

	.agenda-tabs::-webkit-scrollbar {
		display: none;
	}

	.agenda-tab {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		border: 1px solid #e5e7eb;
		border-radius: 9999px;
		background: white;
		font-size: 0.8125rem;
		white-space: nowrap;
		cursor: pointer;
		transition: all 0.15s;
	}

	.agenda-tab:hover:not(.disabled) {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.agenda-tab.active {
		border-color: #3b82f6;
		background: #3b82f6;
		color: white;
	}

	.agenda-tab.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.agenda-num {
		font-weight: 600;
	}

	.agenda-title {
		max-width: 100px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.agenda-duration {
		font-size: 0.75rem;
		opacity: 0.7;
	}

	.agenda-tab-wrapper {
		position: relative;
		z-index: 10;
	}

	.child-dropdown {
		position: fixed;
		min-width: 280px;
		max-width: 400px;
		max-height: 300px;
		overflow-y: auto;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 1000;
	}

	.child-item {
		display: block;
		width: 100%;
		padding: 0.75rem 1rem;
		text-align: left;
		font-size: 0.875rem;
		color: #374151;
		background: white;
		border: none;
		cursor: pointer;
		transition: background 0.15s;
		line-height: 1.4;
	}

	.child-item:hover:not(.disabled) {
		background: #f3f4f6;
	}

	.child-item.active {
		background: #eff6ff;
		color: #2563eb;
		font-weight: 500;
	}

	.child-item.disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.child-item + .child-item {
		border-top: 1px solid #f3f4f6;
	}

	.grandchild-item {
		padding-left: 1.5rem;
		font-size: 0.75rem;
		background: #f9fafb;
	}

	.viewer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #e5e7eb;
		background: #f9fafb;
	}

	.title {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.filters {
		display: flex;
		gap: 0.5rem;
	}

	.search-box {
		position: relative;
		display: flex;
		align-items: center;
	}

	.search-icon {
		position: absolute;
		left: 0.5rem;
		width: 16px;
		height: 16px;
		color: #9ca3af;
		pointer-events: none;
	}

	.search-input {
		padding: 0.375rem 0.5rem 0.375rem 2rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		width: 160px;
	}

	.search-input:focus {
		outline: none;
		border-color: #3b82f6;
	}

	.clear-btn {
		position: absolute;
		right: 0.375rem;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		border: none;
		border-radius: 50%;
		background: #e5e7eb;
		color: #6b7280;
		cursor: pointer;
	}

	.clear-btn:hover {
		background: #d1d5db;
	}

	.speaker-filter {
		padding: 0.375rem 0.5rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		background: white;
	}

	.speaker-legend {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.25rem 0.5rem;
		border: 1px solid #e5e7eb;
		border-radius: 9999px;
		background: white;
		font-size: 0.75rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.legend-item:hover {
		background: #f3f4f6;
	}

	.legend-item.active {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.legend-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
	}

	.legend-name {
		color: #374151;
	}

	.segments-container {
		flex: 1;
		overflow-y: auto;
		max-height: 400px;
	}

	.segments-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.segment {
		border-bottom: 1px solid #f3f4f6;
	}

	.segment:last-child {
		border-bottom: none;
	}

	.segment-btn {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
		width: 100%;
		padding: 0.75rem 1rem;
		border: none;
		background: transparent;
		text-align: left;
		cursor: pointer;
		transition: background 0.15s;
	}

	.segment-btn:hover {
		background: #f9fafb;
	}

	.segment-time {
		flex-shrink: 0;
		font-family: ui-monospace, monospace;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.segment-speaker {
		flex-shrink: 0;
		font-size: 0.75rem;
		font-weight: 600;
		min-width: 80px;
	}

	.segment-text {
		flex: 1;
		font-size: 0.875rem;
		color: #111827;
		line-height: 1.5;
	}

	.confidence-warning {
		flex-shrink: 0;
		color: #f59e0b;
	}

	.empty-state {
		padding: 2rem;
		text-align: center;
		color: #9ca3af;
	}

	.empty-state p {
		margin-top: 0.5rem;
		font-size: 0.875rem;
	}

	.viewer-footer {
		display: flex;
		gap: 1rem;
		padding: 0.5rem 1rem;
		background: #f9fafb;
		border-top: 1px solid #e5e7eb;
	}

	.stat {
		font-size: 0.75rem;
		color: #6b7280;
	}

	/* Analysis Controls */
	.analysis-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 1rem;
		background: #fefce8;
		border-bottom: 1px solid #fef08a;
	}

	.analyze-btn {
		display: flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.375rem 0.75rem;
		border: 1px solid #eab308;
		border-radius: 0.375rem;
		background: white;
		color: #854d0e;
		font-size: 0.8125rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.analyze-btn:hover:not(:disabled) {
		background: #fef9c3;
		border-color: #ca8a04;
	}

	.analyze-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.suggestion-count {
		font-size: 0.8125rem;
		font-weight: 600;
		color: #ca8a04;
		background: #fef9c3;
		padding: 0.25rem 0.5rem;
		border-radius: 9999px;
	}

	.toggle-suggestions {
		font-size: 0.75rem;
		color: #854d0e;
		background: none;
		border: none;
		cursor: pointer;
		text-decoration: underline;
	}

	.toggle-suggestions:hover {
		color: #713f12;
	}

	.analysis-error {
		font-size: 0.75rem;
		color: #dc2626;
	}

	.analysis-success {
		font-size: 0.8125rem;
		color: #16a34a;
		font-weight: 500;
	}

	/* Segment with suggestion */
	.segment.has-suggestion {
		background: #fffbeb;
		border-left: 3px solid #f59e0b;
	}

	.suggestion-badge {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		background: #fef3c7;
		border-top: 1px dashed #fcd34d;
	}

	.suggestion-info {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
	}

	.suggestion-icon {
		font-size: 1rem;
		flex-shrink: 0;
	}

	.suggestion-text {
		font-size: 0.8125rem;
		color: #78350f;
		line-height: 1.4;
	}

	.suggestion-text strong {
		color: #b45309;
	}

	.suggestion-confidence {
		font-size: 0.75rem;
		color: #92400e;
		opacity: 0.8;
	}

	.suggestion-actions {
		display: flex;
		gap: 0.5rem;
		padding-left: 1.5rem;
	}

	.suggestion-accept {
		padding: 0.25rem 0.75rem;
		border: none;
		border-radius: 0.25rem;
		background: #f59e0b;
		color: white;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: background 0.15s;
	}

	.suggestion-accept:hover {
		background: #d97706;
	}

	.suggestion-reject {
		padding: 0.25rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.25rem;
		background: white;
		color: #6b7280;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.suggestion-reject:hover {
		background: #f3f4f6;
		border-color: #9ca3af;
	}

	@media (pointer: coarse) {
		.segment-btn {
			padding: 1rem;
		}

		.search-input {
			padding: 0.5rem 0.5rem 0.5rem 2rem;
		}

		.agenda-tab {
			padding: 0.625rem 1rem;
		}

		.suggestion-badge {
			padding: 1rem;
		}

		.suggestion-actions {
			padding-left: 0;
		}

		.suggestion-accept,
		.suggestion-reject {
			padding: 0.5rem 1rem;
			font-size: 0.8125rem;
		}
	}
</style>
