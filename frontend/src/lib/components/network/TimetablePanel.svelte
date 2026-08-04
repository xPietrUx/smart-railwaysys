<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchScenarios, runScenario } from '$lib/services/scenarios';
	import type { ActiveScenarioInfo, Scenario } from '$lib/types/scenario';

	export let apiBaseUrl: string;
	/** Aktywny rozkład z żywego snapshotu (WebSocket). */
	export let scenario: ActiveScenarioInfo | null = null;
	/** Zmiana wartości wymusza przeładowanie listy (po zapisie/usunięciu w modalu). */
	export let refreshKey = 0;
	/** Otwiera modal szczegółów (edycja pociągów rozkładu). */
	export let onDetails: (scenario: Scenario) => void = () => {};
	/** Otwiera modal tworzenia nowego rozkładu. */
	export let onCreate: () => void = () => {};
	export let readOnly = false;

	const SCENARIO_ICON: Record<string, string> = {
		ROZKLAD_BAZOWY: '🚉',
		ROZKLAD_SZCZYT_GOP: '🌇',
		ROZKLAD_EKSPRESY: '⚡',
		ROZKLAD_TOWAROWY: '🏗️',
		ROZKLAD_BESKIDY: '🏔️'
	};

	let scenarios: Scenario[] = [];
	let listError = '';
	let actionError = '';
	let busyId: string | null = null;

	onMount(() => {
		void loadScenarios();
	});

	// refreshKey startuje od 0 (pierwsze ładowanie robi onMount); każde podbicie
	// przez stronę po zapisie/usunięciu w modalu przeładowuje listę.
	$: if (refreshKey > 0) {
		void loadScenarios();
	}

	async function loadScenarios() {
		listError = '';
		try {
			scenarios = await fetchScenarios(fetch, apiBaseUrl);
		} catch {
			listError = 'Nie udało się pobrać scenariuszy — sprawdź, czy backend działa.';
		}
	}

	async function handleRun(scenarioId: string) {
		if (busyId !== null) return;
		busyId = scenarioId;
		actionError = '';
		try {
			await runScenario(fetch, apiBaseUrl, scenarioId);
		} catch (error) {
			actionError = error instanceof Error ? error.message : 'Nie udało się uruchomić rozkładu.';
		} finally {
			busyId = null;
		}
	}

	function trainsCountLabel(count: number): string {
		if (count === 1) return '1 pociąg';
		const lastDigit = count % 10;
		const lastTwo = count % 100;
		if (lastDigit >= 2 && lastDigit <= 4 && !(lastTwo >= 12 && lastTwo <= 14)) {
			return `${count} pociągi`;
		}
		return `${count} pociągów`;
	}
</script>

