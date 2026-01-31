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
	import type { MeetingDetail, Agenda, TimeSegment } from '$lib/stores/meeting';

	let meetingId = $derived(parseInt($page.params.id || '', 10));

	let meeting = $state<MeetingDetail | null>(null);
	let currentAgendaIndex = $state(0);

	// Time segments tracking
	let activeAgendaId = $state<number | null>(null);

	// New state variables for notes/sketch
	let activeTab = $state<'memo' | 'pen' | 'task'>('memo');
	let agendaNotes = $state<Map<number, string>>(new Map());
	let agendaSketches = $state<Map<number, any>>(new Map());
	let savedSketchAgendas = $state<Set<number>>(new Set()); // Track which sketches have been saved

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

		// Save notes and sketches on destroy
		await notesStore.forceSave();
		await saveAllSketches();
		notesStore.cleanup();
	});

	// New handlers for notes/sketch
	function handleNoteChange(agendaId: number, content: string) {
		// agendaId가 유효한지 확인
		if (!agendaId || typeof agendaId !== 'number' || isNaN(agendaId)) {
			console.warn('[record] handleNoteChange: 유효하지 않은 agendaId:', agendaId);
			return;
		}
		console.log('[record] handleNoteChange: agendaId:', agendaId, '내용 길이:', content.length);
		notesStore.saveNote(agendaId, content);
		agendaNotes = new Map(agendaNotes.set(agendaId, content));
	}

	function handleSketchChange(snapshot: any) {
		if (meeting && meeting.agendas[currentAgendaIndex]) {
			const agendaId = meeting.agendas[currentAgendaIndex].id;
			agendaSketches = new Map(agendaSketches.set(agendaId, snapshot));
			// Mark as unsaved when changed
			savedSketchAgendas.delete(agendaId);
			savedSketchAgendas = new Set(savedSketchAgendas);
		}
	}

	// Save sketch to backend
	async function saveSketchToBackend(agendaId: number): Promise<boolean> {
		const snapshot = agendaSketches.get(agendaId);
		if (!snapshot?.dataUrl || savedSketchAgendas.has(agendaId)) {
			return true; // Nothing to save or already saved
		}

		// Check if sketch has any strokes
		if (!snapshot.strokes || snapshot.strokes.length === 0) {
			return true; // Empty sketch, don't save
		}

		try {
			await api.post(`/meetings/${meetingId}/sketches`, {
				agenda_id: agendaId,
				image_data: snapshot.dataUrl,
				timestamp_seconds: $recordingTime || null
			});
			savedSketchAgendas.add(agendaId);
			savedSketchAgendas = new Set(savedSketchAgendas);
			console.log('[record] Sketch saved for agenda:', agendaId);
			return true;
		} catch (error) {
			console.error('[record] Failed to save sketch:', error);
			return false;
		}
	}

	// Save all unsaved sketches
	async function saveAllSketches(): Promise<void> {
		const promises: Promise<boolean>[] = [];
		for (const [agendaId, snapshot] of agendaSketches.entries()) {
			if (snapshot?.strokes?.length > 0 && !savedSketchAgendas.has(agendaId)) {
				promises.push(saveSketchToBackend(agendaId));
			}
		}
		await Promise.all(promises);
	}

	function handleTabChange(tab: 'memo' | 'pen' | 'task') {
		activeTab = tab;
	}

	async function handleStartRecording() {
		const success = await recordingStore.start(meetingId);
		if (success) {
			const mediaRecorder = recordingStore.getMediaRecorder();
			if (mediaRecorder) {
				visualizationStore.start(mediaRecorder);
			}

			// 새 녹음 시작 시 모든 안건의 time_segments 초기화
			if (meeting) {
				for (const agenda of meeting.agendas) {
					if (agenda.time_segments && agenda.time_segments.length > 0) {
						await api.patch(`/agendas/${agenda.id}`, { time_segments: [] });
						updateLocalAgenda(agenda.id, { time_segments: [] });
					}
					// 자식안건도 초기화
					if (agenda.children) {
						for (const child of agenda.children) {
							if (child.time_segments && child.time_segments.length > 0) {
								await api.patch(`/agendas/${child.id}`, { time_segments: [] });
								updateLocalAgenda(child.id, { time_segments: [] });
							}
							// 하하위안건도 초기화
							if (child.children) {
								for (const grandchild of child.children) {
									if (grandchild.time_segments && grandchild.time_segments.length > 0) {
										await api.patch(`/agendas/${grandchild.id}`, { time_segments: [] });
										updateLocalAgenda(grandchild.id, { time_segments: [] });
									}
								}
							}
						}
					}
				}
			}

			// Start first agenda segment
			if (meeting && meeting.agendas.length > 0) {
				const agenda = meeting.agendas[currentAgendaIndex];
				await openSegment(agenda.id, 0);
				activeAgendaId = agenda.id;
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

		// Close current segment before stopping
		if (activeAgendaId !== null) {
			await closeSegment(activeAgendaId, $recordingTime);
			activeAgendaId = null;
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

	// Time segment management
	async function handleAgendaChange(prevAgendaId: number | null, newAgendaId: number, currentTime: number) {
		// Save sketch for previous agenda before switching
		if (prevAgendaId !== null && prevAgendaId !== newAgendaId) {
			await saveSketchToBackend(prevAgendaId);
		}

		// Close previous segment
		if (prevAgendaId !== null && prevAgendaId !== newAgendaId) {
			await closeSegment(prevAgendaId, currentTime);
		}

		// Open new segment
		await openSegment(newAgendaId, currentTime);
		activeAgendaId = newAgendaId;
	}

	// 자식안건 타임스탬프 핸들러
	async function handleChildAgendaChange(prevId: number | null, childId: number, currentTime: number) {
		console.log('[record] handleChildAgendaChange:', { prevId, childId, currentTime });

		// Close previous segment (대안건 또는 자식안건)
		if (prevId !== null && prevId !== childId) {
			console.log('[record] Closing previous segment:', prevId);
			await closeSegment(prevId, currentTime);
		}

		// Open new segment for child
		console.log('[record] Opening new segment for child:', childId);
		await openSegment(childId, currentTime);
		activeAgendaId = childId;
		console.log('[record] activeAgendaId set to:', activeAgendaId);
	}

	// 안건 찾기 (대안건, 자식안건, 하하위안건)
	function findAgendaById(agendaId: number): Agenda | null {
		if (!meeting) return null;

		// 대안건에서 찾기
		const parent = meeting.agendas.find(a => a.id === agendaId);
		if (parent) return parent;

		// 자식안건에서 찾기
		for (const agenda of meeting.agendas) {
			if (agenda.children) {
				const child = agenda.children.find(c => c.id === agendaId);
				if (child) return child;

				// 하하위안건에서 찾기 (3레벨)
				for (const childAgenda of agenda.children) {
					if (childAgenda.children) {
						const grandchild = childAgenda.children.find(gc => gc.id === agendaId);
						if (grandchild) return grandchild;
					}
				}
			}
		}

		return null;
	}

	async function closeSegment(agendaId: number, endTime: number) {
		if (!meeting) return;

		const agenda = findAgendaById(agendaId);
		if (!agenda) return;

		const segments = [...(agenda.time_segments || [])];
		const lastSeg = segments[segments.length - 1];

		if (lastSeg && lastSeg.end === null) {
			lastSeg.end = endTime;

			try {
				await api.patch(`/agendas/${agendaId}`, { time_segments: segments });
				updateLocalAgenda(agendaId, { time_segments: segments });
			} catch (error) {
				console.error('Failed to close segment:', error);
			}
		}
	}

	async function openSegment(agendaId: number, startTime: number) {
		console.log('[record] openSegment called:', { agendaId, startTime });
		if (!meeting) {
			console.log('[record] openSegment: no meeting');
			return;
		}

		const agenda = findAgendaById(agendaId);
		console.log('[record] openSegment: found agenda:', agenda?.title, 'id:', agenda?.id);
		if (!agenda) {
			console.log('[record] openSegment: agenda not found for id:', agendaId);
			return;
		}

		const segments = [...(agenda.time_segments || [])];
		segments.push({ start: startTime, end: null });
		console.log('[record] openSegment: new segments:', segments);

		try {
			console.log('[record] openSegment: calling API PATCH for agenda:', agendaId);
			await api.patch(`/agendas/${agendaId}`, {
				time_segments: segments,
				started_at_seconds: segments[0].start,
				status: 'in_progress'
			});
			updateLocalAgenda(agendaId, {
				time_segments: segments,
				started_at_seconds: segments[0].start,
				status: 'in_progress' as const
			});
			console.log('[record] openSegment: success');
		} catch (error) {
			console.error('Failed to open segment:', error);
		}
	}

	function updateLocalAgenda(agendaId: number, updates: Partial<Agenda>) {
		if (meeting) {
			meeting = {
				...meeting,
				agendas: meeting.agendas.map((a) => {
					// 대안건 업데이트
					if (a.id === agendaId) {
						return { ...a, ...updates };
					}
					// 자식안건 또는 하하위안건 업데이트
					if (a.children) {
						return {
							...a,
							children: a.children.map((c) => {
								if (c.id === agendaId) {
									return { ...c, ...updates };
								}
								// 하하위안건 업데이트 (3레벨)
								if (c.children) {
									return {
										...c,
										children: c.children.map((gc) =>
											gc.id === agendaId ? { ...gc, ...updates } : gc
										)
									};
								}
								return c;
							})
						};
					}
					return a;
				})
			};
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

	async function handleFinishMeeting() {
		console.log('[record] Finishing meeting:', meetingId);

		// Save notes first
		await notesStore.forceSave();
		console.log('[record] Notes saved');

		// Save all sketches
		await saveAllSketches();
		console.log('[record] Sketches saved');

		// Update meeting status to completed
		try {
			const response = await api.patch(`/meetings/${meetingId}`, { status: 'completed' });
			console.log('[record] Meeting finished, response:', response);
			toast.success('회의가 마무리되었습니다. 회의록을 생성합니다...');
			goto(`/meetings/${meetingId}/results`);
		} catch (error) {
			console.error('[record] Failed to finish meeting:', error);
			toast.error('회의 마무리에 실패했습니다.');
		}
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
	<!-- Main content area (below nav) -->
	<div class="pt-16 h-screen flex flex-col">
		<!-- Breadcrumb + Hint -->
		<div class="px-4 py-3 border-b bg-white flex-shrink-0">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<Breadcrumb items={breadcrumbItems} />
					{#if !$isRecording && !$isPaused}
						<span class="text-xs text-gray-400 hidden sm:inline">
							녹음 없이 진행하려면 오른쪽 "회의 마무리" 버튼을 누르세요
						</span>
					{/if}
				</div>

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

		<!-- Recording Bar (inside meeting area, at top) -->
		<div class="flex-shrink-0 border-b">
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
				onFinishMeeting={handleFinishMeeting}
			/>
		</div>

		<!-- Split layout (fills remaining space) -->
		<div class="flex flex-1 min-h-0">
			<!-- Left: Agenda Panel (25%) -->
			<div class="w-1/4 min-w-64 max-w-80 border-r flex flex-col">
				<div class="flex-1 overflow-auto">
					<AgendaNotePanel
						agendas={meeting.agendas}
						bind:currentAgendaIndex
						notes={agendaNotes}
						recordingTime={$recordingTime}
						isRecording={$isRecording}
						onAgendaChange={handleAgendaChange}
						onChildAgendaChange={handleChildAgendaChange}
						onQuestionToggle={handleQuestionToggle}
						onNoteChange={handleNoteChange}
					/>
				</div>
			</div>

			<!-- Right: Note/Sketch Area (75%) -->
			<div class="flex-1 flex flex-col min-h-0">
				<div class="flex-1 min-h-0 overflow-hidden">
					<NoteSketchArea
						bind:activeTab
						textContent={agendaNotes.get(meeting.agendas[currentAgendaIndex]?.id) || ''}
						sketchSnapshot={agendaSketches.get(meeting.agendas[currentAgendaIndex]?.id)}
						{meetingId}
						onTabChange={handleTabChange}
						onTextChange={(content) => {
						const agenda = meeting?.agendas?.[currentAgendaIndex];
						if (agenda?.id) {
							handleNoteChange(agenda.id, content);
						}
					}}
						onSketchChange={handleSketchChange}
					/>
				</div>
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
				회의 재시작
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
