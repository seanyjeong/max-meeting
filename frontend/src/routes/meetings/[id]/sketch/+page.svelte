<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import SketchPad from '$lib/components/sketch/SketchPad.svelte';
	import { Breadcrumb, Button, LoadingSpinner } from '$lib/components';
	import { currentMeeting, isLoading } from '$lib/stores/meeting';
	import { sketchStore } from '$lib/stores/sketch';
	import { api } from '$lib/api';
	import type { MeetingDetail } from '$lib/stores/meeting';

	let meetingId = $derived(parseInt($page.params.id ?? '0'));
	let currentAgendaId = $state<number | null>(null);

	// Breadcrumb items
	let breadcrumbItems = $derived([
		{ label: '홈', href: '/' },
		{ label: '회의', href: '/meetings' },
		{
			label: $currentMeeting?.title || '회의',
			href: `/meetings/${meetingId}`
		},
		{ label: '스케치' }
	]);

	onMount(async () => {
		if (!$currentMeeting || $currentMeeting.id !== meetingId) {
			$isLoading = true;
			try {
				const response = await api.get<MeetingDetail>(`/meetings/${meetingId}`);
				$currentMeeting = response;

				// Set first pending/in_progress agenda as current
				const activeAgenda = response.agendas?.find(
					a => a.status === 'in_progress' || a.status === 'pending'
				);
				if (activeAgenda) {
					currentAgendaId = activeAgenda.id;
				}
			} catch {
				goto('/meetings');
			} finally {
				$isLoading = false;
			}
		} else if ($currentMeeting.agendas?.length > 0) {
			const activeAgenda = $currentMeeting.agendas.find(
				a => a.status === 'in_progress' || a.status === 'pending'
			);
			currentAgendaId = activeAgenda?.id ?? $currentMeeting.agendas[0].id;
		}
	});

	onDestroy(() => {
		// Save sketch on page leave
		sketchStore.saveSketch(meetingId);
	});

	function handleAgendaChange(agendaId: number) {
		currentAgendaId = agendaId;
		// Optionally record timestamp when agenda changes
	}

	async function handleSave() {
		await sketchStore.saveSketch(meetingId);
	}

	function handleBack() {
		goto(`/meetings/${meetingId}`);
	}
</script>

<svelte:head>
	<title>스케치 - {$currentMeeting?.title || '회의'} | MAX Meeting</title>
</svelte:head>

<div class="sketch-page">
	{#if $isLoading}
		<div class="loading-container">
			<LoadingSpinner />
			<p>회의 로딩 중...</p>
		</div>
	{:else if $currentMeeting}
		<!-- Header -->
		<header class="page-header">
			<div class="header-left">
				<Breadcrumb items={breadcrumbItems} />
			</div>

			<div class="header-actions">
				{#if $sketchStore.isDirty}
					<span class="unsaved-indicator">저장되지 않은 변경사항</span>
				{/if}

				<Button variant="secondary" size="sm" onclick={handleSave}>
					{#snippet children()}
						<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
						</svg>
						저장
					{/snippet}
				</Button>

				<Button variant="secondary" size="sm" onclick={handleBack}>
					{#snippet children()}
						<svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
						뒤로
					{/snippet}
				</Button>
			</div>
		</header>

		<!-- Main Content -->
		<main class="sketch-content">
			<SketchPad
				{meetingId}
				agendas={$currentMeeting.agendas || []}
				{currentAgendaId}
				onAgendaChange={handleAgendaChange}
			/>
		</main>
	{:else}
		<div class="error-container">
			<p>회의를 찾을 수 없습니다</p>
			<Button variant="primary" onclick={() => goto('/meetings')}>
				{#snippet children()}회의 목록으로{/snippet}
			</Button>
		</div>
	{/if}
</div>

<style>
	.sketch-page {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 64px); /* Account for main nav */
		margin: -2rem; /* Override main padding */
	}

	.loading-container,
	.error-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 1rem;
		color: #6b7280;
	}

	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		background: white;
		border-bottom: 1px solid #e5e7eb;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.unsaved-indicator {
		padding: 0.25rem 0.5rem;
		background: #fef3c7;
		color: #d97706;
		font-size: 0.75rem;
		border-radius: 9999px;
	}

	.sketch-content {
		flex: 1;
		overflow: hidden;
	}
</style>
