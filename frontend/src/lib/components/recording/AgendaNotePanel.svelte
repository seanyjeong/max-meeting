<script lang="ts">
	import { onDestroy } from 'svelte';
	import type { Agenda, AgendaQuestion, TimeSegment } from '$lib/stores/meeting';

	interface Props {
		agendas: Agenda[];
		currentAgendaIndex: number;
		notes: Map<number, string>;
		recordingTime: number;
		isRecording: boolean;
		onAgendaChange: (prevAgendaId: number | null, newAgendaId: number, currentTime: number) => void;
		onChildAgendaChange?: (prevId: number | null, childId: number, currentTime: number) => void;
		onQuestionToggle: (questionId: number, answered: boolean) => void;
		onNoteChange: (agendaId: number, content: string) => void;
	}

	let {
		agendas,
		currentAgendaIndex = $bindable(),
		notes,
		recordingTime,
		isRecording,
		onAgendaChange,
		onChildAgendaChange,
		onQuestionToggle,
		onNoteChange
	}: Props = $props();

	let noteDebounceTimers = new Map<number, ReturnType<typeof setTimeout>>();
	let listCollapsed = $state(false);
	let activeChildId = $state<number | null>(null);

	// Current agenda
	let currentAgenda = $derived(agendas[currentAgendaIndex]);
	let noteContent = $derived(currentAgenda ? (notes.get(activeChildId || currentAgenda.id) || '') : '');
	let activeItem = $derived(
		activeChildId && currentAgenda?.children
			? currentAgenda.children.find(c => c.id === activeChildId) || currentAgenda
			: currentAgenda
	);
	let answeredCount = $derived(activeItem ? activeItem.questions.filter(q => q.answered).length : 0);
	let totalQuestions = $derived(activeItem ? activeItem.questions.length : 0);

	// Cleanup on destroy
	onDestroy(() => {
		noteDebounceTimers.forEach((timer) => clearTimeout(timer));
		noteDebounceTimers.clear();
	});

	// Helper functions
	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}

	function getStatusIcon(agenda: Agenda, index: number): string {
		if (index === currentAgendaIndex) return '▶';
		if (agenda.status === 'completed') return '✓';
		if (hasMultipleSegments(agenda)) return '↺';
		if (agenda.time_segments?.length || agenda.started_at_seconds !== null) return '●';
		return '○';
	}

	function getStatusColor(agenda: Agenda, index: number): string {
		if (index === currentAgendaIndex) return 'text-blue-600';
		if (agenda.status === 'completed') return 'text-green-600';
		if (hasMultipleSegments(agenda)) return 'text-purple-600';
		return 'text-gray-400';
	}

	function hasMultipleSegments(agenda: Agenda): boolean {
		return (agenda.time_segments?.length ?? 0) > 1;
	}

	function formatAgendaTime(agenda: Agenda): string {
		if (agenda.time_segments?.length) {
			const time = formatTime(agenda.time_segments[0].start);
			if (agenda.time_segments.length > 1) {
				return `${time} +${agenda.time_segments.length - 1}`;
			}
			return time;
		}
		if (agenda.started_at_seconds !== null) {
			return formatTime(agenda.started_at_seconds);
		}
		return '—';
	}

	function truncate(text: string, maxLen: number): string {
		if (text.length <= maxLen) return text;
		return text.slice(0, maxLen - 1) + '…';
	}

	function handleQuestionToggle(question: AgendaQuestion) {
		onQuestionToggle(question.id, !question.answered);
	}

	function handleNoteInput(event: Event) {
		if (!currentAgenda) return;
		const target = event.target as HTMLTextAreaElement;
		const content = target.value;
		const agendaId = currentAgenda.id;

		const existingTimer = noteDebounceTimers.get(agendaId);
		if (existingTimer) {
			clearTimeout(existingTimer);
		}

		const timer = setTimeout(() => {
			onNoteChange(agendaId, content);
			noteDebounceTimers.delete(agendaId);
		}, 500);

		noteDebounceTimers.set(agendaId, timer);
	}

	function goToAgenda(index: number) {
		if (index >= 0 && index < agendas.length && index !== currentAgendaIndex) {
			const prevAgenda = agendas[currentAgendaIndex];
			const targetAgenda = agendas[index];

			// 녹음 중일 때만 time_segments 처리
			if (isRecording) {
				onAgendaChange(activeChildId ?? prevAgenda?.id ?? null, targetAgenda.id, recordingTime);
			}

			currentAgendaIndex = index;
			activeChildId = null; // 대안건으로 이동 시 자식안건 선택 해제
		}
	}

	function goToChildAgenda(parentIndex: number, childId: number) {
		const parentAgenda = agendas[parentIndex];

		// 같은 자식안건이면 무시
		if (activeChildId === childId && currentAgendaIndex === parentIndex) return;

		// 녹음 중일 때만 time_segments 처리
		if (isRecording && onChildAgendaChange) {
			const prevId = activeChildId ?? agendas[currentAgendaIndex]?.id ?? null;
			onChildAgendaChange(prevId, childId, recordingTime);
		}

		currentAgendaIndex = parentIndex;
		activeChildId = childId;
	}

	function goToPrevAgenda() {
		if (currentAgendaIndex > 0) {
			goToAgenda(currentAgendaIndex - 1);
		}
	}

	function goToNextAgenda() {
		if (currentAgendaIndex < agendas.length - 1) {
			goToAgenda(currentAgendaIndex + 1);
		}
	}

	function isChildActive(childId: number): boolean {
		return activeChildId === childId;
	}

	function toggleListCollapse() {
		listCollapsed = !listCollapsed;
	}
