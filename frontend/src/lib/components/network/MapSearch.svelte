<script lang="ts">
	import { tick } from 'svelte';
	import { t, type TranslationKey, type Translator } from '$lib/i18n';
	import type { RailEventNode } from '$lib/types/event';
	import type { NetworkGraph } from '$lib/types/network';
	import type { Selected } from '$lib/types/selection';
	import type { TrainNode } from '$lib/types/train';

	export let graph: NetworkGraph;
	export let trains: TrainNode[];
	export let events: RailEventNode[];
	export let onSelect: (selected: Selected) => void = () => {};

	type CategoryId = 'station' | 'train' | 'segment' | 'incident';

	type Suggestion =
		| { kind: 'category'; id: CategoryId; label: string; count: number }
		| { kind: 'element'; categoryId: CategoryId; label: string; sub: string; sel: Selected };

	const CATEGORY_IDS: CategoryId[] = ['station', 'train', 'segment', 'incident'];
	const CATEGORY_ICONS: Record<CategoryId, string> = {
		station: '🚉',
		train: '🚆',
		segment: '🛤️',
		incident: '⚠️'
	};

	let query = '';
	let category: CategoryId | null = null;
	let open = false;
	let activeIndex = 0;
	let root: HTMLDivElement;
	let input: HTMLInputElement;
	let list: HTMLUListElement;

	/** Składanie do ASCII: wielkość liter i polskie znaki nie psują dopasowania. */
	function fold(text: string): string {
		return text
			.toLowerCase()
			.replace(/ł/g, 'l')
			.normalize('NFD')
			.replace(/[̀-ͯ]/g, '');
	}

	/** Klucze i18n budowane dynamicznie (kategoria/typ/status) — rzut na typ kluczy. */
	function key(dynamicKey: string): TranslationKey {
		return dynamicKey as TranslationKey;
	}

	function matches(needle: string, ...haystack: (string | null | undefined)[]): boolean {
		if (!needle) return true;
		return haystack.some((value) => value && fold(value).includes(needle));
	}

	function categoryLabel(id: CategoryId, translator: Translator): string {
		return translator(key(`search.category.${id}`));
	}

	$: stationById = new Map(graph.stations.map((station) => [station.id, station]));

	function stationName(id: string | null | undefined): string {
		if (!id) return '—';
		return stationById.get(id)?.name ?? id;
	}

	$: activeIncidents = events.filter((event) => event.status === 'active');

	function incidentSelection(event: RailEventNode): Selected | null {
		if (event.type === 'derailment' && event.trainId) return { kind: 'train', id: event.trainId };
		if (event.stationId) return { kind: 'station', id: event.stationId };
		if (event.segmentId) return { kind: 'segment', id: event.segmentId };
		return null;
	}

	function elementsOf(id: CategoryId, needle: string, translator: Translator): Suggestion[] {
		if (id === 'station') {
			return graph.stations
				.filter((s) => matches(needle, s.name, s.code, s.id))
				.map((s) => ({
					kind: 'element' as const,
					categoryId: id,
					label: s.name,
					sub: s.code,
					sel: { kind: 'station' as const, id: s.id }
				}));
		}
		if (id === 'train') {
			return trains
				.filter((train) => matches(needle, train.name, train.id))
				.map((train) => ({
					kind: 'element' as const,
					categoryId: id,
					label: train.name,
					sub: `${translator(key(`label.trainType.${train.type}`))} · ${translator(key(`label.trainStatus.${train.status}`))}`,
					sel: { kind: 'train' as const, id: train.id }
				}));
		}
		if (id === 'segment') {
			return graph.segments
				.filter((segment) =>
					matches(
						needle,
						segment.segmentId,
						stationName(segment.source),
						stationName(segment.target)
					)
				)
				.map((segment) => ({
					kind: 'element' as const,
					categoryId: id,
					label: `${stationName(segment.source)} – ${stationName(segment.target)}`,
					sub: `${segment.segmentId} · ${segment.distKm} km`,
					sel: { kind: 'segment' as const, id: segment.segmentId }
				}));
		}
		return activeIncidents
			.filter((event) =>
				matches(
					needle,
					translator(key(`label.event.${event.type}`)),
					stationName(event.stationId),
					stationName(event.fromStationId),
					stationName(event.toStationId)
				)
			)
			.flatMap((event) => {
				const sel = incidentSelection(event);
				if (sel === null) return [];
				const where = event.stationId
					? stationName(event.stationId)
					: `${stationName(event.fromStationId)} – ${stationName(event.toStationId)}`;
				return [
					{
						kind: 'element' as const,
						categoryId: id,
						label: translator(key(`label.event.${event.type}`)),
						sub: where,
						sel
					}
				];
			});
	}

	function buildSuggestions(
		needle: string,
		activeCategory: CategoryId | null,
		translator: Translator
	): Suggestion[] {
		if (activeCategory !== null) {
			return elementsOf(activeCategory, needle, translator).slice(0, 10);
		}
		const counts: Record<CategoryId, number> = {
			station: graph.stations.length,
			train: trains.length,
			segment: graph.segments.length,
			incident: activeIncidents.length
		};
		const categories: Suggestion[] = CATEGORY_IDS.filter((id) =>
			matches(needle, categoryLabel(id, translator))
		).map((id) => ({
			kind: 'category' as const,
			id,
			label: categoryLabel(id, translator),
			count: counts[id]
		}));
		// Bez frazy podpowiadamy tylko kategorie; z frazą dokładamy do nich
		// elementy ze wszystkich kategorii (po kilka na kategorię).
		if (!needle) return categories;
		const elements = CATEGORY_IDS.flatMap((id) => elementsOf(id, needle, translator).slice(0, 4));
		return [...categories, ...elements].slice(0, 14);
	}

	$: suggestions = open ? buildSuggestions(fold(query.trim()), category, $t) : [];
	$: if (activeIndex >= suggestions.length) activeIndex = 0;

	async function moveActive(delta: number) {
		if (suggestions.length === 0) return;
		activeIndex = (activeIndex + delta + suggestions.length) % suggestions.length;
		await tick();
		list?.querySelector('.active')?.scrollIntoView({ block: 'nearest' });
	}

	function pick(suggestion: Suggestion) {
		if (suggestion.kind === 'category') {
			category = suggestion.id;
			query = '';
			activeIndex = 0;
			input?.focus();
			return;
		}
		onSelect(suggestion.sel);
		open = false;
		query = '';
		category = null;
		input?.blur();
	}

	function clearAll() {
		query = '';
		category = null;
		activeIndex = 0;
		input?.focus();
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (open) {
				event.stopPropagation();
				open = false;
				input?.blur();
			}
			return;
		}
		if (event.key === 'Backspace' && query === '' && category !== null) {
			category = null;
			activeIndex = 0;
			return;
		}
		if (!open) return;
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			void moveActive(1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			void moveActive(-1);
		} else if (event.key === 'Enter') {
			const active = suggestions[activeIndex];
			if (active) {
				event.preventDefault();
				pick(active);
			}
		}
	}

	function handleWindowPointerDown(event: MouseEvent) {
		if (open && root && !root.contains(event.target as Node)) open = false;
	}
