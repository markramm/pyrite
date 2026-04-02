<!--
  SkeletonLoader: Animated shimmer placeholder for loading states.
  Renders configurable placeholder bars that approximate the shape of real content.

  Variants:
  - default: generic text lines
  - "cards": entry-card-shaped skeletons (title + body + tags row)
  - "detail": entry detail page (header + prose body lines)
  - "timeline": timeline events with dot + card
  - "search": search result cards
-->
<script lang="ts">
  interface Props {
    /** Number of content lines (default variant) or cards/items (card variants) */
    lines?: number;
    /** Show a large header bar */
    header?: boolean;
    /** Layout variant */
    variant?: 'default' | 'cards' | 'detail' | 'timeline' | 'search';
  }

  let { lines = 3, header = false, variant = 'default' }: Props = $props();
</script>

{#if variant === 'cards'}
  <div class="space-y-3">
    {#each Array(lines) as _, i}
      <div class="animate-pulse rounded-lg border border-zinc-200 p-5 dark:border-zinc-700" style="border-left: 3px solid rgba(113,113,122,0.3)">
        <!-- Title row -->
        <div class="mb-3 flex items-center justify-between">
          <div class="h-5 w-2/5 rounded bg-zinc-200 dark:bg-zinc-800"></div>
          <div class="h-4 w-16 rounded bg-zinc-200 dark:bg-zinc-800"></div>
        </div>
        <!-- Body preview -->
        <div class="mb-3 space-y-2">
          <div class="h-3.5 w-full rounded bg-zinc-200 dark:bg-zinc-800"></div>
          <div class="h-3.5 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {65 + (i * 11) % 30}%"></div>
        </div>
        <!-- Tags row -->
        <div class="flex gap-2">
          <div class="h-5 w-14 rounded-full bg-zinc-200 dark:bg-zinc-800"></div>
          <div class="h-5 w-18 rounded-full bg-zinc-200 dark:bg-zinc-800"></div>
        </div>
      </div>
    {/each}
  </div>

{:else if variant === 'detail'}
  <div class="animate-pulse space-y-4 p-6">
    <!-- Title bar -->
    <div class="h-8 w-2/3 rounded bg-zinc-200 dark:bg-zinc-800"></div>
    <!-- Meta line -->
    <div class="flex gap-3">
      <div class="h-4 w-20 rounded bg-zinc-200 dark:bg-zinc-800"></div>
      <div class="h-4 w-24 rounded bg-zinc-200 dark:bg-zinc-800"></div>
      <div class="h-4 w-16 rounded bg-zinc-200 dark:bg-zinc-800"></div>
    </div>
    <!-- Body paragraphs -->
    <div class="mt-4 space-y-3">
      {#each Array(lines) as _, i}
        <div class="h-4 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {75 + (i * 13) % 25}%"></div>
      {/each}
    </div>
    <div class="mt-6 space-y-3">
      {#each Array(Math.max(2, lines - 2)) as _, i}
        <div class="h-4 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {60 + (i * 17) % 35}%"></div>
      {/each}
    </div>
  </div>

{:else if variant === 'timeline'}
  <div class="relative ml-4">
    <div class="absolute left-3 top-0 bottom-0 w-px bg-zinc-300 dark:bg-zinc-600"></div>
    {#each Array(lines) as _, i}
      <div class="relative mb-3 animate-pulse pl-10">
        <!-- Dot -->
        <div class="absolute left-1.5 top-2 h-3 w-3 rounded-full bg-zinc-300 ring-2 ring-white dark:bg-zinc-600 dark:ring-zinc-900"></div>
        <!-- Card -->
        <div class="rounded-lg border border-zinc-200 p-3 dark:border-zinc-700">
          <div class="flex items-center gap-3">
            <div class="h-3.5 w-20 rounded bg-zinc-200 dark:bg-zinc-800"></div>
            <div class="h-4 flex-1 rounded bg-zinc-200 dark:bg-zinc-800" style="max-width: {40 + (i * 19) % 35}%"></div>
          </div>
          <div class="mt-2 flex gap-2">
            <div class="h-4 w-12 rounded-full bg-zinc-200 dark:bg-zinc-800"></div>
            <div class="h-4 w-16 rounded-full bg-zinc-200 dark:bg-zinc-800"></div>
          </div>
        </div>
      </div>
    {/each}
  </div>

{:else if variant === 'search'}
  <div class="space-y-2">
    {#each Array(lines) as _, i}
      <div class="animate-pulse rounded-lg border border-zinc-200 p-4 dark:border-zinc-700" style="border-left: 3px solid rgba(113,113,122,0.3)">
        <div class="mb-2 flex items-center gap-2">
          <div class="h-5 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {30 + (i * 11) % 25}%"></div>
          <div class="h-4 w-14 rounded bg-zinc-200 dark:bg-zinc-800"></div>
          <div class="h-4 w-12 rounded bg-zinc-100 dark:bg-zinc-700"></div>
        </div>
        <div class="space-y-1.5">
          <div class="h-3.5 w-full rounded bg-zinc-200 dark:bg-zinc-800"></div>
          <div class="h-3.5 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {55 + (i * 7) % 30}%"></div>
        </div>
      </div>
    {/each}
  </div>

{:else}
  <!-- Default: simple text lines -->
  <div class="animate-pulse space-y-3">
    {#if header}
      <div class="h-8 w-2/3 rounded bg-zinc-200 dark:bg-zinc-800"></div>
    {/if}
    {#each Array(lines) as _, i}
      <div class="h-4 rounded bg-zinc-200 dark:bg-zinc-800" style="width: {70 + (i * 13) % 30}%"></div>
    {/each}
  </div>
{/if}
