<script lang="ts">
  import InputGraph from './Graphs/InputGraph.svelte'
  import OutputGraph from './Graphs/OutputGraph.svelte'
  import SimulationStats from './SimulationStats.svelte'
</script>

<SimulationStats />
<div
  class="card-glass card-glass flex h-40 min-h-40 min-w-2xs flex-1 flex-col items-center justify-between gap-3 rounded-md border border-(--color-accent-border) p-4 px-4 py-5"
>
  <InputGraph />
</div>
<div
  class="card-glass card-glass flex h-40 min-h-40 min-w-2xs flex-1 flex-col items-center justify-between gap-3 rounded-md border border-(--color-accent-border) p-4 px-4 py-5"
>
  <OutputGraph />
</div>
