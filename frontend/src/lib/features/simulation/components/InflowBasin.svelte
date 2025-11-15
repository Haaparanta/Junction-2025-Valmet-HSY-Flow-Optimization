<script lang="ts">
  import Icon from '@iconify/svelte'

  type Props = {
    maxHeight: number // in meters
    currentHeight: number // in meters
    currentInflow: number // in cubic meters per second
    ref: HTMLDivElement | undefined
  }

  let { maxHeight, currentHeight, currentInflow, ref = $bindable() }: Props = $props()

  // Calculate level as percentage from current volume vs max capacity
  let level = $derived((currentHeight / maxHeight) * 100)
</script>

<div class="relative z-10 flex flex-col items-center">
  <div class="mb-4 flex items-center gap-2 text-cyan-400">
    <Icon icon="lucide:droplets" class="h-5 w-5" />
    <span>Inflow Basin L1</span>
  </div>

  <!-- Current Inflow Display -->
  <div class="card-glass-secondary mb-3 rounded-lg px-4 py-2">
    <div class="flex items-center gap-2">
      <Icon icon="lucide:arrow-down" class="h-4 w-4" style="color: var(--color-chart-inflow)" />
      <span class="text-xs" style="color: var(--color-text-secondary)">Inflow:</span>
      <span class="font-semibold" style="color: var(--color-chart-inflow)">
        {currentInflow.toFixed(1)} m³/s
      </span>
    </div>
  </div>

  <div bind:this={ref} class="relative h-80 w-48 overflow-hidden rounded-lg border-4 border-slate-700 bg-black">
    <div
      class="absolute right-0 bottom-0 left-0 bg-linear-to-t from-cyan-500 to-cyan-400"
      style:height="{level}%"
      style:opacity="0.8"
      style:transition="height 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
    >
      <div class="absolute top-0 right-0 left-0 h-2 bg-cyan-300 opacity-50">
        <div class="animate-wave h-full bg-white opacity-30"></div>
      </div>
    </div>

    <div class="pointer-events-none absolute inset-0">
      {#each [25, 50, 75, 100] as mark}
        <div class="absolute right-0 left-0 border-t border-dashed border-slate-700" style:bottom="{mark}%">
          <span class="absolute -top-2 -left-8 text-xs text-slate-600">
            {mark}%
          </span>
        </div>
      {/each}
    </div>

    <div class="pointer-events-none absolute right-0 left-0 border-t-2 border-cyan-300" style:bottom="{level}%">
      <div class="absolute -top-3 -right-16 rounded bg-cyan-500 px-2 py-1 text-xs text-white">
        {level.toFixed(1)}%
      </div>
    </div>
  </div>

  <div class="mt-4 space-y-1 text-center">
    <div class="text-white">
      {currentHeight.toFixed(0)} m
    </div>
    <div class="text-xs text-slate-400">
      Max: {maxHeight} m
    </div>
  </div>
</div>

<style>
  @keyframes wave {
    0% {
      transform: translateX(-100%);
    }
    100% {
      transform: translateX(100%);
    }
  }

  .animate-wave {
    animation: wave 2s linear infinite;
  }
</style>
