/**
 * Audio utilities for recording and playback
 */

let audioContext: AudioContext | null = null;

/**
 * Get or create the shared AudioContext
 */
export function getAudioContext(): AudioContext {
	if (!audioContext || audioContext.state === 'closed') {
		audioContext = new AudioContext();
	}
	return audioContext;
}

/**
 * Create an AnalyserNode for audio visualization
 */
export function createAnalyser(
	stream: MediaStream,
	fftSize = 256
): { analyser: AnalyserNode; source: MediaStreamAudioSourceNode } {
	const ctx = getAudioContext();
	const source = ctx.createMediaStreamSource(stream);
	const analyser = ctx.createAnalyser();

	analyser.fftSize = fftSize;
	analyser.smoothingTimeConstant = 0.8;
	source.connect(analyser);

	return { analyser, source };
}

/**
 * Get frequency data from analyser
 */
export function getFrequencyData(analyser: AnalyserNode): Uint8Array {
	const dataArray = new Uint8Array(analyser.frequencyBinCount);
	analyser.getByteFrequencyData(dataArray);
	return dataArray;
}

/**
 * Get waveform data from analyser
 */
export function getWaveformData(analyser: AnalyserNode): Uint8Array {
	const dataArray = new Uint8Array(analyser.frequencyBinCount);
	analyser.getByteTimeDomainData(dataArray);
	return dataArray;
}

/**
 * Check if audio recording is supported
 */
export function isRecordingSupported(): boolean {
	return !!(typeof MediaRecorder !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

/**
 * Get supported MIME types for MediaRecorder
 */
export function getSupportedMimeTypes(): string[] {
	const types = [
		'audio/webm;codecs=opus',
		'audio/webm',
		'audio/ogg;codecs=opus',
		'audio/mp4',
		'audio/mpeg'
	];

	return types.filter((type) => MediaRecorder.isTypeSupported(type));
}

/**
 * Get the best supported MIME type
 */
export function getBestMimeType(): string {
	const supported = getSupportedMimeTypes();
	return supported[0] || 'audio/webm';
}

/**
 * Request microphone permission
 */
export async function requestMicrophonePermission(): Promise<PermissionState> {
	try {
		const permission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
		return permission.state;
	} catch {
		// Firefox doesn't support permissions.query for microphone
		// Try to get user media to check permission
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			stream.getTracks().forEach((track) => track.stop());
			return 'granted';
		} catch {
			return 'denied';
		}
	}
}

/**
 * Create audio blob URL for playback
 */
export function createAudioUrl(blob: Blob): string {
	return URL.createObjectURL(blob);
}

/**
 * Revoke audio blob URL
 */
export function revokeAudioUrl(url: string): void {
	URL.revokeObjectURL(url);
}

/**
 * Get audio duration from blob
 */
export async function getAudioDuration(blob: Blob): Promise<number> {
	return new Promise((resolve, reject) => {
		const audio = new Audio();
		audio.src = createAudioUrl(blob);

		audio.onloadedmetadata = () => {
			// Some browsers set duration to Infinity initially
			if (audio.duration === Infinity) {
				audio.currentTime = 1e101;
				audio.ontimeupdate = () => {
					audio.ontimeupdate = null;
					resolve(audio.duration);
					audio.currentTime = 0;
				};
			} else {
				resolve(audio.duration);
			}
		};

		audio.onerror = () => {
			reject(new Error('Failed to load audio'));
		};
	});
}

/**
 * Convert blob to ArrayBuffer
 */
export function blobToArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
	return blob.arrayBuffer();
}

/**
 * Convert ArrayBuffer to blob
 */
export function arrayBufferToBlob(buffer: ArrayBuffer, mimeType = 'audio/webm'): Blob {
	return new Blob([buffer], { type: mimeType });
}

/**
 * Monitor battery status (for recording warnings)
 */
export async function getBatteryStatus(): Promise<{
	level: number;
	charging: boolean;
} | null> {
	try {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const battery = await (navigator as any).getBattery?.();
		if (battery) {
			return {
				level: Math.round(battery.level * 100),
				charging: battery.charging
			};
		}
		return null;
	} catch {
		return null;
	}
}

/**
 * Subscribe to battery status changes
 */
export async function onBatteryStatusChange(
	callback: (status: { level: number; charging: boolean }) => void
): Promise<() => void> {
	try {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const battery = await (navigator as any).getBattery?.();
		if (!battery) return () => {};

		const handleChange = () => {
			callback({
				level: Math.round(battery.level * 100),
				charging: battery.charging
			});
		};

		battery.addEventListener('levelchange', handleChange);
		battery.addEventListener('chargingchange', handleChange);

		return () => {
			battery.removeEventListener('levelchange', handleChange);
			battery.removeEventListener('chargingchange', handleChange);
		};
	} catch {
		return () => {};
	}
}
