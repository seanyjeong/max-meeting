<script lang="ts">
	/**
	 * RecordingGuard - Prevents accidental navigation during recording
	 *
	 * - Shows confirmation dialog on navigation attempt
	 * - Warns on browser close/refresh (beforeunload)
	 * - Warning for short recordings (<5 minutes)
	 */
	import { onMount, onDestroy } from 'svelte';
	import { beforeNavigate } from '$app/navigation';
	import { isRecording, isPaused, recordingTime } from '$lib/stores/recording';
	import Modal from '$lib/components/Modal.svelte';
	import Button from '$lib/components/Button.svelte';

	interface Props {
		minimumDuration?: number; // seconds - warn if stopping before this
		onConfirmLeave?: () => void;
		onConfirmStop?: () => void;
	}

	let { minimumDuration = 300, onConfirmLeave, onConfirmStop }: Props = $props();

	let showLeaveModal = $state(false);
	let showStopModal = $state(false);
	let pendingNavigation: (() => void) | null = null;

	// Handle beforeunload (browser close/refresh)
	function handleBeforeUnload(e: BeforeUnloadEvent) {
		if ($isRecording || $isPaused) {
			e.preventDefault();
			// Modern browsers require returnValue to be set
			e.returnValue = '녹음이 진행 중입니다. 페이지를 나가시겠습니까?';
			return e.returnValue;
		}
	}

	onMount(() => {
		window.addEventListener('beforeunload', handleBeforeUnload);
	});

	onDestroy(() => {
		window.removeEventListener('beforeunload', handleBeforeUnload);
	});

	// Handle SvelteKit navigation
	beforeNavigate(({ cancel, to }) => {
		if ($isRecording || $isPaused) {
			cancel();
			pendingNavigation = () => {
				// This will be called if user confirms leaving
				if (to?.url) {
					window.location.href = to.url.href;
				}
			};
			showLeaveModal = true;
		}
	});

	function handleConfirmLeave() {
		showLeaveModal = false;
		onConfirmLeave?.();
		if (pendingNavigation) {
			pendingNavigation();
			pendingNavigation = null;
		}
	}

	function handleCancelLeave() {
		showLeaveModal = false;
		pendingNavigation = null;
	}

	// Check if recording is too short
	export function checkMinimumDuration(): boolean {
		if ($recordingTime < minimumDuration) {
			showStopModal = true;
			return false;
		}
		return true;
	}

	function handleConfirmStop() {
		showStopModal = false;
		onConfirmStop?.();
	}

	function handleCancelStop() {
		showStopModal = false;
	}
</script>

<!-- Leave Confirmation Modal -->
<Modal bind:open={showLeaveModal} title="녹음 진행 중" size="sm">
	<div class="text-gray-600">
		<p class="mb-4">녹음이 진행 중입니다. 페이지를 떠나면 녹음이 중단됩니다.</p>
		<p class="text-sm text-gray-500">저장되지 않은 녹음 데이터는 복구할 수 있습니다.</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleCancelLeave}>계속 녹음</Button>
			<Button variant="danger" onclick={handleConfirmLeave}>페이지 나가기</Button>
		</div>
	{/snippet}
</Modal>

<!-- Short Recording Confirmation Modal -->
<Modal bind:open={showStopModal} title="녹음 종료 확인" size="sm">
	<div class="text-gray-600">
		<p class="mb-4">녹음 시간이 {Math.floor(minimumDuration / 60)}분 미만입니다.</p>
		<p>정말로 녹음을 종료하시겠습니까?</p>
	</div>

	{#snippet footer()}
		<div class="flex justify-end gap-3">
			<Button variant="secondary" onclick={handleCancelStop}>계속 녹음</Button>
			<Button variant="danger" onclick={handleConfirmStop}>녹음 종료</Button>
		</div>
	{/snippet}
</Modal>
