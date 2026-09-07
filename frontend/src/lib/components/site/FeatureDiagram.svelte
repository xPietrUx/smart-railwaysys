<script lang="ts">
	export let kind: 'network' | 'incidents' | 'timetable' | 'scenarios';
</script>

<svg class="diagram" viewBox="0 0 440 300" fill="none" aria-hidden="true">
	{#if kind === 'network'}
		<g stroke="currentColor" stroke-width="1.1" stroke-linejoin="miter">
			<path d="M40 168 L112 128 L184 168 L112 208 Z" />
			<path d="M112 128 L112 92" />
			<path d="M96 108 H128 M96 98 H128" />
			<rect x="102" y="70" width="20" height="22" />
			<path d="M184 168 L256 128 L328 168 L256 208 Z" />
			<path d="M256 128 L256 86" />
			<path d="M240 104 H272 M240 94 H272" />
			<rect x="246" y="64" width="20" height="22" />
			<path d="M328 168 L400 128 L400 168 L328 208 Z" />
			<path d="M400 128 L400 90" />
			<path d="M384 108 H416" />
			<rect x="390" y="68" width="20" height="22" />
			<path d="M112 208 L184 168 L256 208" />
			<path d="M256 208 L328 168" />
			<path d="M72 236 H390" opacity="0.35" />
			<path d="M88 248 H374" opacity="0.18" />
			<path d="M48 148 L40 168" opacity="0.5" />
		</g>
	{:else if kind === 'incidents'}
		<g stroke="currentColor" stroke-width="1.1">
			<path d="M156 70 L284 70 L348 108 L348 196 L220 196 L156 158 Z" />
			<path d="M284 70 L284 158 L156 158" />
			<path d="M284 158 L348 196" />
			<path d="M220 112 L236 148 H204 Z" />
			<path d="M220 160 V172" />
			<path d="M92 96 L156 96" />
			<path d="M92 96 L92 58" />
			<path d="M78 74 H106" />
			<path d="M348 108 L404 80" />
			<path d="M404 80 L404 48" />
			<path d="M390 62 H418" />
			<path d="M156 158 L92 196 L92 232" />
			<path d="M78 214 H106" />
			<path d="M220 196 L220 244" opacity="0.4" />
			<path d="M64 252 H380" opacity="0.28" />
		</g>
	{:else if kind === 'timetable'}
		<g stroke="currentColor" stroke-width="1.1">
			<path d="M58 214 L58 96 L118 62 L118 180 Z" />
			<path d="M58 96 L118 62" />
			<path d="M68 118 H108 M68 132 H108 M68 146 H96" />
			<path d="M138 228 L138 84 L230 32 L230 176 Z" />
			<path d="M138 84 L230 32" />
			<path d="M152 102 H216 M152 118 H216 M152 134 H200 M152 150 H184" />
			<path d="M250 216 L250 98 L322 56 L322 174 Z" />
			<path d="M250 98 L322 56" />
			<path d="M262 116 H310 M262 132 H298" />
			<path d="M342 200 L342 114 L390 86 L390 172 Z" />
			<path d="M342 114 L390 86" />
			<path d="M352 132 H380" />
			<path d="M40 248 H410" opacity="0.3" />
			<path d="M56 260 H394" opacity="0.16" />
		</g>
	{:else}
		<g stroke="currentColor" stroke-width="1.1">
			<path d="M210 36 L258 64 L258 112 L210 140 L162 112 L162 64 Z" />
			<path d="M210 36 L210 140" />
			<path d="M162 64 L258 64" />
			<path d="M210 140 L118 192" />
			<path d="M210 140 L302 192" />
			<path d="M118 192 L166 220 L166 260 L118 288 L70 260 L70 220 Z" />
			<path d="M118 192 L118 288" />
			<path d="M302 192 L350 220 L350 260 L302 288 L254 260 L254 220 Z" />
			<path d="M302 192 L302 288" />
			<path d="M118 192 L46 232 L46 268" />
			<path d="M32 250 H60" />
			<path d="M302 192 L394 232 L394 268" />
			<path d="M380 250 H408" />
			<path d="M70 260 H166" opacity="0.3" />
			<path d="M254 260 H350" opacity="0.3" />
		</g>
	{/if}
</svg>

<style>
	.diagram {
		width: min(100%, 440px);
		height: auto;
		display: block;
		overflow: visible;
	}
</style>
