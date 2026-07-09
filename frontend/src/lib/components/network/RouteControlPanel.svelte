<script lang="ts">
	import type { StationNode } from '$lib/types/network';
	import type { FastestRouteResponse } from '$lib/types/routing';
	import { fetchFastestRoute } from '$lib/services/routing';

	export let stations: StationNode[] = [];
	export let activeRoute: FastestRouteResponse | null = null;
	export let onRouteFound: (route: FastestRouteResponse | null) => void = () => {};

	let fromStationId = stations.length > 0 ? stations[0].id : 'KAT';
	let toStationId = stations.length > 1 ? stations[1].id : 'GLI';
	let trainType: 'IC' | 'REGIONAL' | 'FREIGHT' = 'IC';
	let loading = false;
	let errorMsg: string | null = null;

	const trainOptions = [
		{ id: 'IC', label: 'InterCity (IC)', speed: '160 km/h', desc: 'Brak kar za postoje na stacjach pośrednich' },
		{ id: 'REGIONAL', label: 'Regionalny (REG)', speed: '120 km/h', desc: '+1 min postoju na każdej stacji' },
		{ id: 'FREIGHT', label: 'Towarowy (TW)', speed: '80 km/h', desc: 'Przewóz towarowy o ograniczonych prędkościach' }
	] as const;

	async function calculateRoute() {
		if (!fromStationId || !toStationId) return;
		loading = true;
		errorMsg = null;
		try {
			const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
			const res = await fetchFastestRoute(fetch, baseUrl, fromStationId, toStationId, trainType);
			activeRoute = res;
			onRouteFound(res);
			if (!res.found && res.message) {
				errorMsg = res.message;
			}
		} catch (err) {
			errorMsg = err instanceof Error ? err.message : 'Błąd połączenia z serwerem routingu';
			activeRoute = null;
			onRouteFound(null);
		} finally {
			loading = false;
		}
	}

	function swapStations() {
		const temp = fromStationId;
		fromStationId = toStationId;
		toStationId = temp;
	}

	function clearRoute() {
		activeRoute = null;
		errorMsg = null;
		onRouteFound(null);
	}
</script>

