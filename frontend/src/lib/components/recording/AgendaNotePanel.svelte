<script lang="ts">
	import { onDestroy } from 'svelte';
	import type { Agenda, AgendaQuestion } from '$lib/stores/meeting';

	interface Props {
		agendas: Agenda[];
		currentAgendaIndex: number;
		notes: Map<number, string>;
		onNextAgenda: (agendaId: number, timestamp: number) => void;
		onQuestionToggle: (questionId: number, answered: boolean) => void;
		onNoteChange: (agendaId: number, content: string) => void;
		recordingTime: number;
	}

	let {
		agendas,
		currentAgendaIndex = $bindable(),
		notes,
		onNextAgenda,
		onQuestionToggle,
		onNoteChange,
		recordingTime
	}: Props = $props();

	let noteDebounceTimers = new Map<number, ReturnType<typeof setTimeout>>();

	// Current agenda
	let currentAgenda = $derived(agendas[currentAgendaIndex]);
	let noteContent = $derived(currentAgenda ? (notes.get(currentAgenda.id) || '') : '');
	let answeredCount = $derived(currentAgenda ? currentAgenda.questions.filter(q => q.answered).length : 0);
	let totalQuestions = $derived(currentAgenda ? currentAgenda.questions.length : 0);

	// Cleanup on destroy
	onDestroy(() => {
		noteDebounceTimers.forEach((timer) => clearTimeout(timer));
		noteDebounceTimers.clear();
	});

	function handleQuestionToggle(question: AgendaQuestion) {
		onQuestionToggle(question.id, !question.answered);
	}

	function handleNoteInput(event: Event) {
		if (!currentAgenda) return;
		const target = event.target as HTMLTextAreaElement;
		const content = target.value;
		const agendaId = currentAgenda.id;

		// Clear existing timer
		const existingTimer = noteDebounceTimers.get(agendaId);
		if (existingTimer) {
			clearTimeout(existingTimer);
		}

		// Debounce note save
		const timer = setTimeout(() => {
			onNoteChange(agendaId, content);
			noteDebounceTimers.delete(agendaId);
		}, 500);

		noteDebounceTimers.set(agendaId, timer);
	}

	function goToPrevAgenda() {
		if (currentAgendaIndex > 0) {
			currentAgendaIndex--;
		}
	}

	function goToNextAgenda() {
		if (currentAgendaIndex < agendas.length - 1) {
			// Mark transition with timestamp for recording
			if (currentAgenda) {
				onNextAgenda(currentAgenda.id, recordingTime);
			}
			currentAgendaIndex++;
		}
	}

	function goToAgenda(index: number) {
		if (index >= 0 && index < agendas.length) {
			currentAgendaIndex = index;
		}
	}
</script>

