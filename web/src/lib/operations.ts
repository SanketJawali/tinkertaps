import type { JobOperation } from './api/jobs';

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
	// Image — live
	{
		slug: 'jpeg-to-png',
		title: 'JPEG to PNG',
		description: 'Convert a JPEG image to PNG.',
		category: 'image',
		status: 'live',
		allowedTypes: ['image/jpeg'],
		accept: '.jpg,.jpeg,image/jpeg',
		apiOperation: 'convert',
	},
	// Image — coming soon
	{
		slug: 'png-to-jpeg',
		title: 'PNG to JPEG',
		description: 'Convert a PNG image to JPEG.',
		category: 'image',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'png-to-webp',
		title: 'PNG to WebP',
		description: 'Convert a PNG image to WebP.',
		category: 'image',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'webp-to-png',
		title: 'WebP to PNG',
		description: 'Convert a WebP image to PNG.',
		category: 'image',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'jpeg-to-webp',
		title: 'JPEG to WebP',
		description: 'Convert a JPEG image to WebP.',
		category: 'image',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'compress-image',
		title: 'Compress image',
		description: 'Reduce an image file size.',
		category: 'image',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	// PDF — coming soon
	{
		slug: 'pdf-to-text',
		title: 'PDF to text',
		description: 'Extract text from a PDF.',
		category: 'pdf',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'compress-pdf',
		title: 'Compress PDF',
		description: 'Reduce a PDF file size.',
		category: 'pdf',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'pdf-to-images',
		title: 'PDF to images',
		description: 'Turn PDF pages into images.',
		category: 'pdf',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	// Text — coming soon
	{
		slug: 'md-to-html',
		title: 'MD to HTML',
		description: 'Convert Markdown to HTML.',
		category: 'text',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'html-to-md',
		title: 'HTML to MD',
		description: 'Convert HTML to Markdown.',
		category: 'text',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
	{
		slug: 'txt-to-md',
		title: 'TXT to MD',
		description: 'Convert plain text to Markdown.',
		category: 'text',
		status: 'coming_soon',
		allowedTypes: [],
		accept: '',
		apiOperation: null,
	},
];

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
