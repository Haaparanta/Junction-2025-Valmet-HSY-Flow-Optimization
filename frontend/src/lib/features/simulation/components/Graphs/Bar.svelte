<script lang="ts">
  import { getContext } from 'svelte'

  const { data: contextData, xGet, yGet } = getContext<any>('LayerCake')

  let { fill = 'var(--color-chart-result)', opacity = 0.3, data = undefined } = $props()

  const barData = $derived(data || $contextData || [])

  // Calculate bar width based on data points
  const barWidth = $derived.by(() => {
    if (barData.length < 2) return 10
    const x1 = $xGet(barData[0])
    const x2 = $xGet(barData[1])
    return Math.abs(x2 - x1) * 0.8 // 80% of the space between points
  })
</script>

<g class="bars">
  {#each barData as d}
    {@const hasBaseline = 'y0' in d}
    {@const yTop = hasBaseline ? $yGet({ x: d.x, y: (d as any).y0 + d.y }) : $yGet(d)}
    {@const yBottom = hasBaseline ? $yGet({ x: d.x, y: (d as any).y0 }) : $yGet({ x: d.x, y: 0 })}
    <rect x={$xGet(d) - barWidth / 2} y={yTop} width={barWidth} height={Math.abs(yBottom - yTop)} {fill} {opacity} />
  {/each}
</g>
