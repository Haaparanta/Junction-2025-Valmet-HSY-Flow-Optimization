<script lang="ts">
  import { getContext } from 'svelte'

  const { height } = getContext<any>('LayerCake')

  let { label = '' } = $props()
</script>

<text x="50%" y={$height + 35} text-anchor="middle" fill="var(--color-text-muted)" font-size="12">
  {label}
</text>
