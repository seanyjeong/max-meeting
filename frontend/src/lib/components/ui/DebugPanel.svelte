<script lang="ts">
	/**
	 * DebugPanel - On-screen debug console for mobile/tablet debugging
	 *
	 * Features:
	 * - Captures console.log, console.error, console.warn
	 * - Shows API request/response logs
	 * - Toggleable via floating button
	 * - Persists logs during session
	 */
	import { onMount, onDestroy } from 'svelte';
	import { Bug, X, Trash2, ChevronDown, ChevronUp } from 'lucide-svelte';
	import { browser } from '$app/environment';

	interface LogEntry {
		id: number;
		type: 'log' | 'error' | 'warn' | 'info' | 'api';
		message: string;
		timestamp: Date;
		details?: string;
	}

	let isOpen = $state(false);
	let isMinimized = $state(false);
	let logs = $state<LogEntry[]>([]);
	let logId = 0;

	// Store original console methods
	let originalLog: typeof console.log;
	let originalError: typeof console.error;
	let originalWarn: typeof console.warn;
	let originalInfo: typeof console.info;

	function addLog(type: LogEntry['type'], ...args: unknown[]) {
		const message = args.map(arg => {
			if (typeof arg === 'object') {
				try {
					return JSON.stringify(arg, null, 2);
				} catch {
					return String(arg);
				}
			}
			return String(arg);
		}).join(' ');

		logs = [...logs.slice(-99), {
			id: logId++,
			type,
			message: message.slice(0, 500),
			timestamp: new Date(),
			details: message.length > 500 ? message : undefined
		}];
	}

	onMount(() => {
		if (!browser) return;

		// Save original methods
		originalLog = console.log;
		originalError = console.error;
		originalWarn = console.warn;
		originalInfo = console.info;

		// Override console methods
		console.log = (...args: unknown[]) => {
			originalLog.apply(console, args);
			addLog('log', ...args);
		};

		console.error = (...args: unknown[]) => {
			originalError.apply(console, args);
			addLog('error', ...args);
		};

		console.warn = (...args: unknown[]) => {
			originalWarn.apply(console, args);
			addLog('warn', ...args);
		};

		console.info = (...args: unknown[]) => {
			originalInfo.apply(console, args);
			addLog('info', ...args);
		};

		// Initial log
		addLog('info', '[DebugPanel] Initialized');
	});

	onDestroy(() => {
		if (!browser) return;

		// Restore original methods
		if (originalLog) console.log = originalLog;
		if (originalError) console.error = originalError;
		if (originalWarn) console.warn = originalWarn;
		if (originalInfo) console.info = originalInfo;
	});

	function clearLogs() {
		logs = [];
		addLog('info', '[DebugPanel] Logs cleared');
	}

	function getTypeColor(type: LogEntry['type']) {
		switch (type) {
			case 'error': return 'text-red-400 bg-red-900/30';
			case 'warn': return 'text-yellow-400 bg-yellow-900/30';
			case 'info': return 'text-blue-400 bg-blue-900/30';
			case 'api': return 'text-purple-400 bg-purple-900/30';
			default: return 'text-gray-300 bg-gray-800/50';
		}
	}

	function formatTime(date: Date) {
		return date.toLocaleTimeString('ko-KR', { hour12: false });
	}

	// Export function for external use
	export function logApi(method: string, url: string, status?: number, data?: unknown) {
		addLog('api', `[${method}] ${url}${status ? ` → ${status}` : ''}`, data ? JSON.stringify(data).slice(0, 200) : '');
	}
</script>

