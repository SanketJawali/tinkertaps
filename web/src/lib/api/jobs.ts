export type JobOperation = 'compress' | 'convert';

export type PresignResponse = {
	job_id: string;
	upload_url: string;
	input_key: string;
	expires_in: number;
};

export type StartJobResponse = {
	id: string;
	status: string;
	operation: JobOperation;
	input_key: string;
	credits_remaining: number;
};

export class ApiError extends Error {
	status: number;
	detail: unknown;

	constructor(status: number, detail: unknown, message: string) {
		super(message);
		this.name = 'ApiError';
		this.status = status;
		this.detail = detail;
	}
}

function errorMessageFromDetail(detail: unknown, fallback: string): string {
	if (typeof detail === 'string' && detail.trim()) {
		return detail;
	}

	if (Array.isArray(detail) && detail.length > 0) {
		const first = detail[0];

		if (
			first &&
			typeof first === 'object' &&
			'msg' in first &&
			typeof first.msg === 'string'
		) {
			return first.msg;
		}
	}

	return fallback;
}

async function parseError(response: Response, fallback: string): Promise<ApiError> {
	let detail: unknown = fallback;

	try {
		const body = (await response.json()) as { detail?: unknown };
		detail = body.detail ?? fallback;
	} catch {
		// Non-JSON error bodies are fine — use the fallback message.
	}

	return new ApiError(
		response.status,
		detail,
		errorMessageFromDetail(detail, fallback),
	);
}

async function authHeaders(getToken?: () => Promise<string | null>): Promise<HeadersInit> {
	const headers: Record<string, string> = {
		Accept: 'application/json',
	};

	if (!getToken) {
		return headers;
	}

	const token = await getToken();

	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}

	return headers;
}

export async function createPresignedUpload(
	body: {
		operation: JobOperation;
		filename: string;
		content_type: string;
	},
	getToken?: () => Promise<string | null>,
): Promise<PresignResponse> {
	const response = await fetch('/api/jobs/presign', {
		method: 'POST',
		credentials: 'include',
		headers: {
			...(await authHeaders(getToken)),
			'Content-Type': 'application/json',
		},
		body: JSON.stringify(body),
	});

	if (!response.ok) {
		throw await parseError(
			response,
			"We couldn't prepare the upload. Try again.",
		);
	}

	return (await response.json()) as PresignResponse;
}

function s3ErrorMessage(body: string): string | null {
	const code = body.match(/<Code>([^<]+)<\/Code>/)?.[1];
	const message = body.match(/<Message>([^<]+)<\/Message>/)?.[1];

	if (!code && !message) {
		return null;
	}

	if (code && message) {
		return `${code}: ${message}`;
	}

	return code ?? message ?? null;
}

export async function uploadFileToPresignedUrl(
	uploadUrl: string,
	file: File,
	contentType: string,
): Promise<void> {
	const response = await fetch(uploadUrl, {
		method: 'PUT',
		body: file,
		headers: {
			// Must match the ContentType baked into the presigned URL signature.
			'Content-Type': contentType,
		},
	});

	if (!response.ok) {
		const body = await response.text().catch(() => '');
		const s3Message = s3ErrorMessage(body);

		throw new ApiError(
			response.status,
			body || null,
			s3Message ?? "We couldn't upload your file. Try again.",
		);
	}
}

export async function startJob(
	jobId: string,
	getToken?: () => Promise<string | null>,
): Promise<StartJobResponse> {
	const response = await fetch(`/api/jobs/${jobId}/start`, {
		method: 'POST',
		credentials: 'include',
		headers: await authHeaders(getToken),
	});

	if (!response.ok) {
		throw await parseError(
			response,
			"We couldn't start working on your file. Try again.",
		);
	}

	return (await response.json()) as StartJobResponse;
}
