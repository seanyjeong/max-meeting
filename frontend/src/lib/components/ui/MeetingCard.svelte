<script lang="ts">
	import { Calendar, Clock, Users, ChevronRight } from 'lucide-svelte';
	import type { Meeting } from '$lib/stores/meeting';
	import { formatDate } from '$lib/utils/format';

	interface Props {
		meeting: Meeting;
		isSelected?: boolean;
		compact?: boolean;
		onclick?: () => void;
	}

	let { meeting, isSelected = false, compact = false, onclick }: Props = $props();

	function formatTimeLocal(dateStr: string | null): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleTimeString('ko-KR', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusBadge(status: Meeting['status']) {
		switch (status) {
			case 'draft':
				return { label: '작성 중', class: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300' };
			case 'in_progress':
				return { label: '진행 중', class: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' };
			case 'completed':
				return { label: '완료', class: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' };
			default:
				return { label: status, class: 'bg-gray-100 text-gray-700' };
		}
	}

	const status = $derived(getStatusBadge(meeting.status));
</script>

<button
	type="button"
	{onclick}
	class="w-full text-left p-4 rounded-xl border transition-all duration-normal
		{isSelected
			? 'bg-primary-50 border-primary-300 dark:bg-primary-900/20 dark:border-primary-700'
			: 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-soft dark:bg-surface dark:border-surface-light dark:hover:border-text-subtle'}
		{compact ? 'py-3' : 'py-4'}
		active:scale-[0.99] touch-target"
>
	<div class="flex items-start justify-between gap-3">
		<div class="flex-1 min-w-0">
			<!-- Title -->
			<h3 class="font-medium text-gray-900 dark:text-text truncate {compact ? 'text-sm' : 'text-base'}">
				{meeting.title}
			</h3>

			<!-- Meeting Type -->
			{#if meeting.meeting_type?.name}
				<p class="text-xs text-gray-500 dark:text-text-muted mt-0.5">
					{meeting.meeting_type.name}
				</p>
			{/if}

			<!-- Meta info -->
			<div class="flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-text-subtle">
				{#if meeting.scheduled_at}
					<span class="inline-flex items-center gap-1">
						<Calendar class="w-3.5 h-3.5" />
						{formatDate(meeting.scheduled_at)}
					</span>
					<span class="inline-flex items-center gap-1">
						<Clock class="w-3.5 h-3.5" />
						{formatTimeLocal(meeting.scheduled_at)}
					</span>
				{/if}
			</div>
		</div>

		<div class="flex flex-col items-end gap-2">
			<!-- Status badge -->
			<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {status.class}">
				{status.label}
			</span>

			<!-- Arrow indicator when selected -->
			{#if isSelected}
				<ChevronRight class="w-4 h-4 text-primary-500" />
			{/if}
		</div>
	</div>
</button>
