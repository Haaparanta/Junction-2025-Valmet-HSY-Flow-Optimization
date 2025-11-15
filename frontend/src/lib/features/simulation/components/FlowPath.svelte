<script lang="ts">
  import { quintOut } from 'svelte/easing'
  import { fade } from 'svelte/transition'

  type Props = {
    id: string
    startX: number
    startY: number
    endX: number
    endY: number
    color: string
    animationDelay?: number
  }

  let { id, startX, startY, endX, endY, color, animationDelay = 0 }: Props = $props()

  interface ChevronPosition {
    x: number
    y: number
    angle: number
  }

  let chevronPositions = $state<ChevronPosition[]>([])
  let pathElement = $state<SVGPathElement>()

  // Calculate control points for smoother, more natural bezier curve
  let path = $derived(() => {
    // Calculate orientation
    const horizontalDistance = Math.abs(endX - startX)
    const verticalDistance = Math.abs(endY - startY)

    const horizontal = horizontalDistance >= verticalDistance

    // The control points should be as follows: in the middle between start and end,
    // in the horizontal case the first control point is on the same y axis as the start point,
    // and the second control point on the same y axis as the end point. In vertical case, vice versa.
    let cp1X, cp1Y, cp2X, cp2Y
    if (horizontal) {
      const middleX = (startX + endX) / 2
      cp1X = middleX + horizontalDistance * 0.4
      cp1Y = startY
      cp2X = middleX - horizontalDistance * 0.4
      cp2Y = endY
    } else {
      const middleY = (startY + endY) / 2
      cp1X = startX
      cp1Y = endY
      cp2X = startY
      cp2Y = endY
    }

    return `M ${startX} ${startY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${endX} ${endY}`
  })

  // Custom transition for path drawing animation
  function drawPath(node: SVGPathElement, { delay = 0, duration = 800 }) {
    const length = node.getTotalLength()

    return {
      delay,
      duration,
      easing: quintOut,
      css: (t: number) => `
        stroke-dasharray: ${length};
        stroke-dashoffset: ${length * (1 - t)};
        opacity: ${t * 0.5};
      `
    }
  }

  $effect(() => {
    const deps = [startX, startY, endX, endY]
    if (!pathElement) return

    const calculatePositions = () => {
      if (!pathElement) return

      const positions: ChevronPosition[] = []
      const pathLength = pathElement.getTotalLength()

      // Calculate chevron size (original width 165, scaled by 0.15)
      const chevronWidth = 165 * 0.15
      // Add some spacing between chevrons
      const spacing = chevronWidth * 0.5
      const totalChevronSpace = chevronWidth + spacing

      // Calculate how many chevrons can fit along the path
      const dynamicNumChevrons = Math.floor(pathLength / totalChevronSpace)
      const actualNumChevrons = Math.max(1, dynamicNumChevrons) // At least 1 chevron

      // Calculate chevron spacing to distribute evenly with clearance
      const chevronSpacing = pathLength / (actualNumChevrons + 1)

      for (let i = 0; i < actualNumChevrons; i++) {
        const distance = chevronSpacing * (i + 1)
        const point = pathElement.getPointAtLength(distance)

        // Calculate angle by looking at nearby point
        const nextDistance = Math.min(distance + 1, pathLength)
        const nextPoint = pathElement.getPointAtLength(nextDistance)
        const angle = Math.atan2(nextPoint.y - point.y, nextPoint.x - point.x) * (180 / Math.PI)

        positions.push({
          x: point.x,
          y: point.y,
          angle: angle
        })
      }

      chevronPositions = positions
    }

    // Delay to ensure path is rendered
    const timer = setTimeout(calculatePositions, 100)
    return () => clearTimeout(timer)
  })
</script>

<g>
  <path
    bind:this={pathElement}
    id="flow-path-{id}"
    d={path()}
    stroke={color}
    stroke-opacity="0.2"
    stroke-width="3"
    fill="none"
    stroke-linecap="round"
    in:drawPath={{ delay: animationDelay * 200, duration: 4 * 1000 }}
  />

  {#each chevronPositions as pos, i (`chevron-${id}-${i}`)}
    <g
      class="chevron-wrapper"
      transform="translate({pos.x}, {pos.y}) rotate({pos.angle}) scale(0.15, 0.2)"
      style="--animation-delay: {i * 0.2}s"
      in:fade={{ delay: animationDelay * 200 + i * 200, duration: 300 }}
    >
      <path
        d="M0.527886 3.34954C-0.645523 2.06612 0.264963 0 2.00394 0H145.728C146.204 0 146.664 0.169797 147.026 0.478871L165.184 15.9789C166.119 16.7773 166.119 18.2227 165.184 19.0211L147.026 34.5211C146.664 34.8302 146.204 35 145.728 35H2.00394C0.264966 35 -0.645525 32.9339 0.527884 31.6505L12.2316 18.8495C12.9302 18.0855 12.9302 16.9145 12.2316 16.1505L0.527886 3.34954Z"
        fill={color}
        transform="translate(-83, -17.5)"
        style="filter: drop-shadow(0 0 4px {color})"
      />
    </g>
  {/each}
</g>

<style>
  .chevron-wrapper {
    animation: chevronPulse 3s infinite var(--animation-delay);
  }

  @keyframes chevronPulse {
    0% {
      opacity: 0.1;
    }
    20% {
      opacity: 0.3;
    }
    40% {
      opacity: 0.3;
    }
    60% {
      opacity: 0.6;
    }
    100% {
      opacity: 0.2;
    }
  }
</style>
