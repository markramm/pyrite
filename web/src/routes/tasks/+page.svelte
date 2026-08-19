<script lang="ts">
	import Topbar from '$lib/components/layout/Topbar.svelte';
	import LoadingState from '$lib/components/common/LoadingState.svelte';
	import { onMount } from 'svelte';
	import { listTasks, LANES, laneFor, daysStale, type Task, type Lane } from '$lib/api/tasks';

	let tasks = $state<Task[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let assignee = $state('mark');
	let kbFilter = $state('');

	async function load() {
		loading = true;
		error = null;
		try {
			const res = await listTasks({ assignee, status: 'open', kb: kbFilter || undefined });
			tasks = res.tasks;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not load tasks';
		} finally {
			loading = false;
		}
	}

	onMount(load);

	const kbs = $derived([...new Set(tasks.map((t) => t.kb_name))].sort());
	const byLane = $derived(
		LANES.map((lane) => ({
			...lane,
			items: tasks
				.filter((t) => laneFor(t) === lane.id)
				.sort((a, b) => b.priority - a.priority || (daysStale(b) ?? 0) - (daysStale(a) ?? 0))
		}))
	);
	const oldest = $derived(Math.max(1, ...tasks.map((t) => daysStale(t) ?? 0)));

	// Lanes where the next move is yours. Drives the one colour decision.
	const YOURS: Lane[] = ['now', 'decide', 'send'];
</script>

<Topbar title="Worklist" />

<div class="worklist">
	<header class="masthead">
		<div>
			<p class="eyebrow">Assigned to a person, not an agent</p>
			<h1>Worklist</h1>
		</div>
		<div class="controls">
			<label>
				<span>Assignee</span>
				<input bind:value={assignee} onchange={load} spellcheck="false" />
			</label>
			<label>
				<span>Knowledge base</span>
				<select bind:value={kbFilter} onchange={load}>
					<option value="">All</option>
					{#each kbs as k}<option value={k}>{k}</option>{/each}
				</select>
			</label>
		</div>
	</header>

	{#if loading}
		<LoadingState />
	{:else if error}
		<p class="notice error">{error}</p>
	{:else if tasks.length === 0}
		<p class="notice">
			Nothing is waiting on <strong>{assignee}</strong>. If that seems wrong, the tasks may still
			carry an old assignee — run <code>kb/scripts/human-worklist-migrate.py</code>.
		</p>
	{:else}
		<div class="lanes">
			{#each byLane as lane}
				<section class="lane" class:yours={YOURS.includes(lane.id)}>
					<header class="lane-head">
						<h2>{lane.label}</h2>
						<span class="count">{lane.items.length}</span>
						<p class="blurb">{lane.blurb}</p>
					</header>

					{#if lane.items.length === 0}
						<p class="lane-empty">Clear.</p>
					{:else}
						<ul>
							{#each lane.items as t (t.kb_name + t.id)}
								{@const days = daysStale(t)}
								<li>
									<a href={`/entries/${encodeURIComponent(t.id)}?kb=${encodeURIComponent(t.kb_name)}`}>
										<p class="title">{t.title || t.id}</p>
									</a>
									<p class="meta">
										<span class="pri">p{t.priority}</span>
										<span class="kb">{t.kb_name}</span>
										{#if days !== null}
											<span class="age">{days === 0 ? 'today' : `${days}d`}</span>
										{/if}
									</p>
									{#if days !== null && days > 0}
										<!-- The latency bar: length is days parked, scaled to the
										     oldest task on the board. Colour says whose move it is. -->
										<div
											class="latency"
											style={`--fill:${Math.max(2, Math.round((days / oldest) * 100))}%`}
											aria-hidden="true"
										></div>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
				</section>
			{/each}
		</div>
	{/if}
</div>

<style>
	.worklist {
		--paper: #efe9dc;
		--ink: #191713;
		--yours: #8c2f17;
		--theirs: #33513f;
		--pencil: #8b8579;
		--rule: #d6cfc0;
		background: var(--paper);
		color: var(--ink);
		min-height: 100%;
		padding: 2.5rem 2rem 4rem;
		font-family: 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
	}

	.masthead {
		display: flex;
		flex-wrap: wrap;
		gap: 1.5rem;
		align-items: flex-end;
		justify-content: space-between;
		border-bottom: 2px solid var(--ink);
		padding-bottom: 1rem;
		margin-bottom: 2.25rem;
	}
	.eyebrow {
		font-family: 'Roboto Condensed', 'Helvetica Neue', sans-serif;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.7rem;
		color: var(--pencil);
		margin: 0 0 0.35rem;
	}
	h1 {
		font-size: clamp(2rem, 5vw, 3rem);
		line-height: 0.95;
		margin: 0;
		letter-spacing: -0.02em;
	}
	.controls {
		display: flex;
		gap: 1.25rem;
		flex-wrap: wrap;
	}
	.controls label {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}
	.controls span {
		font-family: 'Roboto Condensed', sans-serif;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		font-size: 0.65rem;
		color: var(--pencil);
	}
	.controls input,
	.controls select {
		background: transparent;
		border: 0;
		border-bottom: 1px solid var(--pencil);
		padding: 0.2rem 0;
		font: inherit;
		font-size: 0.95rem;
		color: var(--ink);
		min-width: 9rem;
	}
	.controls input:focus-visible,
	.controls select:focus-visible {
		outline: 2px solid var(--yours);
		outline-offset: 3px;
	}

	.lanes {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
		gap: 2rem;
	}
	.lane-head {
		border-top: 3px solid var(--theirs);
		padding-top: 0.6rem;
		margin-bottom: 1.1rem;
	}
	.lane.yours .lane-head {
		border-top-color: var(--yours);
	}
	.lane-head h2 {
		display: inline;
		font-family: 'Roboto Condensed', sans-serif;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		font-size: 0.95rem;
		margin: 0;
	}
	.count {
		font-family: 'Roboto Condensed', sans-serif;
		font-size: 0.95rem;
		color: var(--pencil);
		margin-left: 0.4rem;
	}
	.blurb {
		font-size: 0.82rem;
		color: var(--pencil);
		font-style: italic;
		margin: 0.25rem 0 0;
	}

	.lane ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.lane li {
		padding: 0.7rem 0 0.8rem;
		border-bottom: 1px solid var(--rule);
	}
	.lane a {
		color: inherit;
		text-decoration: none;
	}
	.lane a:hover .title,
	.lane a:focus-visible .title {
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.lane a:focus-visible {
		outline: 2px solid var(--yours);
		outline-offset: 2px;
	}
	.title {
		margin: 0;
		font-size: 0.97rem;
		line-height: 1.35;
	}
	.meta {
		display: flex;
		gap: 0.7rem;
		margin: 0.35rem 0 0;
		font-family: 'Roboto Condensed', sans-serif;
		font-size: 0.72rem;
		letter-spacing: 0.04em;
		color: var(--pencil);
		text-transform: uppercase;
	}
	.pri {
		color: var(--ink);
	}

	.latency {
		height: 2px;
		margin-top: 0.5rem;
		background: var(--theirs);
		width: var(--fill);
		opacity: 0.55;
	}
	.lane.yours .latency {
		background: var(--yours);
		opacity: 0.8;
	}

	.lane-empty,
	.notice {
		color: var(--pencil);
		font-style: italic;
		font-size: 0.9rem;
	}
	.notice {
		max-width: 34rem;
		line-height: 1.6;
	}
	.notice.error {
		color: var(--yours);
		font-style: normal;
	}
	code {
		font-size: 0.85em;
		background: #e3dccd;
		padding: 0.1em 0.35em;
	}

	@media (prefers-color-scheme: dark) {
		.worklist {
			--paper: #17150f;
			--ink: #ece5d6;
			--yours: #d9714e;
			--theirs: #7fa88c;
			--pencil: #8f887a;
			--rule: #322d24;
		}
		code {
			background: #262117;
		}
	}
</style>
