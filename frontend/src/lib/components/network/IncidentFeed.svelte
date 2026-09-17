<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import { t } from '$lib/i18n';
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

    let showCreateForm = false;
    let formType: RailEventType = 'line_failure';
    let formTargetId = '';
    let submitting = false;
    let formError = '';

    let nowSec = Date.now() / 1000;
    let interval: ReturnType<typeof setInterval>;

    const INCIDENT_ICONS: Record<string, string> = {
        signal_failure: 'electric_bolt',
        derailment: 'warning',
        track_blockage: 'do_not_disturb_on',
        default: 'error'
    };

    onMount(() => {
        interval = setInterval(() => {
            nowSec = Date.now() / 1000;
        }, 1000);
    });
    onDestroy(() => {
        clearInterval(interval);
        if (pickMode) onCancelPick();
    });

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

    // Cel zależy od typu: odcinek (line_failure/speed_restriction) albo stacja
    // (signal_failure) — backend i tak zweryfikuje dostępność celu, ta lista to
    // tylko wygoda wyboru w formularzu.
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
    }

    function pickModeForType(type: RailEventType): 'segment' | 'station' {
        return type === 'signal_failure' ? 'station' : 'segment';
    }

    function startPickOnMap() {
        onStartPick(pickModeForType(formType), (id: string) => {
            formTargetId = id;
        });
    }

    function handleTypeChange() {
        if (pickMode) onCancelPick();
    }

    async function handleCreateIncident() {
        if (!formTargetId || submitting) return;
        submitting = true;
        formError = '';
        try {
            const created = await createIncident(fetch, { type: formType, targetId: formTargetId });
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
                {$t('incidents.title')}
                {#if activeEvents.length > 0}
                    <span class="count">{activeEvents.length}</span>
                {/if}
            </h2>
        </div>
        {#if !readOnly}
            <button
                type="button"
                class="add-btn"
                on:click={toggleCreateForm}
                aria-expanded={showCreateForm}
                title={$t('incidents.addTitle')}
            >
                <span class="material-symbols-outlined" aria-hidden="true">
                    {showCreateForm ? 'close' : 'add'}
                </span>
            </button>
        {/if}
    </div>

    {#if showCreateForm}
        <form class="create-form" on:submit|preventDefault={handleCreateIncident}>
            <label class="field">
                <span>{$t('incidents.form.type')}</span>
                <select bind:value={formType} on:change={handleTypeChange}>
                    {#each INCIDENT_TYPES as type (type)}
                        <option value={type}>{eventLabel(type, $t)}</option>
                    {/each}
                </select>
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
                        <select bind:value={formTargetId}>
                            {#each targetOptions as option (option.id)}
                                <option value={option.id}>{option.label}</option>
                            {/each}
                        </select>
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
    .field select:focus {
        outline: none;
    }

    button:focus-visible,
    .field select:focus-visible {
        outline: 2px solid var(--focus-ring);
        outline-offset: 2px;
    }

    .panel-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 12px;
        /* Dok (rodzic panelu) ma własny przycisk zwijania w prawym górnym rogu
           (position: absolute, 26px, 10px od krawędzi) — ten margines chroni
           add-btn przed wjechaniem pod niego. */
        padding-right: 28px;
        flex-shrink: 0;
    }

    .add-btn {
        flex-shrink: 0;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 0;
        background: var(--card-bg);
        color: var(--panel-text);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        transition: background-color 150ms ease;
    }

    .add-btn:hover {
        background: var(--card-bg-hover);
    }

    .add-btn .material-symbols-outlined {
        font-size: 18px;
    }

    .create-form {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-bottom: 14px;
        padding: 12px;
        border-radius: 10px;
        background: var(--card-bg);
        flex-shrink: 0;
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 0.72rem;
        color: var(--panel-muted);
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .field select {
        padding: 8px 10px;
        border-radius: 8px;
        border: 0;
        background: rgba(255, 255, 255, 0.06);
        color: var(--panel-text);
        font-family: inherit;
        font-size: 0.8rem;
        text-transform: none;
        letter-spacing: normal;
    }

    :global(html.light-mode) .field select,
    :global([data-theme='light']) .field select,
    :global(.light) .field select {
        background: rgba(0, 0, 0, 0.05);
    }

    /* Sam <select> dziedziczy motyw z --panel-text/tło powyżej, ale rozwinięta
       lista <option> to natywny popup przeglądarki, który tego NIE dziedziczy —
       bez jawnego stylu wypadał zawsze jasny/systemowy, nawet w trybie ciemnym. */
    .field select option {
        background: #1c1c1c;
        color: #f5f7f8;
    }

    :global(html.light-mode) .field select option,
    :global([data-theme='light']) .field select option,
    :global(.light) .field select option {
        background: #f4f5f6;
        color: #111827;
    }

    .no-targets {
        margin: 0;
        font-size: 0.72rem;
        color: var(--panel-muted);
        text-transform: none;
        letter-spacing: normal;
    }

    .target-row {
        display: flex;
        gap: 6px;
        align-items: center;
    }

    .target-row select {
        flex: 1;
        min-width: 0;
    }

    .pick-btn {
        flex-shrink: 0;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        border: 0;
        background: rgba(255, 255, 255, 0.06);
        color: var(--panel-text);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        padding: 0;
        transition: background-color 150ms ease;
    }

    :global(html.light-mode) .pick-btn,
    :global([data-theme='light']) .pick-btn,
    :global(.light) .pick-btn {
        background: rgba(0, 0, 0, 0.05);
    }

    .pick-btn:hover {
        background: var(--card-bg-hover);
    }

    .pick-btn .material-symbols-outlined {
        font-size: 17px;
    }

    .picking-hint {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
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
        gap: 8px;
        margin-top: 2px;
    }

    .ghost-btn {
        background: none;
        border: 0;
        color: var(--panel-muted);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        cursor: pointer;
        padding: 8px 10px;
        border-radius: 8px;
    }

    .ghost-btn:hover {
        color: var(--panel-text);
    }

    .submit-btn {
        background: var(--severity-major-color);
        color: #141414;
        border: 0;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 0.72rem;
        font-weight: 400;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        cursor: pointer;
        transition: opacity 150ms ease;
    }

    .submit-btn:disabled {
        opacity: 0.5;
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
    }

    .create-form .error-icon {
        font-size: 16px;
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
        transition: background-color 150ms ease;
    }

    button.incident {
        cursor: pointer;
    }

    button.incident:hover {
        background: var(--card-bg-hover);
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