<!--
  LoadingState: Consistent loading indicator with spinner and message.
-->
<script lang="ts">
    interface Props {
        message?: string;
        size?: 'sm' | 'md' | 'lg';
        inline?: boolean;
    }
    let { message = 'Loading...', size = 'md', inline = false }: Props = $props();

    const sizeClasses = {
        sm: 'h-4 w-4 border',
        md: 'h-6 w-6 border-2',
        lg: 'h-8 w-8 border-2',
    };
</script>

{#if inline}
    <span class="inline-flex items-center gap-2 text-zinc-400">
        <span class="animate-spin rounded-full border-zinc-300 border-t-blue-600 {sizeClasses[size]}"></span>
        {#if message}<span class="text-sm">{message}</span>{/if}
    </span>
{:else}
    <div class="flex items-center justify-center py-12">
        <div class="flex items-center gap-3 text-zinc-400">
            <div class="animate-spin rounded-full border-zinc-300 border-t-blue-600 {sizeClasses[size]}"></div>
            <span class="text-sm">{message}</span>
        </div>
    </div>
{/if}
