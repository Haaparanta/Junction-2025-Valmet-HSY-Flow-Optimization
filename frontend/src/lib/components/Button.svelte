<script lang="ts">
  import Icon from '@iconify/svelte'

  interface Props {
    variant?: 'primary' | 'outline' | 'ghost'
    children: any
    onclick?: (event: MouseEvent) => void
    disabled?: boolean
    type?: 'button' | 'submit' | 'reset'
    href?: string
    leftIcon?: string
    rightIcon?: string
  }

  let {
    variant = 'primary',
    children,
    onclick,
    disabled = false,
    type = 'button',
    href,
    leftIcon,
    rightIcon
  }: Props = $props()

  const variantClasses = {
    primary:
      'bg-(--color-accent-primary) text-background-primary shadow-[0_0_25px_rgba(34,211,238,0.35)] hover:bg-cyan-400/90 hover:shadow-[0_0_30px_rgba(34,211,238,0.45)] active:bg-cyan-300 disabled:bg-text-disabled disabled:text-background-primary disabled:shadow-none',
    outline:
      'border border-(--color-accent-border) text-(--color-accent-primary) bg-background-card-secondary hover:bg-(--color-accent-bg) hover:border-(--color-accent-primary) active:bg-[rgba(15,23,42,0.9)] disabled:border-(--color-border-secondary) disabled:text-text-disabled',
    ghost:
      'text-(--color-accent-primary) hover:bg-(--color-hover-bg) hover:text-(--color-hover-text) active:bg-[rgba(15,23,42,0.9)] disabled:text-text-disabled'
  }
</script>

{#snippet content()}
  {#if leftIcon}
    <Icon icon={leftIcon} class="h-4 w-4" aria-hidden="true" />
  {/if}

  {@render children()}

  {#if rightIcon}
    <Icon icon={rightIcon} class="h-4 w-4" aria-hidden="true" />
  {/if}
{/snippet}

{#if href}
  <a
    {href}
    aria-disabled={disabled ? 'true' : undefined}
    tabindex={disabled ? -1 : undefined}
    {onclick}
    class="inline-flex items-center justify-center gap-2 rounded-md border border-transparent bg-background-card px-5 py-2.5 text-sm font-semibold tracking-wide text-text-primary shadow-[0_18px_45px_rgba(15,23,42,0.8)] ring-1 ring-[rgba(15,23,42,0.9)] backdrop-blur-md transition-[background-color,box-shadow,color,border-color] duration-150 disabled:cursor-not-allowed disabled:opacity-70 {disabled
      ? 'pointer-events-none opacity-70'
      : ''} {variantClasses[variant]}"
  >
    {@render content()}
  </a>
{:else}
  <button
    {type}
    {disabled}
    {onclick}
    class="inline-flex items-center justify-center gap-2 rounded-md border border-transparent bg-background-card px-5 py-2.5 text-sm font-semibold tracking-wide text-text-primary shadow-[0_18px_45px_rgba(15,23,42,0.8)] ring-1 ring-[rgba(15,23,42,0.9)] backdrop-blur-md transition-[background-color,box-shadow,color,border-color] duration-150 disabled:cursor-not-allowed disabled:opacity-70 {variantClasses[
      variant
    ]}"
  >
    {@render content()}
  </button>
{/if}
