<script lang="ts">
	/**
	 * RecordingsList - Display recording files with status and metadata
	 */
	import { Mic, Clock, FileAudio, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-svelte';

	interface Recording {
		id: number;
		original_filename: string | null;
		safe_filename: string;
		status: 'pending' | 'uploaded' | 'processing' | 'completed' | 'failed';
		duration_seconds: number | null;
		file_size_bytes: number | null;
		created_at: string;
		error_message: string | null;
	}

	interface Props {
		recordings: Recording[];
		loading?: boolean;
	}

	let { recordings = [], loading = false }: Props = $props();

	function formatDuration(seconds: number | null): string {
		if (seconds === null || seconds === undefined) return '--:--';
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
	}

	function formatFileSize(bytes: number | null): string {
		if (bytes === null || bytes === undefined) return '-';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString('ko-KR', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusConfig(status: Recording['status']) {
		switch (status) {
			case 'uploaded':
				return { icon: FileAudio, color: 'text-blue-500', bg: 'bg-blue-50', label: '업로드됨' };
			case 'processing':
				return { icon: Loader2, color: 'text-yellow-500', bg: 'bg-yellow-50', label: '처리 중', animate: true };
			case 'completed':
				return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50', label: '완료' };
			case 'failed':
				return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', label: '실패' };
			default:
				return { icon: AlertCircle, color: 'text-gray-400', bg: 'bg-gray-50', label: '대기 중' };
		}
	}
</script>

<div class="recordings-list">
	<div class="header">
		<h3 class="title">
			<Mic class="w-4 h-4" />
			녹음 파일
		</h3>
		{#if recordings.length > 0}
			<span class="count">{recordings.length}개</span>
		{/if}
	</div>

	{#if loading}
		<div class="loading">
			<Loader2 class="w-5 h-5 animate-spin text-gray-400" />
			<span>로딩 중...</span>
		</div>
	{:else if recordings.length === 0}
		<div class="empty">
			<FileAudio class="w-8 h-8 text-gray-300" />
			<p>녹음 파일이 없습니다</p>
		</div>
	{:else}
		<ul class="list">
			{#each recordings as recording (recording.id)}
				{@const config = getStatusConfig(recording.status)}
				<li class="item {config.bg}">
					<div class="item-main">
						<div class="status-icon {config.color}">
							<svelte:component this={config.icon} class="w-5 h-5 {config.animate ? 'animate-spin' : ''}" />
						</div>
						<div class="item-info">
							<div class="item-row">
								<span class="filename">{recording.original_filename || recording.safe_filename || `녹음 ${recording.id}`}</span>
								<span class="status-badge {config.color}">{config.label}</span>
							</div>
							<div class="item-meta">
								<span class="meta-item">
									<Clock class="w-3 h-3" />
									{formatDate(recording.created_at)}
								</span>
								{#if recording.duration_seconds}
									<span class="meta-item">
										{formatDuration(recording.duration_seconds)}
									</span>
								{/if}
								{#if recording.file_size_bytes}
									<span class="meta-item">
										{formatFileSize(recording.file_size_bytes)}
									</span>
								{/if}
							</div>
							{#if recording.error_message}
								<div class="error-msg">
									{recording.error_message}
								</div>
							{/if}
						</div>
					</div>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<style>
	.recordings-list {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 0.5rem;
		overflow: hidden;
	}

	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		background: #f9fafb;
		border-bottom: 1px solid #e5e7eb;
	}

	.title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: #374151;
		margin: 0;
	}

	.count {
		font-size: 0.75rem;
		color: #6b7280;
		background: #e5e7eb;
		padding: 0.125rem 0.5rem;
		border-radius: 9999px;
	}

	.loading, .empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 2rem;
		color: #9ca3af;
		font-size: 0.875rem;
	}

	.list {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.item {
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #f3f4f6;
	}

	.item:last-child {
		border-bottom: none;
	}

	.item-main {
		display: flex;
		align-items: flex-start;
		gap: 0.75rem;
	}

	.status-icon {
		flex-shrink: 0;
		margin-top: 0.125rem;
	}

	.item-info {
		flex: 1;
		min-width: 0;
	}

	.item-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.filename {
		font-size: 0.875rem;
		font-weight: 500;
		color: #111827;
	}

	.status-badge {
		font-size: 0.75rem;
		font-weight: 500;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: 0.25rem;
		flex-wrap: wrap;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: #6b7280;
	}

	.error-msg {
		margin-top: 0.375rem;
		font-size: 0.75rem;
		color: #dc2626;
		background: #fef2f2;
		padding: 0.25rem 0.5rem;
		border-radius: 0.25rem;
	}
</style>
