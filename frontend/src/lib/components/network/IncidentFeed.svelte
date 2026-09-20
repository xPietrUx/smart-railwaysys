<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { locale, t } from '$lib/i18n';
    import { createIncident } from '$lib/services/incidents';
    import { eventLabel, formatEventMessage } from '$lib/services/labels';
    import type { RailEventNode, RailEventType } from '$lib/types/event';
    import type { StationNode, TrackSegment } from '$lib/types/network';
    import type { Selected } from '$lib/types/selection';

    export let events: RailEventNode[];
    export let stations: StationNode[] = [];
    export let segments: TrackSegment[] = [];
    export let onSelect: (selected: Selected) => void = () => {};
    export let readOnly = false;
    /** Bieżący tryb wskazywania celu na mapie — właścicielem stanu jest strona
     *  panelu (mapa i ten formularz to rodzeństwo), stąd sterowanie przez propsy. */
    export let pickMode: 'segment' | 'station' | 'train' | null = null;
    export let onStartPick: (mode: 'segment' | 'station' | 'train', resolve: (id: string) => void) => void =
        () => {};
    export let onCancelPick: () => void = () => {};

    const INCIDENT_TYPES: RailEventType[] = ['line_failure', 'speed_restriction', 'signal_failure'];

    const TYPE_ICONS: Record<string, string> = {
        signal_failure: 'electric_bolt',
        line_failure: 'warning',
        speed_restriction: 'slow_motion_video'
    };

    let showCreateForm = false;
    let formType: RailEventType = 'line_failure';
    let formTargetId = '';
    let formDurationS: number | null = null;
    let submitting = false;
    let formError = '';

    let typeDropdownOpen = false;
    let targetDropdownOpen = false;

    let nowSec = Date.now() / 1000;
    let interval: ReturnType<typeof setInterval>;

    const INCIDENT_ICONS: Record<string, string> = {
        signal_failure: 'electric_bolt',
        derailment: 'warning',
        track_blockage: 'do_not_disturb_on',
        default: 'error'
    };

    function handleWindowClick(e: MouseEvent) {
        const target = e.target as HTMLElement | null;
        if (typeDropdownOpen && !target?.closest('.custom-select-type')) {
            typeDropdownOpen = false;
        }
        if (targetDropdownOpen && !target?.closest('.custom-select-target')) {
            targetDropdownOpen = false;
        }
    }

    onMount(() => {
        interval = setInterval(() => {
            nowSec = Date.now() / 1000;
        }, 1000);
        window.addEventListener('click', handleWindowClick);
    });
    onDestroy(() => {
        clearInterval(interval);
        window.removeEventListener('click', handleWindowClick);
        if (pickMode) onCancelPick();
    });

    function toggleTypeDropdown() {
        typeDropdownOpen = !typeDropdownOpen;
        if (typeDropdownOpen) targetDropdownOpen = false;
    }

    function toggleTargetDropdown() {
        targetDropdownOpen = !targetDropdownOpen;
        if (targetDropdownOpen) typeDropdownOpen = false;
    }

    function selectType(type: RailEventType) {
        formType = type;
        typeDropdownOpen = false;
        handleTypeChange();
    }

    function selectTarget(id: string) {
        formTargetId = id;
        targetDropdownOpen = false;
        if (formError) formError = '';
    }

    function countdownLabel(resolvesAt: number): string {
        const remaining = Math.max(0, Math.round(resolvesAt - nowSec));
        if (remaining <= 0) return $t('incidents.soon');
        const minutes = Math.floor(remaining / 60);
        const seconds = Math.floor(remaining % 60);
        return minutes > 0 ? `${minutes} min ${seconds}s` : `${seconds}s`;
    }

    $: stationById = new Map(stations.map((station) => [station.id, station.name]));

    function stationName(id: string | null): string {
        if (!id) return '—';
        return stationById.get(id) ?? id;
    }

    function selectIncident(event: RailEventNode) {
        if (event.type === 'derailment' && event.trainId) {
            onSelect({ kind: 'train', id: event.trainId });
        } else if (event.stationId) {
            onSelect({ kind: 'station', id: event.stationId });
        } else if (event.segmentId) {
            onSelect({ kind: 'segment', id: event.segmentId });
        }
    }

    $: segmentOptions = segments
        .filter((s) => s.forward.status === 'active' || s.backward.status === 'active')
        .map((s) => ({ id: s.segmentId, label: `${stationName(s.source)} – ${stationName(s.target)}` }));

    $: stationOptions = stations
        .filter((s) => !activeEvents.some((e) => e.type === 'signal_failure' && e.stationId === s.id))
        .map((s) => ({ id: s.id, label: s.name }));

    $: targetOptions = formType === 'signal_failure' ? stationOptions : segmentOptions;

    $: if (!targetOptions.some((option) => option.id === formTargetId)) {
        formTargetId = targetOptions[0]?.id ?? '';
    }

    function toggleCreateForm() {
        if (pickMode) onCancelPick();
        showCreateForm = !showCreateForm;
        formError = '';
        formDurationS = null;
        typeDropdownOpen = false;
        targetDropdownOpen = false;
    }

    function pickModeForType(type: RailEventType): 'segment' | 'station' {
        return type === 'signal_failure' ? 'station' : 'segment';
    }

    function startPickOnMap() {
        typeDropdownOpen = false;
        targetDropdownOpen = false;
        onStartPick(pickModeForType(formType), (id: string) => {
            formTargetId = id;
            if (formError) formError = '';
        });
    }

    function handleTypeChange() {
        if (pickMode) onCancelPick();
        typeDropdownOpen = false;
        targetDropdownOpen = false;
        if (formError) formError = '';
    }

    function validateDuration(): number | undefined | null {
        if (formDurationS === null || formDurationS === undefined || `${formDurationS}`.trim() === '') {
            return undefined; // opcjonalny czas trwania
        }
        const num = Number(formDurationS);
        if (isNaN(num) || !Number.isInteger(num)) {
            formError = $locale === 'pl'
                ? 'Czas trwania musi być liczbą całkowitą sekund.'
                : 'Duration must be an integer number of seconds.';
            return null;
        }
        if (num < 1 || num > 86400) {
            formError = $locale === 'pl'
                ? 'Czas trwania musi wynosić od 1 do 86400 sekund (maks. 24h).'
                : 'Duration must be between 1 and 86400 seconds (max 24h).';
            return null;
        }
        return num;
    }

    async function handleCreateIncident() {
        if (submitting) return;

        if (!formTargetId) {
            formError = $locale === 'pl'
                ? 'Wybierz cel zdarzenia z listy lub wskaż go na mapie.'
                : 'Please select a target from the list or pick it on the map.';
            return;
        }

        const validDuration = validateDuration();
        if (validDuration === null) return;

        submitting = true;
        formError = '';
        try {
            const created = await createIncident(fetch, {
                type: formType,
                targetId: formTargetId,
                durationS: validDuration
            });
            showCreateForm = false;
            selectIncident(created);
        } catch (err) {
            formError = err instanceof Error ? err.message : $t('incidents.form.error');
        } finally {
            submitting = false;
        }
    }

    $: activeEvents = events
        .filter((event) => event.status === 'active')
        .slice()
        .sort((a, b) => b.startedAt - a.startedAt);

    $: resolvedEvents = events
        .filter((event) => event.status === 'resolved')
        .slice()
        .sort((a, b) => (b.resolvedAt ?? 0) - (a.resolvedAt ?? 0))
        .slice(0, 5);
