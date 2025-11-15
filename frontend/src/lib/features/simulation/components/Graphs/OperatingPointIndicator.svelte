<script lang="ts">
  import { getContext } from 'svelte'

  type Props = {
    currentFlow: number
    performanceCurve: Array<{ x: number; y: number }>
  }

  let { currentFlow, performanceCurve }: Props = $props()

  const { xScale, yScale } = getContext<any>('LayerCake')

  // Find the current operating point on the performance curve
  // Interpolate between points if exact match isn't found
  const operatingPoint = $derived.by(() => {
    if (!performanceCurve || performanceCurve.length === 0 || currentFlow === 0) return null

    // Find the two points that bracket the current flow
    let lowerPoint = performanceCurve[0]
    let upperPoint = performanceCurve[performanceCurve.length - 1]

    for (let i = 0; i < performanceCurve.length - 1; i++) {
      const curr = performanceCurve[i]
      const next = performanceCurve[i + 1]

      if (currentFlow >= curr.x && currentFlow <= next.x) {
        lowerPoint = curr
        upperPoint = next
        break
      }
    }

    // Linear interpolation to find the head at current flow
    const t = (currentFlow - lowerPoint.x) / (upperPoint.x - lowerPoint.x)
    const interpolatedHead = lowerPoint.y + t * (upperPoint.y - lowerPoint.y)

    return {
      x: currentFlow,
      y: interpolatedHead
    }
  })

  const xPos = $derived(operatingPoint && $xScale ? $xScale(operatingPoint.x) : undefined)
  const yPos = $derived(operatingPoint && $yScale ? $yScale(operatingPoint.y) : undefined)
</script>

{#if typeof xPos === 'number' && typeof yPos === 'number' && Number.isFinite(xPos) && Number.isFinite(yPos)}
  <!-- Crosshair lines -->
  <line
    x1={xPos}
    y1="0"
    x2={xPos}
    y2="100%"
    stroke="var(--color-accent-primary)"
    stroke-width="2"
    stroke-dasharray="4 4"
    opacity="0.6"
  />
  <line
    x1="0"
    y1={yPos}
    x2="100%"
    y2={yPos}
    stroke="var(--color-accent-primary)"
    stroke-width="2"
    stroke-dasharray="4 4"
    opacity="0.6"
  />

  <!-- Pulsing circle at operating point -->
  <circle cx={xPos} cy={yPos} r="8" fill="var(--color-accent-primary)" opacity="0.3">
    <animate attributeName="r" from="8" to="12" dur="1.5s" repeatCount="indefinite" />
    <animate attributeName="opacity" from="0.3" to="0" dur="1.5s" repeatCount="indefinite" />
  </circle>

  <!-- Main operating point circle -->
  <circle
    cx={xPos}
    cy={yPos}
    r="6"
    fill="var(--color-accent-primary)"
    stroke="var(--color-bg-secondary)"
    stroke-width="2"
  />
{/if}
