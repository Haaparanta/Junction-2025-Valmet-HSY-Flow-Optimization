<script lang="ts">
  import { Html, LayerCake, Svg } from 'layercake'
  import { getSimulationContext } from '../../logic.svelte'
  import AxisX from './AxisX.svelte'
  import AxisY from './AxisY.svelte'
  import Bar from './Bar.svelte'
  import Line from './Line.svelte'
  import QuadTree from './QuadTree.svelte'
  import TimeIndicator from './TimeIndicator.svelte'
  import Tooltip from './Tooltip.svelte'

  type DataPoint = {
    x: number
    y: number
    rawY: number
    index: number
  }

  type Dataset = {
    name: string
    unit: string
    color: string
    data: DataPoint[]
    yAxisSide: 'left' | 'right'
    formatValue: (value: number) => string
  }

  const ctx = getSimulationContext()

  const datasets = $derived.by((): Dataset[] => {
    const electricityData =
      ctx.electricityPrices.length === ctx.timeStamps.length
        ? ctx.electricityPrices.map((value, index) => ({
            x: new Date(ctx.timeStamps[index]).getTime(),
            y: value,
            rawY: value,
            index
          }))
        : []

    const inflowData =
      ctx.inflowPrediction.length === ctx.timeStamps.length
        ? ctx.inflowPrediction.map((value, index) => ({
            x: new Date(ctx.timeStamps[index]).getTime(),
            y: value,
            rawY: value,
            index
          }))
        : []

    const outflowData =
      ctx.outflowStrategy.length === ctx.timeStamps.length
        ? ctx.outflowStrategy.map((value, index) => ({
            x: new Date(ctx.timeStamps[index]).getTime(),
            y: value,
            rawY: value,
            index
          }))
        : []

    const rainfallData =
      ctx.weatherForecast.length === ctx.timeStamps.length
        ? ctx.weatherForecast.map((value, index) => ({
            x: new Date(ctx.timeStamps[index]).getTime(),
            y: value,
            rawY: value,
            index
          }))
        : []

    return [
      {
        name: 'Electricity Price',
        unit: '€/kWh',
        color: 'var(--color-chart-electricity)',
        data: electricityData,
        yAxisSide: 'left' as const,
        formatValue: (v: number) => v.toFixed(2)
      },
      {
        name: 'Inflow Prediction',
        unit: 'm³/s',
        color: 'var(--color-chart-inflow)',
        data: inflowData,
        yAxisSide: 'right' as const,
        formatValue: (v: number) => v.toFixed(0)
      },
      {
        name: 'Outflow Strategy',
        unit: 'm³/s',
        color: 'var(--color-chart-strategy)',
        data: outflowData,
        yAxisSide: 'right' as const,
        formatValue: (v: number) => v.toFixed(1)
      },
      {
        name: 'Expected Rainfall',
        unit: 'mm',
        color: 'var(--color-chart-result)',
        data: rainfallData,
        yAxisSide: 'left' as const,
        formatValue: (v: number) => v.toFixed(1)
      }
    ]
  })

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    const hour = date.getHours()
    return `${hour}`
  }

  // Normalize data to 0-1 range for rendering
  const normalizeToScale = (value: number, min: number, max: number) => {
    if (max === min) return 0
    return (value - min) / (max - min)
  }

  // Calculate extents and normalized data for each dataset
  const normalizedDatasets = $derived.by(() => {
    return datasets.map((dataset) => {
      const values = dataset.data.map((d) => d.y)
      const extent = [Math.min(...values), Math.max(...values)]

      return {
        ...dataset,
        extent,
        normalizedData: dataset.data.map((d) => ({
          ...d,
          y: normalizeToScale(d.y, extent[0], extent[1])
        })),
        formatAxisValue: (normalized: number) => {
          const value = normalized * (extent[1] - extent[0]) + extent[0]
          return dataset.formatValue(value)
        }
      }
    })
  })

  const allNormalizedData = $derived(normalizedDatasets.flatMap((dataset) => dataset.normalizedData))

  const indicatorX = $derived.by<number | null>(() => {
    const timestamp = ctx.timeStamps[ctx.currentTimeIndex]
    return timestamp ? new Date(timestamp).getTime() : null
  })

  const indicatorXNext = $derived.by<number | null>(() => {
    const nextIndex = ctx.currentTimeIndex + 1
    if (nextIndex >= ctx.timeStamps.length) return null
    const timestamp = ctx.timeStamps[nextIndex]
    return timestamp ? new Date(timestamp).getTime() : null
  })

  // Group datasets by y-axis side
  const leftAxisDatasets = $derived(normalizedDatasets.filter((d) => d.yAxisSide === 'left'))
  const rightAxisDatasets = $derived(normalizedDatasets.filter((d) => d.yAxisSide === 'right'))

  // Calculate current values for legend
  const currentElectricityPrice = $derived.by(() => {
    const electricityDataset = datasets.find((d) => d.name === 'Electricity Price')
    return electricityDataset?.data[ctx.currentTimeIndex]?.rawY ?? 0
  })

  const currentInflow = $derived.by(() => {
    const inflowDataset = datasets.find((d) => d.name === 'Inflow Prediction')
    return inflowDataset?.data[ctx.currentTimeIndex]?.rawY ?? 0
  })

  const currentOutflow = $derived.by(() => {
    const outflowDataset = datasets.find((d) => d.name === 'Outflow Strategy')
    return outflowDataset?.data[ctx.currentTimeIndex]?.rawY ?? 0
  })

  const currentRainfall = $derived.by(() => {
    const rainfallDataset = datasets.find((d) => d.name === 'Expected Rainfall')
    return rainfallDataset?.data[ctx.currentTimeIndex]?.rawY ?? 0
  })

  // Separate line datasets from bar datasets
  const lineDatasets = $derived(normalizedDatasets.filter((d) => d.name !== 'Expected Rainfall'))
  const barDatasets = $derived(normalizedDatasets.filter((d) => d.name === 'Expected Rainfall'))
