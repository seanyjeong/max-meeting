/**
 * Recording Store - Audio recording state management
 *
 * Handles MediaRecorder state, audio chunks, and recording metadata.
 * Integrates with IndexedDB for crash recovery.
 */
import { writable, derived, get } from 'svelte/store';
import { saveRecordingChunk, getRecordingChunks, clearRecordingChunks } from '$lib/utils/indexeddb';
import { api } from '$lib/api';

export type RecordingState = 'idle' | 'recording' | 'paused' | 'stopped';

interface RecordingStoreState {
	state: RecordingState;
	currentTime: number;
	duration: number;
	meetingId: number | null;
	startedAt: Date | null;
	lastChunkSavedAt: Date | null;
	audioChunks: Blob[];
	error: string | null;
	batteryLevel: number | null;
	batteryCharging: boolean;
}

// Audio visualization state (separate for performance)
interface AudioVisualizationState {
	analyserData: Uint8Array;
	isAnalyserActive: boolean;
}

const CHUNK_SAVE_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

function createRecordingStore() {
	const { subscribe, set, update } = writable<RecordingStoreState>({
		state: 'idle',
		currentTime: 0,
		duration: 0,
		meetingId: null,
		startedAt: null,
		lastChunkSavedAt: null,
		audioChunks: [],
		error: null,
		batteryLevel: null,
		batteryCharging: false
	});

	let mediaRecorder: MediaRecorder | null = null;
	let timerInterval: ReturnType<typeof setInterval> | null = null;
	let chunkSaveInterval: ReturnType<typeof setInterval> | null = null;
	let wakeLock: WakeLockSentinel | null = null;

	const startTimer = () => {
		if (timerInterval) clearInterval(timerInterval);
		timerInterval = setInterval(() => {
			update((state) => ({
				...state,
				currentTime: state.currentTime + 1
			}));
		}, 1000);
	};

	const stopTimer = () => {
		if (timerInterval) {
			clearInterval(timerInterval);
			timerInterval = null;
		}
	};

	const requestWakeLock = async () => {
		try {
			if ('wakeLock' in navigator) {
				wakeLock = await navigator.wakeLock.request('screen');
			}
		} catch {
			// Wake lock not supported or failed, continue without it
		}
	};

	const releaseWakeLock = async () => {
		if (wakeLock) {
			try {
				await wakeLock.release();
			} catch {
				// Ignore errors on release
			}
			wakeLock = null;
		}
	};

	const triggerVibration = (pattern: number | number[]) => {
		if ('vibrate' in navigator) {
			navigator.vibrate(pattern);
		}
	};

	const saveChunksToIndexedDB = async (meetingId: number, chunks: Blob[]) => {
		if (chunks.length === 0) return;

		try {
			const combinedBlob = new Blob(chunks, { type: 'audio/webm' });
			await saveRecordingChunk(meetingId, combinedBlob);
			update((state) => ({ ...state, lastChunkSavedAt: new Date() }));
		} catch {
			// Silently fail - next interval will retry
		}
	};

	const startChunkSaveInterval = (meetingId: number) => {
		if (chunkSaveInterval) clearInterval(chunkSaveInterval);
		chunkSaveInterval = setInterval(async () => {
			const state = get({ subscribe });
			if (state.audioChunks.length > 0) {
				await saveChunksToIndexedDB(meetingId, state.audioChunks);
				// Trigger haptic feedback every 5 minutes
				triggerVibration(100);
			}
		}, CHUNK_SAVE_INTERVAL_MS);
	};

	const stopChunkSaveInterval = () => {
		if (chunkSaveInterval) {
			clearInterval(chunkSaveInterval);
			chunkSaveInterval = null;
		}
	};

	return {
		subscribe,

		async start(meetingId: number): Promise<boolean> {
			try {
				const stream = await navigator.mediaDevices.getUserMedia({
					audio: {
						echoCancellation: true,
						noiseSuppression: true,
						autoGainControl: true
					}
				});

				mediaRecorder = new MediaRecorder(stream, {
					mimeType: 'audio/webm;codecs=opus'
				});

				const chunks: Blob[] = [];

				mediaRecorder.ondataavailable = (event) => {
					if (event.data.size > 0) {
						chunks.push(event.data);
						update((state) => ({
							...state,
							audioChunks: [...state.audioChunks, event.data]
						}));
					}
				};

				mediaRecorder.onerror = () => {
					update((state) => ({
						...state,
						error: 'Recording error occurred'
					}));
				};

				mediaRecorder.start(1000); // Capture in 1 second chunks

				await requestWakeLock();
				startTimer();
				startChunkSaveInterval(meetingId);

				// Vibration feedback on start
				triggerVibration(200);

				update((state) => ({
					...state,
					state: 'recording',
					meetingId,
					startedAt: new Date(),
					currentTime: 0,
					audioChunks: [],
					error: null
				}));

				return true;
			} catch (error) {
				const message =
					error instanceof Error ? error.message : 'Failed to start recording';
				update((state) => ({ ...state, error: message }));
				return false;
			}
		},

		pause(): void {
			if (mediaRecorder && mediaRecorder.state === 'recording') {
				mediaRecorder.pause();
				stopTimer();
				triggerVibration(100);
				update((state) => ({ ...state, state: 'paused' }));
			}
		},

		resume(): void {
			if (mediaRecorder && mediaRecorder.state === 'paused') {
				mediaRecorder.resume();
				startTimer();
				triggerVibration(100);
				update((state) => ({ ...state, state: 'recording' }));
			}
		},

		async stop(): Promise<Blob | null> {
			return new Promise((resolve) => {
				if (!mediaRecorder || mediaRecorder.state === 'inactive') {
					resolve(null);
					return;
				}

				mediaRecorder.onstop = async () => {
					stopTimer();
					stopChunkSaveInterval();
					await releaseWakeLock();

					const state = get({ subscribe });
					const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });

					// Vibration feedback on stop
					triggerVibration([100, 50, 100]);

					update((s) => ({
						...s,
						state: 'stopped',
						duration: s.currentTime
					}));

					// Stop all tracks
					mediaRecorder?.stream.getTracks().forEach((track) => track.stop());
					mediaRecorder = null;

					resolve(audioBlob);
				};

				mediaRecorder.stop();
			});
		},

		async clearSavedChunks(meetingId: number): Promise<void> {
			await clearRecordingChunks(meetingId);
		},

		async getSavedChunks(meetingId: number): Promise<Blob[]> {
			return getRecordingChunks(meetingId);
		},

		getMediaRecorder(): MediaRecorder | null {
			return mediaRecorder;
		},

		updateBatteryStatus(level: number, charging: boolean): void {
			update((state) => ({
				...state,
				batteryLevel: level,
				batteryCharging: charging
			}));
		},

		reset(): void {
			stopTimer();
			stopChunkSaveInterval();
			releaseWakeLock();

			if (mediaRecorder) {
				mediaRecorder.stream.getTracks().forEach((track) => track.stop());
				mediaRecorder = null;
			}

			set({
				state: 'idle',
				currentTime: 0,
				duration: 0,
				meetingId: null,
				startedAt: null,
				lastChunkSavedAt: null,
				audioChunks: [],
				error: null,
				batteryLevel: null,
				batteryCharging: false
			});
		},

		async uploadRecording(
			meetingId: number,
			audioBlob: Blob,
			onProgress?: (progress: number) => void
		): Promise<{ recordingId: number; success: boolean }> {
			try {
				// Step 1: Create recording entry
				// API returns: { upload_id, recording_id, upload_url, max_chunk_size }
				const createResponse = await api.post<{ recording_id: number; upload_id: string }>(
					`/meetings/${meetingId}/recordings`,
					{}
				);
				const recordingId = createResponse.recording_id;

				// Step 2: Upload in chunks (1MB chunks)
				const CHUNK_SIZE = 1024 * 1024; // 1MB
				const totalSize = audioBlob.size;
				let offset = 0;

				while (offset < totalSize) {
					const chunk = audioBlob.slice(offset, offset + CHUNK_SIZE);
					const progress = await api.uploadChunk(recordingId, chunk, offset, totalSize);

					offset += chunk.size;

					// Report progress
					if (onProgress) {
						const percentage = (progress.bytes_received / totalSize) * 100;
						onProgress(percentage);
					}

					// Check if complete
					if (progress.is_complete) {
						break;
					}
				}

				return { recordingId, success: true };
			} catch {
				return { recordingId: -1, success: false };
			}
		}
	};
}

