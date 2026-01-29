<script lang="ts">
	import { onMount } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	export let meetingId: number;
	export let onComplete: (() => void) | undefined = undefined;

	const dispatch = createEventDispatcher<{
		complete: void;
		skip: void;
	}>();

	interface CheckItem {
		id: string;
		label: string;
		status: 'pending' | 'checking' | 'success' | 'warning' | 'error';
		message: string;
	}

	let checks: CheckItem[] = [
		{ id: 'agendas', label: '안건 캐싱', status: 'pending', message: '확인 대기...' },
		{ id: 'contacts', label: '연락처 동기화', status: 'pending', message: '확인 대기...' },
		{ id: 'storage', label: '저장 공간', status: 'pending', message: '확인 대기...' },
		{ id: 'battery', label: '배터리', status: 'pending', message: '확인 대기...' },
		{ id: 'microphone', label: '마이크 권한', status: 'pending', message: '확인 대기...' },
	];

	let allChecksComplete = false;
	let hasErrors = false;

	function updateCheck(id: string, update: Partial<CheckItem>) {
		checks = checks.map((c) => (c.id === id ? { ...c, ...update } : c));
	}

	async function runChecks() {
		// Check agendas cached
		updateCheck('agendas', { status: 'checking', message: '안건 캐싱 확인 중...' });
		try {
			const agendaCache = await caches.match(`/api/v1/meetings/${meetingId}/agendas`);
			if (agendaCache) {
				updateCheck('agendas', { status: 'success', message: '안건 캐싱 완료' });
			} else {
				// Try to fetch and cache
				const response = await fetch(`/api/v1/meetings/${meetingId}/agendas`);
				if (response.ok) {
					const cache = await caches.open('api-cache');
					await cache.put(`/api/v1/meetings/${meetingId}/agendas`, response);
					updateCheck('agendas', { status: 'success', message: '안건 캐싱 완료' });
				} else {
					updateCheck('agendas', {
						status: 'warning',
						message: '오프라인 시 안건 로드 불가'
					});
				}
			}
		} catch {
			updateCheck('agendas', { status: 'warning', message: '캐싱 확인 실패' });
		}

		// Check contacts
		updateCheck('contacts', { status: 'checking', message: '연락처 동기화 확인 중...' });
		try {
			const contactCache = await caches.match('/api/v1/contacts');
			if (contactCache) {
				updateCheck('contacts', { status: 'success', message: '연락처 동기화 완료' });
			} else {
				updateCheck('contacts', { status: 'warning', message: '오프라인 시 연락처 미사용' });
			}
		} catch {
			updateCheck('contacts', { status: 'warning', message: '연락처 확인 실패' });
		}

		// Check storage
		updateCheck('storage', { status: 'checking', message: '저장 공간 확인 중...' });
		try {
			if ('storage' in navigator && 'estimate' in navigator.storage) {
				const estimate = await navigator.storage.estimate();
				const usedGB = ((estimate.usage ?? 0) / 1024 ** 3).toFixed(2);
				const quotaGB = ((estimate.quota ?? 0) / 1024 ** 3).toFixed(1);
				const freeGB = (((estimate.quota ?? 0) - (estimate.usage ?? 0)) / 1024 ** 3).toFixed(1);

				if (parseFloat(freeGB) > 1) {
					updateCheck('storage', { status: 'success', message: `${freeGB}GB 여유` });
				} else if (parseFloat(freeGB) > 0.1) {
					updateCheck('storage', {
						status: 'warning',
						message: `${freeGB}GB 여유 - 장시간 녹음 주의`
					});
				} else {
					updateCheck('storage', { status: 'error', message: '저장 공간 부족' });
				}
			} else {
				updateCheck('storage', { status: 'warning', message: '저장 공간 확인 불가' });
			}
		} catch {
			updateCheck('storage', { status: 'warning', message: '저장 공간 확인 실패' });
		}

		// Check battery
		updateCheck('battery', { status: 'checking', message: '배터리 확인 중...' });
		try {
			if ('getBattery' in navigator) {
				// @ts-ignore - getBattery is not in standard types
				const battery = await navigator.getBattery();
				const level = Math.round(battery.level * 100);

				if (battery.charging) {
					updateCheck('battery', { status: 'success', message: `${level}% (충전 중)` });
				} else if (level > 30) {
					updateCheck('battery', { status: 'success', message: `${level}%` });
				} else if (level > 15) {
					updateCheck('battery', { status: 'warning', message: `${level}% - 충전 권장` });
				} else {
					updateCheck('battery', { status: 'error', message: `${level}% - 충전 필요` });
				}
			} else {
				updateCheck('battery', { status: 'success', message: '배터리 정보 없음 (PC)' });
			}
		} catch {
			updateCheck('battery', { status: 'warning', message: '배터리 확인 불가' });
		}

		// Check microphone permission
		updateCheck('microphone', { status: 'checking', message: '마이크 권한 확인 중...' });
		try {
			const permissionStatus = await navigator.permissions.query({
				name: 'microphone' as PermissionName
			});

			if (permissionStatus.state === 'granted') {
				updateCheck('microphone', { status: 'success', message: '마이크 권한 허용됨' });
			} else if (permissionStatus.state === 'prompt') {
				updateCheck('microphone', {
					status: 'warning',
					message: '마이크 권한 요청 예정'
				});
			} else {
				updateCheck('microphone', { status: 'error', message: '마이크 권한 거부됨' });
			}
		} catch {
			// Fallback: try to get user media
			try {
				const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
				stream.getTracks().forEach((t) => t.stop());
				updateCheck('microphone', { status: 'success', message: '마이크 접근 가능' });
			} catch {
				updateCheck('microphone', { status: 'error', message: '마이크 접근 불가' });
			}
		}

		// Update overall status
		allChecksComplete = true;
		hasErrors = checks.some((c) => c.status === 'error');
	}

	function handleComplete() {
		dispatch('complete');
		onComplete?.();
	}

	function handleSkip() {
		dispatch('skip');
		onComplete?.();
	}

	function getStatusIcon(status: string) {
		switch (status) {
			case 'success':
				return { icon: '✓', class: 'text-green-500' };
			case 'warning':
				return { icon: '⚠', class: 'text-yellow-500' };
			case 'error':
				return { icon: '✕', class: 'text-red-500' };
			case 'checking':
				return { icon: '⟳', class: 'text-blue-500 animate-spin' };
			default:
				return { icon: '○', class: 'text-gray-400' };
		}
	}

	onMount(() => {
		runChecks();
	});
