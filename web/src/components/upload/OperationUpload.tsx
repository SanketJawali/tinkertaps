import { useAuth } from '@clerk/astro/react';
import { useEffect, useRef, useState } from 'react';

import {
	ApiError,
	buildPresignRequest,
	createPresignedUpload,
	getJobStatus,
	getOperationOptions,
	startJob,
	streamJobStatus,
	uploadFileToPresignedUrl,
	type JobOperation,
} from '../../lib/api/jobs';
import {
	clearStoredJob,
	getJobStorageKey,
	getStoredJob,
	setStoredJob,
} from '../../lib/jobStorage';
import { validateOperationFile, type ToolOperation } from '../../lib/operations';

type Phase =
	| 'idle'
	| 'uploading'
	| 'uploaded'
	| 'starting'
	| 'streaming'
	| 'completed'
	| 'failed';

type Props = {
	operation: ToolOperation & { apiOperation: JobOperation };
};

/**
 * File picker UI has no Clerk dependency in its render path.
 * Auth is only consulted when the user uploads or starts a job.
 */

function formatBytes(bytes: number) {
	if (bytes < 1024 * 1024) {
		return `${(bytes / 1024).toFixed(1)} KB`;
	}

	return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function formatTargetSize(bytes: number) {
	if (bytes >= 1024 * 1024) {
		return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
	}

	return `${(bytes / 1024).toFixed(0)} KB`;
}

function formatExpiry(seconds: number) {
	if (seconds < 60) {
		return `${seconds} second${seconds === 1 ? '' : 's'}`;
	}

	const minutes = Math.round(seconds / 60);

	if (minutes < 60) {
		return `${minutes} minute${minutes === 1 ? '' : 's'}`;
	}

	const hours = Math.round(minutes / 60);

	return `${hours} hour${hours === 1 ? '' : 's'}`;
}

function getFileLabel(filename: string) {
	const extension = filename.split('.').pop();

	return extension?.toUpperCase() ?? 'FILE';
}

function acceptHint(accept: string) {
	return accept
		.split(',')
		.map((part) => part.trim())
		.filter((part) => part.startsWith('.'))
		.map((ext) => ext.slice(1).toUpperCase())
		.join(' · ');
}

function userFacingError(error: unknown): string {
	if (error instanceof ApiError) {
		if (error.status === 402) {
			return "You're out of free uses for now.";
		}

		return error.message;
	}

	if (error instanceof Error && error.message) {
		return error.message;
	}

	return 'Something went wrong. Try again.';
}

function ErrorAlert({
	message,
	onDismiss,
}: {
	message: string;
	onDismiss: () => void;
}) {
	return (
		<div
			className="alert alert-error mt-6 items-start shadow-sm"
			role="alert"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				className="mt-0.5 size-5 shrink-0 stroke-current"
				fill="none"
				viewBox="0 0 24 24"
				aria-hidden="true"
			>
				<path
					strokeLinecap="round"
					strokeLinejoin="round"
					strokeWidth="2"
					d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>

			<div className="min-w-0 flex-1">
				<p className="font-semibold">Something went wrong</p>
				<p className="mt-1 text-sm leading-6 opacity-90">{message}</p>
			</div>

			<button
				type="button"
				className="btn btn-ghost btn-sm btn-square"
				aria-label="Dismiss error"
				onClick={onDismiss}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					className="size-4"
					fill="none"
					viewBox="0 0 24 24"
					stroke="currentColor"
					aria-hidden="true"
				>
					<path
						strokeLinecap="round"
						strokeLinejoin="round"
						strokeWidth="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>
	);
}

export default function OperationUpload({
	operation,
}: Props) {
	const { title, accept, apiOperation } = operation;
	const { getToken, isLoaded, isSignedIn } = useAuth();
	const inputRef = useRef<HTMLInputElement>(null);
	const storageKey = getJobStorageKey(apiOperation);

	const [file, setFile] = useState<File | null>(null);
	const [restoredFileInfo, setRestoredFileInfo] = useState<{
		name: string;
		size: number;
	} | null>(null);
	const [dragging, setDragging] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [phase, setPhase] = useState<Phase>('idle');
	const [jobId, setJobId] = useState<string | null>(null);
	const [streamStartedAt, setStreamStartedAt] = useState<number | null>(null);
	const [creditsRemaining, setCreditsRemaining] = useState<number | null>(
		null,
	);
	const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
	const [downloadExpiresIn, setDownloadExpiresIn] = useState<number | null>(
		null,
	);
	const [downloadFilename, setDownloadFilename] = useState<string | null>(
		null,
	);
	const [compressTarget, setCompressTarget] = useState('250000');
	const [maxWidth, setMaxWidth] = useState('2048');
	const [maxHeight, setMaxHeight] = useState('2048');
	const [outputFormat, setOutputFormat] = useState(operation.outputFormat);
	const [statusLabel, setStatusLabel] = useState('Working on it');

	const activeFile = file
		? { name: file.name, size: file.size }
		: restoredFileInfo;

	const typeHint = acceptHint(accept) || 'FILE';
	const canUpload = isLoaded && isSignedIn;

	const activeFileRef = useRef(activeFile);
	activeFileRef.current = activeFile;
	const creditsRemainingRef = useRef(creditsRemaining);
	creditsRemainingRef.current = creditsRemaining;
	const outputFormatRef = useRef(outputFormat);
	outputFormatRef.current = outputFormat;
	const streamStartedAtRef = useRef(streamStartedAt);
	streamStartedAtRef.current = streamStartedAt;

	// Restore active job from localStorage on initial mount
	useEffect(() => {
		const stored = getStoredJob(storageKey);
		if (!stored) {
			return;
		}

		setJobId(stored.jobId);
		setRestoredFileInfo({
			name: stored.fileName,
			size: stored.fileSize,
		});
		setPhase(stored.phase === 'polling' ? 'streaming' : stored.phase);
		setStreamStartedAt(stored.startedAt);
		if (stored.statusLabel) {
			setStatusLabel(stored.statusLabel);
		}
		if (stored.creditsRemaining !== undefined && stored.creditsRemaining !== null) {
			setCreditsRemaining(stored.creditsRemaining);
		}
		if (stored.downloadUrl) {
			setDownloadUrl(stored.downloadUrl);
		}
		if (stored.downloadExpiresIn !== undefined) {
			setDownloadExpiresIn(stored.downloadExpiresIn);
		}
		if (stored.downloadFilename) {
			setDownloadFilename(stored.downloadFilename);
		}
		if (stored.outputFormat) {
			setOutputFormat(stored.outputFormat);
		}
		if (stored.error) {
			setError(stored.error);
		}
	}, [storageKey]);

	useEffect(() => {
		if (phase !== 'streaming' || !jobId || !isLoaded) {
			return;
		}

		let cancelled = false;
		const controller = new AbortController();
		const startTime = streamStartedAtRef.current || Date.now();
		if (!streamStartedAtRef.current) {
			streamStartedAtRef.current = startTime;
			setStreamStartedAt(startTime);
		}

		async function connect() {
			try {
				await streamJobStatus(jobId, getToken, async (event) => {
					if (cancelled) return;
					if (event.status === 'pending') setStatusLabel('Waiting');
					if (event.status === 'processing') setStatusLabel('Working on it');
					setStoredJob(storageKey, {
						jobId,
						operation: apiOperation,
						category: operation.category,
						slug: operation.slug,
						fileName: activeFileRef.current?.name ?? 'file',
						fileSize: activeFileRef.current?.size ?? 0,
						phase: 'streaming',
						statusLabel: event.status === 'pending' ? 'Waiting' : 'Working on it',
						startedAt: startTime,
						expiresAt: startTime + 60 * 60 * 1000,
						creditsRemaining: creditsRemainingRef.current,
						outputFormat: outputFormatRef.current,
					});

					if (event.status !== 'completed' && event.status !== 'failed') return;

					const result = await getJobStatus(jobId, getToken);
					if (result.status === 'completed' && result.download_url) {
						const finalFilename = result.filename ?? result.output_filename ?? result.download_filename ?? null;
						const serverFilename = finalFilename;
						const finalFormat = serverFilename?.split('.').pop()?.toUpperCase() ?? outputFormatRef.current;
						setDownloadUrl(result.download_url);
						setDownloadExpiresIn(result.download_expires_in);
						setDownloadFilename(finalFilename);
						setOutputFormat(finalFormat);
						setPhase('completed');
						setStoredJob(storageKey, { jobId, operation: apiOperation, category: operation.category, slug: operation.slug, fileName: activeFileRef.current?.name ?? 'file', fileSize: activeFileRef.current?.size ?? 0, phase: 'completed', startedAt: startTime, expiresAt: Date.now() + (result.download_expires_in ?? 3600) * 1000, downloadUrl: result.download_url, downloadExpiresIn: result.download_expires_in, downloadFilename: finalFilename, outputFormat: finalFormat });
						controller.abort();
						return;
					}

					const failureMsg = result.error_message?.trim() || `We couldn't finish ${title.toLowerCase()}.`;
					setError(result.status === 'completed' ? 'The file is ready, but the download link is missing. Try again.' : failureMsg);
					setPhase('failed');
					setStoredJob(storageKey, { jobId, operation: apiOperation, category: operation.category, slug: operation.slug, fileName: activeFileRef.current?.name ?? 'file', fileSize: activeFileRef.current?.size ?? 0, phase: 'failed', startedAt: startTime, expiresAt: Date.now() + 60 * 60 * 1000, error: result.status === 'completed' ? 'The file is ready, but the download link is missing. Try again.' : failureMsg });
					controller.abort();
				}, controller.signal);
			} catch (err) {
				if (!cancelled) setError(userFacingError(err));
			}
		}

		void connect();

		return () => {
			cancelled = true;
			controller.abort();
		};
	}, [phase, jobId, isLoaded, getToken, title, storageKey, apiOperation, operation]);

	function chooseFile(next: File) {
		clearStoredJob(storageKey);
		setRestoredFileInfo(null);
		setError(null);
		setPhase('idle');
		setJobId(null);
		setStreamStartedAt(null);
		setCreditsRemaining(null);
		setDownloadUrl(null);
		setDownloadExpiresIn(null);
		setDownloadFilename(null);
		setOutputFormat(
			operation.outputFormat === 'same as input'
				? next.name.split('.').pop()?.toUpperCase() ?? operation.outputFormat
				: operation.outputFormat,
		);
		setStatusLabel('Working on it');

		const validationError = validateOperationFile(next, operation);

		if (validationError) {
			setFile(null);
			setError(validationError);
			return;
		}

		setFile(next);
	}

	function resetFile() {
		clearStoredJob(storageKey);
		setRestoredFileInfo(null);
		setFile(null);
		setError(null);
		setPhase('idle');
		setJobId(null);
		setStreamStartedAt(null);
		setCreditsRemaining(null);
		setDownloadUrl(null);
		setDownloadExpiresIn(null);
		setDownloadFilename(null);
		setOutputFormat(operation.outputFormat);
		setStatusLabel('Working on it');

		if (inputRef.current) {
			inputRef.current.value = '';
		}
	}

	async function handleUpload() {
		if (!file || phase === 'uploading') {
			return;
		}

		if (!canUpload) {
			setError('Sign in to upload.');
			return;
		}

		setError(null);
		setPhase('uploading');

		try {
			const optionResult = getOperationOptions(operation.optionKind, {
				targetSizeBytes: Number(compressTarget),
				maxWidth: Number(maxWidth),
				maxHeight: Number(maxHeight),
			});

			if (optionResult.error) {
				setPhase('idle');
				setError(optionResult.error);
				return;
			}

			const presign = await createPresignedUpload(
				buildPresignRequest({
					operation: apiOperation,
					filename: file.name,
					content_type: file.type,
					...(optionResult.options
						? { operation_options: optionResult.options }
						: {}),
				}),
				getToken,
			);

			await uploadFileToPresignedUrl(
				presign.upload_url,
				file,
				file.type,
			);

			setJobId(presign.job_id);
			setPhase('uploaded');

			setStoredJob(storageKey, {
				jobId: presign.job_id,
				operation: apiOperation,
				category: operation.category,
				slug: operation.slug,
				fileName: file.name,
				fileSize: file.size,
				phase: 'uploaded',
				startedAt: Date.now(),
				expiresAt: Date.now() + 60 * 60 * 1000,
				outputFormat,
			});
		} catch (err) {
			setPhase('idle');
			setError(userFacingError(err));
		}
	}

	async function handleStart() {
		if (!jobId || phase === 'starting') {
			return;
		}

		setError(null);
		setPhase('starting');

		try {
			const result = await startJob(jobId, getToken);
			const now = Date.now();
			setCreditsRemaining(result.credits_remaining);
			setStatusLabel('Waiting');
			setStreamStartedAt(now);
			setPhase('streaming');

			setStoredJob(storageKey, {
				jobId,
				operation: apiOperation,
				category: operation.category,
				slug: operation.slug,
				fileName: activeFile?.name ?? 'file',
				fileSize: activeFile?.size ?? 0,
				phase: 'streaming',
				startedAt: now,
				expiresAt: now + 60 * 60 * 1000,
				statusLabel: 'Waiting',
				creditsRemaining: result.credits_remaining,
				outputFormat,
			});
		} catch (err) {
			setPhase('uploaded');
			setError(userFacingError(err));
		}
	}

	const fileInput = (
		<input
			ref={inputRef}
			type="file"
			className="hidden"
			accept={accept}
			onChange={(event) => {
				const next = event.target.files?.[0];

				if (next) {
					chooseFile(next);
				}
			}}
		/>
	);

	const errorAlert = error ? (
		<ErrorAlert message={error} onDismiss={() => setError(null)} />
	) : null;
	const optionResult = getOperationOptions(operation.optionKind, {
		targetSizeBytes: Number(compressTarget),
		maxWidth: Number(maxWidth),
		maxHeight: Number(maxHeight),
	});

	if (!activeFile) {
		return (
			<section className="mt-10">
				{errorAlert}

				<div
					className={[
						'flex min-h-80 flex-col items-center justify-center rounded-box border p-8 text-center transition-colors',
						dragging
							? 'border-primary bg-base-200/70'
							: 'border-base-300 bg-base-100',
					].join(' ')}
					onDragEnter={(event) => {
						event.preventDefault();
						setDragging(true);
					}}
					onDragOver={(event) => {
						event.preventDefault();
						setDragging(true);
					}}
					onDragLeave={(event) => {
						event.preventDefault();

						if (
							event.currentTarget.contains(
								event.relatedTarget as Node,
							)
						) {
							return;
						}

						setDragging(false);
					}}
					onDrop={(event) => {
						event.preventDefault();
						setDragging(false);

						const next = event.dataTransfer.files[0];

						if (next) {
							chooseFile(next);
						}
					}}
				>
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						Upload
					</p>

					<h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">
						Drop a file here
					</h2>

					<p className="mt-3 text-base-content/50">
						or choose one from your computer
					</p>

					<button
						type="button"
						className="btn btn-primary mt-8"
						onClick={() => inputRef.current?.click()}
					>
						Choose file
					</button>

					{fileInput}

					<p className="mt-6 font-mono text-xs uppercase tracking-[0.12em] text-base-content/35">
						{typeHint}
					</p>
				</div>
			</section>
		);
	}

	return (
		<section className="mt-10">
			{errorAlert}

			<div className="flex items-center justify-between gap-6 border-b border-base-300 pb-6">
				<div className="min-w-0">
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						File
					</p>

					<p className="mt-3 truncate text-xl font-semibold tracking-[-0.025em]">
						{activeFile.name}
					</p>

					<p className="mt-1 text-sm text-base-content/45">
						{getFileLabel(activeFile.name)} · {formatBytes(activeFile.size)}
					</p>
				</div>

				{(phase === 'idle' ||
					phase === 'uploaded' ||
					phase === 'failed' ||
					phase === 'completed') && (
					<button
						type="button"
						className="btn btn-ghost btn-sm"
						onClick={resetFile}
					>
						Change
					</button>
				)}
			</div>

			{phase === 'idle' && (
				<div className="mt-8 rounded-box border border-base-300 p-7 sm:p-9">
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						{title}
					</p>

					<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
						Ready to upload
					</h2>

					<p className="mt-3 max-w-xl leading-7 text-base-content/50">
						Upload this file to start {title.toLowerCase()}.
					</p>

					{operation.optionKind === 'compress' && (
						<div className="mt-8 max-w-sm">
							<label className="text-sm font-medium" htmlFor="target-size">
								Maximum target size (bytes)
							</label>
							<input
								id="target-size"
								type="number"
								min="1"
								step="1"
								className="input input-bordered mt-2 w-full"
								value={compressTarget}
								onChange={(event) => setCompressTarget(event.target.value)}
							/>
							<p className="mt-2 text-sm text-base-content/50">
								{Number(compressTarget) > 0 && Number.isFinite(Number(compressTarget))
									? `About ${formatTargetSize(Number(compressTarget))}. `
									: ''}
								This is a maximum target and may not be achievable for every image.
							</p>
						</div>
					)}

					{operation.optionKind === 'downsample' && (
						<div className="mt-8 grid max-w-xl gap-4 sm:grid-cols-2">
							<label className="text-sm font-medium" htmlFor="max-width">
								Maximum width
								<input
									id="max-width"
									type="number"
									min="1"
									step="1"
									className="input input-bordered mt-2 w-full"
									value={maxWidth}
									onChange={(event) => setMaxWidth(event.target.value)}
								/>
							</label>
							<label className="text-sm font-medium" htmlFor="max-height">
								Maximum height
								<input
									id="max-height"
									type="number"
									min="1"
									step="1"
									className="input input-bordered mt-2 w-full"
									value={maxHeight}
									onChange={(event) => setMaxHeight(event.target.value)}
								/>
							</label>
						</div>
					)}

					{optionResult.error && (
						<p className="mt-3 text-sm text-error" role="alert">
							{optionResult.error}
						</p>
					)}

					{isLoaded && !isSignedIn && (
						<p className="mt-4 text-sm text-base-content/55">
							<a
								href="/login"
								className="font-medium underline decoration-base-300 underline-offset-4 hover:decoration-base-content"
							>
								Sign in
							</a>{' '}
							to upload.
						</p>
					)}

					<div className="mt-10 flex items-center justify-between gap-5 border-t border-base-300 pt-6">
						<p className="text-sm text-base-content/45">
							Accepted: {typeHint}
						</p>

						<button
							type="button"
							className="btn btn-primary"
							onClick={handleUpload}
							disabled={!canUpload || Boolean(optionResult.error)}
						>
							Upload
						</button>
					</div>
				</div>
			)}

			{(phase === 'uploading' ||
				phase === 'uploaded' ||
				phase === 'starting' ||
				phase === 'streaming' ||
				phase === 'completed' ||
				phase === 'failed') && (
				<div className="mt-8 rounded-box border border-base-300 p-7 sm:p-9">
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						{title}
					</p>

					{phase === 'uploading' && (
						<>
							<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
								Uploading…
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								Sending your file. This usually takes a moment.
							</p>
						</>
					)}

					{phase === 'uploaded' && (
						<>
							<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
								File uploaded
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								Continue to start {title.toLowerCase()}.
							</p>

							<div className="mt-10 flex items-center justify-between gap-5 border-t border-base-300 pt-6">
								<button
									type="button"
									className="btn btn-ghost btn-sm"
									onClick={resetFile}
								>
									Start over
								</button>

								<button
									type="button"
									className="btn btn-primary"
									onClick={handleStart}
								>
									Continue
								</button>
							</div>
						</>
					)}

					{phase === 'starting' && (
						<>
							<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
								Starting…
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								Getting your file ready.
							</p>
						</>
					)}

					{phase === 'streaming' && (
						<>
							<div className="mt-4 flex flex-wrap items-center gap-3">
								<span className="badge badge-neutral badge-soft">
									{statusLabel}
								</span>
							</div>

							<h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">
								Working on your file
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								Status updates automatically. You can leave this
								page and come back later.
							</p>

							{creditsRemaining !== null && (
								<p className="mt-4 text-sm text-base-content/45">
									{creditsRemaining} free{' '}
									{creditsRemaining === 1 ? 'use' : 'uses'}{' '}
									left
								</p>
							)}

							<div className="mt-10 flex flex-wrap items-center gap-3 border-t border-base-300 pt-6">
								<a href="/app" className="btn btn-ghost">
									Back to desk
								</a>
							</div>
						</>
					)}

					{phase === 'completed' && downloadUrl && (
						<>
							<div className="mt-4 flex flex-wrap items-center gap-3">
								<span className="badge badge-success badge-soft">
									Ready
								</span>
							</div>

							<h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">
								Your file is ready
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								{title} finished successfully. Output format: {outputFormat}.
							</p>

							{downloadExpiresIn !== null && (
								<p className="mt-4 text-sm text-base-content/55">
									Download link expires in{' '}
									{formatExpiry(downloadExpiresIn)}.
								</p>
							)}

							<div className="mt-10 flex flex-wrap items-center gap-3 border-t border-base-300 pt-6">
								<a
									href={downloadUrl}
									className="btn btn-primary"
									download={downloadFilename ?? undefined}
								>
									Download
								</a>

								<button
									type="button"
									className="btn btn-ghost"
									onClick={resetFile}
								>
									Choose another file
								</button>
							</div>
						</>
					)}

					{phase === 'failed' && (
						<>
							<div className="mt-4 flex flex-wrap items-center gap-3">
								<span className="badge badge-error badge-soft">
									{error?.toLowerCase().includes('timed out')
										? 'Timed out'
										: "Couldn't finish"}
								</span>
							</div>

							<h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">
								{error?.toLowerCase().includes('timed out')
									? 'Processing timed out'
									: 'Conversion failed'}
							</h2>

							<p className="mt-3 max-w-xl leading-7 text-base-content/50">
								{error?.toLowerCase().includes('timed out')
									? 'The operation took too long to complete. Try again or check back later.'
									: 'Try a different file, or start over with the same tool.'}
							</p>

							<div className="mt-10 flex flex-wrap items-center gap-3 border-t border-base-300 pt-6">
								<button
									type="button"
									className="btn btn-primary"
									onClick={resetFile}
								>
									Try again
								</button>

								<a href="/app" className="btn btn-ghost">
									Back to desk
								</a>
							</div>
						</>
					)}
				</div>
			)}

			{fileInput}
		</section>
	);
}
