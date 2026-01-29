<script lang="ts">
	/**
	 * Recording Page - Integrated recording interface
	 *
	 * Layout:
	 * - CompactRecordingBar (fixed top, 56px)
	 * - Breadcrumb
	 * - Split: AgendaNotePanel (25%) | NoteSketchArea (75%)
	 *
	 * Features:
	 * - Battery warning
	 * - Recording guard (navigation protection)
	 * - Agenda tracking with notes
	 * - Text/Sketch tabs per agenda
	 */
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import {
		recordingStore,
		visualizationStore,
		isRecording,
		isPaused,
		batteryWarning,
		formatTime,
		recordingTime
	} from '$lib/stores/recording';
	import { notesStore } from '$lib/stores/notes';
	import { getBatteryStatus, onBatteryStatusChange } from '$lib/utils/audio';
	import { hasUnsavedRecordings, combineRecordingChunks } from '$lib/utils/indexeddb';
	import { api } from '$lib/api';
	import { toast } from '$lib/stores/toast';
	import { Breadcrumb, Button, Modal, LoadingSpinner } from '$lib/components';
	import RecordingGuard from '$lib/components/recording/RecordingGuard.svelte';
	import CompactRecordingBar from '$lib/components/recording/CompactRecordingBar.svelte';
	import AgendaNotePanel from '$lib/components/recording/AgendaNotePanel.svelte';
	import NoteSketchArea from '$lib/components/recording/NoteSketchArea.svelte';
	import type { MeetingDetail, Agenda } from '$lib/stores/meeting';

	let meetingId = $derived(parseInt($page.params.id || '', 10));

	let meeting = $state<MeetingDetail | null>(null);
	let currentAgendaIndex = $state(0);

	// New state variables for notes/sketch
	let activeTab = $state<'text' | 'sketch'>('text');
	let agendaNotes = $state<Map<number, string>>(new Map());
	let agendaSketches = $state<Map<number, any>>(new Map());

	// Recovery modal
	let showRecoveryModal = $state(false);
	let hasRecoveryData = $state(false);

	// Preview modal
	let showPreviewModal = $state(false);
	let previewAudioUrl = $state<string | null>(null);
	let audioBlob = $state<Blob | null>(null);

	// Upload state
	let isUploading = $state(false);
	let uploadProgress = $state(0);

	// Guard reference
	let recordingGuard: RecordingGuard;

	// Battery monitoring
	let unsubscribeBattery: (() => void) | null = null;

	const breadcrumbItems = $derived([
		{ label: 'Home', href: '/' },
		{ label: '회의', href: '/meetings' },
		{ label: meeting?.title || '회의', href: `/meetings/${meetingId}` },
		{ label: '녹음', href: `/meetings/${meetingId}/record` }
	]);

	onMount(async () => {
		// Fetch meeting details
		try {
			const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
			meeting = response;
			currentMeeting.set(response);

			// Find current agenda (first non-completed)
			const idx = meeting.agendas.findIndex((a) => a.status !== 'completed');
			currentAgendaIndex = idx >= 0 ? idx : 0;

			// Load notes for this meeting
			await notesStore.loadNotes(meetingId);
			const notesState = get(notesStore);
			agendaNotes = new Map([...notesState.notes].map(([id, note]) => [id, note.content]));
		} catch {
			goto('/meetings');
			return;
		}

		// Check for recovery data
		hasRecoveryData = await hasUnsavedRecordings(meetingId);
		if (hasRecoveryData) {
			showRecoveryModal = true;
		}

		// Initialize battery monitoring
		const status = await getBatteryStatus();
		if (status) {
			recordingStore.updateBatteryStatus(status.level, status.charging);
		}
		unsubscribeBattery = await onBatteryStatusChange((status) => {
			recordingStore.updateBatteryStatus(status.level, status.charging);
		});
	});

	onDestroy(async () => {
		unsubscribeBattery?.();
		recordingStore.reset();
		visualizationStore.stop();
		if (previewAudioUrl) {
			URL.revokeObjectURL(previewAudioUrl);
		}

		// Save notes on destroy
		await notesStore.forceSave();
		notesStore.cleanup();
	});

	// New handlers for notes/sketch
	function handleNoteChange(agendaId: number, content: string) {
		notesStore.saveNote(agendaId, content);
		agendaNotes = new Map(agendaNotes.set(agendaId, content));
	}

	function handleSketchChange(snapshot: any) {
		if (meeting && meeting.agendas[currentAgendaIndex]) {
			const agendaId = meeting.agendas[currentAgendaIndex].id;
			agendaSketches = new Map(agendaSketches.set(agendaId, snapshot));
		}
	}

	function handleTabChange(tab: 'text' | 'sketch') {
		activeTab = tab;
	}

	async function handleStartRecording() {
		const success = await recordingStore.start(meetingId);
		if (success) {
			const mediaRecorder = recordingStore.getMediaRecorder();
			if (mediaRecorder) {
				visualizationStore.start(mediaRecorder);
			}

			// Mark first agenda as in_progress
			if (meeting && meeting.agendas.length > 0) {
				const agenda = meeting.agendas[currentAgendaIndex];
				await updateAgendaTimestamp(agenda.id, 0);
			}
		}
	}

	function handlePauseRecording() {
		recordingStore.pause();
	}

	function handleResumeRecording() {
		recordingStore.resume();
	}

	async function handleStopRecording() {
		// Check minimum duration
		if (recordingGuard && !recordingGuard.checkMinimumDuration()) {
			return;
		}

		visualizationStore.stop();
		const blob = await recordingStore.stop();

		if (blob) {
			audioBlob = blob;
			previewAudioUrl = URL.createObjectURL(blob);
			showPreviewModal = true;
		}
	}

	function handleConfirmStop() {
		// Called from RecordingGuard when user confirms short recording stop
		handleActualStop();
	}

	async function handleActualStop() {
		visualizationStore.stop();
		const blob = await recordingStore.stop();

		if (blob) {
			audioBlob = blob;
			previewAudioUrl = URL.createObjectURL(blob);
			showPreviewModal = true;
		}
	}

	async function handleConfirmRecording() {
		if (!audioBlob) return;

		isUploading = true;
		uploadProgress = 0;

		try {
			const result = await recordingStore.uploadRecording(
				meetingId,
				audioBlob,
				(progress) => {
					uploadProgress = progress;
				}
			);

			if (result.success) {
				// Clear saved chunks after successful upload
				await recordingStore.clearSavedChunks(meetingId);

				showPreviewModal = false;
				if (previewAudioUrl) {
					URL.revokeObjectURL(previewAudioUrl);
					previewAudioUrl = null;
				}

				goto(`/meetings/${meetingId}/results`);
			} else {
				console.error('Upload failed');
				toast.error('업로드에 실패했습니다. 다시 시도해주세요.');
			}
		} finally {
			isUploading = false;
		}
	}

	function handleDiscardRecording() {
		showPreviewModal = false;
		if (previewAudioUrl) {
			URL.revokeObjectURL(previewAudioUrl);
			previewAudioUrl = null;
		}
		audioBlob = null;
		recordingStore.reset();
	}

	async function handleRecoverRecording() {
		const blob = await combineRecordingChunks(meetingId);
		if (blob) {
			audioBlob = blob;
			previewAudioUrl = URL.createObjectURL(blob);
			showRecoveryModal = false;
			showPreviewModal = true;
		}
	}

	async function handleDiscardRecovery() {
		await recordingStore.clearSavedChunks(meetingId);
		showRecoveryModal = false;
		hasRecoveryData = false;
	}

	async function handleNextAgenda(agendaId: number, timestamp: number) {
		await updateAgendaTimestamp(agendaId, timestamp);

		// Mark previous as completed, current as in_progress
		if (meeting && currentAgendaIndex < meeting.agendas.length - 1) {
			currentAgendaIndex++;
		}
	}

	async function updateAgendaTimestamp(agendaId: number, timestamp: number) {
		try {
			await api.patch(`/agendas/${agendaId}`, {
				started_at_seconds: timestamp,
				status: 'in_progress'
			});

			// Update local state
			if (meeting) {
				meeting = {
					...meeting,
					agendas: meeting.agendas.map((a) =>
						a.id === agendaId
							? { ...a, started_at_seconds: timestamp, status: 'in_progress' as const }
							: a
					)
				};
			}
		} catch (error) {
			console.error('Failed to update agenda timestamp:', error);
		}
	}

	async function handleQuestionToggle(questionId: number, answered: boolean) {
		try {
			await api.patch(`/questions/${questionId}`, { answered });

			// Update local state
			if (meeting) {
				meeting = {
					...meeting,
					agendas: meeting.agendas.map((a) => ({
						...a,
						questions: a.questions.map((q) => (q.id === questionId ? { ...q, answered } : q))
					}))
				};
			}
		} catch (error) {
			console.error('Failed to toggle question:', error);
		}
	}

	function handleLeaveRecording() {
		// Called when user confirms leaving during recording
		recordingStore.reset();
		visualizationStore.stop();
	}