</script>

<svelte:window on:mousedown={handleWindowPointerDown} />

<div class="search" bind:this={root} role="search" aria-label={$t('search.aria')}>
	<div class="field" class:field-open={open && suggestions.length > 0}>
		<span class="icon" aria-hidden="true">🔍</span>
		{#if category !== null}
			<button
				type="button"
				class="chip"
				title={$t('search.clear')}
				on:click={() => {
					category = null;
					input?.focus();
				}}
			>
				{CATEGORY_ICONS[category]}
				{categoryLabel(category, $t)}
				<span class="chip-x">×</span>
			</button>
		{/if}
		<input
			bind:this={input}
			bind:value={query}
			type="text"
			placeholder={category === null ? $t('search.placeholder') : $t('search.placeholderNarrow')}
			on:focus={() => {
				open = true;
				activeIndex = 0;
			}}
			on:input={() => {
				open = true;
				activeIndex = 0;
			}}
			on:keydown={handleKeydown}
			aria-expanded={open}
			aria-autocomplete="list"
			role="combobox"
			aria-controls="map-search-listbox"
		/>
		{#if query !== '' || category !== null}
			<button type="button" class="clear" title={$t('search.clear')} on:click={clearAll}>
				×
			</button>
		{/if}
	</div>

	{#if open && suggestions.length > 0}
		<ul class="dropdown" id="map-search-listbox" role="listbox" bind:this={list}>
			{#each suggestions as suggestion, index (suggestion.kind === 'category' ? `c-${suggestion.id}` : `e-${suggestion.categoryId}-${suggestion.sel.kind}-${suggestion.sel.id}`)}
				{#if suggestion.kind === 'category'}
					{#if index === 0}
						<li class="group-header">{$t('search.categories')}</li>
					{/if}
					<li
						class="item"
						class:active={index === activeIndex}
						role="option"
						aria-selected={index === activeIndex}
					>
						<button
							type="button"
							on:mousedown|preventDefault
							on:click={() => pick(suggestion)}
							on:mousemove={() => (activeIndex = index)}
						>
							<span class="item-icon">{CATEGORY_ICONS[suggestion.id]}</span>
							<span class="item-label">{suggestion.label}</span>
							<span class="item-count">{suggestion.count}</span>
							<span class="item-go">→</span>
						</button>
					</li>
				{:else}
					{#if index > 0 && suggestions[index - 1].kind === 'category'}
						<li class="group-header">{$t('search.results')}</li>
					{/if}
					<li
						class="item"
						class:active={index === activeIndex}
						role="option"
						aria-selected={index === activeIndex}
					>
						<button
							type="button"
							on:mousedown|preventDefault
							on:click={() => pick(suggestion)}
							on:mousemove={() => (activeIndex = index)}
						>
							<span class="item-icon">{CATEGORY_ICONS[suggestion.categoryId]}</span>
							<span class="item-label">{suggestion.label}</span>
							<span class="item-sub">{suggestion.sub}</span>
						</button>
					</li>
				{/if}
			{/each}
			<li class="hint" aria-hidden="true">{$t('search.hint')}</li>
		</ul>
	{:else if open && query.trim() !== ''}
		<div class="dropdown empty">{$t('search.noResults', { query: query.trim() })}</div>
	{/if}
</div>

<style>
	.search {
		position: relative;
		width: min(430px, 92vw);
		font-family: 'Inter Variable', sans-serif;
	}

	.field {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 8px 12px;
		border-radius: 14px;
		background: rgba(15, 23, 42, 0.88);
		border: 1px solid rgba(148, 163, 184, 0.25);
		backdrop-filter: blur(10px);
		box-shadow: 0 16px 40px rgba(2, 6, 23, 0.4);
		transition: border-color 0.25s;
	}

	.field:focus-within {
		border-color: rgba(96, 165, 250, 0.7);
	}

	.field-open {
		border-bottom-left-radius: 4px;
		border-bottom-right-radius: 4px;
	}

	.icon {
		font-size: 0.85rem;
		opacity: 0.8;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 3px 9px;
		border-radius: 999px;
		border: 1px solid rgba(96, 165, 250, 0.55);
		background: rgba(37, 99, 235, 0.25);
		color: #bfdbfe;
		font: inherit;
		font-size: 0.74rem;
		font-weight: 600;
		white-space: nowrap;
		cursor: pointer;
	}

	.chip:hover .chip-x {
		color: #f8fafc;
	}

	.chip-x {
		color: #93c5fd;
		font-weight: 700;
	}

	input {
		flex: 1;
		min-width: 0;
		border: none;
		background: transparent;
		color: #f1f5f9;
		font: inherit;
		font-size: 0.86rem;
		outline: none;
	}

	input::placeholder {
		color: #64748b;
	}

	.clear {
		border: none;
		background: transparent;
		color: #94a3b8;
		font-size: 1.05rem;
		line-height: 1;
		cursor: pointer;
		padding: 0 2px;
	}

	.clear:hover {
		color: #f8fafc;
	}

	.dropdown {
		position: absolute;
		top: calc(100% + 6px);
		left: 0;
		right: 0;
		margin: 0;
		padding: 6px;
		list-style: none;
		border-radius: 14px;
		background: rgba(15, 23, 42, 0.94);
		border: 1px solid rgba(148, 163, 184, 0.25);
		backdrop-filter: blur(12px);
		box-shadow: 0 24px 60px rgba(2, 6, 23, 0.55);
		max-height: 330px;
		overflow-y: auto;
	}

	.dropdown.empty {
		padding: 14px;
		color: #94a3b8;
		font-size: 0.82rem;
	}

	.group-header {
		padding: 6px 10px 4px;
		font-size: 0.64rem;
		font-weight: 600;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: #64748b;
	}

	.item button {
		display: flex;
		align-items: center;
		gap: 9px;
		width: 100%;
		padding: 8px 10px;
		border: none;
		border-radius: 9px;
		background: transparent;
		color: inherit;
		font: inherit;
		text-align: left;
		cursor: pointer;
	}

	.item.active button {
		background: rgba(37, 99, 235, 0.3);
	}

	.item-icon {
		font-size: 0.85rem;
		flex: 0 0 auto;
	}

	.item-label {
		color: #f1f5f9;
		font-size: 0.85rem;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.item-sub {
		margin-left: auto;
		color: #94a3b8;
		font-size: 0.72rem;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex-shrink: 1;
	}

	.item-count {
		margin-left: auto;
		padding: 1px 8px;
		border-radius: 999px;
		background: rgba(30, 41, 59, 0.9);
		border: 1px solid rgba(148, 163, 184, 0.25);
		color: #cbd5e1;
		font-size: 0.7rem;
	}

	.item-go {
		color: #64748b;
		font-size: 0.8rem;
	}

	.hint {
		padding: 7px 10px 3px;
		border-top: 1px solid rgba(148, 163, 184, 0.15);
		margin-top: 4px;
		color: #475569;
		font-size: 0.68rem;
		text-align: center;
	}
</style>
