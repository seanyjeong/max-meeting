<script lang="ts">
	import { onMount } from 'svelte';
	import { meetings, isLoading, type Meeting } from '$lib/stores/meeting';
	import { api } from '$lib/api';
	import { formatDateTime } from '$lib/utils/format';
	import { logger } from '$lib/utils/logger';

	let recentMeetings: Meeting[] = [];
	let upcomingMeetings: Meeting[] = [];
	let inProgressMeeting: Meeting | null = null;

	onMount(async () => {
		isLoading.set(true);
		try {
			const response = await api.get<{ data: Meeting[]; meta: { total: number } }>('/meetings', {
				limit: 10,
				offset: 0
			});
			meetings.set(response.data);

			// Filter meetings
			const now = new Date();
			recentMeetings = response.data
				.filter((m) => m.status === 'completed')
				.slice(0, 5);

			upcomingMeetings = response.data
				.filter((m) => m.status === 'draft' && m.scheduled_at && new Date(m.scheduled_at) > now)
				.slice(0, 3);

			inProgressMeeting = response.data.find((m) => m.status === 'in_progress') || null;
		} catch (error) {
			logger.error('Failed to load meetings:', error);
		} finally {
			isLoading.set(false);
		}
	});

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

<div class="space-y-8">
	<!-- Logo -->
	<div class="flex justify-center py-4">
		<img src="/maxmeeting-final.png" alt="MAX Meeting" class="h-24 w-auto" />
	</div>

	<div class="flex justify-between items-center">
		<h1 class="text-2xl font-bold text-gray-900">대시보드</h1>
		<a href="/meetings/new" class="btn btn-primary">
			+ 새 회의
		</a>
	</div>

	{#if $isLoading}
		<div class="flex justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
		</div>
	{:else}
		<!-- In Progress Meeting -->
		{#if inProgressMeeting}
			<section class="card border-l-4 border-yellow-500" aria-labelledby="in-progress-title">
				<h2 id="in-progress-title" class="text-lg font-semibold text-gray-900 mb-4">
					회의 계속하기
				</h2>
				<div class="flex items-center justify-between">
					<div>
						<h3 class="font-medium text-gray-900">{inProgressMeeting.title}</h3>
						<p class="text-sm text-gray-500">{formatDateTime(inProgressMeeting.scheduled_at)}</p>
					</div>
					<a href="/meetings/{inProgressMeeting.id}" class="btn btn-primary">
						계속하기
					</a>
				</div>
			</section>
		{/if}

		<!-- Upcoming Meetings -->
		<section class="card" aria-labelledby="upcoming-title">
			<h2 id="upcoming-title" class="text-lg font-semibold text-gray-900 mb-4">
				예정된 회의
			</h2>
			{#if upcomingMeetings.length === 0}
				<p class="text-gray-500 text-sm">예정된 회의가 없습니다</p>
			{:else}
				<ul class="divide-y divide-gray-200">
					{#each upcomingMeetings as meeting (meeting.id)}
						<li class="py-4 first:pt-0 last:pb-0">
							<a href="/meetings/{meeting.id}" class="block hover:bg-gray-50 -mx-4 px-4 py-2 rounded">
								<div class="flex items-center justify-between">
									<div>
										<h3 class="font-medium text-gray-900">{meeting.title}</h3>
										<p class="text-sm text-gray-500">{formatDateTime(meeting.scheduled_at)}</p>
									</div>
									<span
										class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadgeClass(
											meeting.status
										)}"
									>
										{getStatusLabel(meeting.status)}
									</span>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<!-- Recent Meetings -->
		<section class="card" aria-labelledby="recent-title">
			<div class="flex justify-between items-center mb-4">
				<h2 id="recent-title" class="text-lg font-semibold text-gray-900">
					최근 회의
				</h2>
				<a href="/meetings" class="text-sm text-primary-600 hover:text-primary-700">
					전체 보기
				</a>
			</div>
			{#if recentMeetings.length === 0}
				<p class="text-gray-500 text-sm">완료된 회의가 없습니다</p>
			{:else}
				<ul class="divide-y divide-gray-200">
					{#each recentMeetings as meeting (meeting.id)}
						<li class="py-4 first:pt-0 last:pb-0">
							<a href="/meetings/{meeting.id}" class="block hover:bg-gray-50 -mx-4 px-4 py-2 rounded">
								<div class="flex items-center justify-between">
									<div>
										<h3 class="font-medium text-gray-900">{meeting.title}</h3>
										<p class="text-sm text-gray-500">{formatDateTime(meeting.scheduled_at)}</p>
									</div>
									<span
										class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadgeClass(
											meeting.status
										)}"
									>
										{getStatusLabel(meeting.status)}
									</span>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/if}
</div>
