<script lang="ts">
	import { resultsStore } from '$lib/stores/results';
	import DOMPurify from 'dompurify';

	interface Props {
		readonly?: boolean;
	}

	let { readonly = false }: Props = $props();

	let showPreview = $state(false);
	let textareaEl = $state<HTMLTextAreaElement | null>(null);

	// Simple markdown to HTML converter for preview
	function parseMarkdown(text: string): string {
		if (!text) return '';

		// Convert markdown to HTML
		let html = text
			// Headers
			.replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
			.replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
			.replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>')
			// Bold
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			// Italic
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			// Bullet lists
			.replace(/^\s*[-*]\s+(.*)$/gim, '<li class="ml-4">$1</li>')
			// Numbered lists
			.replace(/^\s*\d+\.\s+(.*)$/gim, '<li class="ml-4 list-decimal">$1</li>')
			// Line breaks
			.replace(/\n\n/g, '</p><p class="mb-2">')
			.replace(/\n/g, '<br>');

		// Sanitize the HTML to prevent XSS
		return DOMPurify.sanitize(html);
	}

	function handleInput(event: Event) {
		const target = event.target as HTMLTextAreaElement;
		resultsStore.setEditedSummary(target.value);
	}

	function togglePreview() {
		showPreview = !showPreview;
	}

	function insertMarkdown(prefix: string, suffix: string = '') {
		if (!textareaEl || readonly) return;

		const el = textareaEl;
		const start = el.selectionStart;
		const end = el.selectionEnd;
		const text = $resultsStore.editedSummary;
		const selected = text.substring(start, end);

		const newText =
			text.substring(0, start) +
			prefix +
			(selected || 'text') +
			suffix +
			text.substring(end);

		resultsStore.setEditedSummary(newText);

		// Restore cursor position
		requestAnimationFrame(() => {
			el.focus();
			const newPos = start + prefix.length + (selected ? selected.length : 4);
			el.setSelectionRange(newPos, newPos);
		});
	}
</script>

<div class="summary-editor">
	<!-- Toolbar -->
	<div class="editor-toolbar">
		<div class="toolbar-group">
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('# ')}
				title="Heading 1"
				disabled={readonly}
			>
				H1
			</button>
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('## ')}
				title="Heading 2"
				disabled={readonly}
			>
				H2
			</button>
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('### ')}
				title="Heading 3"
				disabled={readonly}
			>
				H3
			</button>
		</div>

		<div class="toolbar-divider"></div>

		<div class="toolbar-group">
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('**', '**')}
				title="Bold"
				disabled={readonly}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 4h8a4 4 0 014 4 4 4 0 01-4 4H6z" />
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 12h9a4 4 0 014 4 4 4 0 01-4 4H6z" />
				</svg>
			</button>
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('*', '*')}
				title="Italic"
				disabled={readonly}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 4h4m-2 0l-2 16m-2 0h4" />
				</svg>
			</button>
		</div>

		<div class="toolbar-divider"></div>

		<div class="toolbar-group">
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('- ')}
				title="Bullet list"
				disabled={readonly}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
				</svg>
			</button>
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => insertMarkdown('1. ')}
				title="Numbered list"
				disabled={readonly}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
				</svg>
			</button>
		</div>

		<div class="toolbar-spacer"></div>

		<button
			type="button"
			class="preview-toggle"
			class:active={showPreview}
			onclick={togglePreview}
		>
			{showPreview ? 'Edit' : 'Preview'}
		</button>
	</div>

	<!-- Editor / Preview -->
	<div class="editor-content">
		{#if showPreview}
			<div class="preview-pane prose">
				{@html parseMarkdown($resultsStore.editedSummary)}
			</div>
		{:else}
			<textarea
				bind:this={textareaEl}
				class="editor-textarea"
				value={$resultsStore.editedSummary}
				oninput={handleInput}
				placeholder="Enter meeting summary in Markdown format..."
				{readonly}
				aria-label="Meeting summary editor"
			></textarea>
		{/if}
	</div>

	<!-- Character count -->
	<div class="editor-footer">
		<span class="char-count">
			{$resultsStore.editedSummary?.length || 0} characters
		</span>
	</div>
</div>

<style>
	.summary-editor {
		display: flex;
		flex-direction: column;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		background: white;
		overflow: hidden;
	}

	.editor-toolbar {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.toolbar-group {
		display: flex;
		gap: 0.125rem;
	}

	.toolbar-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 32px;
		height: 32px;
		padding: 0 0.5rem;
		border: none;
		border-radius: 0.25rem;
		background: transparent;
		color: #374151;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.15s;
	}

	.toolbar-btn:hover:not(:disabled) {
		background: #e5e7eb;
	}

	.toolbar-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.toolbar-divider {
		width: 1px;
		height: 20px;
		background: #d1d5db;
		margin: 0 0.25rem;
	}

	.toolbar-spacer {
		flex: 1;
	}

	.preview-toggle {
		padding: 0.375rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.25rem;
		background: white;
		color: #374151;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.preview-toggle:hover {
		background: #f3f4f6;
	}

	.preview-toggle.active {
		background: #dbeafe;
		border-color: #3b82f6;
		color: #1d4ed8;
	}

	.editor-content {
		flex: 1;
		min-height: 300px;
	}

	.editor-textarea {
		width: 100%;
		height: 100%;
		min-height: 300px;
		padding: 1rem;
		border: none;
		resize: vertical;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		font-size: 0.875rem;
		line-height: 1.6;
		color: #111827;
	}

	.editor-textarea:focus {
		outline: none;
	}

	.editor-textarea::placeholder {
		color: #9ca3af;
	}

	.editor-textarea:read-only {
		background: #f9fafb;
		cursor: not-allowed;
	}

	.preview-pane {
		padding: 1rem;
		min-height: 300px;
		font-size: 0.875rem;
		line-height: 1.6;
		color: #111827;
	}

	.preview-pane :global(h1),
	.preview-pane :global(h2),
	.preview-pane :global(h3) {
		color: #111827;
	}

	.preview-pane :global(p) {
		margin-bottom: 0.5rem;
	}

	.preview-pane :global(li) {
		margin-bottom: 0.25rem;
	}

	.preview-pane :global(strong) {
		font-weight: 600;
	}

	.preview-pane :global(em) {
		font-style: italic;
	}

	.editor-footer {
		padding: 0.5rem;
		background: #f9fafb;
		border-top: 1px solid #e5e7eb;
	}

	.char-count {
		font-size: 0.75rem;
		color: #6b7280;
	}
</style>
