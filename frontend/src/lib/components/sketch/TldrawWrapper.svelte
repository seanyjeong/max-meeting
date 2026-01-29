<script lang="ts">
	/**
	 * SimpleSketch - 간단한 HTML5 Canvas 스케치 도구
	 * Excalidraw 대신 직접 구현 (SSR 호환)
	 */
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

	interface Props {
		height?: string;
		width?: string;
		onEditorMount?: (api: any) => void;
		onEditorChange?: () => void;
		onPencilDetected?: () => void;
		initialSnapshot?: SketchSnapshot;
		autoFocus?: boolean;
	}

	interface SketchSnapshot {
		dataUrl?: string;
		strokes?: Stroke[];
	}

	interface Point {
		x: number;
		y: number;
	}

	interface Stroke {
		points: Point[];
		color: string;
		width: number;
	}

	let {
		height = '100%',
		width = '100%',
		onEditorMount,
		onEditorChange,
		onPencilDetected,
		initialSnapshot,
		autoFocus = true
	}: Props = $props();

	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;
	let isDrawing = $state(false);
	let currentColor = $state('#000000');
	let currentWidth = $state(3);
	let strokes = $state<Stroke[]>([]);
	let currentStroke: Stroke | null = null;

	// 도구 선택
	let tool = $state<'pen' | 'eraser'>('pen');

	// 펜 모드: 펜이 감지되면 터치 무시
	let penDetected = $state(false);
	let activePointerId = $state<number | null>(null);

	// 색상 팔레트
	const colors = ['#000000', '#EF4444', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'];

	onMount(() => {
		if (!browser || !canvas) return;

		ctx = canvas.getContext('2d');
		if (!ctx) return;

		// 캔버스 크기 설정
		resizeCanvas();
		window.addEventListener('resize', resizeCanvas);

		// 초기 스냅샷 로드
		if (initialSnapshot?.strokes) {
			strokes = initialSnapshot.strokes;
			redraw();
		} else if (initialSnapshot?.dataUrl) {
			const img = new Image();
			img.onload = () => {
				ctx?.drawImage(img, 0, 0);
			};
			img.src = initialSnapshot.dataUrl;
		}

		onEditorMount?.({ getSnapshot, loadSnapshot, clearAll });
	});

	onDestroy(() => {
		if (browser) {
			window.removeEventListener('resize', resizeCanvas);
		}
	});

	function resizeCanvas() {
		if (!canvas || !ctx) return;
		const rect = canvas.parentElement?.getBoundingClientRect();
		if (rect) {
			canvas.width = rect.width;
			canvas.height = rect.height;
			redraw();
		}
	}

	function redraw() {
		if (!ctx || !canvas) return;
		ctx.fillStyle = '#ffffff';
		ctx.fillRect(0, 0, canvas.width, canvas.height);

		for (const stroke of strokes) {
			drawStroke(stroke);
		}
	}

	function drawStroke(stroke: Stroke) {
		if (!ctx || stroke.points.length < 2) return;

		ctx.beginPath();
		ctx.strokeStyle = stroke.color;
		ctx.lineWidth = stroke.width;
		ctx.lineCap = 'round';
		ctx.lineJoin = 'round';

		ctx.moveTo(stroke.points[0].x, stroke.points[0].y);
		for (let i = 1; i < stroke.points.length; i++) {
			ctx.lineTo(stroke.points[i].x, stroke.points[i].y);
		}
		ctx.stroke();
	}

	function getPointerPos(e: PointerEvent): Point {
		const rect = canvas.getBoundingClientRect();
		return {
			x: e.clientX - rect.left,
			y: e.clientY - rect.top
		};
	}

	function handlePointerDown(e: PointerEvent) {
		// 펜이 감지되면 이후 터치 입력 무시 (Palm Rejection)
		if (e.pointerType === 'pen') {
			penDetected = true;
			onPencilDetected?.();
		}

		// 펜이 감지된 상태에서 터치 입력은 무시
		if (penDetected && e.pointerType === 'touch') {
			e.preventDefault();
			return;
		}

		// 이미 다른 포인터가 그리고 있으면 무시
		if (activePointerId !== null && activePointerId !== e.pointerId) {
			return;
		}

		isDrawing = true;
		activePointerId = e.pointerId;
		const pos = getPointerPos(e);

		currentStroke = {
			points: [pos],
			color: tool === 'eraser' ? '#ffffff' : currentColor,
			width: tool === 'eraser' ? 20 : currentWidth
		};

		canvas.setPointerCapture(e.pointerId);
	}

	function handlePointerMove(e: PointerEvent) {
		// 펜이 감지된 상태에서 터치 입력은 무시
		if (penDetected && e.pointerType === 'touch') {
			return;
		}

		// 활성 포인터가 아니면 무시
		if (activePointerId !== e.pointerId) {
			return;
		}

		if (!isDrawing || !currentStroke || !ctx) return;

		const pos = getPointerPos(e);
		currentStroke.points.push(pos);

		// 실시간 그리기
		if (currentStroke.points.length >= 2) {
			const lastIdx = currentStroke.points.length - 1;
			ctx.beginPath();
			ctx.strokeStyle = currentStroke.color;
			ctx.lineWidth = currentStroke.width;
			ctx.lineCap = 'round';
			ctx.lineJoin = 'round';
			ctx.moveTo(currentStroke.points[lastIdx - 1].x, currentStroke.points[lastIdx - 1].y);
			ctx.lineTo(currentStroke.points[lastIdx].x, currentStroke.points[lastIdx].y);
			ctx.stroke();
		}
	}

	function handlePointerUp(e: PointerEvent) {
		// 활성 포인터가 아니면 무시
		if (activePointerId !== e.pointerId) {
			return;
		}

		if (!isDrawing || !currentStroke) {
			activePointerId = null;
			return;
		}

		isDrawing = false;
		activePointerId = null;

		if (currentStroke.points.length > 1) {
			strokes = [...strokes, currentStroke];
			onEditorChange?.();
		}
		currentStroke = null;
		canvas.releasePointerCapture(e.pointerId);
	}

	// Public API
	export function getSnapshot(): SketchSnapshot {
		return {
			strokes: [...strokes],
			dataUrl: canvas?.toDataURL('image/png')
		};
	}

	export function loadSnapshot(snapshot: SketchSnapshot): void {
		if (snapshot?.strokes) {
			strokes = snapshot.strokes;
			redraw();
		}
	}

	export function clearAll(): void {
		strokes = [];
		redraw();
		onEditorChange?.();
	}

	export function getEditor() {
		return { getSnapshot, loadSnapshot, clearAll };
	}

	// 호환성을 위한 빈 함수들
	export function setTool(t: string): void {
		if (t === 'eraser') tool = 'eraser';
		else tool = 'pen';
	}
	export function undo(): void {
		if (strokes.length > 0) {
			strokes = strokes.slice(0, -1);
			redraw();
			onEditorChange?.();
		}
	}
	export function redo(): void {}
	export function zoomToFit(): void {}
	export function zoomIn(): void {}
	export function zoomOut(): void {}
</script>

<div class="sketch-container" style="height: {height}; width: {width};">
	<!-- 툴바 -->
	<div class="toolbar">
		<!-- 도구 선택 -->
		<div class="tool-group">
			<button
				type="button"
				class="tool-btn {tool === 'pen' ? 'active' : ''}"
				onclick={() => (tool = 'pen')}
				title="펜"
			>
				✏️
			</button>
			<button
				type="button"
				class="tool-btn {tool === 'eraser' ? 'active' : ''}"
				onclick={() => (tool = 'eraser')}
				title="지우개"
			>
				🧹
			</button>
		</div>

		<!-- 색상 선택 -->
		<div class="color-group">
			{#each colors as color}
				<button
					type="button"
					class="color-btn {currentColor === color ? 'active' : ''}"
					style="background-color: {color};"
					onclick={() => (currentColor = color)}
				></button>
			{/each}
		</div>

		<!-- 굵기 선택 -->
		<div class="width-group">
			<input
				type="range"
				min="1"
				max="20"
				bind:value={currentWidth}
				class="width-slider"
			/>
			<span class="width-label">{currentWidth}px</span>
		</div>

		<!-- 작업 버튼 -->
		<div class="action-group">
			<button type="button" class="action-btn" onclick={undo} title="실행 취소">
				↩️
			</button>
			<button type="button" class="action-btn" onclick={clearAll} title="전체 지우기">
				🗑️
			</button>
		</div>
	</div>

	<!-- 캔버스 -->
	<div class="canvas-wrapper">
		<canvas
			bind:this={canvas}
			class="sketch-canvas"
			onpointerdown={handlePointerDown}
			onpointermove={handlePointerMove}
			onpointerup={handlePointerUp}
			onpointerleave={handlePointerUp}
		></canvas>
	</div>
</div>

<style>
	.sketch-container {
		display: flex;
		flex-direction: column;
		background: #f9fafb;
	}

	.toolbar {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 8px 12px;
		background: white;
		border-bottom: 1px solid #e5e7eb;
		flex-shrink: 0;
	}

	.tool-group,
	.color-group,
	.width-group,
	.action-group {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.tool-btn,
	.action-btn {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid #e5e7eb;
		border-radius: 6px;
		background: white;
		cursor: pointer;
		font-size: 18px;
		transition: all 0.15s;
	}

	.tool-btn:hover,
	.action-btn:hover {
		background: #f3f4f6;
	}

	.tool-btn.active {
		background: #dbeafe;
		border-color: #3b82f6;
	}

	.color-btn {
		width: 24px;
		height: 24px;
		border: 2px solid #e5e7eb;
		border-radius: 50%;
		cursor: pointer;
		transition: transform 0.15s;
	}

	.color-btn:hover {
		transform: scale(1.1);
	}

	.color-btn.active {
		border-color: #3b82f6;
		box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
	}

	.width-slider {
		width: 80px;
		cursor: pointer;
	}

	.width-label {
		font-size: 12px;
		color: #6b7280;
		min-width: 35px;
	}

	.canvas-wrapper {
		flex: 1;
		overflow: hidden;
		background: white;
	}

	.sketch-canvas {
		display: block;
		width: 100%;
		height: 100%;
		touch-action: none;
		cursor: crosshair;
		-webkit-touch-callout: none;
		-webkit-user-select: none;
		user-select: none;
	}

	/* 캔버스 래퍼도 터치 방지 */
	.canvas-wrapper {
		touch-action: none;
		-webkit-overflow-scrolling: auto;
	}

	/* 터치 친화적 */
	@media (hover: none) and (pointer: coarse) {
		.tool-btn,
		.action-btn {
			width: 44px;
			height: 44px;
		}

		.color-btn {
			width: 32px;
			height: 32px;
		}
	}
</style>
