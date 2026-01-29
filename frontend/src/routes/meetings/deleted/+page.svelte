<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getDeletedMeetings, restoreMeeting } from '$lib/api/meetings';
	import type { Meeting } from '$lib/stores/meeting';

	let meetings: Meeting[] = [];
	let isLoading = false;
	let currentPage = 0;
	let totalCount = 0;
	const pageSize = 20;

	onMount(() => {
		loadDeletedMeetings();
	});

	async function loadDeletedMeetings() {
		isLoading = true;
		try {
			const response = await getDeletedMeetings({
				limit: pageSize,
				offset: currentPage * pageSize
			});
			meetings = response.data;
			totalCount = response.meta?.total || 0;
		} catch (error) {
			console.error('Failed to load deleted meetings:', error);
		} finally {
			isLoading = false;
		}
	}

	async function handleRestore(id: number) {
		if (!confirm('이 회의를 복구하시겠습니까?')) return;

		try {
			await restoreMeeting(id);
			// Remove from list
			meetings = meetings.filter((m) => m.id !== id);
			totalCount--;
		} catch (error) {
			console.error('Failed to restore meeting:', error);
			alert('회의 복구에 실패했습니다.');
		}
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
</script>

<svelte:head>
	<title>삭제된 회의 - MAX Meeting</title>
</svelte:head>

<div class="space-y-6">
	<div class="flex justify-between items-center">
		<h1 class="text-2xl font-bold text-gray-900">삭제된 회의</h1>
		<a href="/meetings" class="btn btn-secondary"> ← 회의 목록으로 </a>
	</div>

	<!-- Deleted Meetings List -->
	{#if isLoading}
		<div class="flex justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
		</div>
	{:else if meetings.length === 0}
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
					d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
				/>
			</svg>
			<h3 class="mt-2 text-sm font-medium text-gray-900">삭제된 회의가 없습니다</h3>
			<p class="mt-1 text-sm text-gray-500">삭제된 회의가 여기에 표시됩니다.</p>
			<div class="mt-6">
				<a href="/meetings" class="btn btn-primary"> 회의 목록으로 </a>
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
					{#each meetings as meeting (meeting.id)}
						<tr class="hover:bg-gray-50">
							<td class="px-6 py-4">
								<div class="text-sm font-medium text-gray-900">
									{meeting.title}
								</div>
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
								<button
									type="button"
									onclick={() => handleRestore(meeting.id)}
									class="text-primary-600 hover:text-primary-900 font-medium"
								>
									복구
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
					<span class="font-medium">{Math.min((currentPage + 1) * pageSize, totalCount)}</span
					>까지 표시
				</p>
				<div class="flex space-x-2">
					<button
						type="button"
						disabled={currentPage === 0}
						onclick={() => {
							currentPage--;
							loadDeletedMeetings();
						}}
						class="btn btn-secondary disabled:opacity-50"
					>
						이전
					</button>
					<button
						type="button"
						disabled={(currentPage + 1) * pageSize >= totalCount}
						onclick={() => {
							currentPage++;
							loadDeletedMeetings();
						}}
						class="btn btn-secondary disabled:opacity-50"
					>
						다음
					</button>
				</div>
			</div>
		{/if}
	{/if}
</div>
