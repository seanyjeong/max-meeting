<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	interface Attendee {
		id: number;
		name: string;
		role?: string | null;
		organization?: string | null;
	}

	export let speakers: string[] = []; // ["SPEAKER_00", "SPEAKER_01"]
	export let attendees: Attendee[] = [];
	export let mapping: Record<string, number> = {}; // {"SPEAKER_00": 1}

	const dispatch = createEventDispatcher<{
		change: Record<string, number>;
	}>();

	let draggedSpeaker: string | null = null;

	function handleDragStart(speaker: string) {
		draggedSpeaker = speaker;
	}

	function handleDragEnd() {
		draggedSpeaker = null;
	}

	function handleDrop(attendeeId: number) {
		if (draggedSpeaker) {
			mapping = { ...mapping, [draggedSpeaker]: attendeeId };
			dispatch('change', mapping);
		}
		draggedSpeaker = null;
	}

	function removeMapping(speaker: string) {
		const { [speaker]: _, ...rest } = mapping;
		mapping = rest;
		dispatch('change', mapping);
	}

	function getMappedAttendeeName(speaker: string): string | undefined {
		const attendeeId = mapping[speaker];
		if (!attendeeId) return undefined;
		return attendees.find((a) => a.id === attendeeId)?.name;
	}

	function getUnmappedAttendees(): Attendee[] {
		const mappedIds = new Set(Object.values(mapping));
		return attendees.filter((a) => !mappedIds.has(a.id));
	}

	$: unmappedAttendees = getUnmappedAttendees();
</script>

<div class="bg-white border border-gray-200 rounded-lg p-4">
	<h3 class="text-lg font-medium text-gray-900 mb-4">
		화자 매핑
		<span class="text-sm font-normal text-gray-500 ml-2">
			(화자를 참석자에게 드래그하여 매핑)
		</span>
	</h3>

	{#if speakers.length === 0}
		<p class="text-gray-500 text-sm">감지된 화자가 없습니다.</p>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
			<!-- Left: Speakers -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 mb-3">감지된 화자</h4>
				<div class="space-y-2">
					{#each speakers as speaker (speaker)}
						{@const mappedName = getMappedAttendeeName(speaker)}
						<div
							draggable="true"
							ondragstart={() => handleDragStart(speaker)}
							ondragend={handleDragEnd}
							class="flex items-center justify-between p-3 bg-blue-50 border border-blue-200 rounded-lg cursor-move hover:bg-blue-100 transition-colors {draggedSpeaker === speaker ? 'opacity-50 ring-2 ring-blue-400' : ''}"
						>
							<div class="flex items-center gap-2">
								<span class="w-8 h-8 flex items-center justify-center bg-blue-200 text-blue-800 rounded-full text-sm font-medium">
									{speaker.replace('SPEAKER_', '')}
								</span>
								<span class="text-gray-900">{speaker}</span>
							</div>

							{#if mappedName}
								<div class="flex items-center gap-2">
									<span class="text-sm text-green-600 font-medium">
										{mappedName}
									</span>
									<button
										type="button"
										onclick={() => removeMapping(speaker)}
										class="p-1 text-gray-400 hover:text-red-500 transition-colors"
										title="매핑 해제"
									>
										<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								</div>
							{:else}
								<span class="text-xs text-gray-400">매핑되지 않음</span>
							{/if}
						</div>
					{/each}
				</div>
			</div>

			<!-- Right: Attendees -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 mb-3">
					참석자
					{#if unmappedAttendees.length < attendees.length}
						<span class="text-gray-400 font-normal">
							({attendees.length - unmappedAttendees.length}/{attendees.length} 매핑됨)
						</span>
					{/if}
				</h4>

				{#if attendees.length === 0}
					<p class="text-gray-500 text-sm">참석자가 없습니다.</p>
				{:else}
					<div class="space-y-2">
						{#each attendees as attendee (attendee.id)}
							{@const isMapped = Object.values(mapping).includes(attendee.id)}
							<div
								ondragover={(e) => e.preventDefault()}
								ondrop={() => handleDrop(attendee.id)}
								class="p-3 border rounded-lg transition-all {isMapped
									? 'bg-green-50 border-green-200'
									: 'bg-gray-50 border-gray-200 hover:border-blue-300 hover:bg-blue-50'}"
							>
								<div class="flex items-center justify-between">
									<div>
										<span class="font-medium text-gray-900">{attendee.name}</span>
										{#if attendee.organization || attendee.role}
											<p class="text-xs text-gray-500">
												{attendee.organization || ''}{attendee.organization && attendee.role ? ' - ' : ''}{attendee.role || ''}
											</p>
										{/if}
									</div>
									{#if isMapped}
										<span class="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
											매핑됨
										</span>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- Summary -->
		{#if Object.keys(mapping).length > 0}
			<div class="mt-4 pt-4 border-t border-gray-200">
				<h4 class="text-sm font-medium text-gray-700 mb-2">현재 매핑</h4>
				<div class="flex flex-wrap gap-2">
					{#each Object.entries(mapping) as [speaker, attendeeId] (speaker)}
						{@const attendee = attendees.find((a) => a.id === attendeeId)}
						{#if attendee}
							<span class="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">
								<span class="font-medium">{speaker.replace('SPEAKER_', 'S')}</span>
								<span class="text-gray-400">=</span>
								<span>{attendee.name}</span>
							</span>
						{/if}
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>
