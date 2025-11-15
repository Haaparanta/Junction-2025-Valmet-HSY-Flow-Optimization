<script lang="ts">
  import { getContext } from 'svelte'

  const { height, width, yScale, yDomain } = getContext<any>('LayerCake')

  let {
    ticks = 5,
    tickColor = 'var(--color-text-muted)',
    gridlines = true,
    label = '',
    side = 'left',
    format = (d: number) => d.toFixed(1)
  } = $props()

  const tickValues = $derived.by(() => {
    if (!$yScale || !$yDomain) return []
    const domain = $yDomain
    const step = (domain[1] - domain[0]) / ticks
    return Array.from({ length: ticks + 1 }, (_, i) => domain[0] + i * step)
  })
</script>

<g class="axis axis-y">
  {#each tickValues as tick}
    {#if gridlines}
      <line
        x1="0"
        x2="100%"
        y1={$yScale(tick)}
        y2={$yScale(tick)}
        stroke="var(--color-chart-grid)"
        stroke-width="1"
        stroke-opacity="0.3"
      />
    {/if}
    <text
      x={side === 'left' ? -5 : $width + 5}
      y={$yScale(tick)}
      text-anchor={side === 'left' ? 'end' : 'start'}
      fill={tickColor}
      font-size="12"
      dy="0.33em"
    >
      {format(tick)}
    </text>
  {/each}
  {#if label}
    <text
      x={side === 'left' ? -40 : $width + 40}
      y={$height / 2}
      text-anchor="middle"
      fill={tickColor}
      font-size="12"
      transform="rotate({side === 'left' ? -90 : 90}, {side === 'left' ? -40 : $width + 40}, {$height / 2})"
      style="paint-order: stroke; stroke: var(--color-bg-primary, #1a1a1a); stroke-width: 3px; stroke-linecap: butt; stroke-linejoin: miter;"
    >
      {label}
    </text>
  {/if}
</g>
