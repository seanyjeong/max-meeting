<script lang="ts">
	/**
	 * AgendaTracker - Shows current agenda and tracks progress
	 *
	 * - Displays agenda list with current highlight
	 * - "다음 안건" button records timestamp
	 * - Question checklist with color coding
	 */
	import type { Agenda, AgendaQuestion } from '$lib/stores/meeting';
	import { recordingTime, formatTime } from '$lib/stores/recording';
	import Button from '$lib/components/Button.svelte';

	interface Props {
		agendas: Agenda[];
		currentAgendaIndex?: number;
		collapsed?: boolean;
		onNextAgenda?: (agendaId: number, timestamp: number) => void;
		onQuestionToggle?: (questionId: number, answered: boolean) => void;
		onToggleCollapse?: () => void;
	}

	let {
		agendas = [],
		currentAgendaIndex = 0,
		collapsed = false,
		onNextAgenda,
		onQuestionToggle,
		onToggleCollapse
	}: Props = $props();

	// Calculate progress for each agenda
	function getAgendaProgress(agenda: Agenda): number {
		if (!agenda.questions || agenda.questions.length === 0) return 0;
		const answered = agenda.questions.filter((q) => q.answered).length;
		return (answered / agenda.questions.length) * 100;
	}

	function getStatusColor(status: Agenda['status']): string {
		switch (status) {
			case 'completed':
				return 'bg-green-500';
			case 'in_progress':
				return 'bg-yellow-500';
			default:
				return 'bg-gray-300';
		}
	}

	function getQuestionColor(answered: boolean): string {
		return answered ? 'text-green-600 bg-green-50' : 'text-gray-600 bg-gray-50';
	}

	function handleNextAgenda() {
		if (currentAgendaIndex < agendas.length - 1) {
			const nextAgenda = agendas[currentAgendaIndex + 1];
			onNextAgenda?.(nextAgenda.id, $recordingTime);
		}
	}

	function handleQuestionClick(question: AgendaQuestion) {
		onQuestionToggle?.(question.id, !question.answered);
	}
</script>

<aside
	class="agenda-tracker {collapsed ? 'w-12' : 'w-full md:w-80'} transition-all duration-300"
	aria-label="안건 패널"
>
	<!-- Collapse Toggle -->
	<button
		type="button"
		onclick={onToggleCollapse}
		class="w-full flex items-center justify-between p-3 bg-gray-100 hover:bg-gray-200 transition-colors"
		aria-expanded={!collapsed}
		aria-controls="agenda-list"
	>
		{#if collapsed}
			<svg class="w-5 h-5 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		{:else}
			<span class="font-medium text-gray-700">안건 목록</span>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		{/if}
	</button>

	{#if !collapsed}
		<div id="agenda-list" class="p-4 space-y-4 overflow-y-auto max-h-[calc(100vh-300px)]">
			{#each agendas as agenda, index (agenda.id)}
				{@const isCurrent = index === currentAgendaIndex}
				{@const isCompleted = agenda.status === 'completed'}

				<div
					class="agenda-item rounded-lg border {isCurrent
						? 'border-primary-500 bg-primary-50'
						: isCompleted
							? 'border-green-200 bg-green-50'
							: 'border-gray-200 bg-white'}"
				>
					<!-- Agenda Header -->
					<div class="p-3">
						<div class="flex items-center gap-2 mb-2">
							<!-- Status indicator -->
							<span
								class="w-3 h-3 rounded-full flex-shrink-0 {getStatusColor(agenda.status)}"
								aria-hidden="true"
							></span>

							<!-- Agenda title -->
							<h4
								class="font-medium {isCurrent ? 'text-primary-700' : isCompleted ? 'text-green-700' : 'text-gray-800'}"
							>
								{agenda.order_num}. {agenda.title}
							</h4>
						</div>

						<!-- Progress bar -->
						{#if agenda.questions && agenda.questions.length > 0}
							<div class="mb-2">
								<div class="h-1.5 bg-gray-200 rounded-full overflow-hidden">
									<div
										class="h-full {isCurrent ? 'bg-primary-500' : 'bg-green-500'} transition-all duration-300"
										style="width: {getAgendaProgress(agenda)}%"
									></div>
								</div>
							</div>
						{/if}

						<!-- Timestamp -->
						{#if agenda.started_at_seconds !== null}
							<p class="text-xs text-gray-500">
								시작: {formatTime(agenda.started_at_seconds)}
							</p>
						{/if}
					</div>

					<!-- Question Checklist (only show for current or expanded) -->
					{#if isCurrent && agenda.questions && agenda.questions.length > 0}
						<div class="border-t border-gray-200 p-3 space-y-2">
							{#each agenda.questions as question (question.id)}
								<button
									type="button"
									onclick={() => handleQuestionClick(question)}
									class="w-full flex items-start gap-2 p-2 rounded-md text-left transition-colors {getQuestionColor(question.answered)} hover:opacity-80"
								>
									<!-- Checkbox -->
									<span
										class="w-5 h-5 flex-shrink-0 rounded border-2 flex items-center justify-center mt-0.5 {question.answered
											? 'bg-green-500 border-green-500'
											: 'border-gray-300'}"
									>
										{#if question.answered}
											<svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
												<path
													fill-rule="evenodd"
													d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
										{/if}
									</span>

									<span class="text-sm">{question.question}</span>
								</button>
							{/each}
						</div>
					{/if}
				</div>
			{/each}

			<!-- Next Agenda Button -->
			{#if currentAgendaIndex < agendas.length - 1}
				<div class="pt-4 border-t border-gray-200">
					<Button variant="primary" onclick={handleNextAgenda} class="w-full">
						다음 안건
						<svg class="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 5l7 7-7 7"
							/>
						</svg>
					</Button>
				</div>
			{/if}
		</div>
	{/if}
</aside>

<style>
	.agenda-tracker {
		background-color: white;
		border-right: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
	}
</style>
