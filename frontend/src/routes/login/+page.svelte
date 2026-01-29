<script lang="ts">
	import { auth } from '$lib/stores/auth';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_URL } from '$env/static/public';

	const API_BASE = PUBLIC_API_URL || '/api/v1';

	let password = '';
	let error = '';
	let isLoading = false;

	async function handleSubmit() {
		error = '';
		isLoading = true;

		try {
			const response = await fetch(`${API_BASE}/auth/login`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ password })
			});

			if (!response.ok) {
				const data = await response.json();
				error = data.error?.message || '로그인 실패';
				return;
			}

			const data = await response.json();

			// Store tokens 먼저 저장 (redirect 전에)
			localStorage.setItem('accessToken', data.access_token);
			localStorage.setItem('refreshToken', data.refresh_token);

			// 저장 확인 로그
			if (import.meta.env.DEV) {
				console.log('[LOGIN] Token stored:', {
					accessToken: localStorage.getItem('accessToken') ? 'EXISTS' : 'MISSING',
					refreshToken: localStorage.getItem('refreshToken') ? 'EXISTS' : 'MISSING'
				});
			}

			// Svelte store 업데이트
			auth.set({
				isAuthenticated: true,
				accessToken: data.access_token,
				refreshToken: data.refresh_token
			});

			// 저장 완료 후 redirect
			goto('/');
		} catch (err) {
			error = '네트워크 오류. 다시 시도하세요.';
			console.error('Login error:', err);
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>로그인 - MAX Meeting</title>
</svelte:head>

<div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
	<div class="max-w-md w-full space-y-8">
		<div>
			<h1 class="text-center text-3xl font-extrabold text-gray-900">
				MAX Meeting
			</h1>
			<p class="mt-2 text-center text-sm text-gray-600">
				비밀번호를 입력하세요
			</p>
		</div>

		<form class="mt-8 space-y-6" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
			{#if error}
				<div class="rounded-md bg-red-50 p-4" role="alert">
					<div class="flex">
						<div class="flex-shrink-0">
							<svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
								<path
									fill-rule="evenodd"
									d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
						<div class="ml-3">
							<p class="text-sm font-medium text-red-800">{error}</p>
						</div>
					</div>
				</div>
			{/if}

			<div>
				<label for="password" class="sr-only">비밀번호</label>
				<input
					id="password"
					name="password"
					type="password"
					required
					bind:value={password}
					class="input text-lg py-3"
					placeholder="비밀번호"
					autocomplete="current-password"
				/>
			</div>

			<div>
				<button
					type="submit"
					disabled={isLoading || !password}
					class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if isLoading}
						<svg
							class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
						>
							<circle
								class="opacity-25"
								cx="12"
								cy="12"
								r="10"
								stroke="currentColor"
								stroke-width="4"
							></circle>
							<path
								class="opacity-75"
								fill="currentColor"
								d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
							></path>
						</svg>
						로그인 중...
					{:else}
						로그인
					{/if}
				</button>
			</div>
		</form>
	</div>
</div>
