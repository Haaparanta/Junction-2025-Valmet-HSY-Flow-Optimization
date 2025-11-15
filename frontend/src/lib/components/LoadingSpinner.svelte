<script lang="ts">
  let { message = 'Loading...', subtitle }: { message?: string; subtitle?: string } = $props()
</script>

<div class="flex min-h-[600px] items-center justify-center">
  <div class="text-center">
    <div class="relative mb-8 inline-flex">
      <!-- Outer rotating ring -->
      <div
        class="absolute inset-0 animate-spin rounded-full border-4 border-slate-800 border-t-cyan-400 opacity-75"
        style="width: 80px; height: 80px;"
      ></div>

      <!-- Inner pulsing circle -->
      <div
        class="absolute inset-0 m-auto animate-pulse rounded-full bg-cyan-400/20"
        style="width: 48px; height: 48px;"
      ></div>

      <!-- Center dot -->
      <div class="relative flex items-center justify-center" style="width: 80px; height: 80px;">
        <div class="h-3 w-3 rounded-full bg-cyan-400"></div>
      </div>
    </div>

    <h2 class="mb-2 text-xl font-semibold text-slate-300">{message}</h2>
    {#if subtitle}
      <p class="text-sm text-slate-500">{subtitle}</p>
    {/if}
  </div>
</div>
