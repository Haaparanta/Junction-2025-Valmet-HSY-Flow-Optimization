<script lang="ts">
  import Icon from '@iconify/svelte'
  import { getSimulationContext } from '../logic.svelte'

  const ctx = getSimulationContext()

  const numberFormatter = new Intl.NumberFormat('en', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1
  })

  const percentFormatter = new Intl.NumberFormat('en', {
    maximumFractionDigits: 0
  })

  const currencyFormatter = new Intl.NumberFormat('en', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0
  })

  const priceFormatter = new Intl.NumberFormat('en', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  })

  const timeFormatter = new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit'
  })

  const shortTimeFormatter = new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit'
  })

  const sumNumbers = (values: number[]) =>
    values.reduce((total, value) => total + (Number.isFinite(value) ? value : 0), 0)

  const average = (values: number[]) => (values.length ? sumNumbers(values) / values.length : 0)
  const safeMax = (values: number[]) => (values.length ? Math.max(...values) : 0)
  const safeMin = (values: number[]) => (values.length ? Math.min(...values) : 0)

  const totalCost = $derived.by(() => sumNumbers(ctx.simulatedPrice))
  const totalEnergy = $derived.by(() => sumNumbers(ctx.simulatedElectricityUse))
  const avgPrice = $derived.by(() => average(ctx.electricityPrices))
  const peakPrice = $derived.by(() => safeMax(ctx.electricityPrices))

  const totalInflow = $derived.by(() => sumNumbers(ctx.inflowPrediction))
  const totalOutflow = $derived.by(() => sumNumbers(ctx.outflowStrategy))
  const netFlow = $derived.by(() => totalInflow - totalOutflow)

  const waterLevelRange = $derived.by(() => safeMax(ctx.simulatedWaterLevel) - safeMin(ctx.simulatedWaterLevel))
  const waterLevelDelta = $derived.by(() => {
    const sampleCount = Math.min(ctx.timeStamps.length, ctx.simulatedWaterLevel.length)
    if (sampleCount === 0) return 0
    const first = ctx.simulatedWaterLevel[0] ?? 0
    const last = ctx.simulatedWaterLevel[sampleCount - 1] ?? first
    return last - first
  })

  const pumpUptime = $derived.by(() => {
    if (!ctx.outflowStrategy.length) return 0
    const activeSlots = ctx.outflowStrategy.filter((value) => value > 0.1).length
    return (activeSlots / ctx.outflowStrategy.length) * 100
  })

  const cheapestSlot = $derived.by(() => {
    if (!ctx.electricityPrices.length) return null
    let minIndex = 0
    for (let i = 1; i < ctx.electricityPrices.length; i++) {
      if (ctx.electricityPrices[i] < ctx.electricityPrices[minIndex]) {
        minIndex = i
      }
    }

    const timestamp = ctx.timeStamps[minIndex]
    const price = ctx.electricityPrices[minIndex]
    const date = timestamp ? new Date(timestamp) : null
    const isValidDate = date && !isNaN(date.getTime())

    return {
      priceLabel: priceFormatter.format(price),
      timeLabel: isValidDate ? timeFormatter.format(date) : '—'
    }
  })

  const liveTimestamp = $derived.by(() => {
    const ts = ctx.timeStamps[ctx.currentTimeIndex]
    const date = ts ? new Date(ts) : null
    const isValidDate = date && !isNaN(date.getTime())
    return isValidDate ? shortTimeFormatter.format(date) : '--:--'
  })

  const stats = $derived.by(() => [
    {
      label: 'Cost Forecast',
      value: currencyFormatter.format(totalCost),
      hint: `Avg ${priceFormatter.format(avgPrice)} / kWh`,
      icon: 'solar:wallet-money-line-duotone'
    },
    {
      label: 'Energy Use',
      value: `${numberFormatter.format(totalEnergy)} kWh`,
      hint: `${percentFormatter.format(pumpUptime)}% pump uptime`,
      icon: 'solar:bolt-circle-line-duotone'
    }
    // {
    //   label: 'Flow Balance',
    //   value: `${netFlow >= 0 ? '+' : ''}${numberFormatter.format(netFlow)} m³`,
    //   hint: `${numberFormatter.format(totalInflow)} in / ${numberFormatter.format(totalOutflow)} out`,
    //   icon: 'solar:waterdrops-line-duotone'
    // },
    // {
    //   label: 'Storage Swing',
    //   value: `${numberFormatter.format(waterLevelRange)} m`,
    //   hint: `${waterLevelDelta >= 0 ? '+' : ''}${numberFormatter.format(waterLevelDelta)} m vs start`,
    //   icon: 'solar:chart-line-duotone'
    // }
  ])
</script>

<div class="flex min-w-2xs flex-1 flex-col gap-2">
  <div class="grid flex-1 grid-cols-2 gap-2">
    {#each stats as stat}
      <div class="card-glass rounded-md border border-(--color-border-secondary) p-3">
        <div class="flex items-center gap-2 text-[11px] font-semibold tracking-wide text-text-muted uppercase">
          <Icon icon={stat.icon} class="h-4 w-4 text-accent-primary" aria-hidden="true" />
          {stat.label}
        </div>
        <p class="mt-1 text-xl font-semibold text-text-primary">{stat.value}</p>
        <p class="text-xs text-text-secondary">{stat.hint}</p>
      </div>
    {/each}
  </div>

  {#if cheapestSlot}
    <div
      class="card-glass flex items-center justify-between rounded-md border border-(--color-accent-border) px-4 py-3"
    >
      <div>
        <p class="text-[11px] font-semibold tracking-wide text-text-muted uppercase">Cheapest slot</p>
        <p class="text-sm font-semibold text-text-primary">{cheapestSlot.timeLabel}</p>
      </div>
      <div class="text-right">
        <p class="text-xl font-semibold text-accent-primary">{cheapestSlot.priceLabel}</p>
        <p class="text-xs text-text-secondary">€/kWh</p>
      </div>
    </div>
  {/if}
</div>
