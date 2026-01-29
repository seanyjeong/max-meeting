// Vitest setup file
import { vi } from 'vitest';

// Mock fetch globally
globalThis.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
	clear: vi.fn()
};
Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock });
