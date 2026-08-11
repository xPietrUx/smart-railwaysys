<script lang="ts">
	import { t } from '$lib/i18n';
	import type { LiveSnapshot } from '$lib/services/live';
	import {
		pauseSimulation,
		resumeSimulation,
		setSimulationSpeed
	} from '$lib/services/simulation';

	export let snapshot: LiveSnapshot;
	export let apiBaseUrl: string;

	// Ćwiartka koła w stylu EU4, zagnieżdżona w dolnym-lewym rogu mapy: wachlarz
	// klinów prędkości od pionu (najwolniej) zgodnie z zegarem do poziomu
	// (najszybciej) + przycisk start/stop w samym narożniku.
	const SPEEDS = [0.5, 1, 1.5, 2];
	const CX = 6;
	const CY = 110;
	const R_INNER = 40;
	const R_OUTER = 78;
	const R_RIM = 84;
	const CORE_R = 32;
	const GAP_DEG = 1.6;
	const SPAN_DEG = 90 / SPEEDS.length;

	function polar(radius: number, deg: number): { x: number; y: number } {
		const rad = (deg * Math.PI) / 180;
		return { x: CX + radius * Math.cos(rad), y: CY + radius * Math.sin(rad) };
	}

	function point(radius: number, deg: number): string {
		const { x, y } = polar(radius, deg);
		return `${x.toFixed(2)} ${y.toFixed(2)}`;
	}

	function wedgePath(index: number): string {
		const from = -90 + index * SPAN_DEG + GAP_DEG;
		const to = -90 + (index + 1) * SPAN_DEG - GAP_DEG;
		return [
			`M ${point(R_OUTER, from)}`,
			`A ${R_OUTER} ${R_OUTER} 0 0 1 ${point(R_OUTER, to)}`,
			`L ${point(R_INNER, to)}`,
			`A ${R_INNER} ${R_INNER} 0 0 0 ${point(R_INNER, from)}`,
			'Z'
		].join(' ');
	}

	function labelPos(index: number): { x: number; y: number } {
		return polar((R_INNER + R_OUTER) / 2, -90 + (index + 0.5) * SPAN_DEG);
	}

	const RIM_PATH = `M ${point(R_RIM, -90)} A ${R_RIM} ${R_RIM} 0 0 1 ${point(R_RIM, 0)}`;

	// Zegar symulacji: 1 realna sekunda pracy symulacji = 1 symulowana minuta
	// (SIM_TIME_SCALE=60), więc realne sekundy wyświetlamy jako minuty.
	function formatSimClock(elapsedRealS: number): string {
		const simMinutes = Math.max(0, Math.floor(elapsedRealS));
		const pad = (value: number) => String(value).padStart(2, '0');
		return `${pad(Math.floor(simMinutes / 60))}:${pad(simMinutes % 60)}`;
	}

	let busy = false;
	// Optymistyczny stan pauzy/prędkości do czasu potwierdzenia następnym tickiem WS.
	let optimisticPaused: boolean | null = null;
	let optimisticSpeed: number | null = null;
	$: paused = optimisticPaused ?? snapshot.paused;
	$: speed = optimisticSpeed ?? snapshot.speed;
	// Reaktywne użycie jest rozpoznawane przez Svelte, ale nie przez bazową regułę ESLint.
	// eslint-disable-next-line no-useless-assignment
	$: if (optimisticPaused !== null && snapshot.paused === optimisticPaused) optimisticPaused = null;
	// eslint-disable-next-line no-useless-assignment
	$: if (optimisticSpeed !== null && snapshot.speed === optimisticSpeed) optimisticSpeed = null;

	async function togglePause() {
		if (busy) return;
		busy = true;
		try {
			if (paused) {
				await resumeSimulation(fetch, apiBaseUrl);
				optimisticPaused = false;
			} else {
				await pauseSimulation(fetch, apiBaseUrl);
				optimisticPaused = true;
			}
		} catch {
			// 409 przy podwójnym kliknięciu -- następny tick pokaże właściwy stan.
		} finally {
			busy = false;
		}
	}

	async function pickSpeed(option: number) {
		if (busy || option === speed) return;
		busy = true;
		try {
			await setSimulationSpeed(fetch, apiBaseUrl, option);
			optimisticSpeed = option;
		} catch {
			// Błąd sieci/walidacji -- następny tick pokaże faktyczną prędkość.
		} finally {
			busy = false;
		}
	}

	function activateOnKey(event: KeyboardEvent, action: () => void) {
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			action();
		}
	}
</script>

