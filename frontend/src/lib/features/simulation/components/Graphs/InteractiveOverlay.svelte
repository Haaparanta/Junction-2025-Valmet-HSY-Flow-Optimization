<script lang="ts">
  let {
    onMouseMove,
    onMouseLeave,
    onClick
  }: {
    onMouseMove: (e: MouseEvent, svg: SVGElement) => void
    onMouseLeave: () => void
    onClick: (e: MouseEvent, svg: SVGElement) => void
  } = $props()

  let svgElement = $state<SVGElement>()
</script>

<rect
  bind:this={svgElement}
  x="0"
  y="0"
  width="100%"
  height="100%"
  fill="transparent"
  role="button"
  tabindex="0"
  aria-label="Chart interaction area - click to select time"
  style="cursor: pointer;"
  onmousemove={(e) => svgElement && onMouseMove(e, svgElement)}
  onmouseleave={onMouseLeave}
  onclick={(e) => svgElement && onClick(e, svgElement)}
  onkeydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') svgElement && onClick(e as any, svgElement)
  }}
/>