<div class="route-panel">
	<div class="panel-header">
		<div class="header-title">
			<span class="icon">🧭</span>
			<div>
				<h3>Najszybsza Trasa (A*)</h3>
				<p class="subtitle">Optymalizacja czasu przejazdu ze wzorem Haversine'a</p>
			</div>
		</div>
		{#if activeRoute}
			<button class="clear-btn" on:click={clearRoute} title="Wyczyść trasę">✕</button>
		{/if}
	</div>

	<!-- Wybór typu pociągu -->
	<div class="section">
		<label class="section-label" for="train-type">Typ pociągu (wpływ na prędkość i postoje)</label>
		<div class="train-pills" id="train-type">
			{#each trainOptions as opt}
				<button
					type="button"
					class="train-pill"
					class:active={trainType === opt.id}
					on:click={() => (trainType = opt.id)}
				>
					<span class="pill-label">{opt.label}</span>
					<span class="pill-speed">{opt.speed}</span>
				</button>
			{/each}
		</div>
	</div>

	<!-- Wybór stacji -->
	<div class="station-selector-grid">
		<div class="input-group">
			<label for="from-station">Stacja początkowa</label>
			<select id="from-station" bind:value={fromStationId}>
				{#each stations as s}
					<option value={s.id}>{s.name} ({s.id})</option>
				{/each}
			</select>
		</div>

		<button type="button" class="swap-btn" on:click={swapStations} title="Zamień stacje">
			⇄
		</button>

		<div class="input-group">
			<label for="to-station">Stacja docelowa</label>
			<select id="to-station" bind:value={toStationId}>
				{#each stations as s}
					<option value={s.id}>{s.name} ({s.id})</option>
				{/each}
			</select>
		</div>
	</div>

	<div class="actions">
		<button type="button" class="calc-btn" on:click={calculateRoute} disabled={loading}>
			{#if loading}
				<span class="spinner"></span> Obliczanie A*...
			{:else}
				⚡ Wyznacz Najszybszą Trasę
			{/if}
		</button>
	</div>

	{#if errorMsg}
		<div class="error-alert">
			<span>⚠️ {errorMsg}</span>
		</div>
	{/if}

	{#if activeRoute && activeRoute.found}
		<div class="results-card">
			<div class="results-header">
				<span class="badge-optimal">✨ Optymalna Trasa</span>
				<span class="algo-tag">{activeRoute.algorithm}</span>
			</div>

			<div class="stats-grid">
				<div class="stat-box">
					<span class="stat-label">Czas przejazdu</span>
					<span class="stat-value highlight-time">{activeRoute.totalTravelMin} min</span>
				</div>
				<div class="stat-box">
					<span class="stat-label">Dystans</span>
					<span class="stat-value">{activeRoute.totalDistKm} km</span>
				</div>
				<div class="stat-box">
					<span class="stat-label">Sprawdzone węzły</span>
					<span class="stat-value">{activeRoute.exploredNodesCount}</span>
				</div>
			</div>

			<div class="path-sequence">
				<span class="path-label">Przebieg trasy:</span>
				<div class="path-nodes">
					{#each activeRoute.path as st, idx}
						<span class="path-node">
							<strong class="node-code">{st.id}</strong>
							<span class="node-name">{st.name}</span>
						</span>
						{#if idx < activeRoute.path.length - 1}
							<span class="path-arrow">→</span>
						{/if}
					{/each}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.route-panel {
		background: rgba(17, 24, 39, 0.85);
		backdrop-filter: blur(12px);
		border: 1px solid rgba(255, 255, 255, 0.1);
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

	.clear-btn {
		background: rgba(255, 255, 255, 0.1);
		border: none;
		color: #d1d5db;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.2s;
	}

	.clear-btn:hover {
		background: rgba(239, 68, 68, 0.3);
		color: #ffffff;
	}

	.section {
		margin-bottom: 16px;
	}

	.section-label {
		display: block;
		font-size: 0.78rem;
		font-weight: 600;
		color: #9ca3af;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 8px;
	}

	.train-pills {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
	}

	.train-pill {
		background: rgba(255, 255, 255, 0.05);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 10px;
		padding: 8px 10px;
		text-align: center;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: 2px;
		transition: all 0.2s ease;
		color: #d1d5db;
	}

	.train-pill:hover {
		background: rgba(255, 255, 255, 0.1);
	}

	.train-pill.active {
		background: rgba(59, 130, 246, 0.2);
		border-color: #3b82f6;
		color: #60a5fa;
		box-shadow: 0 0 15px rgba(59, 130, 246, 0.25);
	}

	.pill-label {
		font-weight: 600;
		font-size: 0.82rem;
	}

	.pill-speed {
		font-size: 0.72rem;
		opacity: 0.8;
	}

	.station-selector-grid {
		display: grid;
		grid-template-columns: 1fr auto 1fr;
		gap: 10px;
		align-items: flex-end;
		margin-bottom: 16px;
	}

	.input-group {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.input-group label {
		font-size: 0.75rem;
		font-weight: 600;
		color: #9ca3af;
	}

	select {
		background: rgba(15, 23, 42, 0.8);
		border: 1px solid rgba(255, 255, 255, 0.15);
		border-radius: 8px;
		color: #ffffff;
		padding: 8px 10px;
		font-size: 0.88rem;
		outline: none;
		transition: border-color 0.2s;
	}

	select:focus {
		border-color: #3b82f6;
	}

	.swap-btn {
		background: rgba(255, 255, 255, 0.08);
		border: 1px solid rgba(255, 255, 255, 0.15);
		color: #ffffff;
		border-radius: 8px;
		padding: 8px 12px;
		cursor: pointer;
		font-size: 1rem;
		transition: background 0.2s;
	}

	.swap-btn:hover {
		background: rgba(255, 255, 255, 0.18);
	}

	.actions {
		display: flex;
	}

	.calc-btn {
		width: 100%;
		background: linear-gradient(135deg, #3b82f6, #2563eb);
		border: none;
		border-radius: 10px;
		color: #ffffff;
		font-weight: 600;
		font-size: 0.95rem;
		padding: 12px;
		cursor: pointer;
		box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4);
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
	}

	.calc-btn:hover:not(:disabled) {
		background: linear-gradient(135deg, #60a5fa, #3b82f6);
		transform: translateY(-1px);
		box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
	}

	.calc-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error-alert {
		margin-top: 12px;
		padding: 10px 14px;
		background: rgba(239, 68, 68, 0.15);
		border: 1px solid rgba(239, 68, 68, 0.3);
		border-radius: 8px;
		color: #fca5a5;
		font-size: 0.85rem;
	}

	.results-card {
		margin-top: 18px;
		padding: 16px;
		background: rgba(15, 23, 42, 0.65);
		border: 1px solid rgba(16, 185, 129, 0.35);
		border-radius: 12px;
		animation: fadeIn 0.3s ease;
	}

	.results-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.badge-optimal {
		color: #10b981;
		font-weight: 700;
		font-size: 0.85rem;
	}

	.algo-tag {
		background: rgba(16, 185, 129, 0.15);
		color: #34d399;
		border: 1px solid rgba(16, 185, 129, 0.3);
		border-radius: 6px;
		padding: 2px 8px;
		font-size: 0.72rem;
		font-weight: 600;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 10px;
		margin-bottom: 14px;
	}

	.stat-box {
		background: rgba(255, 255, 255, 0.04);
		border-radius: 8px;
		padding: 8px;
		text-align: center;
	}

	.stat-label {
		display: block;
		font-size: 0.72rem;
		color: #9ca3af;
		margin-bottom: 4px;
	}

	.stat-value {
		font-size: 0.95rem;
		font-weight: 700;
		color: #e5e7eb;
	}

	.highlight-time {
		color: #34d399;
		font-size: 1.05rem;
	}

	.path-sequence {
		border-top: 1px solid rgba(255, 255, 255, 0.08);
		padding-top: 10px;
	}

	.path-label {
		font-size: 0.75rem;
		color: #9ca3af;
		display: block;
		margin-bottom: 8px;
	}

	.path-nodes {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}

	.path-node {
		background: rgba(59, 130, 246, 0.15);
		border: 1px solid rgba(59, 130, 246, 0.3);
		border-radius: 6px;
		padding: 4px 8px;
		font-size: 0.78rem;
	}

	.node-code {
		color: #60a5fa;
		margin-right: 4px;
	}

	.path-arrow {
		color: #6b7280;
		font-size: 0.8rem;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>
