/**
 * API Client - Minimal implementation for GET request
 */

import { PUBLIC_API_URL } from '$env/static/public';
import { refreshToken } from './stores/auth';
import { goto } from '$app/navigation';

const API_BASE = PUBLIC_API_URL || '/api/v1';

interface UploadInitResponse {
	upload_id: string;
	recording_id: number;
	upload_url: string;
	max_chunk_size: number;
}

interface UploadProgressResponse {
	upload_id: string;
	bytes_received: number;
	total_bytes: number | null;
	is_complete: boolean;
}

class ApiClient {
	private static instance: ApiClient;

	static getInstance(): ApiClient {
		if (!ApiClient.instance) {
			ApiClient.instance = new ApiClient();
		}
		return ApiClient.instance;
	}

	private getHeaders(): Record<string, string> {
		const headers: Record<string, string> = {
			'Content-Type': 'application/json'
		};

		// localStorage에서 access token 가져오기 (브라우저 환경에서만)
		if (typeof window !== 'undefined') {
			const token = localStorage.getItem('accessToken');
			if (token) {
				headers['Authorization'] = `Bearer ${token}`;
				console.log('[API] Authorization header added');
			} else {
				console.warn('[API] No access token found in localStorage');
			}
		} else {
			console.warn('[API] SSR environment - no access token available');
		}

		return headers;
	}

	private async fetchWithAuth<T>(
		url: string,
		options: RequestInit
	): Promise<T> {
		let response: Response;
		console.log('[API] Request:', options.method, url);

		try {
			response = await fetch(url, options);
		} catch (networkError) {
			// 네트워크 오류 (서버 다운, CORS, 오프라인 등)
			console.error('[API] Network error:', networkError);
			throw new ApiError('NETWORK_ERROR', '서버에 연결할 수 없습니다', 0);
		}

		console.log('[API] Response status:', response.status);

		// Handle 401 Unauthorized
		if (response.status === 401) {
			console.log('[API] 401 received, attempting token refresh');
			const refreshSucceeded = await refreshToken();

			if (refreshSucceeded) {
				console.log('[API] Token refreshed, retrying request');
				// Update headers with new token
				const newHeaders = this.getHeaders();
				const retryOptions = {
					...options,
					headers: newHeaders
				};

				let retryResponse: Response;
				try {
					retryResponse = await fetch(url, retryOptions);
				} catch (retryNetworkError) {
					console.error('[API] Retry network error:', retryNetworkError);
					throw new ApiError('NETWORK_ERROR', '서버에 연결할 수 없습니다', 0);
				}

				if (!retryResponse.ok && retryResponse.status !== 401) {
					const errorData = await this.parseErrorResponse(retryResponse);
					throw new ApiError(errorData.code, errorData.message, retryResponse.status);
				}

				if (retryResponse.status === 401) {
					console.log('[API] Still 401 after refresh, redirecting to login');
					goto('/login');
					throw new ApiError('UNAUTHORIZED', '세션이 만료되었습니다', 401);
				}

				// Handle 204 No Content
				if (retryResponse.status === 204) {
					return undefined as T;
				}

				return retryResponse.json();
			} else {
				console.log('[API] Token refresh failed, redirecting to login');
				goto('/login');
				throw new ApiError('UNAUTHORIZED', '세션이 만료되었습니다', 401);
			}
		}

		if (!response.ok) {
			const errorData = await this.parseErrorResponse(response);
			console.error('[API] Error response:', errorData);
			throw new ApiError(errorData.code, errorData.message, response.status);
		}

		// Handle 204 No Content
		if (response.status === 204) {
			return undefined as T;
		}

		const jsonData = await response.json();
		console.log('[API] Response data:', JSON.stringify(jsonData).slice(0, 200));
		return jsonData;
	}

	private async parseErrorResponse(response: Response): Promise<{ code: string; message: string }> {
		try {
			const errorJson = await response.json();
			// 여러 에러 형식 지원
			if (errorJson.error?.code) {
				return { code: errorJson.error.code, message: errorJson.error.message || '알 수 없는 오류' };
			}
			if (errorJson.detail) {
				return { code: 'API_ERROR', message: errorJson.detail };
			}
			if (errorJson.message) {
				return { code: 'API_ERROR', message: errorJson.message };
			}
			return { code: 'API_ERROR', message: JSON.stringify(errorJson) };
		} catch {
			return { code: 'PARSE_ERROR', message: `HTTP ${response.status}: ${response.statusText}` };
		}
	}

	async get<T>(endpoint: string, params?: Record<string, string | number | undefined>): Promise<T> {
		let url = `${API_BASE}${endpoint}`;

		if (params) {
			const searchParams = new URLSearchParams();
			Object.entries(params).forEach(([key, value]) => {
				if (value !== undefined) {
					searchParams.append(key, String(value));
				}
			});
			const queryString = searchParams.toString();
			if (queryString) {
				url += `?${queryString}`;
			}
		}

		return this.fetchWithAuth<T>(url, {
			method: 'GET',
			headers: this.getHeaders()
		});
	}

	async post<T>(endpoint: string, data?: unknown): Promise<T> {
		return this.fetchWithAuth<T>(`${API_BASE}${endpoint}`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: data ? JSON.stringify(data) : undefined
		});
	}

	async patch<T>(endpoint: string, data: unknown): Promise<T> {
		return this.fetchWithAuth<T>(`${API_BASE}${endpoint}`, {
			method: 'PATCH',
			headers: this.getHeaders(),
			body: JSON.stringify(data)
		});
	}

	async put<T>(endpoint: string, data: unknown): Promise<T> {
		return this.fetchWithAuth<T>(`${API_BASE}${endpoint}`, {
			method: 'PUT',
			headers: this.getHeaders(),
			body: JSON.stringify(data)
		});
	}

	async delete<T>(endpoint: string): Promise<T> {
		return this.fetchWithAuth<T>(`${API_BASE}${endpoint}`, {
			method: 'DELETE',
			headers: this.getHeaders()
		});
	}

	async uploadChunk(
		recordingId: number,
		chunk: Blob,
		offset: number,
		totalSize: number
	): Promise<UploadProgressResponse> {
		const headers: Record<string, string> = {
			'Content-Type': chunk.type || 'audio/webm',
			'Upload-Offset': String(offset),
			'Content-Length': String(chunk.size),
			'Upload-Length': String(totalSize)
		};

		const token = localStorage.getItem('accessToken');
		if (token) {
			headers['Authorization'] = `Bearer ${token}`;
		}

		console.log('[API] uploadChunk 시작:', {
			recordingId,
			offset,
			chunkSize: chunk.size,
			totalSize,
			mimeType: chunk.type
		});

		const response = await fetch(`${API_BASE}/recordings/${recordingId}/upload`, {
			method: 'POST',
			headers,
			body: chunk
		});

		if (!response.ok) {
			let error;
			try {
				error = await response.json();
			} catch {
				error = { error: { message: `HTTP ${response.status}` } };
			}
			console.error('[API] uploadChunk 실패:', {
				status: response.status,
				error
			});
			throw new ApiError(
				error.error?.code || 'UPLOAD_ERROR',
				error.error?.message || 'Upload failed',
				response.status
			);
		}

		const result = await response.json();
		console.log('[API] uploadChunk 완료:', result);
		return result;
	}
}

export class ApiError extends Error {
	code: string;
	status: number;

	constructor(code: string, message: string, status: number) {
		super(message);
		this.code = code;
		this.status = status;
		this.name = 'ApiError';
	}
}

export const api = ApiClient.getInstance();