</script>

<svelte:head>
    <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
    />
</svelte:head>

<div class="panel incidents">
    <div class="panel-header">
        <div>
            <p class="panel-label">{$t('incidents.live')}</p>
            <h2>
                <span>{$t('incidents.title')}</span>
                {#if activeEvents.length > 0}
                    <span class="count">{activeEvents.length}</span>
                {/if}
                {#if !readOnly}
                    <button
                        type="button"
                        class="add-btn"
                        on:click={toggleCreateForm}
                        aria-expanded={showCreateForm}
                        aria-label={$t('incidents.addTitle') || 'Dodaj incydent'}
                        title={$t('incidents.addTitle')}
                    >
                        <span class="material-symbols-outlined" aria-hidden="true">
                            {showCreateForm ? 'close' : 'add'}
                        </span>
                    </button>
                {/if}
            </h2>
        </div>
    </div>

    {#if showCreateForm}
        <form class="create-form" on:submit|preventDefault={handleCreateIncident} novalidate>
            <label class="field">
                <span>{$t('incidents.form.type')}</span>
                <div class="custom-select custom-select-type">
                    <button
                        type="button"
                        class="select-trigger"
                        class:open={typeDropdownOpen}
                        on:click|stopPropagation={toggleTypeDropdown}
                        aria-expanded={typeDropdownOpen}
                    >
                        <span class="trigger-label">{eventLabel(formType, $t)}</span>
                        <span class="material-symbols-outlined chevron" aria-hidden="true">expand_more</span>
                    </button>
                    {#if typeDropdownOpen}
                        <ul class="dropdown" role="listbox">
                            {#each INCIDENT_TYPES as type (type)}
                                <li class="item" class:active={type === formType}>
                                    <button
                                        type="button"
                                        on:click={() => selectType(type)}
                                    >
                                        <span class="material-symbols-outlined item-icon" aria-hidden="true">
                                            {TYPE_ICONS[type] ?? 'error'}
                                        </span>
                                        <span class="item-label">{eventLabel(type, $t)}</span>
                                        {#if type === formType}
                                            <span class="material-symbols-outlined item-check" aria-hidden="true">check</span>
                                        {/if}
                                    </button>
                                </li>
                            {/each}
                        </ul>
                    {/if}
                </div>
            </label>

            <label class="field">
                <span>{$t('incidents.form.target')}</span>
                {#if pickMode}
                    <div class="picking-hint">
                        <span class="material-symbols-outlined pick-icon" aria-hidden="true">touch_app</span>
                        <span>{$t('incidents.form.pickHint')}</span>
                        <button type="button" class="ghost-btn" on:click={onCancelPick}>
                            {$t('incidents.form.cancel')}
                        </button>
                    </div>
                {:else if targetOptions.length === 0}
                    <p class="no-targets">{$t('incidents.form.noTargets')}</p>
                {:else}
                    <div class="target-row">
                        <div class="custom-select custom-select-target">
                            <button
                                type="button"
                                class="select-trigger"
                                class:open={targetDropdownOpen}
                                on:click|stopPropagation={toggleTargetDropdown}
                                aria-expanded={targetDropdownOpen}
                            >
                                <span class="trigger-label">
                                    {targetOptions.find((o) => o.id === formTargetId)?.label ?? formTargetId}
                                </span>
                                <span class="material-symbols-outlined chevron" aria-hidden="true">expand_more</span>
                            </button>
                            {#if targetDropdownOpen}
                                <ul class="dropdown" role="listbox">
                                    {#each targetOptions as option (option.id)}
                                        <li class="item" class:active={option.id === formTargetId}>
                                            <button
                                                type="button"
                                                on:click={() => selectTarget(option.id)}
                                            >
                                                <span class="item-label">{option.label}</span>
                                                {#if option.id === formTargetId}
                                                    <span class="material-symbols-outlined item-check" aria-hidden="true">check</span>
                                                {/if}
                                            </button>
                                        </li>
                                    {/each}
                                </ul>
                            {/if}
                        </div>
                        <button
                            type="button"
                            class="pick-btn"
                            on:click={startPickOnMap}
                            title={$t('incidents.form.pickOnMap')}
                            aria-label={$t('incidents.form.pickOnMap')}
                        >
                            <span class="material-symbols-outlined" aria-hidden="true">my_location</span>
                        </button>
                    </div>
                {/if}
            </label>

            <label class="field">
                <span>{$t('incidents.form.duration')}</span>
                <input
                    type="number"
                    min="1"
                    max="86400"
                    step="1"
                    placeholder={$t('incidents.form.durationPlaceholder')}
                    bind:value={formDurationS}
                    on:input={() => { if (formError) formError = ''; }}
                />
            </label>

            {#if formError}
                <div class="error" role="alert">
                    <span class="material-symbols-outlined error-icon" aria-hidden="true">error</span>
                    <span>{formError}</span>
                </div>
            {/if}

            <div class="form-actions">
                <button type="button" class="ghost-btn" on:click={toggleCreateForm}>
                    {$t('incidents.form.cancel')}
                </button>
                <button
                    type="submit"
                    class="submit-btn"
                    disabled={submitting || !!pickMode || !formTargetId}
                >
                    {submitting ? $t('incidents.form.submitting') : $t('incidents.form.submit')}
                </button>
            </div>
        </form>
    {/if}

    <div class="scroll-area">
        {#if activeEvents.length === 0}
            <p class="empty">{$t('incidents.empty')}</p>
        {:else}
            <ul class="incident-list">
                {#each activeEvents as event (event.id)}
                    <li>
                        <button
                            type="button"
                            class="incident active-incident severity-{event.severity}"
                            on:click={() => selectIncident(event)}
                            title={$t('incidents.showOnMap')}
                        >
                            <span class="material-symbols-outlined icon" aria-hidden="true">
                                {INCIDENT_ICONS[event.type] ?? INCIDENT_ICONS.default}
                            </span>
                            <div class="incident-body">
                                <strong>{eventLabel(event.type, $t)}</strong>
                                <p>{formatEventMessage(event, $t, stationName)}</p>
                                <small>
                                    {$t('incidents.resolvesIn', { time: countdownLabel(event.resolvesAt) })}
                                </small>
                            </div>
                        </button>
                    </li>
                {/each}
            </ul>
        {/if}

        {#if resolvedEvents.length > 0}
            <div class="section">
                <h3>{$t('incidents.recentlyResolved')}</h3>
                <ul class="incident-list resolved">
                    {#each resolvedEvents as event (event.id)}
                        <li>
                            <div class="incident">
                                <span class="material-symbols-outlined icon" aria-hidden="true">
                                    {INCIDENT_ICONS[event.type] ?? INCIDENT_ICONS.default}
                                </span>
                                <div class="incident-body">
                                    <strong>{eventLabel(event.type, $t)}</strong>
                                    <p>{formatEventMessage(event, $t, stationName)}</p>
                                </div>
                            </div>
                        </li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>
</div>

<style>
    .material-symbols-outlined {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 19px;
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
            'wght' 200,
            'GRAD' 0,
            'opsz' 24;
        user-select: none;
        vertical-align: middle;
    }

    .panel {
        --panel-bg: rgba(20, 20, 20, 0.94);
        --panel-shadow: 0 20px 48px rgba(0, 0, 0, 0.6);
        --panel-border: 1px solid rgba(255, 255, 255, 0.06);
        --panel-title: #ffffff;
        --panel-text: #f5f7f8;
        --panel-muted: #97a5ad;
        --card-bg: rgba(255, 255, 255, 0.03);
        --card-bg-hover: rgba(255, 255, 255, 0.07);
        --input-bg: rgba(255, 255, 255, 0.05);
        --input-bg-hover: rgba(255, 255, 255, 0.08);
        --input-border: 1px solid rgba(255, 255, 255, 0.12);
        --input-border-hover: 1px solid rgba(255, 255, 255, 0.22);
        --input-border-focus: var(--severity-minor-color, #f0c29a);
        --input-ring-focus: rgba(240, 194, 154, 0.25);
        --severity-major-bg: rgba(222, 132, 137, 0.1);
        --severity-major-hover: rgba(222, 132, 137, 0.16);
        --severity-major-color: #de8489;
        --severity-minor-bg: rgba(240, 194, 154, 0.1);
        --severity-minor-hover: rgba(240, 194, 154, 0.16);
        --severity-minor-color: #f0c29a;
        --count-bg: rgba(222, 132, 137, 0.15);
        --count-color: #de8489;
        --focus-ring: rgba(255, 255, 255, 0.65);

        background: var(--panel-bg);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: var(--panel-border);
        box-shadow: var(--panel-shadow);
        border-radius: 14px;
        padding: 16px 18px;
        display: flex;
        flex-direction: column;
        max-height: min(420px, calc(100vh - 340px));
        min-height: 0;
        box-sizing: border-box;
        font-family: 'Inter Variable', Inter, sans-serif;
        color: var(--panel-text);
        transition: background-color 200ms ease, color 200ms ease, border-color 200ms ease;
    }

    :global(html.light-mode) .panel.incidents,
    :global([data-theme='light']) .panel.incidents,
    :global(.light) .panel.incidents {
        --panel-bg: rgba(244, 245, 243, 0.96);
        --panel-shadow: 0 20px 48px rgba(0, 0, 0, 0.08);
        --panel-border: 1px solid rgba(0, 0, 0, 0.08);
        --panel-title: #111827;
        --panel-text: #1f2933;
        --panel-muted: #52606a;
        --card-bg: rgba(0, 0, 0, 0.03);
        --card-bg-hover: rgba(0, 0, 0, 0.06);
        --input-bg: rgba(0, 0, 0, 0.04);
        --input-bg-hover: rgba(0, 0, 0, 0.07);
        --input-border: 1px solid rgba(0, 0, 0, 0.14);
        --input-border-hover: 1px solid rgba(0, 0, 0, 0.26);
        --input-border-focus: var(--severity-minor-color, #c97d39);
        --input-ring-focus: rgba(201, 125, 57, 0.22);
        --severity-major-bg: rgba(201, 81, 88, 0.12);
        --severity-major-hover: rgba(201, 81, 88, 0.2);
        --severity-major-color: #c95158;
        --severity-minor-bg: rgba(201, 125, 57, 0.12);
        --severity-minor-hover: rgba(201, 125, 57, 0.2);
        --severity-minor-color: #c97d39;
        --count-bg: rgba(201, 81, 88, 0.15);
        --count-color: #c95158;
        --focus-ring: rgba(17, 24, 39, 0.65);
    }

    button:focus,
    .field input:focus {
        outline: none;
    }

    button:focus-visible,
    .field input:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .panel-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 12px;
        padding-right: 28px;
        flex-shrink: 0;
    }

    .add-btn {
        flex-shrink: 0;
        width: 24px;
        height: 24px;
        border-radius: 50%;
        border: 0;
        background: var(--card-bg);
        color: var(--panel-text);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        margin-left: 4px;
        transition: opacity 150ms ease;
    }

    .add-btn:hover {
        opacity: 0.7;
    }

    .add-btn .material-symbols-outlined {
        font-size: 16px;
    }

    .create-form {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 14px;
        padding: 14px;
        border-radius: 14px;
        background: var(--search-dropdown-bg, rgba(20, 20, 20, 0.94));
        border: var(--search-dropdown-border, 1px solid rgba(255, 255, 255, 0.06));
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: var(--search-dropdown-shadow, 0 20px 48px rgba(0, 0, 0, 0.6));
        flex-shrink: 0;
    }

    :global(html.light-mode) .create-form,
    :global([data-theme='light']) .create-form,
    :global(.light) .create-form {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .field > span {
        font-size: 0.62rem;
        font-weight: 300;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--search-header, #64748b);
    }

    :global(html.light-mode) .field > span,
    :global([data-theme='light']) .field > span,
    :global(.light) .field > span {
        color: #52606a;
    }

    .field input {
        width: 100%;
        height: 38px;
        box-sizing: border-box;
        padding: 0 14px;
        border-radius: 999px;
        border: var(--search-border, 1px solid rgba(255, 255, 255, 0.08));
        background: var(--search-field-bg, rgba(20, 20, 20, 0.92));
        color: var(--search-text, #f5f7f8);
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        outline: none;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: border-color 200ms ease, background-color 200ms ease;
    }

    :global(html.light-mode) .field input,
    :global([data-theme='light']) .field input,
    :global(.light) .field input {
        border: 1px solid rgba(0, 0, 0, 0.08);
        background: rgba(244, 245, 243, 0.96);
        color: #1f2933;
    }

    .field input:focus {
        border-color: var(--search-border-focus, rgba(255, 255, 255, 0.65));
        box-shadow: none;
    }

    :global(html.light-mode) .field input:focus,
    :global([data-theme='light']) .field input:focus,
    :global(.light) .field input:focus {
        border-color: rgba(17, 24, 39, 0.65);
    }

    .field input::placeholder {
        color: var(--search-placeholder, #97a5ad);
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    :global(html.light-mode) .field input::placeholder,
    :global([data-theme='light']) .field input::placeholder,
    :global(.light) .field input::placeholder {
        color: #52606a;
    }

    .field input[type='number']::-webkit-inner-spin-button,
    .field input[type='number']::-webkit-outer-spin-button {
        -webkit-appearance: none;
        appearance: none;
        margin: 0;
    }

    .field input[type='number'] {
        -moz-appearance: textfield;
        appearance: textfield;
    }

    .custom-select {
        position: relative;
        width: 100%;
    }

    .target-row {
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
    }

    .target-row .custom-select {
        flex: 1;
        min-width: 0;
    }

    .select-trigger {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        height: 38px;
        box-sizing: border-box;
        padding: 0 14px;
        border-radius: 999px;
        border: var(--search-border, 1px solid rgba(255, 255, 255, 0.08));
        background: var(--search-field-bg, rgba(20, 20, 20, 0.92));
        color: var(--search-text, #f5f7f8);
        font-family: inherit;
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: border-color 200ms ease, background-color 200ms ease, opacity 150ms ease;
    }

    :global(html.light-mode) .select-trigger,
    :global([data-theme='light']) .select-trigger,
    :global(.light) .select-trigger {
        border: 1px solid rgba(0, 0, 0, 0.08);
        background: rgba(244, 245, 243, 0.96);
        color: #1f2933;
    }

    .select-trigger:focus,
    .select-trigger.open {
        border-color: var(--search-border-focus, rgba(255, 255, 255, 0.65));
        outline: none;
    }

    :global(html.light-mode) .select-trigger:focus,
    :global(html.light-mode) .select-trigger.open,
    :global([data-theme='light']) .select-trigger:focus,
    :global([data-theme='light']) .select-trigger.open,
    :global(.light) .select-trigger:focus,
    :global(.light) .select-trigger.open {
        border-color: rgba(17, 24, 39, 0.65);
    }

    .trigger-label {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        flex: 1;
        text-align: left;
    }

    .chevron {
        font-size: 18px;
        color: var(--search-muted, #97a5ad);
        transition: transform 180ms ease;
        flex-shrink: 0;
        margin-left: 6px;
    }

    .select-trigger.open .chevron {
        transform: rotate(180deg);
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
        background: var(--search-dropdown-bg, rgba(20, 20, 20, 0.96));
        border: var(--search-dropdown-border, 1px solid rgba(255, 255, 255, 0.06));
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: var(--search-dropdown-shadow, 0 20px 48px rgba(0, 0, 0, 0.6));
        max-height: 220px;
        overflow-y: auto;
        z-index: 50;
        animation: dropdown-fade 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
        transform-origin: top;
    }

    :global(html.light-mode) .dropdown,
    :global([data-theme='light']) .dropdown,
    :global(.light) .dropdown {
        background: rgba(255, 255, 255, 0.98);
        border: 1px solid rgba(0, 0, 0, 0.08);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
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

    .dropdown .item {
        margin: 0;
        padding: 0;
    }

    .dropdown .item button {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 8px 10px;
        border: 0;
        border-radius: 8px;
        background: transparent;
        color: var(--search-text, #f5f7f8);
        font-family: inherit;
        font-size: 0.74rem;
        font-weight: 300;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        text-align: left;
        cursor: pointer;
        transition: background-color 150ms ease;
    }

    :global(html.light-mode) .dropdown .item button,
    :global([data-theme='light']) .dropdown .item button,
    :global(.light) .dropdown .item button {
        color: #1f2933;
    }

    .dropdown .item button:hover,
    .dropdown .item.active button {
        background: var(--search-item-hover, rgba(255, 255, 255, 0.06));
    }

    :global(html.light-mode) .dropdown .item button:hover,
    :global(html.light-mode) .dropdown .item.active button,
    :global([data-theme='light']) .dropdown .item button:hover,
    :global([data-theme='light']) .dropdown .item.active button,
    :global(.light) .dropdown .item button:hover,
    :global(.light) .dropdown .item.active button {
        background: rgba(0, 0, 0, 0.05);
    }

    .item-icon {
        font-size: 17px;
        color: var(--search-muted, #97a5ad);
        flex-shrink: 0;
    }

    .item-label {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .item-check {
        font-size: 16px;
        color: var(--severity-minor-color, #f0c29a);
        flex-shrink: 0;
    }

    .pick-btn {
        flex-shrink: 0;
        width: 38px;
        height: 38px;
        border-radius: 999px;
        border: var(--search-border, 1px solid rgba(255, 255, 255, 0.08));
        background: var(--search-field-bg, rgba(20, 20, 20, 0.92));
        color: var(--search-muted, #97a5ad);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        transition: border-color 200ms ease, opacity 150ms ease;
    }

    :global(html.light-mode) .pick-btn,
    :global([data-theme='light']) .pick-btn,
    :global(.light) .pick-btn {
        border: 1px solid rgba(0, 0, 0, 0.08);
        background: rgba(244, 245, 243, 0.96);
        color: #52606a;
    }

    .pick-btn:hover {
        border-color: var(--search-border-focus, rgba(255, 255, 255, 0.65));
        opacity: 0.75;
    }

    .pick-btn .material-symbols-outlined {
        font-size: 17px;
    }

    .picking-hint {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 8px;
        background: var(--severity-minor-bg);
        color: var(--severity-minor-color);
        font-size: 0.72rem;
        text-transform: none;
        letter-spacing: normal;
        flex-wrap: wrap;
    }

    .pick-icon {
        font-size: 16px;
        flex-shrink: 0;
    }

    .picking-hint .ghost-btn {
        margin-left: auto;
        padding: 4px 8px;
    }

    .form-actions {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 8px;
        margin-top: 4px;
    }

    .ghost-btn {
        background: transparent;
        border: 0;
        color: var(--search-muted, #97a5ad);
        font-size: 0.68rem;
        font-weight: 300;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        padding: 8px 14px;
        border-radius: 999px;
        transition: opacity 150ms ease, background-color 150ms ease;
    }

    .ghost-btn:hover {
        opacity: 0.7;
        background: var(--search-chip-bg, rgba(255, 255, 255, 0.08));
    }

    .submit-btn {
        background: #6cb09f;
        color: #0e1e19;
        border: 0;
        border-radius: 999px;
        padding: 8px 16px;
        font-size: 0.68rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        cursor: pointer;
        transition: opacity 150ms ease;
    }

    :global(html.light-mode) .submit-btn,
    :global([data-theme='light']) .submit-btn,
    :global(.light) .submit-btn {
        background: #4e9b89;
        color: #ffffff;
    }

    .submit-btn:hover:not(:disabled) {
        opacity: 0.75;
    }

    .submit-btn:disabled {
        opacity: 0.35;
        cursor: not-allowed;
    }

    .create-form .error {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        color: var(--severity-major-color);
        text-transform: none;
        letter-spacing: normal;
        line-height: 1.35;
        padding: 4px 0;
    }

    .create-form .error-icon {
        font-size: 16px;
        flex-shrink: 0;
    }

    .panel-label {
        margin: 0 0 4px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.66rem;
        font-weight: 300;
        color: var(--panel-muted);
    }

    h2,
    h3 {
        margin: 0;
    }

    h2 {
        font-size: 1.05rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: var(--panel-title);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .count {
        background: var(--count-bg);
        color: var(--count-color);
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 400;
        padding: 2px 8px;
        line-height: 1.2;
    }

    .scroll-area {
        overflow-y: auto;
        min-height: 0;
        flex: 1;
        padding-right: 4px;
        scrollbar-width: thin;
        scrollbar-color: rgba(255, 255, 255, 0.15) transparent;
    }

    :global(html.light-mode) .scroll-area {
        scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
    }

    .scroll-area::-webkit-scrollbar {
        width: 4px;
    }

    .scroll-area::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.15);
        border-radius: 4px;
    }

    :global(html.light-mode) .scroll-area::-webkit-scrollbar-thumb {
        background: rgba(0, 0, 0, 0.15);
    }

    .empty {
        margin: 0;
        color: var(--panel-muted);
        font-size: 0.76rem;
        font-weight: 300;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .incident-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        gap: 6px;
    }

    .incident {
        display: flex;
        gap: 10px;
        align-items: flex-start;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--card-bg);
        border: 0;
        width: 100%;
        text-align: left;
        color: inherit;
        box-sizing: border-box;
        transition: background-color 150ms ease, opacity 150ms ease;
    }

    button.incident {
        cursor: pointer;
    }

    button.incident:hover {
        background: var(--card-bg-hover);
        opacity: 0.85;
    }

    .active-incident.severity-major {
        background: var(--severity-major-bg);
    }

    .active-incident.severity-major:hover {
        background: var(--severity-major-hover);
    }

    .active-incident.severity-minor {
        background: var(--severity-minor-bg);
    }

    .active-incident.severity-minor:hover {
        background: var(--severity-minor-hover);
    }

    .icon {
        font-size: 18px;
        color: var(--panel-muted);
        margin-top: 1px;
        flex-shrink: 0;
    }

    .severity-major .icon {
        color: var(--severity-major-color);
    }

    .severity-minor .icon {
        color: var(--severity-minor-color);
    }

    .incident-body {
        min-width: 0;
        flex: 1;
    }

    .incident-body strong {
        display: block;
        font-size: 0.76rem;
        font-weight: 400;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--panel-text);
    }

    .incident-body p {
        margin: 3px 0 0;
        font-size: 0.74rem;
        font-weight: 300;
        color: var(--panel-muted);
        line-height: 1.4;
        letter-spacing: 0.02em;
    }

    .incident-body small {
        display: block;
        margin-top: 4px;
        color: var(--severity-minor-color);
        font-size: 0.68rem;
        font-weight: 400;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .section {
        margin-top: 14px;
    }

    .section h3 {
        margin-bottom: 8px;
        font-size: 0.68rem;
        font-weight: 400;
        color: var(--panel-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .resolved .incident {
        opacity: 0.55;
    }
</style>