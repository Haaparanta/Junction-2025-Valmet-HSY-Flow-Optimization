<script lang="ts">
  import Icon from '@iconify/svelte'
  import { Tween } from 'svelte/motion'

  type Props = {
    forecastedUse: number
    name: string
    performanceCurve: number[][]
  }

  let { name, forecastedUse, performanceCurve }: Props = $props()

  let isActive = $derived(forecastedUse !== undefined && forecastedUse > 0)

  // Constant slow rotation for active pumps
  let rotation = new Tween(0, { duration: 1000, easing: (t) => t })

  $effect(() => {
    if (isActive) {
      const interval = setInterval(() => {
        rotation.set(rotation.current + 360)
      }, 1000)
      return () => clearInterval(interval)
    }
  })
</script>

<div class="pointer-events-none relative z-10 flex flex-col items-center gap-2">
  <div class="relative z-10" data-pump-icon>
    <Icon
      icon="material-symbols:water-pump-outline-rounded"
      class="h-9 w-9"
      data-pump-id={name}
      style="color: {isActive ? 'var(--color-chart-strategy)' : 'var(--color-text-subtle)'}; stroke-width: 1.5;"
    />

    {#if isActive}
      <div
        class="absolute inset-0 top-1/2 left-1/2 h-10 w-10 rounded-full blur-sm"
        style="transform: translate(-50%, -50%) rotate({rotation.current}deg); background: conic-gradient(from 0deg, #10b981d9 0deg 90deg, #3b82f6d9 90deg 180deg, #10b981d9 180deg 270deg, #3b82f6d9 270deg 360deg); background-opacity: 0.6;"
      ></div>
    {/if}
  </div>

  <div class="space-y-0.5 text-center">
    <div class="text-sm" style:color={isActive ? 'var(--color-text-primary)' : 'var(--color-text-muted)'}>
      {name}
    </div>
    <div class="text-xs" style:color={isActive ? 'var(--color-chart-strategy)' : 'var(--color-text-disabled)'}>
      {forecastedUse.toFixed(1)} m³/s
    </div>
  </div>
</div>
