<script lang="ts">
  import { getContext } from 'svelte'

  const { width, height, xScale, xDomain } = getContext<any>('LayerCake')

  let {
    ticks = 6,
    tickColor = 'var(--color-text-muted)',
    gridlines = true,
    format = (d: number) => `${d}h`,
    hoursOnly = false
  } = $props()

  const tickValues = $derived.by(() => {
    if (!$xScale || !$xDomain) return []
    const domain = $xDomain

    if (hoursOnly) {
      // Generate ticks only at full hours
      const startTime = new Date(domain[0])
      const endTime = new Date(domain[1])
      const ticks = []

      // Round up to next hour
      const currentTime = new Date(startTime)
      currentTime.setMinutes(0, 0, 0)
      if (currentTime < startTime) {
        currentTime.setHours(currentTime.getHours() + 1)
      }

      while (currentTime <= endTime) {
        ticks.push(currentTime.getTime())
        currentTime.setHours(currentTime.getHours() + 1)
      }

      return ticks
    }

    const step = (domain[1] - domain[0]) / ticks
    return Array.from({ length: ticks + 1 }, (_, i) => domain[0] + i * step)
  })
</script>

<g class="axis axis-x">
  {#each tickValues as tick, i}
    {#if gridlines}
      <line
        x1={$xScale(tick)}
        x2={$xScale(tick)}
        y1="0"
        y2={$height}
        stroke="var(--color-chart-grid)"
        stroke-width="1"
        stroke-opacity="0.3"
      />
    {/if}
    {#if i % 2 === 0}
      <text x={$xScale(tick)} y={$height + 20} text-anchor="middle" fill={tickColor} font-size="12">
        {format(tick)}
      </text>
    {/if}
  {/each}
</g>
