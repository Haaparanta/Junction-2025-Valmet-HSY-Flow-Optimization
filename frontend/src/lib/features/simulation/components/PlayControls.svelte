<script lang="ts">
  import Button from '$lib/components/Button.svelte'
  import { getSimulationContext } from '../logic.svelte'

  const ctx = getSimulationContext()

  const maxIndex = $derived(ctx.timeStamps.length - 1)

  function handleSkipToStart() {
    ctx.currentTimeIndex = 0
  }

  function handleStepBackward() {
    if (ctx.currentTimeIndex > 0) {
      ctx.currentTimeIndex--
    }
  }

  function handleStepForward() {
    if (ctx.currentTimeIndex < maxIndex) {
      ctx.currentTimeIndex++
    }
  }

  function handleSkipToEnd() {
    ctx.currentTimeIndex = maxIndex
  }

  function handleSliderChange(event: Event) {
    const target = event.target as HTMLInputElement
    ctx.currentTimeIndex = parseInt(target.value)
  }

  const thumbPosition = $derived((ctx.currentTimeIndex / maxIndex) * 100)

  const formattedTime = $derived(() => {
    const timestamp = ctx.timeStamps[ctx.currentTimeIndex]
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  })

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      handleStepBackward()
    } else if (event.key === 'ArrowRight') {
      event.preventDefault()
      handleStepForward()
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- Playback Controls -->
<div class="flex flex-wrap items-center justify-center gap-2">
  <div class="flex gap-2">
    <Button variant="outline" onclick={handleSkipToStart} disabled={ctx.currentTimeIndex === 0}>
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
      </svg>
    </Button>

    <Button variant="outline" onclick={handleStepBackward} disabled={ctx.currentTimeIndex === 0}>
      <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
    </Button>
  </div>

  <div class="relative min-w-2xs flex-1 px-2">
    <div class="pointer-events-none absolute -top-9 -translate-x-1/2 transform" style="left: {thumbPosition}%">
      <div class="card-glass-secondary rounded-lg border border-(--color-accent-border) px-3 py-1.5">
        <span class="text-xs font-semibold tracking-wide whitespace-nowrap text-(--color-accent-primary)">
          {formattedTime()}
        </span>
      </div>
    </div>
    <input
      type="range"
      value={ctx.currentTimeIndex}
      oninput={handleSliderChange}
      min="0"
      max={maxIndex}
      step="1"
      class="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-cyan-500
             [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:cursor-pointer
             [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-2
             [&::-moz-range-thumb]:border-cyan-400 [&::-moz-range-thumb]:bg-cyan-500
             [&::-moz-range-thumb]:shadow-[0_0_8px_rgba(34,211,238,0.5)] [&::-webkit-slider-thumb]:h-4
             [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:appearance-none
             [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2
             [&::-webkit-slider-thumb]:border-cyan-400 [&::-webkit-slider-thumb]:bg-cyan-500
             [&::-webkit-slider-thumb]:shadow-[0_0_8px_rgba(34,211,238,0.5)]"
    />
  </div>

  <div class="flex gap-2">
    <Button variant="outline" onclick={handleStepForward} disabled={ctx.currentTimeIndex === maxIndex}>
      <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
    </Button>

    <Button variant="outline" onclick={handleSkipToEnd} disabled={ctx.currentTimeIndex === maxIndex}>
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
      </svg>
    </Button>
  </div>
</div>
