<script lang="ts">
  import { quadtree } from 'd3-quadtree'
  import { getContext } from 'svelte'

  const { data, xGet, yGet, width, height } = getContext<any>('LayerCake')

  let visible = $state(false)
  let found = $state({})
  let e = $state({})

  type Props = {
    x?: string
    y?: string
    searchRadius?: number
    dataset?: any[]
    children?: any
    onSelect?: (found: any, event: MouseEvent) => void
  }

  let { x = 'x', y = 'y', searchRadius, dataset, children, onSelect }: Props = $props()

  let xGetter = $derived(x === 'x' ? $xGet : $yGet)
  let yGetter = $derived(y === 'y' ? $yGet : $xGet)

  function findItem(evt: MouseEvent) {
    e = evt

    const xLayerKey = `layer${x.toUpperCase()}` as 'layerX' | 'layerY'
    const yLayerKey = `layer${y.toUpperCase()}` as 'layerX' | 'layerY'

    found = finder.find(evt[xLayerKey], evt[yLayerKey], searchRadius) || {}
    visible = Object.keys(found).length > 0
  }

  function handleClick(evt: MouseEvent) {
    if (visible && typeof onSelect === 'function') {
      onSelect(found, evt)
    }
  }

  let finder = $derived(
    quadtree()
      .extent([
        [-1, -1],
        [$width + 1, $height + 1]
      ])
      .x(xGetter)
      .y(yGetter)
      .addAll(dataset || $data)
  )
</script>

<div
  class="bg"
  onmousemove={findItem}
  onmouseout={() => (visible = false)}
  onblur={() => (visible = false)}
  onclick={handleClick}
  onkeydown={(evt) => {
    if (evt.key === 'Enter' || evt.key === ' ') handleClick(evt as any)
  }}
  role="button"
  tabindex="0"
  aria-label="Select data point"
></div>
{@render children?.({ x: xGetter(found) || 0, y: yGetter(found) || 0, found, visible, e })}

<style>
  .bg {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
  }
</style>
