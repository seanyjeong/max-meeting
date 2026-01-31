<script lang="ts">
	import { sketchStore } from '$lib/stores/sketch';
	import { exportToPng, exportToPdf, downloadBlob } from '$lib/utils/sketch-export';

	interface Props {
		onUndo?: () => void;
		onRedo?: () => void;
		onClear?: () => void;
		onExportPng?: () => Promise<SVGElement | null>;
		onExportPdf?: () => Promise<SVGElement | null>;
		disabled?: boolean;
	}

	let {
		onUndo,
		onRedo,
		onClear,
		onExportPng,
		onExportPdf,
		disabled = false
	}: Props = $props();

	let showSecondary = $state(false);

	const tools = [
		{ id: 'draw', icon: 'pen', label: 'Pen' },
		{ id: 'eraser', icon: 'eraser', label: 'Eraser' }
	] as const;

	const colors = [
		{ id: 'black', value: sketchStore.COLORS.black, label: 'Black' },
		{ id: 'red', value: sketchStore.COLORS.red, label: 'Red' },
		{ id: 'blue', value: sketchStore.COLORS.blue, label: 'Blue' },
		{ id: 'green', value: sketchStore.COLORS.green, label: 'Green' }
	];

	const highlighters = [
		{ id: 'highlightYellow', value: sketchStore.COLORS.highlightYellow, label: 'Yellow Highlight' },
		{ id: 'highlightGreen', value: sketchStore.COLORS.highlightGreen, label: 'Green Highlight' },
		{ id: 'highlightPink', value: sketchStore.COLORS.highlightPink, label: 'Pink Highlight' }
	];

	const strokeWidths = [
		{ id: 'thin', value: sketchStore.STROKE_WIDTHS.thin, label: '1px' },
		{ id: 'medium', value: sketchStore.STROKE_WIDTHS.medium, label: '2px' },
		{ id: 'thick', value: sketchStore.STROKE_WIDTHS.thick, label: '4px' },
		{ id: 'extraThick', value: sketchStore.STROKE_WIDTHS.extraThick, label: '8px' }
	];

	function selectTool(tool: 'draw' | 'eraser') {
		sketchStore.setTool(tool);
	}

	function selectColor(color: string) {
		sketchStore.setColor(color);
	}

	function selectStrokeWidth(width: number) {
		sketchStore.setStrokeWidth(width);
	}

	function toggleSecondary() {
		showSecondary = !showSecondary;
	}

	async function handleExportPng() {
		if (!onExportPng) return;

		try {
			const svgElement = await onExportPng();
			if (!svgElement) {
				alert('스케치를 내보낼 수 없습니다');
				return;
			}

			const blob = await exportToPng(svgElement);
			downloadBlob(blob, `sketch-${Date.now()}.png`);
		} catch {
			alert('PNG 내보내기 중 오류가 발생했습니다');
		}
	}

	async function handleExportPdf() {
		if (!onExportPdf) return;

		try {
			const svgElement = await onExportPdf();
			if (!svgElement) {
				alert('스케치를 내보낼 수 없습니다');
				return;
			}

			await exportToPdf(svgElement, `sketch-${Date.now()}.pdf`);
		} catch {
			alert('PDF 내보내기 중 오류가 발생했습니다');
		}
	}

	// Icons as SVG paths
	const icons = {
		pen: 'M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z',
		eraser: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
		undo: 'M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3',
		redo: 'M15 15l6-6m0 0l-6-6m6 6H9a6 6 0 000 12h3',
		more: 'M6.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM12.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0zM18.75 12a.75.75 0 11-1.5 0 .75.75 0 011.5 0z',
		trash: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
		download: 'M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3'
	};
</script>

