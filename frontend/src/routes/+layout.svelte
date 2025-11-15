<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="dashboard-gradient min-h-screen p-8">
	<div class="mx-auto max-w-7xl">
		{@render children()}
	</div>
</div>
