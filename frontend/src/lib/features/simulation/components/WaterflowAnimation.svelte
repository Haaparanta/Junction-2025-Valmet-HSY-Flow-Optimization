<script lang="ts">
  import { getSimulationContext } from '../logic.svelte'
  import FlowPath from './FlowPath.svelte'

  type Props = {
    inflowRef: HTMLDivElement | undefined
  }

  let { inflowRef }: Props = $props()

  let containerElement = $state<SVGSVGElement>()

  const ctx = getSimulationContext()

  let pumps = $derived(ctx.current.simulatedPumps)

  let inflowPaths = $state<Map<string, { startX: number; startY: number; endX: number; endY: number }>>(new Map())

  // Calculate paths whenever pumps or refs change
  $effect(() => {
    if (!inflowRef || !containerElement) return

    const activePumps = pumps.filter((p) => p.forecastedUse > 0)

    const calculatePaths = () => {
      const inflowRect = inflowRef.getBoundingClientRect()
      const containerRect = containerElement!.getBoundingClientRect()

      const inflowOriginX = inflowRect.left + inflowRect.width / 2 - containerRect.left
      const inflowOriginY = inflowRect.top + inflowRect.height / 2 - containerRect.top

      const newInflowPaths = new Map<string, { startX: number; startY: number; endX: number; endY: number }>()

      // Calculate paths for each active pump
      activePumps.forEach((pump) => {
        if (pump.forecastedUse <= 0) return

        // Find the specific pump element
        const pumpElement = document.querySelector(`[data-pump-id=\"${pump.name}\"]`) as HTMLElement
        if (!pumpElement) return

        const iconRect = pumpElement.getBoundingClientRect()

        // Inflow path: from inflow basin to left center of pump icon
        const pumpLeftX = iconRect.left + iconRect.width / 2 - containerRect.left
        const pumpLeftY = iconRect.top + iconRect.height / 2 - containerRect.top

        newInflowPaths.set(pump.name, {
          startX: inflowOriginX,
          startY: inflowOriginY,
          endX: pumpLeftX,
          endY: pumpLeftY
        })
      })

      inflowPaths = newInflowPaths
    }

    const timer = setTimeout(calculatePaths, 100)

    // Recalculate on window resize
    const handleResize = () => calculatePaths()
    window.addEventListener('resize', handleResize)

    // Add observers if the container or inflowRef size/position might change due to layout shifts
    const containerObserver = new ResizeObserver(calculatePaths)
    const inflowObserver = new ResizeObserver(calculatePaths)

    containerObserver.observe(containerElement)
    inflowObserver.observe(inflowRef)

    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', handleResize)
      containerObserver.disconnect()
      inflowObserver.disconnect()
    }
  })
</script>

<svg class="pointer-events-none absolute top-0 left-0 z-0 h-full w-full" bind:this={containerElement}>
  {#each Array.from(inflowPaths.entries()) as [pumpId, coords], index (pumpId)}
    <FlowPath
      id="inflow-{pumpId}"
      startX={coords.startX}
      startY={coords.startY}
      endX={coords.endX}
      endY={coords.endY}
      color="rgb(34, 211, 238)"
      animationDelay={index * 0.05}
    />
  {/each}
</svg>
