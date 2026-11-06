import { describe, it, expect, vi } from 'vitest';
import { POST } from './+server';

describe('POST /panel/simulation/[action]', () => {
	it('handles 204 No Content response from backend without throwing TypeError', async () => {
		const mockFetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
		const mockCookies = {
			get: vi.fn().mockReturnValue('test-token')
		};
		const mockRequest = new Request('http://localhost/panel/simulation/pause', {
			method: 'POST'
		});

		const res = await POST({
			params: { action: 'pause' },
			request: mockRequest,
			cookies: mockCookies as any,
			fetch: mockFetch as any,
			url: new URL('http://localhost/panel/simulation/pause'),
			route: { id: '/panel/simulation/[action]' },
			setHeaders: vi.fn(),
			getClientAddress: vi.fn(),
			locals: {} as any,
			platform: undefined,
			isDataRequest: false,
			isSubRequest: false
		} as any);

		expect(res.status).toBe(204);
		expect(res.body).toBeNull();
	});

	it('forwards error response from backend with JSON body', async () => {
		const mockFetch = vi.fn().mockResolvedValue(
			new Response(JSON.stringify({ detail: 'Symulacja jest już wstrzymana' }), {
				status: 409,
				headers: { 'Content-Type': 'application/json' }
			})
		);
		const mockCookies = {
			get: vi.fn().mockReturnValue('test-token')
		};
		const mockRequest = new Request('http://localhost/panel/simulation/pause', {
			method: 'POST'
		});

		const res = await POST({
			params: { action: 'pause' },
			request: mockRequest,
			cookies: mockCookies as any,
			fetch: mockFetch as any,
			url: new URL('http://localhost/panel/simulation/pause'),
			route: { id: '/panel/simulation/[action]' },
			setHeaders: vi.fn(),
			getClientAddress: vi.fn(),
			locals: {} as any,
			platform: undefined,
			isDataRequest: false,
			isSubRequest: false
		} as any);

		expect(res.status).toBe(409);
		const json = await res.json();
		expect(json).toEqual({ detail: 'Symulacja jest już wstrzymana' });
	});
});
