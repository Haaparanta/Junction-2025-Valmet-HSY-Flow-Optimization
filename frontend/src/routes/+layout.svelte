<script lang="ts">
  import favicon from '$lib/assets/favicon.svg'
  import { Toaster } from 'svelte-french-toast'
  import '../app.css'

  let { children } = $props()
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

<div class="dashboard-gradient min-h-screen p-8">
  <Toaster />
  <div class="mx-auto flex max-w-7xl flex-col gap-2">
    {@render children()}
  </div>
</div>
