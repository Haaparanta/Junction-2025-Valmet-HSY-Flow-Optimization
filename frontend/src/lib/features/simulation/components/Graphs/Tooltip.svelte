<script lang="ts">
  import { getContext } from 'svelte'
  type TooltipDataset = {
    name: string
    value: number
    unit: string
    color: string
  }

  const { width, yScale } = getContext<any>('LayerCake')

  let {
    x = 0,
    y = 0,
    visible = false,
    datasets = [],
    timestamp = 0,
    offset = -20,
    anchorY = null
  }: {
    x?: number
    y?: number
    visible?: boolean
    datasets?: TooltipDataset[]
    timestamp?: number
    offset?: number
    anchorY?: number | null
  } = $props()

  const formatTime = (ts: number) => {
    const date = new Date(ts)
    return date.toLocaleString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const w = 180
  const w2 = w / 2

  const left = $derived(Math.min(Math.max(w2, x), $width - w2))
  const top = $derived(anchorY !== null ? $yScale(anchorY) + offset : y + offset)
</script>

{#if visible}
  {#if Number.isFinite(x)}
    <div class="hover-line" style={`left:${x}px;`}></div>
  {/if}
  <div
    class="tooltip card-glass pointer-events-none rounded-lg px-3 py-2 text-sm shadow-lg"
    style="
      width: {w}px;
      left: {left}px;
      top: {top}px;
      color: var(--color-text-primary);
    "
  >
    <div class="mb-2 font-semibold" style="color: var(--color-text-secondary)">
      {formatTime(timestamp)}
    </div>
    <div class="flex flex-col gap-1">
      {#each datasets as dataset}
        <div class="flex items-center gap-2">
          {#if dataset.color.includes(',')}
            <!-- Gradient indicator for combined outflow -->
            <div class="gradient-indicator h-2 w-2 rounded-full"></div>
          {:else}
            <div class="h-2 w-2 rounded-full" style="background-color: {dataset.color}"></div>
          {/if}
          <span>{dataset.value.toFixed(dataset.unit.includes('€') ? 2 : 0)} {dataset.unit}</span>
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .tooltip {
    position: absolute;
    z-index: 50;
    transform: translate(-50%, -100%);
    transition:
      left 250ms ease-out,
      top 250ms ease-out;
  }

  .hover-line {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background-color: var(--color-primary, #10b981);
    opacity: 0.3;
    pointer-events: none;
    z-index: 40;
  }

  @keyframes gradientShift {
    0% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
    100% {
      background-position: 0% 50%;
    }
  }

  .gradient-indicator {
    background: linear-gradient(90deg, #10b981, #f59e0b, #06b6d4, #f59e0b, #ec4899, #8b5cf6, #06b6d4, #14b8a6, #10b981);
    background-size: 300% 100%;
    animation: gradientShift 4s ease-in-out infinite;
  }
</style>
