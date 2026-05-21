<script lang="ts">
	import { onMount } from 'svelte';

	let message = 'Ładowanie komunikatu z backendu...';

	onMount(async () => {
		try {
			const response = await fetch('http://localhost:8000/api/hello');

			if (response.ok) {
				const data = await response.json();
				message = data.message;
			} else {
				message = `Błąd serwera: ${response.status}`;
			}
		} catch (error) {
			message = 'Nie udało się nawiązać połączenia z backendem. Czy docker działa?';
			console.error(error);
		}
	});
</script>

<main>
	<h1>Prezentacja systemu</h1>
	<div class="card">
		<p>Status komunikacji:</p>
		<strong>{message}</strong>
	</div>
</main>