</script>

<div class="w-full h-full bg-white flex flex-col overflow-hidden">
	{#if currentAgenda}
		<!-- Agenda List Section -->
		<div class="border-b border-gray-200">
			<button
				type="button"
				onclick={toggleListCollapse}
				class="w-full px-4 py-3 flex items-center justify-between bg-gradient-to-r from-blue-50 to-white hover:from-blue-100 transition-colors"
			>
				<span class="text-sm font-semibold text-blue-700 flex items-center gap-2">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
					</svg>
					안건 목록
					<span class="text-blue-500 font-normal">({currentAgendaIndex + 1}/{agendas.length})</span>
				</span>
				<svg
					class="w-5 h-5 text-gray-500 transition-transform duration-200 {listCollapsed ? '' : 'rotate-180'}"
					fill="none" stroke="currentColor" viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
				</svg>
			</button>

			{#if !listCollapsed}
				<div class="max-h-[220px] overflow-y-auto border-t border-gray-100">
					{#each agendas as agenda, index (agenda.id)}
						<!-- 대안건 -->
						<button
							type="button"
							onclick={() => goToAgenda(index)}
							class="w-full h-[48px] px-4 flex items-center gap-3 text-left transition-colors
								{index === currentAgendaIndex && !activeChildId
									? 'bg-blue-50 border-l-4 border-blue-600'
									: index === currentAgendaIndex
										? 'bg-blue-50/50 border-l-4 border-blue-300'
										: 'hover:bg-gray-50 border-l-4 border-transparent'}"
						>
							<span class="w-5 text-center font-medium {getStatusColor(agenda, index)}">
								{getStatusIcon(agenda, index)}
							</span>
							<span class="flex-1 text-sm truncate {index === currentAgendaIndex && !activeChildId ? 'font-semibold text-blue-900' : 'text-gray-700'}">
								{agenda.order_num}. {truncate(agenda.title, 16)}
								{#if agenda.children && agenda.children.length > 0}
									<span class="text-gray-400 text-xs">+{agenda.children.length}</span>
								{/if}
							</span>
							<span class="text-xs text-gray-400 tabular-nums w-14 text-right">
								{formatAgendaTime(agenda)}
							</span>
						</button>

						<!-- 자식안건들 (현재 대안건이 선택된 경우에만 표시) -->
						{#if index === currentAgendaIndex && agenda.children && agenda.children.length > 0}
							{#each agenda.children as child, childIdx (child.id)}
								<button
									type="button"
									onclick={() => goToChildAgenda(index, child.id)}
									class="w-full h-[40px] pl-10 pr-4 flex items-center gap-2 text-left transition-colors
										{isChildActive(child.id)
											? 'bg-purple-50 border-l-4 border-purple-500'
											: 'hover:bg-gray-50 border-l-4 border-transparent'}"
								>
									<span class="text-xs text-gray-400">{agenda.order_num}.{childIdx + 1}</span>
									<span class="flex-1 text-sm truncate {isChildActive(child.id) ? 'font-medium text-purple-800' : 'text-gray-600'}">
										{truncate(child.title, 14)}
									</span>
									{#if child.time_segments?.length}
										<span class="text-xs text-purple-400">●</span>
									{/if}
								</button>
								<!-- 하하위 안건들 (3레벨) -->
								{#if child.children && child.children.length > 0}
									{#each child.children as grandchild, grandchildIdx (grandchild.id)}
										<button
											type="button"
											onclick={() => goToChildAgenda(index, grandchild.id)}
											class="w-full h-[36px] pl-14 pr-4 flex items-center gap-2 text-left transition-colors
												{isChildActive(grandchild.id)
													? 'bg-pink-50 border-l-4 border-pink-500'
													: 'hover:bg-gray-50 border-l-4 border-transparent'}"
										>
											<span class="text-xs text-gray-400">{agenda.order_num}.{childIdx + 1}.{grandchildIdx + 1}</span>
											<span class="flex-1 text-xs truncate {isChildActive(grandchild.id) ? 'font-medium text-pink-800' : 'text-gray-500'}">
												{truncate(grandchild.title, 12)}
											</span>
											{#if grandchild.time_segments?.length}
												<span class="text-xs text-pink-400">●</span>
											{/if}
										</button>
									{/each}
								{/if}
							{/each}
						{/if}
					{/each}
				</div>
			{/if}
		</div>

		<!-- Scrollable content area -->
		<div class="flex-1 overflow-y-auto">
			<div class="p-4 space-y-4">
				<!-- Current Item Header (대안건 또는 자식안건) -->
				<div class="{activeChildId ? 'bg-purple-50 border-purple-100' : 'bg-blue-50 border-blue-100'} rounded-xl p-4 border">
					<div class="flex items-start justify-between gap-2">
						<div class="flex-1">
							{#if activeChildId && activeItem !== currentAgenda}
								<!-- 자식안건 선택됨 -->
								<p class="text-xs text-purple-600 mb-1">
									{currentAgenda.order_num}. {currentAgenda.title}
								</p>
								<h2 class="text-lg font-bold text-gray-900 leading-tight">
									↳ {activeItem.title}
								</h2>
							{:else}
								<!-- 대안건 선택됨 -->
								<h2 class="text-lg font-bold text-gray-900 leading-tight">
									{currentAgenda.order_num}. {currentAgenda.title}
								</h2>
							{/if}
						</div>
						{#if activeItem.status === 'in_progress'}
							<span class="flex-shrink-0 px-2.5 py-1 text-xs font-semibold {activeChildId ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'} rounded-full">
								진행중
							</span>
						{:else if activeItem.status === 'completed'}
							<span class="flex-shrink-0 px-2.5 py-1 text-xs font-semibold bg-green-100 text-green-700 rounded-full">
								완료
							</span>
						{/if}
					</div>
					{#if activeItem.time_segments?.length}
						<p class="mt-2 text-xs {activeChildId ? 'text-purple-600' : 'text-blue-600'}">
							⏱ {formatAgendaTime(activeItem)}
							{#if hasMultipleSegments(activeItem)}
								<span class="text-purple-600">(재방문 {activeItem.time_segments.length - 1}회)</span>
							{/if}
						</p>
					{/if}
				</div>

				<!-- Description -->
				{#if activeItem.description}
					<div class="bg-gray-50 rounded-xl p-4 border border-gray-100">
						<h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
							상세 내용
						</h3>
						<p class="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
							{activeItem.description}
						</p>
					</div>
				{/if}

				<!-- Children (Sub-topics) - 자식안건이 선택되지 않은 경우에만 표시 -->
				{#if !activeChildId && currentAgenda.children && currentAgenda.children.length > 0}
					<div class="bg-blue-50 rounded-xl p-4 border border-blue-100">
						<h3 class="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-3">
							하위 안건 (클릭하여 선택)
						</h3>
						<div class="space-y-2">
							{#each currentAgenda.children as child, idx (child.id)}
								<button
									type="button"
									onclick={() => goToChildAgenda(currentAgendaIndex, child.id)}
									class="w-full flex items-center gap-2 p-2 rounded-lg hover:bg-blue-100 transition-colors text-left"
								>
									<span class="text-blue-500 font-medium text-sm">{currentAgenda.order_num}.{idx + 1}</span>
									<span class="text-sm font-medium text-gray-800 flex-1">{child.title}</span>
									{#if child.questions?.length}
										<span class="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
											질문 {child.questions.length}
										</span>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Questions Checklist (activeItem 기준) -->
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
							{#each activeItem.questions as question (question.id)}
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
							rows="4"
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
		<div class="flex-1 flex items-center justify-center text-gray-500">
			<p>안건이 없습니다</p>
		</div>
	{/if}
</div>

<style>
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

	* {
		-webkit-font-smoothing: antialiased;
	}
</style>
