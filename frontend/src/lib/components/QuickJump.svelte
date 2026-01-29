<!--
	Quick Jump Component

	A command palette-style search interface triggered by Cmd+K (Mac) or Ctrl+K (Windows/Linux).
	Searches across meetings and contacts with keyboard navigation and recent search history.

	Features:
	- ⌘K/Ctrl+K to open
	- Real-time search with 300ms debounce
	- Arrow key navigation
	- Enter to select, ESC to close
	- Recent searches (last 3)
	- Dark brutalist aesthetic
-->
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth';

	interface SearchResult {
		meetings?: Array<{
			id: number;
			title: string;
			scheduled_at: string;
			status: string;
			highlight?: string;
			match_score: number;
		}>;
		contacts?: Array<{
			id: number;
			name: string;
			organization?: string;
			role?: string;
			highlight?: string;
			match_score: number;
		}>;
		transcripts?: Array<{
			id: number;
			meeting_id: number;
			meeting_title: string;
			chunk_index: number;
			highlight?: string;
			match_score: number;
			created_at: string;
		}>;
	}

	interface SearchResponse {
		data: SearchResult;
		meta: {
			query: string;
			total: number;
			limit: number;
			offset: number;
		};
	}

	let open = $state(false);
	let query = $state('');
	let results = $state<SearchResult>({ meetings: [], contacts: [], transcripts: [] });
	let selectedIndex = $state(0);
	let loading = $state(false);
	let searchInput = $state<HTMLInputElement | undefined>(undefined);
	let recentSearches = $state<string[]>([]);

	const RECENT_SEARCHES_KEY = 'max-meeting-recent-searches';
	const MAX_RECENT = 3;

	$effect(() => {
		if (open && searchInput) {
			searchInput.focus();
		}
	});

	onMount(() => {
		// Load recent searches
		const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
		if (stored) {
			recentSearches = JSON.parse(stored);
		}

		// Add keyboard listener
		window.addEventListener('keydown', handleGlobalKeydown);

		return () => {
			window.removeEventListener('keydown', handleGlobalKeydown);
		};
	});

	function handleGlobalKeydown(e: KeyboardEvent) {
		// Cmd+K (Mac) or Ctrl+K (Windows/Linux)
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			toggleOpen();
		}
	}

	function toggleOpen() {
		open = !open;
		if (!open) {
			resetSearch();
		}
	}

	function resetSearch() {
		query = '';
		results = { meetings: [], contacts: [] };
		selectedIndex = 0;
		loading = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		const allResults = [...(results.meetings || []), ...(results.contacts || [])];
		const totalResults = allResults.length;

		switch (e.key) {
			case 'Escape':
				e.preventDefault();
				toggleOpen();
				break;
			case 'ArrowDown':
				e.preventDefault();
				selectedIndex = (selectedIndex + 1) % totalResults;
				break;
			case 'ArrowUp':
				e.preventDefault();
				selectedIndex = (selectedIndex - 1 + totalResults) % totalResults;
				break;
			case 'Enter':
				e.preventDefault();
				if (totalResults > 0) {
					selectResult(allResults[selectedIndex]);
				}
				break;
		}
	}

	async function handleSearch() {
		if (!query.trim()) {
			results = { meetings: [], contacts: [], transcripts: [] };
			return;
		}

		loading = true;
		try {
			const token = $auth.accessToken;
			const response = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}&limit=10`, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});

			if (response.ok) {
				const data: SearchResponse = await response.json();
				results = data.data;
				selectedIndex = 0;

				// Save to recent searches
				if (!recentSearches.includes(query)) {
					recentSearches = [query, ...recentSearches.slice(0, MAX_RECENT - 1)];
					localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(recentSearches));
				}
			}
		} catch (err) {
			console.error('Search failed:', err);
		} finally {
			loading = false;
		}
	}

	function selectResult(result: any) {
		if ('title' in result) {
			// It's a meeting
			goto(`/meetings/${result.id}`);
		} else if ('name' in result) {
			// It's a contact
			goto(`/contacts/${result.id}`);
		}
		toggleOpen();
	}

	function selectRecentSearch(search: string) {
		query = search;
		handleSearch();
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			toggleOpen();
		}
	}

	// Debounced search
	let searchTimeout: number;
	$effect(() => {
		if (query) {
			clearTimeout(searchTimeout);
			searchTimeout = setTimeout(() => {
				handleSearch();
			}, 300);
		}
	});

	const allResults = $derived([...(results.meetings || []), ...(results.contacts || [])]);
</script>

<svelte:window onkeydown={handleGlobalKeydown} />

{#if open}
	<div
		class="fixed inset-0 z-[100] overflow-hidden"
		role="dialog"
		aria-modal="true"
		aria-labelledby="quickjump-title"
	>
		<!-- Backdrop with gradient -->
		<div
			class="fixed inset-0 bg-black/80 backdrop-blur-sm transition-opacity"
			onclick={handleBackdropClick}
			onkeydown={(e) => e.key === 'Enter' && handleBackdropClick(e as any)}
			role="button"
			tabindex="-1"
			aria-label="Close search dialog"
		></div>

		<!-- Command palette -->
		<div class="fixed inset-x-0 top-[10vh] mx-auto max-w-2xl px-4">
			<div
				class="quick-jump-panel"
				role="search"
			>
				<!-- Search header -->
				<div class="search-header">
					<svg
						class="search-icon"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2.5"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
					<input
						bind:this={searchInput}
						bind:value={query}
						type="text"
						placeholder="Search meetings, contacts..."
						class="search-input"
						autocomplete="off"
						spellcheck="false"
						aria-label="Quick search"
						onkeydown={handleKeydown}
					/>
					<kbd class="kbd">ESC</kbd>
				</div>

				<!-- Results area -->
				<div class="results-container">
					{#if loading}
						<div class="loading-state">
							<div class="spinner"></div>
							<span>Searching...</span>
						</div>
					{:else if query && allResults.length === 0}
						<div class="empty-state">
							<svg class="empty-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<p>No results found</p>
						</div>
					{:else if !query && recentSearches.length > 0}
						<div class="section">
							<div class="section-header">Recent Searches</div>
							{#each recentSearches as search}
								<button
									class="result-item"
									onclick={() => selectRecentSearch(search)}
								>
									<svg class="result-icon clock" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
									<span class="result-text">{search}</span>
								</button>
							{/each}
						</div>
					{:else if allResults.length > 0}
						{#if results.meetings && results.meetings.length > 0}
							<div class="section">
								<div class="section-header">Meetings</div>
								{#each results.meetings as meeting, i}
									{@const index = i}
									<button
										class="result-item"
										class:selected={selectedIndex === index}
										onclick={() => selectResult(meeting)}
									>
										<svg class="result-icon meeting" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
											/>
										</svg>
										<div class="result-content">
											<div class="result-title">{meeting.title}</div>
											<div class="result-meta">
												{new Date(meeting.scheduled_at).toLocaleDateString()} •
												<span class="status-badge status-{meeting.status}">{meeting.status}</span>
											</div>
										</div>
										{#if selectedIndex === index}
											<kbd class="enter-badge">↵</kbd>
										{/if}
									</button>
								{/each}
							</div>
						{/if}

						{#if results.contacts && results.contacts.length > 0}
							<div class="section">
								<div class="section-header">Contacts</div>
								{#each results.contacts as contact, i}
									{@const index = (results.meetings?.length || 0) + i}
									<button
										class="result-item"
										class:selected={selectedIndex === index}
										onclick={() => selectResult(contact)}
									>
										<svg class="result-icon contact" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
											/>
										</svg>
										<div class="result-content">
											<div class="result-title">{contact.name}</div>
											<div class="result-meta">
												{#if contact.role}
													{contact.role}
												{/if}
												{#if contact.organization}
													{#if contact.role}• {/if}{contact.organization}
												{/if}
											</div>
										</div>
										{#if selectedIndex === index}
											<kbd class="enter-badge">↵</kbd>
										{/if}
									</button>
								{/each}
							</div>
						{/if}
					{:else}
						<div class="hint-state">
							<div class="hint-item">
								<kbd class="kbd">⌘K</kbd>
								<span>Quick search</span>
							</div>
							<div class="hint-item">
								<kbd class="kbd">↑↓</kbd>
								<span>Navigate</span>
							</div>
							<div class="hint-item">
								<kbd class="kbd">↵</kbd>
								<span>Select</span>
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.quick-jump-panel {
		background: linear-gradient(to bottom right, #0a0a0a, #1a1a1a);
		border: 2px solid #333;
		border-radius: 12px;
		box-shadow:
			0 25px 50px -12px rgba(0, 0, 0, 0.8),
			0 0 0 1px rgba(255, 255, 255, 0.1) inset;
		overflow: hidden;
		animation: slideDown 0.2s cubic-bezier(0.16, 1, 0.3, 1);
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.search-header {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 20px 24px;
		border-bottom: 2px solid #333;
		background: linear-gradient(to bottom, #1a1a1a, #0f0f0f);
	}

	.search-icon {
		width: 24px;
		height: 24px;
		color: #666;
		flex-shrink: 0;
	}

	.search-input {
		flex: 1;
		background: transparent;
		border: none;
		color: #fff;
		font-size: 18px;
		font-weight: 500;
		letter-spacing: -0.02em;
		outline: none;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
	}

	.search-input::placeholder {
		color: #555;
		font-weight: 400;
	}

	.kbd {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 32px;
		height: 24px;
		padding: 0 8px;
		background: #0a0a0a;
		border: 1.5px solid #333;
		border-radius: 4px;
		color: #888;
		font-size: 11px;
		font-weight: 700;
		font-family: monospace;
		text-transform: uppercase;
		box-shadow: 0 2px 0 0 #000;
		flex-shrink: 0;
	}

	.results-container {
		max-height: 50vh;
		overflow-y: auto;
		padding: 8px;
	}

	.results-container::-webkit-scrollbar {
		width: 6px;
	}

	.results-container::-webkit-scrollbar-track {
		background: #0a0a0a;
	}

	.results-container::-webkit-scrollbar-thumb {
		background: #333;
		border-radius: 3px;
	}

	.results-container::-webkit-scrollbar-thumb:hover {
		background: #444;
	}

	.section {
		margin-bottom: 12px;
	}

	.section-header {
		padding: 12px 16px 8px;
		color: #666;
		font-size: 11px;
		font-weight: 800;
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.result-item {
		display: flex;
		align-items: center;
		gap: 12px;
		width: 100%;
		padding: 12px 16px;
		background: transparent;
		border: none;
		border-radius: 6px;
		color: #fff;
		text-align: left;
		cursor: pointer;
		transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
		margin-bottom: 4px;
	}

	.result-item:hover,
	.result-item.selected {
		background: linear-gradient(to right, #2563eb, #1d4ed8);
		transform: translateX(4px);
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
	}

	.result-icon {
		width: 20px;
		height: 20px;
		flex-shrink: 0;
		stroke-width: 2.5;
	}

	.result-icon.meeting {
		color: #10b981;
	}

	.result-icon.contact {
		color: #f59e0b;
	}

	.result-icon.clock {
		color: #8b5cf6;
	}

	.result-content {
		flex: 1;
		min-width: 0;
	}

	.result-title {
		font-size: 15px;
		font-weight: 600;
		letter-spacing: -0.01em;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.result-meta {
		font-size: 12px;
		color: #888;
		margin-top: 2px;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.status-badge {
		display: inline-block;
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 10px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-scheduled {
		background: #1e40af;
		color: #60a5fa;
	}

	.status-completed {
		background: #065f46;
		color: #34d399;
	}

	.status-cancelled {
		background: #7c2d12;
		color: #fb923c;
	}

	.enter-badge {
		background: rgba(255, 255, 255, 0.1);
		border-color: rgba(255, 255, 255, 0.2);
		color: rgba(255, 255, 255, 0.6);
		min-width: 28px;
	}

	.loading-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 40px 20px;
		color: #666;
		font-size: 14px;
	}

	.spinner {
		width: 20px;
		height: 20px;
		border: 2px solid #333;
		border-top-color: #666;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 40px 20px;
		color: #666;
	}

	.empty-icon {
		width: 48px;
		height: 48px;
		color: #333;
		stroke-width: 1.5;
	}

	.empty-state p {
		font-size: 14px;
		font-weight: 500;
	}

	.hint-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 24px;
		padding: 32px 20px;
	}

	.hint-item {
		display: flex;
		align-items: center;
		gap: 8px;
		color: #666;
		font-size: 13px;
	}

	@media (prefers-reduced-motion: reduce) {
		.quick-jump-panel,
		.result-item {
			animation: none;
			transition: none;
		}
	}
</style>
