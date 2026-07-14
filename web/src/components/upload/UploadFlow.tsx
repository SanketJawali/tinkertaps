import { useRef, useState } from 'react';

type Action = 'compress' | 'convert' | 'extract';

type SelectedFile = {
    file: File;
    kind: 'image' | 'pdf';
};

const IMAGE_TYPES = [
    'image/png',
    'image/jpeg',
    'image/webp',
];

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

export default function UploadFlow() {
    const inputRef = useRef<HTMLInputElement>(null);

    const [selectedFile, setSelectedFile] =
        useState<SelectedFile | null>(null);

    const [action, setAction] = useState<Action | null>(null);
    const [targetFormat, setTargetFormat] = useState('WEBP');
    const [dragging, setDragging] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function chooseFile(file: File) {
        setError(null);
        setAction(null);

        if (IMAGE_TYPES.includes(file.type)) {
            setSelectedFile({
                file,
                kind: 'image',
            });

            return;
        }

        if (file.type === 'application/pdf') {
            setSelectedFile({
                file,
                kind: 'pdf',
            });

            return;
        }

        setSelectedFile(null);
        setError('Choose a PNG, JPG, WEBP, or PDF file.');
    }

    function resetFile() {
        setSelectedFile(null);
        setAction(null);
        setError(null);

        if (inputRef.current) {
            inputRef.current.value = '';
        }
    }

    function start() {
        if (!selectedFile || !action) {
            return;
        }

        console.log({
            file: selectedFile.file,
            action,
            targetFormat:
                action === 'convert' ? targetFormat : undefined,
        });

        // Backend integration goes here.
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

                <p className="mt-5 text-center text-sm text-base-content/45">
                    3 free uses left today
                </p>
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

                <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={resetFile}
                >
                    Change
                </button>
            </div>

            {!action && (
                <div className="mt-10">
                    <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                        What do you need?
                    </p>

                    <div
                        className={[
                            'mt-5 grid overflow-hidden rounded-box border border-base-300',
                            selectedFile.kind === 'image'
                                ? 'md:grid-cols-2'
                                : '',
                        ].join(' ')}
                    >
                        {selectedFile.kind === 'image' && (
                            <>
                                <button
                                    type="button"
                                    className="group min-h-55 p-7 text-left transition-colors hover:bg-base-200/60 md:border-r md:border-base-300"
                                    onClick={() => setAction('compress')}
                                >
                                    <h3 className="text-2xl font-semibold tracking-[-0.035em]">
                                        Make it smaller
                                    </h3>

                                    <p className="mt-3 max-w-sm leading-7 text-base-content/50">
                                        Reduce the file size while keeping the
                                        image looking good.
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
                                        Turn the image into PNG, JPG, or WEBP.
                                    </p>

                                    <p className="mt-10 text-sm font-medium transition-transform group-hover:translate-x-1">
                                        Choose →
                                    </p>
                                </button>
                            </>
                        )}

                        {selectedFile.kind === 'pdf' && (
                            <button
                                type="button"
                                className="group min-h-55 p-7 text-left transition-colors hover:bg-base-200/60"
                                onClick={() => setAction('extract')}
                            >
                                <h3 className="text-2xl font-semibold tracking-[-0.035em]">
                                    Pull out the text
                                </h3>

                                <p className="mt-3 max-w-sm leading-7 text-base-content/50">
                                    Get the written text as a separate file.
                                </p>

                                <p className="mt-10 text-sm font-medium transition-transform group-hover:translate-x-1">
                                    Choose →
                                </p>
                            </button>
                        )}
                    </div>
                </div>
            )}

            {action && (
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
                                    We'll reduce the file size while keeping the
                                    image looking good.
                                </p>
                            </>
                        )}

                        {action === 'convert' && (
                            <>
                                <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                                    Change the format
                                </p>

                                <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
                                    Which format do you need?
                                </h2>

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
                            </>
                        )}

                        {action === 'extract' && (
                            <>
                                <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                                    Pull out the text
                                </p>

                                <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em]">
                                    Get the words without the PDF.
                                </h2>

                                <p className="mt-3 max-w-xl leading-7 text-base-content/50">
                                    We'll pull out the written text and give it
                                    back as a separate file.
                                </p>
                            </>
                        )}

                        <div className="mt-10 flex items-center justify-between gap-5 border-t border-base-300 pt-6">
                            <p className="text-sm text-base-content/45">
                                3 free uses left today
                            </p>

                            <button
                                type="button"
                                className="btn btn-primary"
                                onClick={start}
                            >
                                {action === 'compress' && 'Make it smaller'}
                                {action === 'convert' && 'Change my file'}
                                {action === 'extract' && 'Pull out the text'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}
