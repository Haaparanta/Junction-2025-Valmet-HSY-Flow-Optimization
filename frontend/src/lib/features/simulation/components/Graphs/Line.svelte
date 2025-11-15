<script lang="ts">
  import { curveMonotoneX, line } from 'd3-shape'
  import { getContext } from 'svelte'

  const { data: contextData, xGet, yGet, height } = getContext<any>('LayerCake')

  let {
    stroke = 'var(--color-chart-electricity)',
    strokeWidth = 2,
    showArea = false,
    areaOpacity = 0.2,
    data = undefined
  } = $props()

  const lineData = $derived(data || $contextData || [])

  const path = $derived(
    line()
      .x((d: any) => $xGet(d))
      .y((d: any) => $yGet(d))
      .curve(curveMonotoneX)(lineData)
  )
</script>

<path d={path} fill="none" {stroke} stroke-width={strokeWidth} stroke-linecap="round" />
