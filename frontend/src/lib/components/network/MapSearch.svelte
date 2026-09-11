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
        station: 'train',
        train: 'directions_subway',
        segment: 'conversion_path',
        incident: 'warning'
    };

    let query = '';
    let category: CategoryId | null = null;
    let open = false;
    let activeIndex = 0;
    let root: HTMLDivElement;
    let input: HTMLInputElement;
    let list: HTMLUListElement;

    function fold(text: string): string {
        return text
            .toLowerCase()
            .replace(/ł/g, 'l')
            .normalize('NFD')
            .replace(/[̀-ͯ]/g, '');
    }

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

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<svelte:window on:mousedown={handleWindowPointerDown} />

<div class="search" bind:this={root} role="search" aria-label={$t('search.aria')}>
    <div class="field">
        <span class="material-symbols-outlined search-icon" aria-hidden="true">search</span>
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
                <span class="material-symbols-outlined chip-icon" aria-hidden="true">{CATEGORY_ICONS[category]}</span>
                <span>{categoryLabel(category, $t)}</span>
                <span class="material-symbols-outlined chip-x" aria-hidden="true">close</span>
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
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
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
                            <span class="material-symbols-outlined item-icon" aria-hidden="true">{CATEGORY_ICONS[suggestion.id]}</span>
                            <span class="item-label">{suggestion.label}</span>
                            <span class="item-count">{suggestion.count}</span>
                            <span class="material-symbols-outlined item-go" aria-hidden="true">chevron_right</span>
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
                            <span class="material-symbols-outlined item-icon" aria-hidden="true">{CATEGORY_ICONS[suggestion.categoryId]}</span>
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
        width: min(340px, 92vw);
        font-family: 'Inter Variable', Inter, sans-serif;
    }

    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 18px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-smoothing: antialiased;
        text-rendering: optimizeLegibility;
        -moz-osx-font-smoothing: grayscale;
        font-feature-settings: 'liga';
        font-variation-settings:
            'FILL' 0,
            'wght' 300,
            'GRAD' 0,
            'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    .field {
        display: flex;
        align-items: center;
        gap: 8px;
        height: 38px;
        padding: 0 12px;
        border-radius: 999px;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.22);
        box-sizing: border-box;
        transition: border-color 200ms ease;
    }

    .field:focus-within {
        border-color: rgba(255, 255, 255, 0.6);
    }

    .search-icon {
        font-size: 18px;
        color: #97a5ad;
        flex-shrink: 0;
    }

    .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        height: 24px;
        padding: 0 8px;
        border-radius: 6px;
        border: 0;
        background: rgba(255, 255, 255, 0.08);
        color: #f5f7f8;
        font-family: inherit;
        font-size: 0.66rem;
        font-weight: 400;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        white-space: nowrap;
        cursor: pointer;
        box-sizing: border-box;
        transition: background-color 150ms ease;
    }

    .chip:hover {
        background: rgba(255, 255, 255, 0.14);
    }

    .chip-icon {
        font-size: 14px;
        color: #97a5ad;
    }

    .chip-x {
        font-size: 13px;
        color: #97a5ad;
        margin-left: 2px;
    }

    input {
        flex: 1;
        min-width: 0;
        height: 100%;
        border: 0;
        background: transparent;
        color: #f5f7f8;
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        outline: none;
    }

    input::placeholder {
        color: #97a5ad;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .clear {
        border: 0;
        background: transparent;
        color: #97a5ad;
        cursor: pointer;
        width: 24px;
        height: 24px;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        transition: color 150ms ease, background-color 150ms ease;
    }

    .clear .material-symbols-outlined {
        font-size: 16px;
    }

    .clear:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.06);
    }

    .dropdown {
        position: absolute;
        top: calc(100% + 6px);
        left: 0;
        right: 0;
        margin: 0;
        padding: 6px;
        list-style: none;
        border-radius: 12px;
        background: rgba(20, 20, 20, 0.96);
        border: 0;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        max-height: 280px;
        overflow-y: auto;
        z-index: 40;
        animation: dropdown-fade 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        transform-origin: top;
    }

    @keyframes dropdown-fade {
        from {
            opacity: 0;
            transform: translateY(-6px) scale(0.98);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }

    .dropdown.empty {
        padding: 14px;
        color: #97a5ad;
        font-size: 0.72rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-align: center;
    }

    .group-header {
        padding: 6px 10px 4px;
        font-size: 0.6rem;
        font-weight: 400;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #64748b;
    }

    .item button {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 6px 10px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: inherit;
        font-family: inherit;
        text-align: left;
        cursor: pointer;
        transition: background-color 150ms ease;
    }

    .item button:hover,
    .item.active button {
        background: rgba(255, 255, 255, 0.06);
    }

    .item-icon {
        font-size: 17px;
        color: #97a5ad;
        flex: 0 0 auto;
    }

    .item-label {
        color: #f5f7f8;
        font-size: 0.74rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .item-sub {
        margin-left: auto;
        color: #97a5ad;
        font-size: 0.66rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex-shrink: 1;
    }

    .item-count {
        margin-left: auto;
        padding: 2px 6px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.05);
        color: #97a5ad;
        font-size: 0.64rem;
        font-weight: 300;
    }

    .item-go {
        font-size: 16px;
        color: #64748b;
    }

    .hint {
        padding: 8px 10px 4px;
        margin-top: 4px;
        color: #64748b;
        font-size: 0.62rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        text-align: center;
    }
</style>