import { describe, expect, it, vi } from 'vitest';

import {
	buildPresignRequest,
	createPresignedUpload,
	getOperationOptions,
	pollJobStatus,
	startJob,
	uploadFileToPresignedUrl,
} from './jobs';
import {
	OPERATIONS,
	getOperation,
	validateOperationFile,
} from '../operations';

const jsonResponse = (body: unknown, status = 200) =>
	new Response(JSON.stringify(body), {
		status,
		headers: { 'Content-Type': 'application/json' },
	});

describe('image operation request construction', () => {
	it.each([
		['jpeg-to-png', 'jpeg_to_png', 'photo.jpg', 'image/jpeg'],
		['png-to-jpeg', 'png_to_jpeg', 'image.png', 'image/png'],
		['png-to-webp', 'png_to_webp', 'image.png', 'image/png'],
		['webp-to-png', 'webp_to_png', 'image.webp', 'image/webp'],
		['webp-to-jpeg', 'webp_to_jpeg', 'image.webp', 'image/webp'],
		['jpeg-to-webp', 'jpeg_to_webp', 'photo.jpeg', 'image/jpeg'],
	] as const)('builds %s payload without options', (_slug, operation, filename, content_type) => {
		const result = buildPresignRequest({ operation, filename, content_type });

		expect(result).toEqual({ operation, filename, content_type });
	});

	it('builds compression options in bytes', () => {
		const result = buildPresignRequest({
			operation: 'compress',
			filename: 'photo.jpg',
			content_type: 'image/jpeg',
			operation_options: { target_size_bytes: 250000 },
		});

		expect(result.operation_options).toEqual({ target_size_bytes: 250000 });
	});

	it('builds downsample options without a target size', () => {
		const result = buildPresignRequest({
			operation: 'downsample',
			filename: 'photo.jpg',
			content_type: 'image/jpeg',
			operation_options: { max_width: 2048, max_height: 1024 },
		});

		expect(result.operation_options).toEqual({ max_width: 2048, max_height: 1024 });
	});

	it('exposes all supported image operations as live tools', () => {
		expect(OPERATIONS.filter((operation) => operation.category === 'image' && operation.status === 'live')).toHaveLength(8);
	});
});

describe('operation validation', () => {
	it('rejects an extension or MIME mismatch', () => {
		const operation = getOperation('image', 'jpeg-to-png')!;

		expect(validateOperationFile({ name: 'photo.png', type: 'image/jpeg' } as File, operation)).toMatch(/JPG or JPEG/);
		expect(validateOperationFile({ name: 'photo.jpg', type: 'image/png' } as File, operation)).toMatch(/image\/jpeg/);
	});

	it('accepts matching WebP input', () => {
		const operation = getOperation('image', 'webp-to-png')!;

		expect(validateOperationFile({ name: 'image.webp', type: 'image/webp' } as File, operation)).toBeNull();
	});
});

describe('numeric operation options', () => {
	it('rejects invalid compression sizes', () => {
		expect(getOperationOptions('compress', { targetSizeBytes: 0 })).toEqual({
			error: 'Enter a positive whole-number target size.',
		});
		expect(getOperationOptions('compress', { targetSizeBytes: -1 })).toHaveProperty('error');
		expect(getOperationOptions('compress', { targetSizeBytes: 1.5 })).toHaveProperty('error');
	});

	it('rejects invalid downsample dimensions and accepts positive integers', () => {
		expect(getOperationOptions('downsample', { maxWidth: 0, maxHeight: 100 })).toHaveProperty('error');
		expect(getOperationOptions('downsample', { maxWidth: 100, maxHeight: 200 })).toEqual({
		options: { max_width: 100, max_height: 200 },
	});
	});
});

describe('job API flow', () => {
	it('presigns, uploads, starts, and polls successfully', async () => {
		const fetchMock = vi
			.spyOn(globalThis, 'fetch')
			.mockResolvedValueOnce(jsonResponse({ job_id: 'job-1', upload_url: 'https://upload', input_key: 'input', expires_in: 60 }))
			.mockResolvedValueOnce(new Response(null, { status: 200 }))
			.mockResolvedValueOnce(jsonResponse({ id: 'job-1', status: 'pending', operation: 'png_to_webp', input_key: 'input', credits_remaining: 2 }))
			.mockResolvedValueOnce(jsonResponse({ id: 'job-1', status: 'completed', operation: 'png_to_webp', error_message: null, download_url: 'https://download', download_expires_in: 60, filename: 'image.webp' }));

		const presign = await createPresignedUpload({ operation: 'png_to_webp', filename: 'image.png', content_type: 'image/png' });
		await uploadFileToPresignedUrl(presign.upload_url, new File(['image'], 'image.png', { type: 'image/png' }), 'image/png');
		await startJob(presign.job_id);
		const completed = await pollJobStatus(presign.job_id);

		expect(completed.download_url).toBe('https://download');
		expect(fetchMock).toHaveBeenCalledTimes(4);
		expect(fetchMock.mock.calls[0][1]).toMatchObject({ body: JSON.stringify({ operation: 'png_to_webp', filename: 'image.png', content_type: 'image/png' }) });
		expect(fetchMock.mock.calls[1][1]).toMatchObject({ headers: { 'Content-Type': 'image/png' } });
	});

	it('surfaces API errors', async () => {
		vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({ detail: 'Not allowed' }, 403));

		await expect(createPresignedUpload({ operation: 'compress', filename: 'photo.jpg', content_type: 'image/jpeg', operation_options: { target_size_bytes: 1000 } })).rejects.toMatchObject({ status: 403, message: 'Not allowed' });
	});
});
