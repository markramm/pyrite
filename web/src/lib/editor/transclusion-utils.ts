/**
 * Shared utilities for transclusion loading: cycle detection and WebSocket live updates.
 */

/**
 * Module-level set of entry IDs currently being loaded via transclusion.
 * Used to detect circular references (A transcludes B which transcludes A).
 *
 * When a transclusion starts loading, its target is added to this set.
 * When loading completes (or fails), the target is removed.
 * Before loading, we check if the target is already in the set — if so,
 * it means we have a circular transclusion chain.
 */
export const activeTransclusions = new Set<string>();

/**
 * Check if loading a given target would create a circular transclusion.
 * Returns true if the target is already being loaded in the current chain.
 */
export function isCircularTransclusion(target: string): boolean {
	return activeTransclusions.has(target);
}

/**
 * Mark a transclusion target as actively loading.
 * Call this before fetching content. Returns a cleanup function
 * that removes the target from the active set.
 */
export function markTransclusionActive(target: string): () => void {
	activeTransclusions.add(target);
	return () => {
		activeTransclusions.delete(target);
	};
}

/** Message shown when a circular transclusion is detected. */
export const CIRCULAR_REF_MESSAGE = '\u26A0 Circular reference detected';

/** Maximum depth for nested transclusions. */
export const MAX_TRANSCLUSION_DEPTH = 3;

/** Track current transclusion depth. */
let currentDepth = 0;

/** Check if the current transclusion depth has been exceeded. */
export function isDepthExceeded(): boolean {
	return currentDepth >= MAX_TRANSCLUSION_DEPTH;
}

/** Increment depth before loading a transclusion. Returns cleanup function. */
export function incrementDepth(): () => void {
	currentDepth++;
	return () => { currentDepth--; };
}

/** Reset depth counter (for testing). */
export function resetDepth(): void {
	currentDepth = 0;
}
