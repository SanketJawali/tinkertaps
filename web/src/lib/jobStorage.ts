import type { JobOperation } from './api/jobs';

export type StoredJobPhase =
	| 'uploaded'
	| 'starting'
	| 'polling'
	| 'completed'
	| 'failed';

export type StoredJob = {
	jobId: string;
	operation: JobOperation;
	category?: string;
	slug?: string;
	fileName: string;
	fileSize: number;
	phase: StoredJobPhase;
	statusLabel?: string;
	startedAt: number;
	creditsRemaining?: number | null;
	downloadUrl?: string | null;
	downloadExpiresIn?: number | null;
	downloadFilename?: string | null;
	outputFormat?: string;
	error?: string | null;
};

const STORAGE_PREFIX = 'tinkertaps_job_';

export function getJobStorageKey(operation: JobOperation | string): string {
	return `${STORAGE_PREFIX}${operation}`;
}

function getStorage(): Storage | null {
	if (typeof window !== 'undefined' && window.localStorage) {
		return window.localStorage;
	}

	if (typeof localStorage !== 'undefined') {
		return localStorage;
	}

	return null;
}

export function getStoredJob(key: string): StoredJob | null {
	const storage = getStorage();
	if (!storage) {
		return null;
	}

	try {
		const raw = storage.getItem(key);
		if (!raw) {
			return null;
		}

		const data = JSON.parse(raw) as Partial<StoredJob>;
		if (
			typeof data.jobId === 'string' &&
			typeof data.fileName === 'string' &&
			typeof data.fileSize === 'number' &&
			typeof data.phase === 'string' &&
			typeof data.startedAt === 'number'
		) {
			return data as StoredJob;
		}

		// Invalid or incomplete stored data
		storage.removeItem(key);
		return null;
	} catch {
		return null;
	}
}

export function setStoredJob(key: string, job: StoredJob): void {
	const storage = getStorage();
	if (!storage) {
		return;
	}

	try {
		storage.setItem(key, JSON.stringify(job));
	} catch (e) {
		console.warn('Failed to save job to localStorage', e);
	}
}

export function clearStoredJob(key: string): void {
	const storage = getStorage();
	if (!storage) {
		return;
	}

	try {
		storage.removeItem(key);
	} catch {
		// Ignore errors on clear
	}
}
