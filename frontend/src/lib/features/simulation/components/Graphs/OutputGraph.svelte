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
    renderType: 'line' | 'bar'
    stackIndex?: number
  }

  const ctx = getSimulationContext()

  // Define pump colors - cycling through chart colors
  const pumpColors = [
    '#10b981', // emerald-500 (strategy)
    '#f59e0b', // amber-500 (electricity)
    '#06b6d4', // cyan-500 (inflow)
    '#f59e0b', // amber-500
    '#ec4899', // pink-500
    '#8b5cf6', // violet-500
    '#06b6d4', // cyan-500
    '#14b8a6' // teal-500
  ]

  // Create gradient string for use in styles
  const gradientColors = pumpColors.join(', ')

  // Define datasets - these are the raw, un-normalized datasets
  const datasets = $derived.by((): Dataset[] => {
    const waterLevelData =
      ctx.simulatedWaterLevel.length === ctx.timeStamps.length
        ? ctx.simulatedWaterLevel.map((value, index) => ({
            x: new Date(ctx.timeStamps[index]).getTime(),
            y: value,
            rawY: value, // Keep original value for tooltip
            index // Keep index for time tracking
          }))
        : []

    // Create a dataset for each pump
    const pumpDatasets = ctx.simulatedPumps.map((pump, index) => {
      const pumpData =
        pump.forecastedUse.length === ctx.timeStamps.length
          ? pump.forecastedUse.map((value, idx) => ({
              x: new Date(ctx.timeStamps[idx]).getTime(),
              y: value,
              rawY: value, // Keep original value for tooltip
              index: idx // Keep index for time tracking
            }))
          : []

      return {
        name: pump.name,
        unit: 'm³/s',
        color: pumpColors[index % pumpColors.length],
        data: pumpData,
        yAxisSide: 'left' as const,
        formatValue: (v: number) => v.toFixed(1),
        renderType: 'bar' as const,
        stackIndex: index
      }
    })

    // Add water level dataset
    return [
      ...pumpDatasets,
      {
        name: 'Water Level',
        unit: 'm',
        color: 'var(--color-chart-result)',
        data: waterLevelData,
        yAxisSide: 'right' as const,
        formatValue: (v: number) => v.toFixed(1),
        renderType: 'line' as const
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

  // Calculate stacked data for bar datasets
  const stackedData = $derived.by(() => {
    const barDatasets = datasets.filter((d) => d.renderType === 'bar')
    if (barDatasets.length === 0) return []

    const numPoints = barDatasets[0].data.length
    const stacked: { x: number; y: number; y0: number; datasetIndex: number }[][] = []

    for (let i = 0; i < barDatasets.length; i++) {
      stacked[i] = []
      for (let j = 0; j < numPoints; j++) {
        const y0 = i === 0 ? 0 : stacked[i - 1][j].y0 + stacked[i - 1][j].y
        stacked[i][j] = {
          x: barDatasets[i].data[j].x,
          y: barDatasets[i].data[j].y,
          y0,
          datasetIndex: i
        }
      }
    }

    return stacked
  })

  // Calculate extents and normalized data for each dataset
  const normalizedDatasets = $derived.by(() => {
    // Group by axis side to calculate separate extents
    const leftDatasets = datasets.filter((d) => d.yAxisSide === 'left')
    const rightDatasets = datasets.filter((d) => d.yAxisSide === 'right')

    // For left axis (stacked bars), we need the max of the stacked values
    const leftExtent =
      leftDatasets.length > 0
        ? (() => {
            if (stackedData.length > 0) {
              // Find max stacked value
              const maxStacked = Math.max(...stackedData[stackedData.length - 1].map((d) => d.y0 + d.y))
              return [0, maxStacked]
            }
            const allValues = leftDatasets.flatMap((d) => d.data.map((p) => p.y))
            return [Math.min(...allValues), Math.max(...allValues)]
          })()
        : [0, 1]

    // For right axis (line), use min/max
    const rightExtent =
      rightDatasets.length > 0
        ? (() => {
            const allValues = rightDatasets.flatMap((d) => d.data.map((p) => p.y))
            return [Math.min(...allValues), Math.max(...allValues)]
          })()
        : [0, 1]

    return datasets.map((dataset, idx) => {
      const extent = dataset.yAxisSide === 'left' ? leftExtent : rightExtent

      let normalizedData
      if (dataset.renderType === 'bar' && typeof dataset.stackIndex === 'number') {
        // Use stacked data for bars but keep original metadata for tooltips
        normalizedData = stackedData[dataset.stackIndex].map((stackPoint, idx) => {
          const sourcePoint = dataset.data[idx]
          return {
            ...sourcePoint,
            y: normalizeToScale(stackPoint.y, 0, extent[1] - extent[0]),
            y0: normalizeToScale(stackPoint.y0, 0, extent[1] - extent[0])
          }
        })
      } else {
        // Regular normalization for lines while preserving metadata
        normalizedData = dataset.data.map((d) => ({
          ...d,
          y: normalizeToScale(d.y, extent[0], extent[1])
        }))
      }

      return {
        ...dataset,
        extent,
        normalizedData,
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

  const interactionDataset = $derived(normalizedDatasets.find((d) => d.renderType === 'line') ?? normalizedDatasets[0])

  // Calculate current values for legend
  const currentOutflow = $derived.by(() => {
    const pumpDatasets = datasets.filter((d) => d.renderType === 'bar')
    return pumpDatasets.reduce((sum, dataset) => {
      return sum + (dataset.data[ctx.currentTimeIndex]?.rawY || 0)
    }, 0)
  })

  const currentWaterLevel = $derived.by(() => {
    const waterLevelDataset = datasets.find((d) => d.renderType === 'line')
    return waterLevelDataset?.data[ctx.currentTimeIndex]?.rawY ?? 0
  })
</script>

{#if datasets.length > 0 && datasets.every((d) => d.data.length > 0)}
  <div class="flex flex-wrap items-center justify-end gap-4">
    <!-- Combined Outflow legend with gradient -->
    <div class="flex items-center gap-2">
      <div class="gradient-legend h-2 w-2 rounded-full"></div>
      <span class="text-xs" style="color: var(--color-text-secondary)">
        Outflow: <span class="font-semibold">{currentOutflow.toFixed(1)}</span> m³/s
      </span>
    </div>

    <!-- Water Level legend -->
    {#each datasets as dataset}
      {#if dataset.renderType === 'line'}
        <div class="flex items-center gap-2">
          <div class="h-0.5 w-6" style="background-color: {dataset.color}"></div>
          <span class="text-xs" style="color: var(--color-text-secondary)">
            {dataset.name}: <span class="font-semibold">{currentWaterLevel.toFixed(1)}</span>
            {dataset.unit}
          </span>
        </div>
      {/if}
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
      {#each normalizedDatasets as dataset}
        {#if dataset.renderType === 'bar'}
          <Bar fill={dataset.color} opacity={0.6} data={dataset.normalizedData} />
        {:else}
          <Line stroke={dataset.color} strokeWidth={2} data={dataset.normalizedData} />
        {/if}
      {/each}
      <TimeIndicator x={indicatorX ?? undefined} xNext={indicatorXNext ?? undefined} />
    </Svg>
    <Html>
      <QuadTree
        y="x"
        dataset={interactionDataset?.normalizedData || []}
        onSelect={(point) => {
          if (point?.index !== undefined) {
            ctx.currentTimeIndex = point.index
          }
        }}
      >
        {#snippet children({ x, y, visible, found }: { x: number; y: number; visible: boolean; found: DataPoint })}
          {@const foundIndex = found?.index ?? -1}
          {@const pumpDatasets = datasets.filter((d) => d.renderType === 'bar')}
          {@const waterLevelDataset = datasets.find((d) => d.renderType === 'line')}
          {@const totalOutflow =
            foundIndex >= 0
              ? pumpDatasets.reduce((sum, dataset) => {
                  return sum + (dataset.data[foundIndex]?.rawY || 0)
                }, 0)
              : 0}
          {@const tooltipDatasets =
            foundIndex >= 0
              ? [
                  {
                    name: 'Outflow',
                    value: totalOutflow,
                    unit: pumpDatasets[0]?.unit || 'm³/s',
                    color: gradientColors
                  },
                  ...(waterLevelDataset
                    ? [
                        {
                          name: waterLevelDataset.name,
                          value: waterLevelDataset.data[foundIndex]?.rawY || 0,
                          unit: waterLevelDataset.unit,
                          color: waterLevelDataset.color
                        }
                      ]
                    : [])
                ]
              : []}
          {@const anchorY = foundIndex >= 0 ? (interactionDataset?.normalizedData[foundIndex]?.y ?? null) : null}
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

<style>
  @keyframes gradientShift {
    0% {
      background-position: 0% 50%;
    }
    50% {
      background-position: 100% 50%;
    }
    100% {
      background-position: 0% 50%;
    }
  }

  .gradient-legend {
    background: linear-gradient(90deg, #10b981, #f59e0b, #06b6d4, #f59e0b, #ec4899, #8b5cf6, #06b6d4, #14b8a6, #10b981);
    background-size: 300% 100%;
    animation: gradientShift 4s ease-in-out infinite;
  }
</style>
