<script lang="ts">
  import Icon from '@iconify/svelte'
  import { flip } from 'svelte/animate'
  import { fade } from 'svelte/transition'
  import { getSimulationContext } from '../logic.svelte'
  import PumpControl from './PumpControl.svelte'

  const ctx = getSimulationContext()

  let pumps = $derived(ctx.current.simulatedPumps)
</script>

<div
  class="relative z-10 flex w-full flex-col gap-6 rounded-md"
  style="background: radial-gradient(ellipse at center, rgba(2, 6, 23, 0.4) 0%, rgba(2, 6, 23, 0.25) 50%, transparent 100%);"
>
  <div class="flex items-center justify-center gap-2 text-blue-400">
    <Icon icon="lucide:gauge" class="h-5 w-5" />
    <span>Pump Array</span>
  </div>

  <div class="grid grid-cols-2 gap-x-6 gap-y-2">
    {#each pumps as pump, index (pump.name)}
      <div
        class={index % 2 === 1 ? 'mt-12' : ''}
        transition:fade={{ duration: 300, delay: index * 50 }}
        animate:flip={{ duration: 300 }}
      >
        <PumpControl {...pump} />
      </div>
    {/each}
  </div>
</div>
