<script lang="ts">
  import { getContext } from 'svelte'

  type Point = {
    x: number
    y: number
  }

  type Props = {
    data: Point[]
    efficiencyScores: number[]
    getColorForEfficiency: (efficiency: number) => string
  }

  let { data, efficiencyScores, getColorForEfficiency }: Props = $props()

  const { xGet, yGet } = getContext<any>('LayerCake')
</script>

{#each data.slice(0, -1) as point, i}
  {@const nextPoint = data[i + 1]}
  {@const efficiency = (efficiencyScores[i] + efficiencyScores[i + 1]) / 2}
  {@const color = getColorForEfficiency(efficiency)}
  <line
    x1={$xGet(point)}
    y1={$yGet(point)}
    x2={$xGet(nextPoint)}
    y2={$yGet(nextPoint)}
    stroke={color}
    stroke-width="3"
    stroke-linecap="round"
  />
{/each}
