import type { JobOperation, OperationOptionKind } from './api/jobs';

export type OperationCategory = 'image' | 'pdf' | 'text';

export type OperationStatus = 'live' | 'coming_soon';

export type ToolOperation = {
	slug: string;
	title: string;
	description: string;
	category: OperationCategory;
	status: OperationStatus;
	/** MIME types allowed for this tool page. Empty when coming soon. */
	allowedTypes: string[];
	/** Value for the file input `accept` attribute. */
	accept: string;
	/** API operation when live; null when not wired yet. */
	apiOperation: JobOperation | null;
	optionKind: OperationOptionKind;
	outputFormat: string;
	allowedExtensions: string[];
};

export const CATEGORIES: {
	id: OperationCategory;
	label: string;
}[] = [
	{ id: 'image', label: 'Image' },
	{ id: 'pdf', label: 'PDF' },
	{ id: 'text', label: 'Text' },
];

export const OPERATIONS: ToolOperation[] = [
	{
		slug: 'jpeg-to-png', title: 'JPEG to PNG', description: 'Convert a JPEG image to PNG.', category: 'image', status: 'live',
		allowedTypes: ['image/jpeg'], accept: '.jpg,.jpeg,image/jpeg', apiOperation: 'jpeg_to_png', optionKind: 'none', outputFormat: 'PNG', allowedExtensions: ['.jpg', '.jpeg'],
	},
	{
		slug: 'png-to-jpeg', title: 'PNG to JPEG', description: 'Convert a PNG image to JPEG.', category: 'image', status: 'live',
		allowedTypes: ['image/png'], accept: '.png,image/png', apiOperation: 'png_to_jpeg', optionKind: 'none', outputFormat: 'JPG', allowedExtensions: ['.png'],
	},
	{
		slug: 'png-to-webp', title: 'PNG to WebP', description: 'Convert a PNG image to WebP.', category: 'image', status: 'live',
		allowedTypes: ['image/png'], accept: '.png,image/png', apiOperation: 'png_to_webp', optionKind: 'none', outputFormat: 'WEBP', allowedExtensions: ['.png'],
	},
	{
		slug: 'webp-to-png', title: 'WebP to PNG', description: 'Convert a WebP image to PNG.', category: 'image', status: 'live',
		allowedTypes: ['image/webp'], accept: '.webp,image/webp', apiOperation: 'webp_to_png', optionKind: 'none', outputFormat: 'PNG', allowedExtensions: ['.webp'],
	},
	{
		slug: 'webp-to-jpeg', title: 'WebP to JPEG', description: 'Convert a WebP image to JPEG.', category: 'image', status: 'live',
		allowedTypes: ['image/webp'], accept: '.webp,image/webp', apiOperation: 'webp_to_jpeg', optionKind: 'none', outputFormat: 'JPG', allowedExtensions: ['.webp'],
	},
	{
		slug: 'jpeg-to-webp', title: 'JPEG to WebP', description: 'Convert a JPEG image to WebP.', category: 'image', status: 'live',
		allowedTypes: ['image/jpeg'], accept: '.jpg,.jpeg,image/jpeg', apiOperation: 'jpeg_to_webp', optionKind: 'none', outputFormat: 'WEBP', allowedExtensions: ['.jpg', '.jpeg'],
	},
	{
		slug: 'compress-image', title: 'Compress image', description: 'Reduce an image file size.', category: 'image', status: 'live',
		allowedTypes: ['image/jpeg', 'image/png', 'image/webp'], accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp', apiOperation: 'compress', optionKind: 'compress', outputFormat: 'same as input', allowedExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
	},
	{
		slug: 'downsample-image', title: 'Downsample image', description: 'Resize an image within maximum dimensions.', category: 'image', status: 'live',
		allowedTypes: ['image/jpeg', 'image/png', 'image/webp'], accept: '.jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp', apiOperation: 'downsample', optionKind: 'downsample', outputFormat: 'same as input', allowedExtensions: ['.jpg', '.jpeg', '.png', '.webp'],
	},
	...[
		['pdf-to-text', 'PDF to text', 'Extract text from a PDF.', 'pdf'],
		['compress-pdf', 'Compress PDF', 'Reduce a PDF file size.', 'pdf'],
		['pdf-to-images', 'PDF to images', 'Turn PDF pages into images.', 'pdf'],
		['md-to-html', 'MD to HTML', 'Convert Markdown to HTML.', 'text'],
		['html-to-md', 'HTML to MD', 'Convert HTML to Markdown.', 'text'],
		['txt-to-md', 'TXT to MD', 'Convert plain text to Markdown.', 'text'],
	].map(([slug, title, description, category]) => ({
		slug,
		title,
		description,
		category: category as OperationCategory,
		status: 'coming_soon' as const,
		allowedTypes: [],
		accept: '',
		apiOperation: null,
		optionKind: 'none' as const,
		outputFormat: '',
		allowedExtensions: [],
	})),
];

export function validateOperationFile(
	file: Pick<File, 'name' | 'type'>,
	operation: ToolOperation,
): string | null {
	const extension = file.name.includes('.')
		? `.${file.name.split('.').pop()!.toLowerCase()}`
		: '';

	if (!operation.allowedExtensions.includes(extension)) {
		return `Choose a ${operation.allowedExtensions
			.map((value) => value.slice(1).toUpperCase())
			.join(' or ')} file.`;
	}

	if (!operation.allowedTypes.includes(file.type)) {
		return `This file must be reported as ${operation.allowedTypes.join(' or ')}.`;
	}

	return null;
}

export function isOperationCategory(
	value: string,
): value is OperationCategory {
	return value === 'image' || value === 'pdf' || value === 'text';
}

export function getCategoryOps(category: OperationCategory): ToolOperation[] {
	return OPERATIONS.filter((op) => op.category === category);
}

export function getOperation(
	category: string,
	slug: string,
): ToolOperation | undefined {
	if (!isOperationCategory(category)) {
		return undefined;
	}

	return OPERATIONS.find(
		(op) => op.category === category && op.slug === slug,
	);
}

export function toolPath(op: ToolOperation): string {
	return `/tools/${op.category}/${op.slug}`;
}

export function categoryLabel(category: OperationCategory): string {
	return CATEGORIES.find((c) => c.id === category)?.label ?? category;
}