<div class="corner" class:paused>
	<svg
		viewBox="0 0 116 116"
		width="116"
		height="116"
		role="group"
		aria-label={$t('header.speed.title', { speed })}
	>
		<defs>
			<linearGradient id="ssc-wedge-on" x1="0" y1="1" x2="1" y2="0">
				<stop offset="0" stop-color="#1d4ed8" />
				<stop offset="1" stop-color="#60a5fa" />
			</linearGradient>
			<radialGradient id="ssc-core" cx="0.25" cy="0.75" r="1">
				<stop offset="0" stop-color="#1e293b" />
				<stop offset="1" stop-color="#0f172a" />
			</radialGradient>
		</defs>

		<path d={RIM_PATH} class="rim" />

		{#each SPEEDS as option, index (option)}
			<path
				d={wedgePath(index)}
				class="wedge"
				class:on={option <= speed}
				role="button"
				tabindex="0"
				aria-label={$t('header.speed.set', { speed: option })}
				aria-pressed={option === speed}
				on:click={() => pickSpeed(option)}
				on:keydown={(event) => activateOnKey(event, () => pickSpeed(option))}
			>
				<title>{$t('header.speed.set', { speed: option })}</title>
			</path>
			<text
				x={labelPos(index).x.toFixed(2)}
				y={labelPos(index).y.toFixed(2)}
				class="wedge-label"
				class:lit={option <= speed}
			>
				{option}
			</text>
		{/each}

		<circle
			cx={CX}
			cy={CY}
			r={CORE_R}
			class="core"
			role="button"
			tabindex="0"
			aria-label={paused ? $t('header.resumeTitle') : $t('header.pauseTitle')}
			on:click={togglePause}
			on:keydown={(event) => activateOnKey(event, togglePause)}
		>
			<title>{paused ? $t('header.resumeTitle') : $t('header.pauseTitle')}</title>
		</circle>
		<text x="21" y="95.5" class="core-icon">{paused ? '▶' : '⏸'}</text>
	</svg>

	<div class="readout">
		<span class="clock" title={$t('header.elapsedTitle')}>{formatSimClock(snapshot.elapsedRealS)}</span>
		<span class="speed-line">
			{#if paused}
				<span class="paused-badge">⏸ {$t('header.paused')}</span>
			{:else}
				{speed}×
			{/if}
		</span>
	</div>
</div>

<style>
	.corner {
		display: flex;
		align-items: flex-end;
		gap: 10px;
		padding: 0 0 0 0;
		pointer-events: none;
	}

	.corner svg,
	.corner .readout {
		pointer-events: auto;
	}

	svg {
		display: block;
		overflow: hidden;
		filter: drop-shadow(0 12px 28px rgba(2, 6, 23, 0.65));
		font-family: inherit;
	}

	.rim {
		fill: none;
		stroke: rgba(148, 163, 184, 0.25);
		stroke-width: 1.5;
		pointer-events: none;
	}

	.wedge {
		fill: rgba(15, 23, 42, 0.88);
		stroke: rgba(148, 163, 184, 0.35);
		stroke-width: 1;
		cursor: pointer;
		outline: none;
		transition:
			fill 0.25s,
			stroke 0.25s,
			opacity 0.25s;
	}

	.wedge:hover,
	.wedge:focus-visible {
		stroke: rgba(96, 165, 250, 0.95);
	}

	.wedge.on {
		fill: url(#ssc-wedge-on);
		stroke: rgba(147, 197, 253, 0.9);
	}

	.paused .wedge.on {
		opacity: 0.45;
	}

	.wedge-label {
		font-size: 8px;
		font-weight: 600;
		fill: #64748b;
		text-anchor: middle;
		dominant-baseline: central;
		pointer-events: none;
		user-select: none;
		transition: fill 0.25s;
	}

	.wedge-label.lit {
		fill: #f8fafc;
	}

	.paused .wedge-label.lit {
		fill: #cbd5e1;
	}

	.core {
		fill: url(#ssc-core);
		stroke: rgba(148, 163, 184, 0.5);
		stroke-width: 1.2;
		cursor: pointer;
		outline: none;
		transition:
			fill 0.25s,
			stroke 0.25s;
	}

	.core:hover,
	.core:focus-visible {
		stroke: rgba(96, 165, 250, 0.95);
	}

	.paused .core {
		fill: rgba(120, 53, 15, 0.75);
		stroke: rgba(245, 158, 11, 0.85);
	}

	.core-icon {
		font-size: 14px;
		fill: #e2e8f0;
		text-anchor: middle;
		dominant-baseline: central;
		pointer-events: none;
		user-select: none;
	}

	.paused .core-icon {
		fill: #fbbf24;
		animation: blink 1.6s ease-in-out infinite;
	}

	@keyframes blink {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.45;
		}
	}

	.readout {
		display: flex;
		flex-direction: column;
		gap: 2px;
		margin-bottom: 10px;
		padding: 8px 14px;
		border-radius: 14px;
		background: rgba(15, 23, 42, 0.85);
		border: 1px solid rgba(148, 163, 184, 0.22);
		backdrop-filter: blur(10px);
		box-shadow: 0 16px 40px rgba(2, 6, 23, 0.45);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.clock {
		font-size: 1.35rem;
		font-weight: 600;
		line-height: 1.1;
		letter-spacing: 0.04em;
		color: #f8fafc;
	}

	.speed-line {
		font-size: 0.78rem;
		font-weight: 600;
		color: #93c5fd;
	}

	.paused-badge {
		color: #fbbf24;
	}
</style>
