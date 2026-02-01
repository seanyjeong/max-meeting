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
	import { Pencil, Trash2, X, Check, Plus, RefreshCw } from 'lucide-svelte';
	import { formatDateTime } from '$lib/utils/format';
	import { logger } from '$lib/utils/logger';

	let meetingId = $derived($page.params.id);

	let error = $state('');
	let isGeneratingQuestions = $state(false);
	let isUsingCache = $state(false);

	// 안건 토글 상태
	let expandedAgendas = $state(new Set<number>());
	let expandedChildren = $state(new Set<number>());

	// 질문 수정/삭제/생성 상태
	let editingQuestionId = $state<number | null>(null);
	let editingQuestionText = $state('');
	let addingQuestionAgendaId = $state<number | null>(null);
	let newQuestionText = $state('');
	// 태블릿용: 선택된 질문 (클릭 시 수정/삭제 버튼 표시)
	let selectedQuestionId = $state<number | null>(null);

	function toggleQuestionSelection(questionId: number) {
		if (selectedQuestionId === questionId) {
			selectedQuestionId = null;
		} else {
			selectedQuestionId = questionId;
		}
	}

	async function addQuestion(agendaId: number) {
		if (!newQuestionText.trim()) return;
		try {
			await api.post(`/agendas/${agendaId}/questions`, {
				question: newQuestionText.trim()
			});
			newQuestionText = '';
			addingQuestionAgendaId = null;
			await loadMeeting();
		} catch (err) {
			logger.error('Failed to add question:', err);
			error = '질문 추가에 실패했습니다.';
		}
	}

	async function deleteQuestion(questionId: number) {
		if (!confirm('이 질문을 삭제하시겠습니까?')) return;
		try {
			await api.delete(`/questions/${questionId}`);
			await loadMeeting(); // 새로고침
		} catch (err) {
			logger.error('Failed to delete question:', err);
			error = '질문 삭제에 실패했습니다.';
		}
	}

	function startEditQuestion(questionId: number, currentText: string) {
		editingQuestionId = questionId;
		editingQuestionText = currentText;
	}

	function cancelEditQuestion() {
		editingQuestionId = null;
		editingQuestionText = '';
	}

	async function saveEditQuestion(questionId: number) {
		if (!editingQuestionText.trim()) return;
		try {
			await api.patch(`/questions/${questionId}`, {
				question: editingQuestionText.trim()
			});
			editingQuestionId = null;
			editingQuestionText = '';
			await loadMeeting();
		} catch (err) {
			logger.error('Failed to update question:', err);
			error = '질문 수정에 실패했습니다.';
		}
	}

	function toggleAgenda(id: number) {
		if (expandedAgendas.has(id)) {
			expandedAgendas.delete(id);
		} else {
			expandedAgendas.add(id);
		}
		expandedAgendas = new Set(expandedAgendas);
	}

	function toggleChild(id: number) {
		if (expandedChildren.has(id)) {
			expandedChildren.delete(id);
		} else {
			expandedChildren.add(id);
		}
		expandedChildren = new Set(expandedChildren);
	}

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

			logger.error('회의 데이터 로드 실패:', err);

			// AbortError (타임아웃)
			if (errorObj.name === 'AbortError') {
				error = '요청 시간이 초과되었습니다. 다시 시도해주세요.';
				isLoading.set(false);
				return;
			}

			// 네트워크 에러 또는 오프라인일 경우 캐시에서 조회
			if (isOffline() || errorObj.code === 'NETWORK_ERROR') {
				logger.debug('오프라인 모드: 캐시에서 데이터 조회');
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
					logger.error('캐시 조회 실패:', cacheErr);
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
			logger.error('Failed to generate questions:', err);
		} finally {
			isGeneratingQuestions = false;
		}
	}

	let regeneratingAgendaId = $state<number | null>(null);

	async function regenerateQuestions(agendaId: number) {
		regeneratingAgendaId = agendaId;
		try {
			await api.post(`/agendas/${agendaId}/questions/regenerate`);
			await loadMeeting();
		} catch (err) {
			logger.error('Failed to regenerate questions:', err);
		} finally {
			regeneratingAgendaId = null;
		}
	}

	async function startMeeting() {
		if (!$currentMeeting) return;

		try {
			await api.patch(`/meetings/${meetingId}`, { status: 'in_progress' });
			goto(`/meetings/${meetingId}/record`);
		} catch (err) {
			logger.error('Failed to start meeting:', err);
		}
	}

	async function finishMeeting() {
		if (!$currentMeeting) return;

		logger.debug('[meeting] Finishing meeting:', meetingId);
		try {
			const response = await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
			logger.debug('[meeting] Meeting finished, response:', response);
			// Update local state
			$currentMeeting = { ...$currentMeeting, status: 'completed' };
			goto(`/meetings/${meetingId}/results`);
		} catch (err) {
			logger.error('[meeting] Failed to finish meeting:', err);
		}
	}

	async function startWithoutRecording() {
		if (!$currentMeeting) return;

		try {
			// Set status to completed directly (skip recording)
			await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
			goto(`/meetings/${meetingId}/results`);
		} catch (err) {
			logger.error('Failed to start without recording:', err);
		}
	}

	async function deleteMeeting() {
		if (!confirm('이 회의를 삭제하시겠습니까?')) return;

		try {
			await api.delete(`/meetings/${meetingId}`);
			goto('/meetings');
		} catch (err) {
			logger.error('Failed to delete meeting:', err);
		}
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
						onclick={startMeeting}
						disabled={isUsingCache}
						class="btn btn-primary"
					>
						회의 시작
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
					<dd class="mt-1 text-sm text-gray-900">{formatDateTime($currentMeeting.scheduled_at)}</dd>
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
				<div class="space-y-3">
					{#each $currentMeeting.agendas as agenda, index (agenda.id)}
						<div class="border border-gray-200 rounded-lg overflow-hidden">
							<!-- 대안건 헤더 (클릭으로 토글) -->
							<button
								type="button"
								onclick={() => toggleAgenda(agenda.id)}
								class="w-full p-4 flex items-center gap-3 text-left hover:bg-gray-50 transition-colors"
							>
								<span class="flex-shrink-0 text-gray-400 transition-transform {expandedAgendas.has(agenda.id) ? 'rotate-90' : ''}">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
									</svg>
								</span>
								<span class="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-semibold">
									{index + 1}
								</span>
								<div class="flex-1 min-w-0">
									<h3 class="font-medium text-gray-900 flex items-center gap-2">
										{agenda.title}
										{#if agenda.children && agenda.children.length > 0}
											<span class="text-xs text-gray-400">({agenda.children.length}개 하위 안건)</span>
										{/if}
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
										<p class="mt-1 text-sm text-gray-500 truncate">{agenda.description}</p>
									{/if}
								</div>
							</button>

							<!-- 펼쳐진 내용 -->
							{#if expandedAgendas.has(agenda.id)}
								<div class="border-t border-gray-100 bg-gray-50/50">
									<!-- 자식안건이 있으면 -->
									{#if agenda.children && agenda.children.length > 0}
										<div class="p-4 space-y-3">
											{#each agenda.children as child, childIndex (child.id)}
												<div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
													<!-- 자식안건 헤더 -->
													<button
														type="button"
														onclick={() => toggleChild(child.id)}
														class="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-gray-50 transition-colors"
													>
														<span class="flex-shrink-0 text-gray-400 transition-transform {expandedChildren.has(child.id) ? 'rotate-90' : ''}">
															<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
															</svg>
														</span>
														<span class="flex-shrink-0 text-sm font-medium text-gray-500">
															{index + 1}.{childIndex + 1}
														</span>
														<span class="flex-1 text-sm font-medium text-gray-800">
															{child.title}
														</span>
														{#if child.questions && child.questions.length > 0}
															<span class="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
																질문 {child.questions.length}
															</span>
														{/if}
													</button>

													<!-- 자식안건 내용 -->
													{#if expandedChildren.has(child.id)}
														<div class="px-4 pb-3 pt-1 border-t border-gray-100">
															{#if child.description}
																<p class="text-sm text-gray-600 mb-3">{child.description}</p>
															{/if}
															<!-- 자식안건의 질문 -->
															{#if child.questions && child.questions.length > 0}
																<div class="space-y-2">
																	<p class="text-xs font-semibold text-gray-500 uppercase">토의 질문</p>
																	{#each child.questions as question (question.id)}
																		<button
																			type="button"
																			onclick={() => toggleQuestionSelection(question.id)}
																			class="w-full flex items-start gap-2 text-sm group text-left p-1 -m-1 rounded hover:bg-gray-50 {selectedQuestionId === question.id ? 'bg-blue-50 ring-1 ring-blue-200' : ''}"
																		>
																			<input
																				type="checkbox"
																				checked={question.answered}
																				disabled
																				class="mt-0.5 h-4 w-4 rounded border-gray-300"
																				onclick={(e) => e.stopPropagation()}
																			/>
																			{#if editingQuestionId === question.id}
																				<input
																					type="text"
																					bind:value={editingQuestionText}
																					class="flex-1 px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
																					onkeydown={(e) => e.key === 'Enter' && saveEditQuestion(question.id)}
																					onclick={(e) => e.stopPropagation()}
																				/>
																				<button onclick={(e) => { e.stopPropagation(); saveEditQuestion(question.id); }} class="p-1 text-green-600 hover:bg-green-50 rounded">
																					<Check class="w-4 h-4" />
																				</button>
																				<button onclick={(e) => { e.stopPropagation(); cancelEditQuestion(); }} class="p-1 text-gray-600 hover:bg-gray-100 rounded">
																					<X class="w-4 h-4" />
																				</button>
																			{:else}
																				<span class="flex-1 {question.answered ? 'text-gray-400 line-through' : 'text-gray-700'}">
																					{question.question}
																				</span>
																				<div class="{selectedQuestionId === question.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} flex gap-1 transition-opacity">
																					<button onclick={(e) => { e.stopPropagation(); startEditQuestion(question.id, question.question); }} class="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded" title="수정">
																						<Pencil class="w-3.5 h-3.5" />
																					</button>
																					<button onclick={(e) => { e.stopPropagation(); deleteQuestion(question.id); }} class="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded" title="삭제">
																						<Trash2 class="w-3.5 h-3.5" />
																					</button>
																				</div>
																			{/if}
																		</button>
																	{/each}
																</div>
															{/if}
															<!-- 손자안건 (3레벨) -->
															{#if child.children && child.children.length > 0}
																<div class="mt-3 space-y-2">
																	<p class="text-xs font-semibold text-gray-500 uppercase">하위 안건</p>
																	{#each child.children as grandchild, grandchildIndex (grandchild.id)}
																		<div class="ml-2 p-2 bg-pink-50 rounded border border-pink-100">
																			<div class="flex items-center gap-2">
																				<span class="text-xs font-medium text-pink-600">
																					{index + 1}.{childIndex + 1}.{grandchildIndex + 1}
																				</span>
																				<span class="text-sm text-gray-700">{grandchild.title}</span>
																			</div>
																			{#if grandchild.description}
																				<p class="mt-1 text-xs text-gray-500 ml-6">{grandchild.description}</p>
																			{/if}
																			{#if grandchild.questions && grandchild.questions.length > 0}
																				<div class="mt-2 ml-6 space-y-1">
																					{#each grandchild.questions as gq (gq.id)}
																						<div class="flex items-start gap-2 text-xs">
																							<input type="checkbox" checked={gq.answered} disabled class="mt-0.5 h-3 w-3 rounded border-gray-300" />
																							<span class="{gq.answered ? 'text-gray-400 line-through' : 'text-gray-600'}">{gq.question}</span>
																						</div>
																					{/each}
																				</div>
																			{/if}
																		</div>
																	{/each}
																</div>
															{/if}
															<!-- 질문 추가 버튼 -->
															{#if addingQuestionAgendaId === child.id}
																<div class="flex items-center gap-2 mt-2">
																	<input
																		type="text"
																		bind:value={newQuestionText}
																		placeholder="새 질문 입력..."
																		class="flex-1 px-2 py-1 text-sm border border-green-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
																		onkeydown={(e) => e.key === 'Enter' && addQuestion(child.id)}
																	/>
																	<button onclick={() => addQuestion(child.id)} class="p-1 text-green-600 hover:bg-green-50 rounded">
																		<Check class="w-4 h-4" />
																	</button>
																	<button onclick={() => { addingQuestionAgendaId = null; newQuestionText = ''; }} class="p-1 text-gray-600 hover:bg-gray-100 rounded">
																		<X class="w-4 h-4" />
																	</button>
																</div>
															{:else}
																<div class="flex items-center gap-3 mt-2">
																	<button
																		onclick={() => addingQuestionAgendaId = child.id}
																		class="text-xs text-green-600 hover:text-green-700 flex items-center gap-1"
																	>
																		<Plus class="w-3 h-3" /> 질문 추가
																	</button>
																	{#if child.questions && child.questions.length > 0}
																		<button
																			onclick={() => regenerateQuestions(child.id)}
																			disabled={regeneratingAgendaId === child.id}
																			class="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 disabled:opacity-50"
																		>
																			<RefreshCw class="w-3 h-3 {regeneratingAgendaId === child.id ? 'animate-spin' : ''}" />
																			{regeneratingAgendaId === child.id ? '생성 중...' : '질문 재생성'}
																		</button>
																	{/if}
																</div>
															{/if}
														</div>
													{/if}
												</div>
											{/each}
										</div>
									{:else}
										<!-- 자식안건 없으면 대안건 상세 + 질문 표시 -->
										<div class="p-4">
											{#if agenda.description}
												<p class="text-sm text-gray-600 mb-3">{agenda.description}</p>
											{/if}
											{#if agenda.questions && agenda.questions.length > 0}
												<div class="space-y-2">
													<p class="text-xs font-semibold text-gray-500 uppercase">토의 질문</p>
													{#each agenda.questions as question (question.id)}
														<button
															type="button"
															onclick={() => toggleQuestionSelection(question.id)}
															class="w-full flex items-start gap-2 text-sm group text-left p-1 -m-1 rounded hover:bg-gray-50 {selectedQuestionId === question.id ? 'bg-blue-50 ring-1 ring-blue-200' : ''}"
														>
															<input
																type="checkbox"
																checked={question.answered}
																disabled
																class="mt-0.5 h-4 w-4 rounded border-gray-300"
																onclick={(e) => e.stopPropagation()}
															/>
															{#if editingQuestionId === question.id}
																<input
																	type="text"
																	bind:value={editingQuestionText}
																	class="flex-1 px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
																	onkeydown={(e) => e.key === 'Enter' && saveEditQuestion(question.id)}
																	onclick={(e) => e.stopPropagation()}
																/>
																<button onclick={(e) => { e.stopPropagation(); saveEditQuestion(question.id); }} class="p-1 text-green-600 hover:bg-green-50 rounded">
																	<Check class="w-4 h-4" />
																</button>
																<button onclick={(e) => { e.stopPropagation(); cancelEditQuestion(); }} class="p-1 text-gray-600 hover:bg-gray-100 rounded">
																	<X class="w-4 h-4" />
																</button>
															{:else}
																<span class="flex-1 {question.answered ? 'text-gray-400 line-through' : 'text-gray-700'}">
																	{question.question}
																</span>
																<div class="{selectedQuestionId === question.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'} flex gap-1 transition-opacity">
																	<button onclick={(e) => { e.stopPropagation(); startEditQuestion(question.id, question.question); }} class="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded" title="수정">
																		<Pencil class="w-3.5 h-3.5" />
																	</button>
																	<button onclick={(e) => { e.stopPropagation(); deleteQuestion(question.id); }} class="p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded" title="삭제">
																		<Trash2 class="w-3.5 h-3.5" />
																	</button>
																</div>
															{/if}
														</button>
													{/each}
												</div>
											{/if}
											<!-- 대안건 질문 추가 버튼 -->
											{#if addingQuestionAgendaId === agenda.id}
												<div class="flex items-center gap-2 mt-2">
													<input
														type="text"
														bind:value={newQuestionText}
														placeholder="새 질문 입력..."
														class="flex-1 px-2 py-1 text-sm border border-green-300 rounded focus:outline-none focus:ring-1 focus:ring-green-500"
														onkeydown={(e) => e.key === 'Enter' && addQuestion(agenda.id)}
													/>
													<button onclick={() => addQuestion(agenda.id)} class="p-1 text-green-600 hover:bg-green-50 rounded">
														<Check class="w-4 h-4" />
													</button>
													<button onclick={() => { addingQuestionAgendaId = null; newQuestionText = ''; }} class="p-1 text-gray-600 hover:bg-gray-100 rounded">
														<X class="w-4 h-4" />
													</button>
												</div>
											{:else}
												<div class="flex items-center gap-3 mt-2">
													<button
														onclick={() => addingQuestionAgendaId = agenda.id}
														class="text-xs text-green-600 hover:text-green-700 flex items-center gap-1"
													>
														<Plus class="w-3 h-3" /> 질문 추가
													</button>
													{#if agenda.questions && agenda.questions.length > 0}
														<button
															onclick={() => regenerateQuestions(agenda.id)}
															disabled={regeneratingAgendaId === agenda.id}
															class="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 disabled:opacity-50"
														>
															<RefreshCw class="w-3 h-3 {regeneratingAgendaId === agenda.id ? 'animate-spin' : ''}" />
															{regeneratingAgendaId === agenda.id ? '생성 중...' : '질문 재생성'}
														</button>
													{/if}
												</div>
											{/if}
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}