<div class="w-full h-full bg-white flex flex-col overflow-hidden">
	{#if currentAgenda}
		<!-- Header with progress indicator -->
		<div class="px-4 py-3 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-white">
			<div class="flex items-center justify-between">
				<span class="text-sm font-medium text-blue-600">
					안건 {currentAgendaIndex + 1} / {agendas.length}
				</span>
				<!-- Mini progress dots -->
				<div class="flex gap-1.5">
					{#each agendas as _, i}
						<button
							type="button"
							onclick={() => goToAgenda(i)}
							class="w-2.5 h-2.5 rounded-full transition-all duration-200 {i === currentAgendaIndex ? 'bg-blue-600 scale-110' : i < currentAgendaIndex ? 'bg-blue-300' : 'bg-gray-300'}"
							aria-label="안건 {i + 1}로 이동"
						></button>
					{/each}
				</div>
			</div>
		</div>

		<!-- Scrollable content area -->
		<div class="flex-1 overflow-y-auto">
			<div class="p-4 space-y-5">
				<!-- Agenda Title -->
				<div>
					<h2 class="text-lg font-bold text-gray-900 leading-tight">
						{currentAgenda.title}
					</h2>
					{#if currentAgenda.status === 'in_progress'}
						<span class="inline-block mt-2 px-2.5 py-1 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full">
							진행중
						</span>
					{:else if currentAgenda.status === 'completed'}
						<span class="inline-block mt-2 px-2.5 py-1 text-xs font-semibold bg-green-100 text-green-700 rounded-full">
							완료
						</span>
					{/if}
				</div>

				<!-- Description -->
				{#if currentAgenda.description}
					<div class="bg-gray-50 rounded-xl p-4 border border-gray-100">
						<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							상세 내용
						</h3>
						<p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
							{currentAgenda.description}
						</p>
					</div>
				{/if}

				<!-- Children (Sub-topics) -->
				{#if currentAgenda.children && currentAgenda.children.length > 0}
					<div class="bg-blue-50 rounded-xl p-4 border border-blue-100">
						<h3 class="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-3">
							하위 토픽
						</h3>
						<ul class="space-y-2">
							{#each currentAgenda.children as child (child.id)}
								<li class="flex items-start gap-2">
									<span class="text-blue-400 mt-0.5">•</span>
									<div>
										<span class="text-sm font-medium text-gray-800">{child.title}</span>
										{#if child.description}
											<p class="text-xs text-gray-600 mt-0.5">{child.description}</p>
										{/if}
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Questions Checklist -->
				{#if totalQuestions > 0}
					<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
						<div class="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
							<h3 class="text-sm font-semibold text-gray-700">
								질문 체크리스트
							</h3>
							<span class="text-xs font-medium px-2.5 py-1 rounded-full {answeredCount === totalQuestions ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'}">
								{answeredCount}/{totalQuestions}
							</span>
						</div>
						<div class="p-3 space-y-1">
							{#each currentAgenda.questions as question (question.id)}
								<label class="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors min-h-[48px]">
									<input
										type="checkbox"
										checked={question.answered}
										onchange={() => handleQuestionToggle(question)}
										class="mt-0.5 w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer flex-shrink-0"
									/>
									<span
										class="text-sm text-gray-700 leading-relaxed flex-1 {question.answered ? 'line-through text-gray-400' : ''}"
									>
										{question.question}
									</span>
								</label>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Memo -->
				<div class="bg-white rounded-xl border border-gray-200 overflow-hidden">
					<div class="px-4 py-3 bg-gray-50 border-b border-gray-200">
						<h3 class="text-sm font-semibold text-gray-700">
							메모
						</h3>
					</div>
					<div class="p-3">
						<textarea
							value={noteContent}
							oninput={handleNoteInput}
							placeholder="이 안건에 대한 메모를 입력하세요..."
							rows="5"
							class="w-full px-4 py-3 text-base text-gray-900 placeholder-gray-400 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-shadow duration-150"
						></textarea>
					</div>
				</div>
			</div>
		</div>

		<!-- Navigation Footer -->
		<div class="border-t border-gray-200 bg-white p-4">
			<div class="flex gap-3">
				<button
					type="button"
					onclick={goToPrevAgenda}
					disabled={currentAgendaIndex === 0}
					class="flex-1 min-h-[52px] px-4 py-3 text-base font-medium rounded-xl transition-all duration-150 flex items-center justify-center gap-2
						{currentAgendaIndex === 0
							? 'bg-gray-100 text-gray-400 cursor-not-allowed'
							: 'bg-gray-100 text-gray-700 hover:bg-gray-200 active:bg-gray-300'}"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
					이전
				</button>
				<button
					type="button"
					onclick={goToNextAgenda}
					disabled={currentAgendaIndex === agendas.length - 1}
					class="flex-1 min-h-[52px] px-4 py-3 text-base font-medium rounded-xl transition-all duration-150 flex items-center justify-center gap-2
						{currentAgendaIndex === agendas.length - 1
							? 'bg-gray-100 text-gray-400 cursor-not-allowed'
							: 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800'}"
				>
					다음
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>
			</div>
		</div>
	{:else}
		<!-- No agenda state -->
		<div class="flex-1 flex items-center justify-center text-gray-500">
			<p>안건이 없습니다</p>
		</div>
	{/if}
</div>

<style>
	/* iPad optimization */
	button, label {
		-webkit-tap-highlight-color: transparent;
	}

	.overflow-y-auto {
		-webkit-overflow-scrolling: touch;
	}

	button {
		user-select: none;
		-webkit-user-select: none;
	}

	/* Smooth transitions */
	* {
		-webkit-font-smoothing: antialiased;
	}
</style>
