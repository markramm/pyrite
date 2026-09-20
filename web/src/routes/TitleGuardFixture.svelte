<!--
  Test-only fixture for untitled-routes-guard.test.ts (#49).

  Mirrors the exact shape +layout.svelte renders in its <svelte:head>:
  a brand-name <title> guarded by route-id membership in UNTITLED_ROUTES,
  around a slot standing in for the routed page. Real SvelteKit page
  components declare their own <svelte:head><title> when titled (see
  e.g. src/routes/search/+page.svelte) — TitledChild and UntitledChild
  below stand in for that split so the test can drive route/brand changes
  without a full SvelteKit router.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { UNTITLED_ROUTES } from './brand-title-routes';

	let { routeId, brandName, children }: { routeId: string; brandName: string; children?: Snippet } = $props();
</script>

<svelte:head>
	{#if UNTITLED_ROUTES.includes(routeId)}
		<title>{brandName}</title>
	{/if}
</svelte:head>

{#if children}{@render children()}{/if}
