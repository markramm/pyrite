<script lang="ts">
	interface Heading {
		level: number;
		text: string;
		slug: string;
	}

	interface Props {
		body: string;
	}

	let { body }: Props = $props();
	let activeSlug = $state('');

	const headings = $derived(parseHeadings(body));

	function parseHeadings(md: string): Heading[] {
		const result: Heading[] = [];
		const lines = md.split('\n');
		let inCodeBlock = false;

		for (const line of lines) {
			if (line.startsWith('```')) {
				inCodeBlock = !inCodeBlock;
				continue;
			}
			if (inCodeBlock) continue;

			const match = line.match(/^(#{1,6})\s+(.+)$/);
			if (match) {
				const text = match[2].trim();
				const slug = text
					.toLowerCase()
					.replace(/[^\w\s-]/g, '')
					.replace(/\s+/g, '-')
					.replace(/-+/g, '-')
					.trim();
				result.push({ level: match[1].length, text, slug });
			}
		}
		return result;
	}

	function scrollTo(slug: string) {
		const el = document.getElementById(slug);
		if (el) {
			el.scrollIntoView({ behavior: 'smooth', block: 'start' });
			activeSlug = slug;
		}
	}
</script>

<div class="p-4">
	<h3 class="mb-3 text-xs font-semibold uppercase tracking-wider text-zinc-500">Outline</h3>
	{#if headings.length === 0}
		<p class="text-sm text-zinc-400">No headings found.</p>
	{:else}
		<nav class="space-y-0.5">
			{#each headings as heading}
				<button
					onclick={() => scrollTo(heading.slug)}
					class="block w-full truncate rounded px-2 py-1 text-left text-sm transition-colors
						{activeSlug === heading.slug
						? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
						: 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800 dark:hover:text-zinc-200'}"
					style="padding-left: {0.5 + (heading.level - 1) * 0.75}rem"
					title={heading.text}
				>
					{heading.text}
				</button>
			{/each}
		</nav>
	{/if}
</div>
