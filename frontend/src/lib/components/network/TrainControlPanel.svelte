<script lang="ts">
	import type { StationNode } from '$lib/types/network';
	import type { TrainState, TrainCreateRequest } from '$lib/types/simulation';
	import { createTrain, spawnDemoTrains, clearAllTrains } from '$lib/services/simulation';

	export let stations: StationNode[] = [];
	export let trains: TrainState[] = [];
	export let isRunning = true;
	export let timeScale = 60.0;
	export let onTrainsUpdated: (trains: TrainState[]) => void = () => {};
	export let onSelectTrainRoute: (train: TrainState | null) => void = () => {};
	export let onToggleRunning: () => void = () => {};

	let showForm = false;
	let loading = false;

	let trainName = 'IC Morcinek';
	let trainType: 'IC' | 'REGIONAL' | 'FREIGHT' = 'IC';
	let fromStation = stations.length > 0 ? stations[0].id : 'KAT';
	let toStation = stations.length > 1 ? stations[1].id : 'WRO';

	$: stationNameMap = new Map(stations.map((s) => [s.id, s.name]));

	async function handleSpawnDemo() {
		if (loading) return;
		loading = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			const res = await spawnDemoTrains(fetch, baseUrl);
			onTrainsUpdated(res.trains);
		} catch (err) {
			alert('Błąd uruchamiania zestawu demo: ' + (err instanceof Error ? err.message : err));
		} finally {
			loading = false;
		}
	}

	async function handleAddTrain() {
		if (loading) return;
		if (fromStation === toStation) {
			alert('Stacja początkowa i docelowa muszą być różne!');
			return;
		}
		loading = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			const payload: TrainCreateRequest = {
				trainId: `${trainType}_${Date.now().toString().slice(-4)}`,
				name: trainName,
				trainType,
				fromStation,
				toStation
			};
			await createTrain(fetch, baseUrl, payload);
			showForm = false;
		} catch (err) {
			alert('Błąd dodawania pociągu: ' + (err instanceof Error ? err.message : err));
		} finally {
			loading = false;
		}
	}

	async function handleClearAll() {
		if (loading) return;
		loading = true;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			await clearAllTrains(fetch, baseUrl);
			onTrainsUpdated([]);
			onSelectTrainRoute(null);
		} catch (err) {
			alert('Błąd usuwania pociągów: ' + (err instanceof Error ? err.message : err));
		} finally {
			loading = false;
		}
	}
</script>

