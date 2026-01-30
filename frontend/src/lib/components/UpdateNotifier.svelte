<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { APP_VERSION } from '$lib/version';
	import { RefreshCw, X } from 'lucide-svelte';

	let showUpdateBanner = $state(false);
	let checkInterval: ReturnType<typeof setInterval> | null = null;

	// Check for updates every 5 minutes
	const CHECK_INTERVAL = 5 * 60 * 1000;

	async function checkForUpdates() {
		try {
			// Fetch version.json with cache-busting
			const response = await fetch(`/version.json?t=${Date.now()}`, {
				cache: 'no-store'
			});

			if (response.ok) {
				const data = await response.json();
				if (data.version && data.version !== APP_VERSION) {
					showUpdateBanner = true;
				}
			}
		} catch (error) {
			// Silently fail - version check is optional
			console.debug('Version check failed:', error);
		}
	}

	function handleUpdate() {
		// Force reload to get new version
		window.location.reload();
	}

	function dismissBanner() {
		showUpdateBanner = false;
		// Don't show again for this session
		sessionStorage.setItem('update-dismissed', APP_VERSION);
	}

	onMount(() => {
		// Don't show if already dismissed this session
		const dismissed = sessionStorage.getItem('update-dismissed');
		if (dismissed === APP_VERSION) {
			return;
		}

		// Initial check after a short delay
		setTimeout(checkForUpdates, 3000);

		// Periodic checks
		checkInterval = setInterval(checkForUpdates, CHECK_INTERVAL);

		// Also check when tab becomes visible
		document.addEventListener('visibilitychange', () => {
			if (document.visibilityState === 'visible') {
				checkForUpdates();
			}
		});
	});

	onDestroy(() => {
		if (checkInterval) {
			clearInterval(checkInterval);
		}
	});
</script>

{#if showUpdateBanner}
	<div class="update-banner" role="alert">
		<div class="update-content">
			<RefreshCw class="w-5 h-5 animate-spin-slow" />
			<span>새 버전이 있습니다!</span>
			<button class="update-btn" onclick={handleUpdate}>
				업데이트
			</button>
		</div>
		<button class="close-btn" onclick={dismissBanner} aria-label="닫기">
			<X class="w-4 h-4" />
		</button>
	</div>
{/if}

<style>
	.update-banner {
		position: fixed;
		bottom: 1rem;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem 1rem;
		background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
		color: white;
		border-radius: 0.75rem;
		box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
		z-index: 9999;
		animation: slideUp 0.3s ease-out;
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(1rem);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}

	.update-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.update-btn {
		padding: 0.375rem 0.75rem;
		background: white;
		color: #2563eb;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.15s;
	}

	.update-btn:hover {
		background: #f0f9ff;
	}

	.close-btn {
		padding: 0.25rem;
		background: transparent;
		border: none;
		color: white;
		opacity: 0.7;
		cursor: pointer;
		transition: opacity 0.15s;
	}

	.close-btn:hover {
		opacity: 1;
	}

	:global(.animate-spin-slow) {
		animation: spin 2s linear infinite;
	}

	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}
</style>
