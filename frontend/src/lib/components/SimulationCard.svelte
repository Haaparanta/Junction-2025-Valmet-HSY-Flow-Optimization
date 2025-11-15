<script lang="ts">
  import type { SimulationMetadataDTO } from '$lib/api'
  import Icon from '@iconify/svelte'

  let { simulation }: { simulation: SimulationMetadataDTO } = $props()

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
</script>

{#snippet statistic(icon: string, label: string, value: string, color: string)}
  <div class="flex items-center gap-2 rounded-lg bg-slate-900/60 p-3">
    <Icon {icon} class="h-5 w-5 {color}" />
    <div>
      <p class="text-xs text-slate-400">{label}</p>
      <p class="text-sm font-semibold text-slate-200">{value}</p>
    </div>
  </div>
{/snippet}

<a
  href="/{simulation.id}"
  class="group block rounded-md border border-slate-800 bg-slate-950/80 p-6 backdrop-blur transition-all hover:border-cyan-500/50 hover:bg-slate-800/50"
  aria-label="View simulation {simulation.name}"
>
  <div class="flex items-start justify-between gap-6">
    <div class="flex-1 space-y-4">
      <div class="flex items-center gap-4">
        <div
          class="flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-500/20 text-cyan-400 group-hover:bg-cyan-500/30"
          aria-hidden="true"
        >
          <Icon icon="mdi:chart-bar" class="h-6 w-6" />
        </div>
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-slate-200 group-hover:text-cyan-400">
            {simulation.name}
          </h3>
          <p class="text-sm text-slate-400">
            <time datetime={simulation.timestamp}>{formatDate(simulation.timestamp)}</time>
          </p>
        </div>
      </div>

      <!-- Statistics Grid -->
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4" role="list" aria-label="Simulation statistics">
        {@render statistic('mdi:currency-eur', 'Cost', `€${simulation.total_cost.toFixed(2)}`, 'text-amber-400')}
        {@render statistic(
          'mdi:water',
          'Start Level',
          `${simulation.starting_water_level.toFixed(2)}m`,
          'text-cyan-400'
        )}
        {@render statistic(
          'mdi:chart-line',
          'Avg Level',
          `${simulation.average_water_level.toFixed(2)}m`,
          'text-violet-400'
        )}
        {@render statistic(
          'mdi:lightning-bolt',
          'Energy',
          `${simulation.total_electricity_consumption.toFixed(0)} kWh`,
          'text-emerald-500'
        )}
      </div>
    </div>

    <div class="flex items-center text-slate-400 group-hover:text-cyan-400" aria-hidden="true">
      <Icon icon="mdi:chevron-right" class="h-6 w-6" />
    </div>
  </div>
</a>
