<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { meetings, isLoading, type Meeting } from '$lib/stores/meeting';
	import { api } from '$lib/api';
	import { cacheContacts } from '$lib/stores/offlineCache';
	import { Search, Plus, Trash2, Calendar, Filter } from 'lucide-svelte';
	import MeetingCard from '$lib/components/ui/MeetingCard.svelte';
	import ConfirmDialog from '$lib/components/ui/ConfirmDialog.svelte';

	let statusFilter: string = '';
	let searchQuery: string = '';
	let currentPage = 0;
	let totalCount = 0;
	const pageSize = 20;

	// Delete confirmation
	let deleteDialogOpen = $state(false);
	let meetingToDelete = $state<Meeting | null>(null);

	// Selected meeting for detail panel (future use)
	let selectedMeeting = $state<Meeting | null>(null);

	// Using derived for reactive filtering
	let filteredMeetings = $derived($meetings);

	onMount(() => {
		loadMeetings();
		cacheContacts();
	});

	async function loadMeetings() {
		isLoading.set(true);
		try {
			const params: Record<string, string | number | undefined> = {
				limit: pageSize,
				offset: currentPage * pageSize
			};

			if (statusFilter) {
				params.status = statusFilter;
			}

			if (searchQuery) {
				params.q = searchQuery;
			}

			const response = await api.get<{ data: Meeting[]; meta: { total: number } }>(
				'/meetings',
				params
			);
			meetings.set(response.data);
			totalCount = response.meta?.total || 0;
		} catch {
			// Failed to load meetings
		} finally {
			isLoading.set(false);
		}
	}

	function handleSearch() {
		currentPage = 0;
		loadMeetings();
	}

	function handleFilterChange() {
		currentPage = 0;
		loadMeetings();
	}

	function handleMeetingClick(meeting: Meeting) {
		goto(`/meetings/${meeting.id}`);
	}

	function openDeleteDialog(meeting: Meeting, e: Event) {
		e.stopPropagation();
		meetingToDelete = meeting;
		deleteDialogOpen = true;
	}

	async function confirmDelete() {
		if (!meetingToDelete) return;

		try {
			await api.delete(`/meetings/${meetingToDelete.id}`);
			deleteDialogOpen = false;
			meetingToDelete = null;
			loadMeetings();
		} catch {
			// Failed to delete meeting
		}
	}

	function cancelDelete() {
		deleteDialogOpen = false;
		meetingToDelete = null;
	}
</script>

<svelte:head>
	<title>회의 - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-text">회의</h1>
		<div class="flex gap-3">
			<a href="/meetings/deleted" class="btn btn-ghost text-sm">
				<Trash2 class="w-4 h-4" />
				삭제된 회의
			</a>
			<a href="/meetings/new" class="btn btn-primary">
				<Plus class="w-4 h-4" />
				새 회의
			</a>
		</div>
	</div>

	<!-- Search & Filters -->
	<div class="flex flex-col sm:flex-row gap-3">
		<!-- Search -->
		<div class="flex-1 relative">
			<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
			<input
				type="text"
				bind:value={searchQuery}
				onkeydown={(e) => e.key === 'Enter' && handleSearch()}
				placeholder="회의 검색..."
				class="input pl-10"
			/>
		</div>

		<!-- Status Filter -->
		<div class="sm:w-44 relative">
			<Filter class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
			<select
				bind:value={statusFilter}
				onchange={handleFilterChange}
				class="input pl-9 appearance-none cursor-pointer"
			>
				<option value="">전체 상태</option>
				<option value="draft">작성 중</option>
				<option value="in_progress">진행 중</option>
				<option value="completed">완료</option>
			</select>
		</div>

		<button type="button" onclick={handleSearch} class="btn btn-secondary">
			검색
		</button>
	</div>

	<!-- Meetings List -->
	{#if $isLoading}
		<!-- Loading skeletons -->
		<div class="space-y-3">
			{#each Array(5) as _, i}
				<div class="card p-4">
					<div class="flex items-start justify-between gap-3">
						<div class="flex-1 space-y-2">
							<div class="skeleton h-5 w-2/3"></div>
							<div class="skeleton h-3 w-1/3"></div>
							<div class="flex gap-3 mt-2">
								<div class="skeleton h-3 w-20"></div>
								<div class="skeleton h-3 w-16"></div>
							</div>
						</div>
						<div class="skeleton h-6 w-16 rounded-full"></div>
					</div>
				</div>
			{/each}
		</div>
	{:else if filteredMeetings.length === 0}
		<!-- Empty state -->
		<div class="card text-center py-16">
			<Calendar class="mx-auto w-12 h-12 text-gray-400 dark:text-text-subtle" />
			<h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-text">회의를 찾을 수 없습니다</h3>
			<p class="mt-2 text-sm text-gray-500 dark:text-text-muted">
				새 회의를 생성하여 시작하세요.
			</p>
			<div class="mt-6">
				<a href="/meetings/new" class="btn btn-primary">
					<Plus class="w-4 h-4" />
					새 회의
				</a>
			</div>
		</div>
	{:else}
		<!-- Meeting cards -->
		<div class="space-y-3">
			{#each filteredMeetings as meeting (meeting.id)}
				<div class="relative group">
					<MeetingCard
						{meeting}
						isSelected={selectedMeeting?.id === meeting.id}
						onclick={() => handleMeetingClick(meeting)}
					/>
					<!-- Delete button overlay -->
					<button
						type="button"
						onclick={(e) => openDeleteDialog(meeting, e)}
						class="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all touch-target"
						title="삭제"
					>
						<Trash2 class="w-4 h-4" />
					</button>
				</div>
			{/each}
		</div>

		<!-- Pagination -->
		{#if totalCount > pageSize}
			<div class="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4">
				<p class="text-sm text-gray-600 dark:text-text-muted">
					전체 <span class="font-medium text-gray-900 dark:text-text">{totalCount}</span>개 중
					<span class="font-medium text-gray-900 dark:text-text">{currentPage * pageSize + 1}</span> -
					<span class="font-medium text-gray-900 dark:text-text">{Math.min((currentPage + 1) * pageSize, totalCount)}</span>
				</p>
				<div class="flex gap-2">
					<button
						type="button"
						disabled={currentPage === 0}
						onclick={() => { currentPage--; loadMeetings(); }}
						class="btn btn-secondary disabled:opacity-50"
					>
						이전
					</button>
					<button
						type="button"
						disabled={(currentPage + 1) * pageSize >= totalCount}
						onclick={() => { currentPage++; loadMeetings(); }}
						class="btn btn-secondary disabled:opacity-50"
					>
						다음
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>

<!-- Delete Confirmation Dialog -->
<ConfirmDialog
	open={deleteDialogOpen}
	title="회의 삭제"
	message="'{meetingToDelete?.title}' 회의를 삭제하시겠습니까? 삭제된 회의는 '삭제된 회의' 목록에서 복구할 수 있습니다."
	confirmText="삭제"
	cancelText="취소"
	variant="danger"
	onConfirm={confirmDelete}
	onCancel={cancelDelete}
/>
