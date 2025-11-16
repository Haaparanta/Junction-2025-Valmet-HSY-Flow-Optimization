<script lang="ts">
  import { goto } from '$app/navigation'
  import { generateNewSimulation, type SimulationMetadataDTO } from '$lib/api'
  import Button from '$lib/components/Button.svelte'
  import LoadingSpinner from '$lib/components/LoadingSpinner.svelte'
  import SimulationCard from '$lib/components/SimulationCard.svelte'
  import type { FormEventHandler } from 'svelte/elements'

  const { data } = $props()

  let generating = $state<boolean>(false)
  let sortBy = $state<'timestamp' | 'cost' | 'energy' | 'name'>('timestamp')
  let sortOrder = $state<'asc' | 'desc'>('desc')

  const handleSubmit: FormEventHandler<HTMLFormElement> = async (event) => {
    event.preventDefault()
    const values = new FormData(event.currentTarget)
    const name = values.get('simulationName')?.toString()
    await handleGenerateSimulation(name)
  }

  const handleGenerateSimulation = async (name?: string) => {
    generating = true
    try {
      const trimmedName = name?.trim() || undefined
      const newSim = await generateNewSimulation(trimmedName)
      await goto(`/${newSim.id}`)
    } catch (err) {
      console.error('Failed to generate simulation:', err)
    } finally {
      generating = false
    }
  }

  const handleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'
    } else {
      sortBy = field
      sortOrder = 'desc'
    }
  }

  const sortedSimulations = $derived.by(async (): Promise<SimulationMetadataDTO[]> => {
    const depsTracked = [sortBy, sortOrder]
    const sims = await data.simulations
    if (!sims) return []

    const sorted = [...sims].sort((a: SimulationMetadataDTO, b: SimulationMetadataDTO) => {
      let comparison = 0
      switch (sortBy) {
        case 'timestamp':
          comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          break
        case 'cost':
          comparison = a.total_cost - b.total_cost
          break
        case 'energy':
          comparison = a.total_electricity_consumption - b.total_electricity_consumption
          break
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })
    return sorted
  })
</script>

<div class="mx-auto max-w-5xl space-y-8">
  <div class="flex flex-col items-center justify-between gap-4">
    <div>
      <h1 class="text-3xl font-bold text-slate-200">Simulations</h1>
      <p class="mt-2 text-slate-400">Browse and deep dive in to pumping strategies</p>
    </div>
    <form class="flex w-full max-w-md flex-col gap-2 sm:flex-row" onsubmit={handleSubmit}>
      <label class="sr-only" for="header-simulation-name">Simulation name</label>
      <input
        id="header-simulation-name"
        type="text"
        class="flex-1 rounded-xl border border-border-secondary bg-background-card px-4 py-2 text-sm font-medium text-text-primary placeholder-text-muted shadow-[0_12px_30px_rgba(2,6,23,0.65)] transition focus:border-(--color-accent-primary) focus:ring-2 focus:ring-(--color-accent-primary)/40 focus:outline-none disabled:cursor-not-allowed disabled:opacity-70"
        placeholder="Optional simulation name"
        name="simulationName"
        disabled={generating}
      />
      <Button variant="primary" type="submit" disabled={generating}>
        {generating ? 'Generating...' : '+ New Simulation'}
      </Button>
    </form>
  </div>

  {#await data.simulations}
    <LoadingSpinner message="Loading Simulations" subtitle="Fetching simulation history..." />
  {:then simulations}
    {#if simulations?.length === 0}
      <div
        class="relative flex min-h-96 flex-col items-center justify-center gap-6 rounded-xl border border-slate-800 bg-slate-950/80 p-12 backdrop-blur"
      >
        <div class="text-center">
          <h2 class="mb-2 text-2xl font-bold text-slate-200">No Simulations Yet</h2>
          <p class="text-slate-400">Get started by generating your first simulation</p>
        </div>
      </div>
    {:else}
      <!-- Sort Controls -->
      <div class="flex flex-wrap gap-2" role="toolbar" aria-label="Sort simulations">
        <span class="self-center text-sm text-slate-400">Sort by:</span>
        <button
          onclick={() => handleSort('timestamp')}
          class="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:border-cyan-500/50 hover:text-cyan-400"
          class:!border-cyan-500={sortBy === 'timestamp'}
          class:!text-cyan-400={sortBy === 'timestamp'}
          aria-pressed={sortBy === 'timestamp'}
        >
          Date
          {#if sortBy === 'timestamp'}
            <span aria-label={sortOrder === 'asc' ? 'ascending' : 'descending'}>
              {sortOrder === 'asc' ? '↑' : '↓'}
            </span>
          {/if}
        </button>
        <button
          onclick={() => handleSort('name')}
          class="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:border-cyan-500/50 hover:text-cyan-400"
          class:!border-cyan-500={sortBy === 'name'}
          class:!text-cyan-400={sortBy === 'name'}
          aria-pressed={sortBy === 'name'}
        >
          Name
          {#if sortBy === 'name'}
            <span aria-label={sortOrder === 'asc' ? 'ascending' : 'descending'}>
              {sortOrder === 'asc' ? '↑' : '↓'}
            </span>
          {/if}
        </button>
        <button
          onclick={() => handleSort('cost')}
          class="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:border-cyan-500/50 hover:text-cyan-400"
          class:!border-cyan-500={sortBy === 'cost'}
          class:!text-cyan-400={sortBy === 'cost'}
          aria-pressed={sortBy === 'cost'}
        >
          Cost
          {#if sortBy === 'cost'}
            <span aria-label={sortOrder === 'asc' ? 'ascending' : 'descending'}>
              {sortOrder === 'asc' ? '↑' : '↓'}
            </span>
          {/if}
        </button>
        <button
          onclick={() => handleSort('energy')}
          class="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-1.5 text-sm font-medium text-slate-300 transition hover:border-cyan-500/50 hover:text-cyan-400"
          class:!border-cyan-500={sortBy === 'energy'}
          class:!text-cyan-400={sortBy === 'energy'}
          aria-pressed={sortBy === 'energy'}
        >
          Energy
          {#if sortBy === 'energy'}
            <span aria-label={sortOrder === 'asc' ? 'ascending' : 'descending'}>
              {sortOrder === 'asc' ? '↑' : '↓'}
            </span>
          {/if}
        </button>
      </div>

      <!-- Simulations List -->
      <ul class="space-y-4" role="list" aria-label="Available simulations">
        {#await sortedSimulations then sortedSims}
          {#each sortedSims as simulation (simulation.id)}
            <li>
              <SimulationCard {simulation} />
            </li>
          {/each}
        {/await}
      </ul>
    {/if}
  {:catch error}
    <div
      class="relative flex min-h-96 flex-col items-center justify-center gap-6 rounded-xl border border-slate-800 bg-slate-950/80 p-12 backdrop-blur"
    >
      <div class="text-center">
        <h2 class="mb-2 text-2xl font-bold text-slate-200">Failed to Load Simulations</h2>
        <p class="text-slate-400">{error.message}</p>
      </div>
    </div>
  {/await}
</div>
