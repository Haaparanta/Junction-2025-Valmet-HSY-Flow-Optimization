<script lang="ts">
  import Button from '$lib/components/Button.svelte'
  import Graphs from '$lib/features/simulation/components/Graphs.svelte'
  import InflowBasin from '$lib/features/simulation/components/InflowBasin.svelte'
  import PlayControls from '$lib/features/simulation/components/PlayControls.svelte'
  import PumpArray from '$lib/features/simulation/components/PumpArray.svelte'
  import WaterflowAnimation from '$lib/features/simulation/components/WaterflowAnimation.svelte'
  import { createSimulationContext } from '$lib/features/simulation/logic.svelte'

  const { data } = $props()

  const ctx = createSimulationContext()

  let inflowBasin = $state<HTMLDivElement | undefined>(undefined)

  $effect(() => {
    ctx.setSimulation(data.simulation)
  })
</script>

<header class="flex flex-wrap items-center justify-between gap-4 px-6 py-4">
  <Button variant="outline" href="/" leftIcon="mdi:arrow-left">Back</Button>

  <div class="flex flex-1 flex-col text-center sm:text-left">
    <p class="text-xs font-semibold tracking-wide text-slate-400 uppercase">Simulation</p>
    <h1 class="text-2xl font-semibold text-slate-100">{data.simulation.name || data.simulation.timestamp}</h1>
  </div>
</header>

<div class="relative rounded-md border border-slate-800 bg-slate-950/80 p-8 backdrop-blur">
  <PlayControls />
</div>

<div class="flex w-full flex-wrap gap-2">
  <div class="relative flex flex-2 flex-col gap-2">
    <Graphs />
  </div>
  <div class="relative flex-3 rounded-md border border-slate-800 bg-slate-950/80 p-8 backdrop-blur">
    <div class="flex flex-wrap items-center justify-between gap-48">
      <WaterflowAnimation inflowRef={inflowBasin} />

      <div class="flex w-full flex-1 items-center justify-center">
        <InflowBasin
          bind:ref={inflowBasin}
          maxHeight={14.5}
          currentHeight={ctx.current.simulatedWaterLevel}
          currentInflow={ctx.current.inflowPrediction}
        />
      </div>

      <div class="flex w-full flex-1 items-center justify-center">
        <PumpArray />
      </div>
    </div>
  </div>
</div>