<div class="panel">
	<div class="panel-header">
		<div>
			<p class="panel-label">Rozkłady jazdy</p>
			<h2>Scenariusze rozkładu pociągów</h2>
		</div>
	</div>

	<div class="scroll-area">
		{#if scenario}
			<div class="active-box">
				<strong>▶ {scenario.name}</strong>
				<p>
					na sieci {scenario.spawnedTrains}/{scenario.totalTrains} pociągów
					{#if scenario.spawnedTrains < scenario.totalTrains}
						· kolejne wjeżdżają
					{/if}
				</p>
			</div>
		{/if}

		{#if actionError}
			<p class="error">{actionError}</p>
		{/if}

		{#if listError}
			<p class="error">{listError}</p>
			<button type="button" class="ghost-btn" on:click={loadScenarios}>Spróbuj ponownie</button>
		{:else}
			<ul class="scenario-list">
				{#each scenarios as item (item.id)}
					<li class="scenario" class:active={scenario?.id === item.id}>
						<span class="icon">{SCENARIO_ICON[item.id] ?? '🗓️'}</span>
						<div class="scenario-body">
							<strong>{item.name}</strong>
							{#if item.description}
								<p>{item.description}</p>
							{/if}
							<small>{trainsCountLabel(item.trains.length)}</small>
						</div>
						{#if !readOnly}<div class="scenario-actions">
								<button
									type="button"
									class="run-btn"
									on:click={() => handleRun(item.id)}
									disabled={busyId !== null}
									title="Uruchom rozkład (zastąpi pociągi na sieci)"
								>
									{busyId === item.id ? '…' : '▶'}
								</button>
								<button
									type="button"
									class="details-btn"
									on:click={() => onDetails(item)}
									title="Szczegóły — edytuj pociągi rozkładu"
								>
									Szczegóły
								</button>
							</div>{/if}
					</li>
				{/each}
			</ul>

			{#if !readOnly}<button type="button" class="new-btn" on:click={onCreate}
					>➕ Nowy scenariusz</button
				>{/if}
		{/if}
	</div>
</div>

<style>
	.panel {
		background: rgba(15, 23, 42, 0.82);
		border: 1px solid rgba(148, 163, 184, 0.18);
		box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
		backdrop-filter: blur(12px);
		border-radius: 18px;
		padding: 18px;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.panel-header {
		margin-bottom: 12px;
		flex-shrink: 0;
	}

	.panel-label {
		margin: 0 0 6px;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		font-size: 0.72rem;
		color: #93c5fd;
	}

	h2 {
		margin: 0;
		font-size: 1.05rem;
		line-height: 1.3;
	}

	.scroll-area {
		overflow-y: auto;
		min-height: 0;
	}

	.active-box {
		margin-bottom: 12px;
		padding: 10px 12px;
		border-radius: 12px;
		background: rgba(30, 58, 138, 0.35);
		border: 1px solid rgba(96, 165, 250, 0.5);
	}

	.active-box strong {
		font-size: 0.88rem;
		color: #bfdbfe;
	}

	.active-box p {
		margin: 4px 0 0;
		font-size: 0.78rem;
		color: #cbd5e1;
	}

	.error {
		margin: 0 0 10px;
		padding: 8px 10px;
		border-radius: 10px;
		background: rgba(127, 29, 29, 0.35);
		border: 1px solid rgba(239, 68, 68, 0.45);
		color: #fecaca;
		font-size: 0.82rem;
		line-height: 1.4;
	}

	.scenario-list {
		list-style: none;
		margin: 0 0 12px;
		padding: 0;
		display: grid;
		gap: 8px;
	}

	.scenario {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		padding: 10px 12px;
		border-radius: 12px;
		background: rgba(30, 41, 59, 0.72);
		border: 1px solid rgba(148, 163, 184, 0.14);
	}

	.scenario.active {
		border-color: rgba(96, 165, 250, 0.6);
		background: rgba(30, 58, 138, 0.28);
	}

	.icon {
		font-size: 1.25rem;
		line-height: 1;
	}

	.scenario-body {
		min-width: 0;
		flex: 1;
	}

	.scenario-body strong {
		display: block;
		font-size: 0.87rem;
	}

	.scenario-body p {
		margin: 3px 0 0;
		font-size: 0.8rem;
		color: #cbd5e1;
		line-height: 1.4;
	}

	.scenario-body small {
		display: block;
		margin-top: 5px;
		color: #94a3b8;
		font-size: 0.74rem;
	}

	.scenario-actions {
		display: flex;
		flex-direction: column;
		gap: 6px;
		align-items: stretch;
	}

	.run-btn {
		padding: 6px 10px;
		border-radius: 9px;
		border: 1px solid rgba(52, 211, 153, 0.5);
		background: rgba(6, 78, 59, 0.45);
		color: #6ee7b7;
		font-size: 0.85rem;
		font-weight: 700;
		cursor: pointer;
	}

	.run-btn:hover:not(:disabled) {
		border-color: rgba(52, 211, 153, 0.9);
	}

	.run-btn:disabled {
		opacity: 0.45;
		cursor: default;
	}

	.details-btn {
		padding: 5px 10px;
		border-radius: 9px;
		border: 1px solid rgba(96, 165, 250, 0.4);
		background: rgba(30, 58, 138, 0.3);
		color: #bfdbfe;
		font-size: 0.76rem;
		font-weight: 600;
		cursor: pointer;
		white-space: nowrap;
	}

	.details-btn:hover {
		border-color: rgba(96, 165, 250, 0.85);
	}

	.new-btn {
		width: 100%;
		padding: 9px 12px;
		border-radius: 12px;
		border: 1px dashed rgba(96, 165, 250, 0.5);
		background: rgba(30, 58, 138, 0.25);
		color: #bfdbfe;
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
	}

	.new-btn:hover {
		border-color: rgba(96, 165, 250, 0.9);
	}

	.ghost-btn {
		width: 100%;
		padding: 7px 12px;
		border-radius: 10px;
		border: 1px solid rgba(148, 163, 184, 0.3);
		background: transparent;
		color: #cbd5e1;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.ghost-btn:hover {
		border-color: rgba(96, 165, 250, 0.6);
	}
</style>
