<script lang="ts">
	import '../app.css';
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import QuickJump from '$lib/components/QuickJump.svelte';
	import SkipLink from '$lib/components/SkipLink.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import UpdateNotifier from '$lib/components/UpdateNotifier.svelte';
	import DebugPanel from '$lib/components/ui/DebugPanel.svelte';
	import { APP_VERSION } from '$lib/version';

	// Public routes that don't require authentication
	const publicRoutes = ['/login'];

	let isRedirecting = false;

	$: isPublicRoute = publicRoutes.includes($page.url.pathname);

	// Redirect to login if not authenticated and not on public route
	$: if (browser && !$auth.isAuthenticated && !isPublicRoute && !isRedirecting) {
		isRedirecting = true;
		goto('/login').finally(() => {
			isRedirecting = false;
		});
	}
</script>

<svelte:head>
	<title>MAX Meeting</title>
	<meta name="description" content="Meeting management application" />
</svelte:head>

<SkipLink />

{#if $auth.isAuthenticated || isPublicRoute}
	<!-- Quick Jump Component (only for authenticated users) -->
	{#if $auth.isAuthenticated}
		<QuickJump />
	{/if}

	<div class="min-h-screen bg-gray-50">
		{#if $auth.isAuthenticated}
			<nav class="bg-white shadow-sm border-b border-gray-200" aria-label="Main navigation">
				<div class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8">
					<div class="flex justify-between h-16">
						<div class="flex items-center">
							<a href="/" class="flex items-center gap-2">
								<img src="/maxmeeting-final.png" alt="" class="h-10 w-auto" />
								<span class="text-xl font-bold text-primary-600">MAX Meeting</span>
								<span class="text-xs text-gray-400 font-normal self-end mb-0.5">v{APP_VERSION}</span>
							</a>
							<div class="hidden md:ml-10 md:flex md:space-x-8">
								<a
									href="/"
									class="inline-flex items-center px-1 pt-1 text-sm font-medium {$page.url
										.pathname === '/'
										? 'text-primary-600 border-b-2 border-primary-600'
										: 'text-gray-500 hover:text-gray-700'}"
								>
									대시보드
								</a>
								<a
									href="/meetings"
									class="inline-flex items-center px-1 pt-1 text-sm font-medium {$page.url.pathname.startsWith(
										'/meetings'
									)
										? 'text-primary-600 border-b-2 border-primary-600'
										: 'text-gray-500 hover:text-gray-700'}"
								>
									회의
								</a>
								<a
									href="/contacts"
									class="inline-flex items-center px-1 pt-1 text-sm font-medium {$page.url.pathname.startsWith(
										'/contacts'
									)
										? 'text-primary-600 border-b-2 border-primary-600'
										: 'text-gray-500 hover:text-gray-700'}"
								>
									연락처
								</a>
							</div>
						</div>
						<div class="flex items-center gap-4">
							<!-- Quick Jump indicator -->
							<button
								type="button"
								class="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-gray-100 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-200 transition-colors cursor-pointer"
								onclick={() => {
									// Trigger Quick Jump
									window.dispatchEvent(
										new KeyboardEvent('keydown', {
											key: 'k',
											metaKey: true,
											ctrlKey: true,
											bubbles: true
										})
									);
								}}
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
									/>
								</svg>
								<span>빠른 이동</span>
								<kbd
									class="px-1.5 py-0.5 bg-white border border-gray-300 rounded text-xs font-mono text-gray-500"
								>
									⌘K
								</kbd>
							</button>

							<button
								type="button"
								class="btn btn-secondary text-sm"
								onclick={() => {
									import('$lib/stores/auth').then(({ logout }) => logout());
									goto('/login');
								}}
							>
								로그아웃
							</button>
						</div>
					</div>
				</div>
			</nav>
		{/if}

		<main id="main-content" class="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8" aria-label="Main content">
			<slot />
		</main>
	</div>
{:else}
	<div class="min-h-screen flex items-center justify-center">
		<div class="animate-pulse text-gray-500">로딩 중...</div>
	</div>
{/if}

<ToastContainer />
<UpdateNotifier />
<DebugPanel />

