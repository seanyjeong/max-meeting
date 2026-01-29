<script lang="ts">
	/**
	 * Waveform - Real-time audio visualization
	 *
	 * - Uses AnalyserNode for frequency data
	 * - 15fps for battery efficiency
	 * - Canvas-based rendering
	 */
	import { onMount, onDestroy } from 'svelte';
	import { visualizationStore } from '$lib/stores/recording';

	interface Props {
		width?: number;
		height?: number;
		barColor?: string;
		backgroundColor?: string;
		barWidth?: number;
		barGap?: number;
	}

	let {
		width = 300,
		height = 80,
		barColor = '#ef4444',
		backgroundColor = 'transparent',
		barWidth = 3,
		barGap = 1
	}: Props = $props();

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;

	onMount(() => {
		ctx = canvas.getContext('2d');
		if (ctx) {
			// Set canvas resolution for retina displays
			const dpr = window.devicePixelRatio || 1;
			canvas.width = width * dpr;
			canvas.height = height * dpr;
			ctx.scale(dpr, dpr);
		}
	});

	// Reactive drawing based on store updates
	$effect(() => {
		if (!ctx) return;

		const data = $visualizationStore.analyserData;
		drawBars(data);
	});

	function drawBars(data: Uint8Array) {
		if (!ctx) return;

		// Clear canvas
		ctx.fillStyle = backgroundColor;
		ctx.fillRect(0, 0, width, height);

		if (!$visualizationStore.isAnalyserActive) {
			// Draw idle state (flat line)
			ctx.fillStyle = '#e5e7eb';
			const centerY = height / 2;
			ctx.fillRect(0, centerY - 1, width, 2);
			return;
		}

		// Calculate number of bars that fit
		const barCount = Math.floor(width / (barWidth + barGap));
		const step = Math.floor(data.length / barCount);

		ctx.fillStyle = barColor;

		for (let i = 0; i < barCount; i++) {
			// Get average value for this bar
			let sum = 0;
			for (let j = 0; j < step; j++) {
				sum += data[i * step + j];
			}
			const average = sum / step;

			// Normalize to height (0-255 -> 0-height)
			const barHeight = Math.max(2, (average / 255) * height * 0.9);

			const x = i * (barWidth + barGap);
			const y = (height - barHeight) / 2;

			// Draw bar with rounded corners
			ctx.beginPath();
			ctx.roundRect(x, y, barWidth, barHeight, barWidth / 2);
			ctx.fill();
		}
	}

	onDestroy(() => {
		// Cleanup if needed
	});
</script>

<div class="waveform-container">
	<canvas
		bind:this={canvas}
		style="width: {width}px; height: {height}px;"
		aria-label="오디오 파형 시각화"
	></canvas>
</div>

<style>
	.waveform-container {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	canvas {
		border-radius: 8px;
	}
</style>