<div class="train-panel">
	<div class="panel-header">
		<div class="header-title">
			<span class="icon">🚆</span>
			<div>
				<h3>Ruch Pociągów na Żywo (A* w akcji)</h3>
				<p class="subtitle">Symulacja jazdy pociągów i reakcji na awarie torów</p>
			</div>
		</div>
		<div class="header-controls">
			<button
				type="button"
				class="running-toggle-btn"
				class:paused={!isRunning}
				on:click={onToggleRunning}
			>
				{isRunning ? '⏸️ Pauza' : '▶️ Wznów'}
			</button>
		</div>
	</div>

	<!-- Szybkie akcje / Demo -->
	<div class="actions-bar">
		<button
			type="button"
			class="btn-demo"
			on:click={handleSpawnDemo}
			disabled={loading}
		>
			🚀 Uruchom zestaw demonstracyjny (3 pociągi)
		</button>
		<button
			type="button"
			class="btn-add-form"
			on:click={() => (showForm = !showForm)}
		>
			{showForm ? '✖ Zamknij form' : '➕ Dodaj własny pociąg'}
		</button>
	</div>

	<!-- Formularz dodawania pociągu -->
	{#if showForm}
		<div class="train-form-card">
			<h4>Parametry nowego pociągu</h4>
			<div class="form-grid">
				<div>
					<label for="t-name">Nazwa pociągu</label>
					<input id="t-name" type="text" bind:value={trainName} />
				</div>
				<div>
					<label for="t-type">Typ składu</label>
					<select id="t-type" bind:value={trainType}>
						<option value="IC">Express InterCity (140 km/h)</option>
						<option value="REGIONAL">Koleje Regionalne (100 km/h)</option>
						<option value="FREIGHT">Pociąg Towarowy (70 km/h)</option>
					</select>
				</div>
				<div>
					<label for="t-from">Stacja startowa</label>
					<select id="t-from" bind:value={fromStation}>
						{#each stations as s}
							<option value={s.id}>{s.name} ({s.id})</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="t-to">Stacja docelowa</label>
					<select id="t-to" bind:value={toStation}>
						{#each stations as s}
							<option value={s.id}>{s.name} ({s.id})</option>
						{/each}
					</select>
				</div>
			</div>
			<button type="button" class="btn-submit" on:click={handleAddTrain} disabled={loading}>
				Wypuść pociąg na trasę 🚆
			</button>
		</div>
	{/if}

	<!-- Lista aktywnych pociągów -->
	<div class="trains-list-section">
		<h4>Aktywne pociągi na mapie ({trains.length})</h4>
		{#if trains.length === 0}
			<div class="empty-state">
				Brak aktywnych pociągów. Kliknij „🚀 Uruchom zestaw demonstracyjny”, aby zobaczyć pociągi na żywo!
			</div>
		{:else}
			<div class="trains-grid">
				{#each trains as t}
					<div class="train-item-card" class:rerouted-card={t.status === 'rerouted'}>
						<div class="t-top-row">
							<div class="t-title">
								<span class="t-icon">
									{t.trainType === 'IC' ? '🚄' : t.trainType === 'REGIONAL' ? '🚆' : '🚂'}
								</span>
								<div>
									<strong>{t.name}</strong>
									<span class="t-type-tag">{t.trainType} · {t.speedKmh} km/h</span>
								</div>
							</div>
							<span class="status-pill" class:pill-arrived={t.status === 'arrived'} class:pill-rerouted={t.status === 'rerouted'}>
								{#if t.status === 'arrived'}
									🏁 Dotarł do celu
								{:else if t.status === 'rerouted'}
									⚡ Rerouting A*
								{:else if t.status === 'blocked'}
									🔴 Zablokowany
								{:else}
									🟢 W drodze
								{/if}
							</span>
						</div>

						<div class="t-route-row">
							<span>
								{stationNameMap.get(t.fromStation) ?? t.fromStation} → {stationNameMap.get(t.toStation) ?? t.toStation}
							</span>
							{#if t.status !== 'arrived'}
								<small>
									Aktualnie: {stationNameMap.get(t.currentStationId)} → {stationNameMap.get(t.nextStationId || '') || 'Cel'}
								</small>
							{/if}
						</div>

						<!-- Alert po zmianie trasy (Rerouting) -->
						{#if t.rerouteMessage}
							<div class="reroute-alert">
								<span>⚡ {t.rerouteMessage}</span>
							</div>
						{/if}

						<div class="t-actions">
							<button type="button" class="btn-show-route" on:click={() => onSelectTrainRoute(t)}>
								🎯 Podświetl trasę A* tego pociągu
							</button>
						</div>
					</div>
				{/each}
			</div>

			<div class="footer-actions">
				<button type="button" class="btn-clear" on:click={handleClearAll} disabled={loading}>
					🗑️ Usuń wszystkie pociągi
				</button>
			</div>
		{/if}
	</div>
</div>

<style>
	.train-panel {
		background: rgba(17, 24, 39, 0.85);
		backdrop-filter: blur(12px);
		border: 1px solid rgba(59, 130, 246, 0.3);
		border-radius: 16px;
		padding: 20px;
		color: #f3f4f6;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
		font-family: system-ui, -apple-system, sans-serif;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 16px;
		padding-bottom: 12px;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.icon {
		font-size: 1.6rem;
	}

	h3 {
		margin: 0;
		font-size: 1.1rem;
		font-weight: 700;
		color: #ffffff;
	}

	.subtitle {
		margin: 2px 0 0;
		font-size: 0.78rem;
		color: #9ca3af;
	}

	.running-toggle-btn {
		background: rgba(16, 185, 129, 0.2);
		border: 1px solid #10b981;
		color: #6ee7b7;
		padding: 6px 12px;
		border-radius: 8px;
		font-weight: 700;
		cursor: pointer;
		transition: all 0.2s;
	}

	.running-toggle-btn.paused {
		background: rgba(245, 158, 11, 0.2);
		border-color: #f59e0b;
		color: #fcd34d;
	}

	.actions-bar {
		display: flex;
		gap: 10px;
		margin-bottom: 16px;
		flex-wrap: wrap;
	}

	.btn-demo {
		flex: 1;
		background: linear-gradient(135deg, #3b82f6, #2563eb);
		border: none;
		color: #ffffff;
		padding: 10px 14px;
		border-radius: 10px;
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
		box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
		transition: all 0.2s;
	}

	.btn-demo:hover:not(:disabled) {
		background: linear-gradient(135deg, #60a5fa, #3b82f6);
	}

	.btn-add-form {
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.2);
		color: #e5e7eb;
		padding: 10px 14px;
		border-radius: 10px;
		font-weight: 600;
		font-size: 0.85rem;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-add-form:hover {
		background: rgba(255, 255, 255, 0.15);
		color: #ffffff;
	}

	.train-form-card {
		background: rgba(15, 23, 42, 0.9);
		border: 1px solid rgba(59, 130, 246, 0.4);
		border-radius: 12px;
		padding: 14px;
		margin-bottom: 16px;
	}

	.train-form-card h4 {
		margin: 0 0 12px;
		font-size: 0.9rem;
		color: #93c5fd;
	}

	.form-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 12px;
		margin-bottom: 14px;
	}

	@media (max-width: 600px) {
		.form-grid {
			grid-template-columns: 1fr;
		}
	}

	label {
		display: block;
		font-size: 0.75rem;
		color: #9ca3af;
		margin-bottom: 4px;
	}

	input,
	select {
		width: 100%;
		background: rgba(30, 41, 59, 0.9);
		border: 1px solid rgba(255, 255, 255, 0.2);
		border-radius: 8px;
		color: #ffffff;
		padding: 8px 10px;
		font-size: 0.85rem;
		outline: none;
	}

	.btn-submit {
		width: 100%;
		background: #10b981;
		border: none;
		color: #ffffff;
		padding: 10px;
		border-radius: 8px;
		font-weight: 700;
		cursor: pointer;
	}

	.trains-list-section h4 {
		margin: 0 0 12px;
		font-size: 0.88rem;
		color: #e5e7eb;
	}

	.empty-state {
		background: rgba(255, 255, 255, 0.04);
		border: 1px dashed rgba(255, 255, 255, 0.15);
		border-radius: 10px;
		padding: 16px;
		text-align: center;
		color: #9ca3af;
		font-size: 0.85rem;
	}

	.trains-grid {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.train-item-card {
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 12px;
		padding: 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.train-item-card.rerouted-card {
		border-color: #f59e0b;
		background: rgba(245, 158, 11, 0.08);
	}

	.t-top-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.t-title {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.t-icon {
		font-size: 1.3rem;
	}

	.t-type-tag {
		display: block;
		font-size: 0.72rem;
		color: #9ca3af;
	}

	.status-pill {
		font-size: 0.72rem;
		font-weight: 700;
		padding: 3px 8px;
		border-radius: 12px;
		background: rgba(16, 185, 129, 0.2);
		color: #6ee7b7;
		border: 1px solid rgba(16, 185, 129, 0.35);
	}

	.status-pill.pill-arrived {
		background: rgba(100, 116, 139, 0.25);
		color: #cbd5e1;
		border-color: rgba(100, 116, 139, 0.4);
	}

	.status-pill.pill-rerouted {
		background: rgba(245, 158, 11, 0.25);
		color: #fcd34d;
		border-color: #f59e0b;
	}

	.t-route-row {
		font-size: 0.85rem;
		color: #f3f4f6;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.t-route-row small {
		color: #93c5fd;
		font-size: 0.75rem;
	}

	.reroute-alert {
		background: rgba(245, 158, 11, 0.15);
		border: 1px solid rgba(245, 158, 11, 0.4);
		color: #fde68a;
		padding: 8px 10px;
		border-radius: 8px;
		font-size: 0.78rem;
		font-weight: 600;
	}

	.btn-show-route {
		background: rgba(255, 255, 255, 0.06);
		border: 1px solid rgba(255, 255, 255, 0.15);
		color: #d1d5db;
		padding: 6px 12px;
		border-radius: 6px;
		font-size: 0.75rem;
		font-weight: 600;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-show-route:hover {
		background: rgba(255, 255, 255, 0.15);
		color: #ffffff;
	}

	.footer-actions {
		margin-top: 12px;
	}

	.btn-clear {
		width: 100%;
		background: rgba(239, 68, 68, 0.15);
		border: 1px solid rgba(239, 68, 68, 0.35);
		color: #fca5a5;
		padding: 8px;
		border-radius: 8px;
		font-size: 0.8rem;
		cursor: pointer;
	}

	.btn-clear:hover {
		background: rgba(239, 68, 68, 0.3);
		color: #ffffff;
	}
</style>
