<script lang="ts">
	/**
	 * DraggablePostIt - Draggable PostIt note component
	 * Supports mouse and touch drag, delete action, custom colors
	 */
	import { X } from 'lucide-svelte';

	interface Note {
		id: number;
		content: string;
		position_x: number | null;
		position_y: number | null;
		rotation: number | null;
		z_index: number;
		bg_color?: string | null;
		text_color?: string | null;
	}

	interface Props {
		note: Note;
		editable?: boolean;
		onmove?: (id: number, x: number, y: number) => void;
		ondelete?: (id: number) => void;
	}

	let { note, editable = true, onmove, ondelete }: Props = $props();

	let isDragging = $state(false);
	let showActions = $state(false);
	let element: HTMLDivElement;

	// Position state (% based)
	let currentX = $state(note.position_x ?? 5 + Math.random() * 20);
	let currentY = $state(note.position_y ?? 5 + Math.random() * 30);

	// Drag offset
	let offsetX = 0;
	let offsetY = 0;

	// Random rotation for natural look
	let rotation = $derived(note.rotation ?? (Math.random() * 6 - 3));

	// Color mapping
	const bgColorMap: Record<string, string> = {
		yellow: '#fef08a',
		pink: '#fbcfe8',
		green: '#bbf7d0',
		blue: '#bfdbfe',
		purple: '#ddd6fe',
		orange: '#fed7aa'
	};

	const borderColorMap: Record<string, string> = {
		yellow: '#fde047',
		pink: '#f9a8d4',
		green: '#86efac',
		blue: '#93c5fd',
		purple: '#c4b5fd',
		orange: '#fdba74'
	};

	// Get actual colors
	let bgColor = $derived(
		note.bg_color
			? bgColorMap[note.bg_color] || note.bg_color
			: '#fef08a'
	);
	let borderColor = $derived(
		note.bg_color
			? borderColorMap[note.bg_color] || note.bg_color
			: '#fde047'
	);
	let textColor = $derived(note.text_color || '#374151');

	function handleMouseDown(e: MouseEvent) {
		if (!editable) return;
		startDrag(e.clientX, e.clientY);
	}

	function handleTouchStart(e: TouchEvent) {
		if (!editable) return;
		const touch = e.touches[0];
		startDrag(touch.clientX, touch.clientY);
	}

	function startDrag(clientX: number, clientY: number) {
		isDragging = true;
		const parent = element.parentElement;
		if (!parent) return;

		const rect = parent.getBoundingClientRect();
		const elemRect = element.getBoundingClientRect();

		// Calculate offset from cursor to element top-left (in %)
		offsetX = ((clientX - elemRect.left) / rect.width) * 100;
		offsetY = ((clientY - elemRect.top) / rect.height) * 100;
	}

	function handleMouseMove(e: MouseEvent) {
		if (!isDragging) return;
		moveTo(e.clientX, e.clientY);
	}

	function handleTouchMove(e: TouchEvent) {
		if (!isDragging) return;
		const touch = e.touches[0];
		moveTo(touch.clientX, touch.clientY);
	}

	function moveTo(clientX: number, clientY: number) {
		const parent = element?.parentElement;
		if (!parent) return;

		const rect = parent.getBoundingClientRect();
		const newX = ((clientX - rect.left) / rect.width) * 100 - offsetX;
		const newY = ((clientY - rect.top) / rect.height) * 100 - offsetY;

		// Clamp to container bounds
		currentX = Math.max(0, Math.min(85, newX));
		currentY = Math.max(0, Math.min(85, newY));
	}

	function handleMouseUp() {
		if (isDragging) {
			isDragging = false;
			onmove?.(note.id, currentX, currentY);
		}
	}

	function handleDelete() {
		ondelete?.(note.id);
	}
</script>

<svelte:window
	onmousemove={handleMouseMove}
	onmouseup={handleMouseUp}
	ontouchmove={handleTouchMove}
	ontouchend={handleMouseUp}
/>

<div
	bind:this={element}
	class="draggable-postit"
	class:dragging={isDragging}
	class:editable
	style="
		left: {currentX}%;
		top: {currentY}%;
		transform: rotate({rotation}deg);
		z-index: {isDragging ? 9999 : note.z_index + 10};
		background-color: {bgColor};
		border-color: {borderColor};
		color: {textColor};
	"
	onmousedown={handleMouseDown}
	ontouchstart={handleTouchStart}
	onmouseenter={() => (showActions = true)}
	onmouseleave={() => (showActions = false)}
	role="button"
	tabindex="0"
>
	{#if editable && showActions}
		<button
			type="button"
			class="delete-btn"
			onclick={(e) => { e.stopPropagation(); handleDelete(); }}
			aria-label="메모 삭제"
		>
			<X class="w-3 h-3" />
		</button>
	{/if}

	<div class="postit-content">
		{note.content}
	</div>
</div>

<style>
	.draggable-postit {
		position: absolute;
		width: 140px;
		min-height: 100px;
		padding: 0.75rem;
		border-radius: 2px;
		border: 1px solid;
		box-shadow:
			2px 2px 8px rgba(0, 0, 0, 0.1),
			0 0 1px rgba(0, 0, 0, 0.1);
		transition:
			box-shadow 0.2s ease,
			transform 0.1s ease;
		user-select: none;
	}

	.draggable-postit.editable {
		cursor: grab;
	}

	.draggable-postit:hover {
		box-shadow:
			4px 4px 12px rgba(0, 0, 0, 0.15),
			0 0 2px rgba(0, 0, 0, 0.1);
	}

	.draggable-postit.dragging {
		cursor: grabbing;
		box-shadow:
			8px 8px 20px rgba(0, 0, 0, 0.2),
			0 0 4px rgba(0, 0, 0, 0.1);
		opacity: 0.9;
	}

	.delete-btn {
		position: absolute;
		top: -8px;
		right: -8px;
		width: 20px;
		height: 20px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: #ef4444;
		color: white;
		border: 2px solid white;
		cursor: pointer;
		z-index: 10;
		transition: background 0.15s ease;
	}

	.delete-btn:hover {
		background: #dc2626;
	}

	.postit-content {
		font-size: 0.8125rem;
		line-height: 1.4;
		word-break: break-word;
		white-space: pre-wrap;
	}

	/* Pin effect at top */
	.draggable-postit::before {
		content: '';
		position: absolute;
		top: -4px;
		left: 50%;
		transform: translateX(-50%);
		width: 8px;
		height: 8px;
		background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
		border-radius: 50%;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
	}
</style>
