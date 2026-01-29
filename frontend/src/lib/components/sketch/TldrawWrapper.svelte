<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';

	// Editor type from tldraw - available at runtime via dynamic import
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	type Editor = any;

	interface Props {
		height?: string;
		width?: string;
		onEditorMount?: (editor: Editor) => void;
		onEditorChange?: () => void;
		onPencilDetected?: () => void;
		initialSnapshot?: any;
		autoFocus?: boolean;
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

	let container: HTMLDivElement;
	let reactRoot: any = null;
	let editor: Editor | null = null;
	let isPencilActive = $state(false);
	let changeDebounceTimer: ReturnType<typeof setTimeout> | null = null;

	onMount(async () => {
		if (!browser || !container) return;

		try {
			// Dynamic imports for React and tldraw
			const React = await import('react');
			const ReactDOM = await import('react-dom/client');
			const { Tldraw } = await import('@tldraw/tldraw');
			await import('@tldraw/tldraw/tldraw.css');

			reactRoot = ReactDOM.createRoot(container);

			const handleEditorMount = (e: Editor) => {
				editor = e;

				// Load initial snapshot if provided
				if (initialSnapshot) {
					try {
						e.store.loadSnapshot(initialSnapshot);
					} catch (err) {
						console.warn('Failed to load initial snapshot:', err);
					}
				}

				// Listen for changes with debounce to prevent infinite loop
				e.store.listen(() => {
					if (changeDebounceTimer) {
						clearTimeout(changeDebounceTimer);
					}
					changeDebounceTimer = setTimeout(() => {
						onEditorChange?.();
						changeDebounceTimer = null;
					}, 300);
				}, { source: 'user' });

				// Pencil detection via pointer events
				document.addEventListener('pointerdown', handlePointerEvent);
				document.addEventListener('pointermove', handlePointerEvent);

				onEditorMount?.(e);
			};

			reactRoot.render(
				React.createElement(Tldraw, {
					onMount: handleEditorMount,
					autoFocus
				})
			);
		} catch (error) {
			console.error('Failed to initialize tldraw:', error);
		}
	});

	function handlePointerEvent(event: PointerEvent) {
		if (event.pointerType === 'pen') {
			if (!isPencilActive) {
				isPencilActive = true;
				onPencilDetected?.();
			}
		}
	}

	onDestroy(() => {
		document.removeEventListener('pointerdown', handlePointerEvent);
		document.removeEventListener('pointermove', handlePointerEvent);

		if (changeDebounceTimer) {
			clearTimeout(changeDebounceTimer);
		}

		if (reactRoot) {
			reactRoot.unmount();
			reactRoot = null;
		}
		editor = null;
	});

	// Public methods exposed via bind:this
	export function getEditor(): Editor | null {
		return editor;
	}

	export function getSnapshot(): any {
		return editor?.store.getSnapshot() ?? null;
	}

	export function loadSnapshot(snapshot: any): void {
		if (editor && snapshot) {
			editor.store.loadSnapshot(snapshot);
		}
	}

	export function setTool(tool: string): void {
		if (editor) {
			editor.setCurrentTool(tool);
		}
	}

	export function undo(): void {
		editor?.undo();
	}

	export function redo(): void {
		editor?.redo();
	}

	export function zoomToFit(): void {
		editor?.zoomToFit();
	}

	export function zoomIn(): void {
		editor?.zoomIn();
	}

	export function zoomOut(): void {
		editor?.zoomOut();
	}

	export function clearAll(): void {
		if (editor) {
			editor.selectAll();
			editor.deleteShapes(editor.getSelectedShapeIds());
		}
	}
</script>

<div
	bind:this={container}
	class="tldraw-wrapper"
	style="height: {height}; width: {width};"
	data-pencil-active={isPencilActive}
>
	{#if !browser}
		<div class="flex items-center justify-center h-full bg-gray-100 text-gray-500">
			Loading sketch editor...
		</div>
	{/if}
</div>

<style>
	.tldraw-wrapper {
		position: relative;
		overflow: hidden;
		touch-action: none;
	}

	/* Override tldraw styles for tablet-friendly UI */
	.tldraw-wrapper :global(.tl-canvas) {
		touch-action: none;
	}

	/* Pencil hover preview cursor */
	.tldraw-wrapper[data-pencil-active='true'] :global(.tl-canvas) {
		cursor: crosshair;
	}
</style>