// Visualization store (separate for performance - updates at 15fps)
function createVisualizationStore() {
	const { subscribe, set, update } = writable<AudioVisualizationState>({
		analyserData: new Uint8Array(128),
		isAnalyserActive: false
	});

	let animationFrameId: number | null = null;
	let analyser: AnalyserNode | null = null;
	let audioContext: AudioContext | null = null;
	let lastUpdateTime = 0;
	const targetFps = 15;
	const frameInterval = 1000 / targetFps;

	const updateAnalyser = (timestamp: number) => {
		if (!analyser) return;

		if (timestamp - lastUpdateTime >= frameInterval) {
			const dataArray = new Uint8Array(analyser.frequencyBinCount);
			analyser.getByteFrequencyData(dataArray);
			update((state) => ({
				...state,
				analyserData: dataArray
			}));
			lastUpdateTime = timestamp;
		}

		animationFrameId = requestAnimationFrame(updateAnalyser);
	};

	return {
		subscribe,

		start(mediaRecorder: MediaRecorder): void {
			audioContext = new AudioContext();
			const source = audioContext.createMediaStreamSource(mediaRecorder.stream);
			analyser = audioContext.createAnalyser();
			analyser.fftSize = 256;
			source.connect(analyser);

			set({ analyserData: new Uint8Array(analyser.frequencyBinCount), isAnalyserActive: true });
			animationFrameId = requestAnimationFrame(updateAnalyser);
		},

		stop(): void {
			if (animationFrameId) {
				cancelAnimationFrame(animationFrameId);
				animationFrameId = null;
			}
			analyser = null;

			// Clean up AudioContext to prevent resource leak
			if (audioContext) {
				audioContext.close().catch(() => {
					// Ignore cleanup errors
				});
				audioContext = null;
			}

			set({ analyserData: new Uint8Array(128), isAnalyserActive: false });
		}
	};
}

export const recordingStore = createRecordingStore();
export const visualizationStore = createVisualizationStore();

// Derived stores for convenience
export const isRecording = derived(recordingStore, ($store) => $store.state === 'recording');
export const isPaused = derived(recordingStore, ($store) => $store.state === 'paused');
export const isStopped = derived(recordingStore, ($store) => $store.state === 'stopped');
export const recordingTime = derived(recordingStore, ($store) => $store.currentTime);
export const recordingError = derived(recordingStore, ($store) => $store.error);
export const batteryWarning = derived(recordingStore, ($store) => {
	if ($store.batteryLevel === null || $store.batteryCharging) return null;
	if ($store.batteryLevel <= 10) return 'critical';
	if ($store.batteryLevel <= 20) return 'low';
	return null;
});

// Format time helper
export function formatTime(seconds: number): string {
	const hours = Math.floor(seconds / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const secs = seconds % 60;

	if (hours > 0) {
		return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}
	return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
