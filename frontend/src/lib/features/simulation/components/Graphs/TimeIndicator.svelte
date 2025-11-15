<script lang="ts">
  import { getContext } from 'svelte'

  let { x, xNext }: { x?: number; xNext?: number } = $props()

  const { height, width, xScale, xRange } = getContext<any>('LayerCake')
  const xPos = $derived(typeof x === 'number' && $xScale ? $xScale(x) : undefined)
  const xPosNext = $derived(
    typeof xNext === 'number' && $xScale
      ? $xScale(xNext)
      : typeof xPos === 'number'
        ? xPos + ($xRange ? ($xRange[1] - $xRange[0]) / 24 : 20)
        : undefined
  )
  const rectWidth = $derived(typeof xPos === 'number' && typeof xPosNext === 'number' ? xPosNext - xPos : 0)
</script>

{#if typeof xPos === 'number' && Number.isFinite(xPos) && rectWidth > 0}
  <rect x={xPos} y={0} width={rectWidth} height={$height} fill="var(--color-accent-primary)" opacity="0.15" />
{/if}