</script>

<div class="bg-white border border-gray-200 rounded-lg shadow-sm p-6 max-w-md mx-auto">
	<h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
		<svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				stroke-width="2"
				d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
			/>
		</svg>
		회의 전 점검
	</h3>

	<div class="space-y-3">
		{#each checks as check (check.id)}
			{@const statusInfo = getStatusIcon(check.status)}
			<div class="flex items-center gap-3 py-2 border-b border-gray-100 last:border-0">
				<span class="text-lg {statusInfo.class}">
					{statusInfo.icon}
				</span>
				<div class="flex-1">
					<span class="text-sm font-medium text-gray-700">{check.label}</span>
					<p class="text-xs text-gray-500">{check.message}</p>
				</div>
			</div>
		{/each}
	</div>

	{#if allChecksComplete}
		<div class="mt-6 space-y-3">
			{#if hasErrors}
				<div class="p-3 bg-red-50 border border-red-200 rounded-lg">
					<p class="text-sm text-red-800">
						일부 항목에서 문제가 발생했습니다. 확인 후 진행하세요.
					</p>
				</div>
			{/if}

			<div class="flex gap-3">
				<button
					type="button"
					onclick={handleSkip}
					class="flex-1 py-2 px-4 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
				>
					건너뛰기
				</button>
				<button
					type="button"
					onclick={handleComplete}
					class="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors {hasErrors ? 'opacity-75' : ''}"
				>
					{hasErrors ? '문제 확인 후 진행' : '회의 시작'}
				</button>
			</div>
		</div>
	{:else}
		<div class="mt-6">
			<div class="animate-pulse flex items-center justify-center gap-2 py-3">
				<div class="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
				<span class="text-sm text-gray-600">점검 진행 중...</span>
			</div>
		</div>
	{/if}
</div>
