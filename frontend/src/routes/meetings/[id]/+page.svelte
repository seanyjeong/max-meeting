<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api';
	import { currentMeeting, isLoading, type MeetingDetail, type Agenda } from '$lib/stores/meeting';
	import {
		prefetchMeetingData,
		getCachedMeeting,
		isOffline
	} from '$lib/stores/offlineCache';

	$: meetingId = $page.params.id;

	let error = '';
	let isGeneratingQuestions = false;
	let isUsingCache = false;

	onMount(() => {
		loadMeeting();
		// prefetchMeetingData는 loadMeeting과 동일한 API를 호출하므로 제거
		// 대신 loadMeeting 성공 후 캐싱은 offlineCache 내부에서 처리
	});

	async function loadMeeting() {
		isLoading.set(true);
		error = '';
		isUsingCache = false;

		// 10초 타임아웃 설정
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), 10000);

		try {
			// 온라인 데이터 조회 시도
			const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
			clearTimeout(timeoutId);
			currentMeeting.set(response);
		} catch (err: unknown) {
			clearTimeout(timeoutId);
			const errorObj = err as { code?: string; message?: string; name?: string };

			if (import.meta.env.DEV) console.error('회의 데이터 로드 실패:', err);

			// AbortError (타임아웃)
			if (errorObj.name === 'AbortError') {
				error = '요청 시간이 초과되었습니다. 다시 시도해주세요.';
				isLoading.set(false);
				return;
			}

			// 네트워크 에러 또는 오프라인일 경우 캐시에서 조회
			if (isOffline() || errorObj.code === 'NETWORK_ERROR') {
				if (import.meta.env.DEV) console.log('오프라인 모드: 캐시에서 데이터 조회');
				try {
					if (meetingId) {
						const cachedMeeting = await getCachedMeeting(parseInt(meetingId));
						if (cachedMeeting) {
							currentMeeting.set(cachedMeeting);
							isUsingCache = true;
							error = '오프라인 모드 (캐시된 데이터)';
						} else {
							error = '서버에 연결할 수 없고 캐시된 데이터도 없습니다';
						}
					}
				} catch (cacheErr) {
					if (import.meta.env.DEV) console.error('캐시 조회 실패:', cacheErr);
					error = '회의 데이터를 불러올 수 없습니다';
				}
			} else {
				// 기타 API 에러
				error = errorObj.message || '회의 데이터 로드 실패';
			}
		} finally {
			isLoading.set(false);
		}
	}

	async function generateQuestions(agendaId: number) {
		isGeneratingQuestions = true;
		try {
			await api.put(`/agendas/${agendaId}/questions`, {});
			await loadMeeting();
		} catch (err) {
			console.error('Failed to generate questions:', err);
		} finally {
			isGeneratingQuestions = false;
		}
	}

	async function startMeeting() {
		if (!$currentMeeting) return;

		try {
			await api.patch(`/meetings/${meetingId}`, { status: 'in_progress' });
			goto(`/meetings/${meetingId}/record`);
		} catch (err) {
			console.error('Failed to start meeting:', err);
		}
	}

	async function finishMeeting() {
		if (!$currentMeeting) return;

		console.log('[meeting] Finishing meeting:', meetingId);
		try {
			const response = await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
			console.log('[meeting] Meeting finished, response:', response);
			// Update local state
			$currentMeeting = { ...$currentMeeting, status: 'completed' };
			goto(`/meetings/${meetingId}/results`);
		} catch (err) {
			console.error('[meeting] Failed to finish meeting:', err);
		}
	}

	async function startWithoutRecording() {
		if (!$currentMeeting) return;

		try {
			// Set status to completed directly (skip recording)
			await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
			goto(`/meetings/${meetingId}/results`);
		} catch (err) {
			console.error('Failed to start without recording:', err);
		}
	}

	async function deleteMeeting() {
		if (!confirm('이 회의를 삭제하시겠습니까?')) return;

		try {
			await api.delete(`/meetings/${meetingId}`);
			goto('/meetings');
		} catch (err) {
			console.error('Failed to delete meeting:', err);
		}
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '-';
		return new Date(dateStr).toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusBadgeClass(status: string): string {
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

	function getStatusLabel(status: string): string {
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

	function getAgendaStatusClass(status: Agenda['status']): string {
		switch (status) {
			case 'pending':
				return 'text-gray-400';
			case 'in_progress':
				return 'text-yellow-500';
			case 'completed':
				return 'text-green-500';
			default:
				return 'text-gray-400';
		}
	}
</script>

<svelte:head>
	<title>{$currentMeeting?.title || '회의'} - MAX Meeting</title>
</svelte:head>

{#if $isLoading}
	<div class="flex justify-center py-12">
		<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
	</div>
{:else if error && !isUsingCache}
	<div class="card text-center py-12">
		<p class="text-red-600">{error}</p>
		<button type="button" onclick={loadMeeting} class="btn btn-primary mt-4">
			다시 시도
		</button>
	</div>
{:else if $currentMeeting}
	<div class="space-y-6">
		<!-- 오프라인 모드 배너 -->
		{#if isUsingCache}
			<div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
				<div class="flex">
					<div class="flex-shrink-0">
						<svg
							class="h-5 w-5 text-yellow-400"
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
						>
							<path
								fill-rule="evenodd"
								d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class="ml-3">
						<p class="text-sm text-yellow-700">
							오프라인 모드입니다. 캐시된 데이터를 표시하고 있습니다. 일부 기능이 제한될 수
							있습니다.
						</p>
					</div>
				</div>
			</div>
		{/if}

		<!-- Breadcrumb -->
		<nav class="text-sm text-gray-500" aria-label="Breadcrumb">
			<ol class="flex items-center space-x-2">
				<li><a href="/" class="hover:text-gray-700">홈</a></li>
				<li><span class="mx-1">/</span></li>
				<li><a href="/meetings" class="hover:text-gray-700">회의</a></li>
				<li><span class="mx-1">/</span></li>
				<li class="text-gray-900 font-medium">{$currentMeeting.title}</li>
			</ol>
		</nav>

		<!-- Header -->
		<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
			<div>
				<div class="flex items-center gap-3">
					<h1 class="text-2xl font-bold text-gray-900">{$currentMeeting.title}</h1>
					<span
						class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStatusBadgeClass(
							$currentMeeting.status
						)}"
					>
						{getStatusLabel($currentMeeting.status)}
					</span>
				</div>
				{#if $currentMeeting.meeting_type?.name}
					<p class="mt-1 text-sm text-gray-500">{$currentMeeting.meeting_type.name}</p>
				{/if}
			</div>

			<div class="flex items-center gap-2">
				{#if $currentMeeting.status === 'draft'}
					<button
						type="button"
						onclick={startWithoutRecording}
						disabled={isUsingCache}
						class="btn btn-secondary"
						title="녹음 없이 메모 기반으로 회의록 생성"
					>
						메모로 시작
					</button>
					<button
						type="button"
						onclick={startMeeting}
						disabled={isUsingCache}
						class="btn btn-primary"
					>
						녹음으로 시작
					</button>
				{:else if $currentMeeting.status === 'in_progress'}
					<a href="/meetings/{meetingId}/record" class="btn btn-secondary">
						녹음 계속하기
					</a>
					<button
						type="button"
						onclick={finishMeeting}
						disabled={isUsingCache}
						class="btn btn-primary"
					>
						회의 마무리
					</button>
				{:else if $currentMeeting.status === 'completed'}
					<a href="/meetings/{meetingId}/results" class="btn btn-primary">
						결과 보기
					</a>
				{/if}
				<button
					type="button"
					onclick={deleteMeeting}
					disabled={isUsingCache}
					class="btn btn-secondary text-red-600"
				>
					삭제
				</button>
			</div>
		</div>

		<!-- Meeting Info -->
		<div class="card">
			<h2 class="text-lg font-medium text-gray-900 mb-4">회의 상세</h2>
			<dl class="grid grid-cols-1 sm:grid-cols-2 gap-4">
				<div>
					<dt class="text-sm font-medium text-gray-500">일시</dt>
					<dd class="mt-1 text-sm text-gray-900">{formatDate($currentMeeting.scheduled_at)}</dd>
				</div>
				<div>
					<dt class="text-sm font-medium text-gray-500">장소</dt>
					<dd class="mt-1 text-sm text-gray-900">{$currentMeeting.location || '-'}</dd>
				</div>
			</dl>
		</div>

		<!-- Attendees -->
		{#if $currentMeeting.attendees && $currentMeeting.attendees.length > 0}
			<div class="card">
				<h2 class="text-lg font-medium text-gray-900 mb-4">
					참석자 ({$currentMeeting.attendees.length})
				</h2>
				<div class="flex flex-wrap gap-2">
					{#each $currentMeeting.attendees as attendee (attendee.id)}
						<span class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-700">
							{attendee.contact?.name || '(알 수 없음)'}
							{#if attendee.contact?.role}
								<span class="ml-1 text-gray-500">({attendee.contact.role})</span>
							{/if}
						</span>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Agendas -->
		<div class="card">
			<h2 class="text-lg font-medium text-gray-900 mb-4">
				안건 ({$currentMeeting.agendas?.length || 0})
			</h2>

			{#if !$currentMeeting.agendas || $currentMeeting.agendas.length === 0}
				<p class="text-sm text-gray-500">안건이 없습니다</p>
			{:else}
				<div class="space-y-4">
					{#each $currentMeeting.agendas as agenda, index (agenda.id)}
						<div class="border border-gray-200 rounded-lg p-4">
							<div class="flex items-start justify-between">
								<div class="flex items-start gap-3">
									<span class="flex-shrink-0 w-6 h-6 rounded-full bg-gray-100 text-gray-600 flex items-center justify-center text-sm font-medium">
										{index + 1}
									</span>
									<div>
										<h3 class="font-medium text-gray-900 flex items-center gap-2">
											{agenda.title}
											<span class={getAgendaStatusClass(agenda.status)}>
												{#if agenda.status === 'completed'}
													<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
													</svg>
												{:else if agenda.status === 'in_progress'}
													<svg class="w-4 h-4 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
													</svg>
												{/if}
											</span>
										</h3>
										{#if agenda.description}
											<p class="mt-1 text-sm text-gray-500">{agenda.description}</p>
										{/if}
									</div>
								</div>
							</div>

							<!-- Questions -->
							{#if agenda.questions && agenda.questions.length > 0}
								<div class="mt-4 pl-9">
									<p class="text-sm font-medium text-gray-700 mb-2">토의 질문</p>
									<ul class="space-y-2">
										{#each agenda.questions as question (question.id)}
											<li class="flex items-start gap-2 text-sm">
												<input
													type="checkbox"
													checked={question.answered}
													disabled
													class="mt-0.5 h-4 w-4 rounded border-gray-300"
												/>
												<span class={question.answered ? 'text-gray-400 line-through' : 'text-gray-700'}>
													{question.question}
												</span>
											</li>
										{/each}
									</ul>
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
