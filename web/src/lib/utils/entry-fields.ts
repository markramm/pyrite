import type { TypeFieldSchema } from '$lib/api/types';

/**
 * Coerce a raw string form value into the typed value the API expects,
 * based on the field's declared schema type.
 *
 * Checkbox values are expected as the strings `'true'` / `'false'` (the form
 * binds the checkbox's `checked` state to those strings) — NOT the raw `'on'`
 * that a native checkbox `.value` yields, which is why checkboxes previously
 * never saved as `true`.
 */
export function coerceFieldValue(value: string, schema: TypeFieldSchema | undefined): unknown {
	switch (schema?.type) {
		case 'number':
		case 'integer':
			return Number(value) || 0;
		case 'list':
			return value
				.split(',')
				.map((v) => v.trim())
				.filter(Boolean);
		case 'checkbox':
		case 'boolean':
			return value === 'true';
		default:
			return value;
	}
}

/**
 * Build the metadata object to send to the create-entry API from the raw
 * custom-field string map, coercing each non-empty value by its schema type.
 * Blank/whitespace-only values are omitted entirely.
 */
export function buildMetadata(
	customFields: Record<string, string>,
	fields: Record<string, TypeFieldSchema> | undefined
): Record<string, unknown> {
	const meta: Record<string, unknown> = {};
	for (const [key, value] of Object.entries(customFields)) {
		if (value.trim()) {
			meta[key] = coerceFieldValue(value, fields?.[key]);
		}
	}
	return meta;
}
