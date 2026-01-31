<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import TldrawWrapper from './TldrawWrapper.svelte';
	import SketchToolbar from './SketchToolbar.svelte';
	import { sketchStore } from '$lib/stores/sketch';
	import type { Agenda } from '$lib/stores/meeting';

	// Editor type from tldraw - available at runtime
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	type Editor = any;

	interface Props {
		meetingId: number;
		agendas?: Agenda[];
		currentAgendaId?: number | null;
		showAgendaPanel?: boolean;
		onAgendaChange?: (agendaId: number) => void;
	}

	let {
		meetingId,
		agendas = [],
		currentAgendaId = null,
		showAgendaPanel = true,
		onAgendaChange
	}: Props = $props();

	let tldrawWrapper: TldrawWrapper;
	let isPanelCollapsed = $state(false);
	let isPencilMode = $state(false);

	onMount(() => {
		// Load existing sketches for this meeting
		sketchStore.loadSketches(meetingId);
		sketchStore.loadLastToolPreferences(meetingId);
		sketchStore.startAutoSave();
	});

	onDestroy(() => {
		// Save before unmounting
		sketchStore.saveSketch(meetingId);
		sketchStore.stopAutoSave();
	});

	function handleEditorMount(editor: Editor) {
		sketchStore.setEditor(editor);

		// Try to load from localStorage as backup
		const localSnapshot = sketchStore.loadFromLocalStorage(meetingId);
		if (localSnapshot) {
			try {
				editor.store.loadSnapshot(localSnapshot);
			} catch {
				// Failed to load local snapshot
			}
		}
	}

	function handleEditorChange() {
		sketchStore.markDirty();
	}

	function handlePencilDetected() {
		isPencilMode = true;
		// Switch to draw tool when pencil is detected
		if ($sketchStore.currentTool !== 'draw') {
			sketchStore.setTool('draw');
		}
	}

	function handleUndo() {
		tldrawWrapper?.undo();
	}

	function handleRedo() {
		tldrawWrapper?.redo();
	}

	function handleClear() {
		if (confirm('Are you sure you want to clear all sketches?')) {
			tldrawWrapper?.clearAll();
		}
	}

	function togglePanel() {
		isPanelCollapsed = !isPanelCollapsed;
	}

	function handleAgendaClick(agendaId: number) {
		onAgendaChange?.(agendaId);
	}

	function getAgendaProgress(agenda: Agenda): number {
		if (!agenda.questions || agenda.questions.length === 0) return 0;
		const answered = agenda.questions.filter(q => q.answered).length;
		return (answered / agenda.questions.length) * 100;
	}

	// Keyboard shortcuts
	function handleKeydown(event: KeyboardEvent) {
		if ((event.metaKey || event.ctrlKey) && event.key === 'z') {
			if (event.shiftKey) {
				event.preventDefault();
				handleRedo();
			} else {
				event.preventDefault();
				handleUndo();
			}
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="sketch-pad">
	<!-- Agenda Panel (30% / collapsible) -->
	{#if showAgendaPanel}
		<aside
			class="agenda-panel"
			class:collapsed={isPanelCollapsed}
			aria-label="Agenda panel"
		>
			<div class="panel-header">
				<button
					type="button"
					class="collapse-btn"
					onclick={togglePanel}
					aria-label={isPanelCollapsed ? 'Expand agenda panel' : 'Collapse agenda panel'}
					aria-expanded={!isPanelCollapsed}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						{#if isPanelCollapsed}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						{:else}
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
						{/if}
					</svg>
				</button>
				{#if !isPanelCollapsed}
					<h2 class="panel-title">Agenda</h2>
				{/if}
			</div>

			{#if !isPanelCollapsed}
				<div class="agenda-list">
					{#each agendas as agenda, index}
						<button
							type="button"
							class="agenda-item"
							class:active={currentAgendaId === agenda.id}
							class:completed={agenda.status === 'completed'}
							onclick={() => handleAgendaClick(agenda.id)}
						>
							<div class="agenda-header">
								<span class="agenda-number">{index + 1}</span>
								<span class="agenda-title">{agenda.title}</span>
							</div>

							<!-- Progress bar -->
							<div class="agenda-progress">
								<div
									class="progress-bar"
									style="width: {getAgendaProgress(agenda)}%"
									class:completed={agenda.status === 'completed'}
								></div>
							</div>

							<!-- Questions checklist -->
							{#if agenda.questions && agenda.questions.length > 0}
								<ul class="questions-list">
									{#each agenda.questions as question}
										<li class="question-item" class:answered={question.answered}>
											<span class="question-check">
												{#if question.answered}
													<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
														<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
													</svg>
												{/if}
											</span>
											<span class="question-text">{question.question}</span>
										</li>
									{/each}
								</ul>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		</aside>
	{/if}

	<!-- Sketch Area (70%) -->
	<main class="sketch-area" aria-label="Sketch area">
		<!-- Toolbar -->
		<div class="toolbar-container">
			<SketchToolbar
				onUndo={handleUndo}
				onRedo={handleRedo}
				onClear={handleClear}
			/>

			<!-- Status indicators -->
			<div class="status-bar">
				{#if isPencilMode}
					<span class="status-badge pencil">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
						</svg>
						Pencil Mode
					</span>
				{/if}

				{#if $sketchStore.isDirty}
					<span class="status-badge unsaved">Unsaved changes</span>
				{:else if $sketchStore.lastSavedAt}
					<span class="status-badge saved">
						Saved {$sketchStore.lastSavedAt.toLocaleTimeString()}
					</span>
				{/if}
			</div>
		</div>

		<!-- Tldraw Canvas -->
		<div class="canvas-container">
			<TldrawWrapper
				bind:this={tldrawWrapper}
				onEditorMount={handleEditorMount}
				onEditorChange={handleEditorChange}
				onPencilDetected={handlePencilDetected}
			/>
		</div>
	</main>
</div>

<style>
	.sketch-pad {
		display: flex;
		height: 100%;
		width: 100%;
		background: #f9fafb;
	}

	/* Agenda Panel */
	.agenda-panel {
		width: 30%;
		min-width: 280px;
		max-width: 400px;
		background: white;
		border-right: 1px solid #e5e7eb;
		display: flex;
		flex-direction: column;
		transition: width 0.2s ease;
	}

	.agenda-panel.collapsed {
		width: 48px;
		min-width: 48px;
	}

	.panel-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.75rem;
		border-bottom: 1px solid #e5e7eb;
	}

	.collapse-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		border: none;
		border-radius: 0.375rem;
		background: transparent;
		color: #6b7280;
		cursor: pointer;
		transition: background 0.15s;
	}

	.collapse-btn:hover {
		background: #f3f4f6;
	}

	.panel-title {
		font-size: 1rem;
		font-weight: 600;
		color: #111827;
		margin: 0;
	}

	.agenda-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
	}

	.agenda-item {
		display: block;
		width: 100%;
		text-align: left;
		padding: 0.75rem;
		margin-bottom: 0.5rem;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.agenda-item:hover {
		border-color: #d1d5db;
		background: #f9fafb;
	}

	.agenda-item.active {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.agenda-item.completed {
		opacity: 0.7;
	}

	.agenda-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.agenda-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		font-size: 0.75rem;
		font-weight: 600;
		background: #e5e7eb;
		border-radius: 50%;
		color: #374151;
	}

	.agenda-item.active .agenda-number {
		background: #3b82f6;
		color: white;
	}

	.agenda-title {
		flex: 1;
		font-size: 0.875rem;
		font-weight: 500;
		color: #111827;
	}

	.agenda-progress {
		height: 4px;
		background: #e5e7eb;
		border-radius: 2px;
		margin-bottom: 0.5rem;
		overflow: hidden;
	}

	.progress-bar {
		height: 100%;
		background: #fbbf24;
		transition: width 0.3s ease;
	}

	.progress-bar.completed {
		background: #22c55e;
	}

	.questions-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.question-item {
		display: flex;
		align-items: flex-start;
		gap: 0.375rem;
		padding: 0.25rem 0;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.question-item.answered {
		color: #22c55e;
	}

	.question-check {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		flex-shrink: 0;
		border: 1px solid #d1d5db;
		border-radius: 0.25rem;
		background: white;
	}

	.question-item.answered .question-check {
		background: #22c55e;
		border-color: #22c55e;
		color: white;
	}

	.question-text {
		line-height: 1.4;
	}

	/* Sketch Area */
	.sketch-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.toolbar-container {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem;
		background: #f3f4f6;
		border-bottom: 1px solid #e5e7eb;
	}

	.status-bar {
		display: flex;
		gap: 0.5rem;
	}

	.status-badge {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.25rem 0.5rem;
		font-size: 0.75rem;
		border-radius: 9999px;
	}

	.status-badge.pencil {
		background: #dbeafe;
		color: #1d4ed8;
	}

	.status-badge.unsaved {
		background: #fef3c7;
		color: #d97706;
	}

	.status-badge.saved {
		background: #d1fae5;
		color: #059669;
	}

	.canvas-container {
		flex: 1;
		position: relative;
	}

	/* Responsive adjustments */
	@media (max-width: 1023px) {
		.agenda-panel {
			width: 40%;
		}
	}

	@media (max-width: 767px) {
		.sketch-pad {
			flex-direction: column;
		}

		.agenda-panel {
			width: 100%;
			max-width: none;
			max-height: 200px;
			border-right: none;
			border-bottom: 1px solid #e5e7eb;
		}

		.agenda-panel.collapsed {
			width: 100%;
			max-height: 48px;
		}
	}
</style>
