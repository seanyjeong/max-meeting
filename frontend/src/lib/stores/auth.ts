/**
 * Auth Store - Authentication state management
 */
import { writable } from 'svelte/store';

interface AuthState {
	isAuthenticated: boolean;
	accessToken: string | null;
	refreshToken: string | null;
}

// localStorage에서 토큰을 확인하여 초기 상태 설정 (브라우저 환경에서만)
function getInitialState(): AuthState {
	if (typeof window !== 'undefined') {
		const accessToken = localStorage.getItem('accessToken');
		const refreshToken = localStorage.getItem('refreshToken');

		if (accessToken) {
			console.log('[AUTH_STORE] Restored auth state from localStorage');
			return {
				isAuthenticated: true,
				accessToken,
				refreshToken
			};
		}
	}

	return {
		isAuthenticated: false,
		accessToken: null,
		refreshToken: null
	};
}

const initialState = getInitialState();

export const auth = writable<AuthState>(initialState);

export function logout(): void {
	auth.set(initialState);
	if (typeof localStorage !== 'undefined') {
		localStorage.removeItem('accessToken');
		localStorage.removeItem('refreshToken');
	}
}

export async function refreshToken(): Promise<boolean> {
	if (typeof window === 'undefined') {
		return false;
	}

	const currentRefreshToken = localStorage.getItem('refreshToken');
	if (!currentRefreshToken) {
		logout();
		return false;
	}

	try {
		const response = await fetch('/api/v1/auth/refresh', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${currentRefreshToken}`
			}
		});

		if (!response.ok) {
			logout();
			return false;
		}

		const data = await response.json();
		localStorage.setItem('accessToken', data.access_token);
		localStorage.setItem('refreshToken', data.refresh_token);

		auth.set({
			isAuthenticated: true,
			accessToken: data.access_token,
			refreshToken: data.refresh_token
		});

		return true;
	} catch {
		logout();
		return false;
	}
}
