import { useAuth } from '@clerk/astro/react';
import { useEffect, useRef, useState } from 'react';

import {
	ApiError,
	createPresignedUpload,
	startJob,
	uploadFileToPresignedUrl,
	type JobOperation,
} from '../../lib/api/jobs';

type Action = JobOperation;
type Phase = 'configure' | 'uploading' | 'uploaded' | 'starting' | 'started';

type SelectedFile = {
	file: File;
	kind: 'image' | 'pdf';
};

const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];

const ACTION_QUERY_MAP: Record<string, Action> = {
	'compress-image': 'compress',
	'convert-image': 'convert',
	compress: 'compress',
	convert: 'convert',
};

function formatBytes(bytes: number) {
	if (bytes < 1024 * 1024) {
		return `${(bytes / 1024).toFixed(1)} KB`;
	}

	return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function getFileLabel(file: File) {
	const extension = file.name.split('.').pop();

	return extension?.toUpperCase() ?? 'FILE';
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

function actionLabel(action: Action) {
	if (action === 'compress') {
		return 'Make it smaller';
	}

	return 'Change the format';
}

function uploadButtonLabel(action: Action) {
	if (action === 'compress') {
		return 'Make it smaller';
	}

	return 'Change my file';
}

export default function UploadFlow() {
	const { getToken } = useAuth();
	const inputRef = useRef<HTMLInputElement>(null);

	const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
	const [action, setAction] = useState<Action | null>(null);
	const [preferredAction, setPreferredAction] = useState<Action | null>(null);
	const [targetFormat, setTargetFormat] = useState('WEBP');
	const [dragging, setDragging] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [phase, setPhase] = useState<Phase>('configure');
	const [jobId, setJobId] = useState<string | null>(null);
	const [creditsRemaining, setCreditsRemaining] = useState<number | null>(
		null,
	);

	useEffect(() => {
		const params = new URLSearchParams(window.location.search);
		const rawAction = params.get('action');

		if (!rawAction) {
			return;
		}

		const mapped = ACTION_QUERY_MAP[rawAction];

		if (mapped) {
			setPreferredAction(mapped);
		}
	}, []);

	function chooseFile(file: File) {
		setError(null);
		setPhase('configure');
		setJobId(null);
		setCreditsRemaining(null);

		if (IMAGE_TYPES.includes(file.type)) {
			setSelectedFile({ file, kind: 'image' });
			setAction(preferredAction);
			return;
		}

		if (file.type === 'application/pdf') {
			setSelectedFile({ file, kind: 'pdf' });
			setAction(preferredAction);
			return;
		}

		setSelectedFile(null);
		setAction(null);
		setError('Choose a PNG, JPG, WEBP, or PDF file.');
	}

	function resetFile() {
		setSelectedFile(null);
		setAction(null);
		setError(null);
		setPhase('configure');
		setJobId(null);
		setCreditsRemaining(null);

		if (inputRef.current) {
			inputRef.current.value = '';
		}
	}

	async function handleUpload() {
		if (!selectedFile || !action || phase === 'uploading') {
			return;
		}

		setError(null);
		setPhase('uploading');

		try {
			const contentType =
				selectedFile.file.type || 'application/octet-stream';

			const presign = await createPresignedUpload(
				{
					operation: action,
					filename: selectedFile.file.name,
					content_type: contentType,
				},
				getToken,
			);

			await uploadFileToPresignedUrl(
				presign.upload_url,
				selectedFile.file,
				contentType,
			);

			setJobId(presign.job_id);
			setPhase('uploaded');
		} catch (err) {
			setPhase('configure');
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
			setCreditsRemaining(result.credits_remaining);
			setPhase('started');
		} catch (err) {
			setPhase('uploaded');
			setError(userFacingError(err));
		}
	}

	if (!selectedFile) {
		return (
			<section className="mt-12">
				<div
					className={[
						'flex min-h-105 flex-col items-center justify-center rounded-box border p-8 text-center transition-colors',
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

						const file = event.dataTransfer.files[0];

						if (file) {
							chooseFile(file);
						}
					}}
				>
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						Your file
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
						Choose a file
					</button>

					<input
						ref={inputRef}
						type="file"
						className="hidden"
						accept=".png,.jpg,.jpeg,.webp,.pdf"
						onChange={(event) => {
							const file = event.target.files?.[0];

							if (file) {
								chooseFile(file);
							}
						}}
					/>

					<p className="mt-6 font-mono text-xs uppercase tracking-[0.12em] text-base-content/35">
						PNG · JPG · WEBP · PDF
					</p>
				</div>

				{error && (
					<p
						className="mt-4 text-center text-sm text-error"
						role="alert"
					>
						{error}
					</p>
				)}
			</section>
		);
	}

	return (
		<section className="mt-12">
			<div className="flex items-center justify-between gap-6 border-b border-base-300 pb-6">
				<div className="min-w-0">
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						Your file
					</p>

					<p className="mt-3 truncate text-xl font-semibold tracking-[-0.025em]">
						{selectedFile.file.name}
					</p>

					<p className="mt-1 text-sm text-base-content/45">
						{getFileLabel(selectedFile.file)} ·{' '}
						{formatBytes(selectedFile.file.size)}
					</p>
				</div>

				{phase === 'configure' && (
					<button
						type="button"
						className="btn btn-ghost btn-sm"
						onClick={resetFile}
					>
						Change
					</button>
				)}
			</div>

			{phase === 'configure' && !action && (
				<div className="mt-10">
					<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
						What do you need?
					</p>

					<div className="mt-5 grid overflow-hidden rounded-box border border-base-300 md:grid-cols-2">
						<button
							type="button"
							className="group min-h-55 p-7 text-left transition-colors hover:bg-base-200/60 md:border-r md:border-base-300"
							onClick={() => setAction('compress')}
						>
							<h3 className="text-2xl font-semibold tracking-[-0.035em]">
								Make it smaller
							</h3>

							<p className="mt-3 max-w-sm leading-7 text-base-content/50">
								Reduce the file size while keeping it looking
								good.
							</p>

							<p className="mt-10 text-sm font-medium transition-transform group-hover:translate-x-1">
								Choose →
							</p>
						</button>

						<button
							type="button"
							className="group min-h-55 border-t border-base-300 p-7 text-left transition-colors hover:bg-base-200/60 md:border-t-0"
							onClick={() => setAction('convert')}
						>
							<h3 className="text-2xl font-semibold tracking-[-0.035em]">
								Change the format
							</h3>

							<p className="mt-3 max-w-sm leading-7 text-base-content/50">
								{selectedFile.kind === 'image'
									? 'Turn the image into PNG, JPG, or WEBP.'
									: 'Turn the PDF into the format you need.'}
							</p>

							<p className="mt-10 text-sm font-medium transition-transform group-hover:translate-x-1">
								Choose →
							</p>
						</button>
					</div>
				</div>
			)}

			{phase === 'configure' && action && (
				<div className="mt-10">
					<button
						type="button"
						className="text-sm font-medium text-base-content/50 hover:text-base-content"
						onClick={() => setAction(null)}
					>
						← Back
					</button>

					<div className="mt-8 rounded-box border border-base-300 p-7 sm:p-9">
						{action === 'compress' && (
							<>
								<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
									Make it smaller
								</p>

								<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
									We'll take care of the details.
								</h2>

								<p className="mt-3 max-w-xl leading-7 text-base-content/50">
									We'll reduce the file size while keeping it
									looking good.
								</p>
							</>
						)}

						{action === 'convert' && (
							<>
								<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
									Change the format
								</p>

								<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
									{selectedFile.kind === 'image'
										? 'Which format do you need?'
										: "We'll change the format."}
								</h2>

								{selectedFile.kind === 'image' && (
									<div className="mt-7 flex flex-wrap gap-3">
										{['JPG', 'PNG', 'WEBP'].map((format) => (
											<button
												key={format}
												type="button"
												className={[
													'btn min-w-24',
													targetFormat === format
														? 'btn-primary'
														: 'btn-outline',
												].join(' ')}
												onClick={() =>
													setTargetFormat(format)
												}
											>
												{format}
											</button>
										))}
									</div>
								)}

								{selectedFile.kind === 'pdf' && (
									<p className="mt-3 max-w-xl leading-7 text-base-content/50">
										Upload the file, then continue when you're
										ready for us to work on it.
									</p>
								)}
							</>
						)}

						<div className="mt-10 flex items-center justify-between gap-5 border-t border-base-300 pt-6">
							<p className="text-sm text-base-content/45">
								Your file stays on this page until you continue.
							</p>

							<button
								type="button"
								className="btn btn-primary"
								onClick={handleUpload}
							>
								{uploadButtonLabel(action)}
							</button>
						</div>
					</div>
				</div>
			)}

			{(phase === 'uploading' ||
				phase === 'uploaded' ||
				phase === 'starting' ||
				phase === 'started') &&
				action && (
					<div className="mt-10 rounded-box border border-base-300 p-7 sm:p-9">
						<p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
							{actionLabel(action)}
						</p>

						{phase === 'uploading' && (
							<>
								<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
									Uploading…
								</h2>

								<p className="mt-3 max-w-xl leading-7 text-base-content/50">
									Sending your file securely. This usually
									takes a moment.
								</p>
							</>
						)}

						{phase === 'uploaded' && (
							<>
								<h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
									File is ready to continue.
								</h2>

								<p className="mt-3 max-w-xl leading-7 text-base-content/50">
									Your file is uploaded. Continue when you want
									us to {action === 'compress'
										? 'make it smaller'
										: 'change the format'}
									.
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
									Getting your file ready to work on.
								</p>
							</>
						)}

						{phase === 'started' && (
							<>
								<div className="mt-4 flex flex-wrap items-center gap-3">
									<span className="badge badge-neutral badge-soft">
										Working on it
									</span>
								</div>

								<h2 className="mt-5 text-3xl font-semibold tracking-[-0.04em]">
									We've started on your file.
								</h2>

								<p className="mt-3 max-w-xl leading-7 text-base-content/50">
									You can leave this page. Come back later when
									it's ready.
								</p>

								{creditsRemaining !== null && (
									<p className="mt-4 text-sm text-base-content/45">
										{creditsRemaining} free{' '}
										{creditsRemaining === 1 ? 'use' : 'uses'}{' '}
										left
									</p>
								)}

								<div className="mt-10 flex flex-wrap items-center gap-3 border-t border-base-300 pt-6">
									<a href="/app" className="btn btn-primary">
										Back to your desk
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
					</div>
				)}

			{error && (
				<p className="mt-4 text-sm text-error" role="alert">
					{error}
				</p>
			)}
		</section>
	);
}