<div class="sketch-toolbar" class:disabled>
	<!-- Primary Toolbar -->
	<div class="toolbar-primary">
		<!-- Drawing Tools -->
		<div class="tool-group">
			{#each tools as tool}
				<button
					type="button"
					class="tool-btn"
					class:active={$sketchStore.currentTool === tool.id}
					onclick={() => selectTool(tool.id)}
					title={tool.label}
					{disabled}
					aria-label={tool.label}
					aria-pressed={$sketchStore.currentTool === tool.id}
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons[tool.icon]} />
					</svg>
				</button>
			{/each}
		</div>

		<div class="divider" aria-hidden="true"></div>

		<!-- Undo/Redo -->
		<div class="tool-group">
			<button
				type="button"
				class="tool-btn"
				onclick={onUndo}
				title="Undo (Cmd+Z)"
				{disabled}
				aria-label="Undo"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.undo} />
				</svg>
			</button>
			<button
				type="button"
				class="tool-btn"
				onclick={onRedo}
				title="Redo (Cmd+Shift+Z)"
				{disabled}
				aria-label="Redo"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.redo} />
				</svg>
			</button>
		</div>

		<div class="divider" aria-hidden="true"></div>

		<!-- More Options -->
		<button
			type="button"
			class="tool-btn"
			class:active={showSecondary}
			onclick={toggleSecondary}
			title="More options"
			{disabled}
			aria-label="More options"
			aria-expanded={showSecondary}
		>
			<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.more} />
			</svg>
		</button>
	</div>

	<!-- Secondary Toolbar (Color/Stroke) -->
	{#if showSecondary}
		<div class="toolbar-secondary">
			<!-- Colors -->
			<div class="color-section">
				<span class="section-label">Colors</span>
				<div class="color-palette">
					{#each colors as color}
						<button
							type="button"
							class="color-btn"
							class:active={$sketchStore.currentColor === color.value}
							style="background-color: {color.value};"
							onclick={() => selectColor(color.value)}
							title={color.label}
							{disabled}
							aria-label={color.label}
							aria-pressed={$sketchStore.currentColor === color.value}
						></button>
					{/each}
				</div>
			</div>

			<!-- Highlighters -->
			<div class="color-section">
				<span class="section-label">Highlighters</span>
				<div class="color-palette">
					{#each highlighters as hl}
						<button
							type="button"
							class="color-btn highlighter"
							class:active={$sketchStore.currentColor === hl.value}
							style="background-color: {hl.value};"
							onclick={() => selectColor(hl.value)}
							title={hl.label}
							{disabled}
							aria-label={hl.label}
							aria-pressed={$sketchStore.currentColor === hl.value}
						></button>
					{/each}
				</div>
			</div>

			<!-- Stroke Width -->
			<div class="stroke-section">
				<span class="section-label">Stroke Width</span>
				<div class="stroke-options">
					{#each strokeWidths as sw}
						<button
							type="button"
							class="stroke-btn"
							class:active={$sketchStore.strokeWidth === sw.value}
							onclick={() => selectStrokeWidth(sw.value)}
							title={sw.label}
							{disabled}
							aria-label={sw.label}
							aria-pressed={$sketchStore.strokeWidth === sw.value}
						>
							<div
								class="stroke-preview"
								style="height: {sw.value}px; background-color: {$sketchStore.currentColor};"
							></div>
						</button>
					{/each}
				</div>
			</div>

			<!-- Export & Clear -->
			<div class="actions-section">
				<button
					type="button"
					class="export-btn"
					onclick={handleExportPng}
					title="Export as PNG"
					{disabled}
				>
					<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.download} />
					</svg>
					PNG
				</button>
				<button
					type="button"
					class="export-btn"
					onclick={handleExportPdf}
					title="Export as PDF"
					{disabled}
				>
					<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.download} />
					</svg>
					PDF
				</button>
				<button
					type="button"
					class="clear-btn"
					onclick={onClear}
					title="Clear all"
					{disabled}
				>
					<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={icons.trash} />
					</svg>
					Clear All
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	.sketch-toolbar {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.sketch-toolbar.disabled {
		opacity: 0.5;
		pointer-events: none;
	}

	.toolbar-primary {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem;
		background: white;
		border-radius: 0.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.toolbar-secondary {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		padding: 0.75rem;
		background: white;
		border-radius: 0.5rem;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}

	.tool-group {
		display: flex;
		gap: 0.25rem;
	}

	.tool-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		padding: 0.5rem;
		border: none;
		border-radius: 0.375rem;
		background: transparent;
		color: #374151;
		cursor: pointer;
		transition: all 0.15s;
	}

	.tool-btn:hover:not(:disabled) {
		background: #f3f4f6;
	}

	.tool-btn.active {
		background: #dbeafe;
		color: #1d4ed8;
	}

	.tool-btn:focus-visible {
		outline: 2px solid #1d4ed8;
		outline-offset: 2px;
	}

	.divider {
		width: 1px;
		height: 24px;
		background: #e5e7eb;
		margin: 0 0.25rem;
	}

	.section-label {
		display: block;
		font-size: 0.75rem;
		font-weight: 500;
		color: #6b7280;
		margin-bottom: 0.375rem;
	}

	.color-section,
	.stroke-section {
		display: flex;
		flex-direction: column;
	}

	.color-palette {
		display: flex;
		gap: 0.375rem;
	}

	.color-btn {
		width: 32px;
		height: 32px;
		border: 2px solid transparent;
		border-radius: 0.375rem;
		cursor: pointer;
		transition: all 0.15s;
	}

	.color-btn:hover:not(:disabled) {
		transform: scale(1.1);
	}

	.color-btn.active {
		border-color: #1d4ed8;
		box-shadow: 0 0 0 2px rgba(29, 78, 216, 0.3);
	}

	.color-btn.highlighter {
		border: 1px solid #d1d5db;
	}

	.stroke-options {
		display: flex;
		gap: 0.375rem;
	}

	.stroke-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 32px;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		background: white;
		cursor: pointer;
		transition: all 0.15s;
	}

	.stroke-btn:hover:not(:disabled) {
		border-color: #9ca3af;
	}

	.stroke-btn.active {
		border-color: #1d4ed8;
		background: #eff6ff;
	}

	.stroke-preview {
		width: 24px;
		border-radius: 2px;
	}

	.actions-section {
		margin-left: auto;
		display: flex;
		gap: 0.5rem;
	}

	.export-btn {
		display: flex;
		align-items: center;
		padding: 0.5rem 1rem;
		border: 1px solid #1d4ed8;
		border-radius: 0.375rem;
		background: white;
		color: #1d4ed8;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.export-btn:hover:not(:disabled) {
		background: #eff6ff;
	}

	.clear-btn {
		display: flex;
		align-items: center;
		padding: 0.5rem 1rem;
		border: 1px solid #dc2626;
		border-radius: 0.375rem;
		background: white;
		color: #dc2626;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
		transition: all 0.15s;
	}

	.clear-btn:hover:not(:disabled) {
		background: #fef2f2;
	}

	/* Tablet-friendly touch targets */
	@media (pointer: coarse) {
		.tool-btn {
			width: 48px;
			height: 48px;
		}

		.color-btn {
			width: 40px;
			height: 40px;
		}

		.stroke-btn {
			width: 48px;
			height: 40px;
		}
	}
</style>
