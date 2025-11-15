<script lang="ts">
  import { page } from '$app/state'
  import Button from '$lib/components/Button.svelte'
</script>

<div class="flex min-h-[80vh] items-center justify-center">
  <div
    class="relative flex w-full max-w-2xl flex-col items-center gap-8 rounded-md border border-slate-800 bg-slate-950/80 p-12 text-center backdrop-blur"
  >
    <div class="space-y-4">
      <div class="text-8xl font-bold text-cyan-400">{page.status}</div>
      <h1 class="text-3xl font-bold text-slate-200">
        {page.status === 404 ? 'Page Not Found' : 'Something Went Wrong'}
      </h1>
      <p class="text-lg text-slate-400">{page.error?.message || 'An unexpected error occurred'}</p>
    </div>

    <div class="flex gap-4">
      <Button variant="primary" href="/">Go Home</Button>
      <Button variant="secondary" onclick={() => window.history.back()}>Go Back</Button>
    </div>

    {#if page.status === 404}
      <p class="text-sm text-slate-500">
        The simulation you're looking for might have been removed or the URL might be incorrect.
      </p>
    {/if}
  </div>
</div>
