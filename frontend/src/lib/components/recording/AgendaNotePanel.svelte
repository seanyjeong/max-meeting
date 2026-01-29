<script lang="ts">
	import { onDestroy } from 'svelte';
	import { untrack } from 'svelte';
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
		currentAgendaIndex,
		notes,
		onNextAgenda,
		onQuestionToggle,
		onNoteChange,
		recordingTime
	}: Props = $props();

	let expandedAgendaIds = $state<Set<number>>(new Set());
	let noteDebounceTimers = new Map<number, ReturnType<typeof setTimeout>>();

	// Auto-expand current agenda (use untrack to avoid infinite loop)
	$effect(() => {
		const currentAgenda = agendas[currentAgendaIndex];
		if (currentAgenda) {
			const agendaId = currentAgenda.id;
			untrack(() => {
				if (!expandedAgendaIds.has(agendaId)) {
					expandedAgendaIds = new Set([...expandedAgendaIds, agendaId]);
				}
			});
		}
	});

	// Cleanup on destroy
	onDestroy(() => {
		noteDebounceTimers.forEach((timer) => clearTimeout(timer));
		noteDebounceTimers.clear();
	});

	function toggleAgenda(agendaId: number) {
		if (expandedAgendaIds.has(agendaId)) {
			const newSet = new Set(expandedAgendaIds);
			newSet.delete(agendaId);
			expandedAgendaIds = newSet;
		} else {
			expandedAgendaIds = new Set([...expandedAgendaIds, agendaId]);
		}
	}

	function handleQuestionToggle(question: AgendaQuestion) {
		onQuestionToggle(question.id, !question.answered);
	}

	function handleNoteInput(agendaId: number, event: Event) {
		const target = event.target as HTMLTextAreaElement;
		const content = target.value;

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

	function handleNextAgenda(agendaId: number) {
		onNextAgenda(agendaId, recordingTime);
	}

	function isCurrentAgenda(index: number): boolean {
		return index === currentAgendaIndex;
	}
</script>

<div class="w-full h-full bg-white border-l border-gray-200 flex flex-col overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
		<h3 class="text-sm font-semibold text-gray-900">안건 및 메모</h3>
	</div>

	<!-- Scrollable agenda list -->
	<div class="flex-1 overflow-y-auto">
		<div class="divide-y divide-gray-100">
			{#each agendas as agenda, index (agenda.id)}
				{@const isExpanded = expandedAgendaIds.has(agenda.id)}
				{@const isCurrent = isCurrentAgenda(index)}
				{@const noteContent = notes.get(agenda.id) || ''}

				<div
					class="transition-colors duration-150"
					class:bg-blue-50={isCurrent}
					class:border-l-4={isCurrent}
					class:border-blue-600={isCurrent}
				>
					<!-- Agenda header -->
					<button
						type="button"
						onclick={() => toggleAgenda(agenda.id)}
						aria-label="안건 {index + 1} {isExpanded ? '접기' : '펼치기'}"
						aria-expanded={isExpanded}
						class="w-full px-4 py-3 flex items-start gap-2 hover:bg-gray-50 transition-colors duration-150 text-left"
						class:hover:bg-blue-100={isCurrent}
					>
						<div class="mt-0.5 flex-shrink-0">
							{#if isExpanded}
								<!-- ChevronDown icon -->
								<svg class="w-4 h-4 text-gray-500 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
								</svg>
							{:else}
								<!-- ChevronRight icon -->
								<svg class="w-4 h-4 text-gray-500 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							{/if}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2">
								<span
									class="text-sm font-medium"
									class:text-blue-700={isCurrent}
									class:text-gray-900={!isCurrent}
								>
									{index + 1}. {agenda.title}
								</span>
								{#if isCurrent}
									<span
										class="px-1.5 py-0.5 text-xs font-medium bg-blue-600 text-white rounded"
									>
										진행중
									</span>
								{:else if agenda.status === 'completed'}
									<span
										class="px-1.5 py-0.5 text-xs font-medium bg-gray-500 text-white rounded"
									>
										완료
									</span>
								{/if}
							</div>
							{#if agenda.description}
								<p class="mt-0.5 text-xs text-gray-500 line-clamp-1">
									{agenda.description}
								</p>
							{/if}
						</div>
					</button>

					<!-- Expanded content -->
					{#if isExpanded}
						<div class="px-4 pb-4 space-y-3">
							<!-- Questions checklist -->
							{#if agenda.questions.length > 0}
								<div class="space-y-2">
									{#each agenda.questions as question (question.id)}
										<label class="flex items-start gap-2 group cursor-pointer">
											<input
												type="checkbox"
												checked={question.answered}
												onchange={() => handleQuestionToggle(question)}
												class="mt-0.5 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
											/>
											<span
												class="text-sm text-gray-700 group-hover:text-gray-900 transition-colors duration-150 flex-1"
												class:line-through={question.answered}
												class:text-gray-500={question.answered}
											>
												{question.question}
											</span>
										</label>
									{/each}
								</div>
							{/if}

							<!-- Notes textarea -->
							<div>
								<textarea
									value={noteContent}
									oninput={(e) => handleNoteInput(agenda.id, e)}
									placeholder="안건별 메모..."
									rows="3"
									class="w-full px-3 py-2 text-sm text-gray-900 placeholder-gray-400 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-shadow duration-150"
								></textarea>
							</div>

							<!-- Next agenda button (only for current agenda) -->
							{#if isCurrent && index < agendas.length - 1}
								<button
									type="button"
									onclick={() => handleNextAgenda(agenda.id)}
									class="w-full px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 hover:border-blue-300 transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
								>
									다음 안건 →
								</button>
							{/if}
						</div>
					{/if}
				</div>
			{/each}
		</div>
	</div>
</div>