</script>

<svelte:head>
	<title>녹음 - {meeting?.title || '회의'} - MAX Meeting</title>
</svelte:head>

<RecordingGuard
	bind:this={recordingGuard}
	onConfirmLeave={handleLeaveRecording}
	onConfirmStop={handleConfirmStop}
/>

{#if !meeting}
	<div class="flex justify-center py-12 pt-20">
		<LoadingSpinner size="lg" />
	</div>
{:else}
	<!-- Compact Recording Bar -->
	<CompactRecordingBar
		isRecording={$isRecording}
		isPaused={$isPaused}
		recordingTime={$recordingTime}
		currentAgenda={meeting.agendas[currentAgendaIndex]?.title || ''}
		visualizationData={$visualizationStore.analyserData}
		onStart={handleStartRecording}
		onStop={handleStopRecording}
		onPause={handlePauseRecording}
		onResume={handleResumeRecording}
	/>

	<!-- Main content area (below nav + recording bar) -->
	<div class="pt-[120px]">
		<!-- Breadcrumb -->
		<div class="px-4 py-3 border-b bg-white">
			<div class="flex items-center justify-between">
				<Breadcrumb items={breadcrumbItems} />

				<!-- Battery warning -->
				{#if $batteryWarning}
					<div
						class="flex items-center gap-2 px-3 py-1 rounded-full {$batteryWarning === 'critical'
							? 'bg-red-100 text-red-700'
							: 'bg-yellow-100 text-yellow-700'}"
						role="alert"
					>
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
							<path
								d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 1.34-.6 1.34-1.33V5.33C17 4.6 16.4 4 15.67 4z"
							/>
						</svg>
						<span class="text-sm font-medium">
							{$batteryWarning === 'critical' ? '배터리 부족!' : '배터리 낮음'}
						</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Split layout (100vh - nav 64px - bar 56px - breadcrumb 52px) -->
		<div class="flex h-[calc(100vh-172px)]">
			<!-- Left: Agenda Panel (25%) -->
			<div class="w-1/4 min-w-64 max-w-80 border-r">
				<AgendaNotePanel
					agendas={meeting.agendas}
					bind:currentAgendaIndex
					notes={agendaNotes}
					recordingTime={$recordingTime}
					onNextAgenda={handleNextAgenda}
					onQuestionToggle={handleQuestionToggle}
					onNoteChange={handleNoteChange}
				/>
			</div>

			<!-- Right: Note/Sketch Area (75%) -->
			<div class="flex-1">
				<NoteSketchArea
					bind:activeTab
					textContent={agendaNotes.get(meeting.agendas[currentAgendaIndex]?.id) || ''}
					sketchSnapshot={agendaSketches.get(meeting.agendas[currentAgendaIndex]?.id)}
					onTabChange={handleTabChange}
					onTextChange={(content) => handleNoteChange(meeting.agendas[currentAgendaIndex].id, content)}
					onSketchChange={handleSketchChange}
				/>
			</div>
		</div>
	</div>
{/if}

<!-- Recovery Modal -->
<Modal bind:open={showRecoveryModal} title="미저장 녹음 발견" size="sm">
	<div class="text-gray-600">
		<p class="mb-4">이전에 저장되지 않은 녹음 데이터가 있습니다.</p>
		<p>복구하시겠습니까?</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleDiscardRecovery}>삭제</Button>
			<Button variant="primary" onclick={handleRecoverRecording}>복구</Button>
		</div>
	{/snippet}
</Modal>

<!-- Preview Modal -->
<Modal bind:open={showPreviewModal} title="녹음 확인" size="md">
	<div class="space-y-4">
		<p class="text-gray-600">녹음이 완료되었습니다. 10초간 미리 들어보세요.</p>

		{#if previewAudioUrl}
			<audio controls class="w-full" src={previewAudioUrl}>
				<track kind="captions" />
				Your browser does not support the audio element.
			</audio>
		{/if}

		<div class="text-sm text-gray-500">
			녹음 시간: {formatTime($recordingTime)}
		</div>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleDiscardRecording} disabled={isUploading}>
				다시 녹음
			</Button>
			<Button variant="primary" onclick={handleConfirmRecording} disabled={isUploading}>
				{#if isUploading}
					업로드 중... {Math.round(uploadProgress)}%
				{:else}
					업로드
				{/if}
			</Button>
		</div>
	{/snippet}
</Modal>
