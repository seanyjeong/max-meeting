import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('ApiClient', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('should make GET request to correct endpoint', async () => {
		const mockResponse = { data: { id: 1, title: 'Test Meeting' } };
		vi.mocked(globalThis.fetch).mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: () => Promise.resolve(mockResponse)
		} as Response);

		const { api } = await import('./api');
		const result = await api.get('/meetings/1');

		expect(globalThis.fetch).toHaveBeenCalledWith(
			'/api/v1/meetings/1',
			expect.objectContaining({
				method: 'GET',
				headers: expect.objectContaining({
					'Content-Type': 'application/json'
				})
			})
		);
		expect(result).toEqual(mockResponse);
	});

	it('should append query params to URL', async () => {
		const mockResponse = { data: [], meta: { total: 0, limit: 20, offset: 0 } };
		vi.mocked(globalThis.fetch).mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: () => Promise.resolve(mockResponse)
		} as Response);

		const { api } = await import('./api');
		await api.get('/meetings', { status: 'draft', limit: 10 });

		expect(globalThis.fetch).toHaveBeenCalledWith(
			'/api/v1/meetings?status=draft&limit=10',
			expect.any(Object)
		);
	});

	it('should make POST request with JSON body', async () => {
		const mockResponse = { data: { id: 1, title: 'New Meeting' } };
		vi.mocked(globalThis.fetch).mockResolvedValueOnce({
			ok: true,
			status: 201,
			json: () => Promise.resolve(mockResponse)
		} as Response);

		const { api } = await import('./api');
		const result = await api.post('/meetings', { title: 'New Meeting', type_id: 1 });

		expect(globalThis.fetch).toHaveBeenCalledWith(
			'/api/v1/meetings',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ title: 'New Meeting', type_id: 1 })
			})
		);
		expect(result).toEqual(mockResponse);
	});

	it('should make PATCH request', async () => {
		const mockResponse = { data: { id: 1, status: 'in_progress' } };
		vi.mocked(globalThis.fetch).mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: () => Promise.resolve(mockResponse)
		} as Response);

		const { api } = await import('./api');
		await api.patch('/meetings/1', { status: 'in_progress' });

		expect(globalThis.fetch).toHaveBeenCalledWith(
			'/api/v1/meetings/1',
			expect.objectContaining({
				method: 'PATCH',
				body: JSON.stringify({ status: 'in_progress' })
			})
		);
	});

	it('should make DELETE request', async () => {
		vi.mocked(globalThis.fetch).mockResolvedValueOnce({
			ok: true,
			status: 204,
			json: () => Promise.resolve(undefined)
		} as Response);

		const { api } = await import('./api');
		await api.delete('/meetings/1');

		expect(globalThis.fetch).toHaveBeenCalledWith(
			'/api/v1/meetings/1',
			expect.objectContaining({
				method: 'DELETE'
			})
		);
	});
});
