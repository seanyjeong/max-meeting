<script lang="ts">
	import { resultsStore, type TranscriptSegment } from '$lib/stores/results';
	import DOMPurify from 'dompurify';

	interface Props {
		onSegmentClick?: (segment: TranscriptSegment) => void;
		highlightText?: string;
	}

	let { onSegmentClick, highlightText = '' }: Props = $props();

	let searchQuery = $state('');
	let filterSpeaker = $state<string | null>(null);

	// Get unique speakers
	let speakers = $derived(
		[...new Set($resultsStore.transcriptSegments
			.map(s => s.speaker_label || s.speaker_name)
			.filter(Boolean)
		)] as string[]
	);

	// Filter segments
	let filteredSegments = $derived(
		$resultsStore.transcriptSegments.filter(segment => {
			const matchesSearch = !searchQuery ||
				segment.text.toLowerCase().includes(searchQuery.toLowerCase());
			const matchesSpeaker = !filterSpeaker ||
				segment.speaker_label === filterSpeaker ||
				segment.speaker_name === filterSpeaker;
			return matchesSearch && matchesSpeaker;
		})
	);

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}

	function highlightSearchText(text: string): string {
		const query = searchQuery || highlightText;
		if (!query || !text) return DOMPurify.sanitize(text);

		// First escape HTML entities
		const escapedText = text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#39;');

		// Then apply highlighting
		const escapedQuery = escapeRegex(query);
		const regex = new RegExp(`(${escapedQuery})`, 'gi');
		const highlighted = escapedText.replace(regex, '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>');

		// Sanitize the result
		return DOMPurify.sanitize(highlighted);
	}

	function escapeRegex(str: string): string {
		return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	function getSpeakerColor(speaker: string | null): string {
		if (!speaker) return '#6b7280';
		const colors = [
			'#3b82f6', // blue
			'#22c55e', // green
			'#f59e0b', // amber
			'#ef4444', // red
			'#8b5cf6', // violet
			'#ec4899', // pink
			'#06b6d4', // cyan
			'#f97316'  // orange
		];
		const index = speakers.indexOf(speaker);
		return colors[index % colors.length];
	}

	function handleSegmentClick(segment: TranscriptSegment) {
		onSegmentClick?.(segment);
	}
</script>

<div class="transcript-viewer">
	<!-- Header / Filters -->
	<div class="viewer-header">
		<h3 class="title">Transcript</h3>

		<div class="filters">
			<!-- Search -->
			<div class="search-box">
				<svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					type="text"
					class="search-input"
					placeholder="Search transcript..."
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
					<option value={null}>All speakers</option>
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
					<li class="segment">
						<button
							type="button"
							class="segment-btn"
							onclick={() => handleSegmentClick(segment)}
						>
							<!-- Timestamp -->
							<span class="segment-time">
								{formatTime(segment.start)}
							</span>

							<!-- Speaker -->
							{#if segment.speaker_label || segment.speaker_name}
								<span
									class="segment-speaker"
									style="color: {getSpeakerColor(segment.speaker_label || segment.speaker_name || null)}"
								>
									{segment.speaker_name || segment.speaker_label}
								</span>
							{/if}

							<!-- Text -->
							<span class="segment-text">
								{@html highlightSearchText(segment.text)}
							</span>

							<!-- Confidence indicator (if available) -->
							{#if segment.confidence !== undefined && segment.confidence < 0.7}
								<span class="confidence-warning" title="Low confidence: {Math.round(segment.confidence * 100)}%">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
									</svg>
								</span>
							{/if}
						</button>
					</li>
				{/each}
			</ul>
		{:else if $resultsStore.transcriptSegments.length === 0}
			<div class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
				</svg>
				<p>No transcript available</p>
				<p class="text-sm">Transcript will appear after STT processing</p>
			</div>
		{:else}
			<div class="empty-state">
				<svg class="w-12 h-12 mx-auto text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p>No matching segments found</p>
			</div>
		{/if}
	</div>

	<!-- Stats footer -->
	{#if $resultsStore.transcriptSegments.length > 0}
		<div class="viewer-footer">
			<span class="stat">
				{filteredSegments.length} / {$resultsStore.transcriptSegments.length} segments
			</span>
			{#if speakers.length > 0}
				<span class="stat">{speakers.length} speakers</span>
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
		overflow: hidden;
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
		width: 200px;
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

	/* Touch-friendly */
	@media (pointer: coarse) {
		.segment-btn {
			padding: 1rem;
		}

		.search-input {
			padding: 0.5rem 0.5rem 0.5rem 2rem;
		}
	}
</style>
