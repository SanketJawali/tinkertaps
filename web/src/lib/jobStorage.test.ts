import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
	clearStoredJob,
	getJobStorageKey,
	getStoredJob,
	setStoredJob,
	type StoredJob,
} from './jobStorage';

describe('jobStorage', () => {
	const mockStorage: Record<string, string> = {};

	beforeEach(() => {
		for (const key of Object.keys(mockStorage)) {
			delete mockStorage[key];
		}

		vi.stubGlobal('localStorage', {
			getItem: vi.fn((key: string) => mockStorage[key] ?? null),
			setItem: vi.fn((key: string, value: string) => {
				mockStorage[key] = value;
			}),
			removeItem: vi.fn((key: string) => {
				delete mockStorage[key];
			}),
		});
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('generates consistent storage keys', () => {
		expect(getJobStorageKey('jpeg_to_png')).toBe('tinkertaps_job_jpeg_to_png');
		expect(getJobStorageKey('compress')).toBe('tinkertaps_job_compress');
	});

	it('saves, retrieves, and clears stored job', () => {
		const key = getJobStorageKey('jpeg_to_png');
		const job: StoredJob = {
			jobId: 'job-123',
			operation: 'jpeg_to_png',
			fileName: 'photo.jpg',
			fileSize: 1024,
			phase: 'streaming',
			startedAt: Date.now(),
			statusLabel: 'Waiting',
		};

		expect(getStoredJob(key)).toBeNull();

		setStoredJob(key, job);
		expect(getStoredJob(key)).toEqual(job);

		clearStoredJob(key);
		expect(getStoredJob(key)).toBeNull();
	});

	it('returns null and clears corrupted JSON data', () => {
		const key = getJobStorageKey('jpeg_to_png');
		mockStorage[key] = '{ invalid json';

		expect(getStoredJob(key)).toBeNull();
	});

	it('returns null and clears data missing required fields', () => {
		const key = getJobStorageKey('jpeg_to_png');
		mockStorage[key] = JSON.stringify({ jobId: 'only-job-id' });

		expect(getStoredJob(key)).toBeNull();
		expect(mockStorage[key]).toBeUndefined();
	});

	it('clears expired job data', () => {
		const key = getJobStorageKey('compress');
		mockStorage[key] = JSON.stringify({
			jobId: 'job-123',
			fileName: 'photo.jpg',
			fileSize: 1024,
			phase: 'completed',
			startedAt: Date.now() - 3600000,
			expiresAt: Date.now() - 1,
		});

		expect(getStoredJob(key)).toBeNull();
		expect(mockStorage[key]).toBeUndefined();
	});
});
