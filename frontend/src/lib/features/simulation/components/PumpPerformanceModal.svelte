<script lang="ts">
  import Icon from '@iconify/svelte'
  import { LayerCake, Svg } from 'layercake'
  import { cubicOut } from 'svelte/easing'
  import { fade, type TransitionConfig } from 'svelte/transition'
  import AxisX from './Graphs/AxisX.svelte'
  import AxisXLabel from './Graphs/AxisXLabel.svelte'
  import AxisY from './Graphs/AxisY.svelte'
  import OperatingPointIndicator from './Graphs/OperatingPointIndicator.svelte'
  import PerformanceCurveLine from './Graphs/PerformanceCurveLine.svelte'
  import PerformanceCurvePoints from './Graphs/PerformanceCurvePoints.svelte'

  type Props = {
    name: string
    performanceCurve: number[][] // [flow, head] pairs
    currentFlow: number
    onClose: () => void
  }

  let { name, performanceCurve, currentFlow, onClose }: Props = $props()

  // Transform performance curve data for LayerCake
  // performanceCurve is [[flow1, head1], [flow2, head2], ...]
  // Convert flow from m³/s to L/s (multiply by 1000)
  const data = $derived(
    performanceCurve.map(([flow, head]) => ({
      x: flow * 1000,
      y: head
    }))
  )

  // Calculate efficiency scores (normalized 0-1, higher is better)
  // Efficiency is based on flow rate - higher flow = better efficiency
  const efficiencyScores = $derived.by(() => {
    if (data.length === 0) return []

    const maxFlow = Math.max(...data.map((d) => d.x))
    const minFlow = Math.min(...data.map((d) => d.x))

    return data.map((point) => {
      // Normalize flow rate to 0-1 range
      // Higher flow rate = higher efficiency
      if (maxFlow === minFlow) return 0.5
      const efficiency = (point.x - minFlow) / (maxFlow - minFlow)

      return Math.max(0, Math.min(1, efficiency))
    })
  })

  // Create color interpolation function from red to green
  const getColorForEfficiency = (efficiency: number): string => {
    // Red (low) to Yellow (medium) to Green (high)
    if (efficiency < 0.5) {
      // Red to Yellow
      const r = 255
      const g = Math.round(255 * (efficiency * 2))
      const b = 0
      return `rgb(${r}, ${g}, ${b})`
    } else {
      // Yellow to Green
      const r = Math.round(255 * (1 - (efficiency - 0.5) * 2))
      const g = 255
      const b = 0
      return `rgb(${r}, ${g}, ${b})`
    }
  }

  // Format functions
  const formatFlow = (value: number) => `${value.toFixed(1)}`
  const formatHead = (value: number) => `${value.toFixed(1)}`

  // Handle click outside to close
  const handleBackdropClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // Handle escape key to close
  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose()
    }
  }

  // Custom flip transition - rotates and scales in
  function flip(node: HTMLElement): TransitionConfig {
    return {
      duration: 300,
      easing: cubicOut,
      css: (t) => {
        const scale = 0.8 + t * 0.2
        const rotateY = (1 - t) * 90
        const opacity = t
        return `
          transform: scale(${scale}) rotateY(${rotateY}deg);
          opacity: ${opacity};
          transform-style: preserve-3d;
        `
      }
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div
  {@attach (node) => {
    // Mount this element to document.body to escape any relative positioning contexts
    document.body.appendChild(node)
    return () => {
      document.body.removeChild(node)
    }
  }}
  class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
  onclick={handleBackdropClick}
  onkeydown={handleKeydown}
  role="button"
  tabindex="-1"
  transition:fade
>
  <div
    transition:flip
    class="card-glass relative w-full max-w-2xl rounded-lg p-6 shadow-xl"
    style="background-color: var(--color-bg-secondary);"
  >
    <div class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <Icon
          icon="material-symbols:water-pump-outline-rounded"
          class="h-8 w-8"
          style="color: var(--color-chart-strategy);"
        />
        <div>
          <h2 class="text-xl font-semibold" style="color: var(--color-text-primary);">
            {name}
          </h2>
          <p class="text-sm" style="color: var(--color-text-secondary);">Performance Curve</p>
        </div>
      </div>
      <button
        onclick={onClose}
        class="rounded-full p-2 transition-colors hover:bg-white/10"
        style="color: var(--color-text-secondary);"
      >
        <Icon icon="mdi:close" class="h-6 w-6" />
      </button>
    </div>

    <!-- Graph -->
    <div class="h-80">
      {#if data.length > 0}
        <LayerCake padding={{ top: 20, right: 40, bottom: 50, left: 50 }} x="x" y="y" {data} xNice={true} yNice={true}>
          <Svg>
            <AxisY
              gridlines={true}
              label="Vertical Distance (m)"
              side="left"
              format={formatHead}
              tickColor="var(--color-text-muted)"
            />
            <AxisX gridlines={true} format={formatFlow} tickColor="var(--color-text-muted)" ticks={5} />
            <AxisXLabel label="Flow Rate (L/s)" />

            <!-- Draw line segments with colors based on efficiency -->
            <PerformanceCurveLine {data} {efficiencyScores} {getColorForEfficiency} />

            <!-- Draw points -->
            <PerformanceCurvePoints {data} {efficiencyScores} {getColorForEfficiency} />

            <!-- Show current operating point -->
            <OperatingPointIndicator currentFlow={currentFlow * 1000} performanceCurve={data} />
          </Svg>
        </LayerCake>
      {:else}
        <div class="flex h-full items-center justify-center" style="color: var(--color-text-muted);">
          No performance data available
        </div>
      {/if}
    </div>

    <!-- Legend -->
    <div class="mt-4 flex flex-wrap items-center justify-center gap-4">
      <div class="flex items-center gap-2">
        <div class="h-3 w-3 rounded-full" style="background-color: rgb(255, 0, 0);"></div>
        <span class="text-xs" style="color: var(--color-text-secondary);">Low Efficiency</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="h-3 w-3 rounded-full" style="background-color: rgb(255, 255, 0);"></div>
        <span class="text-xs" style="color: var(--color-text-secondary);">Medium Efficiency</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="h-3 w-3 rounded-full" style="background-color: rgb(0, 255, 0);"></div>
        <span class="text-xs" style="color: var(--color-text-secondary);">High Efficiency</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="h-3 w-3 rounded-full" style="background-color: var(--color-accent-primary);"></div>
        <span class="text-xs" style="color: var(--color-text-secondary);">Current Operating Point</span>
      </div>
    </div>

    <div class="card-glass-secondary mt-4 rounded-md p-3">
      <p class="text-xs leading-relaxed" style="color: var(--color-text-secondary);">
        The performance curve shows how much water this pump can move (flow rate in L/s) at different vertical pumping
        distances (head in meters). Higher flow rates are more efficient, indicated by green coloring, while lower flow
        rates are less efficient (red coloring).
      </p>
    </div>
  </div>
</div>

<style>
  /* Prevent scrolling when modal is open */
  :global(body:has(div[role='button'])) {
    overflow: hidden;
  }
</style>