</script>

{#if datasets.length > 0 && datasets.every((d) => d.data.length > 0)}
  <div class="flex items-center justify-end gap-6">
    {#each datasets as dataset}
      {@const currentValue =
        dataset.name === 'Electricity Price'
          ? currentElectricityPrice
          : dataset.name === 'Inflow Prediction'
            ? currentInflow
            : dataset.name === 'Outflow Strategy'
              ? currentOutflow
              : currentRainfall}
      <div class="flex items-center gap-2">
        <div class="h-0.5 w-6" style="background-color: {dataset.color}"></div>
        <span class="text-xs" style="color: var(--color-text-secondary)">
          {dataset.name}: <span class="font-semibold">{dataset.formatValue(currentValue)}</span>
          {dataset.unit}
        </span>
      </div>
    {/each}
  </div>
  <LayerCake padding={{ top: 0, right: 40, bottom: 10, left: 40 }} x="x" y="y" data={allNormalizedData} yNice={true}>
    <Svg>
      {#if leftAxisDatasets.length > 0}
        <AxisY
          gridlines={true}
          label={leftAxisDatasets[0].unit}
          side="left"
          format={leftAxisDatasets[0].formatAxisValue}
        />
      {/if}
      {#if rightAxisDatasets.length > 0}
        <AxisY
          gridlines={false}
          label={rightAxisDatasets[0].unit}
          side="right"
          format={rightAxisDatasets[0].formatAxisValue}
        />
      {/if}
      <AxisX gridlines={true} format={formatTime} hoursOnly={true} />
      {#each barDatasets as dataset}
        <Bar fill={dataset.color} opacity={0.3} data={dataset.normalizedData} />
      {/each}
      {#each lineDatasets as dataset}
        <Line stroke={dataset.color} strokeWidth={2} data={dataset.normalizedData} />
      {/each}
      <TimeIndicator x={indicatorX ?? undefined} xNext={indicatorXNext ?? undefined} />
    </Svg>
    <Html>
      <QuadTree
        y="x"
        dataset={normalizedDatasets[0]?.normalizedData || []}
        onSelect={(point) => {
          if (point?.index !== undefined) {
            ctx.currentTimeIndex = point.index
          }
        }}
      >
        {#snippet children({ x, y, visible, found }: { x: number; y: number; visible: boolean; found: DataPoint })}
          {@const foundIndex = found?.index ?? -1}
          {@const tooltipDatasets =
            foundIndex >= 0
              ? datasets.map((dataset) => ({
                  name: dataset.name,
                  value: dataset.data[foundIndex]?.rawY || 0,
                  unit: dataset.unit,
                  color: dataset.color
                }))
              : []}
          {@const anchorDataset = normalizedDatasets[0]}
          {@const anchorY = foundIndex >= 0 ? (anchorDataset?.normalizedData[foundIndex]?.y ?? null) : null}
          <Tooltip
            {x}
            anchorY={anchorY ?? undefined}
            {visible}
            datasets={tooltipDatasets}
            timestamp={foundIndex >= 0 ? found?.x : 0}
          />
        {/snippet}
      </QuadTree>
    </Html>
  </LayerCake>
{/if}
