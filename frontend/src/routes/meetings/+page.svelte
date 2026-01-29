<script lang="ts">
	import { onMount } from 'svelte';
	import { meetings, isLoading, type Meeting } from '$lib/stores/meeting';
	import { api } from '$lib/api';
	import { cacheContacts } from '$lib/stores/offlineCache';

	let statusFilter: string = '';
	let searchQuery: string = '';
	let currentPage = 0;
	let totalCount = 0;
	const pageSize = 20;

	$: filteredMeetings = $meetings;

	onMount(() => {
		loadMeetings();
		// 백그라운드에서 연락처 캐싱
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
		} catch (error) {
			console.error('Failed to load meetings:', error);
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

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	function getStatusBadgeClass(status: Meeting['status']): string {
		switch (status) {
			case 'draft':
				return 'bg-gray-100 text-gray-800';
			case 'in_progress':
				return 'bg-yellow-100 text-yellow-800';
			case 'completed':
				return 'bg-green-100 text-green-800';
			default:
				return 'bg-gray-100 text-gray-800';
		}
	}

	function getStatusLabel(status: Meeting['status']): string {
		switch (status) {
			case 'draft':
				return '작성 중';
			case 'in_progress':
				return '진행 중';
			case 'completed':
				return '완료';
			default:
				return status;
		}
	}

	async function deleteMeeting(id: number) {
		if (!confirm('이 회의를 삭제하시겠습니까?')) return;

		try {
			await api.delete(`/meetings/${id}`);
			loadMeetings();
		} catch (error) {
			console.error('Failed to delete meeting:', error);
		}
	}
</script>

<svelte:head>
	<title>회의 - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex justify-between items-center">
		<h1 class="text-2xl font-bold text-gray-900">회의</h1>
		<div class="flex gap-3">
			<a href="/meetings/deleted" class="btn btn-secondary">
				삭제된 회의
			</a>
			<a href="/meetings/new" class="btn btn-primary">
				+ 새 회의
			</a>
		</div>
	</div>

	<!-- Filters -->
	<div class="card">
		<div class="flex flex-col sm:flex-row gap-4">
			<div class="flex-1">
				<label for="search" class="sr-only">회의 검색</label>
				<div class="relative">
					<div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
						<svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
							/>
						</svg>
					</div>
					<input
						id="search"
						type="text"
						bind:value={searchQuery}
						onkeydown={(e) => e.key === 'Enter' && handleSearch()}
						placeholder="회의 검색..."
						class="input pl-10"
					/>
				</div>
			</div>
			<div class="sm:w-48">
				<label for="status" class="sr-only">상태별 필터</label>
				<select
					id="status"
					bind:value={statusFilter}
					onchange={handleFilterChange}
					class="input"
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
	</div>

	<!-- Meetings List -->
	{#if $isLoading}
		<div class="flex justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
		</div>
	{:else if filteredMeetings.length === 0}
		<div class="card text-center py-12">
			<svg
				class="mx-auto h-12 w-12 text-gray-400"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
				/>
			</svg>
			<h3 class="mt-2 text-sm font-medium text-gray-900">회의를 찾을 수 없습니다</h3>
			<p class="mt-1 text-sm text-gray-500">
				새 회의를 생성하여 시작하세요.
			</p>
			<div class="mt-6">
				<a href="/meetings/new" class="btn btn-primary">
					+ 새 회의
				</a>
			</div>
		</div>
	{:else}
		<div class="card overflow-hidden p-0">
			<table class="min-w-full divide-y divide-gray-200">
				<thead class="bg-gray-50">
					<tr>
						<th
							scope="col"
							class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>
							제목
						</th>
						<th
							scope="col"
							class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>
							일자
						</th>
						<th
							scope="col"
							class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
						>
							상태
						</th>
						<th scope="col" class="relative px-6 py-3">
							<span class="sr-only">작업</span>
						</th>
					</tr>
				</thead>
				<tbody class="bg-white divide-y divide-gray-200">
					{#each filteredMeetings as meeting (meeting.id)}
						<tr class="hover:bg-gray-50">
							<td class="px-6 py-4 whitespace-nowrap">
								<a href="/meetings/{meeting.id}" class="text-primary-600 hover:text-primary-900 font-medium">
									{meeting.title}
								</a>
								{#if meeting.type_name}
									<p class="text-xs text-gray-500">{meeting.type_name}</p>
								{/if}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{formatDate(meeting.scheduled_at)}
							</td>
							<td class="px-6 py-4 whitespace-nowrap">
								<span
									class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadgeClass(
										meeting.status
									)}"
								>
									{getStatusLabel(meeting.status)}
								</span>
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
								<a
									href="/meetings/{meeting.id}"
									class="text-primary-600 hover:text-primary-900 mr-4"
								>
									보기
								</a>
								<button
									type="button"
									onclick={() => deleteMeeting(meeting.id)}
									class="text-red-600 hover:text-red-900"
								>
									삭제
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<!-- Pagination -->
		{#if totalCount > pageSize}
			<div class="flex items-center justify-between">
				<p class="text-sm text-gray-700">
					전체 <span class="font-medium">{totalCount}</span>개 중
					<span class="font-medium">{currentPage * pageSize + 1}</span>부터
					<span class="font-medium">{Math.min((currentPage + 1) * pageSize, totalCount)}</span>까지 표시
				</p>
				<div class="flex space-x-2">
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