{#if browser}
<div class="no-print">
	<!-- Toggle Button (always visible) -->
	<button
		type="button"
		class="debug-toggle"
		class:has-errors={logs.some(l => l.type === 'error')}
		onclick={() => isOpen = !isOpen}
		aria-label="디버그 패널 토글"
	>
		<Bug class="w-5 h-5" />
		{#if logs.filter(l => l.type === 'error').length > 0}
			<span class="error-badge">{logs.filter(l => l.type === 'error').length}</span>
		{/if}
	</button>

	<!-- Debug Panel -->
	{#if isOpen}
		<div class="debug-panel" class:minimized={isMinimized}>
			<!-- Header -->
			<div class="panel-header">
				<div class="header-left">
					<Bug class="w-4 h-4" />
					<span>Debug Console</span>
					<span class="log-count">{logs.length}</span>
				</div>
				<div class="header-actions">
					<button type="button" onclick={clearLogs} title="Clear logs">
						<Trash2 class="w-4 h-4" />
					</button>
					<button type="button" onclick={() => isMinimized = !isMinimized} title={isMinimized ? 'Expand' : 'Minimize'}>
						{#if isMinimized}
							<ChevronUp class="w-4 h-4" />
						{:else}
							<ChevronDown class="w-4 h-4" />
						{/if}
					</button>
					<button type="button" onclick={() => isOpen = false} title="Close">
						<X class="w-4 h-4" />
					</button>
				</div>
			</div>

			<!-- Logs -->
			{#if !isMinimized}
				<div class="logs-container">
					{#if logs.length === 0}
						<div class="empty-logs">No logs yet</div>
					{:else}
						{#each logs as log (log.id)}
							<div class="log-entry {getTypeColor(log.type)}">
								<span class="log-time">{formatTime(log.timestamp)}</span>
								<span class="log-type">[{log.type.toUpperCase()}]</span>
								<span class="log-message">{log.message}</span>
							</div>
						{/each}
					{/if}
				</div>
			{/if}
		</div>
	{/if}
</div>
{/if}

<style>
	.debug-toggle {
		position: fixed;
		bottom: 1rem;
		right: 1rem;
		z-index: 9999;
		width: 48px;
		height: 48px;
		border-radius: 50%;
		background: #1f2937;
		color: #9ca3af;
		border: 2px solid #374151;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
		transition: all 0.2s;
	}

	.debug-toggle:hover {
		background: #374151;
		color: white;
	}

	.debug-toggle.has-errors {
		border-color: #ef4444;
		color: #ef4444;
	}

	.error-badge {
		position: absolute;
		top: -4px;
		right: -4px;
		min-width: 18px;
		height: 18px;
		padding: 0 4px;
		background: #ef4444;
		color: white;
		font-size: 10px;
		font-weight: bold;
		border-radius: 9999px;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.debug-panel {
		position: fixed;
		bottom: 5rem;
		right: 1rem;
		z-index: 9998;
		width: min(400px, calc(100vw - 2rem));
		max-height: 50vh;
		background: #111827;
		border: 1px solid #374151;
		border-radius: 0.5rem;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
		display: flex;
		flex-direction: column;
		font-family: ui-monospace, monospace;
		font-size: 11px;
	}

	.debug-panel.minimized {
		max-height: auto;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.75rem;
		background: #1f2937;
		border-bottom: 1px solid #374151;
		border-radius: 0.5rem 0.5rem 0 0;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: #9ca3af;
		font-weight: 600;
	}

	.log-count {
		background: #374151;
		padding: 0 0.375rem;
		border-radius: 9999px;
		font-size: 10px;
	}

	.header-actions {
		display: flex;
		gap: 0.25rem;
	}

	.header-actions button {
		padding: 0.25rem;
		background: transparent;
		border: none;
		color: #6b7280;
		cursor: pointer;
		border-radius: 0.25rem;
	}

	.header-actions button:hover {
		background: #374151;
		color: white;
	}

	.logs-container {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.empty-logs {
		color: #6b7280;
		text-align: center;
		padding: 2rem;
	}

	.log-entry {
		display: flex;
		gap: 0.5rem;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
		line-height: 1.4;
		word-break: break-all;
	}

	.log-time {
		flex-shrink: 0;
		color: #6b7280;
	}

	.log-type {
		flex-shrink: 0;
		font-weight: 600;
	}

	.log-message {
		flex: 1;
		white-space: pre-wrap;
	}

	/* Touch friendly */
	@media (pointer: coarse) {
		.debug-toggle {
			width: 56px;
			height: 56px;
		}

		.debug-panel {
			bottom: 6rem;
			font-size: 12px;
		}
	}
</style>
