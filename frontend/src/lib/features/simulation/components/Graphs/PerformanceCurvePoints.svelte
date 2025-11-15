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

{#each data as point, i}
  {@const efficiency = efficiencyScores[i]}
  {@const color = getColorForEfficiency(efficiency)}
  <circle cx={$xGet(point)} cy={$yGet(point)} r="5" fill={color} stroke="var(--color-bg-secondary)" stroke-width="2" />
{/each}
